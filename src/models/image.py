"""
Image models for the IDR Viewer.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class IDRImage:
    """Represents a microscopy image, potentially multidimensional."""
    image_id: int
    name: str = ""
    size_x: int = 0
    size_y: int = 0
    size_z: int = 1
    size_t: int = 1
    size_c: int = 1
    
    # physical details mapping map annotations or pixel properties
    physical_size_x: Optional[float] = None
    physical_size_y: Optional[float] = None
    physical_size_z: Optional[float] = None
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_api_dict(cls, data: Dict[str, Any]) -> 'IDRImage':
        """Create an IDRImage instance from API dictionary."""
        return cls(
            image_id=data.get('id', -1),
            name=data.get('name', f"Image {data.get('id', 'Unknown')}"),
            size_x=data.get('sizeX', 512),
            size_y=data.get('sizeY', 512),
            size_z=data.get('sizeZ', 1),
            size_t=data.get('sizeT', 1),
            size_c=data.get('sizeC', 1),
        )
        
    @property
    def is_multidimensional(self) -> bool:
        """Returns True if the image has more than one Z-slice or Timepoint."""
        return self.size_z > 1 or self.size_t > 1
