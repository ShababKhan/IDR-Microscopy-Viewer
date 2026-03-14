"""
Main Application Entry Point

Initializes the PyQt6 application, core components, and main window.

This module sets up the application foundation including:
- QApplication initialization
- Core component instantiation (IDR adapter, cache manager)
- Main window creation
- Application lifecycle management
"""

import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QSplitter,
    QDockWidget
)
from PyQt6.QtCore import Qt

from core.idr_adapter import IDRClientAdapter
from core.cache_manager import ImageCacheManager

from viewmodels.plate_viewmodel import PlateViewModel
from viewmodels.image_viewmodel import ImageViewModel
from viewmodels.qc_viewmodel import QCViewModel
from viewmodels.study_browser_viewmodel import StudyBrowserViewModel
from views.plate_grid_view import PlateGridView
from views.image_detail_view import ImageDetailView
from views.memory_dashboard import MemoryDashboard
from views.qc_dashboard_view import QCDashboardView
from views.study_browser_view import StudyBrowserView
from core.concurrency import ThreadPoolManager


# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window.
    
    This is a stub implementation that holds references to core components.
    The full UI implementation will be added in later phases.
    
    Attributes:
        idr_adapter (IDRClientAdapter): The IDR client adapter
        cache_manager (ImageCacheManager): The image cache manager
    """
    
    def __init__(self, idr_adapter: IDRClientAdapter, cache_manager: ImageCacheManager):
        """
        Initialize the main window.
        
        Args:
            idr_adapter: The IDR client adapter instance
            cache_manager: The image cache manager instance
        """
        super().__init__()
        
        self.idr_adapter = idr_adapter
        self.cache_manager = cache_manager
        
        self._setup_ui()
        self._connect_signals()
        
        logger.info("MainWindow initialized")
    
    def _setup_ui(self):
        """Setup the basic UI structure."""
        self.setWindowTitle("IDR Image Viewer")
        self.setMinimumSize(1100, 700)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout base
        layout = QVBoxLayout(central_widget)
        
        # Use QSplitter to divide the window
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Init Concurrency
        self.thread_pool = ThreadPoolManager()
        
        # Init ViewModels
        self.plate_viewmodel = PlateViewModel(self.idr_adapter, self.thread_pool, self)
        self.image_viewmodel = ImageViewModel(self.idr_adapter, self.thread_pool, self)
        self.qc_viewmodel = QCViewModel(self.plate_viewmodel, self)
        self.study_browser_viewmodel = StudyBrowserViewModel(self.idr_adapter, self.thread_pool, self)
        
        # Map StatusBar up to Main Window
        self.plate_viewmodel.statusChanged.connect(self.statusBar().showMessage)
        self.image_viewmodel.statusChanged.connect(self.statusBar().showMessage)
        self.qc_viewmodel.statusChanged.connect(self.statusBar().showMessage)
        self.study_browser_viewmodel.statusChanged.connect(self.statusBar().showMessage)
        
        # Init Views
        self.plate_grid_view = PlateGridView(self.plate_viewmodel)
        self.image_detail_view = ImageDetailView(self.image_viewmodel)
        self.memory_dashboard = MemoryDashboard(self.cache_manager)
        self.qc_dashboard = QCDashboardView(self.qc_viewmodel)
        self.study_browser_view = StudyBrowserView(self.study_browser_viewmodel)
        
        # Study Browser Dock (left)
        dock = QDockWidget("Study Browser", self)
        dock.setWidget(self.study_browser_view)
        dock.setMinimumWidth(240)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        
        # Centre panel: plate grid + cache dashboard stacked vertically
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(self.plate_grid_view, stretch=3)
        left_layout.addWidget(self.memory_dashboard, stretch=1)
        
        # Add views to top splitter
        top_splitter.addWidget(left_panel)
        top_splitter.addWidget(self.image_detail_view)
        top_splitter.setSizes([600, 400])
        
        # Add everything to main splitter
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.qc_dashboard)
        main_splitter.setSizes([700, 300])
        
        layout.addWidget(main_splitter)
    
    def _connect_signals(self):
        """Connect cross-component signals and slots."""
        
        from PyQt6.QtWidgets import QMessageBox
        
        def show_error(message: str):
            logger.error(f"UI Error Popup: {message}")
            QMessageBox.critical(self, "Error", message)
            
        self.plate_viewmodel.errorOccurred.connect(show_error)
        self.image_viewmodel.errorOccurred.connect(show_error)
        self.qc_viewmodel.errorOccurred.connect(show_error)
        self.study_browser_viewmodel.errorOccurred.connect(show_error)
        
        # Study browser → plate/image loading
        self.study_browser_view.plateSelected.connect(self.plate_viewmodel.load_plate)
        self.study_browser_view.imageSelected.connect(self.image_viewmodel.load_image)
        
        def on_well_selection_changed(well):
            if well and well.has_image:
                image_id = well.metadata.get("image_id")
                if image_id:
                    self.image_viewmodel.load_image(image_id)
            else:
                self.image_viewmodel.clear()
                
        self.plate_viewmodel.wellSelectionChanged.connect(on_well_selection_changed)
    
    def initialize(self):
        """
        Initialize the main window and core components.
        
        This method should be called after the window is shown to
        perform any initialization that requires the event loop.
        """
        logger.info("Initializing MainWindow")
        
        # Connect to IDR API
        if self.idr_adapter.connect():
            logger.info("Successfully connected to IDR API")
            # No hardcoded plate — the user browses via the Study Browser dock
        else:
            logger.warning("Failed to connect to IDR API")
        
        # Log cache statistics
        cache_stats = self.cache_manager.get_stats()
        logger.info(f"Cache statistics: {cache_stats}")
    
    def cleanup(self):
        """
        Cleanup resources before application shutdown.
        
        This method should be called before the application exits to
        ensure proper cleanup of all resources.
        """
        logger.info("Cleaning up MainWindow")
        
        # Disconnect from IDR API
        self.idr_adapter.disconnect()
        
        # Log final cache statistics
        cache_stats = self.cache_manager.get_stats()
        logger.info(f"Final cache statistics: {cache_stats}")


def main():
    """
    Main application entry point.
    
    Initializes the QApplication, core components, and main window.
    """
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("IDR Image Viewer")
    app.setOrganizationName("IDR Project")
    
    logger.info("Starting IDR Image Viewer application")
    
    # Initialize core components
    cache_dir = Path(__file__).parent.parent / ".idr_cache"
    idr_adapter = IDRClientAdapter(
        base_url="https://idr.openmicroscopy.org",
        cache_dir=str(cache_dir),
        max_disk_cache=10 * 1024 * 1024 * 1024,  # 10 GB
        memory_threshold=80.0
    )
    
    cache_manager = idr_adapter.cache_manager
    
    logger.info("Core components initialized")
    
    # Create main window
    main_window = MainWindow(idr_adapter, cache_manager)
    
    # Show window
    main_window.show()
    
    # Initialize after window is shown (requires event loop)
    # Use QTimer to defer initialization
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(100, main_window.initialize)
    
    # Setup cleanup on application quit
    app.aboutToQuit.connect(main_window.cleanup)
    
    # Start event loop
    logger.info("Starting event loop")
    result = app.exec()
    
    logger.info(f"Application exiting with code: {result}")
    sys.exit(result)


if __name__ == "__main__":
    main()
