"""
Quality Control Metrics Module

Defines domain models for tracking compound efficacy and well variances.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class QCMetrics:
    """Quality control metrics for a biological well."""
    z_score: Optional[float] = None
    z_prime: Optional[float] = None
    cv: Optional[float] = None  # Coefficient of variation
    snr: Optional[float] = None # Signal to noise ratio
    
    is_positive_control: bool = False
    is_negative_control: bool = False
    
    @classmethod
    def from_api_dict(cls, data: Dict[str, Any]) -> 'QCMetrics':
        """Create a QCMetrics instance from an arbitrary API dictionary."""
        return cls(
            z_score=data.get("z_score"),
            z_prime=data.get("z_prime"),
            cv=data.get("cv"),
            snr=data.get("snr"),
            is_positive_control=data.get("is_positive_control", False),
            is_negative_control=data.get("is_negative_control", False)
        )
