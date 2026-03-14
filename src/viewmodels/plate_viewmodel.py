"""
Plate ViewModel Module

Manages the state and data fetching for the Plate Grid View.
"""

import logging
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import pyqtSignal, pyqtProperty, pyqtSlot

from .base_viewmodel import ViewModel
from models.plate import IDRPlate, IDRWell
from models.qc_metrics import QCMetrics
from core.idr_adapter import IDRClientAdapter
from core.concurrency import ThreadPoolManager

logger = logging.getLogger(__name__)


class PlateViewModel(ViewModel):
    """
    ViewModel for the Plate Grid view.
    
    Handles fetching plate data from the IDR API and managing
    the selected state of wells.
    """
    
    # Signals
    plateLoaded = pyqtSignal()
    wellSelectionChanged = pyqtSignal(object)  # Emits specific IDRWell or None
    
    def __init__(self, idr_adapter: IDRClientAdapter, thread_pool: ThreadPoolManager, parent=None):
        """
        Initialize the PlateViewModel.
        
        Args:
            idr_adapter: Adapter for API calls.
            thread_pool: Concurrency manager.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._idr_adapter = idr_adapter
        self._thread_pool = thread_pool
        self._plate: Optional[IDRPlate] = None
        self._selected_well: Optional[IDRWell] = None
    
    # ---------------------------------------------------------
    # Properties
    # ---------------------------------------------------------
    
    @pyqtProperty(int)
    def plate_id(self) -> int:
        return self._plate.plate_id if self._plate else -1
        
    @property
    def plate(self) -> Optional[IDRPlate]:
        """Provides access to the underlying plate model."""
        return self._plate
        
    @pyqtProperty(str, notify=plateLoaded)
    def plate_name(self) -> str:
        return self._plate.name if self._plate else ""

    @pyqtProperty(int)
    def rows(self) -> int:
        return self._plate.rows if self._plate else 0
        
    @pyqtProperty(int)
    def columns(self) -> int:
        return self._plate.columns if self._plate else 0
        
    @property
    def wells(self) -> List[IDRWell]:
        return self._plate.wells if self._plate else []
        
    @property
    def selected_well(self) -> Optional[IDRWell]:
        return self._selected_well
    
    # ---------------------------------------------------------
    # Methods & Slots
    # ---------------------------------------------------------
    
    @pyqtSlot(int)
    def load_plate(self, plate_id: int):
        """
        Fetch plate data asynchronously from the API and initialize models.
        """
        self.begin_operation(f"Loading plate {plate_id}...")
        
        def fetch_task():
            plate_data = self._idr_adapter.get_plate(plate_id)
            if not plate_data:
                raise ValueError(f"Plate {plate_id} not found.")
            return plate_data
            
        def on_success(plate_data):
            # Parse into a model on main thread
            self._plate = IDRPlate.from_api_dict(plate_data)
            self.select_well(None)
            self.plateLoaded.emit()
            self.end_operation(success=True, status_message=f"Loaded plate: {self.plate_name}")
            
        def on_error(e_tuple):
            e, tb = e_tuple
            self.handle_error(e, "Failed to load plate")
            self._plate = None
            self.plateLoaded.emit()
            
        self._thread_pool.execute(
            fn=fetch_task,
            on_result=on_success,
            on_error=on_error
        )
            
    @pyqtSlot(int, int)
    def select_well_by_coords(self, row: int, col: int):
        """Select a well based on row and column indices."""
        if not self._plate:
            return
            
        well = self._plate.get_well(row, col)
        self.select_well(well)
            
    def select_well(self, well: Optional[IDRWell]):
        """Set the currently selected well."""
        if self._selected_well != well:
            self._selected_well = well
            self.wellSelectionChanged.emit(well)
            
            if well:
                # E.g. Update status to show well details
                self.set_status(f"Selected well: {well.label}")
            else:
                self.set_status("")
                

