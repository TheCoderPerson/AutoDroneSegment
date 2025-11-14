"""
Greedy Segment Generation Algorithm.

Uses a greedy max-coverage approach to minimize the number of segments
while ensuring full coverage of the search polygon.
"""
from typing import List, Tuple, Set, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SegmentGenerator:
    """Generate optimal search segments using greedy max-coverage algorithm."""

    def __init__(self, progress_callback=None):
        """
        Initialize segment generator.

        Args:
            progress_callback: Optional callback function(message, progress_pct)
        """
        self.segments = []
        self.progress_callback = progress_callback

    def generate_segments(
        self,
        grid_points: List[int],
        visibility_sets: Dict[int, Set[int]],
        access_classification: Dict[int, str],
        primary_point_indices: Set[int],
        target_cells: Set[int],
        preferred_size_cells: Optional[int] = None
    ) -> List[Tuple[int, Set[int]]]:
        """
        Generate segments using greedy max-coverage algorithm.

        Algorithm:
        Phase 1: Use access-compliant points (primary set)
        Phase 2: Use non-compliant points if needed (secondary set)
        Phase 3: Fallback subdivision if gaps remain

        Args:
            grid_points: List of grid point IDs
            visibility_sets: Dict mapping point_id -> set of visible cell IDs
            access_classification: Dict mapping point_id -> access type
            primary_point_indices: Set of primary (accessible) point indices
            target_cells: Set of all cell IDs that must be covered
            preferred_size_cells: Optional preferred segment size in cells

        Returns:
            List of tuples: (point_id, covered_cells)
        """
        logger.info("Starting greedy segment generation...")
        logger.info(f"Target cells to cover: {len(target_cells)}")
        logger.info(f"Primary points: {len(primary_point_indices)}")
        logger.info(f"Total grid points: {len(grid_points)}")

        segments = []
        uncovered_cells = target_cells.copy()

        # Phase 1: Use primary (accessible) points
        logger.info("Phase 1: Using primary (accessible) points...")

        primary_points = [
            pid for pid in grid_points
            if pid in primary_point_indices
        ]

        segments_phase1 = self._greedy_selection(
            primary_points,
            visibility_sets,
            uncovered_cells,
            preferred_size_cells
        )

        segments.extend(segments_phase1)

        logger.info(
            f"Phase 1 complete: {len(segments_phase1)} segments, "
            f"{len(uncovered_cells)} cells remaining"
        )

        # Phase 2: Use secondary (non-accessible) points if needed
        if uncovered_cells:
            logger.info("Phase 2: Using secondary (non-accessible) points...")

            secondary_points = [
                pid for pid in grid_points
                if pid not in primary_point_indices
            ]

            segments_phase2 = self._greedy_selection(
                secondary_points,
                visibility_sets,
                uncovered_cells,
                preferred_size_cells
            )

            segments.extend(segments_phase2)

            logger.info(
                f"Phase 2 complete: {len(segments_phase2)} segments, "
                f"{len(uncovered_cells)} cells remaining"
            )

        # Phase 3: Handle remaining uncovered cells (rare)
        if uncovered_cells:
            logger.warning(
                f"{len(uncovered_cells)} cells remain uncovered. "
                "This indicates visibility issues or insufficient grid points."
            )
            # Could implement fallback subdivision here

        logger.info(f"Total segments generated: {len(segments)}")

        # Add metadata
        result_segments = []
        for idx, (point_id, covered_cells) in enumerate(segments):
            result_segments.append({
                'sequence': idx + 1,
                'point_id': point_id,
                'covered_cells': covered_cells,
                'access_type': access_classification.get(point_id, 'none'),
                'cell_count': len(covered_cells)
            })

        return result_segments

    def _greedy_selection(
        self,
        candidate_points: List[int],
        visibility_sets: Dict[int, Set[int]],
        uncovered_cells: Set[int],
        preferred_size_cells: Optional[int] = None
    ) -> List[Tuple[int, Set[int]]]:
        """
        Perform greedy selection from candidate points.

        Args:
            candidate_points: List of candidate point IDs
            visibility_sets: Visibility sets for each point
            uncovered_cells: Set of cells that need coverage (modified in place)
            preferred_size_cells: Optional preferred segment size

        Returns:
            List of (point_id, covered_cells) tuples
        """
        segments = []
        available_points = set(candidate_points)
        initial_uncovered = len(uncovered_cells)
        iteration = 0

        logger.info(f"Starting greedy selection with {len(available_points)} candidate points, {initial_uncovered} cells to cover")

        while uncovered_cells and available_points:
            iteration += 1

            # Report progress every 5 iterations
            if iteration % 5 == 0 and self.progress_callback:
                coverage_pct = ((initial_uncovered - len(uncovered_cells)) / initial_uncovered) * 100
                # Map to 80-82% range (narrow range since this is quick)
                progress = 80 + int(coverage_pct * 0.02)
                self.progress_callback(
                    f"Generating segments... ({len(segments)} segments, {coverage_pct:.0f}% covered)",
                    progress
                )

            # Log progress every 10 iterations
            if iteration % 10 == 0:
                coverage_pct = ((initial_uncovered - len(uncovered_cells)) / initial_uncovered) * 100
                logger.info(
                    f"Greedy iteration {iteration}: {len(segments)} segments selected, "
                    f"{len(uncovered_cells)} cells remaining ({coverage_pct:.1f}% covered), "
                    f"{len(available_points)} points available"
                )

            # Find point with maximum coverage of uncovered cells
            best_point = None
            best_coverage = set()
            best_score = 0

            for point_id in available_points:
                if point_id not in visibility_sets:
                    continue

                # Calculate coverage of uncovered cells
                visible_cells = visibility_sets[point_id]
                coverage = visible_cells.intersection(uncovered_cells)
                coverage_count = len(coverage)

                # Score based on coverage
                score = coverage_count

                # Penalize if too large (if preferred size specified)
                if preferred_size_cells and coverage_count > preferred_size_cells * 1.5:
                    score *= 0.8

                # Bonus for being close to preferred size
                if preferred_size_cells:
                    size_ratio = coverage_count / preferred_size_cells
                    if 0.7 <= size_ratio <= 1.3:
                        score *= 1.2

                if score > best_score:
                    best_score = score
                    best_point = point_id
                    best_coverage = coverage

            # If no improvement possible, break
            if best_point is None or len(best_coverage) == 0:
                break

            # Add segment
            segments.append((best_point, best_coverage))

            # Remove covered cells
            uncovered_cells -= best_coverage

            # Remove selected point from available
            available_points.remove(best_point)

        # Log final results
        coverage_pct = ((initial_uncovered - len(uncovered_cells)) / initial_uncovered) * 100 if initial_uncovered > 0 else 0
        logger.info(
            f"Greedy selection complete: {len(segments)} segments selected in {iteration} iterations, "
            f"{len(uncovered_cells)} cells remaining ({coverage_pct:.1f}% covered)"
        )

        return segments

    def optimize_segments(
        self,
        segments: List[Dict],
        visibility_sets: Dict[int, Set[int]],
        preferred_size_cells: int
    ) -> List[Dict]:
        """
        Optimize segments by merging small adjacent segments or splitting large ones.

        Args:
            segments: List of segment dictionaries
            visibility_sets: Visibility sets
            preferred_size_cells: Target segment size

        Returns:
            Optimized list of segments
        """
        logger.info("Optimizing segments...")

        optimized = []

        for segment in segments:
            cell_count = segment['cell_count']

            # If segment is too large, consider splitting
            if cell_count > preferred_size_cells * 2:
                logger.info(
                    f"Segment {segment['sequence']} is large ({cell_count} cells), "
                    "but splitting not implemented in this version"
                )
                # Could implement radial or geometric splitting
                optimized.append(segment)

            # If segment is very small, could merge with neighbors
            elif cell_count < preferred_size_cells * 0.3:
                logger.info(
                    f"Segment {segment['sequence']} is small ({cell_count} cells)"
                )
                # Could implement merging logic
                optimized.append(segment)

            else:
                optimized.append(segment)

        return optimized

    def calculate_statistics(
        self,
        segments: List[Dict],
        total_target_cells: int,
        cell_area_m2: float
    ) -> Dict:
        """
        Calculate segment statistics.

        Args:
            segments: List of segments
            total_target_cells: Total cells that should be covered
            cell_area_m2: Area of each cell

        Returns:
            Dictionary of statistics
        """
        total_covered = set()
        for segment in segments:
            total_covered.update(segment['covered_cells'])

        coverage_percentage = (len(total_covered) / total_target_cells * 100
                               if total_target_cells > 0 else 0)

        segment_sizes = [seg['cell_count'] for seg in segments]

        stats = {
            'total_segments': len(segments),
            'total_cells_covered': len(total_covered),
            'target_cells': total_target_cells,
            'coverage_percentage': coverage_percentage,
            'min_segment_size_cells': min(segment_sizes) if segment_sizes else 0,
            'max_segment_size_cells': max(segment_sizes) if segment_sizes else 0,
            'avg_segment_size_cells': (sum(segment_sizes) / len(segment_sizes)
                                       if segment_sizes else 0),
            'total_area_m2': len(total_covered) * cell_area_m2,
            'total_area_acres': len(total_covered) * cell_area_m2 / 4046.86
        }

        logger.info(f"Segment Statistics: {stats}")

        return stats
