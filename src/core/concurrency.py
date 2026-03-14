"""
Concurrency core module.

Provides a robust threading wrapper utilizing QThreadPool and QRunnable
to offload heavy operations (API and Disk I/O) from the main UI thread.
"""

import traceback
import sys
from typing import Callable, Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    
    Supported signals:
    - finished: No data, emitted when worker is done
    - error: `tuple(Exception, str)` emitted if an error occurred
    - result: `object` generic data returned from execution
    - progress: `int` indicating % progress
    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    """
    Runnable worker thread setup to run a generic function in the background.
    """
    
    def __init__(self, fn: Callable, *args, **kwargs):
        """
        Initialize the worker.
        
        Args:
            fn: The callback function to run on the thread.
            args: Arguments to pass to fn.
            kwargs: Keyword arguments to pass to fn.
        """
        super().__init__()
        
        # Store parameters
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        
        # Add the callback to our kwargs if the function needs reporting
        # self.kwargs['progress_callback'] = self.signals.progress
        
    @pyqtSlot()
    def run(self):
        """
        Execute the function. Will automatically emit signals appropriately.
        """
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((e, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class ThreadPoolManager:
    """
    Manager for executing concurrent tasks cleanly on a shared global pool.
    """
    
    def __init__(self):
        self.threadpool = QThreadPool.globalInstance()
        # Optional: constrain maximum thread count depending on system/preferences
        # self.threadpool.setMaxThreadCount(4)
        
    def execute(self, 
                fn: Callable, 
                args: tuple = (), 
                kwargs: dict = None, 
                on_result: Optional[Callable[[Any], None]] = None, 
                on_error: Optional[Callable[[tuple], None]] = None,
                on_finished: Optional[Callable[[], None]] = None) -> None:
        """
        Creates a Worker for `fn(*args, **kwargs)` and schedules it in the ThreadPool.
        
        Args:
            fn: Function to execute in thread.
            args: Positional limits to `fn`.
            kwargs: Keyword args to `fn`.
            on_result: Slot called when `fn` completes successfully.
            on_error: Slot called when `fn` raises an Exception.
            on_finished: Slot called when `fn` is completed regardless of success/fail.
        """
        if kwargs is None:
            kwargs = {}
            
        worker = Worker(fn, *args, **kwargs)
        
        # Connect signals
        if on_result:
            worker.signals.result.connect(on_result)
        if on_error:
            worker.signals.error.connect(on_error)
        if on_finished:
            worker.signals.finished.connect(on_finished)
            
        # Start
        self.threadpool.start(worker)
