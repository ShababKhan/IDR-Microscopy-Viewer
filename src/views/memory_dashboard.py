"""
Memory Dashboard Module

A UI component for visualizing cache hits, evictions, and memory 
size used by the ImageCacheManager.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout
from PyQt6.QtCore import QTimer

from core.cache_manager import ImageCacheManager

class MemoryDashboard(QGroupBox):
    """
    Dashboard for displaying cache statistics and memory usage.
    Polls the CacheManager automatically.
    """
    
    def __init__(self, cache_manager: ImageCacheManager, parent=None):
        super().__init__("Cache Performance Dashboard", parent)
        self.cache_manager = cache_manager
        
        self._setup_ui()
        
        # Start polling timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_stats)
        self.timer.start(1000) # update every 1s
        
        self._update_stats()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Memory stats
        self.lbl_mem_size = QLabel("0")
        self.lbl_mem_hits = QLabel("0")
        self.lbl_mem_misses = QLabel("0")
        self.lbl_mem_evictions = QLabel("0")
        self.lbl_mem_hit_rate = QLabel("0.0%")
        
        form_layout.addRow("RAM Items:", self.lbl_mem_size)
        form_layout.addRow("RAM Hits:", self.lbl_mem_hits)
        form_layout.addRow("RAM Misses:", self.lbl_mem_misses)
        form_layout.addRow("RAM Evictions:", self.lbl_mem_evictions)
        form_layout.addRow("Hit Rate:", self.lbl_mem_hit_rate)
        
        # Disk stats
        self.lbl_disk_count = QLabel("0")
        self.lbl_disk_size = QLabel("0.0 MB")
        self.lbl_disk_usage = QLabel("0.0%")
        
        form_layout.addRow("Disk Items:", self.lbl_disk_count)
        form_layout.addRow("Disk Size:", self.lbl_disk_size)
        form_layout.addRow("Disk Usage:", self.lbl_disk_usage)
        
        layout.addLayout(form_layout)
        
    def _update_stats(self):
        """Fetch and update stats from cache manager."""
        stats = self.cache_manager.get_stats()
        
        if 'memory' in stats:
            m = stats['memory']
            self.lbl_mem_size.setText(str(m.get('size', 0)))
            self.lbl_mem_hits.setText(str(m.get('hits', 0)))
            self.lbl_mem_misses.setText(str(m.get('misses', 0)))
            self.lbl_mem_evictions.setText(str(m.get('evictions', 0)))
            self.lbl_mem_hit_rate.setText(f"{m.get('hit_rate', 0.0) * 100:.1f}%")
            
        if 'disk' in stats:
            d = stats['disk']
            self.lbl_disk_count.setText(str(d.get('count', 0)))
            self.lbl_disk_size.setText(f"{d.get('size_mb', 0.0):.2f} MB")
            self.lbl_disk_usage.setText(f"{d.get('usage_percent', 0.0):.1f}%")
