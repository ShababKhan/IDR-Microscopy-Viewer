"""
Plate Grid View Module

Provides QGraphicsView-based visualization for IDR plates,
rendering wells and handling user interactions.
"""

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QWidget, QVBoxLayout,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPainter

from models.plate import IDRWell
from viewmodels.plate_viewmodel import PlateViewModel

class WellItem(QGraphicsEllipseItem):
    """
    QGraphicsItem representing an individual well in a plate.
    Handles drawing and selection events.
    """
    
    # Define sizes and colors
    DIAMETER = 24.0
    PADDING = 4.0
    
    COLOR_EMPTY = QColor("#e0e0e0")      # Light gray for empty wells
    COLOR_HAS_IMAGE = QColor("#4caf50")  # Green for wells with images
    COLOR_SELECTED = QColor("#2196f3")   # Blue for selected wells
    
    def __init__(self, well: IDRWell, parent=None):
        super().__init__(0, 0, self.DIAMETER, self.DIAMETER, parent)
        self.well = well
        
        # Enable item selection
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        
        # Position based on row and column
        x = well.column * (self.DIAMETER + self.PADDING)
        y = well.row * (self.DIAMETER + self.PADDING)
        self.setPos(x, y)
        
        # Setup initial styles
        self._update_style()
        
    def _update_style(self):
        """Update pen and brush based on well state and selection."""
        pen = QPen(Qt.GlobalColor.darkGray)
        pen.setWidth(1)
        
        if self.isSelected():
            pen = QPen(self.COLOR_SELECTED)
            pen.setWidth(2)
            brush = QBrush(self.COLOR_SELECTED.lighter(150))
        elif self.well.has_image:
            brush = QBrush(self.COLOR_HAS_IMAGE)
        else:
            brush = QBrush(self.COLOR_EMPTY)
            
        self.setPen(pen)
        self.setBrush(brush)
        
    def itemChange(self, change, value):
        """Handle selection changes."""
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._update_style()
        return value


class PlateGridScene(QGraphicsScene):
    """
    Custom graphics scene that emits signals when wells are selected.
    """
    wellSelected = pyqtSignal(object)  # Emits IDRWell
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selectionChanged.connect(self._handle_selection)
        
    def _handle_selection(self):
        """Emit the well of the currently selected WellItem."""
        items = self.selectedItems()
        if items and isinstance(items[0], WellItem):
            self.wellSelected.emit(items[0].well)
        else:
            self.wellSelected.emit(None)


class PlateGridView(QWidget):
    """
    Main widget for displaying the plate grid.
    Contains the graphics view and connects to the PlateViewModel.
    """
    
    def __init__(self, viewmodel: PlateViewModel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Initialize the QGraphicsView and layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create Scene & View
        self.scene = PlateGridScene(self)
        self.view = QGraphicsView(self.scene)
        
        # View settings and optimizations
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        layout.addWidget(self.view)
        
    def _connect_signals(self):
        """Connect ViewModel signals to View updates."""
        self.viewmodel.plateLoaded.connect(self._on_plate_loaded)
        self.viewmodel.wellSelectionChanged.connect(self._on_well_selection_changed)
        self.scene.wellSelected.connect(self._on_scene_well_selected)
        
    def _on_plate_loaded(self):
        """Redraw the entire plate grid when a new plate is loaded."""
        self.scene.clear()
        
        rows = self.viewmodel.rows
        cols = self.viewmodel.columns
        wells = self.viewmodel.wells
        
        if rows == 0 or cols == 0:
            return
            
        # Add column labels (1, 2, 3...)
        for c in range(cols):
            text = QGraphicsTextItem(str(c + 1))
            font = text.font()
            font.setBold(True)
            text.setFont(font)
            
            # Position above the columns
            x = c * (WellItem.DIAMETER + WellItem.PADDING) + (WellItem.DIAMETER / 2) - text.boundingRect().width() / 2
            y = -(WellItem.DIAMETER)
            text.setPos(x, y)
            self.scene.addItem(text)
            
        # Add row labels (A, B, C...)
        for r in range(rows):
            label_char = chr(ord('A') + r)
            text = QGraphicsTextItem(label_char)
            font = text.font()
            font.setBold(True)
            text.setFont(font)
            
            # Position to the left of the rows
            x = -(WellItem.DIAMETER)
            y = r * (WellItem.DIAMETER + WellItem.PADDING) + (WellItem.DIAMETER / 2) - text.boundingRect().height() / 2
            text.setPos(x, y)
            self.scene.addItem(text)
            
        # Add wells
        for well in wells:
            item = WellItem(well)
            self.scene.addItem(item)
            
        # Adjust scene rect with padding to include labels
        padding = WellItem.DIAMETER * 2
        rect = self.scene.itemsBoundingRect()
        rect.adjust(-padding, -padding, padding, padding)
        self.scene.setSceneRect(rect)
        
        # Fit view
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _on_well_selection_changed(self, well: IDRWell):
        """Handle programmatic selection changes from the ViewModel."""
        self.scene.blockSignals(True)
        try:
            # Unselect all first
            for item in self.scene.selectedItems():
                item.setSelected(False)
                
            if well:
                # Find and select the corresponding item
                for item in self.scene.items():
                    if isinstance(item, WellItem) and item.well == well:
                        item.setSelected(True)
                        self.view.ensureVisible(item)
                        break
        finally:
            self.scene.blockSignals(False)

    def _on_scene_well_selected(self, well: IDRWell):
        """Handle user clicking on a well in the scene."""
        # Update viewmodel without causing a signal loop
        # We temporarily block signals or rely on the VM's internal check.
        # PlateViewModel.select_well naturally avoids loops by checking for inequality.
        self.viewmodel.select_well(well)
        
    def resizeEvent(self, event):
        """Ensure grid fits perfectly on resize."""
        super().resizeEvent(event)
        if hasattr(self, 'scene') and self.scene.sceneRect().isValid():
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
