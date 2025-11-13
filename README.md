# AutoDroneSegment

**Drone Search Segment Planning Tool**

A comprehensive tool to automatically divide search areas into optimal drone search segments for Search and Rescue (SAR) operations.

---

## 🚁 Features

- **Interactive Map Interface**: Draw search areas directly on a Leaflet map
- **DEM-Based Viewshed Analysis**: Uses Digital Elevation Models and vegetation data for accurate visibility calculations
- **VLOS Compliance**: Ensures each segment is fully visible from a single vantage point under maximum Visual Line of Sight constraints
- **Access Filtering**: Supports road, trail, off-road, and anywhere access restrictions
- **Greedy Max-Coverage Algorithm**: Minimizes the number of segments while ensuring full coverage
- **KML/KMZ Export**: Export segments for field operations (compatible with Google Earth, GPS devices)
- **GeoJSON API**: Programmatic access to segment data
- **Docker Deployment**: Easy setup and deployment

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Using Docker (Recommended)](#using-docker-recommended)
  - [Manual Installation](#manual-installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

---

## 🏗 Architecture

```
┌──────────────────────────────────────────┐
│          React + Leaflet Frontend        │
│   • Draw polygon                         │
│   • Upload DEM                           │
│   • Display segments                     │
└──────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────┐
│           FastAPI Backend                │
│  POST /api/v1/projects                  │
│  POST /api/v1/projects/{id}/calculate   │
│  GET  /api/v1/projects/{id}/segments    │
│  GET  /api/v1/projects/{id}/export-kml  │
└──────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────┐
│          Processing Pipeline             │
│ 1. CRS Management (UTM projection)      │
│ 2. DEM Processing (GDAL)                │
│ 3. Grid Generation                       │
│ 4. Viewshed Calculation                 │
│ 5. Access Filtering                      │
│ 6. Greedy Segment Generation             │
│ 7. Polygon Construction                  │
│ 8. KML Export                            │
└──────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────┐
│        PostgreSQL + PostGIS              │
└──────────────────────────────────────────┘
```

---

## 📦 Requirements

### System Requirements

- Docker and Docker Compose (recommended)
- **OR** for manual installation:
  - Python 3.10+
  - Node.js 18+
  - PostgreSQL 15+ with PostGIS 3.3+
  - GDAL 3.8+

### Data Requirements

- **DEM (Digital Elevation Model)**: GeoTIFF format
- **Vegetation Height** (optional): GeoTIFF format
- **Roads/Trails** (optional): Shapefile or GeoJSON

---

## 🚀 Installation

### Using Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/AutoDroneSegment.git
   cd AutoDroneSegment
   ```

2. **Start the services**:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**:
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

4. **Stop the services**:
   ```bash
   docker-compose down
   ```

### Manual Installation

#### Backend Setup

1. **Install GDAL**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install gdal-bin libgdal-dev python3-gdal

   # macOS
   brew install gdal
   ```

2. **Install Python dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL with PostGIS**:
   ```bash
   # Create database
   createdb drone_segments
   psql drone_segments -c "CREATE EXTENSION postgis;"

   # Run schema
   psql drone_segments -f database_schema.sql
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Run the backend**:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. **Install Node dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**:
   ```bash
   npm start
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

---

## 💻 Usage

### Basic Workflow

1. **Draw Search Area**:
   - Use the polygon drawing tool on the map
   - Click around the perimeter to create your search boundary
   - Double-click to complete

2. **Configure Parameters**:
   - **Project Name**: Name for your mission
   - **Drone Altitude**: Height above ground level (meters)
   - **Segment Size**: Preferred size for each segment (acres)
   - **Max VLOS**: Maximum Visual Line of Sight distance (meters)
   - **Access Types**: Choose road, trail, off-road, or anywhere
   - **Grid Spacing**: Distance between candidate vantage points (meters)

3. **Upload DEM**:
   - Click "Choose File" under DEM Files
   - Select your GeoTIFF DEM file
   - Optionally upload a vegetation height raster

4. **Calculate Segments**:
   - Click "Calculate Segments"
   - Wait for processing to complete (may take several minutes)

5. **Review Results**:
   - Segments will appear on the map in different colors
   - Click on segments to see details
   - Click on markers to see launch point information

6. **Export to KML**:
   - Click "Export KML" to download
   - Use the KML file in Google Earth or GPS devices

### Parameter Guidelines

| Parameter | Typical Range | Notes |
|-----------|--------------|-------|
| Drone Altitude | 100-150m (300-400ft) | FAA limit is 400ft AGL |
| Segment Size | 50-200 acres | Depends on terrain and mission |
| Max VLOS | 300-1000m | Regulatory and practical limits |
| Grid Spacing | 50-100m | Smaller = more candidates, longer processing |
| Access Deviation | 25-100m | Buffer around roads/trails |

---

## 📚 API Documentation

### Create Project

```http
POST /api/v1/projects
Content-Type: application/json

{
  "name": "Search Mission Alpha",
  "search_polygon": {
    "type": "Polygon",
    "coordinates": [[...]]
  },
  "drone_agl_altitude": 120,
  "preferred_segment_size_acres": 100,
  "max_vlos_m": 500,
  "access_types": ["road", "trail"],
  "access_deviation_m": 50,
  "grid_spacing_m": 50
}
```

### Upload DEM

```http
POST /api/v1/projects/{project_id}/upload-dem
Content-Type: multipart/form-data

dem_file: <file>
vegetation_file: <file> (optional)
```

### Calculate Segments

```http
POST /api/v1/projects/{project_id}/calculate
```

### Get Segments

```http
GET /api/v1/projects/{project_id}/segments

Response: GeoJSON FeatureCollection
```

### Export KML

```http
GET /api/v1/projects/{project_id}/export-kml

Response: KML file download
```

For full API documentation, visit: http://localhost:8000/docs

---

## 🔧 Development

### Project Structure

```
AutoDroneSegment/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── core/          # Core processing modules
│   │   ├── models/        # Data models
│   │   └── main.py        # FastAPI app
│   ├── tests/             # Unit tests
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/    # React components
│   │   └── services/      # API client
│   └── package.json
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── data/                  # Data directory
├── exports/               # KML exports
└── docker-compose.yml
```

### Core Algorithms

1. **CRS Manager** (`backend/app/core/crs_manager.py`):
   - Determines appropriate UTM zone
   - Handles coordinate transformations
   - Calculates areas in acres

2. **DEM Processor** (`backend/app/core/dem_processor.py`):
   - Clips DEM to search area
   - Reprojects to UTM
   - Integrates vegetation height
   - Builds cell index

3. **Grid Generator** (`backend/app/core/grid_generator.py`):
   - Creates regular grid of candidate points
   - Filters points inside polygon
   - Supports adaptive spacing

4. **Viewshed Engine** (`backend/app/core/viewshed_engine.py`):
   - Uses GDAL ViewshedGenerate
   - Calculates visibility from each point
   - Returns visible cell sets

5. **Access Filter** (`backend/app/core/access_filter.py`):
   - Loads road/trail data
   - Creates access buffers
   - Classifies points by access type

6. **Segment Generator** (`backend/app/core/segment_generator.py`):
   - Implements greedy max-coverage algorithm
   - Selects optimal vantage points
   - Minimizes number of segments

7. **Polygon Builder** (`backend/app/core/polygon_builder.py`):
   - Converts cell sets to polygons
   - Clips to search boundary
   - Validates coverage

---

## 🧪 Testing

### Run Backend Tests

```bash
cd backend
pytest tests/
```

### Run Frontend Tests

```bash
cd frontend
npm test
```

### Test Coverage

```bash
# Backend
cd backend
pytest --cov=app tests/

# Frontend
cd frontend
npm test -- --coverage
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Python: Follow PEP 8
- JavaScript: Follow Airbnb style guide
- Use meaningful variable names
- Add docstrings and comments

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built for Search and Rescue operations
- Uses GDAL for geospatial processing
- Leaflet for mapping
- FastAPI for API backend
- React for frontend

---

## 📞 Support

For questions or issues:
- Open an issue on GitHub
- Email: support@example.com

---

## 🗺 Example

### Input:
- Search area polygon
- DEM covering the region
- Parameters: 120m altitude, 100 acres/segment, 500m VLOS

### Output:
- 8 optimized segments
- Each fully visible from its launch point
- 98.5% coverage of search area
- KML file for field deployment

---

## 🔮 Future Enhancements

- [ ] Real-time VLOS preview
- [ ] Multi-drone mission optimization
- [ ] Auto-generated flight paths
- [ ] 3D Cesium terrain viewer
- [ ] Machine learning for vantage point prediction
- [ ] Mobile app for field use
- [ ] Integration with drone flight planning software

---

**Built with ❤️ for Search and Rescue teams**
