"""
Grid point data models.
"""
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID


class GridPoint(BaseModel):
    """Grid point model for vantage point candidates."""
    id: int
    project_id: UUID
    visible_area_m2: Optional[float]
    visible_cell_indices: List[int]
    is_accessible: bool
    access_type: Optional[str]
    is_selected: bool
    selected_sequence: Optional[int]

    class Config:
        from_attributes = True
