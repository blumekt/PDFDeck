"""
SecurityPage - Strona bezpieczeństwa dokumentu.

Funkcje:
- Metadata Scrubber (usuwanie metadanych)
- Flatten (spłaszczanie formularzy i adnotacji)
- Podgląd metadanych
"""

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QFrame, QSplitter, QSizePolicy,
    QLineEdit, QComboBox, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt

from pdfdeck.ui.pages.base_page import BasePage
from pdfdeck.ui.widgets.styled_button import StyledButton
from pdfdeck.core.signature_engine import SignatureEngine, SignatureStatus

if TYPE_CHECKING:
    from pdfdeck.core.pdf_manager import PDFManager


class SecurityPage(BasePage):
    """
    Strona bezpieczeństwa dokumentu.

    Układ:
    +------------------------------------------+
    |  Tytuł: Bezpieczeństwo                   |
    +------------------------------------------+
    |  +------------------+  +---------------+ |
    |  | Metadane         |  | Akcje         | |
    |  | Autor: ...       |  | [Usuń meta]   | |
    |  | Data: ...        |  | [Spłaszcz]    | |
    |  | ...              |  |               | |
    |  +------------------+  +---------------+ |
    +------------------------------------------+
    """

    def __init__(self, pdf_manager: "PDFManager", parent=None):
        super().__init__("Bezpieczeństwo", parent)

        self._pdf_manager = pdf_manager
        self._setup_security_ui()

    def _setup_security_ui(self) -> None:
        """Tworzy interfejs bezpieczeństwa."""
        # Scroll area dla całej zawartości
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(self._scroll_style())

        # Kontener wewnętrzny
        content = QWidget()
        content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 10, 0)
        content_layout.setSpacing(15)

        # Splitter dla dwóch kolumn
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2d3a50;
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color: #e0a800;
            }
        """)

        # === Lewa strona: Metadane ===
        metadata_group = QGroupBox("Metadane dokumentu")
        metadata_group.setMinimumWidth(250)
        metadata_group.setStyleSheet(self._group_style())
        metadata_layout = QVBoxLayout(metadata_group)

        # Tabela metadanych
        self._metadata_table = QTableWidget()
        self._metadata_table.setColumnCount(2)
        self._metadata_table.setHorizontalHeaderLabels(["Pole", "Wartość"])
        self._metadata_table.horizontalHeader().setStretchLastSection(True)
        self._metadata_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._metadata_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._metadata_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._metadata_table.setStyleSheet(self._table_style())
        metadata_layout.addWidget(self._metadata_table)

        # Przycisk odśwież
        refresh_btn = StyledButton("Odśwież metadane", "secondary")
        refresh_btn.clicked.connect(self._refresh_metadata)
        metadata_layout.addWidget(refresh_btn)

        splitter.addWidget(metadata_group)

        # === Prawa strona: Akcje ===
        actions_widget = QWidget()
        actions_widget.setMinimumWidth(250)
        actions_layout = QVBoxLayout(actions_widget)
        actions_layout.setContentsMargins(10, 0, 0, 0)
        actions_layout.setSpacing(10)

        # --- Metadata Scrubber ---
        scrub_group = QGroupBox("Usuwanie metadanych")
        scrub_group.setStyleSheet(self._group_style())
        scrub_layout = QVBoxLayout(scrub_group)

        scrub_desc = QLabel(
            "Usuwa wszystkie metadane:\n"
            "• Autor, Tytuł\n"
            "• Daty utworzenia/modyfikacji\n"
            "• Producent, Słowa kluczowe\n"
            "• XMP metadata"
        )
        scrub_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        scrub_desc.setWordWrap(True)
        scrub_layout.addWidget(scrub_desc)

        self._scrub_btn = StyledButton("Usuń metadane", "danger")
        self._scrub_btn.clicked.connect(self._on_scrub_metadata)
        scrub_layout.addWidget(self._scrub_btn)

        actions_layout.addWidget(scrub_group)

        # --- Flatten ---
        flatten_group = QGroupBox("Spłaszczanie dokumentu")
        flatten_group.setStyleSheet(self._group_style())
        flatten_layout = QVBoxLayout(flatten_group)

        flatten_desc = QLabel(
            "Spłaszcza interaktywne elementy:\n"
            "• Formularze PDF\n"
            "• Adnotacje i komentarze\n\n"
            "Elementy staną się nieedytowalne."
        )
        flatten_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        flatten_desc.setWordWrap(True)
        flatten_layout.addWidget(flatten_desc)

        self._flatten_btn = StyledButton("Spłaszcz dokument", "warning")
        self._flatten_btn.clicked.connect(self._on_flatten)
        flatten_layout.addWidget(self._flatten_btn)

        actions_layout.addWidget(flatten_group)

        # --- Ochrona hasłem ---
        password_group = QGroupBox("Ochrona hasłem")
        password_group.setStyleSheet(self._group_style())
        password_layout = QVBoxLayout(password_group)

        password_desc = QLabel(
            "Zaszyfruj dokument hasłem:\n"
            "• Szyfrowanie AES-256\n"
            "• Kontrola uprawnień\n"
            "• Hasło użytkownika i właściciela"
        )
        password_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        password_desc.setWordWrap(True)
        password_layout.addWidget(password_desc)

        self._encrypt_btn = StyledButton("Zaszyfruj dokument", "primary")
        self._encrypt_btn.clicked.connect(self._on_encrypt_document)
        password_layout.addWidget(self._encrypt_btn)

        actions_layout.addWidget(password_group)

        # --- Podpisy cyfrowe ---
        signature_group = QGroupBox("Podpisy cyfrowe")
        signature_group.setStyleSheet(self._group_style())
        signature_layout = QVBoxLayout(signature_group)

        sig_desc = QLabel(
            "Podpisuj dokumenty certyfikatem X.509:\n"
            "• Podpisy z plikami .p12/.pfx\n"
            "• Wizualizacja podpisu\n"
            "• Weryfikacja istniejących podpisów"
        )
        sig_desc.setStyleSheet("color: #8892a0; font-size: 13px;")
        sig_desc.setWordWrap(True)
        signature_layout.addWidget(sig_desc)

        # Status podpisów
        self._sig_status_label = QLabel("Status: brak załadowanego dokumentu")
        self._sig_status_label.setStyleSheet("color: #8892a0; font-size: 12px;")
        signature_layout.addWidget(self._sig_status_label)

        # Przyciski
        sig_buttons = QHBoxLayout()

        self._verify_sig_btn = StyledButton("Weryfikuj", "secondary")
        self._verify_sig_btn.clicked.connect(self._on_verify_signatures)
        sig_buttons.addWidget(self._verify_sig_btn)

        self._sign_btn = StyledButton("Podpisz", "primary")
        self._sign_btn.clicked.connect(self._on_sign_document)
        sig_buttons.addWidget(self._sign_btn)

        signature_layout.addLayout(sig_buttons)

        actions_layout.addWidget(signature_group)
        actions_layout.addStretch()

        splitter.addWidget(actions_widget)
        splitter.setSizes([400, 300])

        content_layout.addWidget(splitter, 1)

        scroll.setWidget(content)
        self.add_widget(scroll)

    def _group_style(self) -> str:
        """Zwraca styl dla QGroupBox."""
        return """
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                border: 1px solid #2d3a50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """

    def _table_style(self) -> str:
        """Zwraca styl dla QTableWidget."""
        return """
            QTableWidget {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                gridline-color: #2d3a50;
            }
            QTableWidget::item {
                padding: 8px;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #e0a800;
                color: #1a1a2e;
            }
            QHeaderView::section {
                background-color: #1f2940;
                color: #8892a0;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2d3a50;
            }
        """

    def _scroll_style(self) -> str:
        """Zwraca styl dla QScrollArea."""
        return """
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #0f1629;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #2d3a50;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #e0a800;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #0f1629;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background-color: #2d3a50;
                border-radius: 5px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #e0a800;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """

    def _refresh_metadata(self) -> None:
        """Odświeża widok metadanych."""
        self._metadata_table.setRowCount(0)

        if not self._pdf_manager.is_loaded:
            return

        try:
            meta = self._pdf_manager.get_metadata()

            fields = [
                ("Tytuł", meta.title),
                ("Autor", meta.author),
                ("Temat", meta.subject),
                ("Słowa kluczowe", meta.keywords),
                ("Twórca", meta.creator),
                ("Producent", meta.producer),
                ("Data utworzenia", meta.creation_date),
                ("Data modyfikacji", meta.modification_date),
            ]

            for name, value in fields:
                row = self._metadata_table.rowCount()
                self._metadata_table.insertRow(row)
                self._metadata_table.setItem(row, 0, QTableWidgetItem(name))
                self._metadata_table.setItem(row, 1, QTableWidgetItem(value or "(brak)"))

        except Exception as e:
            QMessageBox.warning(
                self,
                "Błąd",
                f"Nie można odczytać metadanych:\n{e}"
            )

    def _on_scrub_metadata(self) -> None:
        """Obsługa usuwania metadanych."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        reply = QMessageBox.question(
            self,
            "Potwierdź usunięcie",
            "Czy na pewno chcesz usunąć wszystkie metadane?\n\n"
            "Ta operacja jest nieodwracalna.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._pdf_manager.scrub_metadata()
                self._refresh_metadata()
                QMessageBox.information(
                    self,
                    "Sukces",
                    "Metadane zostały usunięte.\n"
                    "Pamiętaj o zapisaniu dokumentu."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie można usunąć metadanych:\n{e}"
                )

    def _on_flatten(self) -> None:
        """Obsługa spłaszczania dokumentu."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        reply = QMessageBox.question(
            self,
            "Potwierdź spłaszczenie",
            "Czy na pewno chcesz spłaszczyć dokument?\n\n"
            "Formularze i adnotacje staną się nieedytowalne.\n"
            "Ta operacja jest nieodwracalna.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self._pdf_manager.flatten()
                QMessageBox.information(
                    self,
                    "Sukces",
                    "Dokument został spłaszczony.\n"
                    "Pamiętaj o zapisaniu dokumentu."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie można spłaszczyć dokumentu:\n{e}"
                )

    def _on_encrypt_document(self) -> None:
        """Szyfruje dokument hasłem."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        # Dialog z konfiguracją szyfrowania
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Szyfrowanie dokumentu")
        dialog.setText("Ustaw hasła i uprawnienia dla dokumentu PDF")

        # Własny widget z formularzem
        from PyQt6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox

        encrypt_dialog = QDialog(self)
        encrypt_dialog.setWindowTitle("Szyfrowanie dokumentu")
        encrypt_dialog.setMinimumWidth(400)
        encrypt_dialog.setStyleSheet("""
            QDialog {
                background-color: #16213e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit, QComboBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #2d3a50;
                background-color: #0f1629;
            }
            QCheckBox::indicator:checked {
                background-color: #e0a800;
                border-color: #e0a800;
            }
        """)

        layout = QVBoxLayout(encrypt_dialog)

        form = QFormLayout()

        # Hasło użytkownika (do otwierania)
        user_pw_edit = QLineEdit()
        user_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        user_pw_edit.setPlaceholderText("Pozostaw puste dla braku hasła")
        form.addRow("Hasło użytkownika:", user_pw_edit)

        # Hasło właściciela (do uprawnień)
        owner_pw_edit = QLineEdit()
        owner_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        owner_pw_edit.setPlaceholderText("Hasło do zmiany uprawnień")
        form.addRow("Hasło właściciela:", owner_pw_edit)

        # Poziom szyfrowania
        encryption_combo = QComboBox()
        encryption_combo.addItem("AES-256 (najsilniejsze)", 4)
        encryption_combo.addItem("AES-128", 3)
        encryption_combo.addItem("RC4-128", 2)
        encryption_combo.addItem("RC4-40 (słabe)", 1)
        form.addRow("Szyfrowanie:", encryption_combo)

        layout.addLayout(form)

        # Uprawnienia
        perms_group = QGroupBox("Uprawnienia użytkownika")
        perms_group.setStyleSheet(self._group_style())
        perms_layout = QVBoxLayout(perms_group)

        print_check = QCheckBox("Drukowanie")
        print_check.setChecked(True)
        perms_layout.addWidget(print_check)

        copy_check = QCheckBox("Kopiowanie tekstu i grafiki")
        copy_check.setChecked(False)
        perms_layout.addWidget(copy_check)

        modify_check = QCheckBox("Modyfikacja dokumentu")
        modify_check.setChecked(False)
        perms_layout.addWidget(modify_check)

        annotate_check = QCheckBox("Dodawanie adnotacji")
        annotate_check.setChecked(False)
        perms_layout.addWidget(annotate_check)

        forms_check = QCheckBox("Wypełnianie formularzy")
        forms_check.setChecked(True)
        perms_layout.addWidget(forms_check)

        layout.addWidget(perms_group)

        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(encrypt_dialog.accept)
        buttons.rejected.connect(encrypt_dialog.reject)
        layout.addWidget(buttons)

        if encrypt_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Pobierz wartości
        user_pw = user_pw_edit.text()
        owner_pw = owner_pw_edit.text()

        if not owner_pw:
            QMessageBox.warning(
                self,
                "Błąd",
                "Hasło właściciela jest wymagane do ustawienia uprawnień."
            )
            return

        # Wybierz gdzie zapisać
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz zaszyfrowany PDF",
            "",
            "Pliki PDF (*.pdf)"
        )

        if not filepath:
            return

        try:
            import fitz
            from pathlib import Path

            # Otwórz dokument
            doc = fitz.open(str(self._pdf_manager._filepath))

            # Przygotuj uprawnienia (bitmask)
            permissions = 0
            if print_check.isChecked():
                permissions |= fitz.PDF_PERM_PRINT
            if copy_check.isChecked():
                permissions |= fitz.PDF_PERM_COPY
            if modify_check.isChecked():
                permissions |= fitz.PDF_PERM_MODIFY
            if annotate_check.isChecked():
                permissions |= fitz.PDF_PERM_ANNOTATE
            if forms_check.isChecked():
                permissions |= fitz.PDF_PERM_FORM

            # Wybierz algorytm szyfrowania
            encrypt_method = encryption_combo.currentData()

            # Zapisz z szyfrowaniem
            doc.save(
                filepath,
                encryption=encrypt_method,
                user_pw=user_pw if user_pw else None,
                owner_pw=owner_pw,
                permissions=permissions,
            )
            doc.close()

            QMessageBox.information(
                self,
                "Sukces",
                f"Dokument zaszyfrowany i zapisany:\n{filepath}\n\n"
                f"Hasło użytkownika: {'(ustawione)' if user_pw else '(brak)'}\n"
                f"Hasło właściciela: (ustawione)\n"
                f"Algorytm: {encryption_combo.currentText()}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie można zaszyfrować dokumentu:\n{e}"
            )

    def _on_verify_signatures(self) -> None:
        """Weryfikuje podpisy w dokumencie."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        try:
            from pathlib import Path

            engine = SignatureEngine()
            filepath = Path(self._pdf_manager._filepath)
            signatures = engine.verify_signatures(filepath)

            if not signatures:
                QMessageBox.information(
                    self,
                    "Podpisy cyfrowe",
                    "Dokument nie zawiera podpisów cyfrowych."
                )
                return

            # Przygotuj raport
            lines = ["<b>Wykryte podpisy:</b><br>"]

            for i, sig in enumerate(signatures, 1):
                if sig.status == SignatureStatus.NOT_SIGNED:
                    lines.append("Dokument nie jest podpisany cyfrowo.")
                    break

                status_icon = {
                    SignatureStatus.VALID: "✅",
                    SignatureStatus.INVALID: "❌",
                    SignatureStatus.UNKNOWN: "⚠️",
                }.get(sig.status, "❓")

                lines.append(f"<b>Podpis {i}:</b> {status_icon}")
                if sig.signer_name:
                    lines.append(f"  Podpisujący: {sig.signer_name}")
                if sig.signing_time:
                    lines.append(f"  Data: {sig.signing_time}")
                if sig.reason:
                    lines.append(f"  Powód: {sig.reason}")
                if sig.location:
                    lines.append(f"  Miejsce: {sig.location}")
                if sig.page:
                    lines.append(f"  Strona: {sig.page}")
                lines.append("")

            QMessageBox.information(
                self,
                "Weryfikacja podpisów",
                "<br>".join(lines)
            )

            # Aktualizuj status
            self._update_signature_status(signatures)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie można zweryfikować podpisów:\n{e}"
            )

    def _on_sign_document(self) -> None:
        """Podpisuje dokument certyfikatem."""
        if not self._pdf_manager.is_loaded:
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw otwórz dokument PDF"
            )
            return

        from pdfdeck.ui.dialogs.signature_dialog import SignatureDialog
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path

        config = SignatureDialog.get_signature_config(self)

        if not config:
            return

        # Wybierz gdzie zapisać
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz podpisany PDF",
            "",
            "Pliki PDF (*.pdf)"
        )

        if not filepath:
            return

        try:
            engine = SignatureEngine()
            input_path = Path(self._pdf_manager._filepath)
            output_path = Path(filepath)

            success = engine.sign_pdf(input_path, output_path, config)

            if success:
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Dokument podpisany i zapisany:\n{filepath}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Ostrzeżenie",
                    "Dokument został zapisany z wizualnym podpisem,\n"
                    "ale bez pełnego podpisu kryptograficznego.\n\n"
                    "Zainstaluj bibliotekę 'endesive' dla pełnego wsparcia."
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie można podpisać dokumentu:\n{e}"
            )

    def _update_signature_status(self, signatures) -> None:
        """Aktualizuje status podpisów w UI."""
        if not signatures:
            self._sig_status_label.setText("Status: brak podpisów")
            self._sig_status_label.setStyleSheet("color: #8892a0;")
            return

        for sig in signatures:
            if sig.status == SignatureStatus.NOT_SIGNED:
                self._sig_status_label.setText("Status: brak podpisów")
                self._sig_status_label.setStyleSheet("color: #8892a0;")
            elif sig.status == SignatureStatus.VALID:
                self._sig_status_label.setText("Status: ✅ podpisany (ważny)")
                self._sig_status_label.setStyleSheet("color: #27ae60;")
            elif sig.status == SignatureStatus.INVALID:
                self._sig_status_label.setText("Status: ❌ podpisany (nieważny)")
                self._sig_status_label.setStyleSheet("color: #e74c3c;")
            else:
                self._sig_status_label.setText("Status: ⚠️ podpisany (nieznany)")
                self._sig_status_label.setStyleSheet("color: #f39c12;")
            break  # Pokaż status pierwszego podpisu

    # === Public API ===

    def on_document_loaded(self) -> None:
        """Wywoływane po załadowaniu dokumentu."""
        self._refresh_metadata()
        self._sig_status_label.setText("Status: sprawdź podpisy")
        self._sig_status_label.setStyleSheet("color: #8892a0;")
