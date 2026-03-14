"""
Image ViewModel Module

Manages the state, multi-dimensional slicing, and fetching for Image Detail View.
"""

import logging
from typing import Optional

from PyQt6.QtCore import pyqtSignal, pyqtProperty, pyqtSlot, QByteArray

from .base_viewmodel import ViewModel
from models.image import IDRImage
from core.idr_adapter import IDRClientAdapter
from core.concurrency import ThreadPoolManager

logger = logging.getLogger(__name__)


class ImageViewModel(ViewModel):
    """
    ViewModel for the Image Detail view.
    
    Handles fetching multidimensional image data from the API lazily
    and caching it.
    """
    
    # Signals
    imageLoaded = pyqtSignal()
    frameChanged = pyqtSignal()
    
    def __init__(self, idr_adapter: IDRClientAdapter, thread_pool: ThreadPoolManager, parent=None):
        super().__init__(parent)
        self._idr_adapter = idr_adapter
        self._thread_pool = thread_pool
        self._image: Optional[IDRImage] = None
        self._current_z = 0
        self._current_t = 0
        self._image_data = QByteArray()
        self._high_res = False
    
    # ---------------------------------------------------------
    # Properties
    # ---------------------------------------------------------
    
    @pyqtProperty(int)
    def current_z(self) -> int:
        return self._current_z
        
    @pyqtProperty(int)
    def current_t(self) -> int:
        return self._current_t
        
    @pyqtProperty(int)
    def max_z(self) -> int:
        return self._image.size_z if self._image else 1
        
    @pyqtProperty(int)
    def max_t(self) -> int:
        return self._image.size_t if self._image else 1
        
    @pyqtProperty(QByteArray, notify=frameChanged)
    def image_data(self) -> QByteArray:
        return self._image_data
        
    @property
    def has_image(self) -> bool:
        return self._image is not None
        
    # ---------------------------------------------------------
    # Methods & Slots
    # ---------------------------------------------------------
    
    @pyqtSlot(int)
    def load_image(self, image_id: int):
        """Load image metadata asynchronously and then fetch the first frame."""
        self.begin_operation(f"Loading image {image_id} details...")
        
        def fetch_meta():
            meta = self._idr_adapter.get_image_metadata(image_id)
            if not meta:
                raise ValueError(f"Metadata for image {image_id} not found.")
            return meta
            
        def on_success(meta):
            self._image = IDRImage.from_api_dict(meta)
            self._current_z = 0
            self._current_t = 0
            self.imageLoaded.emit()
            
            # Now trigger the frame data fetch (which is also async)
            self._fetch_current_frame()
            self.end_operation(success=True, status_message=f"Loaded Image {image_id}")
            
        def on_error(e_tuple):
            e, tb = e_tuple
            self.handle_error(e, "Failed to load image")
            self._image = None
            self._image_data.clear()
            self.imageLoaded.emit()
            self.frameChanged.emit()
            
        self._thread_pool.execute(fetch_meta, on_result=on_success, on_error=on_error)

    def clear(self):
        """Clear the current image."""
        self._image = None
        self._current_z = 0
        self._current_t = 0
        self._image_data.clear()
        self.imageLoaded.emit()
        self.frameChanged.emit()
        self.set_status("")

    def set_high_res(self, enabled: bool):
        """Toggle high-resolution fetching and re-fetch the current frame."""
        self._high_res = enabled
        if self._image:
            self._fetch_current_frame()
            
    @pyqtSlot(int)
    def set_z(self, z_index: int):
        """Update current Z index and fetch matching frame lazily."""
        if not self._image or z_index == self._current_z:
            return
            
        if 0 <= z_index < self.max_z:
            self._current_z = z_index
            self._fetch_current_frame()
            
    @pyqtSlot(int)
    def set_t(self, t_index: int):
        """Update current T index and fetch matching frame lazily."""
        if not self._image or t_index == self._current_t:
            return
            
        if 0 <= t_index < self.max_t:
            self._current_t = t_index
            self._fetch_current_frame()
            
    def _fetch_current_frame(self):
        """Fetches the image data bytes for the current Z and T lazily and asynchronously."""
        if not self._image:
            return
            
        self.begin_operation("Fetching frame...")
        
        z, t = self._current_z, self._current_t
        image_id = self._image.image_id
        high_res = self._high_res
        
        def fetch_data():
            return self._idr_adapter.get_image(image_id, z=z, t=t, high_res=high_res)
            
        def on_success(data_bytes):
            # Check if user moved sliders while task was running
            if z != self._current_z or t != self._current_t:
                return
                
            if data_bytes:
                self._image_data = QByteArray(data_bytes)
            else:
                self._image_data.clear()
                
            self.frameChanged.emit()
            self.end_operation(success=True, status_message=f"Z: {self.current_z+1}/{self.max_z} | T: {self.current_t+1}/{self.max_t}")
            
        def on_error(e_tuple):
            e, tb = e_tuple
            self.handle_error(e, "Failed fetching frame")
            self._image_data.clear()
            self.frameChanged.emit()
            
        self._thread_pool.execute(fetch_data, on_result=on_success, on_error=on_error)
