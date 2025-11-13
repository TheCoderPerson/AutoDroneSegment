"""
CRS (Coordinate Reference System) Manager for handling coordinate transformations.

All processing occurs in a projected CRS (UTM) for correct area & distance calculations.
"""
import math
from typing import Tuple
from pyproj import CRS, Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform
import logging

logger = logging.getLogger(__name__)


class CRSManager:
    """Manages coordinate reference system transformations."""

    @staticmethod
    def get_utm_zone(lon: float, lat: float) -> int:
        """
        Determine UTM zone from longitude and latitude.

        Args:
            lon: Longitude in degrees
            lat: Latitude in degrees

        Returns:
            UTM zone number (1-60)
        """
        return int((lon + 180) / 6) + 1

    @staticmethod
    def get_utm_epsg(lon: float, lat: float) -> int:
        """
        Get the EPSG code for the appropriate UTM zone.

        Args:
            lon: Longitude in degrees
            lat: Latitude in degrees

        Returns:
            EPSG code for the UTM zone
        """
        utm_zone = CRSManager.get_utm_zone(lon, lat)

        # Northern hemisphere: 32600 + zone, Southern: 32700 + zone
        if lat >= 0:
            epsg = 32600 + utm_zone
        else:
            epsg = 32700 + utm_zone

        logger.info(f"Determined UTM EPSG:{epsg} for coordinates ({lon:.4f}, {lat:.4f})")
        return epsg

    @staticmethod
    def get_polygon_centroid(geojson_geom: dict) -> Tuple[float, float]:
        """
        Get the centroid of a GeoJSON polygon.

        Args:
            geojson_geom: GeoJSON geometry dict

        Returns:
            Tuple of (longitude, latitude)
        """
        geom = shape(geojson_geom)
        centroid = geom.centroid
        return centroid.x, centroid.y

    @staticmethod
    def transform_geometry(geojson_geom: dict, from_epsg: int, to_epsg: int) -> dict:
        """
        Transform a GeoJSON geometry from one CRS to another.

        Args:
            geojson_geom: GeoJSON geometry dict
            from_epsg: Source EPSG code
            to_epsg: Target EPSG code

        Returns:
            Transformed GeoJSON geometry dict
        """
        if from_epsg == to_epsg:
            return geojson_geom

        geom = shape(geojson_geom)

        # Create transformer
        transformer = Transformer.from_crs(
            f"EPSG:{from_epsg}",
            f"EPSG:{to_epsg}",
            always_xy=True
        )

        # Transform geometry
        transformed_geom = transform(transformer.transform, geom)

        return mapping(transformed_geom)

    @staticmethod
    def get_project_crs(search_polygon_geojson: dict) -> Tuple[int, dict]:
        """
        Determine the appropriate projected CRS for a project and transform the polygon.

        Args:
            search_polygon_geojson: GeoJSON geometry in WGS84 (EPSG:4326)

        Returns:
            Tuple of (utm_epsg, transformed_polygon_geojson)
        """
        # Get centroid
        lon, lat = CRSManager.get_polygon_centroid(search_polygon_geojson)

        # Determine UTM zone
        utm_epsg = CRSManager.get_utm_epsg(lon, lat)

        # Transform polygon to UTM
        projected_polygon = CRSManager.transform_geometry(
            search_polygon_geojson,
            from_epsg=4326,
            to_epsg=utm_epsg
        )

        # Log polygon bounds
        orig_geom = shape(search_polygon_geojson)
        proj_geom = shape(projected_polygon)
        logger.info(f"Original polygon (WGS84) bounds: {orig_geom.bounds}")
        logger.info(f"Projected polygon (EPSG:{utm_epsg}) bounds: {proj_geom.bounds}")

        return utm_epsg, projected_polygon

    @staticmethod
    def transform_point(x: float, y: float, from_epsg: int, to_epsg: int) -> Tuple[float, float]:
        """
        Transform a single point from one CRS to another.

        Args:
            x: X coordinate
            y: Y coordinate
            from_epsg: Source EPSG code
            to_epsg: Target EPSG code

        Returns:
            Tuple of (transformed_x, transformed_y)
        """
        if from_epsg == to_epsg:
            return x, y

        transformer = Transformer.from_crs(
            f"EPSG:{from_epsg}",
            f"EPSG:{to_epsg}",
            always_xy=True
        )

        return transformer.transform(x, y)

    @staticmethod
    def calculate_area_acres(geojson_geom: dict, epsg: int = 4326) -> float:
        """
        Calculate area of a polygon in acres.

        Args:
            geojson_geom: GeoJSON geometry dict
            epsg: EPSG code of the geometry

        Returns:
            Area in acres
        """
        geom = shape(geojson_geom)

        # If not in a projected CRS, transform first
        if epsg == 4326:
            lon, lat = geom.centroid.x, geom.centroid.y
            utm_epsg = CRSManager.get_utm_epsg(lon, lat)

            transformer = Transformer.from_crs(
                f"EPSG:{epsg}",
                f"EPSG:{utm_epsg}",
                always_xy=True
            )
            geom = transform(transformer.transform, geom)

        # Calculate area in square meters
        area_m2 = geom.area

        # Convert to acres (1 acre = 4046.86 m²)
        area_acres = area_m2 / 4046.86

        return area_acres
