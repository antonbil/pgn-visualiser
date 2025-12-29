# This program requires the 'python-chess' library.
# Installation: pip install python-chess
import os, sys
import tkinter as tk
from tkinter import ttk, filedialog, font, messagebox
import chess
import chess.pgn
import io
import re
# The Pillow (PIL) library is required to robustly load PNGs in Tkinter.
from PIL import Image, ImageTk
from pathlib import Path
import json
from pgn_editor.pgn_editor import ChessAnnotatorApp, Tooltip
from pgn_editor.pgn_editor import GameChooserDialog, BOARD_THEMES, SettingsDialog
from pgn_entry.pgn_entry import PGNEntryApp, PieceImageManager1
import cairosvg
from io import BytesIO
import traceback

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


def _save_config(default_directory: str, last_pgn_path: str, engine_path: str, piece_set: str, square_size: int, board: str, engine_depth: int):
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
        "engine_path": engine_path.strip(),
        "piece_set": piece_set.strip(),
        "square_size":square_size,
        "engine_depth": engine_depth,
        "board":board.strip()
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
        piece_set = config_data.get("piece_set", "staunty")
        engine_path = config_data.get("engine_path", "")
        square_size = config_data.get("square_size", 80)
        engine_depth = config_data.get("engine_depth", 17)
        board1 = config_data.get("board", "red")
        print(f"Default PGN Directory: {default_pgn_dir}")

        return default_pgn_dir, lastLoadedPgnPath, engine_path, piece_set, square_size, board1, engine_depth


# Functie om de zet-index uit de oorspronkelijke data te halen
def _get_move_number(move_string):
    """
    Haalt het zetnummer op uit de PGN-string (bijv. '1.' of '45.' -> 1 of 45).
    Deze is verbeterd om meercijferige zetnummers te ondersteunen.
    """
    parts = move_string.strip().split()
    if not parts:
        return None

    first_part = parts[0]

    # Controleer of de eerste token eindigt op '.' en meer dan alleen de punt is
    if first_part.endswith('.') and len(first_part) > 1:
        num_part = first_part[:-1]  # Alles behalve de punt
        if num_part.isdigit():
            return int(num_part)

    return None

# --- UTILITY FUNCTIONS FOR EVALUATION AND PGN ---

def get_cp_from_comment(comment):
    """
    Extracts the centipawn value from the PGN comment.
    """
    if not comment:
        return None
    try:
        comment = comment.strip().replace("Stockfish:", "").strip()
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
    move_nr = 0
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
                current_line += f" {move_san}".replace('\n',  ' ')

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

    return output


def select_key_positions(all_events):
    """
    1. Filter out moves 1 & 2.
    2. Merge consecutive/related events in the full list first.
    3. Select the best events from the merged candidates.
    """
    if not all_events:
        return []

        # 1. PRE-FILTER: Skip the first 2 full moves (half-moves 0-3)
    all_events = [e for e in all_events if e['move_index'] >= 4]
    if not all_events:
        return []

    # Determine total length and define the three game phases
    total_half_moves = all_events[-1]['move_index'] + 1
    part_size = total_half_moves // 3
    ranges = [(0, part_size), (part_size, 2 * part_size), (2 * part_size, total_half_moves)]

    merged_candidates = []

    # 2. CREATE REGIONAL ISLANDS
    for start, end in ranges:
        # Identify all events within the current phase
        part_events = [e for e in all_events if start <= e['move_index'] < end]
        if not part_events:
            continue

        # Sort by impact (score) to identify the most significant moments
        part_events.sort(key=lambda x: x['score'], reverse=True)

        # DYNAMIC FALLBACK: Ensure we keep enough moves even in "perfect" games.
        # We take at least 5 moves, but up to 10 to create the necessary 'gaps'.
        min_to_keep = max(5, min(10, len(part_events)))
        interesting_in_part = part_events[:min_to_keep]

        # Sort chronologically to prepare for the clustering logic
        interesting_in_part.sort(key=lambda x: x['move_index'])

        # 3. CLUSTER THE ISLANDS (within this specific phase)
        # Groups moves that are part of the same sequence (diff <= 2)
        if interesting_in_part:
            current_cluster = [interesting_in_part[0]]
            for i in range(1, len(interesting_in_part)):
                curr = interesting_in_part[i]
                # Check if move belongs to current sequence
                if curr['move_index'] - current_cluster[-1]['move_index'] <= 2:
                    current_cluster.append(curr)
                else:
                    # Sequence broken: store the most significant move of the cluster
                    merged_candidates.append(max(current_cluster, key=lambda x: x['score']))
                    current_cluster = [curr]
            # Add the final cluster of the phase
            merged_candidates.append(max(current_cluster, key=lambda x: x['score']))

    if len(merged_candidates) < 6:
        merged_candidates = all_events
    # 4. FINAL SELECTION PROCESS
    selected_events = []
    selected_indices = set()

    # A. Select the single best representative for each of the 3 parts
    for part_num, (start, end) in enumerate(ranges):
        part_candidates = [e for e in merged_candidates if start <= e['move_index'] < end]
        if part_candidates:
            best = max(part_candidates, key=lambda x: x['score'])
            ev_copy = best.copy()
            ev_copy['source'] = f"Part {part_num + 1}"
            selected_events.append(ev_copy)
            selected_indices.add(ev_copy['move_index'])

    # B. Select the Top 3 global highlights from the remaining candidates
    remaining = sorted(
        [e for e in merged_candidates if e['move_index'] not in selected_indices],
        key=lambda x: x['score'],
        reverse=True
    )

    for i in range(min(3, len(remaining))):
        ev_copy = remaining[i].copy()
        ev_copy['source'] = f"Top {i + 1} (Global)"
        selected_events.append(ev_copy)
        selected_indices.add(ev_copy['move_index'])

    # Sort the final 6 key positions chronologically for the user
    selected_events.sort(key=lambda x: x['move_index'])
    return selected_events

# ----------------------------------------------------------------------
# 1. PIECE IMAGE MANAGER (THE FACTORY/SINGLETON)
# This class is responsible for loading all images once from the disk.
# ----------------------------------------------------------------------
class PieceImageManager:
    """
    Beheert het laden en cachen van schaakstukafbeeldingen.
    Ondersteunt nu het kiezen van een specifieke set (bijv. set '2' voor bK2.svg).
    """

    def __init__(self, square_size, image_dir_path, set_identifier="staunty"):
        """
        :param set_identifier: De ID van de gewenste set ('1', '2', '3', etc.).
                               Dit wordt gebruikt om de juiste bestandsnaam te kiezen.
        """
        self.square_size = square_size
        self.image_dir_path = image_dir_path
        self.set_identifier = str(set_identifier) # Zorg ervoor dat het een string is
        self.images = {} # Dictionary om de ImageTk.PhotoImage objecten vast te houden

        # We gebruiken de basisprefixen (wK, bQ)
        self.piece_map = {
            'K': 'wK', 'Q': 'wQ', 'R': 'wR', 'B': 'wB', 'N': 'wN', 'P': 'wP',
            'k': 'bK', 'q': 'bQ', 'r': 'bR', 'b': 'bB', 'n': 'bN', 'p': 'bP',
        }

        self._load_images()

    def _load_images(self):
        """
        Laadt en wijzigt de afmetingen van de afbeeldingen van de GESELECTEERDE SET.
        Zoekt eerst naar een SVG, dan naar een PNG, met de set-identifier eraan vast.
        """
        # Wis oude afbeeldingen om Garbage Collector problemen te voorkomen bij herladen
        self.images = {}

        print(f"Loading chess-pieces '{self.set_identifier}' from: {self.image_dir_path}")

        for symbol, base_prefix in self.piece_map.items():

            # De dynamische prefix: bijv. 'wK2' of 'bN3'
            filename_prefix = f"{base_prefix}"

            # Lijst van te proberen bestandsformaten, in volgorde van voorkeur
            # Zoals u in uw map heeft: wK2.svg, wK3.svg, of wK1.png
            extensions = ['.svg', '.png']

            img = None
            image_path = None

            for ext in extensions:
                image_path = os.path.join(self.image_dir_path, self.set_identifier, f"{filename_prefix}{ext}")

                if os.path.exists(image_path):
                    try:
                        if ext == '.svg':
                            # Voor SVG's hebben we Cairosvg nodig (vereist installatie)
                            #print(f"Loading SVG: {image_path}")
                            # Hieronder moet u de cairosvg import en logica toevoegen
                            # Omdat cairosvg extern is, houden we hier de generieke PNG/fallback logica aan

                            # Tenzij u de cairosvg logica al heeft toegevoegd:
                            png_bytes = cairosvg.svg2png(url=image_path)
                            img = Image.open(BytesIO(png_bytes))

                            # Fallback: We laten de SVG-laadlogica weg uit dit voorbeeld
                            # om afhankelijkheden te minimaliseren, tenzij u het expliciet vraagt.
                            # We gaan verder met het proberen van PNG.
                            # continue # Skip SVG load for simplicity if cairosvg not set up

                        elif ext == '.png':
                            # Laad de PNG (werkt altijd met Pillow)
                            img = Image.open(image_path)
                            break # Bestand gevonden, stop de lus

                    except Exception as e:
                        print(f"Error with loading from {image_path}: {e}")
                        img = None # Bij fout, probeer volgende extensie

            # Controleer of we een afbeelding hebben geladen
            if img:
                # 2. Afmetingen aanpassen
                img = img.resize((self.square_size, self.square_size), Image.Resampling.LANCZOS)

                # 3. Converteren naar Tkinter-formaat en opslaan
                self.images[symbol] = ImageTk.PhotoImage(img)
            else:
                print(f"Warning: No image found for set {self.set_identifier} and piece {symbol}. Leave empty.")

        if self.images:
            print(f"Chess-set '{self.set_identifier}' successfully loaded.")
        else:
            print(f"Error: No chess-pieces loaded. Check if files exist: *K{self.set_identifier}.(png/svg)")
IMAGE_DIRECTORY = "pgn_entry/Images/60"
TOUCH_WIDTH = 25
# --- TKINTER CLASS ---

class ChessEventViewer:
    """
    Tkinter application to display the top events from an analyzed PGN.
    """

    def __init__(self, master, pgn_string, square_size, image_manager, default_pgn_dir, lastLoadedPgnPath, engine_path, piece_set, board="Standard", engine_depth=17):
        image_manager = PieceImageManager(square_size, IMAGE_DIRECTORY, piece_set)
        self.current_movelistbox_info = None
        self.engine_path = engine_path
        self.engine_depth = engine_depth
        self.piece_set = piece_set
        self.board = board
        self.all_moves_chess = None
        self.all_games = []
        self.swap_colours = False
        self.current_move_index = None
        self.game = None
        self.board_canvases = []
        self.current_board_canvas = None
        self.num_events = None
        self.sorted_events = None
        self.master = master
        self.image_manager = image_manager
        self.default_pgn_dir = default_pgn_dir
        self.default_pgn_string = pgn_string
        self.lastLoadedPgnPath = lastLoadedPgnPath

        self.comment_widgets = []
        self.variation_widgets = []
        self.move_display_widgets = []

        # Variable to hold the selected file path for display
        self.pgn_filepath = tk.StringVar(value="No PGN file selected.")

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.current_game_index = 0
        self.num_games = 0
        self.game_counter_var = tk.StringVar(value=f"Game 1 of {self.num_games}")
        self.game_descriptions = []
        self.selected_game_var = tk.StringVar(value=None)

        self.current_game_moves = []

        self.move_listbox = None
        self.move_listboxes = []
        self.current_movelistbox = None
        self.current_tab = 0

        self.square_size = square_size
        self.board_size = self.square_size * 8

        self.theme_name = board
        self.set_theme()

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
        self._setup_menu_bar(master)
        # Hoofdcontainer: grid_columnconfigure op main_frame is correct.
        main_frame = tk.Frame(master, padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=0)  # Kolom 0 (Meta)
        main_frame.grid_columnconfigure(1, weight=1)  # Kolom 1 (Navigatie)
        main_frame.pack(fill='x', anchor='n')

        # Configureer rij 0 om verticaal te kunnen uitrekken
        main_frame.grid_rowconfigure(0, weight=1)
        # Geef rij 1 (indien gebruikt) gewicht 0, zodat het niet uitrekt
        main_frame.grid_rowconfigure(1, weight=0)

        # 1. Frame for the PGN Meta-information (links, rij 0)
        self.meta_info_frame = tk.Frame(main_frame, bd=2, relief=tk.GROOVE, padx=10, pady=5)
        # Plaats in rij 0, kolom 0. De sticky optie 'nwes' zorgt ervoor dat het zich uitrekt.
        self.meta_info_frame.grid(row=0, column=0)

        # 2. Frame voor de GEGROEPEERDE Navigatie (rechts, rij 0)
        self.navigation_container = tk.Frame(main_frame, padx=20, pady=5)
        self.navigation_container.grid(row=0, column=1, sticky='nwes')
        # Binnen de container gebruiken we pack om de items nu HORIZONTAAL te plaatsen

        # 2a. Frame voor Game Navigation (Links in de container)
        self.nav_panel = tk.Frame(self.navigation_container)
        # Gebruik side=tk.LEFT om de frames naast elkaar te plaatsen.
        self.nav_panel.pack(side=tk.LEFT, padx=5, pady=5)  # Fill=tk.Y om verticaal op te vullen

        # 2b. Frame voor Move Navigation (Rechts van de Game Navigatie)
        self.move_nav_panel = tk.Frame(self.navigation_container, pady=10)
        # Gebruik side=tk.LEFT zodat deze direct naast de vorige wordt geplaatst.
        self.move_nav_panel.pack(side=tk.LEFT,  padx=5)  # Fill=tk.Y om verticaal op te vullen

        # --- TOP LEVEL FILE READER WIDGET ---
        file_reader_frame = tk.Frame(self.navigation_container, padx=10, pady=5, bd=1, relief=tk.RIDGE)
        file_reader_frame.pack(fill="x", padx=10, pady=10)



        self._create_file_reader_widget(file_reader_frame)
        self._create_meta_info_widgets(self.meta_info_frame)
        self._create_navigation_widgets(self.nav_panel)
        self._create_move_navigation_widgets(self.move_nav_panel)

        # --- TABBED INTERFACE FOR EVENTS ---
        self._create_tabbed_event_viewer(master)
        self.load_initial_pgn(lastLoadedPgnPath)

    def set_theme(self):
        self.selected_theme = next(
            (theme for theme in BOARD_THEMES if theme["name"] == self.theme_name),
            BOARD_THEMES[0]  # Gebruik Standard als fallback
        )
        self.color_light, self.color_dark = (self.selected_theme["light"], self.selected_theme["dark"])

    # --- Menu Logic ---

    def _setup_menu_bar(self, master):
        """
        Creates the menu bar with File and Game options.
        """
        menubar = tk.Menu(master)
        master.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load PGN...", command=self.load_pgn_file)
        #file_menu.add_command(label="Save PGN...", command=self.save_pgn_file)
        file_menu.add_separator()
        file_menu.add_command(label="Choose Game...", command=self._open_game_chooser)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=master.quit)

        # Game Menu
        game_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=game_menu)
        game_menu.add_command(label="Editor", command=lambda: self.start_editor(), state=tk.NORMAL, accelerator="Ctrl+Left")
        game_menu.add_command(label="Enter new Game", command=lambda: self.enter_new_game(), state=tk.NORMAL, accelerator="Ctrl+Right")
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Modify json-settings", command=lambda: self.show_settings_dialog(), state=tk.NORMAL)
        settings_menu.add_command(label="Swap Colours", command=lambda: self.swap_colours_func())

        self.game_menu = game_menu

    def _setup_quick_toolbar(self, parent):
        """
        Creates a compact row of icon-only buttons for common tasks using GRID.
        """
        toolbar_frame = tk.Frame(parent)
        # Note: Do not pack toolbar_frame here.
        # The calling function should use .grid(row=..., column=...) to place this frame.

        btn_style = {
            "font": ("Segoe UI Symbol", 10),
            "width": 3,
            "height": 1,
            "relief": tk.FLAT,
            "bg": "#f0f0f0"
        }

        # 1. Open File Button
        self.open_btn = tk.Button(
            toolbar_frame,
            text="\U0001F4C2",
            command=self.load_pgn_file,
            **btn_style
        )
        self.open_btn.grid(row=0, column=0, padx=2)  # Use grid instead of pack

        # 2. Choose Game Button
        self.choose_btn = tk.Button(
            toolbar_frame,
            text="\u2630",
            command=self._open_game_chooser,
            **btn_style
        )
        self.choose_btn.grid(row=0, column=1, padx=2)

        # 3. Swap Colors Button
        self.swap_btn = tk.Button(
            toolbar_frame,
            text="\u21C5",
            command=self.swap_colours_func,
            **btn_style
        )
        self.swap_btn.grid(row=0, column=2, padx=2)

        # 4. Exit Button (placed at a higher column index to keep it right)
        self.exit_btn = tk.Button(
            toolbar_frame,
            text="\u23FB",
            command=self.master.destroy,
            fg="red",
            **btn_style
        )
        # Give the previous column weight so the exit button stays on the right
        toolbar_frame.grid_columnconfigure(3, weight=1)
        self.exit_btn.grid(row=0, column=4, padx=2)

        def on_enter(e):
            e.widget.config(bg="#dddddd")

        def on_leave(e):
            e.widget.config(bg="#f0f0f0")

        self.swap_btn.bind("<Enter>", on_enter)
        self.swap_btn.bind("<Leave>", on_leave)

        # 3. Add Tooltips (Optional, helps users know what the icons do)
        Tooltip(self.open_btn, "Open PGN File")
        Tooltip(self.swap_btn, "Flip Board (Swap Colors)")
        # Tooltip(self.save_btn, "Save PGN File")
        Tooltip(self.choose_btn, "Choose game")
        Tooltip(self.exit_btn, "Exit program")
        return toolbar_frame

    def _save_config_wrapper(self, *args):

        # Update the internal attributes after saving,
        #                                   state=tk.NORMAL)
        self.default_pgn_dir = args[0]
        self.engine_path = args[2]
        new_piece_set = args[3]
        piece_set_changed = (new_piece_set != self.piece_set)
        self.piece_set = args[3]
        new_square_size = int(args[4])
        size_changed = (new_square_size != self.square_size)
        self.square_size = new_square_size
        self.board = args[5]
        self.engine_depth = int(args[6])
        self.theme_name = self.board
        self.set_theme()
        _save_config(*args)
        if piece_set_changed or size_changed:
            self.force_restart()
        #self.image_manager = PieceImageManager(self.square_size, IMAGE_DIRECTORY, self.piece_set)
        #self._create_tabbed_event_viewer(self.master)
        self.display_diagram_move(self.current_move_index)

    def force_restart(self):
        """
        Closes the current application and starts a fresh instance.
        """
        # 1. Ask for confirmation (Optional but recommended)
        if not messagebox.askyesno("Restart", "Settings have changed. Restart to see them?"):
            return

        # 2. Close the Tkinter window properly
        self.master.destroy()

        # 3. Get the path to the current Python executable and the script
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def _open_game_chooser(self):
        """
        Opens the Game Chooser dialog, which handles game selection and switching.
        """
        if not hasattr(self, 'all_games') or not self.all_games:
            messagebox.showinfo("Information", "No PGN games are currently loaded.")
            return
        print("self.swap_colours a", self.swap_colours)

        GameChooserDialog(
            master=self.master,
            all_games=self.all_games,
            current_game_index=self.current_game_index,
            # pass the method that will be executed after selection
            switch_callback=self._switch_to_game
        )

    def _switch_to_game(self, index):
        """
        Sets the current game, rebuilds the move list, and resets the UI.
        """
        selected_game = self.all_games[index]

        # Define the Exporter: Set headers, VARIATIONS and COMMENTS to True
        exporter = chess.pgn.StringExporter(
            headers=True,
            variations=True,
            comments=True
        )

        # Convert back the found game (including variants/comments)
        single_pgn_string = selected_game.accept(exporter)

        # Reset the current game index to the first game
        self.current_game_index = index
        self.set_game_var_descriptions(self.current_game_index)

        # Do the analysis of the first game
        self.do_new_analysis(single_pgn_string)
        print("selected index:", index)


    def load_pgn_file(self):
        """
        Opens a dialog to select a PGN file and loads all games from it.
        """
        filepath = filedialog.askopenfilename(
            defaultextension=".pgn",
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")],
            title="Choose a PGN file to load"
        )
        if filepath:
            try:
                self.lastLoadedPgnPath = filepath
                self._read_file_and_analyze(self.lastLoadedPgnPath)
            except Exception as e:
                messagebox.showerror("Loading Error", f"Could not read the file: {e}")

    def start_editor(self):
        new_window = tk.Toplevel(self.master)
        new_window.title("Update Game")

        try:
            string_var_value = self.lastLoadedPgnPath
        except:
            string_var_value = ""
        app = ChessAnnotatorApp(new_window, string_var_value, self.engine_path, hide_file_load=True, image_manager=self.image_manager,
                                square_size=85, current_game_index=self.current_game_index, piece_set=self.piece_set,
                                board=self.board, swap_colours=self.swap_colours, call_back = self.annotator_callback, engine_depth=self.engine_depth)

        new_window.focus_set()

        #parameters: /home/user/Schaken/2025-12-11-Anton-Gerrit-annotated.pgn /home/user/Schaken/stockfish-python/Python-Easy-Chess-GUI/Engines/stockfish-ubuntu-x86-64-avx2 False <__main__.PieceImageManager1 object at 0x78f90a0dfb30> 75 0 ../../../Images/piece/tatiana Rosewood
        #parameters: /home/user/Schaken/2025-12-11-Anton-Gerrit-annotated.pgn /home/user/Schaken/stockfish-python/Python-Easy-Chess-GUI/Engines/stockfish-ubuntu-x86-64-avx2 True None 75 -1 staunty Standard

    def annotator_callback(self, file_name):
        #reload the dta from filename, check if selected_index is still valid
        self.lastLoadedPgnPath = file_name
        self._read_file_and_analyze(self.lastLoadedPgnPath)
        #messagebox.showinfo("Information", "No PGN games are currently loaded.", parent=self.master,)
        pass

    def enter_new_game(self):

        SQUARE_SIZE = 60  # Size of the squares in pixels
        # 2. Initialize the Asset Manager (LOADS IMAGES ONCE)
        # If this fails (e.g., FileNotFoundError), the program stops here.
        # asset_manager = PieceImageManager1(SQUARE_SIZE, IMAGE_DIRECTORY, "2")

        new_window = tk.Toplevel(self.master)
        new_window.title("New Game Entry")

        app = PGNEntryApp(new_window, self.image_manager, self.pgn_filepath, square_size=self.square_size, call_back=self.pgn_entry_callback,color_light = self.color_light,
        color_dark = self.color_dark)

        new_window.focus_set()

    def pgn_entry_callback(self, pgn_chess):
        print("callback received in visualise",pgn_chess)
        new_window = tk.Toplevel(self.master)
        new_window.title("Update New Game")
        ChessAnnotatorApp(new_window, "default.pgn", self.engine_path, hide_file_load=True,
                          image_manager=self.image_manager,
                          square_size=85, current_game_index=0, piece_set=self.piece_set,
                          board=self.board, swap_colours=self.swap_colours, call_back=self.annotator_callback)
        pass

    def save_pgn_file(self):
        """
        Saves the current game, including headers and commentary, to a PGN file.
        """
        if not self.game:
            messagebox.showwarning("Save Failed", "No game loaded to save.")
            return

        # Ask the user where to save the file
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pgn",
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")],
            title="Save PGN Game"
        )

        if filepath:
            try:
                pass
            except Exception as e:
                messagebox.showerror("Saving Error", f"Could not save the file: {e}")

    def _move_selected(self, event):
        """
        Determines the move and move number based on the Listbox content,
        even if a comment or variation line is clicked.
        """
        try:
            # 1. Determine the Listbox index based on the vertical click position (event.y)
            # This is the row index in the Listbox (incl. comment lines)
            # 1. Determine the row height and the y-position of the first item.
            # bbox(0) returns (x, y, width, height) of the item with index 0.
            bbox_result = self.current_movelistbox.bbox(0)

            if not bbox_result:
                # Can happen if Listbox is empty
                print("Cannot determine row height (Listbox empty).")
                return

            # The height of one row in pixels (index 3 of the bbox tuple)
            row_height = bbox_result[3]+1
            # The y-position of the first visible row relative to the Listbox top (index 1)
            y_offset_of_first_item = bbox_result[1]

            if row_height <= 0:
                print("Error: Row height is zero or negative.")
                return

            # 2. Determine the base index (the index of the item currently at the top of the Listbox).
            # We use 'nearest(0)' to get the scroll position. Although 'nearest(event.y)'
            # failed, 'nearest(0)' should work for the scroll offset.
            try:
                first_visible_index = self.current_movelistbox.nearest(0)
            except tk.TclError:
                # Fall back to 0 if nearest(0) fails
                first_visible_index = 0

            # 3. Calculate the index of the clicked row.
            # event.y is the click coordinate relative to the Listbox top.
            # We subtract the y-position of the first row to normalize the starting point.
            # We divide this by the row height (integer division).
            visible_index_offset = (event.y - y_offset_of_first_item) // row_height

            # The total Listbox index
            listbox_index = first_visible_index + visible_index_offset

            # 2. Clear existing selections
            self.current_movelistbox.selection_clear(0, tk.END)

            # 3. Search upwards to find the move line
            target_move_number = None

            # Loop backwards from the clicked index to the beginning (index 0)
            for i in range(listbox_index, -1, -1):
                line_content = self.current_movelistbox.get(i).strip()

                # Check if the line starts with a number followed by a period
                # (e.g., "1." or "12.")
                move_match = re.match(r'^(\d+)\.', line_content)

                if move_match:
                    # This is the move line!
                    target_move_number = int(move_match.group(1))

                    break

            # 4. Process results
            if target_move_number is not None:

                # update board position

                real_move_index = (target_move_number - 1) * 2
                self.display_diagram_move(real_move_index)

            else:
                # This should only happen if there are no moves in the list at all.
                print("No move found.")
                print("No valid move found for this selection.")

        except tk.TclError:
            # Activated by a click in the empty space below the items.
            print("Click detected outside a valid Listbox item.")
        except Exception as e:
            # Unexpected error
            print(f"An unexpected error occurred: {e}")

    def _get_square_coords(self, rank, file):
        """
        Translates chess rank/file to canvas pixel coordinates.
        Handles board flipping via self.swap_colours.
        """
        if self.swap_colours:
            # Black at bottom: Rank 0 is at the top, File 0 is at the right
            display_rank = rank
            display_file = 7 - file
        else:
            # White at bottom: Rank 7 is at the top, File 0 is at the left
            display_rank = 7 - rank
            display_file = file

        x1 = display_file * self.square_size
        y1 = display_rank * self.square_size
        x2 = x1 + self.square_size
        y2 = y1 + self.square_size

        return x1, y1, x2, y2

    def display_diagram_move(self, real_move_index: int):
        board = self.game.board()
        last_move = None
        previous_board = self.game.board()
        # Simulate every move in the mainline up to the desired index
        try:
            # Loop over all moves up to the real_move_index
            for i in range(real_move_index + 1):
                if i < len(self.all_moves_chess):
                    move = self.all_moves_chess[i]
                    # Execute the move on the board
                    if last_move:
                        previous_board.push(last_move)
                    last_move = move
                    board.push(move)

                else:
                    # This happens if the target move index is too high
                    print(f"Warning: Move sequence ends after index {i}.")
                    break

        except IndexError:
            print(f"Error: The requested index is out of range.")
            return

        except Exception as e:
            # This catches illegal moves if the pgn were corrupt
            print(f"Error while simulating the moves: {e}")
            return
        self.update_move_info(board, real_move_index)
        self.current_move_index = real_move_index
        chess_move = board.fullmove_number#int((real_move_index + 1)/2 - 1)
        if self.current_move_index % 2 == 1:
            chess_move = chess_move - 1
        # A. Deselect all selected items
        self.current_movelistbox.selection_clear(0, tk.END)
        for diagram_move in self.get_info_current_listbox()["move_index_map"]:
            if diagram_move[0]==chess_move:
                index_to_select = diagram_move[1]

                # B. Select the item on the specific index (i)
                self.current_movelistbox.selection_set(index_to_select)

                # C. Scroll the Listbox so that the selected item will be visible
                self.current_movelistbox.see(index_to_select)
        # Clear the entire self.current_board_canvas
        self.current_board_canvas.delete("all")
        # Initialize the board with the FEN BEFORE the event

        # Draw the board squares
        for square in chess.SQUARES:
            rank = chess.square_rank(square)
            file = chess.square_file(square)

            x1, y1, x2, y2 = self._get_square_coords(rank, file)

            # Determine color (light/dark)
            color = self.color_light if (rank + file) % 2 != 0 else self.color_dark
            self.current_board_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

            # 4. Highlight Last Move
        if last_move:
            for sq in [last_move.from_square, last_move.to_square]:
                r, f = chess.square_rank(sq), chess.square_file(sq)
                x1, y1, x2, y2 = self._get_square_coords(r, f)

                self.current_board_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline="#FFC300", width=4, tags="highlight"
                )

            # 5. Draw Pieces
            # Note: Ensure your draw_pieces function also uses _get_square_coords
            # internally to place piece images correctly!
        self.draw_pieces(self.current_board_canvas, board)

        # Final Layering
        self.current_board_canvas.tag_raise("highlight")

    def get_info_current_listbox(self):
        """
        Analyzes the move Listbox and returns information about
        the move numbers and their corresponding Listbox row indices.

        Returns a dict:
        - 'min_move_number': The lowest move number found (int).
        - 'max_move_number': The highest move number found (int).
        - 'move_index_map': A list of tuples (move_number, listbox_index).
        """
        if not self.current_movelistbox_info is None:
            return self.current_movelistbox_info
        # Initialization
        min_move_number = float('inf')
        max_move_number = float('-inf')
        move_index_map = []  # List of (move_number, listbox_index) pairs

        # Regex to match a move number followed by a period at the start of a line (e.g., "1." or "12.")
        move_pattern = re.compile(r'^(\d+)\.')

        moves_added = []

        last_index = 0

        # Iterate over all rows in the Listbox
        for i in range(self.current_movelistbox.size()):
            # Get the content of the row and strip whitespace
            line_content = self.current_movelistbox.get(i).strip()
            if line_content.startswith(' '):
                continue

            # Check for a move number pattern
            match = move_pattern.match(line_content)


            if match:
                # Process the found move number
                move_number = int(match.group(1))

                # Add to the mapping
                if not move_number in moves_added:
                    move_index_map.append((move_number, i))
                    moves_added.append(move_number)

                # Update min and max
                if move_number < min_move_number:
                    min_move_number = move_number
                if move_number > max_move_number:
                    max_move_number = move_number
                # get index of move
                splits = line_content.split(" ")
                last_index = (move_number - 1) * 2
                if len(splits) == 3:
                    last_index = last_index + 1

        # Check if any moves were found and reset min/max if the list was empty
        if not move_index_map:
            min_move_number = 0
            max_move_number = 0

        # Return the collected information
        self.current_movelistbox_info = {
            'min_move_number': min_move_number,
            'max_move_number': max_move_number,
            'move_index_map': move_index_map,
            'last_index': last_index
        }
        if self.current_move_index is None:
            self.current_move_index = last_index
        return self.current_movelistbox_info
    # --- WIDGET: MOVE LIST (Listbox) ---
    def _create_move_list_widget(self, parent_frame):
        """
        Creates the Listbox for displaying the moves (PGN).
        """

        # 1. Listbox for a structured, clickable list of moves
        self.move_listbox = tk.Listbox(
            parent_frame,
            selectmode=tk.SINGLE,
            font=("Consolas", 10),
            relief=tk.FLAT
        )
        self.move_listboxes.append(self.move_listbox)
        self.move_listbox.grid(row=0, column=0, sticky='nsew')

        # 2. Scrollbar
        move_list_scrollbar = ttk.Scrollbar(parent_frame, command=self.move_listbox.yview)
        move_list_scrollbar.grid(row=0, column=1, sticky='ns')
        parent_frame.grid_columnconfigure(1, minsize=TOUCH_WIDTH)
        #move_list_scrollbar = tk.Scrollbar(parent_frame, command=self.move_listbox.yview)
        #move_list_scrollbar.grid(row=0, column=1, sticky='ns')
        self.move_listbox.config(yscrollcommand=move_list_scrollbar.set)

        # 3. Populate the Listbox with move data from the model
        for move_pair in self.current_game_moves:
            self.move_listbox.insert(tk.END, move_pair)

        # 4. Add binding for action upon selection (clicking a move)
        self.move_listbox.bind('<ButtonRelease-1>', self._move_selected)

    def _go_to_first_move(self):
        """Go to the first move of the current game."""
        info = self.get_info_current_listbox()
        first = 2 * (info["min_move_number"] - 1)
        if first < 0:
            first = 0
        self.display_diagram_move(first)

    def _go_to_previous_move(self):
        """Go to the previous move in the game."""
        info = self.get_info_current_listbox()
        if self.current_move_index > 2 * (info["min_move_number"] - 1):
            self.display_diagram_move(self.current_move_index - 1)

    def _go_to_next_move(self):
        """Go to the next move in the game."""
        info = self.get_info_current_listbox()
        if self.current_move_index < 2*(info["max_move_number"]-1) and self.current_move_index < len(self.all_moves_chess):
            self.display_diagram_move(self.current_move_index + 1)

    def _go_to_last_move(self):
        """Go to the last move of the game."""
        info = self.get_info_current_listbox()
        number_ = 2 * (info["max_move_number"] - 1)
        if number_ >= len(self.all_moves_chess):
            number_ = self.all_moves_chess
        self.display_diagram_move(number_)

    def _create_move_navigation_widgets(self, parent_frame):
        """Creates buttons for move navigation within the current game."""

        # Use a single frame to arrange both the label and the buttons horizontally
        button_container = tk.Frame(parent_frame)
        # Anchor='w' (West/Left) to keep the whole block left-aligned
        button_container.pack(pady=10)



    def _prev_game(self):
        """Navigates to the previous game in the list."""
        if self.current_game_index > 0:
            self.current_game_index -= 1
            self.set_game_var_descriptions(self.current_game_index)
            self.do_new_analysis_game(self.all_games[self.current_game_index])
        else:
            print("First game reached.")

    def _next_game(self):
        """Navigates to the next game in the list."""
        if self.current_game_index < self.num_games - 1:
            self.current_game_index += 1
            self.set_game_var_descriptions(self.current_game_index)
            self.do_new_analysis_game(self.all_games[self.current_game_index])
        else:
            print("Last game reached.")

    def _select_game(self, event=None):
        """
        Function to select a game via the Combobox dropdown.
        The 'event' parameter is required by the Combobox binding.
        """
        selected_description = self.selected_game_var.get()
        print(f"Action: Game selected: {selected_description}")

        # Search for the index of the selected description
        try:
            new_index = self.game_descriptions.index(selected_description)
            if new_index != self.current_game_index:
                self.current_game_index = new_index
                self.set_game_var_descriptions(new_index)
                self.do_new_analysis_game(self.all_games[new_index])
        except ValueError:
            print(f"Error: Description '{selected_description}' niet gevonden.")

    def _create_navigation_widgets(self, parent_frame):
        """
        CREATES the navigation panel (Game Counter, Dropdown, and Prev/Next buttons).
        Aangepast: Label en knoppen zijn horizontaal gegroepeerd en gecentreerd.
        """
        button_font = ('Arial', 10, 'bold')

        # 2. Container for Horizontal Grouping (Label + Buttons)
        # Use this frame to place the counter and the navigation buttons side-by-side
        game_nav_group = tk.Frame(parent_frame)
        # Fixed padding on the right to separate from Move Navigation
        game_nav_group.pack(side=tk.LEFT, padx=(0, 20))

        # 2. Group: MOVE NAVIGATION (<| / < / > / |>)
        # This group follows directly in the parent_frame
        move_nav_group = tk.Frame(parent_frame)
        move_nav_group.pack(side=tk.LEFT)

        # --- 1. Populating Game Navigation (Left) ---

        # 1a. Game Number (Game X of Y)
        tk.Label(
            game_nav_group,
            textvariable=self.game_counter_var,
            font=button_font
        ).pack(side=tk.LEFT, padx=(5, 5))  # Reduced padding

        # 1b. Previous/Next Game Buttons
        # No extra frame (button_frame) needed, buttons directly in the group
        tk.Button(
            game_nav_group,
            text="<<",
            command=self._prev_game,
            font=button_font,
            width=5,  # Slightly wider for readability
            relief=tk.RAISED, bd=1  # Harmonized style
        ).pack(side=tk.LEFT, padx=(5, 1))  # Reduced space between buttons

        tk.Button(
            game_nav_group,
            text=">>",
            command=self._next_game,
            font=button_font,
            width=5,
            relief=tk.RAISED, bd=1  # Harmonized style
        ).pack(side=tk.LEFT, padx=(1, 5))

        # --- 2. Populating Move Navigation (Right) ---
        # Place the buttons directly in the move_nav_group

        # Go to first move
        tk.Button(move_nav_group, text="|<", command=self._go_to_first_move,
                  width=4, relief=tk.RAISED, bd=1).pack(side=tk.LEFT, padx=(5, 1))

        # Go to previous move
        tk.Button(move_nav_group, text="<", command=self._go_to_previous_move,
                  width=4, relief=tk.RAISED, bd=1).pack(side=tk.LEFT, padx=1)

        # Go to next move
        tk.Button(move_nav_group, text=">", command=self._go_to_next_move,
                  width=4, relief=tk.RAISED, bd=1).pack(side=tk.LEFT, padx=1)

        # Go to last move
        tk.Button(move_nav_group, text=">|", command=self._go_to_last_move,
                  width=4, relief=tk.RAISED, bd=1).pack(side=tk.LEFT, padx=(1, 5))

    def set_game_var_descriptions(self, current_game_index: int):
        # Updates the index, the selected Combobox variable, and the game counter text.
        if len(self.game_descriptions)-1 < current_game_index or current_game_index < 0:
            self.current_game_index = len(self.game_descriptions)-1
            return
        #self.current_game_index = current_game_index
        self.selected_game_var.set(self.game_descriptions[current_game_index])

        self.game_counter_var.set(f"Game {self.current_game_index + 1} of {self.num_games}")

    def _create_tabbed_event_viewer(self, master):
        """
        Creates a draggable interface using PanedWindow to separate
        the Notebook and the Move Info sidebar.
        """
        # Main container for the content area
        # We use a PanedWindow instead of a standard Frame
        self.main_paned_window = tk.PanedWindow(
            master,
            orient=tk.HORIZONTAL,
            sashrelief=tk.RAISED,
            sashwidth=10,  # Increases the thickness of the bar itself
            sashpad=2,  # Adds invisible padding around the bar to catch clicks
        )
        self.main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.main_paned_window.config(showhandle=True, handlepad=10, handlesize=15)

        # 1. Left Side: The Notebook (Board and Move List)
        # We place the Notebook inside a Frame so we can manage its internal expansion
        left_container = tk.Frame(self.main_paned_window)

        self.notebook = ttk.Notebook(left_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_change)

        # Add the left container to the PanedWindow
        # stretch="always" ensures the Notebook gets the extra space when resizing
        self.main_paned_window.add(left_container, stretch="always")

    def _show_variation_preview(self, start_node):
        """
        Creates a popup window with a structured layout: move numbers,
        White/Black moves, and comments aligned in columns.
        """
        preview_win = tk.Toplevel(self.master)
        preview_win.title("Variation Detail View")
        preview_win.geometry("600x450")

        # Use a Text widget with tabs for column alignment
        # Tab 1: 40px (Move number), Tab 2: 120px (White), Tab 3: 200px (Black/Comments)
        text_area = tk.Text(
            preview_win, wrap=tk.WORD, padx=15, pady=15,
            font=("Consolas", 10),  # Monospaced font works best for alignment
            tabs=("40p", "120p", "200p")
        )
        text_area.pack(fill=tk.BOTH, expand=True)

        # Styling tags
        text_area.tag_configure("move_num", foreground="gray")
        text_area.tag_configure("move", font=("Consolas", 10, "bold"))
        text_area.tag_configure("comment", foreground="#008000", font=("Consolas", 9, "italic"))

        # To track move numbers and turns, we need a board object
        board = start_node.parent.board()
        current_node = start_node

        while current_node is not None:
            move_num = board.fullmove_number
            is_white = board.turn  # True if White's turn

            # If it's White's turn, we start a new line with the move number
            if is_white:
                text_area.insert(tk.END, f"{move_num}.\t", "move_num")
            elif current_node == start_node:
                # Special case: if the variation starts with a Black move
                text_area.insert(tk.END, f"{move_num}...\t\t", "move_num")

            # Insert the move
            move_san = current_node.san()
            text_area.insert(tk.END, f"{move_san}\t", "move")

            # Add comment if exists
            if current_node.comment:
                text_area.insert(tk.END, f"({current_node.comment})\t", "comment")

            # If we just finished a Black move (or it's the end), start a new line
            if not is_white or not current_node.variations:
                text_area.insert(tk.END, "\n")

            # Advance board and node
            board.push(current_node.move)
            if current_node.variations:
                current_node = current_node.variation(0)
            else:
                current_node = None

        text_area.config(state=tk.DISABLED)
        tk.Button(preview_win, text="Close", command=preview_win.destroy).pack(pady=5)

    def _on_variation_selected(self, event):
        """
        Callback triggered when a user clicks an item in the variations listbox.
        """
        widget = event.widget
        selection = widget.curselection()

        if not selection:
            return

        index = selection[0]
        # In your logic, index 0 in the listbox is usually variation 1 in the node
        # because variation 0 is the main line.
        all_variations = self.last_node.parent.variations

        if len(all_variations) > 1:
            # Match the listbox index to the variation object
            selected_variation = all_variations[index + 1]
            self._show_variation_preview(selected_variation)

        # --- YOUR LOGIC HERE ---
        # Example: If you want to jump to this variation:
        # self.restore_selected_variation(index)

    def update_move_info(self, last_move, move_index):
        """
        Updates the sidebar widgets with data from the provided Move object.
        :param move_index:
        :param last_move: The current pgn node (chess.pgn.ChildNode)
        """
        if last_move is None:
            self._set_text_widget_content(self.current_comment_widget, "")
            self.current_comment_widget.delete(0, tk.END)
            return

        # 1. Update the Move Label (e.g., "12. Nf3")
        node = self.game
        move_list = []
        last_node = node

        for i in range(move_index + 1):
            if node.variations:
                node = node.variation(0)
                move_list.append(node)
                last_node = node
            else:
                # End of line reached earlier than expected
                break
        self.last_node = last_node
        prev_board = last_node.parent.board()
        move_san = prev_board.san(last_node.move)
        move_number = last_node.parent.board().fullmove_number
        turn = "..." if last_node.parent.board().turn == chess.BLACK else "."
        self.current_move_display_widget.config(text=f"{move_number}{turn} {move_san}")
        # 2. Update Comment (English Translation Applied)
        comment = last_node.comment
        self._set_text_widget_content(self.current_comment_widget, comment if comment else "No comment.")

        # 3. Update Variations
        self.current_variation_widget.delete(0, tk.END)

        # last_move.parent.variations contains all alternative moves at this point
        # We skip index 0 because that is usually the main line move itself
        all_variations = last_node.parent.variations
        if len(all_variations) > 1:
            for i, var in enumerate(all_variations):
                if i == 0:
                    continue
                prefix = "Main: " if i == 0 else f"Var {i}: "
                self.current_variation_widget.insert(tk.END, f"{prefix}{var}")
        else:
            self.current_variation_widget.insert(tk.END, "No variations defined.")

    def _set_text_widget_content(self, widget, content):
        """Helper to update a read-only Text widget."""
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.config(state=tk.DISABLED)

    def _on_tab_change(self, event):
        """
        This function is called when the user clicks on a different tab.
        """

        # 1. Retrieve the widget ID of the newly selected tab
        # if self.notebook.index(self.notebook.select()) == self.current_tab:
        #     return
        selected_tab_id = self.notebook.select()

        # 2. Translate the widget ID to the zero-based index
        new_index = self.notebook.index(selected_tab_id)

        # 3. Update the status variable
        self.current_tab = new_index

        # 4. Update the UI and log the change
        print(f"Tab changed. New index: {self.current_tab}")
        try:
            self.current_movelistbox = self.move_listboxes[self.current_tab]
        except (KeyError, IndexError, AttributeError):
            # Analysis or move list data is missing
            # English translation: "This PGN has not been analyzed yet. Would you like to start the analysis now?"
            msg = "This PGN has not been analyzed yet.\n\nWould you like to start the analysis now?"

            if messagebox.askyesno("Analysis Required", msg, parent=self.master):
                # The user wants to proceed with the analysis
                self.start_editor()
            else:
                # The user declined; you might want to show an empty state or log it
                print("User declined analysis for the current PGN.")
            return
        self.current_movelistbox_info = None
        info = self.get_info_current_listbox()

        number_ = 2 * (info["max_move_number"] - 1)
        if number_ >= len(self.all_moves_chess):
            number_ = self.all_moves_chess
        self.current_move_index = number_

        self.current_board_canvas = self.board_canvases[self.current_tab]
        self.current_comment_widget = self.comment_widgets[self.current_tab]
        self.current_variation_widget = self.variation_widgets[self.current_tab]
        self.current_move_display_widget = self.move_display_widgets[self.current_tab]
        self.display_diagram_move(self.current_move_index)

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
        _save_config(self.default_pgn_dir,self.lastLoadedPgnPath, self.engine_path, self.piece_set, self.square_size, self.board, self.engine_depth)
        exit()

    def show_settings_dialog(self):

        """Roept de instellingendialoog op."""

        # De huidige configuratie ophalen (moet een dictionary zijn!)
        current_settings = {
            "default_directory": self.default_pgn_dir,
            "lastLoadedPgnPath": self.lastLoadedPgnPath,
            "engine_path": self.engine_path,
            "piece_set": self.piece_set,
            "engine_depth":self.engine_depth,
            "square_size": self.square_size,
            "board": self.board
        }

        # Roep de dialoog op. De _save_config functie wordt doorgegeven als callback.
        # We gaan ervan uit dat _save_config elders in deze scope is gedefinieerd
        SettingsDialog(self.master, current_settings, self._save_config_wrapper)

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

    def get_all_significant_events(self, pgn_string):
        """
        Identifies ALL moves that caused a significant loss in advantage (> 50 cp).
        """
        pgn_io = io.StringIO(pgn_string)
        games = []
        while True:
            game = chess.pgn.read_game(pgn_io)
            if game is not None:
                games.append(game)

            else:
                break

        self.num_games = len(self.game_descriptions)
        current_game_index = 0
        self.set_game_var_descriptions(current_game_index)
        if len(games) == 0:
            print("Error: Could not read chess game from PGN string.")
            return []
        else:
            game = games[0]
            if self.num_games == 1:
                # hide the navigation-panel
                self.nav_panel.pack_forget()
            else:
                # show the navigation-panel
                NAV_PACK_ARGS = {'side': tk.TOP, 'fill': tk.X, 'pady': 5}
                self.nav_panel.pack(**NAV_PACK_ARGS)
        self.game = game
        return self.get_all_significant_events_game(game)

    def get_all_significant_events_game(self, game):
        # 1. Reset de lijst voor het huidige spel
        self.all_moves_chess = []

        # 2. Gebruik de ingebouwde methode om door de hoofdlijn te itereren
        # Elke iteratie geeft een chess.Move object terug.
        for move in game.mainline_moves():
            self.all_moves_chess.append(move)

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
                'variations': node.variations,
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
                #print("event", 'score', event_score,'eval_before', eval_before_cp / 100.0,'eval_after', eval_after_cp / 100.0)

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


    def do_new_analysis(self, pgn_string):
        self._clear_content_frame()
        # Perform the advanced analysis
        print("Starting full PGN analysis...")
        try:
            all_events, game = self.get_all_significant_events(pgn_string)
            self._update_meta_info(game)
            print(f"Full analysis complete. {len(all_events)} significant events found (> 50 cp loss).")

            self.sorted_events = select_key_positions(all_events)
            self.num_events = len(self.sorted_events)
            self.populate_event_tabs(self.sorted_events)
            self.master.title(f"Chess Game Analysis: {self.num_events} Critical Positions Selected")
        except Exception as e:
            traceback.print_exc()
            print(e)

    def do_new_analysis_game(self, game):
        self._clear_content_frame()

        all_events, game = self.get_all_significant_events_game(game)
        self.game = game
        self._update_meta_info(game)
        print(f"Full analysis complete. {len(all_events)} significant events found (> 50 cp loss).")

        self.sorted_events = select_key_positions(all_events)
        self.num_events = len(self.sorted_events)
        self.populate_event_tabs(self.sorted_events)

    def _read_file_and_analyze(self, filepath):
        """Reads the PGN-content of the file and start the analysis."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Read the complete content of the PGN-file
                pgn_content = f.read()

            # Use io.StringIO to handle the string like it is a file
            pgn_io = io.StringIO(pgn_content)
            self.all_games = []
            self.game_descriptions = []

            # --- 1. Read ALL games from the PGN file ---
            while game := chess.pgn.read_game(pgn_io):
                self.all_games.append(game)
                self.game_descriptions.append(
                    game.headers.get("White")+"-"+game.headers.get("Black")+"("+game.headers.get("Result")+")")

            # --- 2. Check and Analyze the First Game ---
            if self.all_games:
                first_game = self.all_games[0]

                # Define the Exporter: Set headers, VARIATIONS and COMMENTS to True
                exporter = chess.pgn.StringExporter(
                    headers=True,
                    variations=True,
                    comments=True
                )

                # Convert back the found game (including variants/comments)
                single_pgn_string = first_game.accept(exporter)

                # Reset the current game index to the first game
                self.current_game_index = 0

                # Do the analysis of the first game
                self.do_new_analysis(single_pgn_string)
                self.lastLoadedPgnPath = filepath

            else:
                print("Error: the PGN-file does not contain playable games.")
                # Handle error state: clear path and content
                self.pgn_filepath.set("Error: PGN file contains no games.")
                self._clear_content_frame()
                self.all_games = [] # Ensure the list is empty if no games found

        except Exception as e:
            traceback.print_exc()
            error_message = f"ERROR: Failed to read PGN file: {e}"
            print(error_message)
            self.pgn_filepath.set(error_message)
            self._clear_content_frame()

    def _create_file_reader_widget(self, file_reader_frame):
        """
        Creates the UI elements for selecting and displaying the PGN file path.
        This is placed at the top of the window.
        """


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
        Draws the chess pieces on the canvas using preloaded PNG images.
        Uses _get_square_coords to handle board flipping automatically.
        """
        # 1. Clear existing pieces from the canvas
        canvas.delete("piece")

        for square in chess.SQUARES:
            piece = board.piece_at(square)

            if piece:
                # 2. Get the square boundaries using our helper
                rank = chess.square_rank(square)
                file = chess.square_file(square)
                x1, y1, x2, y2 = self._get_square_coords(rank, file)

                # 3. Calculate the center of the square for image placement
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2

                # 4. Retrieve the preloaded image from the manager
                symbol = piece.symbol()
                piece_img = self.image_manager.images.get(symbol)

                if piece_img:
                    # 5. Draw the image at the calculated center
                    canvas.create_image(
                        center_x,
                        center_y,
                        image=piece_img,
                        tags="piece"
                    )


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

        diagram_block = tk.Frame(tab_frame,
                                      padx=10, pady=10, bd=2, relief=tk.GROOVE)
        diagram_block.grid(row=0, column=0, padx=(0, 15), pady=5, sticky='nsw')

        # 1. Info Label
        info_text = (
            f"Change: {event_data['score'] / 100.0:.2f} P"
            f"Eval BEFORE: {event_data['eval_before']:.2f} | Eval AFTER: {event_data['eval_after']:.2f}"
        )
        tk.Label(diagram_block, text=info_text, justify=tk.LEFT, pady=5).pack(anchor="w")

        # 2. Canvas for the board
        board_canvas = tk.Canvas(diagram_block, width=self.board_size, height=self.board_size,
                                 borderwidth=0, highlightthickness=1, highlightbackground="black")
        board_canvas.pack(pady=10)
        self.board_canvases.append(board_canvas)

        # Initialize the board with the FEN BEFORE the event
        try:
            board = chess.Board(event_data['fen'])
        except ValueError:
            tk.Label(diagram_block, text="Ongeldige FEN", fg="red").pack()
            board_canvas.pack_forget()
            self.notebook.add(tab_frame, text=f"ERROR {index}")
            return
        for square in chess.SQUARES:
            rank = chess.square_rank(square)
            file = chess.square_file(square)

            # Use our helper for all coordinate math
            x1, y1, x2, y2 = self._get_square_coords(rank, file)

            # Determine square color
            # In python-chess, (rank + file) % 2 == 0 is always a dark square (like a1)
            color = self.color_dark if (rank + file) % 2 == 0 else self.color_light
            board_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="", tags="square")

        # Draw the pieces
        self.draw_pieces(board_canvas, board)
        # 4. Mark the move squares (From and To)
        try:
            # Extract SAN move (e.g., "12. Nf3" -> "Nf3")
            move_raw = event_data.get('move_text', "").split()[-1].strip('.')
            if move_raw:
                move = board.parse_san(move_raw)

                # Highlight both departure and arrival squares for better UX
                for sq in [move.from_square, move.to_square]:
                    r, f = chess.square_rank(sq), chess.square_file(sq)
                    hx1, hy1, hx2, hy2 = self._get_square_coords(r, f)

                    board_canvas.create_rectangle(
                        hx1, hy1, hx2, hy2,
                        outline="#FFC300",
                        width=4,
                        tags="highlight"
                    )

                # Ensure highlights are above squares but below pieces
                board_canvas.tag_raise("highlight", "square")
        except Exception as e:
            # If move parsing fails (e.g. at start of game), we simply skip highlighting
            print(f"Highlighting skipped: {e}")
        # Bind the left mouse button click to our handler
        board_canvas.bind("<Button-1>", self._on_board_click)

        # --- COLUMN 1: PGN SNIPPET & ANALYSIS (Right Side) ---
        pgn_block = tk.LabelFrame(tab_frame, text="Game Analysis",
                                  padx=10, pady=10, font=("Helvetica", 12, "bold"), bd=2, relief=tk.GROOVE)
        pgn_block.grid(row=0, column=1, padx=(15, 0), pady=5, sticky='nsew')

        # Configure two equal columns
        pgn_block.grid_columnconfigure(0, weight=1)
        pgn_block.grid_columnconfigure(1, weight=1)

        # Ensure the top section (row 0) takes most of the vertical space
        pgn_block.grid_rowconfigure(0, weight=3)
        # Row 1 will contain our bottom elements
        pgn_block.grid_rowconfigure(1, weight=1)

        # 1. Top Left: The Move List (Ensure this uses grid internally)
        self._create_move_list_widget(pgn_block)

        # 2. Top Right: Move Display and Variations
        top_right_container = tk.Frame(pgn_block)
        top_right_container.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        top_right_container.columnconfigure(0, weight=1)
        top_right_container.grid_rowconfigure(1, weight=1)  # Variations expand vertically

        # --- A. MOVE DISPLAY ---
        move_frame = tk.LabelFrame(top_right_container, text="Move", padx=5, pady=2)
        move_frame.grid(row=0, column=0, sticky='ew', pady=2)

        move_label = tk.Label(move_frame, text=event_data.get('move_text', '-'),
                              font=("Helvetica", 12, "bold"), fg="blue")
        move_label.pack(anchor="w")
        self.move_display_widgets.append(move_label)

        # --- B. VARIATIONS ---
        vars_frame = tk.LabelFrame(top_right_container, text="Variations", padx=5, pady=2)
        vars_frame.grid(row=1, column=0, sticky='nsew', pady=2)

        vars_text = tk.Listbox(vars_frame, font=('Arial', 9), height=6)
        vars_text.pack(fill=tk.BOTH, expand=True)
        if 'variations' in event_data:
            vars_text.insert(tk.END, event_data['variations'])
        self.variation_widgets.append(vars_text)

        # 3. Bottom Container: Full width (columnspan=2)
        # Using sticky='nsew' here is crucial to allow children to push to the bottom
        bottom_container = tk.Frame(pgn_block)
        bottom_container.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(10, 0))
        bottom_container.columnconfigure(0, weight=1)

        # IMPORTANT: Row 0 (Comments) gets weight so it pushes Row 1 (Toolbar) down
        bottom_container.grid_rowconfigure(0, weight=1)
        bottom_container.grid_rowconfigure(1, weight=0)

        # --- C. COMMENTS ---
        comm_frame = tk.LabelFrame(bottom_container, text="Comments", padx=5, pady=2)
        comm_frame.grid(row=0, column=0, sticky='nsew', pady=2)  # Changed sticky to nsew

        comm_text = tk.Text(comm_frame, height=4, wrap=tk.WORD, font=("Segoe UI", 10))
        comm_text.pack(fill=tk.BOTH, expand=True)
        if 'comment' in event_data:
            comm_text.insert(tk.END, event_data['comment'])
        comm_text.config(state=tk.DISABLED)
        self.comment_widgets.append(comm_text)

        # --- D. SHORTCUTS/TOOLBAR ---
        # Because Row 0 has weight and Row 1 does not, this will stick to the bottom
        toolbar = self._setup_quick_toolbar(bottom_container)
        toolbar.grid(row=1, column=0, sticky='ew', pady=(5, 0))

        # 2. Add the frame to the Notebook
        self._update_move_listbox_content(self.current_game_moves)
        tab_title = f"{index}. {event_data['move_text']}"  # Short title for the tab
        self.notebook.add(tab_frame, text=tab_title)

    def _on_board_click(self, event):
        """
        Handles clicks on the board:
        Left half goes back one move, Right half goes forward one move.
        """
        # 1. Get the total width of the canvas
        canvas_width = self.current_board_canvas.winfo_width()
        mid_x = canvas_width / 2

        # 2. Determine the direction based on the click position
        if event.x < mid_x:
            # Left side clicked: Go back
            print("Left side clicked - Previous move")
            self._go_to_previous_move()  # Or your specific move navigation function
        else:
            # Right side clicked: Go forward
            print("Right side clicked - Next move")
            self._go_to_next_move()

            # 3. Always update the board state after moving
        self.display_diagram_move(self.current_move_index)


    def _update_move_listbox_content(self, moves):
        """
        Clears the Listbox completely, and repopulates it with new content.
        """
        # 1. Clear the Listbox entirely
        self.move_listbox.delete(0, tk.END)

        # 2. Populate with new moves and rebuild the map (implicit step)
        for move_index, move_pair in enumerate(moves):
            # Splits the string on every newline character
            lines = move_pair.split('\n')

            for line in lines:
                # Insert each resulting line as a separate Listbox item
                self.move_listbox.insert(tk.END, line)


    def populate_event_tabs(self, events):
        """
        Removes existing tabs and populates the Notebook with new events,
        calculating the PGN snippet for each event.
        """
        # 1. CLEAR ALL EXISTING TABS
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)

        self.move_listboxes = []
        self.board_canvases = []

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
            self.current_game_moves = pgn_snippet

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

    def swap_colours_func(self):
        self.swap_colours = not self.swap_colours
        self.display_diagram_move(self.current_move_index)


# --- Main execution ---

if __name__ == "__main__":
    try:
        root = tk.Tk()
        # Set the initial size to 1200x800
        root.geometry("1200x1020")

        IMAGE_DIRECTORY = "Images/piece"
        default_pgn_dir, lastLoadedPgnPath, engine_path, piece_set, square_size, board1, engine_depth = get_settings()
        SQUARE_SIZE = int(square_size) if square_size else 60  # Size of the squares in pixels
        # 2. Initialize the Asset Manager (LOADS IMAGES ONCE)
        # If this fails (e.g., FileNotFoundError), the program stops here.


        app = ChessEventViewer(root, PGN_WITH_EVENTS, SQUARE_SIZE, None, default_pgn_dir, lastLoadedPgnPath, engine_path, piece_set, board1, engine_depth)
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
