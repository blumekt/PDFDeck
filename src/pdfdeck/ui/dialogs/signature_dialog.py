"""
SignatureDialog - Dialog podpisów cyfrowych.

Funkcje:
- Wybór certyfikatu
- Konfiguracja podpisu
- Podgląd informacji o certyfikacie
- Tworzenie self-signed certyfikatów
"""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QGroupBox, QSpinBox,
    QCheckBox, QFileDialog, QMessageBox, QTabWidget,
    QWidget, QFormLayout, QTextEdit
)
from PyQt6.QtCore import Qt

from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.core.signature_engine import SignatureEngine, SignatureConfig


class SignatureDialog(QDialog):
    """
    Dialog do podpisywania PDF certyfikatem cyfrowym.

    Zakładki:
    - Podpisz: wybór certyfikatu i konfiguracja
    - Weryfikuj: weryfikacja istniejących podpisów
    - Utwórz certyfikat: generowanie self-signed
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._config: Optional[SignatureConfig] = None
        self._engine = SignatureEngine()

        self.setWindowTitle("Podpisy cyfrowe")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setStyleSheet(self._dialog_style())

        self._setup_ui()

    def _dialog_style(self) -> str:
        """Zwraca styl dialogu."""
        return """
            QDialog {
                background-color: #16213e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #ffffff;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit, QSpinBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
            }
            QLineEdit:focus, QSpinBox:focus {
                border-color: #e0a800;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #2d3a50;
                border-radius: 4px;
                background-color: #0f1629;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #e0a800;
                border-radius: 4px;
                background-color: #e0a800;
            }
            QTabWidget::pane {
                border: 1px solid #2d3a50;
                border-radius: 4px;
                background-color: #16213e;
            }
            QTabBar::tab {
                background-color: #1a1a2e;
                color: #8892a0;
                padding: 10px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #16213e;
                color: #e0a800;
            }
            QTextEdit {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
                font-family: 'Consolas', monospace;
            }
        """

    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # Zakładki
        tabs = QTabWidget()

        # === Zakładka: Podpisz ===
        sign_tab = QWidget()
        sign_layout = QVBoxLayout(sign_tab)

        # Wybór certyfikatu
        cert_group = QGroupBox("Certyfikat")
        cert_layout = QVBoxLayout(cert_group)

        cert_row = QHBoxLayout()
        self._cert_path_input = QLineEdit()
        self._cert_path_input.setPlaceholderText("Wybierz plik .p12 lub .pfx")
        self._cert_path_input.setReadOnly(True)
        cert_row.addWidget(self._cert_path_input)

        browse_btn = StyledButton("Przeglądaj", "secondary")
        browse_btn.clicked.connect(self._browse_cert)
        cert_row.addWidget(browse_btn)

        cert_layout.addLayout(cert_row)

        # Hasło
        pass_row = QHBoxLayout()
        pass_label = QLabel("Hasło:")
        pass_label.setFixedWidth(80)
        pass_row.addWidget(pass_label)

        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("Hasło do certyfikatu")
        pass_row.addWidget(self._password_input)

        cert_layout.addLayout(pass_row)

        # Info o certyfikacie
        self._cert_info_btn = StyledButton("Pokaż info", "secondary")
        self._cert_info_btn.clicked.connect(self._show_cert_info)
        cert_layout.addWidget(self._cert_info_btn)

        sign_layout.addWidget(cert_group)

        # Opcje podpisu
        options_group = QGroupBox("Opcje podpisu")
        options_layout = QFormLayout(options_group)

        self._reason_input = QLineEdit()
        self._reason_input.setText("Dokument podpisany cyfrowo")
        options_layout.addRow("Powód:", self._reason_input)

        self._location_input = QLineEdit()
        self._location_input.setText("Poland")
        options_layout.addRow("Miejsce:", self._location_input)

        self._contact_input = QLineEdit()
        options_layout.addRow("Kontakt:", self._contact_input)

        sign_layout.addWidget(options_group)

        # Pozycja wizualizacji
        position_group = QGroupBox("Pozycja wizualizacji")
        position_layout = QHBoxLayout(position_group)

        position_layout.addWidget(QLabel("Strona:"))
        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setValue(1)
        position_layout.addWidget(self._page_spin)

        position_layout.addWidget(QLabel("X:"))
        self._x_spin = QSpinBox()
        self._x_spin.setMaximum(1000)
        self._x_spin.setValue(50)
        position_layout.addWidget(self._x_spin)

        position_layout.addWidget(QLabel("Y:"))
        self._y_spin = QSpinBox()
        self._y_spin.setMaximum(1000)
        self._y_spin.setValue(50)
        position_layout.addWidget(self._y_spin)

        position_layout.addStretch()

        sign_layout.addWidget(position_group)

        # Opcje wizualizacji
        self._show_date_check = QCheckBox("Pokaż datę")
        self._show_date_check.setChecked(True)
        sign_layout.addWidget(self._show_date_check)

        self._show_reason_check = QCheckBox("Pokaż powód")
        self._show_reason_check.setChecked(True)
        sign_layout.addWidget(self._show_reason_check)

        sign_layout.addStretch()

        tabs.addTab(sign_tab, "Podpisz")

        # === Zakładka: Utwórz certyfikat ===
        create_tab = QWidget()
        create_layout = QVBoxLayout(create_tab)

        create_group = QGroupBox("Nowy certyfikat self-signed")
        create_form = QFormLayout(create_group)

        self._cn_input = QLineEdit()
        self._cn_input.setPlaceholderText("np. Jan Kowalski")
        create_form.addRow("Nazwa (CN):", self._cn_input)

        self._org_input = QLineEdit()
        self._org_input.setPlaceholderText("np. Firma ABC")
        create_form.addRow("Organizacja:", self._org_input)

        self._cert_password_input = QLineEdit()
        self._cert_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        create_form.addRow("Hasło:", self._cert_password_input)

        self._validity_spin = QSpinBox()
        self._validity_spin.setMinimum(1)
        self._validity_spin.setMaximum(3650)
        self._validity_spin.setValue(365)
        self._validity_spin.setSuffix(" dni")
        create_form.addRow("Ważność:", self._validity_spin)

        create_layout.addWidget(create_group)

        create_btn = StyledButton("Utwórz certyfikat", "primary")
        create_btn.clicked.connect(self._create_certificate)
        create_layout.addWidget(create_btn)

        # Status
        status_label = QLabel(
            "Uwaga: Certyfikaty self-signed nie są uznawane przez "
            "oficjalne instytucje. Służą do celów wewnętrznych."
        )
        status_label.setStyleSheet("color: #8892a0; font-size: 12px;")
        status_label.setWordWrap(True)
        create_layout.addWidget(status_label)

        # Info o wsparciu
        support_info = QLabel()
        if self._engine.has_certificate_support:
            support_info.setText("✅ Wsparcie certyfikatów: dostępne")
            support_info.setStyleSheet("color: #27ae60;")
        else:
            support_info.setText(
                "⚠️ Wsparcie certyfikatów: brak\n"
                "Zainstaluj: pip install cryptography"
            )
            support_info.setStyleSheet("color: #f39c12;")
        create_layout.addWidget(support_info)

        create_layout.addStretch()

        tabs.addTab(create_tab, "Utwórz certyfikat")

        layout.addWidget(tabs)

        # === Przyciski ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = StyledButton("Anuluj", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        sign_btn = StyledButton("Podpisz", "primary")
        sign_btn.clicked.connect(self._on_sign)
        buttons_layout.addWidget(sign_btn)

        layout.addLayout(buttons_layout)

    def _browse_cert(self) -> None:
        """Przeglądaj w poszukiwaniu certyfikatu."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz certyfikat",
            "",
            "Certyfikaty (*.p12 *.pfx);;Wszystkie pliki (*.*)"
        )

        if filepath:
            self._cert_path_input.setText(filepath)

    def _show_cert_info(self) -> None:
        """Pokazuje informacje o certyfikacie."""
        cert_path = self._cert_path_input.text()
        password = self._password_input.text()

        if not cert_path:
            QMessageBox.warning(self, "Błąd", "Wybierz plik certyfikatu")
            return

        if not password:
            QMessageBox.warning(self, "Błąd", "Podaj hasło do certyfikatu")
            return

        info = self._engine.get_certificate_info(Path(cert_path), password)

        if not info:
            QMessageBox.critical(
                self,
                "Błąd",
                "Nie można odczytać certyfikatu.\n"
                "Sprawdź hasło i format pliku."
            )
            return

        # Formatuj informacje
        lines = [
            "<b>Podmiot (Subject):</b>",
        ]
        for key, value in info.get("subject", {}).items():
            lines.append(f"  {key}: {value}")

        lines.append("<br><b>Wydawca (Issuer):</b>")
        for key, value in info.get("issuer", {}).items():
            lines.append(f"  {key}: {value}")

        lines.extend([
            f"<br><b>Ważny od:</b> {info.get('valid_from', 'N/A')}",
            f"<b>Ważny do:</b> {info.get('valid_to', 'N/A')}",
            f"<b>Numer seryjny:</b> {info.get('serial_number', 'N/A')}",
        ])

        QMessageBox.information(
            self,
            "Informacje o certyfikacie",
            "<br>".join(lines)
        )

    def _create_certificate(self) -> None:
        """Tworzy nowy certyfikat self-signed."""
        cn = self._cn_input.text().strip()
        org = self._org_input.text().strip()
        password = self._cert_password_input.text()
        validity = self._validity_spin.value()

        if not cn:
            QMessageBox.warning(self, "Błąd", "Podaj nazwę (CN)")
            return

        if not org:
            QMessageBox.warning(self, "Błąd", "Podaj organizację")
            return

        if not password:
            QMessageBox.warning(self, "Błąd", "Podaj hasło")
            return

        # Wybierz gdzie zapisać
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz certyfikat",
            f"{cn.replace(' ', '_')}.p12",
            "Certyfikaty (*.p12)"
        )

        if not filepath:
            return

        success = self._engine.create_self_signed_cert(
            cn, org, Path(filepath), password, validity
        )

        if success:
            QMessageBox.information(
                self,
                "Sukces",
                f"Certyfikat utworzony:\n{filepath}\n\n"
                "Możesz go teraz użyć do podpisywania."
            )
            # Ustaw ścieżkę w zakładce podpisywania
            self._cert_path_input.setText(filepath)
            self._password_input.setText(password)
        else:
            QMessageBox.critical(
                self,
                "Błąd",
                "Nie można utworzyć certyfikatu.\n"
                "Upewnij się, że masz zainstalowaną bibliotekę cryptography."
            )

    def _on_sign(self) -> None:
        """Zatwierdza konfigurację podpisu."""
        cert_path = self._cert_path_input.text()
        password = self._password_input.text()

        if not cert_path:
            QMessageBox.warning(self, "Błąd", "Wybierz plik certyfikatu")
            return

        if not password:
            QMessageBox.warning(self, "Błąd", "Podaj hasło do certyfikatu")
            return

        self._config = SignatureConfig(
            cert_path=Path(cert_path),
            password=password,
            reason=self._reason_input.text(),
            location=self._location_input.text(),
            contact=self._contact_input.text(),
            page=self._page_spin.value() - 1,
            x=self._x_spin.value(),
            y=self._y_spin.value(),
            show_date=self._show_date_check.isChecked(),
            show_reason=self._show_reason_check.isChecked(),
        )

        self.accept()

    def get_config(self) -> Optional[SignatureConfig]:
        """Zwraca konfigurację podpisu."""
        return self._config

    @staticmethod
    def get_signature_config(parent=None) -> Optional[SignatureConfig]:
        """
        Statyczna metoda do uzyskania konfiguracji.

        Args:
            parent: Widget rodzic

        Returns:
            SignatureConfig lub None jeśli anulowano
        """
        dialog = SignatureDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_config()
        return None
