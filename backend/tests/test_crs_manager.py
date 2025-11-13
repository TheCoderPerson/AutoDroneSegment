"""
Tests for CRS Manager.
"""
import pytest
from app.core.crs_manager import CRSManager


def test_get_utm_zone():
    """Test UTM zone calculation."""
    # San Francisco
    zone = CRSManager.get_utm_zone(-122.4194, 37.7749)
    assert zone == 10

    # London
    zone = CRSManager.get_utm_zone(-0.1276, 51.5074)
    assert zone == 30


def test_get_utm_epsg():
    """Test UTM EPSG code calculation."""
    # San Francisco (Northern Hemisphere)
    epsg = CRSManager.get_utm_epsg(-122.4194, 37.7749)
    assert epsg == 32610

    # Sydney (Southern Hemisphere)
    epsg = CRSManager.get_utm_epsg(151.2093, -33.8688)
    assert epsg == 32756


def test_get_polygon_centroid():
    """Test polygon centroid calculation."""
    polygon = {
        'type': 'Polygon',
        'coordinates': [[
            [-122.5, 37.7],
            [-122.3, 37.7],
            [-122.3, 37.8],
            [-122.5, 37.8],
            [-122.5, 37.7]
        ]]
    }

    lon, lat = CRSManager.get_polygon_centroid(polygon)
    assert abs(lon - (-122.4)) < 0.01
    assert abs(lat - 37.75) < 0.01


def test_transform_geometry():
    """Test geometry transformation."""
    point = {
        'type': 'Point',
        'coordinates': [-122.4194, 37.7749]
    }

    # Transform from WGS84 to UTM
    transformed = CRSManager.transform_geometry(point, 4326, 32610)

    # Should have different coordinates
    assert transformed['coordinates'][0] != point['coordinates'][0]
    assert transformed['coordinates'][1] != point['coordinates'][1]

    # Transform back should give approximately same result
    back_transformed = CRSManager.transform_geometry(transformed, 32610, 4326)
    assert abs(back_transformed['coordinates'][0] - point['coordinates'][0]) < 0.0001
    assert abs(back_transformed['coordinates'][1] - point['coordinates'][1]) < 0.0001


def test_calculate_area_acres():
    """Test area calculation."""
    # 1 square km polygon
    polygon = {
        'type': 'Polygon',
        'coordinates': [[
            [0, 0],
            [0, 0.009],
            [0.009, 0.009],
            [0.009, 0],
            [0, 0]
        ]]
    }

    area_acres = CRSManager.calculate_area_acres(polygon, 4326)

    # 1 km² ≈ 247 acres
    assert 200 < area_acres < 300
