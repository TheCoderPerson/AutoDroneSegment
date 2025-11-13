"""
Access Filter for determining which grid points are accessible based on:
- Road proximity
- Trail proximity
- Off-road accessibility
- "Anywhere" (no restrictions)
"""
from typing import List, Tuple, Optional, Set
import geopandas as gpd
from shapely.geometry import Point, MultiLineString, LineString
from shapely.ops import unary_union
import logging

logger = logging.getLogger(__name__)


class AccessFilter:
    """Filter grid points based on access restrictions."""

    def __init__(
        self,
        roads_path: Optional[str] = None,
        trails_path: Optional[str] = None,
        target_epsg: int = 4326
    ):
        """
        Initialize access filter.

        Args:
            roads_path: Path to roads shapefile/geojson
            trails_path: Path to trails shapefile/geojson
            target_epsg: Target EPSG code for reprojection
        """
        self.roads_path = roads_path
        self.trails_path = trails_path
        self.target_epsg = target_epsg

        self.roads_gdf = None
        self.trails_gdf = None

        # Load data if paths provided
        if roads_path:
            self._load_roads()
        if trails_path:
            self._load_trails()

    def _load_roads(self):
        """Load roads data."""
        try:
            logger.info(f"Loading roads from {self.roads_path}")
            self.roads_gdf = gpd.read_file(self.roads_path)

            # Reproject if needed
            if self.roads_gdf.crs.to_epsg() != self.target_epsg:
                self.roads_gdf = self.roads_gdf.to_crs(epsg=self.target_epsg)

            logger.info(f"Loaded {len(self.roads_gdf)} road features")

        except Exception as e:
            logger.error(f"Error loading roads: {e}")
            self.roads_gdf = None

    def _load_trails(self):
        """Load trails data."""
        try:
            logger.info(f"Loading trails from {self.trails_path}")
            self.trails_gdf = gpd.read_file(self.trails_path)

            # Reproject if needed
            if self.trails_gdf.crs.to_epsg() != self.target_epsg:
                self.trails_gdf = self.trails_gdf.to_crs(epsg=self.target_epsg)

            logger.info(f"Loaded {len(self.trails_gdf)} trail features")

        except Exception as e:
            logger.error(f"Error loading trails: {e}")
            self.trails_gdf = None

    def filter_points(
        self,
        points: List[Tuple[float, float]],
        access_types: List[str],
        access_deviation_m: float
    ) -> Tuple[List[Tuple[int, str]], List[Tuple[int, str]]]:
        """
        Filter points based on access restrictions.

        Args:
            points: List of (x, y) coordinates
            access_types: List of access types ['road', 'trail', 'off_road', 'anywhere']
            access_deviation_m: Buffer distance in meters

        Returns:
            Tuple of (primary_points, secondary_points)
            Each list contains tuples of (point_index, access_type)
        """
        logger.info(f"Filtering {len(points)} points for access types: {access_types}")

        # If 'anywhere' is selected, all points are primary
        if 'anywhere' in access_types:
            primary = [(idx, 'anywhere') for idx in range(len(points))]
            secondary = []
            logger.info("Access type 'anywhere' selected - all points accessible")
            return primary, secondary

        # Create buffers
        road_buffer = None
        trail_buffer = None

        if 'road' in access_types and self.roads_gdf is not None:
            road_buffer = self._create_buffer(self.roads_gdf, access_deviation_m)

        if 'trail' in access_types and self.trails_gdf is not None:
            trail_buffer = self._create_buffer(self.trails_gdf, access_deviation_m)

        # Classify each point
        primary_points = []
        secondary_points = []

        for idx, (x, y) in enumerate(points):
            point = Point(x, y)
            access_type = self._classify_point(
                point,
                access_types,
                road_buffer,
                trail_buffer
            )

            if access_type:
                primary_points.append((idx, access_type))
            else:
                secondary_points.append((idx, 'none'))

        logger.info(
            f"Filtered: {len(primary_points)} primary points, "
            f"{len(secondary_points)} secondary points"
        )

        return primary_points, secondary_points

    def _create_buffer(self, gdf: gpd.GeoDataFrame, buffer_m: float):
        """
        Create a unified buffer around geometries.

        Args:
            gdf: GeoDataFrame with geometries
            buffer_m: Buffer distance in meters

        Returns:
            Unified buffer geometry
        """
        # Buffer each geometry
        buffered = gdf.geometry.buffer(buffer_m)

        # Union all buffers
        unified_buffer = unary_union(buffered.values)

        return unified_buffer

    def _classify_point(
        self,
        point: Point,
        access_types: List[str],
        road_buffer,
        trail_buffer
    ) -> Optional[str]:
        """
        Classify a point based on access restrictions.

        Args:
            point: Point to classify
            access_types: Requested access types
            road_buffer: Road buffer geometry (or None)
            trail_buffer: Trail buffer geometry (or None)

        Returns:
            Access type string or None if not accessible
        """
        in_road_buffer = road_buffer and road_buffer.contains(point)
        in_trail_buffer = trail_buffer and trail_buffer.contains(point)

        # Check based on access_types
        if 'road' in access_types and 'trail' in access_types:
            # Must be in BOTH buffers
            if in_road_buffer and in_trail_buffer:
                return 'road_and_trail'
            # Or at least one if only one exists
            elif in_road_buffer and trail_buffer is None:
                return 'road'
            elif in_trail_buffer and road_buffer is None:
                return 'trail'

        elif 'road' in access_types:
            if in_road_buffer:
                return 'road'

        elif 'trail' in access_types:
            if in_trail_buffer:
                return 'trail'

        elif 'off_road' in access_types:
            # Must be outside both buffers
            if not in_road_buffer and not in_trail_buffer:
                return 'off_road'

        return None

    def get_accessible_area(
        self,
        polygon_geojson: dict,
        access_types: List[str],
        access_deviation_m: float
    ) -> float:
        """
        Calculate the percentage of polygon area that is accessible.

        Args:
            polygon_geojson: Search polygon
            access_types: Access types
            access_deviation_m: Buffer distance

        Returns:
            Percentage of accessible area (0-100)
        """
        from shapely.geometry import shape

        polygon = shape(polygon_geojson)
        total_area = polygon.area

        if 'anywhere' in access_types:
            return 100.0

        # Create access area
        access_area = None

        if 'road' in access_types and self.roads_gdf is not None:
            road_buffer = self._create_buffer(self.roads_gdf, access_deviation_m)
            access_area = road_buffer

        if 'trail' in access_types and self.trails_gdf is not None:
            trail_buffer = self._create_buffer(self.trails_gdf, access_deviation_m)
            if access_area:
                # Union with roads
                access_area = unary_union([access_area, trail_buffer])
            else:
                access_area = trail_buffer

        if access_area is None:
            return 0.0

        # Intersect with polygon
        accessible = polygon.intersection(access_area)

        return (accessible.area / total_area) * 100.0
