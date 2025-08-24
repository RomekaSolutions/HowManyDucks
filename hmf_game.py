#!/usr/bin/env python3
"""
HowManyFucks - A text-based word-search counting game
Find instances of "FUCK" hidden in a grid of F, U, C, K letters.
"""

import random
import argparse
import sys
from datetime import datetime
from typing import List, Tuple, Dict, Optional, Union
import hashlib

# === ENGINE MODULE ===

class GameEngine:
    """Core game logic for grid generation and word scanning."""
    
    DIRECTIONS = {
        'N': (-1, 0), 'NE': (-1, 1), 'E': (0, 1), 'SE': (1, 1),
        'S': (1, 0), 'SW': (1, -1), 'W': (0, -1), 'NW': (-1, -1)
    }
    
    TARGET_WORD = "FUCK"
    LETTERS = ['F', 'U', 'C', 'K']
    
    def __init__(self, seed: Optional[Union[str, int]] = None):
        """Initialize the game engine with optional seed for determinism."""
        if seed is not None:
            if isinstance(seed, str):
                # Convert string seed to integer hash
                seed = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
            random.seed(seed)
            self.seed = seed
        else:
            self.seed = None
    
    def generate_grid(self, size: int, requested_count: Union[int, Tuple[int, int]], 
                     distribution_mode: str = 'even', allow_overlap: bool = True,
                     directions_mode: str = 'all') -> Dict:
        """
        Generate a game grid with specified parameters.
        
        Args:
            size: Grid size (NxN)
            requested_count: Either exact count (int) or (min, max) tuple
            distribution_mode: 'even' or 'weighted' letter distribution
            allow_overlap: Whether word placements can overlap
            directions_mode: 'all', 'horizontal', or 'horiz_vert'
        
        Returns:
            Dict with grid, true_count, matches, and metadata
        """
        # Determine target count
        if isinstance(requested_count, tuple):
            min_count, max_count = requested_count
            target_count = random.randint(min_count, max_count)
        else:
            target_count = requested_count
        
        # Get allowed directions
        allowed_dirs = self._get_allowed_directions(directions_mode)
        
        max_retries = 25
        for attempt in range(max_retries):
            try:
                grid = self._create_empty_grid(size)
                matches = []
                
                # Place target words
                for _ in range(target_count):
                    if not self._place_word(grid, size, allowed_dirs, allow_overlap, matches):
                        raise ValueError("Failed to place word")
                
                # Fill remaining cells
                self._fill_grid(grid, size, distribution_mode)
                
                # Validate with scanner
                scan_result = self.scan_grid(grid, directions_mode)
                if scan_result['count'] == target_count:
                    return {
                        'grid': grid,
                        'true_count': target_count,
                        'matches': scan_result['matches'],
                        'metadata': {
                            'size': size,
                            'distribution_mode': distribution_mode,
                            'allow_overlap': allow_overlap,
                            'directions_mode': directions_mode,
                            'seed': self.seed
                        }
                    }
                    
            except ValueError:
                continue
        
        raise RuntimeError(f"Failed to generate valid grid after {max_retries} attempts. "
                          f"Try smaller grid, allow overlap, reduce count, or use even distribution.")
    
    def scan_grid(self, grid: List[List[str]], directions_mode: str = 'all') -> Dict:
        """
        Scan grid for all instances of the target word.
        
        Returns:
            Dict with count and list of matches (each match has start, direction, cells)
        """
        matches = []
        size = len(grid)
        allowed_dirs = self._get_allowed_directions(directions_mode)
        
        for row in range(size):
            for col in range(size):
                for dir_name, (dr, dc) in allowed_dirs.items():
                    match = self._check_word_at_position(grid, row, col, dr, dc, size)
                    if match:
                        # Normalize match to avoid duplicates
                        normalized = self._normalize_match(match)
                        if not self._is_duplicate_match(normalized, matches):
                            matches.append({
                                'start': (row, col),
                                'direction': dir_name,
                                'cells': match
                            })
        
        return {'count': len(matches), 'matches': matches}
    
    def _get_allowed_directions(self, mode: str) -> Dict[str, Tuple[int, int]]:
        """Get allowed directions based on mode."""
        if mode == 'horizontal':
            return {'E': self.DIRECTIONS['E'], 'W': self.DIRECTIONS['W']}
        elif mode == 'horiz_vert':
            return {k: v for k, v in self.DIRECTIONS.items() if k in ['N', 'S', 'E', 'W']}
        else:  # 'all'
            return self.DIRECTIONS.copy()
    
    def _create_empty_grid(self, size: int) -> List[List[str]]:
        """Create empty grid filled with None."""
        return [[None for _ in range(size)] for _ in range(size)]
    
    def _place_word(self, grid: List[List[str]], size: int, allowed_dirs: Dict,
                   allow_overlap: bool, matches: List) -> bool:
        """Attempt to place the target word in the grid."""
        max_attempts = 1000
        
        for _ in range(max_attempts):
            row = random.randint(0, size - 1)
            col = random.randint(0, size - 1)
            dir_name = random.choice(list(allowed_dirs.keys()))
            dr, dc = allowed_dirs[dir_name]
            
            # Check bounds
            end_row = row + dr * (len(self.TARGET_WORD) - 1)
            end_col = col + dc * (len(self.TARGET_WORD) - 1)
            
            if not (0 <= end_row < size and 0 <= end_col < size):
                continue
            
            # Check placement validity
            cells = []
            can_place = True
            
            for i, letter in enumerate(self.TARGET_WORD):
                r = row + dr * i
                c = col + dc * i
                cells.append((r, c))
                
                if grid[r][c] is not None:
                    if not allow_overlap or grid[r][c] != letter:
                        can_place = False
                        break
            
            if can_place:
                # Place the word
                for i, letter in enumerate(self.TARGET_WORD):
                    r = row + dr * i
                    c = col + dc * i
                    grid[r][c] = letter
                
                matches.append({
                    'start': (row, col),
                    'direction': dir_name,
                    'cells': cells
                })
                return True
        
        return False
    
    def _fill_grid(self, grid: List[List[str]], size: int, distribution_mode: str):
        """Fill empty cells with random letters."""
        if distribution_mode == 'weighted':
            # F:4, K:4, U:1, C:1 ratio
            weights = ['F'] * 4 + ['K'] * 4 + ['U'] + ['C']
        else:  # 'even'
            weights = self.LETTERS
        
        for row in range(size):
            for col in range(size):
                if grid[row][col] is None:
                    grid[row][col] = random.choice(weights)
    
    def _check_word_at_position(self, grid: List[List[str]], start_row: int, start_col: int,
                               dr: int, dc: int, size: int) -> Optional[List[Tuple[int, int]]]:
        """Check if target word exists starting at position in given direction."""
        cells = []
        word = ""
        
        for i in range(len(self.TARGET_WORD)):
            r = start_row + dr * i
            c = start_col + dc * i
            
            if not (0 <= r < size and 0 <= c < size):
                return None
            
            cells.append((r, c))
            word += grid[r][c]
        
        return cells if word == self.TARGET_WORD else None
    
    def _normalize_match(self, cells: List[Tuple[int, int]]) -> Tuple[Tuple[int, int], ...]:
        """Normalize match cells for duplicate detection."""
        return tuple(sorted(cells))
    
    def _is_duplicate_match(self, normalized_match: Tuple, matches: List[Dict]) -> bool:
        """Check if this match already exists."""
        for match in matches:
            if self._normalize_match(match['cells']) == normalized_match:
                return True
        return False


# === DAILY SEED MODULE ===

class DailySeed:
    """Handles deterministic date-based seeds."""
    
    @staticmethod
    def get_daily_seed(salt: str = "hmf") -> str:
        """Generate deterministic seed based on current UTC date."""
        utc_date = datetime.utcnow().strftime("%Y-%m-%d")
        return f"{salt}-{utc_date}"


# === RENDER MODULE ===

class GridRenderer:
    """Handles text rendering and highlighting of grids."""
    
    def render_grid(self, grid: List[List[str]]) -> str:
        """Render grid as formatted text."""
        lines = []
        for row in grid:
            lines.append(" ".join(row))
        return "\n".join(lines)
    
    def render_highlighted_grid(self, grid: List[List[str]], matches: List[Dict]) -> str:
        """Render grid with matched letters highlighted."""
        size = len(grid)
        highlighted = [[cell for cell in row] for row in grid]  # Copy grid
        
        # Track which cells are highlighted
        highlight_cells = set()
        for match in matches:
            for cell in match['cells']:
                highlight_cells.add(cell)
        
        # Apply highlighting
        lines = []
        for row in range(size):
            line_parts = []
            for col in range(size):
                if (row, col) in highlight_cells:
                    line_parts.append(f"[{grid[row][col]}]")
                else:
                    line_parts.append(f" {grid[row][col]} ")
            lines.append("".join(line_parts))
        
        return "\n".join(lines)
    
    def render_match_list(self, matches: List[Dict]) -> str:
        """Render list of matches with details."""
        if not matches:
            return "No matches found."
        
        lines = []
        for i, match in enumerate(matches, 1):
            start_row, start_col = match['start']
            direction = match['direction']
            cells = match['cells']
            
            cells_str = ",".join(f"({r+1},{c+1})" for r, c in cells)
            lines.append(f"#{i}: start=(row {start_row+1}, col {start_col+1}), "
                        f"dir={direction}, cells=[{cells_str}]")
        
        return "\n".join(lines)


# === CLI MODULE ===

class CLI:
    """Command-line interface for the game."""
    
    def __init__(self):
        self.engine = None
        self.renderer = GridRenderer()
    
    def main(self):
        """Main CLI entry point."""
        parser = self.create_parser()
        args = parser.parse_args()
        
        if args.command == 'play':
            self.play_game(args)
        elif args.command == 'daily':
            self.daily_game(args)
        elif args.command == 'print':
            self.print_puzzle(args)
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create command-line argument parser."""
        parser = argparse.ArgumentParser(description='HowManyFucks - Word search counting game')
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Play command
        play_parser = subparsers.add_parser('play', help='Play the game interactively')
        self.add_common_args(play_parser)
        play_parser.add_argument('--reveal', action='store_true', 
                               help='Show highlighted matches after guess')
        
        # Daily command
        daily_parser = subparsers.add_parser('daily', help='Play daily puzzle')
        daily_parser.add_argument('--size', type=int, default=10, choices=[8, 10, 15, 20],
                                help='Grid size (default: 10)')
        daily_parser.add_argument('--reveal', action='store_true',
                                help='Show highlighted matches after guess')
        daily_parser.add_argument('--weighted', action='store_true',
                                help='Use weighted letter distribution')
        
        # Print command
        print_parser = subparsers.add_parser('print', help='Generate and print puzzle')
        self.add_common_args(print_parser)
        print_parser.add_argument('--reveal', action='store_true',
                                help='Show true count and matches')
        
        return parser
    
    def add_common_args(self, parser):
        """Add common arguments to parser."""
        parser.add_argument('--size', type=int, default=10, choices=[8, 10, 15, 20],
                           help='Grid size (default: 10)')
        
        count_group = parser.add_mutually_exclusive_group()
        count_group.add_argument('--exact', type=int, help='Exact number of occurrences')
        count_group.add_argument('--min', type=int, default=0, help='Minimum occurrences (default: 0)')
        parser.add_argument('--max', type=int, default=5, help='Maximum occurrences (default: 5)')
        
        dist_group = parser.add_mutually_exclusive_group()
        dist_group.add_argument('--weighted', action='store_true',
                               help='Use weighted letter distribution')
        dist_group.add_argument('--even', action='store_true',
                               help='Use even letter distribution (default)')
        
        parser.add_argument('--seed', type=str, help='Seed for deterministic generation')
        
        overlap_group = parser.add_mutually_exclusive_group()
        overlap_group.add_argument('--allow-overlap', action='store_true', default=True,
                                  help='Allow word overlaps (default)')
        overlap_group.add_argument('--no-overlap', action='store_true',
                                  help='Forbid word overlaps')
        
        parser.add_argument('--directions', choices=['all', 'horizontal', 'horiz_vert'],
                           default='all', help='Allowed directions (default: all)')
    
    def play_game(self, args):
        """Play the interactive game."""
        while True:
            try:
                puzzle = self.generate_puzzle(args)
                self.play_single_round(puzzle, args.reveal)
                
                if input("\nPlay again? (y/n): ").lower().strip() != 'y':
                    break
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                break
    
    def daily_game(self, args):
        """Play the daily puzzle."""
        # Convert daily args to play args format
        class DailyArgs:
            def __init__(self, daily_args):
                self.size = daily_args.size
                self.exact = None
                self.min = 0
                self.max = 5
                self.weighted = daily_args.weighted
                self.even = not daily_args.weighted
                self.seed = DailySeed.get_daily_seed()
                self.allow_overlap = True
                self.no_overlap = False
                self.directions = 'all'
                self.reveal = daily_args.reveal
        
        daily_args_converted = DailyArgs(args)
        print("=== DAILY PUZZLE ===")
        print(f"Date: {datetime.utcnow().strftime('%Y-%m-%d')} (UTC)")
        print(f"Seed: {daily_args_converted.seed}")
        print()
        
        puzzle = self.generate_puzzle(daily_args_converted)
        self.play_single_round(puzzle, daily_args_converted.reveal)
    
    def print_puzzle(self, args):
        """Generate and print puzzle without playing."""
        puzzle = self.generate_puzzle(args)
        
        print("Generated Puzzle:")
        print(self.renderer.render_grid(puzzle['grid']))
        print()
        
        if args.reveal:
            print(f"True count: {puzzle['true_count']}")
            if puzzle['matches']:
                print("\nMatches found:")
                print(self.renderer.render_match_list(puzzle['matches']))
    
    def generate_puzzle(self, args) -> Dict:
        """Generate a puzzle based on arguments."""
        self.engine = GameEngine(args.seed)
        
        # Determine count parameters
        if hasattr(args, 'exact') and args.exact is not None:
            requested_count = args.exact
        else:
            requested_count = (args.min, args.max)
        
        # Determine distribution mode
        if args.weighted:
            distribution_mode = 'weighted'
        else:
            distribution_mode = 'even'
        
        # Determine overlap setting
        if hasattr(args, 'no_overlap') and args.no_overlap:
            allow_overlap = False
        else:
            allow_overlap = True
        
        return self.engine.generate_grid(
            size=args.size,
            requested_count=requested_count,
            distribution_mode=distribution_mode,
            allow_overlap=allow_overlap,
            directions_mode=args.directions
        )
    
    def play_single_round(self, puzzle: Dict, reveal: bool = False):
        """Play a single round of the game."""
        print(self.renderer.render_grid(puzzle['grid']))
        print()
        
        try:
            guess = int(input("Enter your count guess (integer): "))
        except ValueError:
            print("Invalid input. Please enter an integer.")
            return
        
        true_count = puzzle['true_count']
        
        if guess == true_count:
            print(f"Correct! There were {true_count} FUCK(s).")
        else:
            print(f"Not quite. The correct count is {true_count}.")
        
        if reveal and puzzle['matches']:
            print("\nHighlighted grid:")
            print(self.renderer.render_highlighted_grid(puzzle['grid'], puzzle['matches']))
            print("\nMatches found:")
            print(self.renderer.render_match_list(puzzle['matches']))


# === MAIN ENTRY POINT ===

def main():
    """Main entry point for the CLI application."""
    cli = CLI()
    cli.main()


if __name__ == "__main__":
    main()
