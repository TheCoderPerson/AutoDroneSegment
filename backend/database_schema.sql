-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Original polygon in WGS84 for display
    search_polygon GEOMETRY(Polygon, 4326),

    -- Projected polygon in UTM for calculations (dynamically determined)
    search_polygon_proj GEOMETRY(Polygon, 32600),  -- Example UTM zone
    proj_epsg INTEGER,  -- Store the actual EPSG code used

    -- Drone parameters
    drone_agl_altitude FLOAT NOT NULL,  -- in meters
    preferred_segment_size_acres FLOAT NOT NULL,
    max_vlos_m FLOAT NOT NULL,

    -- Access configuration
    access_types TEXT[] NOT NULL,  -- ['road', 'trail', 'off_road', 'anywhere']
    access_deviation_m FLOAT DEFAULT 50.0,

    -- Grid configuration
    grid_spacing_m FLOAT DEFAULT 50.0,

    -- File paths
    dem_path TEXT,
    vegetation_path TEXT,
    roads_path TEXT,
    trails_path TEXT,

    -- Processing status
    status TEXT DEFAULT 'created',  -- created, processing, completed, failed
    error_message TEXT,

    -- Statistics
    total_area_acres FLOAT,
    segment_count INTEGER DEFAULT 0
);

-- Grid points table
CREATE TABLE IF NOT EXISTS grid_points (
    id SERIAL PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,

    -- Point in projected CRS
    pt GEOMETRY(Point, 32600),

    -- Visibility metrics
    visible_area_m2 FLOAT,
    visible_cell_indices INTEGER[],  -- Array of DEM cell IDs

    -- Access control
    is_accessible BOOLEAN DEFAULT FALSE,
    access_type TEXT,  -- 'road', 'trail', 'off_road', 'none'

    -- Selection status
    is_selected BOOLEAN DEFAULT FALSE,
    selected_sequence INTEGER,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_grid_points_project ON grid_points(project_id);
CREATE INDEX idx_grid_points_accessible ON grid_points(project_id, is_accessible);
CREATE INDEX idx_grid_points_selected ON grid_points(project_id, is_selected);
CREATE INDEX idx_grid_points_geom ON grid_points USING GIST(pt);

-- Search segments table
CREATE TABLE IF NOT EXISTS search_segments (
    id SERIAL PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    grid_point_id INTEGER REFERENCES grid_points(id),

    -- Segment polygon in WGS84 for export
    segment_polygon GEOMETRY(Polygon, 4326),

    -- Launch point in WGS84
    launch_point GEOMETRY(Point, 4326),

    -- Metrics
    area_acres FLOAT,
    area_m2 FLOAT,

    -- Sequencing
    sequence INTEGER NOT NULL,

    -- Metadata
    access_type TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_segments_project ON search_segments(project_id);
CREATE INDEX idx_segments_sequence ON search_segments(project_id, sequence);
CREATE INDEX idx_segments_geom ON search_segments USING GIST(segment_polygon);

-- Processing log table
CREATE TABLE IF NOT EXISTS processing_logs (
    id SERIAL PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT NOW(),
    log_level TEXT,  -- INFO, WARNING, ERROR
    message TEXT,
    details JSONB
);

CREATE INDEX idx_logs_project ON processing_logs(project_id);

-- Create views for easier querying
CREATE OR REPLACE VIEW project_summary AS
SELECT
    p.id,
    p.name,
    p.status,
    p.segment_count,
    p.total_area_acres,
    p.drone_agl_altitude,
    p.max_vlos_m,
    p.created_at,
    COUNT(DISTINCT s.id) as actual_segment_count,
    SUM(s.area_acres) as covered_area_acres,
    ST_AsGeoJSON(p.search_polygon) as search_polygon_geojson
FROM projects p
LEFT JOIN search_segments s ON p.id = s.project_id
GROUP BY p.id;
