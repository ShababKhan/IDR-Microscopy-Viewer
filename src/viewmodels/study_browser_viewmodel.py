"""
Study Browser ViewModel

Drives the IDR hierarchy tree: discovers study type and lazily exposes
plates/datasets on demand.
"""
import logging
from typing import Optional, List, Any, Dict

from PyQt6.QtCore import pyqtSignal, QObject

from .base_viewmodel import ViewModel
from models.study import IDRStudy, IDRDataset, IDRDatasetImage
from core.idr_adapter import IDRClientAdapter
from core.concurrency import ThreadPoolManager

logger = logging.getLogger(__name__)


class StudyBrowserViewModel(ViewModel):
    """
    ViewModel that backs the Study Browser tree view.

    It exposes async loaders for each level of the OMERO hierarchy:
      Screen  → Plates
      Project → Datasets → Images
    """

    studyLoaded      = pyqtSignal(object)    # emits IDRStudy
    platesLoaded     = pyqtSignal(list)      # emits list[dict]
    datasetsLoaded   = pyqtSignal(list)      # emits list[dict]
    datasetImagesLoaded = pyqtSignal(int, list)  # dataset_id, list[dict]

    def __init__(
        self,
        idr_adapter: IDRClientAdapter,
        thread_pool: ThreadPoolManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self._adapter = idr_adapter
        self._pool = thread_pool

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_study(self, study_id: int):
        """Detect whether study_id is a Screen or Project, emit studyLoaded."""
        self.begin_operation(f"Looking up study {study_id}…")

        def fetch():
            kind, name, desc = self._adapter.get_study_type(study_id)
            if kind is None:
                raise ValueError(f"No screen or project found with ID {study_id}.")
            return IDRStudy(study_id=study_id, name=name or f"Study {study_id}",
                            study_type=kind, description=desc or "")

        def on_success(study: IDRStudy):
            self.end_operation(success=True, status_message=f"Loaded {study.study_type}: {study.name}")
            self.studyLoaded.emit(study)

        def on_error(e_tuple):
            e, _ = e_tuple
            self.handle_error(e, "Study lookup failed")

        self._pool.execute(fetch, on_result=on_success, on_error=on_error)

    def load_plates(self, screen_id: int):
        """Fetch all plates for a screen."""
        self.begin_operation(f"Loading plates for screen {screen_id}…")

        def fetch():
            return self._adapter.get_screen_plates(screen_id)

        def on_success(plates):
            self.end_operation(success=True, status_message=f"{len(plates)} plate(s) found")
            self.platesLoaded.emit(plates)

        def on_error(e_tuple):
            e, _ = e_tuple
            self.handle_error(e, "Failed to load plates")

        self._pool.execute(fetch, on_result=on_success, on_error=on_error)

    def load_datasets(self, project_id: int):
        """Fetch all datasets for a project."""
        self.begin_operation(f"Loading datasets for project {project_id}…")

        def fetch():
            return self._adapter.get_project_datasets(project_id)

        def on_success(datasets):
            self.end_operation(success=True, status_message=f"{len(datasets)} dataset(s) found")
            self.datasetsLoaded.emit(datasets)

        def on_error(e_tuple):
            e, _ = e_tuple
            self.handle_error(e, "Failed to load datasets")

        self._pool.execute(fetch, on_result=on_success, on_error=on_error)

    def load_dataset_images(self, dataset_id: int):
        """Fetch all images inside a dataset."""
        self.begin_operation(f"Loading images for dataset {dataset_id}…")

        def fetch():
            return self._adapter.get_dataset_images(dataset_id)

        def on_success(images):
            self.end_operation(success=True, status_message=f"{len(images)} image(s) in dataset")
            self.datasetImagesLoaded.emit(dataset_id, images)

        def on_error(e_tuple):
            e, _ = e_tuple
            self.handle_error(e, "Failed to load dataset images")

        self._pool.execute(fetch, on_result=on_success, on_error=on_error)
