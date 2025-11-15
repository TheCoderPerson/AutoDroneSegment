"""
Segment Polygon Constructor.

Converts visibility cell sets into actual polygon geometries.
"""
from typing import Set, List, Tuple, Dict
from shapely.geometry import box, Point, Polygon, MultiPolygon, mapping
from shapely.ops import unary_union
import logging

logger = logging.getLogger(__name__)


class PolygonBuilder:
    """Build segment polygons from visibility cells."""

    def __init__(self, dem_processor, progress_callback=None):
        """
        Initialize polygon builder.

        Args:
            dem_processor: DEMProcessor instance with cell index and transform
            progress_callback: Optional callback function(message, progress_pct)
        """
        self.dem_processor = dem_processor
        self.progress_callback = progress_callback

    def remove_holes(self, polygon, min_hole_area=100):
        """
        Remove interior holes (rings) from a polygon to create solid segments.

        Small holes can be artifacts from overlap removal or cell-based construction.
        This ensures segments are solid polygons without interior holes.

        Args:
            polygon: Shapely Polygon or MultiPolygon
            min_hole_area: Minimum hole area in m² to keep (smaller holes are filled)

        Returns:
            Polygon or MultiPolygon without small holes
        """
        from shapely.geometry import Polygon as ShapelyPolygon, MultiPolygon as ShapelyMultiPolygon

        if isinstance(polygon, ShapelyPolygon):
            if polygon.interiors:
                # Keep only large holes (if any)
                exteriors = [polygon.exterior]
                large_holes = [interior for interior in polygon.interiors
                              if ShapelyPolygon(interior).area >= min_hole_area]

                if large_holes:
                    return ShapelyPolygon(exteriors[0], holes=large_holes)
                else:
                    # No holes to keep - return solid polygon
                    return ShapelyPolygon(exteriors[0])
            return polygon

        elif isinstance(polygon, ShapelyMultiPolygon):
            # Remove holes from each polygon in the multipolygon
            cleaned_polys = [self.remove_holes(p, min_hole_area) for p in polygon.geoms]
            return ShapelyMultiPolygon(cleaned_polys)

        return polygon

    def consolidate_multipolygon(self, polygon, min_part_area=1000, min_part_ratio=0.05):
        """
        Consolidate MultiPolygons by removing small disconnected parts.

        This fixes the issue where overlap removal creates tiny disconnected pieces
        of one segment inside or near other segments. Small parts are removed to
        ensure each segment is a single contiguous polygon.

        Args:
            polygon: Shapely Polygon or MultiPolygon
            min_part_area: Minimum area (m²) for a part to be kept (default 1000m² ≈ 0.25 acres)
            min_part_ratio: Minimum ratio of part area to total area (default 5%)

        Returns:
            Polygon or consolidated MultiPolygon with only significant parts
        """
        from shapely.geometry import Polygon as ShapelyPolygon, MultiPolygon as ShapelyMultiPolygon

        if isinstance(polygon, ShapelyPolygon):
            # Already a single polygon, nothing to consolidate
            return polygon

        elif isinstance(polygon, ShapelyMultiPolygon):
            if len(polygon.geoms) == 1:
                # Only one part, return it as a Polygon
                return polygon.geoms[0]

            # Calculate total area
            total_area = polygon.area

            # Sort parts by area (largest first)
            parts_with_area = [(p, p.area) for p in polygon.geoms]
            parts_with_area.sort(key=lambda x: x[1], reverse=True)

            # Keep parts that meet minimum criteria
            kept_parts = []
            removed_count = 0
            removed_area = 0

            for part, area in parts_with_area:
                area_ratio = area / total_area if total_area > 0 else 0

                # Keep if it meets either threshold
                if area >= min_part_area or area_ratio >= min_part_ratio:
                    kept_parts.append(part)
                else:
                    removed_count += 1
                    removed_area += area

            if removed_count > 0:
                logger.info(
                    f"Consolidated MultiPolygon: removed {removed_count} small part(s) "
                    f"totaling {removed_area:.0f} m² ({removed_area/total_area*100:.1f}% of segment)"
                )

            # Return appropriate geometry
            if len(kept_parts) == 0:
                logger.warning("All parts removed during consolidation, keeping original")
                return polygon
            elif len(kept_parts) == 1:
                return kept_parts[0]  # Single polygon
            else:
                return ShapelyMultiPolygon(kept_parts)

        return polygon

    def build_segment_polygon(
        self,
        cell_ids: Set[int],
        search_polygon_geojson: dict,
        simplify_tolerance: float = 1.0
    ) -> dict:
        """
        Build a polygon from a set of visible cells.

        Args:
            cell_ids: Set of cell IDs
            search_polygon_geojson: Original search polygon for clipping
            simplify_tolerance: Tolerance for polygon simplification (meters)

        Returns:
            GeoJSON polygon geometry
        """
        if not cell_ids:
            return None

        # Get cell polygons
        cell_polygons = []

        transform = self.dem_processor.transform
        cell_width = abs(transform[0])
        cell_height = abs(transform[4])

        for cell_id in cell_ids:
            if cell_id not in self.dem_processor.cell_index:
                continue

            # Get cell centroid
            cx, cy = self.dem_processor.cell_index[cell_id]

            # Create cell polygon (bounding box)
            minx = cx - cell_width / 2
            maxx = cx + cell_width / 2
            miny = cy - cell_height / 2
            maxy = cy + cell_height / 2

            cell_poly = box(minx, miny, maxx, maxy)
            cell_polygons.append(cell_poly)

        if not cell_polygons:
            return None

        # Union all cell polygons
        unified_polygon = unary_union(cell_polygons)

        # Handle MultiPolygon: use conservative consolidation
        from shapely.geometry import MultiPolygon as ShapelyMultiPolygon
        if isinstance(unified_polygon, ShapelyMultiPolygon):
            num_parts = len(unified_polygon.geoms)
            total_area = unified_polygon.area

            logger.info(
                f"Segment created MultiPolygon with {num_parts} parts, "
                f"total area {total_area:.2f} m². Applying conservative consolidation..."
            )

            # Strategy: Small buffer to merge nearby parts that are close together
            # Use smaller buffer to avoid creating overlaps with other segments
            buffer_distance = cell_width * 0.3  # Reduced from 0.5 to be more conservative

            # Positive buffer to merge nearby parts
            buffered = unified_polygon.buffer(buffer_distance)

            # Negative buffer to restore size (slightly smaller negative to smooth edges)
            consolidated = buffered.buffer(-buffer_distance * 0.9)

            # Keep result even if it's still MultiPolygon - don't use convex hull
            # as it creates too much overlap
            if isinstance(consolidated, ShapelyMultiPolygon):
                logger.info(
                    f"After buffer merge: {len(consolidated.geoms)} parts remain. "
                    f"Keeping MultiPolygon (no convex hull to avoid overlaps)."
                )
            else:
                logger.info(f"Consolidated into single polygon")

            unified_polygon = consolidated

        # Clip to search polygon
        from shapely.geometry import shape
        search_poly = shape(search_polygon_geojson)
        clipped_polygon = unified_polygon.intersection(search_poly)

        # Conservative consolidation after clipping as well
        if isinstance(clipped_polygon, ShapelyMultiPolygon):
            num_parts = len(clipped_polygon.geoms)
            total_area = clipped_polygon.area

            logger.info(
                f"Clipping created MultiPolygon with {num_parts} parts, "
                f"total area {total_area:.2f} m². Applying conservative consolidation..."
            )

            # Use conservative buffer to merge nearby parts
            buffer_distance = cell_width * 0.3
            buffered = clipped_polygon.buffer(buffer_distance)
            consolidated = buffered.buffer(-buffer_distance * 0.9)

            # Keep result even if still MultiPolygon - avoid convex hull
            if isinstance(consolidated, ShapelyMultiPolygon):
                logger.info(
                    f"After buffer merge: {len(consolidated.geoms)} parts remain. "
                    f"Keeping as MultiPolygon."
                )
            else:
                logger.info(f"Consolidated into single polygon")

            clipped_polygon = consolidated

        # Simplify to reduce vertex count
        if simplify_tolerance > 0:
            clipped_polygon = clipped_polygon.simplify(
                simplify_tolerance,
                preserve_topology=True
            )

        # Fix invalid geometry if needed
        if not clipped_polygon.is_valid:
            logger.warning("Segment polygon has invalid geometry after clipping/simplification, fixing...")
            clipped_polygon = clipped_polygon.buffer(0)

        # Remove small holes to ensure solid segments
        clipped_polygon = self.remove_holes(clipped_polygon, min_hole_area=100)

        # Convert to GeoJSON
        return mapping(clipped_polygon)

    def build_all_segments(
        self,
        segments: List[Dict],
        grid_points: List[Tuple[float, float]],
        search_polygon_geojson: dict,
        proj_epsg: int,
        simplify_tolerance: float = 1.0
    ) -> List[Dict]:
        """
        Build polygons for all segments.

        Args:
            segments: List of segment dictionaries from SegmentGenerator
            grid_points: List of (x, y) grid point coordinates
            search_polygon_geojson: Search polygon in projected CRS
            proj_epsg: Projected EPSG code
            simplify_tolerance: Simplification tolerance

        Returns:
            List of segment dictionaries with polygon and launch point
        """
        logger.info(f"Building polygons for {len(segments)} segments...")

        result_segments = []
        total_segments = len(segments)

        for idx, segment in enumerate(segments):
            # Report progress
            if self.progress_callback:
                progress_pct = 85 + int((idx / total_segments) * 4)  # Map to 85-89%
                self.progress_callback(
                    f"Building segment polygons... ({idx + 1}/{total_segments})",
                    progress_pct
                )

            point_id = segment['point_id']
            cell_ids = segment['covered_cells']

            # Build polygon
            polygon_geom = self.build_segment_polygon(
                cell_ids,
                search_polygon_geojson,
                simplify_tolerance
            )

            if polygon_geom is None:
                logger.warning(f"Failed to build polygon for segment {segment['sequence']}")
                continue

            # Get launch point coordinates
            if point_id < len(grid_points):
                lx, ly = grid_points[point_id]
            else:
                logger.error(f"Invalid point_id {point_id}")
                continue

            # Calculate area
            from shapely.geometry import shape
            poly_shape = shape(polygon_geom)
            area_m2 = poly_shape.area
            area_acres = area_m2 / 4046.86

            # Store segment data
            result_segment = {
                'sequence': segment['sequence'],
                'point_id': point_id,
                'launch_point': {'x': lx, 'y': ly},
                'polygon': polygon_geom,
                'area_m2': area_m2,
                'area_acres': area_acres,
                'access_type': segment.get('access_type', 'none'),
                'cell_count': len(cell_ids),
                'proj_epsg': proj_epsg
            }

            result_segments.append(result_segment)

        logger.info(f"Successfully built {len(result_segments)} segment polygons")

        # Remove overlaps between segments
        result_segments = self._remove_overlaps(result_segments)

        return result_segments

    def _remove_overlaps(self, segments: List[Dict]) -> List[Dict]:
        """
        Remove overlaps between segments by processing in sequence order.

        Each segment is clipped to remove any overlap with previously processed segments.
        This ensures non-overlapping coverage while maintaining the sequence priority.

        Args:
            segments: List of segment dictionaries with polygons

        Returns:
            List of segments with overlaps removed
        """
        logger.info("Removing overlaps between segments...")

        from shapely.geometry import shape

        processed_segments = []
        previous_union = None

        for idx, segment in enumerate(segments):
            seg_shape = shape(segment['polygon'])
            original_area = seg_shape.area

            # If not the first segment, remove overlap with all previous segments
            if previous_union is not None:
                # Subtract the union of all previous segments
                non_overlapping = seg_shape.difference(previous_union)

                # Check if we lost significant area
                new_area = non_overlapping.area
                area_loss_pct = ((original_area - new_area) / original_area * 100) if original_area > 0 else 0

                if area_loss_pct > 1.0:  # Log if more than 1% area lost
                    logger.info(
                        f"Segment {segment['sequence']}: removed {area_loss_pct:.1f}% overlap "
                        f"(from {original_area:.0f} to {new_area:.0f} m²)"
                    )

                # Update segment with non-overlapping polygon
                if not non_overlapping.is_empty:
                    # Handle case where difference creates MultiPolygon
                    from shapely.geometry import MultiPolygon as ShapelyMultiPolygon
                    if isinstance(non_overlapping, ShapelyMultiPolygon):
                        logger.info(
                            f"Segment {segment['sequence']}: overlap removal created "
                            f"MultiPolygon with {len(non_overlapping.geoms)} parts"
                        )
                        # Keep all parts to maintain coverage

                    # Fix invalid geometry if needed
                    if not non_overlapping.is_valid:
                        logger.warning(f"Segment {segment['sequence']} has invalid geometry after overlap removal, fixing...")
                        non_overlapping = non_overlapping.buffer(0)

                    # Remove holes created by overlap removal
                    non_overlapping = self.remove_holes(non_overlapping, min_hole_area=100)

                    # Consolidate MultiPolygons by removing small disconnected parts
                    # This prevents tiny islands of one segment appearing inside others
                    non_overlapping = self.consolidate_multipolygon(
                        non_overlapping,
                        min_part_area=1000,  # 1000 m² ≈ 0.25 acres
                        min_part_ratio=0.05   # 5% of segment area
                    )

                    # Recalculate area after consolidation
                    new_area = non_overlapping.area

                    segment['polygon'] = mapping(non_overlapping)
                    segment['area_m2'] = new_area
                    segment['area_acres'] = new_area / 4046.86

                    # Update union of processed segments
                    previous_union = previous_union.union(non_overlapping)
                else:
                    logger.warning(
                        f"Segment {segment['sequence']} became empty after overlap removal. "
                        "This segment was entirely overlapped by previous segments."
                    )
                    continue  # Skip empty segments
            else:
                # First segment - no overlap to remove
                previous_union = seg_shape

            processed_segments.append(segment)

        logger.info(
            f"Overlap removal complete: kept {len(processed_segments)}/{len(segments)} segments"
        )

        return processed_segments

    def transform_segments_to_wgs84(
        self,
        segments: List[Dict],
        from_epsg: int
    ) -> List[Dict]:
        """
        Transform segment polygons and launch points to WGS84.

        Args:
            segments: List of segments in projected CRS
            from_epsg: Source EPSG code

        Returns:
            List of segments in WGS84
        """
        from app.core.crs_manager import CRSManager

        logger.info("Transforming segments to WGS84...")

        wgs84_segments = []
        total_segments = len(segments)

        for idx, segment in enumerate(segments):
            # Report progress
            if self.progress_callback:
                progress_pct = 90 + int((idx / total_segments) * 4)  # Map to 90-94%
                self.progress_callback(
                    f"Transforming to WGS84... ({idx + 1}/{total_segments})",
                    progress_pct
                )

            # Transform polygon
            polygon_wgs84 = CRSManager.transform_geometry(
                segment['polygon'],
                from_epsg=from_epsg,
                to_epsg=4326
            )

            # Transform launch point
            lx, ly = segment['launch_point']['x'], segment['launch_point']['y']
            lx_wgs84, ly_wgs84 = CRSManager.transform_point(
                lx, ly,
                from_epsg=from_epsg,
                to_epsg=4326
            )

            wgs84_segment = {
                'sequence': segment['sequence'],
                'polygon': polygon_wgs84,
                'launch_point': {
                    'type': 'Point',
                    'coordinates': [lx_wgs84, ly_wgs84]
                },
                'area_acres': segment['area_acres'],
                'area_m2': segment['area_m2'],
                'access_type': segment['access_type']
            }

            wgs84_segments.append(wgs84_segment)

        return wgs84_segments

    def validate_coverage(
        self,
        segments: List[Dict],
        search_polygon_geojson: dict
    ) -> Dict:
        """
        Validate that segments provide full coverage of search area.

        Args:
            segments: List of segment dictionaries
            search_polygon_geojson: Original search polygon

        Returns:
            Validation results dictionary
        """
        from shapely.geometry import shape
        from shapely.ops import unary_union

        logger.info("Validating segment coverage...")

        search_poly = shape(search_polygon_geojson)
        search_area = search_poly.area

        # Union all segment polygons - fix invalid geometries first
        segment_polys = []
        for seg in segments:
            poly = shape(seg['polygon'])
            # Fix invalid geometries using buffer(0)
            if not poly.is_valid:
                logger.warning(f"Segment {seg.get('sequence')} has invalid geometry, fixing...")
                poly = poly.buffer(0)
            segment_polys.append(poly)

        try:
            covered_area = unary_union(segment_polys)
        except Exception as e:
            logger.error(f"Failed to union segments for validation: {e}")
            # If union fails, skip detailed validation and return basic stats
            return {
                'coverage_percentage': 0.0,
                'gap_percentage': 0.0,
                'overlap_count': 0,
                'validation_skipped': True,
                'error': str(e)
            }

        # Calculate coverage
        intersection = search_poly.intersection(covered_area)
        coverage_area = intersection.area
        coverage_percentage = (coverage_area / search_area * 100) if search_area > 0 else 0

        # Find gaps
        gaps = search_poly.difference(covered_area)
        gap_area = gaps.area
        gap_percentage = (gap_area / search_area * 100) if search_area > 0 else 0

        # Find overlaps
        overlaps = []
        for i, seg1 in enumerate(segments):
            for j, seg2 in enumerate(segments[i+1:], start=i+1):
                poly1 = shape(seg1['polygon'])
                poly2 = shape(seg2['polygon'])
                overlap = poly1.intersection(poly2)
                if not overlap.is_empty:
                    overlaps.append({
                        'segment1': seg1['sequence'],
                        'segment2': seg2['sequence'],
                        'overlap_area_m2': overlap.area
                    })

        validation = {
            'coverage_percentage': coverage_percentage,
            'gap_percentage': gap_percentage,
            'gap_area_m2': gap_area,
            'overlap_count': len(overlaps),
            'overlaps': overlaps[:10],  # Limit to first 10
            'is_complete': coverage_percentage >= 99.0
        }

        logger.info(
            f"Coverage validation: {coverage_percentage:.2f}% covered, "
            f"{gap_percentage:.2f}% gaps, {len(overlaps)} overlaps"
        )

        return validation
