"""
ProfileComboBox - ComboBox z profilami watermark/stamp.

Funkcje:
- Wyświetla listę zapisanych profili
- Przycisk "Zapisz jako profil"
- Przycisk "Usuń profil"
"""

from typing import Optional, Callable

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from pdfdeck.core.profile_manager import ProfileManager, ProfileType


class ProfileComboBox(QWidget):
    """
    ComboBox z profilami i przyciskami zarządzania.

    Sygnały:
        profile_selected(str): Wyemitowany po wyborze profilu
        profile_deleted(str): Wyemitowany po usunięciu profilu
    """

    profile_selected = pyqtSignal(str)  # nazwa profilu
    profile_deleted = pyqtSignal(str)

    def __init__(
        self,
        profile_type: ProfileType,
        on_save_clicked: Optional[Callable] = None,
        parent=None,
    ):
        super().__init__(parent)

        self._profile_type = profile_type
        self._on_save_clicked = on_save_clicked
        self._profile_manager = ProfileManager()

        self._setup_ui()
        self._refresh_profiles()

    def _setup_ui(self) -> None:
        from PyQt6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ComboBox
        self._combo = QComboBox()
        self._combo.setStyleSheet(
            """
            QComboBox {
                background-color: #0f1629;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                padding: 8px 12px;
                padding-right: 30px;
                color: #ffffff;
                min-width: 180px;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #3d4a60;
            }
            QComboBox:focus {
                border-color: #e0a800;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            QComboBox::down-arrow {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #e0a800;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1f2940;
                border: 1px solid #2d3a50;
                border-radius: 6px;
                color: #ffffff;
                selection-background-color: #e0a800;
                selection-color: #1a1a2e;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px;
                min-height: 20px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #2d3a50;
            }
        """
        )
        self._combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self._combo)

        # Wiersz przycisków
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        # Przycisk zapisz
        self._save_btn = QPushButton("Zapisz")
        self._save_btn.setMinimumWidth(80)
        self._save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #1a5a2e;
                border: 1px solid #2d7a40;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2d7a40;
                border-color: #3d9a50;
            }
            QPushButton:pressed {
                background-color: #145020;
            }
        """
        )
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._on_save)
        buttons_layout.addWidget(self._save_btn)

        # Przycisk usuń
        self._delete_btn = QPushButton("Usuń")
        self._delete_btn.setMinimumWidth(70)
        self._delete_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #5a1a1a;
                border: 1px solid #7a2d2d;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7a2d2d;
                border-color: #9a3d3d;
            }
            QPushButton:pressed {
                background-color: #401414;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                border-color: #3d3d3d;
                color: #6d6d6d;
            }
        """
        )
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.clicked.connect(self._on_delete)
        self._delete_btn.setEnabled(False)
        buttons_layout.addWidget(self._delete_btn)

        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

    def _refresh_profiles(self) -> None:
        """Odświeża listę profili."""
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem("(brak profilu)", None)

        if self._profile_type == ProfileType.WATERMARK:
            profiles = self._profile_manager.get_watermark_profiles()
        else:
            profiles = self._profile_manager.get_stamp_profiles()

        for profile in profiles:
            self._combo.addItem(profile.metadata.name, profile.metadata.name)

        self._combo.blockSignals(False)
        self._delete_btn.setEnabled(False)

    def _on_selection_changed(self, index: int) -> None:
        name = self._combo.currentData()
        self._delete_btn.setEnabled(name is not None)
        if name:
            self.profile_selected.emit(name)

    def _on_save(self) -> None:
        """Wywołuje callback zapisania profilu."""
        if self._on_save_clicked:
            self._on_save_clicked()

    def _on_delete(self) -> None:
        """Usuwa wybrany profil."""
        name = self._combo.currentData()
        if not name:
            return

        reply = QMessageBox.question(
            self,
            "Usuń profil",
            f"Czy na pewno usunąć profil '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self._profile_type == ProfileType.WATERMARK:
                self._profile_manager.delete_watermark_profile(name)
            else:
                self._profile_manager.delete_stamp_profile(name)

            self.profile_deleted.emit(name)
            self._refresh_profiles()

    def get_selected_profile_name(self) -> Optional[str]:
        """Zwraca nazwę wybranego profilu."""
        return self._combo.currentData()

    def refresh(self) -> None:
        """Odświeża listę profili (wywoływane po zapisaniu)."""
        current = self._combo.currentData()
        self._refresh_profiles()

        # Przywróć poprzedni wybór jeśli nadal istnieje
        if current:
            for i in range(self._combo.count()):
                if self._combo.itemData(i) == current:
                    self._combo.setCurrentIndex(i)
                    break

    def set_save_button_visible(self, visible: bool) -> None:
        """Pokazuje/ukrywa przycisk zapisz."""
        self._save_btn.setVisible(visible)

    def set_delete_button_visible(self, visible: bool) -> None:
        """Pokazuje/ukrywa przycisk usuń."""
        self._delete_btn.setVisible(visible)
