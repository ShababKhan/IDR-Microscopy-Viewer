"""
Base ViewModel Module

Provides the foundation for all ViewModels in the MVVM architecture.

Implements standard signals for error handling, loading states, and
property change notifications following Qt's signal/slot pattern.
"""

from typing import Any, Optional
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, pyqtProperty


class LoadingState(Enum):
    """Enumeration for loading states."""
    IDLE = "idle"
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"


class ViewModel(QObject):
    """
    Base ViewModel class for MVVM architecture.
    
    All ViewModels should inherit from this class to ensure consistent
    signal handling and state management across the application.
    
    This base class provides:
    - Standard error handling signals
    - Loading state management
    - Property change notifications
    - Thread-safe state updates
    
    Signals:
        errorOccurred(str): Emitted when an error occurs
        loadingChanged(bool): Emitted when loading state changes
        statusChanged(str): Emitted when status message changes
    """
    
    # Standard signals for error handling and loading states
    errorOccurred = pyqtSignal(str)
    loadingChanged = pyqtSignal(bool)
    statusChanged = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize the base ViewModel.
        
        Args:
            parent: Optional parent QObject
        """
        super().__init__(parent)
        
        self._loading = False
        self._status = ""
        self._error_message = ""
        self._loading_state = LoadingState.IDLE
    
    # Property: loading
    def get_loading(self) -> bool:
        """Get the loading state."""
        return self._loading
    
    def set_loading(self, loading: bool) -> None:
        """
        Set the loading state.
        
        Args:
            loading: True if loading, False otherwise
        """
        if self._loading != loading:
            self._loading = loading
            self.loadingChanged.emit(loading)
            
            # Update loading state
            if loading:
                self._loading_state = LoadingState.LOADING
            else:
                self._loading_state = LoadingState.IDLE
    
    loading = pyqtProperty(bool, get_loading, set_loading, notify=loadingChanged)
    
    # Property: status
    def get_status(self) -> str:
        """Get the current status message."""
        return self._status
    
    def set_status(self, status: str) -> None:
        """
        Set the status message.
        
        Args:
            status: Status message to display
        """
        if self._status != status:
            self._status = status
            self.statusChanged.emit(status)
    
    status = pyqtProperty(str, get_status, set_status, notify=statusChanged)
    
    # Property: errorMessage
    def get_error_message(self) -> str:
        """Get the last error message."""
        return self._error_message
    
    def set_error_message(self, message: str) -> None:
        """
        Set the error message.
        
        Args:
            message: Error message
        """
        if self._error_message != message:
            self._error_message = message
            if message:
                self.errorOccurred.emit(message)
    
    errorMessage = pyqtProperty(str, get_error_message, set_error_message)
    
    # Property: loadingState
    def get_loading_state(self) -> LoadingState:
        """Get the current loading state."""
        return self._loading_state
    
    def set_loading_state(self, state: LoadingState) -> None:
        """
        Set the loading state.
        
        Args:
            state: LoadingState enum value
        """
        if self._loading_state != state:
            self._loading_state = state
            self.set_loading(state == LoadingState.LOADING)
            
            if state == LoadingState.ERROR:
                self.set_status("Error occurred")
            elif state == LoadingState.SUCCESS:
                self.set_status("Operation completed successfully")
            elif state == LoadingState.LOADING:
                self.set_status("Loading...")
            else:
                self.set_status("")
    
    loadingState = pyqtProperty(LoadingState, get_loading_state, set_loading_state)
    
    def handle_error(self, error: Exception, context: str = "") -> None:
        """
        Handle an error with consistent error reporting.
        
        Args:
            error: The exception that occurred
            context: Optional context string for better error messages
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.set_error_message(error_msg)
        self.set_loading_state(LoadingState.ERROR)
        
        # Log the error
        import logging
        logger = logging.getLogger(self.__class__.__name__)
        logger.error(error_msg, exc_info=True)
    
    def clear_error(self) -> None:
        """Clear the current error state."""
        self.set_error_message("")
        if self._loading_state == LoadingState.ERROR:
            self.set_loading_state(LoadingState.IDLE)
    
    def begin_operation(self, status_message: str = "Loading...") -> None:
        """
        Begin an async operation.
        
        Args:
            status_message: Status message to display
        """
        self.clear_error()
        self.set_status(status_message)
        self.set_loading_state(LoadingState.LOADING)
    
    def end_operation(self, success: bool = True, status_message: str = "") -> None:
        """
        End an async operation.
        
        Args:
            success: Whether the operation succeeded
            status_message: Optional status message
        """
        if success:
            self.set_loading_state(LoadingState.SUCCESS)
            if status_message:
                self.set_status(status_message)
        else:
            self.set_loading_state(LoadingState.ERROR)
            if status_message:
                self.set_status(status_message)
    
    def cleanup(self) -> None:
        """
        Cleanup resources.
        
        Override this method in subclasses to release resources.
        """
        pass
