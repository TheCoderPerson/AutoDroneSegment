"""
Grid Generator for creating candidate vantage points.

Creates an even distribution of points within the search polygon
that serve as potential drone launch locations.
"""
import numpy as np
from shapely.geometry import shape, Point
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class GridGenerator:
    """Generate grid of candidate vantage points."""

    @staticmethod
    def generate_grid(
        polygon_geojson: dict,
        grid_spacing_m: float,
        max_points: int = 10000
    ) -> List[Tuple[float, float]]:
        """
        Generate a regular grid of points within a polygon.

        Args:
            polygon_geojson: GeoJSON polygon geometry (in projected CRS)
            grid_spacing_m: Spacing between grid points in meters
            max_points: Maximum number of points to generate

        Returns:
            List of (x, y) coordinate tuples
        """
        logger.info(f"Generating grid with {grid_spacing_m}m spacing...")

        geom = shape(polygon_geojson)
        bounds = geom.bounds  # (minx, miny, maxx, maxy)

        # Calculate grid dimensions
        minx, miny, maxx, maxy = bounds
        x_range = maxx - minx
        y_range = maxy - miny

        # Number of points in each dimension
        nx = int(np.ceil(x_range / grid_spacing_m)) + 1
        ny = int(np.ceil(y_range / grid_spacing_m)) + 1

        total_points = nx * ny

        # Check if we exceed max points
        if total_points > max_points:
            logger.warning(
                f"Grid would generate {total_points} points, "
                f"exceeds max of {max_points}. Adjusting spacing..."
            )
            # Adjust spacing to fit within max_points
            scale_factor = np.sqrt(total_points / max_points)
            grid_spacing_m *= scale_factor
            nx = int(np.ceil(x_range / grid_spacing_m)) + 1
            ny = int(np.ceil(y_range / grid_spacing_m)) + 1
            logger.info(f"Adjusted spacing to {grid_spacing_m:.1f}m")

        # Generate grid
        x_coords = np.linspace(minx, maxx, nx)
        y_coords = np.linspace(miny, maxy, ny)

        # Create meshgrid
        xx, yy = np.meshgrid(x_coords, y_coords)

        # Flatten and combine
        points = list(zip(xx.flatten(), yy.flatten()))

        # Filter to points inside polygon
        points_inside = []
        for x, y in points:
            point = Point(x, y)
            if geom.contains(point):
                points_inside.append((x, y))

        logger.info(f"Generated {len(points_inside)} grid points inside polygon")

        return points_inside

    @staticmethod
    def generate_adaptive_grid(
        polygon_geojson: dict,
        preferred_spacing_m: float,
        min_spacing_m: float = 25.0,
        max_points: int = 10000
    ) -> List[Tuple[float, float]]:
        """
        Generate an adaptive grid that adjusts spacing based on polygon size.

        Args:
            polygon_geojson: GeoJSON polygon geometry
            preferred_spacing_m: Preferred spacing
            min_spacing_m: Minimum allowed spacing
            max_points: Maximum number of points

        Returns:
            List of (x, y) coordinate tuples
        """
        # Try with preferred spacing
        points = GridGenerator.generate_grid(
            polygon_geojson,
            preferred_spacing_m,
            max_points
        )

        # If too few points, try with smaller spacing
        if len(points) < 10 and preferred_spacing_m > min_spacing_m:
            logger.info("Too few points, trying smaller spacing...")
            points = GridGenerator.generate_grid(
                polygon_geojson,
                min_spacing_m,
                max_points
            )

        return points

    @staticmethod
    def add_boundary_points(
        polygon_geojson: dict,
        grid_points: List[Tuple[float, float]],
        boundary_spacing_m: float = 50.0
    ) -> List[Tuple[float, float]]:
        """
        Add additional points along polygon boundary.

        Args:
            polygon_geojson: GeoJSON polygon geometry
            grid_points: Existing grid points
            boundary_spacing_m: Spacing for boundary points

        Returns:
            Combined list of grid and boundary points
        """
        geom = shape(polygon_geojson)
        boundary = geom.boundary

        # Generate points along boundary
        num_boundary_points = int(boundary.length / boundary_spacing_m)

        boundary_points = []
        for i in range(num_boundary_points):
            distance = (i / num_boundary_points) * boundary.length
            point = boundary.interpolate(distance)
            boundary_points.append((point.x, point.y))

        logger.info(f"Added {len(boundary_points)} boundary points")

        # Combine and remove duplicates
        all_points = grid_points + boundary_points

        # Remove points that are too close together
        unique_points = []
        min_dist = boundary_spacing_m / 2

        for pt in all_points:
            is_unique = True
            for existing_pt in unique_points:
                dist = np.sqrt(
                    (pt[0] - existing_pt[0])**2 +
                    (pt[1] - existing_pt[1])**2
                )
                if dist < min_dist:
                    is_unique = False
                    break

            if is_unique:
                unique_points.append(pt)

        return unique_points
