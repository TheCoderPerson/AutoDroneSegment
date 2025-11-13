"""
Search segment data models.
"""
from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class SegmentResponse(BaseModel):
    """Response model for search segment."""
    id: int
    project_id: UUID
    sequence: int
    area_acres: float
    segment_polygon: dict  # GeoJSON geometry
    launch_point: dict  # GeoJSON point
    access_type: Optional[str]

    class Config:
        from_attributes = True


class SearchSegment(BaseModel):
    """Internal search segment model."""
    id: int
    project_id: UUID
    grid_point_id: int
    sequence: int
    area_acres: float
    area_m2: float
    access_type: Optional[str]

    class Config:
        from_attributes = True
