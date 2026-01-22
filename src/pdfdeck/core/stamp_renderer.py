"""
StampRenderer - Dynamiczne generowanie pieczątek.

Odpowiada za:
- Generowanie SVG z konfiguracji
- Renderowanie tekstu po łuku (okrągłe pieczątki)
- Efekty zużycia (worn/aged)
- Przezroczystość przez kanał alpha
"""

import math
import random
from datetime import datetime
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

from pdfdeck.core.models import (
    StampConfig,
    StampShape,
    BorderStyle,
    WearLevel,
)


class StampRenderer:
    """Renderer dynamicznych pieczątek."""

    DPI = 300  # Zwiększone z 150 do 300 dla lepszej jakości (jak znaki wodne)
    FONT_FAMILY = "Arial"

    def __init__(self):
        self._font_cache: dict = {}

    def render_to_png(self, config: StampConfig) -> bytes:
        """
        Renderuje pieczątkę do PNG z kanałem alpha.

        Returns:
            PNG bytes z przezroczystością
        """
        # Przetwórz tekst - zamień [DATA] na aktualną datę
        processed_config = self._process_auto_date(config)

        # Jeśli użytkownik załadował własną pieczątkę z pliku, użyj jej
        if processed_config.stamp_path:
            return self._render_from_file(processed_config)

        # Oblicz rozmiar w pikselach (z marginesem na splatter)
        margin = 20 if processed_config.ink_splatter else 0
        width_px = int(processed_config.width * self.DPI / 72) + margin * 2
        height_px = int(processed_config.height * self.DPI / 72) + margin * 2

        # Dla okrągłych pieczątek użyj kwadratowego obrazu
        if processed_config.shape == StampShape.CIRCLE:
            size = max(width_px, height_px)
            width_px = height_px = size

        # Utwórz RGBA image (przezroczyste tło)
        img = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Konwertuj kolor RGB 0-1 na 0-255
        color_rgb = tuple(int(c * 255) for c in processed_config.color)
        color_rgba = (*color_rgb, 255)

        # Rysuj kształt (z offsetem jeśli jest margines)
        if processed_config.shape == StampShape.CIRCLE:
            self._draw_circular_stamp(img, draw, processed_config, color_rgba, offset=margin)
        elif processed_config.shape == StampShape.OVAL:
            self._draw_oval_stamp(img, draw, processed_config, color_rgba, offset=margin)
        else:
            self._draw_rectangular_stamp(img, draw, processed_config, color_rgba, offset=margin)

        # Aplikuj efekt podwójnego odbicia (przed innymi efektami)
        if processed_config.double_strike:
            img = self._apply_double_strike(img)

        # Aplikuj efekt starodruku
        if processed_config.vintage_effect:
            img = self._apply_vintage_effect(img)

        # Aplikuj efekt zużycia
        if processed_config.wear_level != WearLevel.NONE:
            img = self._apply_wear_effect(img, processed_config.wear_level)

        # Aplikuj rozbryzgi tuszu
        if processed_config.ink_splatter:
            img = self._apply_ink_splatter(img, color_rgba)

        # Aplikuj opacity
        if processed_config.opacity < 1.0:
            img = self._apply_opacity(img, processed_config.opacity)

        # Konwertuj do bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def _process_auto_date(self, config: StampConfig) -> StampConfig:
        """Dodaje lub zamienia datę w tekście pieczątki."""
        if not config.auto_date:
            return config

        today = datetime.now().strftime("%d.%m.%Y")

        # Jeśli tekst zawiera [DATA], zamień na datę
        if "[DATA]" in config.text or "[data]" in config.text:
            new_text = config.text.replace("[DATA]", today).replace("[data]", today)
        else:
            # Dodaj datę pod tekstem głównym
            new_text = f"{config.text}\n{today}"

        # Utwórz nową konfigurację z przetworonym tekstem
        from dataclasses import replace
        return replace(config, text=new_text)


    def _render_from_file(self, config: StampConfig) -> bytes:
        """
        Renderuje pieczątkę z pliku obrazu.

        Args:
            config: Konfiguracja z ustawionym stamp_path

        Returns:
            PNG bytes z zastosowanymi efektami
        """
        # Załaduj obraz z pliku
        try:
            img = Image.open(config.stamp_path)

            # Konwertuj do RGBA jeśli potrzeba
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # Przeskaluj do żądanego rozmiaru
            target_width = int(config.width * self.DPI / 72)
            target_height = int(config.height * self.DPI / 72)

            # Oblicz współczynnik skalowania zachowując proporcje
            width_ratio = target_width / img.width
            height_ratio = target_height / img.height
            scale_ratio = min(width_ratio, height_ratio)  # Dopasuj do mniejszego wymiaru

            # Nowy rozmiar z zachowaniem proporcji
            new_width = int(img.width * scale_ratio)
            new_height = int(img.height * scale_ratio)

            # Przeskaluj obraz (resize działa w obie strony - powiększa i zmniejsza)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Utwórz nowy obraz z właściwym rozmiarem i wycentruj załadowany obraz
            final_img = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))

            # Wycentruj obraz
            x = (target_width - new_width) // 2
            y = (target_height - new_height) // 2
            final_img.paste(img, (x, y), img)

            # Aplikuj efekty (tak samo jak dla generowanych pieczątek)
            if config.double_strike:
                final_img = self._apply_double_strike(final_img)

            if config.vintage_effect:
                final_img = self._apply_vintage_effect(final_img)

            if config.wear_level != WearLevel.NONE:
                final_img = self._apply_wear_effect(final_img, config.wear_level)

            if config.ink_splatter:
                # Dla splatter potrzebujemy koloru - użyjmy czarnego jako domyślny
                color_rgba = (0, 0, 0, 255)
                final_img = self._apply_ink_splatter(final_img, color_rgba)

            if config.opacity < 1.0:
                final_img = self._apply_opacity(final_img, config.opacity)

            # Konwertuj do bytes
            buffer = BytesIO()
            final_img.save(buffer, format="PNG")
            return buffer.getvalue()

        except Exception as e:
            # W razie błędu zwróć pusty obraz
            print(f"Błąd ładowania pieczątki z pliku: {e}")
            empty_img = Image.new("RGBA", (100, 50), (0, 0, 0, 0))
            buffer = BytesIO()
            empty_img.save(buffer, format="PNG")
            return buffer.getvalue()

    def render_to_svg(self, config: StampConfig) -> str:
        """
        Renderuje pieczątkę do SVG.
        Używane dla prostych przypadków bez efektów rastrowych.
        """
        if config.shape == StampShape.CIRCLE:
            return self._generate_circular_svg(config)
        elif config.shape == StampShape.OVAL:
            return self._generate_oval_svg(config)
        else:
            return self._generate_rectangular_svg(config)

    def _get_font(self, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
        """Pobiera font z cache lub tworzy nowy."""
        key = (size, bold)
        if key not in self._font_cache:
            try:
                weight = "Bold" if bold else "Regular"
                self._font_cache[key] = ImageFont.truetype(f"arial{'bd' if bold else ''}.ttf", size)
            except OSError:
                try:
                    self._font_cache[key] = ImageFont.truetype("DejaVuSans-Bold.ttf", size)
                except OSError:
                    self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _draw_rectangular_stamp(
        self,
        img: Image.Image,
        draw: ImageDraw.ImageDraw,
        config: StampConfig,
        color: Tuple[int, int, int, int],
        offset: int = 0,
    ) -> None:
        """Rysuje prostokątną pieczątkę."""
        width, height = img.size
        padding = 5 + offset
        border_width = int(config.border_width * self.DPI / 72)

        # Określ prostokąt
        rect = (padding, padding, width - padding - 1, height - padding - 1)

        # Rysuj ramkę w zależności od stylu
        self._draw_border(draw, rect, config.border_style, color, border_width)

        # Oblicz margines wewnętrzny dla tekstu (większy dla podwójnej ramki)
        if config.border_style == BorderStyle.DOUBLE:
            # Dla podwójnej ramki: border_width + gap + border_width + dodatkowy margines
            inner_padding = border_width + 14 + border_width + 8  # Minimalny margines dla tekstu
        elif config.border_style == BorderStyle.THICK:
            inner_padding = border_width * 2 + 6
        else:
            inner_padding = border_width + 6

        # Rysuj tekst (obsługa wieloliniowego) z marginesem wewnętrznym
        font_size = int(config.font_size * self.DPI / 72)
        font = self._get_font(font_size)
        text = config.text.upper()
        cx, cy = width // 2, height // 2

        # Podziel na linie (filtruj puste)
        lines = [line for line in text.split('\n') if line.strip()]
        if not lines:
            return

        # Oblicz wysokość każdej linii
        line_heights = []
        line_widths = []
        max_width = width - 2 * (padding + inner_padding)

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_widths.append(bbox[2] - bbox[0])
            line_heights.append(max(bbox[3] - bbox[1], font_size))

        total_height = sum(line_heights)
        line_spacing = font_size // 4
        total_height += line_spacing * (len(lines) - 1)

        # Rysuj każdą linię wycentrowaną (z uwzględnieniem marginesu)
        current_y = cy - total_height // 2
        for i, line in enumerate(lines):
            line_width = line_widths[i]
            x = cx - line_width // 2
            draw.text((x, current_y), line, font=font, fill=color)
            current_y += line_heights[i] + line_spacing

    def _draw_circular_stamp(
        self,
        img: Image.Image,
        draw: ImageDraw.ImageDraw,
        config: StampConfig,
        color: Tuple[int, int, int, int],
        offset: int = 0,
    ) -> None:
        """Rysuje okrągłą pieczątkę z tekstem po obwodzie."""
        width, height = img.size
        cx, cy = width // 2, height // 2
        padding = 5 + offset
        border_width = int(config.border_width * self.DPI / 72)

        # Promień zewnętrzny
        radius = min(cx, cy) - padding

        # Rysuj okręgi w zależności od stylu ramki
        if config.border_style == BorderStyle.DOUBLE:
            # Zewnętrzny okrąg
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                outline=color,
                width=border_width,
            )
            # Wewnętrzny okrąg (większy odstęp dla tekstu)
            inner_gap = border_width + 14  # Umiarkowany gap między ramkami
            inner_radius = radius - inner_gap - border_width
            draw.ellipse(
                (cx - inner_radius, cy - inner_radius, cx + inner_radius, cy + inner_radius),
                outline=color,
                width=border_width,
            )
        elif config.border_style == BorderStyle.THICK:
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                outline=color,
                width=border_width * 2,
            )
        elif config.border_style == BorderStyle.THIN:
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                outline=color,
                width=1,
            )
        else:
            draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                outline=color,
                width=border_width,
            )

        # Oblicz margines wewnętrzny dla tekstu
        if config.border_style == BorderStyle.DOUBLE:
            inner_padding = border_width + 14 + border_width + 8  # Minimalny margines dla tekstu
        elif config.border_style == BorderStyle.THICK:
            inner_padding = border_width * 2 + 6
        else:
            inner_padding = border_width + 6

        # Rysuj tekst po obwodzie
        if config.circular_text:
            self._draw_text_on_arc(
                img,
                config.circular_text.upper(),
                (cx, cy),
                radius - inner_padding - 10,
                color,
                int(config.circular_font_size * self.DPI / 72),
            )

        # Rysuj tekst środkowy (obsługa wieloliniowego)
        if config.text:
            font_size = int(config.font_size * self.DPI / 72)
            font = self._get_font(font_size)
            text = config.text.upper()

            # Oblicz bezpieczny promień dla tekstu
            if config.border_style == BorderStyle.DOUBLE:
                inner_gap = border_width + 14
                safe_radius = radius - inner_gap - border_width - 6  # Dodatkowy margines
            elif config.border_style == BorderStyle.THICK:
                safe_radius = radius - (border_width * 2) - 12
            else:
                safe_radius = radius - border_width - 12

            # Maksymalna szerokość = średnica bezpiecznego okręgu * 0.85 (dla marginesu)
            max_text_width = safe_radius * 2 * 0.85

            # Podziel na linie (filtruj puste)
            lines = [line for line in text.split('\n') if line.strip()]
            if lines:
                # Znajdź najszerszą linię
                max_line_width = 0
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                    max_line_width = max(max_line_width, line_width)

                # Zmniejsz font jeśli przekracza max_text_width
                if max_line_width > max_text_width:
                    scale_factor = (max_text_width / max_line_width) * 0.95  # 0.95 dla bezpiecznego marginesu
                    font_size = int(font_size * scale_factor)
                    font_size = max(font_size, int(8 * self.DPI / 72))  # Minimum 8pt
                    font = self._get_font(font_size)

                # Teraz rysuj z dostosowanym fontem
                line_heights = []
                line_widths = []
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_widths.append(bbox[2] - bbox[0])
                    line_heights.append(max(bbox[3] - bbox[1], font_size))

                total_height = sum(line_heights)
                line_spacing = font_size // 4
                total_height += line_spacing * (len(lines) - 1)

                # Rysuj każdą linię wycentrowaną
                current_y = cy - total_height // 2
                for i, line in enumerate(lines):
                    line_width = line_widths[i]
                    x = cx - line_width // 2
                    draw.text((x, current_y), line, font=font, fill=color)
                    current_y += line_heights[i] + line_spacing

    def _draw_oval_stamp(
        self,
        img: Image.Image,
        draw: ImageDraw.ImageDraw,
        config: StampConfig,
        color: Tuple[int, int, int, int],
        offset: int = 0,
    ) -> None:
        """Rysuje owalną pieczątkę."""
        width, height = img.size
        padding = 5 + offset
        border_width = int(config.border_width * self.DPI / 72)

        # Oblicz margines wewnętrzny dla tekstu (większy dla podwójnej ramki)
        if config.border_style == BorderStyle.DOUBLE:
            # Dla podwójnej ramki: border_width + gap + border_width + dodatkowy margines
            inner_padding = border_width + 14 + border_width + 8  # Minimalny margines dla tekstu
        elif config.border_style == BorderStyle.THICK:
            inner_padding = border_width * 2 + 6
        else:
            inner_padding = border_width + 6

        # Elipsa
        rect = (padding, padding, width - padding - 1, height - padding - 1)

        if config.border_style == BorderStyle.DOUBLE:
            draw.ellipse(rect, outline=color, width=border_width)
            inner_gap = border_width + 14  # Umiarkowany gap między ramkami
            inner_rect = (
                padding + inner_gap,
                padding + inner_gap,
                width - padding - 1 - inner_gap,
                height - padding - 1 - inner_gap,
            )
            draw.ellipse(inner_rect, outline=color, width=border_width)
        elif config.border_style == BorderStyle.THICK:
            draw.ellipse(rect, outline=color, width=border_width * 2)
        elif config.border_style == BorderStyle.THIN:
            draw.ellipse(rect, outline=color, width=1)
        else:
            draw.ellipse(rect, outline=color, width=border_width)

        # Tekst środkowy (obsługa wieloliniowego)
        if config.text:
            font_size = int(config.font_size * self.DPI / 72)
            font = self._get_font(font_size)
            text = config.text.upper()
            cx, cy = width // 2, height // 2

            # Oblicz bezpieczne wymiary dla tekstu
            if config.border_style == BorderStyle.DOUBLE:
                inner_gap = border_width + 14
                safe_width = width - 2 * (padding + inner_gap + border_width + 6)
                safe_height = height - 2 * (padding + inner_gap + border_width + 6)
            elif config.border_style == BorderStyle.THICK:
                margin = border_width * 2 + 12
                safe_width = width - 2 * (padding + margin)
                safe_height = height - 2 * (padding + margin)
            else:
                margin = border_width + 12
                safe_width = width - 2 * (padding + margin)
                safe_height = height - 2 * (padding + margin)

            # Maksymalna szerokość tekstu (85% bezpiecznej szerokości dla marginesu)
            max_text_width = safe_width * 0.85

            # Podziel na linie (filtruj puste)
            lines = [line for line in text.split('\n') if line.strip()]
            if lines:
                # Znajdź najszerszą linię
                max_line_width = 0
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                    max_line_width = max(max_line_width, line_width)

                # Zmniejsz font jeśli przekracza max_text_width
                if max_line_width > max_text_width:
                    scale_factor = (max_text_width / max_line_width) * 0.95
                    font_size = int(font_size * scale_factor)
                    font_size = max(font_size, int(8 * self.DPI / 72))  # Minimum 8pt
                    font = self._get_font(font_size)

                # Oblicz wysokość każdej linii z dostosowanym fontem
                line_heights = []
                line_widths = []
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_widths.append(bbox[2] - bbox[0])
                    line_heights.append(max(bbox[3] - bbox[1], font_size))

                total_height = sum(line_heights)
                line_spacing = font_size // 4
                total_height += line_spacing * (len(lines) - 1)

                # Rysuj każdą linię wycentrowaną
                current_y = cy - total_height // 2
                for i, line in enumerate(lines):
                    line_width = line_widths[i]
                    x = cx - line_width // 2
                    draw.text((x, current_y), line, font=font, fill=color)
                    current_y += line_heights[i] + line_spacing

    def _draw_text_on_arc(
        self,
        img: Image.Image,
        text: str,
        center: Tuple[int, int],
        radius: int,
        color: Tuple[int, int, int, int],
        font_size: int,
    ) -> None:
        """
        Rysuje tekst po łuku (dla okrągłych pieczątek).

        Algorytm:
        1. Dla każdego znaku oblicz pozycję na okręgu
        2. Obróć znak zgodnie z tangentą
        3. Wklej na obraz
        """
        font = self._get_font(font_size)
        cx, cy = center

        # Oblicz szerokości znaków
        char_widths = []
        for char in text:
            bbox = font.getbbox(char)
            char_widths.append(bbox[2] - bbox[0])

        total_width = sum(char_widths) + len(text) * 2  # spacing
        # Kąt na piksel (w stopniach)
        angle_per_pixel = 360 / (2 * math.pi * radius)

        # Oblicz całkowity kąt zajmowany przez tekst
        total_angle = total_width * angle_per_pixel

        # Startujemy od góry (90 stopni), tekst po lewej stronie łuku
        start_angle = 90 + total_angle / 2

        current_angle = start_angle

        for i, char in enumerate(text):
            # Pozycja na okręgu
            angle_rad = math.radians(current_angle)
            x = cx + radius * math.cos(angle_rad)
            y = cy - radius * math.sin(angle_rad)

            # Utwórz obrazek znaku
            char_size = font_size * 2
            char_img = Image.new("RGBA", (char_size, char_size), (0, 0, 0, 0))
            char_draw = ImageDraw.Draw(char_img)

            # Rysuj znak na środku
            char_draw.text((char_size // 2, char_size // 2), char, font=font, fill=color, anchor="mm")

            # Obróć znak (tangenta do okręgu) - znak powinien być prostopadły do promienia
            rotation_angle = current_angle - 90
            char_img = char_img.rotate(rotation_angle, expand=False, resample=Image.BICUBIC)

            # Wklej na główny obraz
            paste_x = int(x - char_size // 2)
            paste_y = int(y - char_size // 2)

            # Użyj maski alpha do wklejania
            img.paste(char_img, (paste_x, paste_y), char_img)

            # Przejdź do następnego znaku
            char_angle = (char_widths[i] + 2) * angle_per_pixel
            current_angle -= char_angle

    def _draw_border(
        self,
        draw: ImageDraw.ImageDraw,
        rect: Tuple[int, int, int, int],
        style: BorderStyle,
        color: Tuple[int, int, int, int],
        width: int,
    ) -> None:
        """Rysuje ramkę w wybranym stylu."""
        x0, y0, x1, y1 = rect

        if style == BorderStyle.SOLID:
            draw.rectangle(rect, outline=color, width=width)

        elif style == BorderStyle.DOUBLE:
            # Zewnętrzna ramka
            draw.rectangle(rect, outline=color, width=width)
            # Wewnętrzna ramka (większy odstęp dla tekstu)
            gap = width + 24  # Zwiększony gap dla większej przestrzeni na tekst
            inner = (x0 + gap, y0 + gap, x1 - gap, y1 - gap)
            draw.rectangle(inner, outline=color, width=width)

        elif style == BorderStyle.DASHED:
            self._draw_dashed_rect(draw, rect, color, width)

        elif style == BorderStyle.THICK:
            draw.rectangle(rect, outline=color, width=width * 2)

        elif style == BorderStyle.THIN:
            draw.rectangle(rect, outline=color, width=1)

    def _draw_dashed_rect(
        self,
        draw: ImageDraw.ImageDraw,
        rect: Tuple[int, int, int, int],
        color: Tuple[int, int, int, int],
        width: int,
        dash_length: int = 10,
        gap_length: int = 5,
    ) -> None:
        """Rysuje przerywaną ramkę."""
        x0, y0, x1, y1 = rect

        def draw_dashed_line(start: Tuple[int, int], end: Tuple[int, int]) -> None:
            x_s, y_s = start
            x_e, y_e = end
            length = math.sqrt((x_e - x_s) ** 2 + (y_e - y_s) ** 2)
            dash_count = int(length / (dash_length + gap_length))

            for i in range(dash_count + 1):
                t1 = i * (dash_length + gap_length) / length
                t2 = min((i * (dash_length + gap_length) + dash_length) / length, 1.0)

                dx1 = int(x_s + (x_e - x_s) * t1)
                dy1 = int(y_s + (y_e - y_s) * t1)
                dx2 = int(x_s + (x_e - x_s) * t2)
                dy2 = int(y_s + (y_e - y_s) * t2)

                draw.line([(dx1, dy1), (dx2, dy2)], fill=color, width=width)

        # Cztery boki
        draw_dashed_line((x0, y0), (x1, y0))  # Góra
        draw_dashed_line((x1, y0), (x1, y1))  # Prawo
        draw_dashed_line((x1, y1), (x0, y1))  # Dół
        draw_dashed_line((x0, y1), (x0, y0))  # Lewo

    def _apply_wear_effect(self, img: Image.Image, level: WearLevel) -> Image.Image:
        """
        Aplikuje efekt zużycia/starości.

        Techniki:
        - LIGHT: Subtelny noise, lekkie blur na krawędziach
        - MEDIUM: Więcej noise, nierówne krawędzie
        - HEAVY: Duże ubytki, mocno zniszczona
        """
        width, height = img.size

        # Pobierz kanał alpha
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        r, g, b, a = img.split()
        alpha_data = list(a.getdata())

        # Parametry zależne od poziomu
        params = {
            WearLevel.LIGHT: {"noise_prob": 0.05, "blob_count": 3, "blob_size": (2, 5)},
            WearLevel.MEDIUM: {"noise_prob": 0.12, "blob_count": 10, "blob_size": (3, 8)},
            WearLevel.HEAVY: {"noise_prob": 0.25, "blob_count": 25, "blob_size": (4, 12)},
        }
        p = params.get(level, params[WearLevel.LIGHT])

        # 1. Losowy noise
        for i in range(len(alpha_data)):
            if alpha_data[i] > 0 and random.random() < p["noise_prob"]:
                alpha_data[i] = 0

        # 2. Losowe "bloby" (większe ubytki)
        for _ in range(p["blob_count"]):
            cx = random.randint(0, width - 1)
            cy = random.randint(0, height - 1)
            blob_radius = random.randint(*p["blob_size"])

            for dx in range(-blob_radius, blob_radius + 1):
                for dy in range(-blob_radius, blob_radius + 1):
                    if dx * dx + dy * dy <= blob_radius * blob_radius:
                        px, py = cx + dx, cy + dy
                        if 0 <= px < width and 0 <= py < height:
                            idx = py * width + px
                            if idx < len(alpha_data):
                                alpha_data[idx] = 0

        # Utwórz nowy alpha channel
        new_alpha = Image.new("L", (width, height))
        new_alpha.putdata(alpha_data)

        # 3. Lekki blur na krawędziach
        new_alpha = new_alpha.filter(ImageFilter.GaussianBlur(0.5))

        # Złóż obraz
        img.putalpha(new_alpha)
        return img

    def _apply_opacity(self, img: Image.Image, opacity: float) -> Image.Image:
        """Redukuje opacity całego obrazu."""
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        r, g, b, a = img.split()
        a = a.point(lambda x: int(x * opacity))

        return Image.merge("RGBA", (r, g, b, a))

    def _apply_vintage_effect(self, img: Image.Image) -> Image.Image:
        """
        Aplikuje efekt starodruku (letterpress/vintage).

        Techniki:
        - Nierówne krawędzie liter (tusz rozlewa się)
        - Nierównomierna gęstość tuszu
        - Ziarnista tekstura
        - Efekt "bleeding" (rozlewanie)
        """
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        width, height = img.size
        r, g, b, a = img.split()

        # 1. Efekt bleeding - lekkie rozmycie + próg dla nierównych krawędzi
        # Rozmyj alpha channel
        blurred_a = a.filter(ImageFilter.GaussianBlur(1.2))

        # Dodaj ziarnistość do rozmazanego alpha
        blurred_data = list(blurred_a.getdata())
        for i in range(len(blurred_data)):
            if blurred_data[i] > 20:  # Tylko tam gdzie jest coś widoczne
                # Losowa wariacja intensywności (symuluje nierówny tusz)
                variation = random.randint(-40, 20)
                new_val = max(0, min(255, blurred_data[i] + variation))
                blurred_data[i] = new_val

        blurred_a.putdata(blurred_data)

        # 2. Nierównomierna gęstość tuszu - modyfikuj kanały kolorów
        r_data = list(r.getdata())
        g_data = list(g.getdata())
        b_data = list(b.getdata())
        a_data = list(a.getdata())

        for i in range(len(r_data)):
            if a_data[i] > 50:  # Tylko widoczne piksele
                # Losowa wariacja koloru (symuluje nierówny nanos tuszu)
                ink_variation = random.randint(-25, 15)
                r_data[i] = max(0, min(255, r_data[i] + ink_variation))
                g_data[i] = max(0, min(255, g_data[i] + ink_variation))
                b_data[i] = max(0, min(255, b_data[i] + ink_variation))

        r.putdata(r_data)
        g.putdata(g_data)
        b.putdata(b_data)

        # 3. Połącz bleeding z oryginalnym alpha (mieszanka)
        original_a_data = list(a.getdata())
        blurred_a_data = list(blurred_a.getdata())
        final_a_data = []

        for i in range(len(original_a_data)):
            orig = original_a_data[i]
            blur = blurred_a_data[i]

            if orig > 0:
                # Wewnątrz - użyj oryginalnego z lekką wariancją
                val = orig + random.randint(-20, 10)
                final_a_data.append(max(0, min(255, val)))
            elif blur > 30:
                # Bleeding na krawędziach - subtelne rozlewanie
                bleeding_strength = min(blur // 3, 60)
                if random.random() < 0.4:  # Nie wszędzie
                    final_a_data.append(bleeding_strength)
                else:
                    final_a_data.append(0)
            else:
                final_a_data.append(0)

        final_a = Image.new("L", (width, height))
        final_a.putdata(final_a_data)

        # 4. Dodaj teksturę ziarnistości
        for _ in range(width * height // 50):  # Losowe punkty
            px = random.randint(0, width - 1)
            py = random.randint(0, height - 1)
            idx = py * width + px

            if idx < len(final_a_data) and final_a_data[idx] > 0:
                # Losowe przyciemnienie/rozjaśnienie
                if random.random() < 0.5:
                    final_a_data[idx] = max(0, final_a_data[idx] - random.randint(20, 50))

        final_a.putdata(final_a_data)

        # Złóż obraz
        return Image.merge("RGBA", (r, g, b, final_a))

    def _apply_double_strike(self, img: Image.Image) -> Image.Image:
        """
        Aplikuje efekt podwójnego odbicia.

        Symuluje sytuację gdy pieczątka została przyłożona dwa razy
        z lekkim przesunięciem - częste w starych dokumentach.
        """
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        width, height = img.size

        # Losowe przesunięcie drugiego odbicia (2-5 pikseli)
        offset_x = random.randint(2, 5)
        offset_y = random.randint(1, 3)

        # Utwórz drugie odbicie z mniejszą opacity
        second_strike = img.copy()

        # Zmniejsz opacity drugiego odbicia do 40-60%
        r, g, b, a = second_strike.split()
        ghost_opacity = random.uniform(0.4, 0.6)
        a = a.point(lambda x: int(x * ghost_opacity))
        second_strike = Image.merge("RGBA", (r, g, b, a))

        # Utwórz nowy obraz z miejscem na przesunięcie
        result = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        # Najpierw wklej drugie (słabsze) odbicie z przesunięciem
        result.paste(second_strike, (offset_x, offset_y), second_strike)

        # Potem wklej pierwsze (mocniejsze) odbicie
        result = Image.alpha_composite(result, img)

        return result

    def _apply_ink_splatter(
        self, img: Image.Image, color: Tuple[int, int, int, int]
    ) -> Image.Image:
        """
        Aplikuje efekt rozbryzgów tuszu.

        Symuluje mokrą pieczątkę z kropelkami tuszu wokół.
        """
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        width, height = img.size
        draw = ImageDraw.Draw(img)

        # Znajdź granice pieczątki (gdzie jest coś narysowane)
        alpha = img.split()[3]
        bbox = alpha.getbbox()
        if not bbox:
            return img

        left, top, right, bottom = bbox

        # Generuj rozbryzgi wokół granic
        num_splatters = random.randint(8, 20)

        for _ in range(num_splatters):
            # Losowa pozycja blisko krawędzi pieczątki
            side = random.choice(["top", "bottom", "left", "right"])

            if side == "top":
                x = random.randint(left, right)
                y = random.randint(max(0, top - 15), top)
            elif side == "bottom":
                x = random.randint(left, right)
                y = random.randint(bottom, min(height - 1, bottom + 15))
            elif side == "left":
                x = random.randint(max(0, left - 15), left)
                y = random.randint(top, bottom)
            else:  # right
                x = random.randint(right, min(width - 1, right + 15))
                y = random.randint(top, bottom)

            # Losowy rozmiar kropelki (1-4 piksele)
            size = random.randint(1, 4)

            # Losowa opacity dla kropelki (50-100%)
            splatter_alpha = int(255 * random.uniform(0.5, 1.0))
            splatter_color = (color[0], color[1], color[2], splatter_alpha)

            # Rysuj kropelkę (koło lub elipsa)
            if size == 1:
                draw.point((x, y), fill=splatter_color)
            else:
                draw.ellipse(
                    (x - size, y - size, x + size, y + size),
                    fill=splatter_color,
                )

        # Dodaj kilka mniejszych kropelek dalej od pieczątki
        for _ in range(random.randint(3, 8)):
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)

            # Tylko jeśli jest wystarczająco daleko od pieczątki
            if x < left - 5 or x > right + 5 or y < top - 5 or y > bottom + 5:
                size = random.randint(1, 2)
                splatter_alpha = int(255 * random.uniform(0.3, 0.7))
                splatter_color = (color[0], color[1], color[2], splatter_alpha)

                if size == 1:
                    draw.point((x, y), fill=splatter_color)
                else:
                    draw.ellipse(
                        (x - size, y - size, x + size, y + size),
                        fill=splatter_color,
                    )

        return img

    def _generate_rectangular_svg(self, config: StampConfig) -> str:
        """Generuje SVG dla prostokątnej pieczątki."""
        w, h = config.width, config.height
        color_hex = "#{:02x}{:02x}{:02x}".format(
            int(config.color[0] * 255),
            int(config.color[1] * 255),
            int(config.color[2] * 255),
        )
        bw = config.border_width

        # Styl ramki
        stroke_dasharray = ""
        if config.border_style == BorderStyle.DASHED:
            stroke_dasharray = 'stroke-dasharray="10,5"'

        actual_width = bw * 2 if config.border_style == BorderStyle.THICK else bw
        if config.border_style == BorderStyle.THIN:
            actual_width = 1

        # Podstawowa ramka
        rect_svg = f'''<rect x="{bw}" y="{bw}" width="{w - 2*bw}" height="{h - 2*bw}"
            fill="none" stroke="{color_hex}" stroke-width="{actual_width}"
            {stroke_dasharray} opacity="{config.opacity}"/>'''

        # Dodatkowa ramka dla DOUBLE
        double_rect = ""
        if config.border_style == BorderStyle.DOUBLE:
            gap = bw + 4
            double_rect = f'''<rect x="{gap + bw}" y="{gap + bw}"
                width="{w - 2*(gap + bw)}" height="{h - 2*(gap + bw)}"
                fill="none" stroke="{color_hex}" stroke-width="{bw}"
                opacity="{config.opacity}"/>'''

        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
    {rect_svg}
    {double_rect}
    <text x="{w/2}" y="{h/2 + config.font_size/3}"
        text-anchor="middle"
        font-family="Arial, sans-serif"
        font-size="{config.font_size}"
        font-weight="bold"
        fill="{color_hex}"
        opacity="{config.opacity}">{config.text.upper()}</text>
</svg>'''

    def _generate_circular_svg(self, config: StampConfig) -> str:
        """Generuje SVG dla okrągłej pieczątki z textPath."""
        size = max(config.width, config.height)
        cx, cy = size / 2, size / 2
        r = min(cx, cy) - 5
        text_r = r - 15

        color_hex = "#{:02x}{:02x}{:02x}".format(
            int(config.color[0] * 255),
            int(config.color[1] * 255),
            int(config.color[2] * 255),
        )
        bw = config.border_width

        # Styl okręgu
        circles = f'''<circle cx="{cx}" cy="{cy}" r="{r}"
            fill="none" stroke="{color_hex}" stroke-width="{bw}"
            opacity="{config.opacity}"/>'''

        if config.border_style == BorderStyle.DOUBLE:
            inner_r = r - bw - 4
            circles += f'''
    <circle cx="{cx}" cy="{cy}" r="{inner_r}"
            fill="none" stroke="{color_hex}" stroke-width="{bw}"
            opacity="{config.opacity}"/>'''

        # Tekst po obwodzie
        circular_text_svg = ""
        if config.circular_text:
            circular_text_svg = f'''
    <defs>
        <path id="circlePath"
            d="M {cx},{cy - text_r} A {text_r},{text_r} 0 1,1 {cx - 0.01},{cy - text_r}"/>
    </defs>
    <text fill="{color_hex}"
        font-size="{config.circular_font_size}"
        font-family="Arial, sans-serif"
        font-weight="bold"
        opacity="{config.opacity}">
        <textPath href="#circlePath" startOffset="50%" text-anchor="middle">
            {config.circular_text.upper()}
        </textPath>
    </text>'''

        # Tekst środkowy
        center_text = ""
        if config.text:
            center_text = f'''
    <text x="{cx}" y="{cy + config.font_size/3}"
        text-anchor="middle"
        font-family="Arial, sans-serif"
        font-size="{config.font_size}"
        font-weight="bold"
        fill="{color_hex}"
        opacity="{config.opacity}">{config.text.upper()}</text>'''

        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}">
    {circles}
    {circular_text_svg}
    {center_text}
</svg>'''

    def _generate_oval_svg(self, config: StampConfig) -> str:
        """Generuje SVG dla owalnej pieczątki."""
        w, h = config.width, config.height
        cx, cy = w / 2, h / 2
        rx, ry = (w - 10) / 2, (h - 10) / 2

        color_hex = "#{:02x}{:02x}{:02x}".format(
            int(config.color[0] * 255),
            int(config.color[1] * 255),
            int(config.color[2] * 255),
        )
        bw = config.border_width

        ellipse = f'''<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"
            fill="none" stroke="{color_hex}" stroke-width="{bw}"
            opacity="{config.opacity}"/>'''

        if config.border_style == BorderStyle.DOUBLE:
            inner_rx, inner_ry = rx - bw - 4, ry - bw - 4
            ellipse += f'''
    <ellipse cx="{cx}" cy="{cy}" rx="{inner_rx}" ry="{inner_ry}"
            fill="none" stroke="{color_hex}" stroke-width="{bw}"
            opacity="{config.opacity}"/>'''

        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
    {ellipse}
    <text x="{cx}" y="{cy + config.font_size/3}"
        text-anchor="middle"
        font-family="Arial, sans-serif"
        font-size="{config.font_size}"
        font-weight="bold"
        fill="{color_hex}"
        opacity="{config.opacity}">{config.text.upper()}</text>
</svg>'''
