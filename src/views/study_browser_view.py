"""
Study Browser View

A QDockWidget containing a QTreeWidget that displays the IDR
hierarchy: Screen → Plates or Project → Datasets → Images.
"""
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QPushButton, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from models.study import IDRStudy
from viewmodels.study_browser_viewmodel import StudyBrowserViewModel

logger = logging.getLogger(__name__)

# Simple text icon tags for readability
_ICONS = {
    "screen":  "🔬",
    "project": "📁",
    "plate":   "🗂",
    "dataset": "📦",
    "image":   "🖼",
    "loading": "⏳",
    "error":   "❌",
}

# Custom node types stored in Qt.ItemDataRole.UserRole
ROLE_TYPE    = Qt.ItemDataRole.UserRole
ROLE_ID      = Qt.ItemDataRole.UserRole + 1
ROLE_LOADED  = Qt.ItemDataRole.UserRole + 2


class StudyBrowserView(QWidget):
    """Tree browser that lets the user navigate any IDR study hierarchy."""

    # Emitted when a plate is selected — connects to PlateViewModel.load_plate
    plateSelected   = pyqtSignal(int)
    # Emitted when a dataset image is selected
    imageSelected   = pyqtSignal(int)

    def __init__(self, viewmodel: StudyBrowserViewModel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self._setup_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Header label
        header = QLabel("Study Browser")
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        # Input row
        input_row = QHBoxLayout()
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Study / Screen / Project ID")
        self.id_input.returnPressed.connect(self._on_load_clicked)
        input_row.addWidget(self.id_input)

        self.load_btn = QPushButton("Load")
        self.load_btn.setFixedWidth(50)
        self.load_btn.clicked.connect(self._on_load_clicked)
        input_row.addWidget(self.load_btn)
        layout.addLayout(input_row)

        # Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tree.itemExpanded.connect(self._on_item_expanded)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree, stretch=1)

        # Hint label
        self.hint = QLabel("Enter a Screen ID (e.g. 3) or Project ID (e.g. 101) and press Load.")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.hint)

    def _connect_signals(self):
        self.viewmodel.studyLoaded.connect(self._on_study_loaded)
        self.viewmodel.platesLoaded.connect(self._on_plates_loaded)
        self.viewmodel.datasetsLoaded.connect(self._on_datasets_loaded)
        self.viewmodel.datasetImagesLoaded.connect(self._on_dataset_images_loaded)
        self.viewmodel.statusChanged.connect(self._on_status)
        self.viewmodel.errorOccurred.connect(self._on_error)

    # ------------------------------------------------------------------
    # User actions
    # ------------------------------------------------------------------

    def _on_load_clicked(self):
        text = self.id_input.text().strip()
        if not text.isdigit():
            self.hint.setText("⚠ Please enter a valid numeric ID.")
            return
        self.tree.clear()
        self.hint.setText("Looking up study…")
        self.viewmodel.load_study(int(text))

    def _on_item_expanded(self, item: QTreeWidgetItem):
        """Lazily load children when a node is expanded for the first time."""
        node_type = item.data(0, ROLE_TYPE)
        node_id   = item.data(0, ROLE_ID)
        loaded    = item.data(0, ROLE_LOADED)

        if loaded:
            return

        item.setData(0, ROLE_LOADED, True)
        # Remove the placeholder "Loading…" child
        item.takeChildren()

        if node_type == "screen":
            self.viewmodel.load_plates(node_id)
            self._pending_screen_item = item
        elif node_type == "project":
            self.viewmodel.load_datasets(node_id)
            self._pending_project_item = item
        elif node_type == "dataset":
            self.viewmodel.load_dataset_images(node_id)
            self._pending_dataset_item = item
            self._pending_dataset_id   = node_id

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _col):
        node_type = item.data(0, ROLE_TYPE)
        node_id   = item.data(0, ROLE_ID)

        if node_type == "plate":
            self.plateSelected.emit(node_id)
        elif node_type == "image":
            self.imageSelected.emit(node_id)

    # ------------------------------------------------------------------
    # ViewModel responses
    # ------------------------------------------------------------------

    def _on_study_loaded(self, study: IDRStudy):
        self.tree.clear()
        icon = _ICONS[study.study_type]
        root = QTreeWidgetItem([f"{icon} {study.name}"])
        root.setData(0, ROLE_TYPE,   study.study_type)
        root.setData(0, ROLE_ID,     study.study_id)
        root.setData(0, ROLE_LOADED, False)
        root.setToolTip(0, study.description or study.name)

        # Add placeholder child so the expand arrow shows
        root.addChild(self._loading_item())
        self.tree.addTopLevelItem(root)
        root.setExpanded(True)  # auto-expand to trigger lazy load

        kind_label = "HCS (Screen → Plates → Wells)" if study.study_type == "screen" \
                     else "Non-HCS (Project → Datasets → Images)"
        self.hint.setText(f"Type: {kind_label}\nDouble-click a Plate or Image to view it.")

    def _on_plates_loaded(self, plates):
        parent = getattr(self, "_pending_screen_item", None)
        if parent is None:
            return
        for p in plates:
            child = QTreeWidgetItem([f"{_ICONS['plate']} {p['name']}"])
            child.setData(0, ROLE_TYPE,   "plate")
            child.setData(0, ROLE_ID,     p["id"])
            child.setData(0, ROLE_LOADED, True)
            child.setToolTip(0, f"Plate ID: {p['id']}")
            parent.addChild(child)
        if not plates:
            parent.addChild(QTreeWidgetItem(["(no plates)"]))

    def _on_datasets_loaded(self, datasets):
        parent = getattr(self, "_pending_project_item", None)
        if parent is None:
            return
        for d in datasets:
            child = QTreeWidgetItem([f"{_ICONS['dataset']} {d['name']} ({d.get('child_count', '?')} images)"])
            child.setData(0, ROLE_TYPE,   "dataset")
            child.setData(0, ROLE_ID,     d["id"])
            child.setData(0, ROLE_LOADED, False)
            child.setToolTip(0, f"Dataset ID: {d['id']}")
            child.addChild(self._loading_item())
            parent.addChild(child)
        if not datasets:
            parent.addChild(QTreeWidgetItem(["(no datasets)"]))

    def _on_dataset_images_loaded(self, dataset_id: int, images):
        parent = getattr(self, "_pending_dataset_item", None)
        if parent is None or getattr(self, "_pending_dataset_id", None) != dataset_id:
            return
        for img in images:
            child = QTreeWidgetItem([f"{_ICONS['image']} {img['name']}"])
            child.setData(0, ROLE_TYPE,   "image")
            child.setData(0, ROLE_ID,     img["id"])
            child.setData(0, ROLE_LOADED, True)
            child.setToolTip(0, f"Image ID: {img['id']}")
            parent.addChild(child)
        if not images:
            parent.addChild(QTreeWidgetItem(["(no images)"]))

    def _on_status(self, msg: str):
        if msg:
            self.hint.setText(msg)

    def _on_error(self, msg: str):
        self.hint.setText(f"{_ICONS['error']} {msg}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _loading_item() -> QTreeWidgetItem:
        item = QTreeWidgetItem([f"{_ICONS['loading']} Loading…"])
        return item
