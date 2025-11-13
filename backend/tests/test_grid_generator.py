"""
Tests for Grid Generator.
"""
import pytest
from app.core.grid_generator import GridGenerator


def test_generate_grid():
    """Test grid generation."""
    # Simple square polygon in UTM coordinates
    polygon = {
        'type': 'Polygon',
        'coordinates': [[
            [0, 0],
            [1000, 0],
            [1000, 1000],
            [0, 1000],
            [0, 0]
        ]]
    }

    grid_spacing = 100  # 100m spacing

    points = GridGenerator.generate_grid(polygon, grid_spacing)

    # Should generate approximately (1000/100)² = 100 points
    assert 80 < len(points) < 120

    # All points should be tuples
    for point in points:
        assert isinstance(point, tuple)
        assert len(point) == 2


def test_generate_grid_max_points():
    """Test max points constraint."""
    # Large polygon
    polygon = {
        'type': 'Polygon',
        'coordinates': [[
            [0, 0],
            [10000, 0],
            [10000, 10000],
            [0, 10000],
            [0, 0]
        ]]
    }

    grid_spacing = 10  # Would generate ~1,000,000 points

    points = GridGenerator.generate_grid(polygon, grid_spacing, max_points=1000)

    # Should not exceed max_points
    assert len(points) <= 1000


def test_generate_adaptive_grid():
    """Test adaptive grid generation."""
    polygon = {
        'type': 'Polygon',
        'coordinates': [[
            [0, 0],
            [1000, 0],
            [1000, 1000],
            [0, 1000],
            [0, 0]
        ]]
    }

    points = GridGenerator.generate_adaptive_grid(
        polygon,
        preferred_spacing_m=100,
        min_spacing_m=50
    )

    assert len(points) > 0
    assert all(isinstance(p, tuple) for p in points)


def test_grid_points_inside_polygon():
    """Test that all generated points are inside polygon."""
    from shapely.geometry import shape, Point

    polygon_geojson = {
        'type': 'Polygon',
        'coordinates': [[
            [0, 0],
            [1000, 0],
            [1000, 1000],
            [0, 1000],
            [0, 0]
        ]]
    }

    points = GridGenerator.generate_grid(polygon_geojson, 100)

    polygon = shape(polygon_geojson)

    # All points should be inside polygon
    for x, y in points:
        point = Point(x, y)
        assert polygon.contains(point) or polygon.boundary.contains(point)
