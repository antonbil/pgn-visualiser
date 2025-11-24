# This program requires the 'python-chess' library.
# Installation: pip install python-chess
import os
import tkinter as tk
from tkinter import ttk, filedialog, font
import chess
import chess.pgn
import io
import re
# The Pillow (PIL) library is required to robustly load PNGs in Tkinter.
from PIL import Image, ImageTk
from pathlib import Path
import json

# --- PGN DATA FOR DEMONSTRATION ---
PGN_WITH_EVENTS = """
[Event "Galaxy"]
[Site "Star"]
[Date "2025/01/02"]
[Round "15"]
[White "Notorious Man"]
[Black "Smart Guy"]
[Result "1-0"]

{ Stockfish 16.1 } 1. e4 e5 2. Nf3 Nc6 3. Bc4 Be7 { C50 Italian Game: Hungarian
Defense } 4. O-O { 0.41 } ( 4. d4 exd4 { 0.55/20 } ) 4... Nf6 5. d4 Nxd4 { 1.43 } ( 5... exd4 6. Nxd4 O-O 7. Nc3 d6 8. Re1 Nxd4 9. Qxd4 c6 10. Bf4 { 0.43/20 } ) 6. Nxe5 { 0.65 } ( 6. Bxf7+ Kf8 7. Nxe5 Nc6 8. f4 d6 9. Nxc6 bxc6 10. Bb3 Nxe4 { 1.35/22 } ) 6... Ne6 7. Nc3 { 0.31 } ( 7. Nxf7 Kxf7 8. e5 d5 9. exf6 dxc4 10. fxe7 Qxd1 11. Rxd1 b6 { 0.67/21 } ) 7... O-O 8. a3 { 0.24 } ( 8. Nf3 d6 { 0.42/19 } ) 8... d6 9. Nd3 { -0.44 } ( 9. Nf3 c6 { 0.20/19 } ) 9... c6 { 0.35 } ( 9... Nxe4 10. Nxe4 d5 11. Bxd5 Qxd5 12. Re1 Rd8 13. Bd2 b6 14. Nf4 { -0.37/21 } ) 10. Nf4 { -0.04 } ( 10. Ba2 Nc7 11. f4 Bg4 12. Qe1 Be6 13. Bxe6 Nxe6 14. Kh1 Re8 { 0.35/18 } ) 10... Nxf4 { 0.10 } ( 10... Qc7 11. Qf3 b5 12. Ba2 a5 13. Re1 Bd7 14. Nxe6 Bxe6 15. e5 { -0.06/19 } ) 11. Bxf4 b5 { 0.24 } ( 11... Nxe4 12. Nxe4 d5 13. Bxd5 Qxd5 14. Qxd5 cxd5 15. Nc3 Be6 16. Ne2 { 0.08/21 } ) 12. Ba2 { 0.02 } ( 12. Be2 Be6 13. Qd4 Qb8 14. Rad1 Rd8 15. h3 a5 16. Bf3 b4 { 0.26/19 } ) 12... Ba6 { 0.67 } ( 12... a5 13. h3 Be6 14. Bxe6 fxe6 15. e5 dxe5 16. Bxe5 Qxd1 17. Rfxd1 { 0.08/18 } ) 13. Re1 Bb7 { 0.90 } ( 13... Bc8 { 0.63/20 } ) 14. e5 { 0.46 } ( 14. Qd3 Nh5 { 0.92/18 } ) 14... dxe5 15. Bxe5 Qb6 { 1.07 } ( 15... Qxd1 16. Raxd1 { 0.45/19 } ) 16. Ne4 { -0.07 } ( 16. Qd3 Rad8 17. Qg3 Rd7 18. Rad1 Rxd1 19. Rxd1 Nh5 20. Qf3 Nf6 { 1.04/19 } ) 16... Rad8 { 0.00 } ( 16... Nxe4 17. Rxe4 c5 18. Bd5 Bxd5 19. Qxd5 Rad8 20. Qb3 Rfe8 21. Qf3 { -0.08/21 } ) 17. Nxf6+ Bxf6 18. Qg4 { -0.15 } ( 18. Qh5 g6 19. Qf3 Bxe5 20. Rxe5 c5 21. Qe3 Qc6 22. f3 Rfe8 { 0.00/22 } ) 18... Bxe5 { -0.01 } ( 18... c5 19. Qf4 { -0.25/21 } ) 19. Rxe5 Rd6 { 0.37 } ( 19... c5 20. Rae1 c4 21. c3 Rd2 22. R5e2 Rxe2 23. Qxe2 g6 24. Bb1 { -0.06/22 } ) 20. Qf4 { 0.31 } ( 20. Rae1 Rf6 21. Qe2 c5 22. h4 Rg6 23. Bd5 Bxd5 24. Rxd5 Re6 { 0.33/18 } ) 20... Rf6 21. Rf5 { -0.01 } ( 21. Qe3 Rd6 { 0.37/19 } ) 21... Rxf5 22. Qxf5 c5 23. Rd1 Qc6 { Mate in 3 } ( 23... c4 24. c3 g6 25. Qf4 Qe6 26. h4 Qe4 27. Qxe4 Bxe4 28. Bb1 { -0.04/22 } ) 24. f3 { 0.02 } ( 24. Qxf7+ Rxf7 25. Rd8+ Qe8 26. Rxe8# ) 24... Qb6 { 0.08 } ( 24... c4 25. c3 g6 26. Qf4 Re8 27. Bb1 Qc5+ 28. Kf1 Qe7 29. Qd2 { 0.01/23 } ) 25. Kf1 { -0.00 } ( 25. c3 g6 26. Qf4 c4+ 27. Kf1 Rd8 28. Re1 Kg7 29. Bb1 Qc5 { 0.13/22 } ) 25... c4 { 0.10 } ( 25... b4 26. Bc4 bxa3 27. bxa3 Ba6 28. Bxa6 Qxa6+ 29. Qd3 Qf6 30. Qd6 { -0.00/24 } ) 26. c3 Bc8 27. Qe4 { -0.00 } ( 27. Qe5 Rd8 28. Ke2 g6 29. Rxd8+ Qxd8 30. Bb1 Qb6 31. Qe8+ Kg7 { 0.09/21 } ) 27... g6 28. Bb1 Bf5 29. Qd4 { -0.45 } ( 29. Qe5 Bxb1 { -0.08/23 } ) 29... Qxd4 30. cxd4 Bxb1 31. Rxb1 Rd8 32. Rd1 { -0.86 } ( 32. b3 Rxd4 33. bxc4 bxc4 34. Ke2 Kf8 35. Rb4 Ke7 36. Ra4 a5 { -0.48/22 } ) 32... a5 { -0.03 } ( 32... f5 33. Ke2 Kf7 34. Ke3 Ke6 35. Re1 Kd5 36. Kd2 Kxd4 37. Re7 { -0.86/22 } ) 33. Ke2 { -0.50 } ( 33. d5 { -0.13/24 } ) 33... a4 { 0.00 } ( 33... Kf8 34. Kf2 { -0.52/21 } ) 34. Ke3 { -0.14 } ( 34. d5 Kf8 35. d6 Ke8 36. Rd5 Rb8 37. Kd2 b4 38. axb4 Rxb4 { 0.00/27 } ) 34... f5 { 0.90 } ( 34... Kf8 35. g4 { -0.35/20 } ) 35. d5 Kf7 36. Kd4 Rc8 { 1.66 } ( 36... Ke7 37. Re1+ Kd7 38. Re6 Rc8 39. Kc3 Rc5 40. Re5 Kd6 41. Kd4 { 0.73/24 } ) 37. Rd2 { 0.28 } ( 37. Re1 c3 38. bxc3 Rc4+ 39. Kd3 Rc5 40. Re5 f4 41. g3 fxg3 { 1.60/27 } ) 37... Ke7 38. Re2+ Kd7 39. Re6 { -0.00 } ( 39. Re3 Rb8 { 0.64/20 } ) 39... Rb8 { 3.28 } ( 39... c3 40. bxc3 Rc4+ 41. Kd3 Rc5 42. Ra6 Rxd5+ 43. Ke2 Rc5 44. Kd2 { -0.00/29 } ) 40. Kc5 h5 { 3.62 } ( 40... Kd8 41. Rd6+ Ke8 42. Rc6 Ra8 43. h4 Ra7 44. Kxb5 Kd7 45. Kc5 { 3.14/19 } ) 41. Rxg6 c3 { 5.08 } ( 41... Rc8+ 42. Rc6 Rg8 43. Rh6 Rc8+ 44. Kxb5 Rb8+ 45. Rb6 Rg8 46. g3 { 3.33/20 } ) 42. bxc3 Rc8+ 43. Rc6 b4 { 9.21 } ( 43... Rg8 44. g3 h4 45. gxh4 Rg2 46. Rd6+ Ke7 47. Re6+ Kd7 48. Kxb5 { 4.92/21 } ) 44. cxb4 Rxc6+ { Mate in 11 } ( 44... Rg8 45. b5 Rxg2 46. b6 Rc2+ 47. Kb5 Rd2 48. Ka6 Rxd5 49. Rh6 { 5.60/20 } ) 45. dxc6+ Kc7 46. b5 ( 46. h4 Kd8 47. Kd6 Ke8 48. b5 Kf7 49. b6 Kf8 50. b7 Kg7 51. Ke7 Kh6 52. Kf6 Kh7 53. b8=Q f4 54. Qc7+ Kh6 55. Qg7# ) 1-0

"""

#define the whereabouts of the json-settings file
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILENAME = "settings/configuration.json"
CONFIG_FILE_PATH = BASE_DIR / CONFIG_FILENAME

def _load_config():
    """
    Loads configuration from the JSON file.
    Provides robust error handling for missing files or invalid JSON.
    """
    print(f"Attempting to load configuration from: {CONFIG_FILE_PATH}")

    if not CONFIG_FILE_PATH.exists():
        print(f"Error: Configuration file not found at {CONFIG_FILE_PATH}. Using empty/default values.")
        # Return an empty dictionary to prevent the program from crashing
        return {}

    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("Configuration successfully loaded.", config)
        return config

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in {CONFIG_FILE_PATH}: {e}. Using empty/default values.")
        return {}
    except Exception as e:
        print(f"Unexpected error loading configuration: {e}. Using empty/default values.")
        return {}


def _save_config(default_directory: str, last_pgn_path: str):
    """
    Saves the current configuration (default directory and last PGN path)
    to the configuration JSON file.
    """

    # Ensure the configuration directory exists (e.g., the '.chess_viewer' folder)
    CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # The data structure to be saved
    new_config = {
        # Ensure paths are clean (no unnecessary whitespace)
        "default_directory": default_directory.strip(),
        "lastLoadedPgnPath": last_pgn_path.strip(),
    }

    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            # Use indent=4 for readability in the JSON file
            json.dump(new_config, f, indent=4)
        print(f"Configuration successfully saved to {CONFIG_FILE_PATH}")
    except Exception as e:
        print(f"ERROR: Failed to save configuration to {CONFIG_FILE_PATH}: {e}")

def get_settings():
        ## 1. Read configuration data
        config_data = _load_config()

        # 2. Assignment of Engine Mappings and Directories

        # The PGN directory
        default_pgn_dir = config_data.get("default_directory", "/home/user/Chess")
        lastLoadedPgnPath = config_data.get("lastLoadedPgnPath", "")
        print(f"Default PGN Directory: {default_pgn_dir}")

        return default_pgn_dir, lastLoadedPgnPath

# --- UTILITY FUNCTIONS FOR EVALUATION AND PGN ---

def get_cp_from_comment(comment):
    """
    Extracts the centipawn value from the PGN comment.
    """
    if not comment:
        return None
    try:
        comment = comment.strip()
        prefixes = ["+", "-", "0", "1", "2", "3","4", "5", "6", "7", "8", "9"]

        # Checking if the string starts with any element in the list
        res = comment.startswith(tuple(prefixes))
        if not res:
            return None
        match_eval = re.search(r'\[%eval\s*([#]?[-]?\d+\.?\d*)\]', comment)
        if match_eval:
            eval_str = match_eval.group(1)
        else:
            match_leading = re.search(r'([#]?[-+]?\d+\.?\d*)(?:/\d+)?', comment.strip())
            if match_leading:
                eval_str = match_leading.group(1).replace('+', '')
            else:
                return None

        if eval_str.startswith('#'):
            mate_val = int(eval_str[1:])
            return 100000 * (1 if mate_val > 0 else -1)

        return int(float(eval_str) * 100)

    except Exception:
        # Error during parsing, ignore this comment
        return None


def _format_pgn_history(move_list):
    """
    Formats a list of move data into a multi-line PGN snippet for display,
    including starting notation for Black, comments, and variations.
    """
    if not move_list:
        return "Starting position (first move of the game)."

    output = []
    current_line = ""

    # Determine if the sequence starts with Black
    starts_with_black = move_list[0]['player'] == chess.BLACK

    last_variation = None
    previous_variation = None
    for i, move in enumerate(move_list):
        move_number = move['move_number']
        move_san = move['san']
        player = move['player']

        # --- 1. Main move notation ---
        if player == chess.WHITE:
            # Start of White's move: New line or add White's move
            if current_line:
                output.append(current_line.strip())
            current_line = f"{move_number}. {move_san}"
        else:  # player == chess.BLACK
            if i == 0 and starts_with_black:
                # First move is Black: "Move number..."
                current_line = f"{move_number}. ... {move_san}"
            else:
                # Add Black's move
                current_line += f" {move_san}"

        # --- 2. Clean up and Add Engine Comment ---
        if move.get('comment'):
            # Regular expression to remove ALL evaluation scores, [%eval ...] and variation parentheses.
            # This prevents the raw variation text from being displayed twice in the comment.
            clean_comment = re.sub(
                r'\s*(?<![A-Za-z])([#]?[-+]?\d+\.?\d*)(?:/\d+)?\s*|\[%eval\s*([#]?[-]?\d+\.?\d*)\]|\s*\([^\)]*\)',
                '',
                move['comment']
            ).strip()

            if clean_comment:
                current_line += f" {{{clean_comment}}}"

        # --- 3. Add Variations (these are stored separately) ---
        if move.get('variations'):
            previous_variation = last_variation
            last_variation = move["variations"]

    if not previous_variation is None:
        for i, variation in enumerate(previous_variation):
            if i>0:
                current_line += "\n    " + str(variation)
    if current_line:
        output.append(current_line.strip())

    return "\n".join(output)

def get_all_significant_events(pgn_string):
    """
    Identifies ALL moves that caused a significant loss in advantage (> 50 cp).
    """
    pgn_io = io.StringIO(pgn_string)
    game = chess.pgn.read_game(pgn_io)

    if not game:
        print("Error: Could not read chess game from PGN string.")
        return []

    events = []
    board = game.board()
    prev_eval_cp = 0
    # List of ALL moves, including the move that caused the event
    moves_made_so_far = []

    # Iterate over the main line
    for node in game.mainline():
        if node.move is None:
            continue

        eval_before_cp = prev_eval_cp
        eval_after_cp = get_cp_from_comment(node.comment)

        fen_before_move = board.fen()
        move_number = board.fullmove_number
        player_who_moved = board.turn

        # --- SAN CONVERSION ---
        move_san = None
        try:
            move_san = board.san(node.move)
        except Exception as e:
            print(f"Warning: Error during SAN conversion for move {move_number} ({e})")
            continue

        # Add the data of the MOVE that was just checked to the history
        move_data = {
            'move_number': move_number,
            'player': player_who_moved,
            'san': move_san,
            'comment': node.comment,
            'variations':node.variations,
            # This is the 0-based index in the complete move list
            'full_move_index': len(moves_made_so_far)
        }
        moves_made_so_far.append(move_data)

        # --- EVENT CALCULATION ---
        if eval_after_cp is not None:
            if player_who_moved == chess.WHITE:
                # Loss of advantage for White is (Previous Eval - New Eval)
                event_score = abs(eval_before_cp - eval_after_cp)
                player_str = "White"
            else:
                # Loss of advantage for Black is (New Eval - Previous Eval)
                event_score = eval_after_cp - eval_before_cp
                player_str = "Black"


            events.append({
                    'score': event_score,
                    'fen': fen_before_move,
                    'move_text': f"{move_number}. {'. ...' if player_who_moved == chess.BLACK else ''}{move_san}",
                    'player': player_str,
                    'eval_before': eval_before_cp / 100.0,
                    'eval_after': eval_after_cp / 100.0,
                    'full_move_history': list(moves_made_so_far),
                    'move_index': len(moves_made_so_far) - 1  # Index of the move
                })

        # --- EXECUTE MOVE AND TRACK EVALUATION ---
        try:
            board.push(node.move)
        except Exception as e:
            print(f"!!! ERROR !!! Cannot execute move '{move_san}' on the board: {e}")
            return events

        if eval_after_cp is not None:
            # For the next move, the 'eval_after' of this move becomes the 'prev_eval'
            prev_eval_cp = eval_after_cp

    return events, game


def select_key_positions(all_events):
    """
    Selects the events based on the new logic:
    1. Biggest event from each of the 3 equal parts of the game.
    2. Top 3 of the remaining event (globally).
    """
    if not all_events:
        return []

    # Determine the total number of half-moves (including the last move in the event list)
    total_half_moves = all_events[-1]['full_move_history'][-1]['full_move_index'] + 1

    # Use a set to prevent selecting the same event twice
    selected_indices = set()
    selected_events = []

    # 1. Divide the game into 3 (almost) equal parts
    part_size = total_half_moves // 3

    # Determine the ranges based on the 0-based move index
    ranges = [
        (0, part_size),  # Part 1 (Opening/Early Middlegame)
        (part_size, 2 * part_size),  # Part 2 (Middlegame)
        (2 * part_size, total_half_moves)  # Part 3 (Late Middlegame/Endgame)
    ]

    print(f"Total half-moves: {total_half_moves}. Part size: {part_size}.")

    # Select the biggest event in each part
    for part_num, (start_index, end_index) in enumerate(ranges):
        best_in_part = None
        max_score = -1

        for event in all_events:
            move_idx = event['move_index']

            # Check if the move falls within the current range
            if start_index <= move_idx < end_index:
                if event['score'] > max_score and move_idx not in selected_indices:
                    max_score = event['score']
                    best_in_part = event

        if best_in_part:
            best_in_part['source'] = f"Biggest Event in Part {part_num + 1}"
            selected_events.append(best_in_part)
            selected_indices.add(best_in_part['move_index'])

    # 2. Select the top 3 of the remaining events
    remaining_events = sorted(
        [b for b in all_events if b['move_index'] not in selected_indices],
        key=lambda x: x['score'],
        reverse=True
    )

    # Add the top 3 to the selection
    for i in range(min(3, len(remaining_events))):
        remaining_events[i]['source'] = f"Global Top {i + 1} (Remaining)"
        selected_events.append(remaining_events[i])
        selected_indices.add(remaining_events[i]['move_index'])

    # Sort the selected events chronologically for display
    selected_events.sort(key=lambda x: x['move_index'])

    return selected_events


# ----------------------------------------------------------------------
# 1. PIECE IMAGE MANAGER (THE FACTORY/SINGLETON)
# This class is responsible for loading all images once from the disk.
# ----------------------------------------------------------------------
class PieceImageManager:
    """
    Manages the loading and storage of chess piece images from disk into memory.
    This ensures images are loaded only once, regardless of how many boards
    (ChessVisualizer instances) are created.
    """

    def __init__(self, square_size, image_dir_path):
        self.square_size = square_size
        self.image_dir_path = image_dir_path
        # Dictionary to hold the loaded ImageTk.PhotoImage objects
        self.images = {}

        # Mapping from chess.Piece.symbol() to the filename prefix
        self.piece_map = {
            'K': 'wK', 'Q': 'wQ', 'R': 'wR', 'B': 'wB', 'N': 'wN', 'P': 'wP',
            'k': 'bK', 'q': 'bQ', 'r': 'bR', 'b': 'bB', 'n': 'bN', 'p': 'bP',
        }

        self._load_images()

    def _load_images(self):
        """
        Loads and resizes the PNG images and stores them in self.images.
        """
        try:
            for symbol, filename_prefix in self.piece_map.items():
                # Assemble the full path
                image_path = os.path.join(self.image_dir_path, f"{filename_prefix}.png")

                # 1. Load the image using PIL (Pillow)
                img = Image.open(image_path)

                # 2. Resize the image to match the square size
                img = img.resize((self.square_size, self.square_size), Image.Resampling.LANCZOS)

                # 3. Convert to a Tkinter-compatible format and store
                self.images[symbol] = ImageTk.PhotoImage(img)

            print(f"Chess images successfully loaded and cached from: {self.image_dir_path}")

        except FileNotFoundError:
            print(f"Error: The directory or files were not found at {self.image_dir_path}.")
            print("Make sure the path is correct and that the filenames are correct (wK.png, bQ.png, etc.).")
            # Re-raise the error to stop execution since assets are critical
            raise
        except Exception as e:
            print(f"An unexpected error occurred while loading the images: {e}")
            raise
# --- TKINTER CLASS ---

class ChessEventViewer:
    """
    Tkinter application to display the top events from an analyzed PGN.
    """

    def __init__(self, master, pgn_string, square_size, image_manager, default_pgn_dir, lastLoadedPgnPath):
        self.num_events = None
        self.sorted_events = None
        self.master = master
        self.image_manager = image_manager
        self.default_pgn_dir = default_pgn_dir
        self.default_pgn_string = pgn_string
        self.lastLoadedPgnPath = lastLoadedPgnPath

        # Variable to hold the selected file path for display
        self.pgn_filepath = tk.StringVar(value="No PGN file selected.")

        # --- TOP LEVEL FILE READER WIDGET ---
        self._create_file_reader_widget(master)
        master.protocol("WM_DELETE_WINDOW", self.on_closing)


        self.square_size = square_size
        self.board_size = self.square_size * 8

        self.color_light = "#F0D9B5"
        self.color_dark = "#B58863"
        self.piece_font = font.Font(family="Arial", size=int(self.square_size * 0.5), weight="bold")
        # --- 1. INITIALIZE STRINGVARS (THE DATA MODEL) ---
        # These variables hold the actual text content and are linked to the UI Labels.
        # When a new PGN is loaded, we only update these variables, and the UI refreshes automatically.
        self.meta_data_vars = {
            "Event": tk.StringVar(master, value="Laden..."),
            "Site": tk.StringVar(master, value="Laden..."),
            "Date": tk.StringVar(master, value="????.??.??"),
            "White": tk.StringVar(master, value="Witte Speler"),
            "Black": tk.StringVar(master, value="Zwarte Speler"),
            "Result": tk.StringVar(master, value="*"),
            "WhiteElo": tk.StringVar(master, value="????"),
            "BlackElo": tk.StringVar(master, value="????"),
        }
        # Frame for the PGN Meta-information (top)
        self.meta_info_frame = tk.Frame(master, bd=2, relief=tk.GROOVE, padx=10, pady=5)
        self.meta_info_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        self._create_meta_info_widgets(self.meta_info_frame)

        # --- TABBED INTERFACE FOR EVENTS ---
        self._create_tabbed_event_viewer(master)
        self.load_initial_pgn(lastLoadedPgnPath)

    def _create_tabbed_event_viewer(self, master):
        """
        Creates the ttk.Notebook (tabbed interface) to display individual chess diagrams/events.
        """
        main_frame = tk.Frame(master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # The Notebook widget is the container for the tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill="both")

        # Load the simulated events into tabs
        # self._populate_tabs(SIMULATED_EVENTS)

    def _populate_tabs(self, events):
        """
        Clears existing tabs and populates the Notebook with new events.
        """
        # Clear all existing tabs if any
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)

        if not events:
            empty_frame = ttk.Frame(self.notebook, padding=20)
            tk.Label(empty_frame, text="No annotated critical events found in PGN.", foreground="gray").pack()
            self.notebook.add(empty_frame, text="No Events")
            return

        for i, event in enumerate(events):
            self._add_event_tab(i + 1, event)


    def _create_meta_info_widgets(self, parent_frame):
        """
        CREATES the static Label widgets for the PGN metadata fields.
        This function MUST only be called ONCE (in _setup_ui).
        It links each value label to a specific StringVar in self.meta_data_vars.
        """

        label_font = ('Arial', 10)
        value_font = ('Arial', 10, 'bold')

        # --- Left Column (Event, Site, Date) ---
        tk.Label(parent_frame, text="Event:", font=label_font).grid(row=0, column=0, sticky='w')
        # BINDING: The text property of this Label is bound to self.meta_data_vars["Event"]
        tk.Label(parent_frame, textvariable=self.meta_data_vars["Event"], font=value_font).grid(row=0, column=1,
                                                                                                sticky='w', padx=5)

        tk.Label(parent_frame, text="Site:", font=label_font).grid(row=1, column=0, sticky='w')
        tk.Label(parent_frame, textvariable=self.meta_data_vars["Site"], font=value_font).grid(row=1, column=1,
                                                                                               sticky='w', padx=5)

        tk.Label(parent_frame, text="Date:", font=label_font).grid(row=2, column=0, sticky='w')
        tk.Label(parent_frame, textvariable=self.meta_data_vars["Date"], font=value_font).grid(row=2, column=1,
                                                                                               sticky='w', padx=5)

        # --- Right Column (White, Black, Result) ---

        # Add horizontal separation between the columns
        parent_frame.grid_columnconfigure(2, minsize=50)

        # White Player Info
        tk.Label(parent_frame, text="White:", font=label_font).grid(row=0, column=3, sticky='w')  # Wit: (White)
        # Name
        tk.Label(parent_frame, textvariable=self.meta_data_vars["White"], font=value_font).grid(row=0, column=4,
                                                                                                sticky='w')
        # ELO
        tk.Label(parent_frame, textvariable=self.meta_data_vars["WhiteElo"], font=label_font).grid(row=0, column=5,
                                                                                                   sticky='w', padx=5)

        # Black Player Info
        tk.Label(parent_frame, text="Black:", font=label_font).grid(row=1, column=3, sticky='w')  # Zwart: (Black)
        # Name
        tk.Label(parent_frame, textvariable=self.meta_data_vars["Black"], font=value_font).grid(row=1, column=4,
                                                                                                sticky='w')
        # ELO
        tk.Label(parent_frame, textvariable=self.meta_data_vars["BlackElo"], font=label_font).grid(row=1, column=5,
                                                                                                   sticky='w', padx=5)

        # Result Info
        tk.Label(parent_frame, text="Result:", font=label_font).grid(row=2, column=3, sticky='w')  # Uitslag: (Result)
        # Result Value (with special formatting/color logic)
        tk.Label(parent_frame, textvariable=self.meta_data_vars["Result"], font=('Arial', 12, 'bold'),
                 foreground="red").grid(row=2, column=4, columnspan=2, sticky='w', padx=5)

    def _update_meta_info(self, game):
        """
        UPDATES the underlying StringVar objects with the metadata from the newly loaded PGN game.
        This is the ONLY function that should be called when loading a new PGN.
        It uses the 'game' object's headers to set the new values.
        """

        # Mapping from PGN header tag to the internal StringVar key
        tag_map = {
            "Event": "Event", "Site": "Site", "Date": "Date",
            "White": "White", "Black": "Black", "Result": "Result",
            "WhiteElo": "WhiteElo", "BlackElo": "BlackElo",
        }

        for tag, var_key in tag_map.items():
            # Retrieve the value, defaulting to "N/A" if the tag is missing
            value = game.headers.get(tag, "N/A")

            # CRITICAL STEP: Update the value of the bound StringVar.
            # Tkinter automatically pushes this change to the linked Label widgets.
            if var_key in self.meta_data_vars:
                self.meta_data_vars[var_key].set(str(value))

        # Example of conditional styling: Update the color of the result label based on the outcome
        result_label = self.meta_info_frame.grid_slaves(row=2, column=4)[0]
        result_value = game.headers.get("Result")

        if result_value == "1-0":
            result_label.configure(foreground="green")
        elif result_value == "0-1":
            result_label.configure(foreground="blue")
        elif result_value == "1/2-1/2":
            result_label.configure(foreground="darkorange")
        else:
            result_label.configure(foreground="red")

    def on_closing(self):
        _save_config(self.default_pgn_dir,self.lastLoadedPgnPath)
        exit()

    def load_initial_pgn(self, lastLoadedPgnPath):
        """Loads a simulated PGN game upon application startup."""
        if not lastLoadedPgnPath:
            print("INFO: No previous PGN path found in settings. Loading default data.")
            self.do_new_analysis(self.default_pgn_string)
            return

        # 1. Strip and create Path object
        clean_path = lastLoadedPgnPath.strip()
        file_path = Path(clean_path)

        print(f"DEBUG: Attempting to load previous PGN from path: '{clean_path}'")
        print(f"DEBUG: Absolute path resolved by Pathlib: '{file_path.resolve()}'")

        # 2. Check if path points to existing file
        if file_path.is_file():
            print("SUCCESS: File found and is a valid file. Loading data.")

            self._read_file_and_analyze(clean_path)

            # Update the path string
            self.pgn_filepath.set(clean_path)

        else:
            print("WARNING: File not found or is a directory. Loading default data.")
            # If the file does not exist or is a directory, use the default pgn
            self.do_new_analysis(self.default_pgn_string)

    def _clear_content_frame(self):
        return
        """HELPER: Removes all widgets from the scrollable content frame."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Reset scrollposition to top
        self.event_canvas.yview_moveto(0)

    def do_new_analysis(self, pgn_string):
        self._clear_content_frame()
        # Perform the advanced analysis
        print("Starting full PGN analysis...")
        all_events, game = get_all_significant_events(pgn_string)
        self._update_meta_info(game)
        print(f"Full analysis complete. {len(all_events)} significant events found (> 50 cp loss).")

        self.sorted_events = select_key_positions(all_events)
        self.num_events = len(self.sorted_events)
        self.populate_event_tabs(self.sorted_events)
        self.master.title(f"Chess Game Analysis: {self.num_events} Critical Positions Selected")

    def _read_file_and_analyze(self, filepath):
        """Reads the PGN-content of the file and start the analysis."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                pgn_content = f.read()

            self.do_new_analysis(pgn_content)
            self.lastLoadedPgnPath = filepath

        except Exception as e:
            error_message = f"ERROR: Failed to read PGN file: {e}"
            print(error_message)
            self.pgn_filepath.set(error_message)
            self._clear_content_frame()

    def _create_file_reader_widget(self, master):
        """
        Creates the UI elements for selecting and displaying the PGN file path.
        This is placed at the top of the window.
        """
        file_reader_frame = tk.Frame(master, padx=10, pady=5, bd=1, relief=tk.RIDGE)
        file_reader_frame.pack(fill="x", padx=10, pady=10)

        # 1. Label/Entry for File Path Display
        path_label = tk.Label(
            file_reader_frame,
            textvariable=self.pgn_filepath,
            anchor="w",
            relief=tk.SUNKEN,
            bg="white",
            padx=5
        )
        path_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # 2. Button to open the file dialog
        select_button = tk.Button(
            file_reader_frame,
            text="Select PGN File",
            command=self._select_pgn_file
        )
        select_button.pack(side="right")

        print("File Reader Widget initialized.")

    def _select_pgn_file(self):
        """
        Opens the system's file dialog to choose a PGN file.
        """
        # Define the file types allowed
        filetypes = (
            ('PGN files', '*.pgn'),
            ('All files', '*.*')
        )

        # Open the dialog and store the path
        filepath = filedialog.askopenfilename(
            title='Open a PGN file',
            initialdir=self.default_pgn_dir,  # Start in the current working directory
            filetypes=filetypes
        )

        if filepath:
            # Update the displayed path
            self.pgn_filepath.set(filepath)
            print(f"File selected: {filepath}")

            # --- NEXT STEP: Call the function to process the file ---
            self._read_file_and_analyze(filepath)
        else:
            print("File selection cancelled.")


    def draw_pieces(self, canvas, board):
        """
        Draws the pieces on a given Canvas, using PNG images.

        The original code that used Unicode characters has been replaced by code
        that uses the preloaded PNG images via canvas.create_image.
        """
        # First, delete any existing pieces
        canvas.delete("piece")

        for square in chess.SQUARES:
            piece = board.piece_at(square)

            if piece:
                # 1. Determine the screen coordinates (x, y)
                rank = chess.square_rank(square)
                file = chess.square_file(square)

                # Calculate the row and column on the Tkinter canvas (row 0 = rank 8)
                tk_row = 7 - rank
                tk_col = file

                # The coordinates (x, y) must refer to the CENTER of the square
                x = tk_col * self.square_size + self.square_size / 2
                y = tk_row * self.square_size + self.square_size / 2

                # 2. Determine the key for the image (e.g., 'P', 'n', 'K')
                symbol = piece.symbol()

                # We check if the image for this symbol has been loaded
                if symbol in self.image_manager.images:
                    # We retrieve the cached image from the manager
                    piece_img = self.image_manager.images.get(symbol)

                    # 3. Draw the image in the center of the square
                    canvas.create_image(
                        x, y,
                        image=piece_img,
                        tags="piece"  # Use tags for easy removal/movement later
                    )
                # If the image is not loaded, the piece is skipped.


    def _add_event_tab(self, index, event_data):
        """
        Creates and adds a single tab containing the detailed diagram and PGN snippet.
        This incorporates the logic previously in draw_event_diagram.
        """

        # --- 1. Create the container Frame for the tab content ---
        tab_frame = ttk.Frame(self.notebook, padding="15 10 15 10")
        tab_frame.columnconfigure(1, weight=1)  # Ensure the PGN column expands

        # Extract the PGN snippet text
        pgn_snippet_text = event_data['move_history']

        # --- COLUMN 0: DIAGRAM & INFO (Left) ---
        title = f"{index}: {event_data['move_text']}"

        diagram_block = tk.LabelFrame(tab_frame,
                                      text=title,
                                      padx=10, pady=10, font=("Helvetica", 12, "bold"), bd=2, relief=tk.GROOVE)
        diagram_block.grid(row=0, column=0, padx=(0, 15), pady=5, sticky='nsw')

        # 1. Info Label
        info_text = (
            f"Move: {event_data['move_text']}\n"
            f"Change: {event_data['score'] / 100.0:.2f} P\n"
            f"Eval BEFORE: {event_data['eval_before']:.2f} | Eval AFTER: {event_data['eval_after']:.2f}"
        )
        tk.Label(diagram_block, text=info_text, justify=tk.LEFT, pady=5).pack(anchor="w")

        # 2. Canvas for the board
        board_canvas = tk.Canvas(diagram_block, width=self.board_size, height=self.board_size,
                                 borderwidth=0, highlightthickness=1, highlightbackground="black")
        board_canvas.pack(pady=10)

        # Initialize the board with the FEN BEFORE the event
        try:
            board = chess.Board(event_data['fen'])
        except ValueError:
            tk.Label(diagram_block, text="Ongeldige FEN", fg="red").pack()
            board_canvas.pack_forget()
            self.notebook.add(tab_frame, text=f"ERROR {index}")
            return

        # Draw the board squares
        for r in range(8):
            for c in range(8):
                x1 = c * self.square_size
                y1 = r * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                color = self.color_light if (r + c) % 2 == 0 else self.color_dark
                board_canvas.create_rectangle(x1, y1, x2, y2, fill=color, tags="square")

        # Draw the pieces
        self.draw_pieces(board_canvas, board)

        # Mark the starting square of the event-move
        try:
            move_san = event_data['move_text'].split()[-1].strip('.')
            move_to_highlight = board.parse_san(move_san)
            from_square = move_to_highlight.from_square

            from_rank = 7 - chess.square_rank(from_square)
            from_file = chess.square_file(from_square)

            x1 = from_file * self.square_size
            y1 = from_rank * self.square_size

            # Add a yellow highlight to the starting square
            board_canvas.create_rectangle(x1, y1, x1 + self.square_size, y1 + self.square_size,
                                          outline="#FFC300", width=4, tags="highlight")
            board_canvas.tag_raise("highlight", "square")
            board_canvas.tag_raise("text")
        except Exception as e:
            print(f"Error highlighting move: {e}")
            pass

        # --- COLUMN 1: PGN SNIPPET & DESCRIPTION (Right) ---
        pgn_block = tk.LabelFrame(tab_frame, text="Relevant Moves",
                                  padx=10, pady=10, font=("Helvetica", 12, "bold"), bd=2, relief=tk.GROOVE)
        pgn_block.grid(row=0, column=1, padx=(15, 0), pady=5, sticky='nsew')

        # ESSENTIAL: Ensures the column containing the Text widget expands
        pgn_block.grid_columnconfigure(0, weight=1)

        # ** Configure ROW 0 (the only remaining row) to expand **
        pgn_block.grid_rowconfigure(0, weight=1)

        # 1. Text widget for the PGN text (Now in Row 0)
        pgn_text_widget = tk.Text(pgn_block, wrap=tk.WORD, font=("Consolas", 10), relief=tk.FLAT)
        pgn_text_widget.insert(tk.END, pgn_snippet_text)
        pgn_text_widget.config(state=tk.DISABLED)

        # Use sticky='nsew' to make the widget fill the entire cell area
        pgn_text_widget.grid(row=0, column=0, sticky='nsew')

        # Add a scrollbar next to the Text widget
        pgn_scrollbar = tk.Scrollbar(pgn_block, command=pgn_text_widget.yview)
        # The scrollbar is in the same row (0) as the Text widget and fills vertically
        pgn_scrollbar.grid(row=0, column=1, sticky='ns')
        pgn_text_widget.config(yscrollcommand=pgn_scrollbar.set)

        # 2. Add the frame to the Notebook
        tab_title = f"{index}. {event_data['move_text']}"  # Short title for the tab
        self.notebook.add(tab_frame, text=tab_title)

    def populate_event_tabs(self, events):
        """
        Removes existing tabs and populates the Notebook with new events,
        calculating the PGN snippet for each event.
        """
        # 1. CLEAR ALL EXISTING TABS
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)

        if not events:
            empty_frame = ttk.Frame(self.notebook, padding=20)
            tk.Label(empty_frame, text="No significant events (>= 50 cp) found in the PGN data.",
                     pady=50, padx=20).pack()
            self.notebook.add(empty_frame, text="No Events")
            return

        last_move_index = -1

        for i, event in enumerate(events):
            # This is the move index that caused the event
            current_move_index = event['move_index']

            # Select the moves that are NEW since the last displayed event
            moves_to_display = event['full_move_history'][last_move_index + 1: current_move_index + 1]

            # Format the PGN for display
            pgn_snippet = _format_pgn_history(moves_to_display)

            # 2. PREPARE DATA FOR THE TAB
            tab_data = {
                # Data directly needed for the _add_event_tab
                "fen": event['fen'],
                "move_text": event.get('move_text', '...'),
                "score": event.get('score', 0),
                "eval_before": event.get('eval_before', 0.0),
                "eval_after": event.get('eval_after', 0.0),
                "event_type": event.get('event_type', 'Event'),
                "move_history": pgn_snippet,
            }

            # 3. CALL THE TAB CREATOR (Replaces the draw_event_diagram call)
            self._add_event_tab(i + 1, tab_data)

            # Update the counter for the next iteration
            last_move_index = current_move_index

        # Select the first tab
        if self.notebook.tabs():
            self.notebook.select(self.notebook.tabs()[0])

# --- Main execution ---

if __name__ == "__main__":
    try:
        root = tk.Tk()
        # Set the initial size to 1200x800
        root.geometry("1200x850")

        IMAGE_DIRECTORY = "Images/60"
        SQUARE_SIZE = 60  # Size of the squares in pixels
        # 2. Initialize the Asset Manager (LOADS IMAGES ONCE)
        # If this fails (e.g., FileNotFoundError), the program stops here.
        asset_manager = PieceImageManager(SQUARE_SIZE, IMAGE_DIRECTORY)

        default_pgn_dir, lastLoadedPgnPath = get_settings()

        app = ChessEventViewer(root, PGN_WITH_EVENTS, SQUARE_SIZE, asset_manager, default_pgn_dir, lastLoadedPgnPath)
        root.mainloop()
    except ImportError:
        error_msg = ("Error: The 'python-chess' library is not installed.\n"
                     "Install this with: pip install python-chess")
        error_root = tk.Tk()
        error_root.title("Installation Required")
        tk.Label(error_root, text=error_msg, padx=20, pady=20).pack()
        tk.Button(error_root, text="Close", command=error_root.destroy).pack(pady=10)
        error_root.mainloop()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")