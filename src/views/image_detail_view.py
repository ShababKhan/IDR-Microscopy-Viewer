"""
Image Detail View Module

Provides visualization for individual microscopy images,
including multi-dimensional navigation (Z-stacks and timepoints).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSizePolicy, QCheckBox
)
from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QPixmap

from viewmodels.image_viewmodel import ImageViewModel


class ImageDetailView(QWidget):
    """
    Widget for displaying a single image and multidimensional controls.
    """
    
    def __init__(self, viewmodel: ImageViewModel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Build the layout and child widgets."""
        layout = QVBoxLayout(self)
        
        # Image Display Area
        self.image_label = QLabel("No image selected")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black; color: white;")
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout.addWidget(self.image_label, stretch=1)
        
        # Controls Container
        controls_layout = QVBoxLayout()
        
        # Z-Stack Control
        z_layout = QHBoxLayout()
        self.z_label = QLabel("Z: 1/1")
        self.z_slider = QSlider(Qt.Orientation.Horizontal)
        self.z_slider.setMinimum(0)
        self.z_slider.setMaximum(0)
        self.z_slider.setEnabled(False)
        z_layout.addWidget(self.z_label)
        z_layout.addWidget(self.z_slider)
        controls_layout.addLayout(z_layout)
        
        # Timepoint Control
        t_layout = QHBoxLayout()
        self.t_label = QLabel("T: 1/1")
        self.t_slider = QSlider(Qt.Orientation.Horizontal)
        self.t_slider.setMinimum(0)
        self.t_slider.setMaximum(0)
        self.t_slider.setEnabled(False)
        t_layout.addWidget(self.t_label)
        t_layout.addWidget(self.t_slider)
        controls_layout.addLayout(t_layout)
        
        # High-Resolution Toggle
        hires_layout = QHBoxLayout()
        self.hires_checkbox = QCheckBox("High Resolution")
        self.hires_checkbox.setToolTip("When checked, fetches a 2048px image instead of 512px thumbnail")
        hires_layout.addStretch()
        hires_layout.addWidget(self.hires_checkbox)
        controls_layout.addLayout(hires_layout)
        
        # Loading Indicator
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_label.setStyleSheet("color: gray; font-size: 11px;")
        controls_layout.addWidget(self.status_label)
        
        layout.addLayout(controls_layout)
        
    def _connect_signals(self):
        """Connect UI signals to ViewModel slots and vice-versa."""
        # UI to ViewModel
        self.z_slider.valueChanged.connect(self.viewmodel.set_z)
        self.t_slider.valueChanged.connect(self.viewmodel.set_t)
        self.hires_checkbox.stateChanged.connect(self._on_hires_toggled)
        
        # ViewModel to UI
        self.viewmodel.imageLoaded.connect(self._on_image_loaded)
        self.viewmodel.frameChanged.connect(self._on_frame_changed)
        self.viewmodel.loadingChanged.connect(self._on_loading_changed)
        self.viewmodel.statusChanged.connect(self.status_label.setText)
        
    def _on_image_loaded(self):
        """Update slider ranges and labels when a new image is loaded."""
        if not self.viewmodel.has_image:
            self._disable_controls()
            self.image_label.clear()
            self.image_label.setText("No image selected")
            return
            
        # Update Z slider
        max_z = self.viewmodel.max_z
        self.z_slider.setMaximum(max_z - 1)
        self.z_slider.setValue(0)
        self.z_slider.setEnabled(max_z > 1)
        self.z_label.setText(f"Z: 1/{max_z}")
        
        # Update T slider
        max_t = self.viewmodel.max_t
        self.t_slider.setMaximum(max_t - 1)
        self.t_slider.setValue(0)
        self.t_slider.setEnabled(max_t > 1)
        self.t_label.setText(f"T: 1/{max_t}")
        
    def _on_hires_toggled(self):
        """Re-fetch the current frame at the new resolution."""
        self.viewmodel.set_high_res(self.hires_checkbox.isChecked())
        
    def _on_frame_changed(self):
        """Update the displayed pixmap and slider labels when the frame changes."""
        # Update labels
        self.z_label.setText(f"Z: {self.viewmodel.current_z + 1}/{self.viewmodel.max_z}")
        self.t_label.setText(f"T: {self.viewmodel.current_t + 1}/{self.viewmodel.max_t}")
        
        # Update Image Pixmap
        # In a real app we'd load QImage from the bytes based on format (TIFF, PNG, etc.)
        # Here our mock adapter returns raw bytes like "MOCK_IMAGE_DATA_...". 
        # We will render this text as an image for demonstration.
        data: QByteArray = self.viewmodel.image_data
        if data.isEmpty():
            self.image_label.clear()
            self.image_label.setText("Failed to load frame.")
            return

        # Load real image bytes into a QPixmap (supports JPEG, PNG, etc.)
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            # Scale to fit the label while keeping aspect ratio
            scaled = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setText("Failed to decode image.")
        
    def _on_loading_changed(self, is_loading: bool):
        """Handle loading state visually (e.g., disable sliders during fetch)."""
        if is_loading:
            self.image_label.setText("Loading...")
        else:
            # Re-enable if multidimensional
            self.z_slider.setEnabled(self.viewmodel.max_z > 1)
            self.t_slider.setEnabled(self.viewmodel.max_t > 1)
            
    def _disable_controls(self):
        """Disable sliders and reset labels."""
        self.z_slider.setEnabled(False)
        self.t_slider.setEnabled(False)
        self.z_label.setText("Z: 1/1")
        self.t_label.setText("T: 1/1")
