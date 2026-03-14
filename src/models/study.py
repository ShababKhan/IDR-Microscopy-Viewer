"""
Study / hierarchy models for the IDR Study Browser.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Literal


StudyType = Literal["screen", "project"]


@dataclass
class IDRStudy:
    """Top-level study — either a Screen (HCS) or a Project (non-HCS)."""
    study_id: int
    name: str
    study_type: StudyType
    description: str = ""


@dataclass
class IDRDataset:
    """A dataset inside a Project (non-HCS counterpart to IDRPlate)."""
    dataset_id: int
    name: str
    image_count: int = 0


@dataclass
class IDRDatasetImage:
    """A single image inside a Dataset."""
    image_id: int
    name: str
    thumb_url: str = ""
