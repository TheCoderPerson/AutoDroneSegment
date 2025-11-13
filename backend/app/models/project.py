"""
Project data models.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Request model for creating a new project."""
    name: str = Field(..., min_length=1, max_length=255)
    search_polygon: dict  # GeoJSON geometry
    drone_agl_altitude: float = Field(..., gt=0, description="Drone altitude AGL in meters")
    preferred_segment_size_acres: float = Field(..., gt=0, description="Preferred segment size in acres")
    max_vlos_m: float = Field(..., gt=0, description="Maximum VLOS distance in meters")
    access_types: List[str] = Field(..., description="Access types: road, trail, off_road, anywhere")
    access_deviation_m: float = Field(default=50.0, gt=0, description="Buffer distance for access roads/trails")
    grid_spacing_m: float = Field(default=50.0, gt=0, description="Grid spacing for candidate points")


class ProjectResponse(BaseModel):
    """Response model for project data."""
    id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    drone_agl_altitude: float
    preferred_segment_size_acres: float
    max_vlos_m: float
    access_types: List[str]
    access_deviation_m: float
    grid_spacing_m: float
    total_area_acres: Optional[float]
    segment_count: int
    search_polygon: Optional[dict]  # GeoJSON
    error_message: Optional[str]

    class Config:
        from_attributes = True


class Project(BaseModel):
    """Internal project model."""
    id: UUID
    name: str
    status: str
    search_polygon_geojson: Optional[str]
    proj_epsg: Optional[int]
    drone_agl_altitude: float
    preferred_segment_size_acres: float
    max_vlos_m: float
    access_types: List[str]
    access_deviation_m: float
    grid_spacing_m: float
    dem_path: Optional[str]
    vegetation_path: Optional[str]
    roads_path: Optional[str]
    trails_path: Optional[str]
    total_area_acres: Optional[float]
    segment_count: int

    class Config:
        from_attributes = True
