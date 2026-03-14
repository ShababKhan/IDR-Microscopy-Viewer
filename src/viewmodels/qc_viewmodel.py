"""
QC ViewModel 

Collects, aggregates, and serves QCMetrics from the loaded plate.
"""

from PyQt6.QtCore import pyqtSignal, pyqtProperty

from .base_viewmodel import ViewModel
from .plate_viewmodel import PlateViewModel

class QCViewModel(ViewModel):
    """
    ViewModel for the Quality Control dashboard.
    Listens to the PlateViewModel to gather updated QC metrics for charts.
    """
    
    metricsReady = pyqtSignal()
    
    def __init__(self, plate_viewmodel: PlateViewModel, parent=None):
        super().__init__(parent)
        self.plate_viewmodel = plate_viewmodel
        
        # Extracted data arrays for plotting
        self._well_labels = []
        self._z_scores = []
        self._colors = [] # Representing control status
        
        # Listen for plate loading
        self.plate_viewmodel.plateLoaded.connect(self._on_plate_loaded)
        
    @property
    def well_labels(self):
        return self._well_labels
        
    @property
    def z_scores(self):
        return self._z_scores
        
    @property
    def colors(self):
        return self._colors
        
    @property
    def has_data(self):
        return len(self._z_scores) > 0
        
    def _on_plate_loaded(self):
        """Extract QC metrics from the plate into flat lists for PyQtGraph."""
        self._well_labels = []
        self._z_scores = []
        self._colors = []
        
        plate = self.plate_viewmodel.plate
        if not plate:
            self.metricsReady.emit()
            return
            
        for well in plate.wells:
            if well.qc_metrics and well.qc_metrics.z_score is not None:
                self._well_labels.append(well.label)
                self._z_scores.append(well.qc_metrics.z_score)
                
                if well.qc_metrics.is_positive_control:
                    self._colors.append((0, 255, 0, 200)) # Green
                elif well.qc_metrics.is_negative_control:
                    self._colors.append((255, 0, 0, 200)) # Red
                else:
                    self._colors.append((100, 150, 255, 150)) # Blue default
                    
        self.metricsReady.emit()
