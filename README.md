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

### Using Docker (Recommended) - Works on All Platforms

Docker installation works on **Windows**, **macOS**, and **Linux**.

#### Prerequisites
- **Windows**: Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- **macOS**: Install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- **Linux**: Install [Docker Engine](https://docs.docker.com/engine/install/) and Docker Compose

#### Installation Steps

1. **Clone the repository**:

   **Windows (PowerShell/Command Prompt)**:
   ```powershell
   git clone https://github.com/yourusername/AutoDroneSegment.git
   cd AutoDroneSegment
   ```

   **macOS/Linux**:
   ```bash
   git clone https://github.com/yourusername/AutoDroneSegment.git
   cd AutoDroneSegment
   ```

2. **Start the services**:

   **Docker Desktop (newer versions)**:
   ```bash
   docker compose up -d
   ```

   **Older Docker versions or standalone docker-compose**:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**:
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

4. **Stop the services**:

   **Docker Desktop (newer versions)**:
   ```bash
   docker compose down
   ```

   **Older Docker versions**:
   ```bash
   docker-compose down
   ```

> **Windows Notes**:
> - Use `docker compose` (no hyphen) on newer Docker Desktop versions
> - If you encounter path issues with Docker volumes, ensure Docker Desktop has access to your drive in Settings > Resources > File Sharing
> - Make sure Docker Desktop is running (check system tray for whale icon)

#### Docker Troubleshooting

**"docker-compose is not recognized" (Windows)**:
```powershell
# Use the newer command format (no hyphen)
docker compose up -d

# If that doesn't work, check Docker installation
docker --version
docker compose version

# Make sure Docker Desktop is running
# Look for the whale icon in your system tray
```

**Docker Desktop not installed**:
- Download from: https://docs.docker.com/desktop/install/windows-install/
- Requires Windows 10/11 with WSL 2
- After installation, restart your computer

**WSL 2 not enabled (Windows)**:
```powershell
# Run in PowerShell as Administrator
wsl --install
wsl --set-default-version 2

# Restart your computer
```

**Docker daemon not running**:
- Windows: Start Docker Desktop from Start menu
- Check system tray for Docker whale icon
- If red, Docker is not running - click to start

**Port conflicts (address already in use)**:
```powershell
# Check what's using port 80 or 8000
netstat -ano | findstr :80
netstat -ano | findstr :8000

# Change ports in docker-compose.yml if needed
# For example, change "80:80" to "8080:80" for frontend
```

---

### Manual Installation

<details>
<summary><b>🐧 Linux (Ubuntu/Debian)</b></summary>

#### Backend Setup

1. **Install GDAL**:
   ```bash
   sudo apt-get update
   sudo apt-get install gdal-bin libgdal-dev python3-gdal python3-pip
   ```

2. **Install Python dependencies**:
   ```bash
   cd backend
   pip3 install -r requirements.txt
   ```

3. **Set up PostgreSQL with PostGIS**:
   ```bash
   # Install PostgreSQL and PostGIS
   sudo apt-get install postgresql postgresql-contrib postgis

   # Start PostgreSQL service
   sudo systemctl start postgresql

   # Create database
   sudo -u postgres createdb drone_segments
   sudo -u postgres psql drone_segments -c "CREATE EXTENSION postgis;"

   # Run schema
   sudo -u postgres psql drone_segments -f database_schema.sql
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   nano .env  # Edit with your database credentials
   ```

5. **Run the backend**:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. **Install Node.js**:
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs
   ```

2. **Install dependencies and run**:
   ```bash
   cd frontend
   npm install
   npm start
   ```

</details>

<details>
<summary><b>🍎 macOS</b></summary>

#### Backend Setup

1. **Install GDAL**:
   ```bash
   # Install Homebrew if not already installed
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

   # Install GDAL
   brew install gdal
   ```

2. **Install Python dependencies**:
   ```bash
   cd backend
   pip3 install -r requirements.txt
   ```

3. **Set up PostgreSQL with PostGIS**:
   ```bash
   # Install PostgreSQL
   brew install postgresql postgis

   # Start PostgreSQL service
   brew services start postgresql

   # Create database
   createdb drone_segments
   psql drone_segments -c "CREATE EXTENSION postgis;"

   # Run schema
   psql drone_segments -f database_schema.sql
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   nano .env  # Edit with your database credentials
   ```

5. **Run the backend**:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. **Install Node.js**:
   ```bash
   brew install node
   ```

2. **Install dependencies and run**:
   ```bash
   cd frontend
   npm install
   npm start
   ```

</details>

<details>
<summary><b>🪟 Windows</b></summary>

#### Prerequisites

1. **Install Python 3.10+**:
   - Download from [python.org](https://www.python.org/downloads/windows/)
   - ✅ Check "Add Python to PATH" during installation

2. **Install Node.js 18+**:
   - Download from [nodejs.org](https://nodejs.org/)

3. **Install PostgreSQL with PostGIS**:
   - Download [PostgreSQL 15](https://www.postgresql.org/download/windows/)
   - During installation, select PostGIS in Stack Builder

#### Backend Setup

1. **Install GDAL** (Choose one method):

   **Method A: Using Conda (Recommended for Windows)**:
   ```powershell
   # Install Miniconda
   # Download from: https://docs.conda.io/en/latest/miniconda.html

   # Create conda environment
   conda create -n drone_segments python=3.10
   conda activate drone_segments

   # Install GDAL
   conda install -c conda-forge gdal
   ```

   **Method B: Using OSGeo4W**:
   ```powershell
   # Download OSGeo4W installer from: https://trac.osgeo.org/osgeo4w/
   # During installation, select: gdal, python3-gdal

   # Add to PATH (in PowerShell as Administrator):
   $env:Path += ";C:\OSGeo4W64\bin"
   [System.Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::Machine)
   ```

2. **Install Python dependencies**:
   ```powershell
   cd backend
   pip install -r requirements.txt
   ```

   If you get GDAL errors:
   ```powershell
   # Find your GDAL version
   gdalinfo --version

   # Install matching GDAL Python bindings
   pip install GDAL==[version]
   ```

3. **Set up PostgreSQL with PostGIS**:
   ```powershell
   # Using psql (adjust path if needed)
   # Add PostgreSQL bin to PATH or use full path

   # Create database
   & "C:\Program Files\PostgreSQL\15\bin\createdb.exe" -U postgres drone_segments

   # Enable PostGIS
   & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -d drone_segments -c "CREATE EXTENSION postgis;"

   # Run schema
   & "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -d drone_segments -f database_schema.sql
   ```

4. **Configure environment**:
   ```powershell
   copy .env.example .env
   notepad .env  # Edit with your database credentials
   ```

   Update the DATABASE_URL in `.env`:
   ```
   DATABASE_URL=postgresql://postgres:your_password@localhost:5432/drone_segments
   ```

5. **Run the backend**:
   ```powershell
   cd backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. **Install dependencies and run**:
   ```powershell
   cd frontend
   npm install
   npm start
   ```

#### Troubleshooting Windows Issues

**GDAL Import Error**:
```powershell
# Make sure GDAL_DATA environment variable is set
$env:GDAL_DATA = "C:\OSGeo4W64\share\gdal"
# Or for Conda:
$env:GDAL_DATA = "$env:CONDA_PREFIX\Library\share\gdal"
```

**PostgreSQL Connection Error**:
- Ensure PostgreSQL service is running (check Services app)
- Verify password in `.env` matches your PostgreSQL installation
- Check `pg_hba.conf` allows local connections

**Port Already in Use**:
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID [PID] /F
```

</details>

---

### Access the Application

After installation (Docker or manual):
- **Frontend**: http://localhost (Docker) or http://localhost:3000 (manual)
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

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
