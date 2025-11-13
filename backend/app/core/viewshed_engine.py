"""
Viewshed Engine using GDAL's optimized C++ implementation.

Calculates visibility from drone vantage points considering:
- Terrain elevation
- Vegetation height
- Maximum VLOS distance
"""
import os
import tempfile
from typing import List, Tuple, Set
import numpy as np
import rasterio
from osgeo import gdal, gdalconst
from shapely.geometry import shape, Point
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class ViewshedEngine:
    """Calculate viewsheds using GDAL."""

    def __init__(self, dem_path: str, dem_processor):
        """
        Initialize viewshed engine.

        Args:
            dem_path: Path to processed DEM
            dem_processor: DEMProcessor instance with cell index
        """
        self.dem_path = dem_path
        self.dem_processor = dem_processor

        # Enable GDAL exceptions
        gdal.UseExceptions()

    def calculate_viewshed(
        self,
        observer_x: float,
        observer_y: float,
        observer_height: float,
        max_distance: float,
        target_height: float = 0.0,
        point_index: int = -1
    ) -> Tuple[Set[int], float]:
        """
        Calculate viewshed from a single observer point.

        Args:
            observer_x: Observer X coordinate (projected)
            observer_y: Observer Y coordinate (projected)
            observer_height: Observer height above ground (drone AGL)
            max_distance: Maximum visibility distance in meters
            target_height: Target height above ground (default 0)

        Returns:
            Tuple of (visible_cell_ids, visible_area_m2)
        """
        # Open DEM
        dem_ds = gdal.Open(self.dem_path, gdalconst.GA_ReadOnly)
        if dem_ds is None:
            raise ValueError(f"Cannot open DEM: {self.dem_path}")

        # Get geotransform and dimensions
        gt = dem_ds.GetGeoTransform()
        dem_width = dem_ds.RasterXSize
        dem_height = dem_ds.RasterYSize

        # Calculate DEM bounds in geographic coordinates
        dem_minx = gt[0]
        dem_maxx = gt[0] + dem_width * gt[1]
        dem_miny = gt[3] + dem_height * gt[5]
        dem_maxy = gt[3]

        # Convert observer coordinates to pixel coordinates
        # Use float to preserve precision - GDAL may need exact coordinates
        pixel_x = (observer_x - gt[0]) / gt[1]
        pixel_y = (observer_y - gt[3]) / gt[5]

        # Log detailed info for debugging
        logger.debug(
            f"Observer: ({observer_x:.2f}, {observer_y:.2f}), "
            f"Pixel: ({pixel_x}, {pixel_y}), "
            f"DEM bounds: X[{dem_minx:.2f}, {dem_maxx:.2f}], Y[{dem_miny:.2f}, {dem_maxy:.2f}], "
            f"DEM size: {dem_width}x{dem_height}"
        )

        # Check if observer is within DEM bounds (with margin for edge effects)
        if pixel_x < 0 or pixel_x >= dem_width or pixel_y < 0 or pixel_y >= dem_height:
            logger.warning(
                f"Observer at ({observer_x:.2f}, {observer_y:.2f}) is outside DEM bounds. "
                f"DEM bounds: ({dem_minx:.2f}, {dem_miny:.2f}) to ({dem_maxx:.2f}, {dem_maxy:.2f}). "
                f"Pixel coords: ({pixel_x}, {pixel_y}), DEM size: {dem_width}x{dem_height}"
            )
            dem_ds = None
            return set(), 0.0

        # Also check if observer is outside geographic bounds
        if not (dem_minx <= observer_x <= dem_maxx and dem_miny <= observer_y <= dem_maxy):
            logger.warning(
                f"Observer at ({observer_x:.2f}, {observer_y:.2f}) is outside DEM geographic bounds: "
                f"X[{dem_minx:.2f}, {dem_maxx:.2f}], Y[{dem_miny:.2f}, {dem_maxy:.2f}]"
            )
            dem_ds = None
            return set(), 0.0

        # Get the band and check for NoData at observer location
        band = dem_ds.GetRasterBand(1)
        nodata_value = band.GetNoDataValue()

        # Read elevation at observer pixel to verify it's valid
        observer_elevation = band.ReadAsArray(int(pixel_x), int(pixel_y), 1, 1)[0, 0]

        if point_index < 3:
            logger.info(
                f"Point {point_index}: Observer elevation={observer_elevation:.2f}m, "
                f"NoData value={nodata_value}"
            )

        if nodata_value is not None and observer_elevation == nodata_value:
            logger.warning(
                f"Observer at pixel ({pixel_x:.1f}, {pixel_y:.1f}) is on NoData cell"
            )
            dem_ds = None
            return set(), 0.0

        # Create output file
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
            output_path = tmp.name

        try:

            # Use GDAL ViewshedGenerate with older API (compatible with GDAL 3.4)
            # Parameters: band, driver, output, creationOptions, x, y,
            #             observerHeight, targetHeight, visibleVal, invisibleVal,
            #             outOfRangeVal, noDataVal, curvCoeff, mode, maxDistance

            # Log parameters for first few points
            # Note: GDAL ViewshedGenerate expects GEOGRAPHIC coordinates, not pixel coordinates
            if point_index < 3:
                logger.info(
                    f"Point {point_index}: Calling GDAL ViewshedGenerate: "
                    f"geo=({observer_x:.2f}, {observer_y:.2f}), pixel=({int(pixel_x)}, {int(pixel_y)}), "
                    f"observer_h={observer_height}m, max_dist={max_distance}m, "
                    f"DEM_size={dem_width}x{dem_height}, "
                    f"DEM_bounds: X[{dem_minx:.2f}, {dem_maxx:.2f}], Y[{dem_miny:.2f}, {dem_maxy:.2f}]"
                )

            viewshed_ds = gdal.ViewshedGenerate(
                band,                    # Source band
                "GTiff",                 # Driver
                output_path,             # Output file
                None,                    # Creation options
                observer_x,              # Observer X coordinate (geographic, not pixel!)
                observer_y,              # Observer Y coordinate (geographic, not pixel!)
                observer_height,         # Observer height
                target_height,           # Target height
                255,                     # Visible value
                0,                       # Invisible value
                0,                       # Out of range value
                0,                       # NoData value
                1.0,                     # Curvature coefficient (1.0 for standard Earth curvature)
                gdal.GVM_Edge,          # Mode (check edges)
                max_distance            # Maximum distance
            )

            if viewshed_ds is None:
                # Get GDAL error message
                err = gdal.GetLastErrorMsg()
                raise RuntimeError(f"Viewshed calculation failed: {err}")

            # Read viewshed results
            viewshed_array = viewshed_ds.GetRasterBand(1).ReadAsArray()

            # Close datasets
            viewshed_ds = None
            dem_ds = None

            # Extract visible cell indices
            visible_cells = self._extract_visible_cells(viewshed_array)

            # Calculate visible area
            cell_area = self.dem_processor.get_cell_area()
            visible_area_m2 = len(visible_cells) * cell_area

            return visible_cells, visible_area_m2

        finally:
            # Clean up temporary file
            if os.path.exists(output_path):
                os.remove(output_path)

    def _extract_visible_cells(self, viewshed_array: np.ndarray) -> Set[int]:
        """
        Extract cell IDs of visible cells from viewshed array.

        Args:
            viewshed_array: 2D numpy array with visibility values

        Returns:
            Set of visible cell IDs
        """
        visible_cells = set()

        # Get indices where visibility is True (value == 255)
        visible_indices = np.where(viewshed_array == 255)

        # Convert 2D indices to cell IDs
        height, width = viewshed_array.shape

        for row, col in zip(visible_indices[0], visible_indices[1]):
            cell_id = row * width + col
            visible_cells.add(cell_id)

        return visible_cells

    def calculate_viewsheds_batch(
        self,
        observer_points: List[Tuple[float, float]],
        observer_height: float,
        max_distance: float,
        max_workers: int = 4
    ) -> List[Tuple[int, Set[int], float]]:
        """
        Calculate viewsheds for multiple points in parallel.

        Args:
            observer_points: List of (x, y) observer coordinates
            observer_height: Observer height AGL
            max_distance: Maximum visibility distance
            max_workers: Number of parallel workers

        Returns:
            List of tuples: (point_index, visible_cells, visible_area_m2)
        """
        logger.info(f"Calculating viewsheds for {len(observer_points)} points...")

        # Log DEM information and first few points for debugging
        dem_ds = gdal.Open(self.dem_path, gdalconst.GA_ReadOnly)
        if dem_ds:
            gt = dem_ds.GetGeoTransform()
            dem_width = dem_ds.RasterXSize
            dem_height = dem_ds.RasterYSize
            dem_minx = gt[0]
            dem_maxx = gt[0] + dem_width * gt[1]
            dem_miny = gt[3] + dem_height * gt[5]
            dem_maxy = gt[3]

            logger.info(f"DEM bounds: X({dem_minx:.2f} to {dem_maxx:.2f}), Y({dem_miny:.2f} to {dem_maxy:.2f})")
            logger.info(f"DEM size: {dem_width} x {dem_height} pixels")

            if len(observer_points) > 0:
                logger.info(f"First 3 grid points: {observer_points[:3]}")
                # Check if first point is in bounds
                x, y = observer_points[0]
                if dem_minx <= x <= dem_maxx and dem_miny <= y <= dem_maxy:
                    logger.info("✓ First point is within DEM bounds")
                else:
                    logger.error(f"✗ First point ({x:.2f}, {y:.2f}) is OUTSIDE DEM bounds!")

            dem_ds = None

        results = []

        # For each point, calculate viewshed
        for idx, (x, y) in enumerate(observer_points):
            try:
                visible_cells, visible_area = self.calculate_viewshed(
                    x, y,
                    observer_height,
                    max_distance,
                    point_index=idx
                )
                results.append((idx, visible_cells, visible_area))

                if (idx + 1) % 50 == 0:
                    logger.info(f"Processed {idx + 1}/{len(observer_points)} viewsheds")

            except Exception as e:
                logger.error(f"Error calculating viewshed for point {idx}: {e}")
                results.append((idx, set(), 0.0))

        logger.info(f"Completed {len(results)} viewshed calculations")

        return results

    def filter_visible_cells_by_polygon(
        self,
        visible_cells: Set[int],
        polygon_geojson: dict
    ) -> Set[int]:
        """
        Filter visible cells to only those inside the search polygon.

        Args:
            visible_cells: Set of cell IDs
            polygon_geojson: Search polygon geometry

        Returns:
            Filtered set of cell IDs
        """
        geom = shape(polygon_geojson)
        filtered_cells = set()

        for cell_id in visible_cells:
            if cell_id in self.dem_processor.cell_index:
                x, y = self.dem_processor.cell_index[cell_id]
                point = Point(x, y)
                if geom.contains(point):
                    filtered_cells.add(cell_id)

        return filtered_cells

    def get_coverage_percentage(
        self,
        covered_cells: Set[int],
        polygon_geojson: dict
    ) -> float:
        """
        Calculate what percentage of the polygon is covered.

        Args:
            covered_cells: Set of covered cell IDs
            polygon_geojson: Search polygon

        Returns:
            Coverage percentage (0-100)
        """
        geom = shape(polygon_geojson)

        # Count total cells inside polygon
        total_cells = 0
        for cell_id, (x, y) in self.dem_processor.cell_index.items():
            point = Point(x, y)
            if geom.contains(point):
                total_cells += 1

        if total_cells == 0:
            return 0.0

        # Count covered cells
        covered_count = len(covered_cells)

        return (covered_count / total_cells) * 100.0
