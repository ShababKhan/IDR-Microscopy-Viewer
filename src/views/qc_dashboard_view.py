"""
QC Dashboard View Module

Renders Quality Control plots (e.g., Z-scores) using pyqtgraph.
"""
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from viewmodels.qc_viewmodel import QCViewModel

class QCDashboardView(QWidget):
    """
    A view containing pyqtgraph plots for QC metrics analysis.
    """
    
    def __init__(self, viewmodel: QCViewModel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        self.title_lbl = QLabel("QC Metrics: Z-Score Distribution")
        self.title_lbl.setStyleSheet("font-weight: bold; background-color: #222; color: white; padding: 4px;")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_lbl)
        
        # Plot Widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1a1a1a')
        self.plot_widget.setLabel('left', 'Z-Score')
        self.plot_widget.setLabel('bottom', 'Wells')
        self.plot_widget.showGrid(x=False, y=True, alpha=0.3)
        self.plot_widget.setVisible(False)
        layout.addWidget(self.plot_widget, stretch=1)
        
        self.empty_lbl = QLabel("No QC Data available for this plate.")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setStyleSheet("color: gray;")
        layout.addWidget(self.empty_lbl)
        
    def _connect_signals(self):
        self.viewmodel.metricsReady.connect(self._render_plots)
        
    def _render_plots(self):
        """Redraw the pyqtgraph scatter plot when new data arrives."""
        self.plot_widget.clear()
        
        if not self.viewmodel.has_data:
            self.plot_widget.setVisible(False)
            self.empty_lbl.setVisible(True)
            return
            
        self.plot_widget.setVisible(True)
        self.empty_lbl.setVisible(False)
        
        # Scatter Plot
        # Convert lists to pg arrays
        x_data = list(range(len(self.viewmodel.z_scores)))
        y_data = self.viewmodel.z_scores
        
        # Create BarGraphItem or ScatterPlotItem
        scatter = pg.ScatterPlotItem(
            x=x_data,
            y=y_data,
            size=10,
            pen=pg.mkPen(None),
            brush=[pg.mkBrush(c) for c in self.viewmodel.colors],
            hoverable=True,
            hoverSize=15
        )
        self.plot_widget.addItem(scatter)
        
        # Add a baseline class for Z=0
        baseline = pg.InfiniteLine(angle=0, pen=pg.mkPen('w', width=1, style=Qt.PenStyle.DashLine))
        self.plot_widget.addItem(baseline)
        
        # Reset view bounds
        self.plot_widget.autoRange()
