# IDR Image Viewer

A PyQt6-based Python package for visualizing microscopy images from the Image Data Resource (IDR) API with efficient memory management and lazy loading.

## Overview

This application provides a graphical user interface for browsing and analyzing high-throughput screening (HTS) microscopy data from the IDR. It features:

- **Lazy Loading**: Images are loaded on-demand to manage memory efficiently
- **Tiered Caching**: Memory-aware LRU cache with disk persistence
- **MVVM Architecture**: Clean separation of concerns with Model-View-ViewModel pattern
- **Interactive Visualization**: Dynamic plate grid views for 96/384/1536-well plates
- **Quality Control Metrics**: Built-in visualization of Z-score, Z-prime, and other QC metrics

## Project Structure

```
src/
├── __init__.py              # Package initialization
├── main.py                  # Application entry point
├── models/                  # Data models (IDRScreen, IDRPlate, IDRImage, etc.)
├── viewmodels/              # MVVM ViewModels
│   └── base_viewmodel.py    # Base ViewModel with signals
├── views/                   # UI components (PlateGridView, ImageDetailView, etc.)
├── core/                    # Core components
│   ├── cache_manager.py     # Memory-aware LRU cache and tiered caching
│   └── idr_adapter.py       # IDR API client with caching
└── utils/                   # Utility functions
```

## Installation

### Requirements

```bash
pip install PyQt6>=6.4.0
pip install pyqtgraph>=0.13.0
pip install Pillow>=10.0.0
pip install numpy>=1.24.0
pip install psutil>=5.9.0
pip install requests>=2.28.0
pip install pandas>=2.0.0
```

### Running the Application

```bash
cd src
python main.py
```

## Architecture

### MVVM Pattern

The application follows the Model-View-ViewModel (MVVM) architectural pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                        VIEW LAYER                           │
│  PlateGridView | ImageDetailView | MetadataPanel | Controls │
└─────────────────────────────────────────────────────────────┘
                              ↕ (Signals/Slots)
┌─────────────────────────────────────────────────────────────┐
│                     VIEWMODEL LAYER                         │
│  PlateViewModel | ImageViewModel | QCViewModel              │
└─────────────────────────────────────────────────────────────┘
                              ↕ (Direct Access)
┌─────────────────────────────────────────────────────────────┐
│                      MODEL LAYER                            │
│  IDRClient | IDRScreen | IDRPlate | IDRImage | Cache        │
└─────────────────────────────────────────────────────────────┘
```

### Caching Strategy

The application implements a three-tier caching strategy:

1. **Memory Cache** (Fastest): LRU cache with memory-aware eviction
2. **Disk Cache** (Persistent): Serialized image data with TTL
3. **API Fetch** (Slowest): Direct IDR API calls

### Memory Management

- **Memory-Aware LRU Cache**: Monitors system memory using `psutil`
- **Automatic Eviction**: Evicts least recently used items when memory exceeds 80%
- **Thread-Safe Operations**: All cache operations use locks for concurrent access
- **Configurable Thresholds**: Memory and disk cache sizes are configurable

## Core Components

### MemoryAwareLRUCache

A thread-safe LRU cache that monitors system memory usage:

```python
from core.cache_manager import MemoryAwareLRUCache

cache = MemoryAwareLRUCache(max_memory_threshold=80.0)
cache.put("key", data)
data = cache.get("key")
stats = cache.get_stats()
```

### ImageCacheManager

Tiered caching manager for microscopy images:

```python
from core.cache_manager import ImageCacheManager

cache_manager = ImageCacheManager(
    disk_cache_dir="~/.idr_cache",
    max_disk_cache_size=10 * 1024 * 1024 * 1024,  # 10 GB
    memory_threshold=80.0
)

# Get image with automatic tiered fallback
image_data = cache_manager.get("image_12345", fetch_func=lambda: fetch_from_api())
```

### IDRClientAdapter

Adapter for IDR API with integrated caching:

```python
from core.idr_adapter import IDRClientAdapter

adapter = IDRClientAdapter(
    base_url="https://idr.openmicroscopy.org",
    cache_dir="~/.idr_cache"
)

adapter.connect()
screen = adapter.get_screen(screen_id=102)
plate = adapter.get_plate(plate_id=1)
image = adapter.get_image(image_id=122770)
adapter.disconnect()
```

## Data Models

### Biological Context

The application is designed for High-Throughput Screening (HTS) data:

- **Plate Formats**: 96-well (8×12), 384-well (16×24), 1536-well (32×48)
- **QC Metrics**: Z-score, Z-prime, coefficient of variation, signal-to-noise
- **Biological Metadata**: Organism, Gene Symbol, Cell Type, Treatment, Phenotype

### Model Classes

- **IDRScreen**: Top-level study container with biological metadata
- **IDRPlate**: HTS plate with grid structure and QC metrics
- **IDRWell**: Individual well with spatial coordinates
- **IDRImage**: Image with lazy loading capability
- **BiologicalMetadata**: Structured biological metadata
- **QCMetrics**: Quality control metrics

## IDR API Integration

### Authentication

The IDR API uses session-based authentication:

```python
import requests

session = requests.Session()
response = session.get("https://idr.openmicroscopy.org/webclient/?experimenter=-1")
```

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `/webclient/api/annotations/?type=map&type={id}` | Get map annotations |
| `/webclient/api/plates/?id={screen_id}` | Get plates in a screen |
| `/webgateway/plate/{plate_id}/{field}/` | Get plate grid |
| `/webclient/imgData/{image_id}/` | Get image details |
| `/webgateway/render_image/{image_id}/{z}/{t}/` | Render image |
| `/webclient/render_thumbnail/{image_id}/` | Get thumbnail |
| `/searchengine/api/v1/resources/{type}/search/` | Search by key-value |

### Search Engine API

The IDR provides a JSON-based Search Engine API:

```python
# Simple query
GET /searchengine/api/v1/resources/image/search/?key=Gene%20Symbol&value=HBB

# Complex query
POST /searchengine/api/v1/resources/submitquery/
{
    "and_filters": [
        {"key": "Organism", "value": "Homo sapiens"},
        {"key": "Gene Symbol", "value": "HBB"}
    ]
}
```

## Development Roadmap

### Phase 1: Core Architecture 
- [x] Memory-aware LRU cache implementation
- [x] Tiered image cache manager
- [x] IDR client adapter with caching
- [x] MVVM base ViewModel classes
- [x] Main application entry point

### Phase 2: Plate Grid View (Next)
- [x] PlateGridView with QGraphicsView
- [x] WellItem with interactive features
- [x] Dynamic grid layout for 96/384/1536 wells
- [x] Row/column label rendering

### Phase 3: Image Detail View
- [x] ImageDetailView with multi-dimensional support
- [x] Z-stack navigation
- [x] Timepoint navigation
- [x] Image transformations (zoom, contrast)

### Phase 4: Concurrency & Performance
- [x] Thread pool for async operations
- [x] Lazy loading optimization
- [x] Cache performance tuning
- [x] Memory monitoring dashboard

### Phase 5: QC Metrics & Polish
- [x] QC metrics visualization
- [x] Charts and statistics
- [x] Error handling improvements
- [x] User documentation
- [ ] Removal of QC metrics

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Plate Grid Render Time | < 100ms | 1536-well plate |
| Image Load Time | < 500ms | 5MB image from cache |
| API Response Time | < 2s | Screen/plate metadata |
| Memory Usage | < 1GB | Typical session |
| UI Responsiveness | < 16ms | 60 FPS rendering |


## References

- [IDR API Documentation](https://idr.openmicroscopy.org/about/api.html)
- [OMERO WebGateway Documentation](https://omero.readthedocs.io/en/stable/developers/Web/WebGateway.html)
- [OMERO Search Engine](https://github.com/ome/omero_search_engine)
- [scikit-image](https://scikit-image.org/) - Biological image analysis library

## Version

Current version: **0.1.0** 
