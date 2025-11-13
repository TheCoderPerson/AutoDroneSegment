"""
Tests for Segment Generator.
"""
import pytest
from app.core.segment_generator import SegmentGenerator


def test_greedy_selection():
    """Test greedy selection algorithm."""
    generator = SegmentGenerator()

    # Create test data
    candidate_points = [0, 1, 2]
    visibility_sets = {
        0: {1, 2, 3, 4, 5},      # Covers 5 cells
        1: {3, 4, 5, 6, 7},      # Covers 5 cells (3 overlap with point 0)
        2: {6, 7, 8, 9, 10}      # Covers 5 cells (2 overlap with point 1)
    }
    uncovered_cells = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}

    segments = generator._greedy_selection(
        candidate_points,
        visibility_sets,
        uncovered_cells,
        preferred_size_cells=5
    )

    # Should select all 3 points to cover all cells
    assert len(segments) == 3

    # Check that all cells are covered
    covered = set()
    for point_id, cells in segments:
        covered.update(cells)

    assert covered == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}


def test_generate_segments():
    """Test full segment generation."""
    generator = SegmentGenerator()

    grid_points = [0, 1, 2, 3, 4]
    visibility_sets = {
        0: {1, 2, 3},
        1: {3, 4, 5},
        2: {5, 6, 7},
        3: {7, 8, 9},
        4: {9, 10, 11}
    }
    access_classification = {
        0: 'road',
        1: 'road',
        2: 'off_road',
        3: 'off_road',
        4: 'trail'
    }
    primary_point_indices = {0, 1, 4}  # Accessible points
    target_cells = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}

    segments = generator.generate_segments(
        grid_points,
        visibility_sets,
        access_classification,
        primary_point_indices,
        target_cells,
        preferred_size_cells=3
    )

    # Should generate segments
    assert len(segments) > 0

    # All segments should have required fields
    for segment in segments:
        assert 'sequence' in segment
        assert 'point_id' in segment
        assert 'covered_cells' in segment
        assert 'access_type' in segment
        assert 'cell_count' in segment


def test_calculate_statistics():
    """Test statistics calculation."""
    generator = SegmentGenerator()

    segments = [
        {'sequence': 1, 'covered_cells': {1, 2, 3}, 'cell_count': 3},
        {'sequence': 2, 'covered_cells': {4, 5, 6}, 'cell_count': 3},
        {'sequence': 3, 'covered_cells': {7, 8}, 'cell_count': 2}
    ]

    stats = generator.calculate_statistics(
        segments,
        total_target_cells=8,
        cell_area_m2=100.0
    )

    assert stats['total_segments'] == 3
    assert stats['total_cells_covered'] == 8
    assert stats['coverage_percentage'] == 100.0
    assert stats['min_segment_size_cells'] == 2
    assert stats['max_segment_size_cells'] == 3
    assert stats['avg_segment_size_cells'] == pytest.approx(2.67, rel=0.1)
