"""
Main Processing Pipeline.

Orchestrates the entire segment generation workflow.
"""
import os
import logging
from typing import Dict, List
from shapely.geometry import shape, Point

from .crs_manager import CRSManager
from .dem_processor import DEMProcessor
from .grid_generator import GridGenerator
from .viewshed_engine import ViewshedEngine
from .access_filter import AccessFilter
from .segment_generator import SegmentGenerator
from .polygon_builder import PolygonBuilder

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """Main processing pipeline for segment generation."""

    def __init__(self, project_config: Dict):
        """
        Initialize processing pipeline.

        Args:
            project_config: Dictionary containing project configuration
        """
        self.config = project_config
        self.project_id = project_config['project_id']
        self.results = {}

    async def execute(self) -> Dict:
        """
        Execute the full processing pipeline.

        Returns:
            Dictionary with results
        """
        logger.info(f"Starting processing pipeline for project {self.project_id}")

        try:
            # Step 1: CRS Management
            logger.info("Step 1: Determining CRS and transforming polygon...")
            utm_epsg, proj_polygon = self._setup_crs()
            self.results['utm_epsg'] = utm_epsg
            self.results['proj_polygon'] = proj_polygon

            # Step 2: DEM Processing
            logger.info("Step 2: Processing DEM...")
            dem_processor = self._process_dem(proj_polygon, utm_epsg)
            self.results['dem_processor'] = dem_processor

            # Step 3: Generate Grid
            logger.info("Step 3: Generating candidate grid points...")
            grid_points = self._generate_grid(proj_polygon)
            self.results['grid_points'] = grid_points
            logger.info(f"Generated {len(grid_points)} grid points")

            # Log grid point bounds
            if grid_points:
                import numpy as np
                xs = [p[0] for p in grid_points]
                ys = [p[1] for p in grid_points]
                logger.info(f"Grid points X range: [{min(xs):.2f}, {max(xs):.2f}]")
                logger.info(f"Grid points Y range: [{min(ys):.2f}, {max(ys):.2f}]")
                logger.info(f"First 5 grid points: {grid_points[:5]}")

            # Step 4: Access Filtering
            logger.info("Step 4: Filtering points by access...")
            primary_points, secondary_points = self._filter_access(grid_points, utm_epsg)
            self.results['primary_points'] = primary_points
            self.results['secondary_points'] = secondary_points
            logger.info(f"Primary: {len(primary_points)}, Secondary: {len(secondary_points)}")

            # Step 5: Calculate Viewsheds
            logger.info("Step 5: Calculating viewsheds...")
            visibility_sets = self._calculate_viewsheds(
                grid_points,
                dem_processor,
                proj_polygon
            )
            self.results['visibility_sets'] = visibility_sets

            # Step 6: Generate Segments
            logger.info("Step 6: Generating segments...")
            segments = self._generate_segments(
                grid_points,
                visibility_sets,
                primary_points,
                proj_polygon,
                dem_processor
            )
            self.results['segments'] = segments
            logger.info(f"Generated {len(segments)} segments")

            # Step 7: Build Segment Polygons
            logger.info("Step 7: Building segment polygons...")
            segment_polygons = self._build_polygons(
                segments,
                grid_points,
                proj_polygon,
                utm_epsg,
                dem_processor
            )
            self.results['segment_polygons'] = segment_polygons

            # Step 8: Transform to WGS84
            logger.info("Step 8: Transforming to WGS84...")
            wgs84_segments = self._transform_to_wgs84(segment_polygons, utm_epsg)
            self.results['wgs84_segments'] = wgs84_segments

            # Step 9: Validation
            logger.info("Step 9: Validating coverage...")
            validation = self._validate_coverage(wgs84_segments)
            self.results['validation'] = validation

            logger.info("Processing pipeline completed successfully")

            return {
                'success': True,
                'project_id': self.project_id,
                'segments': wgs84_segments,
                'validation': validation,
                'statistics': {
                    'total_segments': len(wgs84_segments),
                    'grid_points_generated': len(grid_points),
                    'primary_points': len(primary_points),
                    'secondary_points': len(secondary_points),
                    'utm_epsg': utm_epsg
                }
            }

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'project_id': self.project_id
            }

    def _setup_crs(self):
        """Setup CRS and transform polygon."""
        search_polygon = self.config['search_polygon']

        # Determine UTM zone and transform
        utm_epsg, proj_polygon = CRSManager.get_project_crs(search_polygon)

        return utm_epsg, proj_polygon

    def _process_dem(self, proj_polygon, utm_epsg):
        """Process DEM."""
        dem_path = self.config.get('dem_path')
        vegetation_path = self.config.get('vegetation_path')

        if not dem_path or not os.path.exists(dem_path):
            raise FileNotFoundError(f"DEM file not found: {dem_path}")

        dem_processor = DEMProcessor(dem_path, vegetation_path)

        # Create output directory
        output_dir = self.config.get('output_dir', '/tmp/drone_segments')
        os.makedirs(output_dir, exist_ok=True)

        # Process DEM
        processed_dem = dem_processor.process(
            proj_polygon,
            utm_epsg,
            self.config['max_vlos_m'],
            output_dir
        )

        return dem_processor

    def _generate_grid(self, proj_polygon):
        """Generate grid points."""
        grid_spacing = self.config.get('grid_spacing_m', 50.0)

        grid_points = GridGenerator.generate_grid(
            proj_polygon,
            grid_spacing
        )

        return grid_points

    def _filter_access(self, grid_points, utm_epsg):
        """Filter points by access."""
        access_types = self.config.get('access_types', ['anywhere'])
        access_deviation_m = self.config.get('access_deviation_m', 50.0)

        roads_path = self.config.get('roads_path')
        trails_path = self.config.get('trails_path')

        access_filter = AccessFilter(roads_path, trails_path, utm_epsg)

        primary, secondary = access_filter.filter_points(
            grid_points,
            access_types,
            access_deviation_m
        )

        return primary, secondary

    def _calculate_viewsheds(self, grid_points, dem_processor, proj_polygon):
        """Calculate viewsheds for all grid points."""
        viewshed_engine = ViewshedEngine(
            dem_processor.processed_dem_path,
            dem_processor
        )

        drone_agl = self.config['drone_agl_altitude']
        max_vlos = self.config['max_vlos_m']

        # Calculate viewsheds
        viewshed_results = viewshed_engine.calculate_viewsheds_batch(
            grid_points,
            drone_agl,
            max_vlos
        )

        # Build visibility sets and filter to polygon
        visibility_sets = {}

        for idx, visible_cells, visible_area in viewshed_results:
            # Filter to polygon
            filtered_cells = viewshed_engine.filter_visible_cells_by_polygon(
                visible_cells,
                proj_polygon
            )
            visibility_sets[idx] = filtered_cells

        return visibility_sets

    def _generate_segments(
        self,
        grid_points,
        visibility_sets,
        primary_points,
        proj_polygon,
        dem_processor
    ):
        """Generate segments using greedy algorithm."""
        # Get all target cells (inside polygon)
        target_cells = set()
        geom = shape(proj_polygon)

        for cell_id, (x, y) in dem_processor.cell_index.items():
            point = Point(x, y)
            if geom.contains(point):
                target_cells.add(cell_id)

        # Access classification
        access_classification = {}
        primary_indices = set()

        for idx, access_type in primary_points:
            access_classification[idx] = access_type
            primary_indices.add(idx)

        # Preferred segment size
        preferred_acres = self.config.get('preferred_segment_size_acres', 100.0)
        cell_area = dem_processor.get_cell_area()
        preferred_cells = int(preferred_acres * 4046.86 / cell_area)

        # Generate segments
        segment_generator = SegmentGenerator()
        segments = segment_generator.generate_segments(
            list(range(len(grid_points))),
            visibility_sets,
            access_classification,
            primary_indices,
            target_cells,
            preferred_cells
        )

        return segments

    def _build_polygons(
        self,
        segments,
        grid_points,
        proj_polygon,
        utm_epsg,
        dem_processor
    ):
        """Build polygon geometries for segments."""
        polygon_builder = PolygonBuilder(dem_processor)

        segment_polygons = polygon_builder.build_all_segments(
            segments,
            grid_points,
            proj_polygon,
            utm_epsg,
            simplify_tolerance=2.0
        )

        return segment_polygons

    def _transform_to_wgs84(self, segments, from_epsg):
        """Transform segments to WGS84."""
        polygon_builder = PolygonBuilder(None)

        wgs84_segments = polygon_builder.transform_segments_to_wgs84(
            segments,
            from_epsg
        )

        return wgs84_segments

    def _validate_coverage(self, wgs84_segments):
        """Validate segment coverage."""
        # Transform search polygon to WGS84 for comparison
        search_polygon = self.config['search_polygon']

        polygon_builder = PolygonBuilder(None)
        validation = polygon_builder.validate_coverage(
            wgs84_segments,
            search_polygon
        )

        return validation
