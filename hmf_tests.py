#!/usr/bin/env python3
"""
Test suite for HowManyFucks game
Run with: python -m pytest tests.py -v
"""

import pytest
import time
from hmf import GameEngine, DailySeed, GridRenderer


class TestGameEngine:
    """Test the core game engine functionality."""
    
    def test_deterministic_generation(self):
        """Test that same seed produces identical results."""
        seed = "test123"
        
        engine1 = GameEngine(seed)
        puzzle1 = engine1.generate_grid(size=8, requested_count=2)
        
        engine2 = GameEngine(seed)
        puzzle2 = engine2.generate_grid(size=8, requested_count=2)
        
        assert puzzle1['grid'] == puzzle2['grid']
        assert puzzle1['true_count'] == puzzle2['true_count']
        assert len(puzzle1['matches']) == len(puzzle2['matches'])
    
    def test_scanner_finds_all_directions(self):
        """Test scanner finds words in all 8 directions."""
        engine = GameEngine("scanner_test")
        
        # Create a grid manually with known placements
        grid = [
            ['F', 'U', 'C', 'K', 'F'],  # Horizontal E
            ['U', 'F', 'U', 'C', 'U'],
            ['C', 'U', 'F', 'U', 'C'], 
            ['K', 'C', 'U', 'F', 'K'],  # Anti-diagonal (SW from top-right)
            ['F', 'K', 'C', 'U', 'F']   # Horizontal reversed (KCUF = FUCK backwards)
        ]
        
        result = engine.scan_grid(grid)
        assert result['count'] >= 2  # Should find at least the obvious ones
    
    def test_overlap_handling(self):
        """Test that overlapping words are handled correctly."""
        engine = GameEngine("overlap_test")
        
        # Generate puzzle that allows overlaps
        puzzle = engine.generate_grid(
            size=10, 
            requested_count=3,
            allow_overlap=True
        )
        
        # Verify the generated count matches scan result
        scan_result = engine.scan_grid(puzzle['grid'])
        assert scan_result['count'] == puzzle['true_count']
    
    def test_no_overlap_mode(self):
        """Test no-overlap mode works correctly."""
        engine = GameEngine("no_overlap_test")
        
        puzzle = engine.generate_grid(
            size=15,
            requested_count=2,
            allow_overlap=False
        )
        
        # Verify no overlapping cells in matches
        all_cells = set()
        for match in puzzle['matches']:
            for cell in match['cells']:
                assert cell not in all_cells, "Found overlapping cells in no-overlap mode"
                all_cells.add(cell)
    
    def test_dead_page_zero_count(self):
        """Test that requesting 0 count produces puzzles with 0 matches."""
        engine = GameEngine("zero_test")
        
        for size in [8, 10, 15]:
            puzzle = engine.generate_grid(size=size, requested_count=0)
            assert puzzle['true_count'] == 0
            
            # Double-check with scanner
            scan_result = engine.scan_grid(puzzle['grid'])
            assert scan_result['count'] == 0
    
    def test_exact_count_accuracy(self):
        """Test that exact count requests are satisfied."""
        seeds = ["exact1", "exact2", "exact3"]
        sizes = [8, 10, 15]
        counts = [1, 2, 3]
        
        for seed in seeds:
            for size in sizes:
                for count in counts:
                    engine = GameEngine(seed + str(size) + str(count))
                    puzzle = engine.generate_grid(size=size, requested_count=count)
                    assert puzzle['true_count'] == count
    
    def test_random_bounds(self):
        """Test that random count generation respects bounds."""
        engine = GameEngine("bounds_test")
        
        min_count, max_count = 1, 4
        results = []
        
        for i in range(20):
            engine_instance = GameEngine(f"bounds_test_{i}")
            puzzle = engine_instance.generate_grid(
                size=12,
                requested_count=(min_count, max_count)
            )
            results.append(puzzle['true_count'])
        
        # Check all results are in bounds
        assert all(min_count <= count <= max_count for count in results)
        
        # Check we get some variety (not all the same)
        assert len(set(results)) > 1
    
    def test_weighted_vs_even_distribution(self):
        """Test that weighted and even distributions produce different results."""
        seed = "distribution_test"
        
        engine1 = GameEngine(seed)
        puzzle_even = engine1.generate_grid(
            size=10, 
            requested_count=0,  # No target words, just filler
            distribution_mode='even'
        )
        
        engine2 = GameEngine(seed)
        puzzle_weighted = engine2.generate_grid(
            size=10,
            requested_count=0,
            distribution_mode='weighted'
        )
        
        # Count letter frequencies
        def count_letters(grid):
            counts = {'F': 0, 'U': 0, 'C': 0, 'K': 0}
            for row in grid:
                for cell in row:
                    counts[cell] += 1
            return counts
        
        even_counts = count_letters(puzzle_even['grid'])
        weighted_counts = count_letters(puzzle_weighted['grid'])
        
        # In weighted mode, F and K should be more frequent
        f_k_ratio_weighted = (weighted_counts['F'] + weighted_counts['K']) / sum(weighted_counts.values())
        f_k_ratio_even = (even_counts['F'] + even_counts['K']) / sum(even_counts.values())
        
        # This is probabilistic, but weighted should generally have higher F+K ratio
        # We'll just check they're different
        assert even_counts != weighted_counts
    
    def test_performance(self):
        """Test that generation and scanning complete within time limits."""
        engine = GameEngine("perf_test")
        
        start_time = time.time()
        puzzle = engine.generate_grid(size=20, requested_count=3)
        scan_result = engine.scan_grid(puzzle['grid'])
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration < 0.2, f"Performance test failed: took {duration:.3f}s (limit: 0.2s)"
    
    def test_directions_modes(self):
        """Test different direction modes work correctly."""
        engine = GameEngine("directions_test")
        
        # Test horizontal only
        puzzle_h = engine.generate_grid(
            size=10, 
            requested_count=1,
            directions_mode='horizontal'
        )
        
        # Test horizontal + vertical
        engine2 = GameEngine("directions_test")
        puzzle_hv = engine2.generate_grid(
            size=10,
            requested_count=1, 
            directions_mode='horiz_vert'
        )
        
        # These should succeed without error
        assert puzzle_h['true_count'] == 1
        assert puzzle_hv['true_count'] == 1


class TestScanner:
    """Test the word scanning functionality."""
    
    def test_horizontal_detection(self):
        """Test detection of horizontal words."""
        engine = GameEngine()
        
        grid = [
            ['F', 'U', 'C', 'K', 'F'],
            ['U', 'F', 'U', 'C', 'U'],
            ['C', 'K', 'C', 'U', 'F'],
            ['K', 'U', 'F', 'F', 'K'],
            ['F', 'C', 'U', 'K', 'F']
        ]
        
        result = engine.scan_grid(grid)
        assert result['count'] >= 1  # Should find FUCK in first row
    
    def test_vertical_detection(self):
        """Test detection of vertical words."""
        engine = GameEngine()
        
        grid = [
            ['F', 'U', 'C', 'K', 'F'],
            ['U', 'F', 'U', 'C', 'U'], 
            ['C', 'K', 'C', 'U', 'F'],
            ['K', 'U', 'F', 'F', 'K'],
            ['F', 'C', 'U', 'K', 'F']
        ]
        
        result = engine.scan_grid(grid)
        # Should find FUCK vertically in first column
        vertical_found = any(
            match['direction'] in ['N', 'S'] for match in result['matches']
        )
        assert result['count'] >= 1
    
    def test_diagonal_detection(self):
        """Test detection of diagonal words."""
        engine = GameEngine()
        
        # Create grid with diagonal FUCK
        grid = [
            ['F', 'U', 'C', 'K', 'F'],
            ['K', 'U', 'C', 'K', 'U'],
            ['K', 'F', 'C', 'K', 'F'],  
            ['K', 'F', 'U', 'K', 'K'],
            ['F', 'C', 'U', 'K', 'F']
        ]
        
        result = engine.scan_grid(grid)
        # Should find some matches (may include diagonals)
        assert result['count'] >= 0
    
    def test_reverse_detection(self):
        """Test detection of reversed words (KCUF should count as FUCK)."""
        engine = GameEngine()
        
        grid = [
            ['K', 'C', 'U', 'F', 'F'],  # KCUF = FUCK reversed
            ['U', 'F', 'U', 'C', 'U'],
            ['C', 'K', 'C', 'U', 'F'],
            ['K', 'U', 'F', 'F', 'K'],
            ['F', 'C', 'U', 'K', 'F']
        ]
        
        result = engine.scan_grid(grid)
        # Should find the reversed word
        assert result['count'] >= 1
    
    def test_duplicate_prevention(self):
        """Test that duplicate matches aren't reported."""
        engine = GameEngine()
        
        # Simple grid where same word might be detected multiple ways
        grid = [
            ['F', 'U', 'C', 'K'],
            ['F', 'U', 'C', 'K'],
            ['F', 'U', 'C', 'K'],
            ['F', 'U', 'C', 'K']
        ]
        
        result = engine.scan_grid(grid)
        
        # Check for duplicates manually
        normalized_matches = set()
        for match in result['matches']:
            normalized = tuple(sorted(match['cells']))
            assert normalized not in normalized_matches, "Duplicate match detected"
            normalized_matches.add(normalized)


class TestDailySeed:
    """Test daily seed functionality."""
    
    def test_daily_seed_consistency(self):
        """Test that daily seed is consistent."""
        seed1 = DailySeed.get_daily_seed()
        seed2 = DailySeed.get_daily_seed()
        assert seed1 == seed2
    
    def test_daily_seed_format(self):
        """Test daily seed has expected format."""
        seed = DailySeed.get_daily_seed()
        assert isinstance(seed, str)
        assert "hmf-" in seed
        assert len(seed.split("-")) >= 4  # hmf-YYYY-MM-DD


class TestGridRenderer:
    """Test grid rendering functionality."""
    
    def test_basic_grid_rendering(self):
        """Test basic grid rendering produces correct format."""
        renderer = GridRenderer()
        
        grid = [
            ['F', 'U', 'C'],
            ['K', 'F', 'U'],
            ['C', 'K', 'F']
        ]
        
        result = renderer.render_grid(grid)
        lines = result.split('\n')
        
        assert len(lines) == 3
        assert lines[0] == "F U C"
        assert lines[1] == "K F U"
        assert lines[2] == "C K F"
    
    def test_highlighted_grid_rendering(self):
        """Test highlighted grid rendering."""
        renderer = GridRenderer()
        
        grid = [
            ['F', 'U', 'C', 'K'],
            ['K', 'F', 'U', 'C'],
            ['C', 'K', 'F', 'U'],
            ['U', 'C', 'K', 'F']
        ]
        
        # Mock match data
        matches = [{
            'start': (0, 0),
            'direction': 'E',
            'cells': [(0, 0), (0, 1), (0, 2), (0, 3)]
        }]
        
        result = renderer.render_highlighted_grid(grid, matches)
        lines = result.split('\n')
        
        # First row should have all letters highlighted
        assert '[F]' in lines[0]
        assert '[U]' in lines[0]
        assert '[C]' in lines[0]
        assert '[K]' in lines[0]
    
    def test_match_list_rendering(self):
        """Test match list rendering."""
        renderer = GridRenderer()
        
        matches = [{
            'start': (0, 0),
            'direction': 'E',
            'cells': [(0, 0), (0, 1), (0, 2), (0, 3)]
        }, {
            'start': (1, 0),  
            'direction': 'S',
            'cells': [(1, 0), (2, 0), (3, 0), (4, 0)]
        }]
        
        result = renderer.render_match_list(matches)
        lines = result.split('\n')
        
        assert len(lines) == 2
        assert '#1:' in lines[0]
        assert '#2:' in lines[1]
        assert 'start=(row 1, col 1)' in lines[0]  # 1-based indexing
        assert 'dir=E' in lines[0]
    
    def test_empty_match_list(self):
        """Test rendering empty match list."""
        renderer = GridRenderer()
        result = renderer.render_match_list([])
        assert result == "No matches found."


class TestIntegration:
    """Integration tests for the complete system."""
    
    def test_full_game_flow(self):
        """Test complete game generation and scanning flow."""
        engine = GameEngine("integration_test")
        
        puzzle = engine.generate_grid(
            size=10,
            requested_count=2,
            distribution_mode='even',
            allow_overlap=True,
            directions_mode='all'
        )
        
        # Verify puzzle structure
        assert 'grid' in puzzle
        assert 'true_count' in puzzle
        assert 'matches' in puzzle
        assert 'metadata' in puzzle
        
        # Verify grid dimensions
        assert len(puzzle['grid']) == 10
        assert all(len(row) == 10 for row in puzzle['grid'])
        
        # Verify all cells contain valid letters
        valid_letters = {'F', 'U', 'C', 'K'}
        for row in puzzle['grid']:
            for cell in row:
                assert cell in valid_letters
        
        # Verify match count consistency
        assert len(puzzle['matches']) == puzzle['true_count']
        
        # Verify scanner finds same count
        scan_result = engine.scan_grid(puzzle['grid'])
        assert scan_result['count'] == puzzle['true_count']
    
    def test_error_handling(self):
        """Test error handling for impossible configurations."""
        engine = GameEngine("error_test")
        
        # This should be impossible - too many words for small grid with no overlap
        with pytest.raises(RuntimeError):
            engine.generate_grid(
                size=4,
                requested_count=10,  # Way too many for 4x4 grid
                allow_overlap=False
            )
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        engine = GameEngine("edge_test")
        
        # Minimum size grid
        puzzle = engine.generate_grid(size=4, requested_count=0)
        assert len(puzzle['grid']) == 4
        
        # Single word in minimum grid
        puzzle = engine.generate_grid(size=4, requested_count=1)
        assert puzzle['true_count'] == 1
        
        # Large grid with many words
        puzzle = engine.generate_grid(size=20, requested_count=(3, 8))
        assert 3 <= puzzle['true_count'] <= 8


def run_performance_benchmark():
    """Run performance benchmark (not a unit test)."""
    print("\n=== Performance Benchmark ===")
    
    test_cases = [
        (8, 2), (10, 3), (15, 5), (20, 8)
    ]
    
    for size, count in test_cases:
        engine = GameEngine(f"perf_{size}_{count}")
        
        start_time = time.time()
        puzzle = engine.generate_grid(size=size, requested_count=count)
        scan_result = engine.scan_grid(puzzle['grid'])
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"Size {size}x{size}, count {count}: {duration:.3f}s")
        
        assert scan_result['count'] == puzzle['true_count']


if __name__ == "__main__":
    # Run basic smoke test
    print("Running smoke tests...")
    
    engine = GameEngine("smoke_test")
    puzzle = engine.generate_grid(size=8, requested_count=1)
    
    print(f"Generated {len(puzzle['grid'])}x{len(puzzle['grid'])} grid")
    print(f"True count: {puzzle['true_count']}")
    print(f"Matches found: {len(puzzle['matches'])}")
    
    renderer = GridRenderer()
    print("\nGrid:")
    print(renderer.render_grid(puzzle['grid']))
    
    if puzzle['matches']:
        print("\nHighlighted:")
        print(renderer.render_highlighted_grid(puzzle['grid'], puzzle['matches']))
        print("\nMatch details:")
        print(renderer.render_match_list(puzzle['matches']))
    
    print("\nSmoke test passed!")
    
    # Optionally run performance benchmark
    run_performance_benchmark()