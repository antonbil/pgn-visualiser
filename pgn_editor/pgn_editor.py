import json, sys
import tkinter as tk
import threading
from datetime import datetime
from tkinter import messagebox, simpledialog, filedialog
from io import StringIO
import chess
import chess.pgn
import re # For simple PGN cleaning
import asyncio
import argparse
from PIL import Image, ImageTk
import os
import cairosvg
from io import BytesIO
from tkinter import ttk
import traceback
from pathlib import Path
import zipfile

PREFERENCES_FILE = "preferences.json"

def load_preferences():
    """Loads the preferences from preferences.json, or returns an empty dict."""
    if os.path.exists(PREFERENCES_FILE):
        try:
            with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            # if error in json-file, return empty dict
            return {}
    return {}

def save_preferences(data):
    """Saves the preferences in preferences.json."""
    try:
        with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Warning: cannot save preferences: {e}")


class Tooltip:
    """
    A class to create a hover-over tooltip for any Tkinter widget
    with an automatic timeout.
    """

    def __init__(self, widget, text, timeout_ms=3000):
        self.widget = widget
        self.text = text
        self.timeout_ms = timeout_ms  # Time in milliseconds before it disappears
        self.tip_window = None
        self.after_id = None  # To keep track of the timer

        # Bind mouse events
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return

        # Calculate position
        x, y, _, _ = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 25

        # Create window
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#ffffe0", relief=tk.SOLID, borderwidth=1,
            font=("tahoma", "8", "normal"), padx=4, pady=2
        )
        label.pack(ipadx=1)

        # 1. Schedule the tooltip to hide after the specified timeout
        self.after_id = self.widget.after(self.timeout_ms, self.hide_tip)

    def hide_tip(self, event=None):
        # 2. Cancel the scheduled timeout if it exists
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None

        # 3. Destroy the window
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


# Add this method to your main class to make the previous code work:
def _add_tooltip(widget, text):
    """
    Helper function to attach a tooltip to a widget.
    """
    return Tooltip(widget, text)


class OpeningClassifier:
    def __init__(self, json_path="eco.json"):
        """
        Loads the ECO database and prepares it for FEN-based lookup.
        """
        self.script_path = Path(__file__).resolve().parent
        eco_path = self.script_path / json_path
        self.opening_db = {}
        try:
            with open(eco_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Map standardized FEN to opening data for fast lookup
                for entry in data:
                    clean_fen = entry['f']
                    self.opening_db[clean_fen] = {
                        "name": entry['n'],
                        "code": entry['c']
                    }
        except FileNotFoundError:
            print(f"Error: {eco_path} not found.")
        except Exception as e:
            print(f"Error loading ECO database: {e}")

    def _standardize_fen(self, fen):
        """
        Standardizes FEN by removing move clocks.
        Opening databases usually only care about the board,
        turn, castling, and en passant square.
        """
        parts = fen.split()
        # Keep only board, turn, castling, and en passant (first 4 parts)
        return " ".join(parts[:3])

    def annotate_opening(self, game):
        """
        Uses a while-loop to traverse the mainline and annotate the last matching opening move.
        """
        if not game:
            return None

        node = game
        last_matched_node = None
        opening_info = None

        # Traverse the mainline using the requested while-loop
        while not node.is_end():
            # Move to the next node in the main variation
            node = node.variation(0)

            # Get the board position at this specific node
            board = node.board()
            current_fen = self._standardize_fen(board.fen())

            # Check if this position is in our opening database
            if current_fen in self.opening_db:
                opening_info = self.opening_db[current_fen]
                last_matched_node = node

        # If we found a match, add it as a comment to the specific node
        if last_matched_node and opening_info:
            annotation = f"{opening_info['name']}"

            # Check if the annotation is already there to avoid duplicates
            existing_comment = last_matched_node.comment or ""
            if annotation not in existing_comment:
                if existing_comment:
                    last_matched_node.comment = f"{existing_comment} ({annotation})"
                    #print("opening", annotation, "added to:", last_matched_node)
                else:
                    last_matched_node.comment = annotation
                    #print("opening", annotation, "added to:", last_matched_node)

            return opening_info

        return None

class AnalysisManager:
    # --- CONFIGURATION PARAMETERS ---
    THREADS = 4
    MEMORY_HASH = 256

    MULTIPV_COUNT = 4
    PAWN_THRESHOLD = 0.5

    def __init__(self, root, pgn_game, stockfish_path, on_finished_callback=None, db_info=None, depth_limit=17,
                 check_previous = False, external_progress_ui=None):
        """
        Initialize the analysis manager.
        :param db_info: Optional string info like "Game 3 of 10: Player A vs Player B"
        """
        self.root = root
        self.check_previous = check_previous
        self.external_progress_ui = external_progress_ui
        self.game = pgn_game
        self.stockfish_path = stockfish_path
        self.on_finished_callback = on_finished_callback
        self.db_info = db_info  # Information about database progress

        self.is_cancelled = False  # Flag to stop the process
        self.progress_win = None
        self.progress_bar = None
        self.depth_limit = depth_limit
        self.status_label = None
        self.db_label = None

    def start(self):
        """Creates the UI and starts the background analysis thread."""
        if not self.external_progress_ui:
            self._create_progress_window()
        else:
            # Koppel de externe UI aan de interne variabelen
            self.progress_win = self.external_progress_ui['window']
            self.progress_bar = self.external_progress_ui['progress_bar']
            self.status_label = self.external_progress_ui['status_label']
            self.db_label = self.external_progress_ui.get('db_label')

            # Update db_info als dat meegegeven is
            if self.db_label and self.db_info:
                self.root.after(0, lambda: self.db_label.config(text=self.db_info))
        analysis_thread = threading.Thread(target=self._run_analysis)
        analysis_thread.daemon = True
        analysis_thread.start()

    def _create_progress_window(self):
          """Sets up the Toplevel window for progress tracking."""
          try:
                self.progress_win = tk.Toplevel(self.root)
                self.progress_win.title("Stockfish Analysis")
                self.progress_win.geometry("400x200")
                self.progress_win.transient(self.root)
                self.progress_win.grab_set()

                # Database progress label
                if self.db_info:
                    self.db_label = tk.Label(self.progress_win, text=self.db_info, font=("Arial", 10, "bold"), wraplength=350)
                    self.db_label.pack(pady=(10, 0))

                # Current move status label
                self.status_label = tk.Label(self.progress_win, text="Starting Stockfish...", wraplength=350)
                self.status_label.pack(pady=10)

                # Progress bar
                self.progress_bar = ttk.Progressbar(self.progress_win, length=300, mode='determinate')
                self.progress_bar.pack(pady=10)

                # Stop/Cancel button
                self.stop_button = tk.Button(self.progress_win, text="Stop Analysis", command=self._cancel_analysis,
                                             bg="#ffcccc")
                self.stop_button.pack(pady=10)
          except tk.TclError:
              # Als een ander venster de grab heeft, loggen we het
              # maar laten we het programma gewoon doorgaan.
              print("Waarschuwing: kon grab niet instellen, ander venster is actief.")

    def _cancel_analysis(self):
        """Triggered by the Stop button to halt analysis."""
        if messagebox.askyesno("Cancel", "Do you want to stop the analysis?", parent=self.progress_win):
            self.is_cancelled = True
            self.status_label.config(text="Stopping engine...")


    def _run_analysis(self):
        """
        Two-phase analysis:
        1. Calibration (Fast scan to set optimal thresholds)
        2. Production (Deep analysis using calibrated thresholds)
        """
        engine = None
        try:
            engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
            engine.configure({"Threads": self.THREADS, "Hash": self.MEMORY_HASH})

            # Metadata Header
            engine_name = engine.id.get("name", "Stockfish")
            analysis_header = f"Analysis by {engine_name} (Depth {self.depth_limit}"

            if self.game.comment.startswith(analysis_header) and self.check_previous:
                return

            # --- PHASE 1: CALIBRATION ---
            self.root.after(0,
                            lambda: self.status_label.config(text="Phase 1: Calibrating thresholds for this game..."))
            all_drops = []
            node_indices = []
            node = self.game
            total_moves = sum(1 for _ in self.game.mainline_moves())

            self.root.after(0, lambda: self.progress_bar.config(max=total_moves, value=0))

            calib_count = 0
            prev_score = None
            swing_indices = set()
            idx = 0
            while not node.is_end() and not self.is_cancelled:
                board = node.board()
                # Fast scan (low depth) to find the 'average' error margin of the players
                info = engine.analyse(board, chess.engine.Limit(depth=10))
                best_val = info["score"].pov(chess.WHITE).score(mate_score=10000)

                main_variation = node.variation(0)
                played_move = main_variation.move
                p_info = engine.analyse(board, chess.engine.Limit(depth=10), root_moves=[played_move])
                played_val = p_info["score"].pov(chess.WHITE).score(mate_score=10000)
                played_score_str = self._format_score_simple(p_info["score"])
                self.store_score_in_node(main_variation, played_score_str)

                all_drops.append(abs(best_val - played_val))
                node_indices.append(idx)

                if prev_score is not None:
                    swing = abs(played_val - prev_score)
                    # If the score changes more than 1.00 pawn, it is marked as critical
                    if swing > 100:
                        swing_indices.add(idx)

                prev_score = played_val

                node = main_variation
                calib_count += 1
                self.root.after(0, lambda v=calib_count: self.progress_bar.config(value=v))
                idx += 1

            if self.is_cancelled: return

            # Calculate optimal PAWN_THRESHOLD
            # Target: roughly 20 variations per game
            combined = sorted(zip(all_drops, node_indices), reverse=True, key=lambda x: x[0])
            analysis_worthy_indices = {index for drop, index in combined[:35]}
            # add swing-moments
            analysis_worthy_indices = analysis_worthy_indices | swing_indices
            all_drops.sort(reverse=True)

            target_vbox = 20
            if len(all_drops) >= target_vbox:
                # Set threshold to the 20th biggest error
                calibrated_threshold = all_drops[target_vbox - 1] / 100.0
            elif all_drops:
                calibrated_threshold = all_drops[-1] / 100.0
            else:
                calibrated_threshold = 0.50
            calibrated_threshold = calibrated_threshold + 0.01
            # Safety guardrails: not too sensitive, not too deaf
            self.PAWN_THRESHOLD = max(0.20, min(calibrated_threshold, 1.00))

            # --- PHASE 2: ACTUAL ANALYSIS ---
            self.root.after(0, lambda: self.status_label.config(
                text=f"Phase 2: Deep Analysis (Threshold: {self.PAWN_THRESHOLD:.2f})..."))
            self.root.after(0, lambda: self.progress_bar.config(value=0))

            # Reset node to start of game
            node = self.game
            move_count = 0


            # Remove any existing "Analysis by..." lines to prevent stacking
            # This looks for any line starting with "Analysis by" until the first "|" or end of line
            analysis_header = f"Analysis by {engine_name} (Depth {self.depth_limit}, T={self.PAWN_THRESHOLD:.2f})"
            if self.game.comment:
                # We filter out any previous analysis headers using a regex
                cleaned_root_comment = re.sub(r'Analysis by .*?(\||\n|$)', '', self.game.comment).strip()

                if cleaned_root_comment:
                    self.game.comment = f"{analysis_header} | {cleaned_root_comment}"
                else:
                    self.game.comment = analysis_header
            else:
                self.game.comment = analysis_header
            while not node.is_end():
                if self.is_cancelled: break
                if not move_count in analysis_worthy_indices:
                    node = node.variation(0)
                    move_count += 1
                    continue


                main_variation = node.variation(0)
                played_move = main_variation.move
                board = node.board()
                current_move_num = board.fullmove_number

                self.root.after(0, lambda: self.status_label.config(
                    text=f"Analyzing move {current_move_num}: {played_move}"))

                # Deep Multi-PV Analysis
                limit = chess.engine.Limit(depth=self.depth_limit, time=1.0)
                analysis = engine.analyse(board, limit, multipv=self.MULTIPV_COUNT)

                # Scores
                best_entry = analysis[0]
                best_score_val = best_entry["score"].pov(chess.WHITE).score(mate_score=10000)

                played_entry = next((e for e in analysis if e["pv"][0] == played_move), None)
                if played_entry:
                    played_score_val = played_entry["score"].pov(chess.WHITE).score(mate_score=10000)
                    played_score_str = self._format_score_simple(played_entry["score"])
                else:
                    p_info = engine.analyse(board, chess.engine.Limit(depth=self.depth_limit), root_moves=[played_move])
                    played_score_val = p_info["score"].pov(chess.WHITE).score(mate_score=10000)
                    played_score_str = self._format_score_simple(p_info["score"])

                self.store_score_in_node(main_variation, played_score_str)

                # Logic for variations (using calibrated threshold)
                eval_drop = abs(best_score_val - played_score_val)

                # Add Variations
                if best_entry["pv"][0] != played_move and eval_drop > (calibrated_threshold * 100):
                    self._add_engine_variation(node, best_entry, board, played_score_val)

                # NAGs
                main_variation.nags.clear()
                if eval_drop >= 200:
                    main_variation.nags.add(chess.pgn.NAG_BLUNDER)
                elif eval_drop >= 100:
                    main_variation.nags.add(chess.pgn.NAG_MISTAKE)
                elif eval_drop >= 50:
                    main_variation.nags.add(chess.pgn.NAG_DUBIOUS_MOVE)

                move_count += 1
                self.root.after(0, lambda v=move_count: self.progress_bar.config(value=v))
                node = main_variation

        except Exception as e:
            print(f"Analysis error: {e}")
            traceback.print_exc()
        finally:
            if engine: engine.quit()
            self.root.after(0, self._on_cancel_complete if self.is_cancelled else self._on_complete)

    def store_score_in_node(self, main_variation, played_score_str: str):
        # Comment Clean & Update
        clean_comment = re.sub(r'^[+-]?\d+\.\d+\s*', '', main_variation.comment).strip()
        main_variation.comment = f"{played_score_str} {clean_comment}".strip()

    def _add_engine_variation(self, parent_node, engine_entry, board, played_score):
        """Helper to add an engine move sequence and comment."""
        engine_line = engine_entry["pv"]
        engine_move = engine_line[0]
        engine_score_obj = engine_entry["score"]
        engine_score_val = engine_score_obj.pov(chess.WHITE).score(mate_score=10000)

        var_node = parent_node.add_variation(engine_move)

        temp_board = board.copy()
        temp_board.push(engine_move)
        current_branch = var_node

        for next_move in engine_line[1:5]:
            if next_move in temp_board.legal_moves:
                current_branch = current_branch.add_variation(next_move)
                temp_board.push(next_move)
            else:
                break

        diff = (engine_score_val - played_score) if board.turn == chess.WHITE else (played_score - engine_score_val)
        score_str = self._format_score_simple(engine_score_obj)
        var_node.comment = f"{score_str} (+{round(abs(diff) / 100.0, 2)})"

    def _format_score_simple(self, score_obj):
        """Helper to format score (e.g. 0.88 or #3)."""
        pov_score = score_obj.pov(chess.WHITE)
        if pov_score.is_mate():
            m = pov_score.mate()
            return f"#{m}" if m > 0 else f"#-{-m}"
        return f"{round(pov_score.score(mate_score=10000) / 100.0, 2):.2f}"

    def _on_complete(self):
        """Cleanup after successful game analysis."""
        if not self.external_progress_ui and self.progress_win:
            self.progress_win.destroy()

        if self.on_finished_callback:
            self.on_finished_callback()

    def _on_cancel_complete(self):
        """Cleanup and notification after user cancellation."""
        if self.progress_win: self.progress_win.destroy()
        messagebox.showinfo("Cancelled", "The analysis process has been stopped.")

    def _on_error(self, error):
        """Unified error reporting for the analysis thread."""
        if self.progress_win: self.progress_win.destroy()
        messagebox.showerror("Engine Error", f"An error occurred: {error}", parent=self.root)
class CommentManager:
    def __init__(self, label_widget, lines_per_page=5):
        self.display = label_widget
        self.lines_per_page = lines_per_page
        self.all_chunks = []
        self.current_page = 0

        # 1. Set a reasonable starting wrap length (e.g., 300 pixels)
        # 2. Use 'w' anchor to keep text left-aligned
        self.display.config(
            justify="left",
            anchor="nw",
            wraplength=300
        )

        self.display.bind("<Button-1>", self.on_click)
        self.display.bind("<Configure>", self.update_wraplength)

    def update_wraplength(self, event):
        """
        This event fires whenever the label changes size.
        """
        # Take the actual width of the widget and subtract padding
        padding = 20
        new_width = event.width - padding

        if new_width > 10:  # Only update if there is actual width
            self.display.config(wraplength=new_width)
            # Optional: print(f"New wraplength: {new_width}") # Debugging
        #self.comment_manager.set_comments()
    def set_comments(self, comments_text):
        """
        Cleans the input text and splits it into chunks based on lines_per_page.
        """
        # 1. Clean the text: remove newlines and double spaces
        clean_text = " ".join(comments_text.split())

        # 2. Split into words to create artificial "lines" or chunks
        # Note: In a wrapping label, "lines" are subjective.
        # Here we split by words and group them.
        words = clean_text.split()
        words_per_page = self.lines_per_page * 10  # Estimate 10 words per line

        self.all_chunks = [words[i:i + words_per_page] for i in range(0, len(words), words_per_page)]
        self.current_page = 0
        self.refresh_display()

    def refresh_display(self):
        """
        Updates the label text with the current page's content.
        """
        if not self.all_chunks:
            self.display.config(text="")
            return

        current_words = self.all_chunks[self.current_page]
        display_text = " ".join(current_words)

        # Pagination indicator
        if self.current_page < len(self.all_chunks) - 1:
            display_text += "[ CLICK FOR MORE... ]"
        elif len(self.all_chunks) > 1:
            display_text += "[ CLICK: BACK TO START ]"
        else:
            display_text += "\n\n"

        self.display.config(text=display_text)

    def on_click(self, event):
        """
        Handles the click event to cycle through pages.
        """
        if not self.all_chunks:
            return

        if self.current_page < len(self.all_chunks) - 1:
            self.current_page += 1
        else:
            self.current_page = 0

        self.refresh_display()


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, current_config, save_config_callback):
        """
        Initialiseert de modale instellingendialoog.

        :param parent: De hoofd Tkinter-instantie.
        :param current_config: Een dictionary met de huidige instellingen.
        :param save_config_callback: De functie om de nieuwe instellingen op te slaan (uw _save_config).
        """
        super().__init__(parent)
        self.transient(parent)
        self.title("Application Settings")
        self.parent = parent
        self.current_config = current_config
        self.save_config_callback = save_config_callback

        self.theme_names = [theme["name"] for theme in BOARD_THEMES]  # Lijst met namen

        # --- Modale Setup ---
        self.result = None
        self.grab_set()

        self._create_variables()
        self._create_widgets()

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        self.wait_window(self)

    def _create_variables(self):
        """Maakt Tkinter-variabelen aan en vult deze met de huidige waarden."""

        # Standaard Directory
        self.default_dir_var = tk.StringVar(value=self.current_config.get("default_directory", ""))

        # Laatst Geladen PGN Pad
        self.last_pgn_path_var = tk.StringVar(value=self.current_config.get("lastLoadedPgnPath", ""))

        # Engine Pad
        self.engine_path_var = tk.StringVar(value=self.current_config.get("engine_path", ""))

        # Piece Set (Standaard: staunty)
        self.piece_set_var = tk.StringVar(value=self.current_config.get("piece_set", "staunty"))

        # Square Size (Standaard: 80)
        # Gebruik IntVar voor numerieke waarde
        self.square_size_var = tk.IntVar(value=self.current_config.get("square_size", 80))

        # Engine Depth (Standaard: 17)
        # Gebruik IntVar voor numerieke waarde
        self.engine_depth_var = tk.IntVar(value=self.current_config.get("engine_depth", 17))

        # Board Kleur (Standaard: red)
        self.board_var = tk.StringVar(value=self.current_config.get("board", "Standard"))

    def _create_widgets(self):
        """Maakt en plaatst de GUI-elementen in het dialoogvenster."""

        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # --- Rij 0: Default Directory ---
        ttk.Label(main_frame, text="Default PGN Directory:").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Entry(main_frame, textvariable=self.default_dir_var, width=50).grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Button(main_frame, text="Browse", command=self._browse_dir).grid(row=0, column=2, sticky='e')

        # --- Rij 1: Engine Path ---
        ttk.Label(main_frame, text="Stockfish Engine Path:").grid(row=1, column=0, sticky='w', pady=5)
        ttk.Entry(main_frame, textvariable=self.engine_path_var, width=50).grid(row=1, column=1, sticky='ew', padx=5)
        ttk.Button(main_frame, text="Browse", command=self._browse_engine).grid(row=1, column=2, sticky='e')

        # --- Rij 2: Last Loaded PGN Path (alleen ter info, niet bewerkbaar) ---
        ttk.Label(main_frame, text="Last Loaded PGN (Read-only):").grid(row=2, column=0, sticky='w', pady=5)
        # Disabled entry om te tonen, maar niet bewerkbaar te maken
        ttk.Entry(main_frame, textvariable=self.last_pgn_path_var, width=50, state='readonly').grid(row=2, column=1,
                                                                                                    columnspan=2,
                                                                                                    sticky='ew', padx=5)
        # --- Rij 3 & 4: Visual Settings (in een subframe) ---
        visual_frame = ttk.LabelFrame(main_frame, text="Visual Settings", padding="10")
        visual_frame.grid(row=3, column=0, columnspan=3, sticky='ew', pady=10)

        # Piece Set
        ttk.Label(visual_frame, text="Piece Set Name:").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Entry(visual_frame, textvariable=self.piece_set_var, width=20).grid(row=0, column=1, sticky='w', padx=5)

        # Square Size
        ttk.Label(visual_frame, text="Square Size (px):").grid(row=0, column=2, sticky='w', pady=5)
        ttk.Entry(visual_frame, textvariable=self.square_size_var, width=10).grid(row=0, column=3, sticky='w', padx=5)

        # Engine Depth
        ttk.Label(visual_frame, text="Engine Depth:").grid(row=0, column=2, sticky='w', pady=5)
        ttk.Entry(visual_frame, textvariable=self.engine_depth_var, width=10).grid(row=0, column=3, sticky='w', padx=5)


        # --- BOARD THEME ADJUSTMENT: Use Combobox ---
        ttk.Label(visual_frame, text="Board Theme:").grid(row=1, column=0, sticky='w', pady=5)

        # Combobox for theme selection
        board_combobox = ttk.Combobox(
            visual_frame,
            textvariable=self.board_var,
            values=self.theme_names,  # Use the list of names
            state='readonly',  # Force selection from the list
            width=20
        )
        board_combobox.grid(row=1, column=1, sticky='w', padx=5)

        # Ensure the combobox shows the current value if it is valid
        if self.board_var.get() not in self.theme_names:
            self.board_var.set("Standard")  # Fallback to Standard if the name is invalid

        # --- Row 5: OK / Cancel Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="OK", command=self.ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel, width=10).pack(side=tk.LEFT, padx=5)

        # Ensure the Entry fields in the grid expand properly
        main_frame.grid_columnconfigure(1, weight=1)

    def _browse_dir(self):
        """Opens a dialog window to select the default directory."""
        new_dir = filedialog.askdirectory(
            parent=self,
            initialdir=self.default_dir_var.get() or "~",
            title="Select Default PGN Directory"
        )
        if new_dir:
            self.default_dir_var.set(new_dir)

    def _browse_engine(self):
        """Opens a dialog window to select the Stockfish executable file."""
        new_path = filedialog.askopenfilename(
            parent=self,
            initialdir=self.engine_path_var.get() or "~",
            title="Select Stockfish Executable"
        )
        if new_path:
            self.engine_path_var.set(new_path)

    def ok(self):
        """Processes the OK button: validates, saves, and closes."""
        try:
            # Validation (example: ensure square_size is an integer)
            square_size = self.square_size_var.get()
            if not isinstance(square_size, int) or square_size < 10:
                raise ValueError("Square Size must be a number greater than 10.")
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e), parent=self)
            return

        # Call the external save function with the new values
        self.save_config_callback(
            self.default_dir_var.get(),
            self.last_pgn_path_var.get(),
            self.engine_path_var.get(),
            self.piece_set_var.get(),
            self.square_size_var.get(),
            self.board_var.get(),
            self.engine_depth_var.get()# Sends the selected name (e.g., "Red")
        )

        self.result = True
        self.destroy()

    def cancel(self):
        """Processes the Cancel button or window closure."""
        self.result = False
        self.destroy()

    # Required: pip install python-chess
BOARD_THEMES = [
    {
        "name": "Standard",
        "light": "#F0D9B5",  # Very light beige/cream
        "dark": "#B58863"  # Warm brown/sepia color
    },
    {
        "name": "Blue Lagoon",
        "light": "#C3DDE9",  # Very light blue/gray
        "dark": "#638C9B"  # Muted blue/green
    },
    {
        "name": "Green",
        "light": "#ECECDD",  # Very light green-yellow
        "dark": "#779954"  # Standard dark green
    },
    {
        "name": "Red",
        "light": "#FFF3E1",  # Light cream color
        "dark": "#B83E3E"  # Deep red
    },
    {
        "name": "Dark",
        "light": "#D1D0D0",  # Light gray
        "dark": "#9B9B9B"  # Lighter dark gray (Improved contrast)
    },
    {
        "name": "Moody (Purple)",
        "light": "#E9E4F5",  # Very light purple
        "dark": "#9F8CC4"  # Lighter muted purple (Improved contrast)
    },
    {
        "name": "Classic Tournament",
        "light": "#FFFFFF",  # White
        "dark": "#AAAAAA"  # Medium gray
    },
    {
        "name": "Ocean",
        "light": "#CCFFCC",  # Very light green
        "dark": "#5588C2"  # Lighter navy blue/ocean blue (Improved contrast)
    },
    {
        "name": "Rosewood",
        "light": "#FFC0CB",  # Pink
        "dark": "#C45A5A"  # Lighter reddish-brown (Improved contrast)
    },
    {
        "name": "Terminal (Green on Dark)",
        "light": "#00CC00",  # Bright green
        "dark": "#333333"  # Very dark gray (Improved contrast, was black)
    },
    {
        "name": "Ivory",
        "light": "#F5F5DC",  # Ivory
        "dark": "#696969"  # Dark gray (Sufficient contrast)
    }
]

class PrettyMoveList(tk.Text):
    def __init__(self, master, select_callback=None, **kwargs):
        # Initialize the text widget with specific styles for chess PGN
        super().__init__(master, **kwargs)
        self.master = master
        self.select_callback = select_callback
        # Dictionary to map chess nodes to their position in the text
        self.node_to_index = {}

        # Setup tags and highlight style
        self.tag_config("active_move",
                background="#FFCCCC",
                foreground="black",
                font=("Consolas", 10, "bold"),
                relief="solid",         # Border around move
                borderwidth=1,
                # We simulate padding by increasing the spacing
                # around the characters using offset and spacing
                offset=2)
        # Increase general line spacing to prevent the border
        # from touching the moves above or below
        self.config(spacing1=5, spacing3=5)

        # Let's also add a tag for the current line to make it pop even more
        self.tag_config("active_line", background="#e6f2ff") # Light blue glow over the line
        self.config(state="disabled", wrap="word", font=("Consolas", 10), spacing1=2)

        # Define tags for colors and layout
        self.tag_config("regular", foreground="black", font=("Consolas", 10, "bold"))
        self.tag_config("variant", foreground="#0074D9")
        self.tag_config("subvariant", foreground="#B10DC9")
        self.tag_config("comment", foreground="#2ECC40")
        self.tag_config("number", foreground="#888888")
        self.tag_config("value",
                foreground="#FF851B",
                font=("Consolas", 9, "italic"),
                spacing1=0)  # Geen extra ruimte boven de waardering-regel

        # Define a move_row tag to control the spacing after the move
        self.tag_config("move_row", spacing3=0)

        # Hover effect for clickable moves
        self.tag_config("clickable", underline=False)
        self.tag_bind("clickable", "<Enter>", lambda e: self.config(cursor="hand2"))
        self.tag_bind("clickable", "<Leave>", lambda e: self.config(cursor="arrow"))

    def load_pgn(self, game):
        # Parse the PGN game using the python-chess library
        if game:
            self.node_to_index = {} # Reset de mapping
            self.config(state="normal")
            self.delete("1.0", tk.END)
            self._process_main_line(game)
            self.config(state="disabled")

    def _process_main_line(self, node):
        """Handles main line moves with values and comments underneath."""
        for i, child in enumerate(node.variations):
            if i == 0: # Main line move
                board = node.board()
                san = board.san(child.move)
                prefix = f"{board.fullmove_number}. " if board.turn == chess.WHITE else f"{board.fullmove_number}... "

                # Add 'move_row' tag to minimize space after this line
                # Pre-check if there is a valuation (value)
                raw_comment = child.comment.strip() if child.comment else ""
                comment_text = child.comment
                comment_text = ""

                has_value = False
                val_str = ""
                if raw_comment:
                    # Check for valuation (value)
                    val_match = re.match(r"^(\s?[\+\-\d\.\/\|\\=\?]{1,6})", raw_comment)
                    if val_match:
                        has_value = True
                        val_str = val_match.group(1).strip()
                        # Take the rest and remove internal newlines
                        comment_text = raw_comment[val_match.end():].replace('\n', ' ').strip()
                    else:
                        comment_text = raw_comment.replace('\n', ' ').strip()


                if comment_text:
                    val_match = re.match(r"^(\s?[\+\-\d\.\/\|\\=\?]{1,6})", comment_text)
                    if val_match:
                        has_value = True
                        val_str = val_match.group(1).strip()
                        comment_text = comment_text[val_match.end():].strip()

                # Apply 'move_row' (tight spacing) ONLY if a value follows
                line_tags = ("number",)
                if has_value:
                    line_tags = ("number", "move_row")

                self.insert(tk.END, f"\n{prefix}", line_tags)
                self._add_move_node(san, "regular", "Regulier", child)

                # Add value on a tight line
                if has_value:
                    self.insert(tk.END, f"\n  {val_str}", "value")

                # 3. Display remaining comments on separate lines
                if comment_text:
                    for line in comment_text.split('\n'):
                        self.insert(tk.END, f"\n  {line.strip()}", "comment")

                # 4. Display variants of this move below comments, in brackets
                for j in range(1, len(child.parent.variations)):
                    self.insert(tk.END, "\n  (", "variant")
                    self._process_variant_line(child.parent.variations[j], level=1, force_number=True)
                    self.insert(tk.END, ")", "variant")

                self._process_main_line(child)

    def _process_variant_line(self, node, level, force_number=False):
        """Handles variant lines compactly: '2. Nf3 d6'."""
        board = node.parent.board()
        san = board.san(node.move)
        tag = "variant" if level == 1 else "subvariant"

        # Number logic: only show for White, or if forced (after comments/brackets)
        if board.turn == chess.WHITE:
            self.insert(tk.END, f"{board.fullmove_number}. ", "number")
            next_force = False
        else:
            if force_number:
                self.insert(tk.END, f"{board.fullmove_number}... ", "number")
            next_force = False

        self._add_move_node(san, tag, "Variant", node)

        # Handle comments and sub-variations within the variant block
        if node.comment:
            self.insert(tk.END, f" {{{node.comment}}} ", "comment")
            next_force = True
        else:
            self.insert(tk.END, " ")
            next_force = (len(node.variations) > 1)

        for i, var in enumerate(node.variations):
            if i == 0: # Continue same variant line
                self._process_variant_line(var, level, force_number=next_force)
            else: # Nested sub-variation
                self.insert(tk.END, "(", "subvariant")
                self._process_variant_line(var, level + 1, force_number=True)
                self.insert(tk.END, ")", "subvariant")
                next_force = True

    def _add_move_node(self, text, tag, label, node):
        # Link the text in the widget to a move click event
        start = self.index(tk.INSERT)
        self.insert(tk.END, text, (tag, "clickable"))
        end = self.index(tk.INSERT)

        # Store the start and end index for this specific chess node
        self.node_to_index[node] = (start, end)
        unique_tag = f"m_{start.replace('.', '_')}"
        self.tag_add(unique_id := unique_tag, start, self.index(tk.INSERT))
        self.tag_bind(unique_id, "<Button-1>", lambda e, n=node, l=label: self._on_move_click(n, l))

    def highlight_node(self, node):
        """ English: Highlights the node and ensures it's fully visible. """
        self.tag_remove("active_move", "1.0", tk.END)
        self.tag_remove("active_line", "1.0", tk.END)

        if node in self.node_to_index:
            start, end = self.node_to_index[node]
            self.tag_add("active_move", start, end)

            line_num = int(start.split('.')[0])
            self.tag_add("active_line", f"{line_num}.0", f"{line_num}.end")

            # --- VERBETERDE SCROLL LOGICA ---
            try:
                # English: 1. First, look at the line BELOW the current move.
                # This ensures that when scrolling down, the current move
                # is pushed further up into the visible area.
                self.see(f"{line_num}.0 + 1 displaylines")

                # English: 2. Then look at the context above the move.
                # This 'sandwiches' the move into a good visible position.
                self.see(f"{line_num}.0 - 2 displaylines")
            except tk.TclError:
                # English: Fallback for older Tcl/Tk versions
                self.see(f"{line_num}.0")

            self.update_idletasks()

    def _on_move_click(self, node, type_label):
        # Handle the click and print details as requested
        print(f"KLIK -> Type: {type_label:15} | Zet: {node.san()}")
        self.select_callback(node, type_label)


class TouchMoveListColor(tk.Frame):
    """
    A touch-friendly replacement for tk.Listbox using a tk.Text widget.
    Supports syntax highlighting via tags and maintains compatibility
    with insert/delete/selection methods.
    """

    def __init__(self, parent, move_pairs=None, select_callback=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.move_pairs = move_pairs if move_pairs else []
        self.select_callback = select_callback
        self.selected_index = None

        # --- UI Setup ---
        self.text_area = tk.Text(
            self,
            font=("Consolas", 14),
            wrap=tk.NONE,
            bg="white",
            padx=10,
            pady=10,
            cursor="arrow",
            highlightthickness=0,
            bd=0,
            state=tk.DISABLED
        )
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text_area.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.configure(yscrollcommand=self.scrollbar.set)

        self.text_area.config(
            selectbackground=self.text_area.cget("bg"),  # Maak selectie zelfde kleur als achtergrond
            selectforeground=self.text_area.cget("fg"),  # Maak tekstkleur hetzelfde
            exportselection=False,  # Voorkom dat andere apps de selectie zien
            inactiveselectbackground=self.text_area.cget("bg"),
            spacing1=2, spacing2=0, spacing3=2
        )

        # Tags configuration
        self.text_area.tag_configure("highlight", background="#cfe2f3")
        self.text_area.tag_configure("move_num", foreground="#888888")
        self.text_area.tag_configure("white_move", foreground="black", font=("Consolas", 14, "bold"))
        self.text_area.tag_configure("variation", foreground="#0055ff")
        self.text_area.tag_configure("comment", foreground="#008000")

        # --- REVISED BINDINGS ---
        # 1. Start drag
        self.text_area.bind("<Button-1>", self._on_drag_start)
        # 2. Handle motion (scrolling) - No lambda break here, handled in function
        self.text_area.bind("<B1-Motion>", self._on_drag_motion)
        # 3. Handle release (tap/select)
        self.text_area.bind("<ButtonRelease-1>", self._on_tap)

        # Disable shift-selection
        self.text_area.bind("<Shift-Button-1>", lambda e: "break")

        self.text_area.bind("<<Selection>>", lambda e: "break")
        self.text_area.bind("<Control-a>", lambda e: "break")
        self.text_area.bind("<Double-Button-1>", lambda e: "break")

        self.drag_start_y = 0
        self.start_scroll_pos = 0
        self.scrolled_too_far = False
        self.last_y = 0
        self.velocity = 0
        self.momentum_id = None

        # --- Configure Tags ---
        # Selection highlight
        self.text_area.tag_configure("highlight", background="#cfe2f3")

        # Move number style
        self.text_area.tag_configure("move_num",
                                     foreground="gray",
                                     font=("Consolas", 11)
                                     )

        # White move style (Light gray background)
        self.text_area.tag_configure("white_move",
                                     background="#eeeeee",
                                     foreground="black",
                                     font=("Consolas", 12, "bold")
                                     )

        # Black move style (Dark background, white text)
        self.text_area.tag_configure("black_move",
                                     background="#333333",
                                     foreground="white",
                                     font=("Consolas", 12, "bold")
                                     )
        self.text_area.tag_configure("line_grey", background="#f5f5f5")
        self.text_area.tag_configure("line_major", background="#f8d7da")
        self.text_area.tag_configure("line_minor", background="#fff3cd")
        # You can add more, like a subtle yellow for a 'last move' or 'threat' line
        self.text_area.tag_configure("line_alert", background="#fff0f0")

        self.text_area.tag_lower("line_grey")
        self.text_area.tag_raise("highlight", "line_grey")
        self.text_area.tag_raise("highlight", "line_major")
        self.text_area.tag_raise("highlight", "line_minor")

        if self.move_pairs:
            self._populate()

    def _populate(self):
        """ Clears and fills the text area with initial move pairs. """
        self.delete(0, tk.END)
        for i, move in enumerate(self.move_pairs):
            self.insert(tk.END, move)

    def _on_click(self, event):
        """ Records the start of a click/drag. """
        self.drag_start_y = event.y
        self.scrolled_too_far = False

    def _on_drag_start(self, event):
        """ Capture start and cancel any existing momentum. """
        if self.momentum_id:
            self.after_cancel(self.momentum_id)
            self.momentum_id = None

        self.drag_start_y = event.y
        self.last_y = event.y
        self.start_scroll_pos = self.text_area.yview()[0]
        self.scrolled_too_far = False
        self.velocity = 0
        return "break"

    def _on_drag_motion(self, event):
        """ Calculate instantaneous velocity during movement. """
        delta_y = event.y - self.drag_start_y

        # Calculate velocity for momentum (pixels moved since last motion event)
        self.velocity = event.y - self.last_y
        self.last_y = event.y

        if abs(delta_y) > 5:
            self.scrolled_too_far = True

        height = self.text_area.winfo_height()
        if height > 1:
            new_pos = self.start_scroll_pos - (delta_y / height)
            self.text_area.yview_moveto(max(0, min(1, new_pos)))

        return "break"

    def _on_tap(self, event):
        """ On release, either trigger selection or start momentum. """
        if self.scrolled_too_far:
            # If the user was moving fast, start the decay
            if abs(self.velocity) > 2:
                self._apply_momentum(self.velocity)
            return "break"

        # Selection logic (unchanged)
        index_str = self.text_area.index(f"@{event.x},{event.y}")
        line_index = int(index_str.split('.')[0]) - 1
        self.selection_set(line_index)
        if self.select_callback:
            self.select_callback(line_index)
        return "break"

    def _apply_momentum(self, current_velocity):
        """ Gradually decrease speed and scroll the view in the correct direction. """
        # Friction: Every 10ms we reduce the speed
        friction = 0.92
        new_velocity = current_velocity * friction

        if abs(new_velocity) > 0.5:
            height = self.text_area.winfo_height()
            if height > 1:
                # Get current top position
                current_pos = self.text_area.yview()[0]

                # CORRECTION:
                # If velocity is negative (swiping up), we want to ADD to current_pos
                # to move the scrollbar down.
                # If velocity is positive (swiping down), we want to SUBTRACT.
                shift = new_velocity / height

                # By subtracting a negative shift, we effectively add it.
                new_scroll_pos = current_pos - shift

                self.text_area.yview_moveto(max(0, min(1, new_scroll_pos)))

                # Schedule the next frame
                self.momentum_id = self.after(10, lambda: self._apply_momentum(new_velocity))
        else:
            self.momentum_id = None

    # --- Public API (Listbox Compatibility) ---
    def insert(self, index, move_text, tag_override=""):
        """
        Inserts PGN text.
        If tag_override starts with 'line_', the whole line gets that background.
        """
        self.text_area.config(state=tk.NORMAL)

        # Determine the starting position of this new line
        start_index = self.text_area.index("end-1c")

        pattern = re.compile(r'(\d+\.+\s?)|(\(.+?\))|(\{.+?\})|([^\s(){}\[\]]+)|(\s+)')

        # We still need to know if it's white or black for the move boxes
        # If the override is a line tag, we assume white by default unless we check the text
        is_white = "black" not in (tag_override or "").lower()

        for match in pattern.finditer(str(move_text)):
            move_num, variation, comment, move, whitespace = match.groups()

            # Collect tags for this specific segment
            tags = []
            if tag_override and tag_override.startswith("line_"):
                tags.append(tag_override)

            if move_num:
                tags.append("move_num")
                self.text_area.insert(tk.END, move_num, tuple(tags))
            elif variation:
                tags.append("variation")
                self.text_area.insert(tk.END, variation, tuple(tags))
            elif comment:
                tags.append("comment")
                self.text_area.insert(tk.END, f"{comment} ", tuple(tags))
            elif move:
                # Add the specific move box tag
                if "move" in tag_override:
                    tags.append(tag_override)
                self.text_area.insert(tk.END, f" {move} ", tuple(tags))
            elif whitespace:
                self.text_area.insert(tk.END, whitespace, tuple(tags))

        # Apply the line tag to the trailing newline as well to avoid white gaps
        end_index = self.text_area.index("end-1c")
        if tag_override and tag_override.startswith("line_"):
            self.text_area.insert(tk.END, "\n", tag_override)
        else:
            self.text_area.insert(tk.END, "\n")

        self.text_area.config(state=tk.DISABLED)

    def delete(self, first, last=None):
        """ Deletes lines from the text area. """
        self.text_area.config(state=tk.NORMAL)
        if first == 0 and (last == tk.END or last is None):
            self.text_area.delete("1.0", tk.END)
        else:
            start = f"{first + 1}.0"
            end = f"{last + 1}.0" if last else f"{first + 2}.0"
            self.text_area.delete(start, end)
        self.text_area.config(state=tk.DISABLED)

    def selection_set(self, index):
        """ Highlights the specified line. """
        self.selection_clear()
        self.selected_index = index

        start = f"{index + 1}.0"
        end = f"{index + 1}.end + 1c"
        self.text_area.tag_add("highlight", start, end)
        self.see(index)

    def selection_clear(self, first=None, last=None):
        """ Removes highlighting from all lines. """
        self.text_area.tag_remove("highlight", "1.0", tk.END)
        self.selected_index = None

    def see(self, index):
        """ Scrolls the text area to the given line index. """
        self.text_area.see(f"{index + 1}.0")

    def size(self):
        """ Returns the number of lines. """
        return int(self.text_area.index('end-1c').split('.')[0])

    def get(self, index):
        """ Returns the text of the line at the given index. """
        return self.text_area.get(f"{index + 1}.0", f"{index + 1}.end")

    def scroll_to_start(self):
        """
        Scrolls the move list back to the very first move.
        """
        # 0.0 means the very top (0%) of the scrollable area
        self.text_area.yview_moveto(0.0)

    def set_font_size(self, size):
        """
        Updates the font size for the main text area and all specific tags.
        """
        # 1. Update the main widget font
        current_font = ("Consolas", size)
        self.text_area.config(font=current_font)

        # 2. Update specific tags that have their own font settings
        # Bold tags for moves
        bold_font = ("Consolas", size, "bold")
        self.text_area.tag_configure("white_move", font=bold_font)
        self.text_area.tag_configure("black_move", font=bold_font)

        # Slightly smaller or different styles for other tags
        normal_font = ("Consolas", size)
        self.text_area.tag_configure("move_num", font=("Consolas", max(8, size - 1)))
        self.text_area.tag_configure("variation", font=normal_font)
        self.text_area.tag_configure("comment", font=normal_font)


# English: Base Strategy Class
class MoveListController:
    """
    English: Abstract base class to ensure a consistent interface for
    different move list implementations.
    """

    def __init__(self, master, select_callback):
        self.widget = None
        self.master = master
        self.select_callback = select_callback

    def update_view(self, game, move_list):
        raise NotImplementedError

    def set_selection(self, index, game):
        raise NotImplementedError


# English: Concrete Strategy for the Legacy Listbox
class LegacyMoveListController(MoveListController):
    def __init__(self, app, master, select_callback):
        super().__init__(master, select_callback)
        # English: Initialization logic moved here
        self.widget = TouchMoveListColor(master, select_callback=self.select_callback)
        self.widget.set_font_size(12)
        self.master = master
        self.app = app

    def update_view(self, game, move_list):
        # Clear the existing list
        self.widget.delete(0, tk.END)

        if not self.app.game:
            return
        self.app.move_tags = []
        for i, node in enumerate(self.app.move_list):
            prev_board = node.parent.board()
            move_num = (i // 2) + 1

            # Build the string for the Regex to parse
            if prev_board.turn == chess.WHITE:
                prefix = f"{move_num}. "
            else:
                # Check if we need '...' for black's first move in a list
                if i == 0 or self.app.move_list[i - 1].parent.board().turn == chess.WHITE:
                    prefix = f"{move_num}... "
                else:
                    prefix = "    "  # Space for alignment

            san_move = prev_board.san(node.move)
            new_comment = node.comment.strip().replace('\n', ' ')

            new_comment = new_comment[:6] + new_comment[6:40].replace(" ", "\u00A0")
            # Format comments for our Regex: {Comment}
            comment_text = f"{{{new_comment}}}" if node.comment and node.comment.strip() else ""

            # Variation indicators (can be colored as variations using parentheses)
            variation_text = f"({len(node.variations) - 1})" if len(node.variations) > 1 else ""

            full_line = f"{prefix}{san_move}{variation_text}{comment_text}"

            # Insert into the new widget - it handles the tags/colors!
            # Determine the tag based on whose turn it was
            current_tag = "" if prev_board.turn == chess.WHITE else "line_grey"
            if i in self.app.top_5_major_set:
                current_tag = "line_major"
            if i in self.app.top_5_minor_set:
                current_tag = "line_minor"
            # The widget's insert method now uses this tag to color the move
            self.app.move_tags.append(current_tag)
            self.widget.insert(tk.END, full_line, tag_override=current_tag)

    def set_selection(self, index, game):
        if 0 <= index < self.widget.size():
            self.widget.selection_set(index)
        else:
            self.widget.selection_clear()


# English: Concrete Strategy for the New PrettyMoveList
class PrettyMoveListController(MoveListController):
    def __init__(self, app, master, select_callback):
        super().__init__(master, select_callback)
        # English: Initialization logic for the tree-based widget
        self.widget = PrettyMoveList(master, select_callback=self.select_callback)
        self.app = app

    def update_view(self, game, move_list):
        # English: The tree widget handles everything via the game object
        self.widget.load_pgn(game)

    def set_selection(self, index, game):
        # get move self.current_move_index from self.game
        # pass this move to self.move_list_widget.highlight_node(node)
        # Start at the beginning of the game
        current_node = self.app.game

        # Traverse the main line until reaching the target index
        # Note: ply 1 is the first move, current_move_index is likely 0-based
        for _ in range(self.app.current_move_index + 1):
            next_node = current_node.next()
            if next_node is not None:
                current_node = next_node
            else:
                # Stop if the game is shorter than the index
                break

        # English: Traverse the tree to find the correct node for highlighting
        current_node = game
        for _ in range(index + 1):
            next_node = current_node.next()
            if next_node:
                current_node = next_node
            else:
                break
        self.widget.highlight_node(current_node)

class TouchFileDialog(tk.Toplevel):
    def __init__(self, parent, initialdir=".", file_extension=".pgn", title="PGN Browser"):
        super().__init__(parent)
        self.title(title)

        # --- Responsive Geometry for Chromebook ---
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Use 90% of screen height to ensure footer buttons are visible
        win_height = 700
        win_width = min(500, int(screen_width * 0.95))
        self.geometry(f"{win_width}x{win_height}+50+30")

        self.grab_set()
        self.focus_set()

        # --- State Management ---
        self.result = None
        self.current_dir = os.path.abspath(initialdir)
        self.file_extension = file_extension
        self.item_mapping = {}
        self.current_sort = "name"
        self.sort_reverse = False  # track toggle state
        self.show_folders = tk.BooleanVar(value=True)  # folder visibility
        self.filter_small_pgn = tk.BooleanVar(value=False)

        # --- Touch Logic ---
        self.start_y = 0
        self.is_dragging = False
        self.click_threshold = 8

        self.configure(bg="#2d2d2d")

        # --- Style for the Fat Scrollbar ---
        style = ttk.Style()
        style.configure("Fat.Vertical.TScrollbar", width=25, arrowsize=20)

        # 1. Header (Breadcrumbs)
        self.header_frame = tk.Frame(self, bg="#404040", pady=5)
        self.header_frame.pack(fill=tk.X)

        # 2. Sorting Bar
        sort_frame = tk.Frame(self, bg="#333333", pady=2)
        sort_frame.pack(fill=tk.X)
        btn_opt = {"font": ("Arial", 10, "bold"), "bg": "#505050", "fg": "white", "padx": 10, "pady": 5}

        tk.Button(sort_frame, text="Sort: Name", command=lambda: self._load_dir("name"), **btn_opt).pack(side=tk.LEFT,
                                                                                                         padx=10)
        tk.Button(sort_frame, text="Sort: Date", command=lambda: self._load_dir("date"), **btn_opt).pack(side=tk.LEFT,
                                                                                                         padx=5)

        # Folder toggle checkbox
        self.folder_chk = tk.Checkbutton(sort_frame, text="Folders", variable=self.show_folders,
                                         command=lambda: self._load_dir(self.current_sort),
                                         bg="#333333", fg="white", selectcolor="#2d2d2d",
                                         activebackground="#333333", activeforeground="white",
                                         font=("Arial", 9))
        self.folder_chk.pack(side=tk.RIGHT, padx=10)
        # Checkbox for large PGN's (> 6KB)
        tk.Checkbutton(sort_frame, text="> 6KB", variable=self.filter_small_pgn,
                       command=lambda: self._load_dir(self.current_sort),
                       bg="#333333", fg="white", selectcolor="#2d2d2d",
                       activebackground="#333333", activeforeground="white",
                       font=("Arial", 9)).pack(side=tk.RIGHT, padx=5)

        # 3. Main Area
        container = tk.Frame(self, bg="#1e1e1e")
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.scrollbar = ttk.Scrollbar(container, orient="vertical", style="Fat.Vertical.TScrollbar")
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Reduced font size to 13 for more items per page
        self.list_area = tk.Text(container, bg="#1e1e1e", fg="white", font=("Arial", 13),
                                 padx=10, pady=10, wrap=tk.NONE,
                                 highlightthickness=0, borderwidth=0,height=9,
                                 exportselection=False,
                                 yscrollcommand=self.scrollbar.set)
        self.list_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.list_area.yview)

        # Compact Style Tags (reduced spacing)
        self.list_area.tag_configure("folder", foreground="#ffca28", font=("Arial", 12, "bold"))
        self.list_area.tag_configure("file", foreground="#ffffff")
        self.list_area.tag_configure("details", foreground="#aaaaaa", font=("Arial", 8))
        self.list_area.tag_configure("selected", background="#005a9e", foreground="white")
        # spacing reduced from 15 to 8
        self.list_area.tag_configure("row", spacing1=6, spacing3=6, lmargin1=5)

        # Bindings
        self.list_area.bind("<Button-1>", self._on_press)
        self.list_area.bind("<B1-Motion>", self._on_drag)
        self.list_area.bind("<ButtonRelease-1>", self._on_release)
        self.list_area.bind("<<Selection>>", lambda e: self.list_area.tag_remove("sel", "1.0", tk.END))

        # 4. Footer (Action Buttons)
        footer = tk.Frame(self, bg="#2d2d2d", pady=10)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        self.open_btn = tk.Button(footer, text="OPEN FILE", command=self._confirm_selection,
                                  bg="#28a745", fg="white", font=("Arial", 12, "bold"),
                                  width=12, height=1, state=tk.DISABLED, pady=10)
        self.open_btn.pack(side=tk.RIGHT, padx=20)

        tk.Button(footer, text="CANCEL", command=self.destroy,
                  bg="#dc3545", fg="white", font=("Arial", 12, "bold"),
                  width=10, height=1, pady=10).pack(side=tk.RIGHT)

        self._update_breadcrumb()
        self._load_dir()

    def _on_press(self, event):
        self.start_y = event.y
        self.is_dragging = False
        self.list_area.scan_mark(event.x, event.y)
        return "break"

    def _on_drag(self, event):
        if abs(event.y - self.start_y) > self.click_threshold:
            self.is_dragging = True

        if self.is_dragging:
            self.list_area.scan_dragto(event.x, event.y)
            self.list_area.tag_remove("sel", "1.0", tk.END)
        return "break"

    def _on_release(self, event):
        if not self.is_dragging:
            index = self.list_area.index(f"@{event.x},{event.y}")
            self._handle_tap(index)
        self.is_dragging = False
        return "break"

    def _handle_tap(self, index):
        tags = self.list_area.tag_names(index)
        for t in tags:
            if t.startswith("item_"):
                item = self.item_mapping.get(t)
                if not item: continue
                if item['is_dir']:
                    self._change_dir(item['path'])
                else:
                    self._select_file(item['path'], t)
                break

    def _load_dir(self, sort_by=None):
        # NEW: Toggle logic
        if sort_by == self.current_sort:
            self.sort_reverse = not self.sort_reverse
        else:
            self.current_sort = sort_by if sort_by else "name"
            self.sort_reverse = False
            # Default behavior: names ascending, dates descending
            if self.current_sort == "date":
                self.sort_reverse = True

        self.list_area.config(state=tk.NORMAL)
        self.list_area.delete("1.0", tk.END)
        self.item_mapping = {}
        self.result = None
        self.open_btn.config(state=tk.DISABLED)

        try:
            entries = list(os.scandir(self.current_dir))

            # Sort logic incorporating the toggle
            entries.sort(
                key=lambda e: (not e.is_dir(), e.name.lower() if self.current_sort == "name" else e.stat().st_mtime),
                reverse=self.sort_reverse
            )

            for entry in entries:
                # Skip folders if checkbox is unchecked
                if entry.is_dir() and not self.show_folders.get():
                    continue
                if self.filter_small_pgn.get():
                    file_size_kb = entry.stat().st_size / 1024
                    if file_size_kb <= 6:
                        continue

                if entry.is_dir() or entry.name.lower().endswith(self.file_extension):
                    tag_type = "folder" if entry.is_dir() else "file"
                    icon = "📁" if entry.is_dir() else "📄"
                    item_tag = f"item_{hash(entry.path)}"
                    self.item_mapping[item_tag] = {'path': entry.path, 'is_dir': entry.is_dir()}

                    self.list_area.insert(tk.END, f" {icon}  {entry.name}\n", (tag_type, "row", item_tag))
                    mtime = datetime.fromtimestamp(entry.stat().st_mtime).strftime('%d-%m-%Y %H:%M')
                    self.list_area.insert(tk.END, f"      {mtime}\n", ("details", "row", item_tag))
                    self.list_area.insert(tk.END, "—" * 40 + "\n", "details")
        except Exception as e:
            self.list_area.insert(tk.END, f"Error: {e}")

        self.list_area.config(state=tk.DISABLED)
        self.list_area.yview_moveto(0)

    def _select_file(self, path, tag):
        self.list_area.tag_remove("selected", "1.0", tk.END)
        ranges = self.list_area.tag_ranges(tag)
        if ranges:
            self.list_area.tag_add("selected", ranges[0], ranges[1])
        self.result = path
        self.open_btn.config(state=tk.NORMAL)

    def _change_dir(self, new_path):
        self.current_dir = os.path.abspath(new_path)
        self._update_breadcrumb()
        self._load_dir()

    def _update_breadcrumb(self):
        for widget in self.header_frame.winfo_children():
            widget.destroy()
        tk.Button(self.header_frame, text=" ⬅ UP ", bg="#555555", fg="white",
                  font=("Arial", 10, "bold"), padx=10, pady=2,
                  command=lambda: self._change_dir(os.path.dirname(self.current_dir))).pack(side=tk.LEFT, padx=10)

        parts = [p for p in self.current_dir.split(os.sep) if p]
        acc_path = "/" if self.current_dir.startswith("/") else ""
        for part in parts[-3:]:
            idx = parts.index(part)
            btn_path = os.sep + os.sep.join(parts[:idx + 1]) if self.current_dir.startswith(os.sep) else os.sep.join(
                parts[:idx + 1])
            tk.Button(self.header_frame, text=f"{part} >", fg="#bbdefb", bg="#404040", relief=tk.FLAT,
                      font=("Arial", 9),
                      command=lambda p=btn_path: self._change_dir(p)).pack(side=tk.LEFT)

    def _confirm_selection(self):
        if self.result:
            self.destroy()
            
class GameChooserDialog(tk.Toplevel):
    """
    A Toplevel dialog for selecting a game from a PGN list,
    featuring touch-friendly canvas scrolling.
    """

    def __init__(self, master, all_games, current_game_index, switch_callback):
        # Toplevel initialization
        super().__init__(master)

        # --- External Data ---
        self.all_games = all_games
        self.current_game_index = current_game_index
        # Callback function from the main class (e.g., self._switch_to_game)
        self.switch_callback = switch_callback

        # --- Internal State ---
        self.selected_index = None
        self.drag_data = {
            "_start_y": 0,
            "_last_y": 0,
            "_is_dragging": False,
            "selected_label": None
        }
        self.game_labels = []

        # --- UI Setup ---
        self.title("Choose Game")
        self.transient(master)  # Ensures the dialog stays on top of the master
        self.grab_set()  # Modal behavior

        # Call the UI builder
        self._build_ui(master)

        # Wait until the dialog is destroyed
        self.master.wait_window(self)

    def _build_ui(self, master):
        """Builds the entire user interface within the Toplevel."""

        tk.Label(self, text="Select a game from the list:", font=('Arial', 10, 'bold')).pack(padx=10, pady=5)

        listbox_frame = tk.Frame(self, padx=10, pady=5)
        listbox_frame.pack(fill='both', expand=True)

        # 1. Create the Canvas (the viewport)
        self.game_canvas = tk.Canvas(listbox_frame, borderwidth=0, highlightthickness=0, height=15 * 25)
        self.game_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 2. Create Scrollbar and link it to the Canvas
        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.game_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.game_canvas.config(yscrollcommand=scrollbar.set)

        # 3. Create Inner Frame (the scrollable content container)
        self.canvas_inner_frame = tk.Frame(self.game_canvas)

        # 4. Attach the Inner Frame to the Canvas
        self.canvas_window_id = self.game_canvas.create_window(
            (0, 0),
            window=self.canvas_inner_frame,
            anchor="nw",
            tags="inner_frame"
        )

        # --- Bindings and Populating ---
        self._populate_and_bind_content()
        self._setup_global_bindings()
        self._center_and_focus(master)

    # --- HELPER FUNCTIONS (Now class methods) ---

    def update_scroll_region(self, event=None):
        """Adjusts the inner frame width and the Canvas scrollregion."""
        self.game_canvas.update_idletasks()
        self.game_canvas.itemconfig(self.canvas_window_id, width=self.game_canvas.winfo_width())
        bbox = self.game_canvas.bbox("all")
        if bbox:
            canvas_height = self.game_canvas.winfo_height()
            if bbox[3] > canvas_height:
                self.game_canvas.config(scrollregion=bbox)
            else:
                # Content is smaller than viewport: disable scrolling
                self.game_canvas.config(scrollregion=(0, 0, bbox[2], canvas_height))

    def start_scroll(self, event):
        """Registers the start position (absolute Y) of the drag."""
        self.drag_data["_start_y"] = event.y_root
        self.drag_data["_is_dragging"] = False
        return "break"

    def do_scroll(self, event):
        """Calculates the delta and scrolls the Canvas content."""
        MIN_DRAG_DISTANCE = 5
        if not self.drag_data["_is_dragging"]:
            if abs(event.y_root - self.drag_data["_start_y"]) > MIN_DRAG_DISTANCE:
                self.drag_data["_is_dragging"] = True
                self.drag_data["_last_y"] = event.y_root
            else:
                return

        delta = self.drag_data["_last_y"] - event.y_root
        self.game_canvas.yview_scroll(int(delta / 4), "units")
        self.drag_data["_last_y"] = event.y_root

        # Clear visual selection during scrolling
        if self.drag_data["selected_label"]:
            self.drag_data["selected_label"].config(background='white', foreground='black')
            self.drag_data["selected_label"] = None

        return "break"

    def on_release_or_select(self, event):
        """Handles item selection if it was a click (not a scroll)."""
        if self.drag_data["_is_dragging"]:
            self.drag_data["_is_dragging"] = False
            return

        # Clear previous visual selections
        for lbl in self.game_labels:
            lbl.config(background='white', foreground='black')
        self.drag_data["selected_label"] = None

        widget_clicked = event.widget
        if hasattr(widget_clicked, 'game_index'):
            # Select the label visually
            widget_clicked.config(background='#0078D7', foreground='white')
            self.drag_data["selected_label"] = widget_clicked

        self.drag_data["_is_dragging"] = False

    def select_game_and_close(self, selected_index=None):
        """Handles the selection and closes the dialog."""

        if selected_index is not None:
            final_index = selected_index
        elif self.drag_data["selected_label"]:
            final_index = self.drag_data["selected_label"].game_index
        else:
            messagebox.showwarning("Selection Error", "Please select a game from the list.", parent=self.master)
            return

        if final_index is not None and final_index != self.current_game_index:
            # Call the callback function in the main class
            self.switch_callback(final_index)

        self.destroy()  # Close the dialog

    # --- POPULATE AND BIND METHODS ---

    def _populate_and_bind_content(self):
        """Fills the list with labels and binds local events."""

        for i, game in enumerate(self.all_games):
            white = game.headers.get("White", "???")
            black = game.headers.get("Black", "???")
            result = game.headers.get("Result", "*-*")
            event_name = game.headers.get("Event", "Untitled")

            list_item = f"Game {i + 1}: {white} - {black} ({result}) | {event_name}"

            lbl = ttk.Label(
                self.canvas_inner_frame,
                text=list_item,
                font=('Consolas', 10),
                anchor='w',
                padding=(5, 2),
                background='white',
                cursor='hand2'
            )
            lbl.pack(fill=tk.X, pady=0)
            lbl.game_index = i

            # Bind touch events
            lbl.bind("<ButtonPress-1>", self.start_scroll)
            lbl.bind("<B1-Motion>", self.do_scroll)
            lbl.bind("<ButtonRelease-1>", self.on_release_or_select)
            # Bind double-click to select action
            lbl.bind('<Double-Button-1>', lambda e, index=i: self.select_game_and_close(index))

            self.game_labels.append(lbl)

        # Pre-selection and scrolling
        if 0 <= self.current_game_index < len(self.game_labels):
            pre_selected_label = self.game_labels[self.current_game_index]
            pre_selected_label.config(background='#0078D7', foreground='white')
            self.drag_data["selected_label"] = pre_selected_label

            self.update_idletasks()
            # Scroll to the selected game's position
            self.game_canvas.yview_moveto(pre_selected_label.winfo_y() / self.game_canvas.winfo_reqheight())

        # Buttons at the bottom
        button_frame = tk.Frame(self, pady=10)
        button_frame.pack()

        tk.Button(button_frame, text="Select Game", command=self.select_game_and_close, width=15,
                  bg='#d9ffc7').pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Cancel", command=self.destroy, width=15, bg='#ffe0e0').pack(side=tk.LEFT,
                                                                                                  padx=10)

    def _setup_global_bindings(self):
        """Binds events to the canvas and the window."""
        self.game_canvas.bind('<Configure>', self.update_scroll_region)
        self.game_canvas.bind("<ButtonPress-1>", self.start_scroll)
        self.game_canvas.bind("<B1-Motion>", self.do_scroll)
        self.game_canvas.bind("<ButtonRelease-1>", self.on_release_or_select)
        # Bind mouse wheel for desktop users
        self.game_canvas.bind_all('<MouseWheel>',
                                  lambda e: self.game_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self.update_scroll_region()  # Initial call

    def _center_and_focus(self, master):
        """Centers the dialog on the master window."""
        self.update_idletasks()
        dialog_width = self.winfo_reqwidth()
        dialog_height = self.winfo_reqheight()
        position_x = master.winfo_x() + (master.winfo_width() // 2) - (dialog_width // 2)
        position_y = master.winfo_y() + (master.winfo_height() // 2) - (dialog_height // 2)
        self.geometry(f'+{position_x}+{position_y}')
        self.focus_force()


COMPACT_HEIGHT_THRESHOLD = 1000


class AnalysisProgressUI:
    def __init__(self, parent, title="Database Analysis"):
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("450x250")
        self.window.resizable(False, False)

        # Ensure the window stays on top and centers relative to parent
        self.window.transient(parent)
        self.window.grab_set()

        # Styling based on your app's theme could be added here
        self.window.configure(bg="#f8f9fa")

        # --- Widgets ---
        # Database level progress (e.g., "Game 5 of 100")
        self.db_label = tk.Label(self.window, text="Preparing...",
                                 font=("Segoe UI", 10, "bold"), bg="#f8f9fa", fg="#2c3e50")
        self.db_label.pack(pady=(20, 5))

        # Current move/engine status
        self.status_label = tk.Label(self.window, text="Initializing engine...",
                                     font=("Segoe UI", 9), bg="#f8f9fa", wraplength=400)
        self.status_label.pack(pady=10)

        # Progress bar for the current game
        style = ttk.Style()
        style.configure("TProgressbar", thickness=20)
        self.progress_bar = ttk.Progressbar(self.window, length=350, mode='determinate', style="TProgressbar")
        self.progress_bar.pack(pady=10)

        # Cancel flag and button
        self.is_cancelled = False
        self.cancel_button = tk.Button(self.window, text="Stop All",
                                       command=self.request_cancel,
                                       bg="#e74c3c", fg="white", font=("Segoe UI", 9, "bold"),
                                       activebackground="#c0392b", padx=20)
        self.cancel_button.pack(pady=20)

    def request_cancel(self):
        """ Callback for the stop button. """
        if messagebox.askyesno("Confirm", "Stop the entire analysis process?"):
            self.is_cancelled = True
            self.status_label.config(text="Stopping... please wait.")

    def update_db_info(self, text):
        """ Update the top-level database info. """
        self.window.after(0, lambda: self.db_label.config(text=text))

    def update_status(self, text):
        """ Update the current move status. """
        self.window.after(0, lambda: self.status_label.config(text=text))

    def update_progress(self, value, maximum=None):
        """ Update the progress bar value. """

        def _update():
            if maximum is not None:
                self.progress_bar.config(maximum=maximum)
            self.progress_bar.config(value=value)

        self.window.after(0, _update)

    def destroy(self):
        """ Safely close the window. """
        self.window.grab_release()
        self.window.destroy()

class ChessAnnotatorApp:
    def __init__(self, master, pgn_game, engine_name, hide_file_load = False, image_manager = None, square_size = 75,
                 current_game_index = -1, piece_set = "", board="Standard", swap_colours = False, call_back = None,
                 engine_depth=17):
        print("parameters:",pgn_game, engine_name, hide_file_load, image_manager, square_size, current_game_index, piece_set, board)

        self.theme_name=board
        self.master = master
        self.piece_set = piece_set
        self.square_size = square_size if square_size else 75
        self.image_manager = image_manager
        self.default_pgn_dir = ""
        self.hide_file_load = hide_file_load
        self.is_manual = False
        self.selected_square = None
        self.move_list_type = "TouchMoveListColor"
        #self.move_list_type = "PrettyMoveList"
        self.highlight_item = None
        self.swap_colours = swap_colours
        self.call_back = call_back
        self.is_dirty = False
        self.engine_depth = engine_depth
        master.title("PGN Chess Annotator")
        self.set_theme()
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- Data Initialization ---
        self.all_games = []      # List of all chess.pgn.Game objects in the PGN file
        try:
            self.current_game_index = int(current_game_index) # Index of the current game in all_games
        except:
            self.current_game_index = 0
        self.game = None         # The current chess.pgn.Game object
        self.board = None        # The current chess.Board object
        self.move_list = []      # List of all GameNode objects in the main variation
        self.current_move_index = -1 # Index in move_list. -1 = starting position
        self.meta_entries = {}   # Dictionary to store the Entry widgets for meta-tags
        self.game_menu = None    # Reference to the Game Menu for updating item states
        self.stored_moves = []
        self.top_5_major_set = {}
        self.top_5_minor_set = {}

        # Store button references for robust access
        self.insert_edit_comment_button = None
        self.manage_variations_button = None # New button reference
        self.delete_comment_button = None
        if engine_name is None or len(engine_name) == 0:
            self.ENGINE_PATH = "/home/user/Schaken/stockfish-python/Python-Easy-Chess-GUI/Engines/stockfish-ubuntu-x86-64-avx2"
        else:
            self.ENGINE_PATH = engine_name
        # The engine will analyze up to this many best moves (MPV)
        self.ENGINE_MULTI_PV = 3
        # The analysis depth in ply
        self.ENGINE_DEPTH = self.engine_depth

        # Sample PGN (contains two games with variation added to the first game)
        self.sample_pgn = """
[Event "F/S Mostar"]
[Site "Mostar BIH"]
[Date "2000.04.14"]
[Round "4"]
[White "Bender, Zdenko"]
[Black "Anic, Darko"]
[Result "1-0"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be3 e6 7. f3 Be7 8. Qd2 Qc7 9. O-O-O Nc6 10. g4 Bd7 11. h4 h6 12. Be2 Nxd4 13. Bxd4 e5 14. Be3 b5 15. a3 Rc8 16. g5 Nh5 17. Nd5 Qxc2+ 18. Qxc2 Rxc2+ 19. Kxc2 Ng3 (19... O-O-O 20. Nb4 Kb7 21. Nd5 Kc8) 20. Rhe1 Nxe2 21. Rxe2 hxg5 22. hxg5 Rh3 23. Rf2  Bd8 24. Rdd2 Be6 25. Nb4 a5 26. Na2 Kd7 27. Nc3 b4 28. Nd5 bxa3 29. bxa3 f5 30. gxf6 gxf6 31. Bb6 Rh8 32. Bxd8 Kxd8 33. Nxf6 Ke7 34. Nd5+ Kf7 35. f4 Rh3 36. fxe5+ Kg6 37. Rf6+ Kg5 38. Rxe6 dxe5 39. Rxe5+ Kg4 40. Nf6+ Kf4 41. Rxa5 1-0

[Event "F/S Mostar"]
[Site "Mostar BIH"]
[Date "2000.04.14"]
[Round "5"]
[White "Anic, Darko"]
[Black "Bender, Zdenko"]
[Result "0-1"]

1. d4 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. Nf3 O-O 6. Be2 e5 7. O-O Nc6 8. d5 Ne7 9. Ne1 Nd7 10. f3 f5 11. Be3 f4 12. Bf2 g5 13. a4 Nf6 14. Nd3 b6 15. b4 Nf6 16. c5 h5 17. Rc1 Rf7 18. Nb5 a6 19. Nxd6 cxd6 20. cxd6 Qxd6 21. Rc6 Qd8 22. d6 g4 23. Qb3 Bd7 24. Rc7 Qe8 25. Rfc1 g3 26. hxg3 fxg3 27. Bxg3 h4 28. Bh2 Nf4 29. Bf1 Kh7 30. Nxf4 exf4 31. Bxf4 Qg8 32. Bc4 Rf8 33. Bxg8+ Rxg8 34. Be5 h3 35. gxh3 Nh5 36. Kh2 Raf8 37. Bxg7 Rxg7 38. Rxd7 Rxd7 39. Qe6 Rg7 40. Qf5+ Kh6 41. Rc7 0-1
"""

        # --- UI Setup ---
        self._setup_menu_bar(master)

        self.touch_screen = False
        self.large_screen = True
        self.setup_ui( master)

        self._setup_header_frame(master, self.meta_frame, self.nav_comment_frame, self.comment_frame, self.comment_display_frame)

        self._setup_main_columns(master,self.board_frame,self.moves_frame)

        master.update_idletasks()

        self.set_screen_position(master)
        self.set_filepath(pgn_game)

        if not(pgn_game is None or len(pgn_game) == 0):
            try:
                with open(pgn_game, 'r', encoding='utf-8') as f:
                    pgn_content = f.read()
                self._load_game_from_content(pgn_content)
            except Exception as e:
                messagebox.showerror("Loading Error", f"Could not read the file: {e}", parent=self.master)
        else:
            # Initialize UI status with the sample game
            self._load_game_from_content(self.sample_pgn)
        self._setup_canvas_bindings()

    def set_filepath(self, pgn_game):
        self.last_filepath = pgn_game
        self.update_meta_header()

    def set_theme(self):
        # Find the theme
        self.selected_theme = next(
            (theme for theme in BOARD_THEMES if theme["name"] == self.theme_name),
            BOARD_THEMES[0]  # Use Standard as fallback
        )

    def set_screen_position(self, master):
        # 1. Determine the maximum available width
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()

        # 2. Determine the required width of the window (minimum necessary width)
        # This is the width that your current widgets need based on the chosen layout.
        required_width = master.winfo_reqwidth()
        required_height = master.winfo_reqheight()

        # 3. Set the maximum width to prevent the window from becoming wider than the screen.
        # We use the height defined in your layout logic (e.g., 1000 pixels as a threshold)

        if screen_height < COMPACT_HEIGHT_THRESHOLD:
            # This is likely a compact/touchscreen device.

            # Use the width required by the widgets, but limit it to the screen width.
            # This prevents the window from extending beyond the screen edges.

            # The width is the required width, unless it exceeds the screen width.
            print(required_width, screen_width)
            print(required_height, screen_height)
            window_width = min(required_width, screen_width)
            window_height = min(required_height, screen_height)

            # Starting position: Top-left (+0+0) to guarantee everything is visible.
            # Set the exact geometry.
            master.geometry(f"{window_width}x{window_height}+0+0")

            # Optional: Set the minimum size to prevent the user from shrinking it too much
            master.minsize(window_width, window_height)

    def setup_ui(self, master):
        """
        Sets up the UI elements based on the initial screen height.
        """

        # Force window rendering to calculate initial dimensions
        master.update_idletasks()

        # We use SCREEN height to determine if we are on a compact device.
        # If a user starts a 100x100 window on a 4K monitor, it will still be considered wide.
        # You can use master.winfo_height() if you prefer to measure the initial DESIRED window height.

        # For this example, we use the SCREEN height:
        screen_height = master.winfo_screenheight()
        is_compact_layout = screen_height < COMPACT_HEIGHT_THRESHOLD


        if is_compact_layout or self.large_screen:
            self.touch_screen = True

            # --- 2. Create Frames ---
            # These must always be created before we place or fill them.
            self._setup_menu_bar(master)

            # --- MAIN CONTAINER ---
            # Use a PanedWindow or a Frame with grid to manage the three columns
            self.content_paned = tk.PanedWindow(master, orient=tk.HORIZONTAL, sashwidth=6)
            self.content_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # --- COLUMN 1: BOARD & COMMENTS ---
            column1_frame = tk.Frame(self.content_paned)
            self.column1_frame = column1_frame
            self.content_paned.add(column1_frame, stretch="never")
            # Column 2: Move List
            # --- COLUMN 2: MOVES (The Expanding Column) ---
            column2_frame = tk.Frame(self.content_paned, width=400)
            # stretch="always" ensures this column takes all remaining horizontal space
            self.content_paned.add(column2_frame, stretch="always")
            column2_frame.pack_propagate(False)

            # Column 3: Tools/Meta
            # --- COLUMN 3: TOOLBAR ---
            column3_frame = tk.Frame(self.content_paned)
            self.content_paned.add(column3_frame, stretch="never")

            # 1. Game Meta-Tags section (left in the header)
            meta_frame = tk.LabelFrame(column3_frame, text="Game Meta-Tags", padx=5, pady=5)
            meta_frame.pack(side=tk.TOP, padx=10, pady=5)

            comment_frame = tk.LabelFrame(column3_frame, text="Annotation Tools", padx=10, pady=5)
            comment_frame.pack(fill=tk.Y, padx=10, pady=5)

            nav_comment_frame = tk.Frame(column3_frame)
            nav_comment_frame.pack(padx=30, fill=tk.BOTH, expand=True)

            # Re-initializing main_frame for specific content
            main_frame = tk.Frame(master, padx=10, pady=10)
            main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

            # Column 1 Content: Board
            board_frame = tk.Frame(column1_frame)
            board_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5)

            # Column 2 Content: Moves
            moves_frame = tk.Frame(column2_frame)
            moves_frame.pack(fill=tk.BOTH, expand=True, padx=5)

            # Column 1 Content: Comment display below the board
            # Calculate the exact width of the chess board
            board_width = 8 * self.square_size

            # 1. Create the frame with a specific width
            # You might want to add a fixed height as well if you use pack_propagate(False)
            comment_display_frame = tk.Frame(column1_frame, width=board_width, height=100)

            # 2. Prevent the frame from resizing to fit its internal widgets
            comment_display_frame.pack_propagate(False)

            # 3. Pack it.
            # Remove 'fill=tk.X' if you want it to stay strictly at board_width.
            # Use 'anchor=tk.W' or 'anchor=tk.CENTER' to align it with the board above.
            comment_display_frame.pack(side=tk.TOP, padx=5, pady=5, anchor=tk.NW)
            toolbar_frame = self._setup_quick_toolbar(column3_frame)

        else:
            # Standard Desktop Layout
            header_frame = tk.Frame(master, bd=2, relief=tk.RAISED, padx=10, pady=5)
            header_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

            # 1. Game Meta-Tags section (left in the header)
            meta_frame = tk.LabelFrame(header_frame, text="Game Meta-Tags", padx=5, pady=5)
            meta_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

            middle_column_frame = tk.Frame(header_frame)
            # This frame should take up the remaining horizontal space
            middle_column_frame.pack(side=tk.LEFT, padx=30, fill=tk.BOTH, expand=True)

            nav_comment_frame = tk.Frame(middle_column_frame)

            # Pack this frame HERE with fill=tk.BOTH and expand=True
            # This ensures that this frame claims the remaining horizontal space between
            # meta_frame (LEFT) and comment_frame (RIGHT).
            nav_comment_frame.pack(side=tk.TOP, padx=5, fill=tk.X)

            comment_display_frame = tk.Frame(middle_column_frame)
            comment_display_frame.pack(side=tk.TOP, padx=5, fill=tk.X)

            comment_frame = tk.LabelFrame(header_frame, text="Annotation Tools", padx=10, pady=5)
            comment_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=5)

            main_frame = tk.Frame(master, padx=10, pady=10)
            main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

            # Column 1 (Left): Chess Diagram
            board_frame = tk.Frame(main_frame)
            board_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

            # Column 2 (Right): Move List
            moves_frame = tk.Frame(main_frame)
            moves_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
            #no tolbar in ordinary view
            #toolbar_frame = self._setup_quick_toolbar(moves_frame)

        # Save as class attributes so the rest of the code can access them
        self.meta_frame = meta_frame
        self.nav_comment_frame = nav_comment_frame
        self.comment_frame = comment_frame
        self.board_frame = board_frame
        self.moves_frame = moves_frame
        self.comment_display_frame = comment_display_frame

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
        if not self.hide_file_load:
            file_menu.add_command(label="Load PGN...", command=self.load_pgn_file)
            file_menu.add_command(label="Save PGN...", command=self.save_pgn_file)

        file_menu.add_command(label="Split DB", command=self.split_pgn_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=master.destroy)
        # Game Menu
        game_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Game", menu=game_menu)
        game_menu.add_command(label="Previous Game", command=lambda: self.go_game(-1), state=tk.DISABLED, accelerator="Ctrl+Left")
        game_menu.add_command(label="Next Game", command=lambda: self.go_game(1), state=tk.DISABLED, accelerator="Ctrl+Right")
        game_menu.add_command(label="Choose Game", command=self._open_game_chooser)
        game_menu.add_command(label="Analyse Game", command=self.handle_analyze_button)
        game_menu.add_command(label="Remove Analysis", command=self._clear_variations_func)
        game_menu.add_command(label="Classify Opening", command=self.handle_classify_opening_button)
        db_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="DB", menu=db_menu)
        # Create a separate menu for the sort options
        sort_menu = tk.Menu(db_menu, tearoff=0)

        # Add the sub-options for sorting
        # Using lambda to pass the property to the function
        sort_menu.add_command(label="Date", command=lambda: self.sort_pgn_file("date"))
        sort_menu.add_command(label="White Player", command=lambda: self.sort_pgn_file("white"))
        sort_menu.add_command(label="Black Player", command=lambda: self.sort_pgn_file("black"))
        sort_menu.add_command(label="Site", command=lambda: self.sort_pgn_file("site"))
        sort_menu.add_command(label="Event", command=lambda: self.sort_pgn_file("event"))

        # Add the sort_menu as a cascade to the file_menu
        db_menu.add_cascade(label="Sort DB by...", menu=sort_menu)

        db_menu.add_command(label="Analyse DB", command=self.handle_analyze_db_button)
        db_menu.add_separator()
        db_menu.add_command(label="Merge DB", command=self.merge_pgn_file)
        db_menu.add_command(label="Manage DB", command=self.manage_pgn_file)

        variations_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Variations", menu=variations_menu)
        variations_menu.add_command(label="Restore Variation", command=self.restore_variation)
        variations_menu.add_command(label="Restore All", command=self.restore_all_variations)
        variations_menu.add_separator()
        variations_menu.add_command(label="Manual Move", command=self.manual_move)
        variations_menu.add_command(label="Add New Variation", command=self._add_new_variation)
        if not self.image_manager is None:
            settings_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Settings", menu=settings_menu)
            settings_menu.add_command(label="Modify json-settings", command=lambda: self.show_settings_dialog(),
                                      state=tk.NORMAL)
            settings_menu.add_command(label="Swap Colours", command=lambda: self.swap_colours_func())
            # English: Add a separator for visual clarity
            settings_menu.add_separator()

            # English: Add the toggle for the move list type
            # We use a label that describes the action or the current state
            settings_menu.add_checkbutton(
                label="Use Pretty Move List",
                command=self.toggle_move_list_type,
                variable=tk.BooleanVar(value=(self.move_list_type == "PrettyMoveList"))
            )

        self.game_menu = game_menu
        self.variations_menu = variations_menu

        # Bind shortcuts
        master.bind('<Control-Left>', lambda e: self.go_game(-1))
        master.bind('<Control-Right>', lambda e: self.go_game(1))

    def _setup_quick_toolbar(self, parent):
        """
        Creates a compact row of icon-only buttons for common tasks.
        """
        toolbar_frame = tk.Frame(parent)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        # Styling for compact "Icon" buttons
        btn_style = {
            "font": ("Segoe UI Symbol", 10),  # Good for symbols
            "width": 3,
            "height": 1,
            "relief": tk.FLAT,
            "bg": "#f0f0f0"
        }

        # 1. Open File Button (Folder icon)
        self.open_btn = tk.Button(
            toolbar_frame,
            text="\U0001F4C2",  # 📂 Folder emoji
            command=self.load_pgn_file,
            **btn_style
        )
        self.open_btn.pack(side=tk.LEFT, padx=2)

        self.save_btn = tk.Button(
            toolbar_frame,
            text="\U0001F4BE",  # 💾 Floppy Disk
            command=self.save_pgn_file,
            **btn_style
        )
        self.save_btn.pack(side=tk.LEFT, padx=2)

        self.choose_btn = tk.Button(
            toolbar_frame,
            text="\u2630",  # ☰ Menu/List icon
            command=self._open_game_chooser,
            **btn_style
        )
        self.choose_btn.pack(side=tk.LEFT, padx=2)

        # 2. Swap Colors Button (Vertical flip arrows)
        self.swap_btn = tk.Button(
            toolbar_frame,
            text="\u21C5",  # ⇅ Up/Down arrows
            command=self.swap_colours_func,
            **btn_style
        )
        self.swap_btn.pack(side=tk.LEFT, padx=2)

        self.exit_btn = tk.Button(
            toolbar_frame,
            text="\u23FB",  # ⏻ Power symbol
            command=self.master.destroy,
            fg="red",
            **btn_style
        )
        self.exit_btn.pack(side=tk.RIGHT, padx=2)  # Place Exit on the far right

        def on_enter(e):
            e.widget.config(bg="#dddddd")

        def on_leave(e):
            e.widget.config(bg="#f0f0f0")

        self.swap_btn.bind("<Enter>", on_enter)
        self.swap_btn.bind("<Leave>", on_leave)

        # 3. Add Tooltips (Optional, helps users know what the icons do)
        _add_tooltip(self.open_btn, "Open PGN File")
        _add_tooltip(self.swap_btn, "Flip Board (Swap Colors)")
        _add_tooltip(self.save_btn, "Save PGN File")
        _add_tooltip(self.choose_btn, "Choose game")
        _add_tooltip(self.exit_btn, "Exit program")
        return toolbar_frame

    def on_closing(self):
        """
        Saves the current session information and closes the application.
        Checks for unsaved changes (is_dirty) before exiting.
        """
        if self.is_dirty:
            # Ask the user what to do with unsaved changes
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save before exiting?",
                parent=self.master
            )

            if response:
                # User clicked 'Yes' -> Save and then proceed to close
                self.save_pgn_file()
                # Note: you might want to check if _save_pgn actually succeeded
                # before continuing, but usually we proceed here.
            elif response is False:
                # User clicked 'No' -> Do not save, just proceed to close
                pass
            else:
                # User clicked 'Cancel' or closed the dialog -> Stop the closing process
                return

        # 1. Save general settings/preferences
        self.save_preferences_class()

        # 2. Close the app
        self.master.destroy()

        # 3. Handle the callback if present
        if self.call_back is not None:
            param = self.last_filepath
            self.store_pgn_file(param)
            self.call_back(param)

    def toggle_move_list_type(self):
        """
        English: Swaps between PrettyMoveList and TouchMoveListColor,
        then re-initializes the controller and UI.
        """
        # English: Toggle the setting
        if self.move_list_type == "PrettyMoveList":
            self.move_list_type = "TouchMoveListColor"
        else:
            self.move_list_type = "PrettyMoveList"

        # English: Remove the old widget from the screen
        if hasattr(self, 'move_list_widget') and self.move_list_widget.widget:
            self.move_list_widget.widget.destroy()

        # English: Re-initialize the correct controller (using the Strategy Pattern classes)
        if self.move_list_type == "TouchMoveListColor":
            self.move_list_widget = LegacyMoveListController(self, self.moves_frame, self._on_move_selected)
        else:
            self.move_list_widget = PrettyMoveListController(self, self.moves_frame, self._on_pretty_move_selected)

        # English: Pack the new widget and refresh the content
        self.move_list_widget.widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.move_list_widget.update_view(self.game, self.move_list)
        self.move_list_widget.set_selection(self.current_move_index, self.game)
    def save_preferences_class(self):
        # 1. Collect data
        preferences_data = {
            "default_directory": self.default_pgn_dir,
            "last_pgn_filepath": self.last_filepath,
            "current_game_index": self.current_game_index,
            "engine": self.ENGINE_PATH,
            "square_size": self.square_size + 5,
            "piece_set": self.piece_set,
            "engine_depth": self.engine_depth,
            "board": self.theme_name
            # More items can be added here later, such as last used engine, etc.
        }

        # 2. Save
        save_preferences(preferences_data)

    def swap_colours_func(self):
        self.swap_colours = not self.swap_colours
        self.update_board_display()

    # --- Game Chooser Logic ---

    def _open_game_chooser(self):
        """
        Opens the Game Chooser dialog, which handles game selection and switching.
        """
        if not hasattr(self, 'all_games') or not self.all_games:
            messagebox.showinfo("Information", "No PGN games are currently loaded.", parent=self.master)
            return

        GameChooserDialog(
            master=self.master,
            all_games=self.all_games,
            current_game_index=self.current_game_index,
            # pass the method that will be executed after selection
            switch_callback=self._switch_to_game
        )

    # --- Game Navigation Logic ---

    def go_game(self, direction):
        """
        Goes to the previous or next game in the list.
        direction: -1 for previous, 1 for next.
        """
        if not self.all_games:
            return

        new_index = self.current_game_index + direction

        if 0 <= new_index < len(self.all_games):
            self._switch_to_game(new_index)
        else:
            messagebox.showinfo("Navigation", "This is the beginning or end of the PGN collection.", parent=self.master)

    def _switch_to_game(self, index):
        """
        Sets the current game, rebuilds the move list, and resets the UI.
        """
        if 0 <= index < len(self.all_games):
            self.store_meta_data()
            self.current_game_index = index
            self.game = self.all_games[index]

            self.init_move_list()

            self._update_meta_entries()
            self.analyze_eval_changes()
            self._populate_move_listbox()
            self.show_clear_variation_button()
            self.update_state()

    def init_move_list(self):
        # Reset moves and position
        self.move_list = []
        node = self.game
        while node.variations:
            # Always follow the main (first) variation
            node = node.variation(0)
            self.move_list.append(node)

        self.current_move_index = -1
        self.board = self.game.board()

    def store_meta_data(self):
        if not self.game is None:
            for tag, entry in self.meta_entries.items():
                try:
                    self.game.headers[tag] = entry.get()
                except:
                    pass

    def _update_game_navigation_state(self):
        """
        Updates the status of the buttons in the 'Game' menu and the game numbers.
        """
        total_games = len(self.all_games)

        # Update Game number label
        game_text = f"Game # {self.current_game_index + 1} of {total_games}" if total_games > 0 else "No Game Loaded"
        self.game_index_label.config(text=game_text)

        # Update Menu buttons using entryconfig
        prev_state = tk.NORMAL if self.current_game_index > 0 else tk.DISABLED
        next_state = tk.NORMAL if self.current_game_index < total_games - 1 else tk.DISABLED

        # Index 0 is "Previous Game", Index 1 is "Next Game"
        if self.game_menu:
            self.game_menu.entryconfig(0, state=prev_state)
            self.game_menu.entryconfig(1, state=next_state)

    def show_settings_dialog(self):

        current_settings = {
            "default_directory": self.default_pgn_dir,
            "lastLoadedPgnPath": self.last_filepath,
            "engine_path": self.ENGINE_PATH,
            "piece_set": self.piece_set,
            "engine_depth": self.engine_depth,
            "square_size": self.square_size,
            "board": self.theme_name
        }


        SettingsDialog(self.master, current_settings, self._save_config_wrapper)

    def _save_config_wrapper(self, *args):
        # Update the internal attributes after saving
        self.default_pgn_dir = args[0]
        self.ENGINE_PATH = args[2]
        new_piece_set = args[3]
        piece_set_changed = (new_piece_set != self.piece_set)
        self.piece_set = args[3]
        # Check if square_size has changed to trigger a resize
        new_square_size = int(args[4])
        size_changed = (new_square_size != self.square_size)
        self.square_size = new_square_size
        self.theme_name = args[5]
        self.set_theme()
        self.engine_depth = int(args[6])
        self.save_preferences_class()
        if piece_set_changed:
            self.force_restart()
        # 2. Update Board and Comments Width if size changed
        if size_changed:
            self._resize_board_and_comments()
            self.update_board_display()
        self.update_state()

    def _resize_board_and_comments(self):
            """
            Recalculates and applies the new width to the board and comments frame.
            """
            new_width = 8 * self.square_size

            # Update the board canvas size
            # Assuming your canvas is self.current_board_canvas
            self.board_frame.config(width=new_width, height=new_width)
            self.canvas.config(width=new_width, height=new_width)
            self.content_paned.paneconfigure(self.column1_frame, width=new_width+60)

            # Update the comment frame width
            # We use .config(width=...) because pack_propagate(False) is active
            if hasattr(self, 'comment_display_frame'):
                self.comment_display_frame.config(width=new_width)
                self.comment_display.config(
                    justify="left",  # Align text to the left
                    anchor="nw",  # Position text in the Top-West (top-left) corner
                    wraplength=400  # Initial wrap length in pixels
                )
                # Bind a function to resize the wrap length automatically
                self.comment_display.bind('<Configure>', self.update_wraplength)

                # If you have a label inside for comments, update its wraplength too
                if hasattr(self, 'comment_label'):
                    self.comment_label.config(wraplength=new_width - 10)

    def update_wraplength(self, event):
        """
        Dynamically updates the text wrapping width based on the widget's current size.
        """
        # Subtract a small margin (e.g., 20px) to prevent text from touching the edges
        new_width = event.width - 20
        if new_width > 0:
            self.comment_display.config(wraplength=new_width)

    def display_game_externally(self, file_path, game_index):
        self.current_game_index = game_index
        with open(file_path, 'r', encoding='utf-8') as f:
            pgn_content = f.read()
            self._load_game_from_content(pgn_content)

    def force_restart(self):
        """
        Closes the current application and starts a fresh instance.
        """
        # 1. Ask for confirmation (Optional but recommended)
        if not messagebox.askyesno("Restart", "Piece-set has changed. Are you sure you want to restart?", parent=self.master):
            return

        # 2. Close the Tkinter window properly
        self.master.destroy()

        # 3. Get the path to the current Python executable and the script
        python = sys.executable
        os.execl(python, python, *sys.argv)

    # --- File & Load Logic ---

    def _get_surname(self, name):
        """
        Extracts the first part of a name (surname).
        Handles 'Roebers, Eline' -> 'Roebers' and 'Gukesh D' -> 'Gukesh'.
        """
        if not name or name in ["?", ""]:
            return ""
        # Replace comma with space to treat them equally, then split
        parts = name.replace(",", " ").split()
        return parts[0].strip().lower() if parts else ""

    def merge_pgn_file(self):
        """
        Merges games from an external PGN file into the current list, 
        matching by players and date, then merging comments for duplicates.
        """
        if not hasattr(self, 'all_games'):
            self.all_games = []

        initial_dir = os.path.dirname(self.last_filepath) if hasattr(self, 'last_filepath') else os.getcwd()

        # Present a dialog to choose the png-file
        file_to_merge = filedialog.askopenfilename(
            title="Load pgn",
            initialdir=initial_dir,
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")]
        )

        if not file_to_merge:
            return

        # Ask whether to merge comments for duplicates
        # Using a simple Yes/No dialog
        do_merge_comments = messagebox.askyesno(
            "Merge Comments",
            "Do you want to merge comments for duplicate games?"
        )

        duplicates_count = 0
        new_games_count = 0

        try:
            with open(file_to_merge, 'r', encoding='utf-8', errors='replace') as f:
                while True:
                    new_game = chess.pgn.read_game(f)
                    if new_game is None:
                        break

                    # Extract keys for comparison
                    w_new = self._get_surname(new_game.headers.get("White", ""))
                    b_new = self._get_surname(new_game.headers.get("Black", ""))
                    d_new = new_game.headers.get("Date", "").strip()

                    # Identify a match using normalized surnames
                    match = next((g for g in self.all_games if
                                  self._get_surname(g.headers.get("White", "")) == w_new and
                                  self._get_surname(g.headers.get("Black", "")) == b_new and
                                  g.headers.get("Date", "").strip() == d_new), None)

                    if match:
                        # If duplicate, copy comments from the new game to the existing one
                        if do_merge_comments:
                            self._merge_game_comments(match, new_game)
                        duplicates_count += 1
                    else:
                        # New game: add to the list
                        self.all_games.append(new_game)
                        new_games_count += 1
                    self.is_dirty = True

            messagebox.showinfo("Done",
                                f"Merge complete!\nAdded: {new_games_count}\nMerged comments for: {duplicates_count} duplicates.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to merge PGN: {e}")

    def _merge_game_comments(self, existing_game, new_game):
        """
        Recursive helper to merge only descriptive text from comments,
        filtering out numerical engine evaluations.
        """

        def clean_comment(comment):
            """
            Removes engine scores like '0.35', '+0.17', '(-0.12)' 
            and double spaces.
            """
            if not comment:
                return ""

            # Regex to find numbers, signs, and scores in parentheses
            # Matches: 0.35, +1.2, -0.5, (+0.17), (2.19)
            score_pattern = r"\(?[+-]?\d+[\.,]\d+\s?(\([+-]?\d+[\.,]\d+\))?\)?"

            # Replace the found patterns with an empty string
            cleaned = re.sub(score_pattern, "", comment)

            # Clean up multiple spaces and leading/trailing whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            return cleaned

        def sync_nodes(node_existing, node_new):
            # Clean the new comment first
            new_raw_comment = clean_comment(node_new.comment)

            # Only merge if there is actual text left after cleaning
            if new_raw_comment and new_raw_comment not in node_existing.comment:
                if node_existing.comment:
                    # Check if the text isn't already present in a different form
                    if new_raw_comment not in node_existing.comment:
                        node_existing.comment += " | " + new_raw_comment
                else:
                    node_existing.comment = new_raw_comment

            # Continue recursion for variations and mainline
            for next_node_new in node_new.variations:
                move = next_node_new.move

                # Check if the existing game also has this move
                if node_existing.has_variation(move):
                    sync_nodes(node_existing.variation(move), next_node_new)

        # Start the process from the beginning of the game
        sync_nodes(existing_game, new_game)

    def sort_pgn_file(self, property):
        """
        Sorts self.all_games based on the provided property.
        Handles compound sorting for 'site' and 'event'.
        """
        if not hasattr(self, 'all_games') or not self.all_games:
            return

        # Helper to get header value safely
        def get_h(game, tag):
            return game.headers.get(tag, "").strip().lower()

        if property == "date":
            # Simple date sort (PGN date format YYYY.MM.DD sorts well as string)
            self.all_games.sort(key=lambda g: get_h(g, "Date"))

        elif property == "white":
            self.all_games.sort(key=lambda g: get_h(g, "White"))

        elif property == "black":
            self.all_games.sort(key=lambda g: get_h(g, "Black"))

        elif property == "site":
            # Sort by Site, then by Date
            self.all_games.sort(key=lambda g: (get_h(g, "Site"), get_h(g, "Date")))

        elif property == "event":
            # Sort by Event, then by Date
            self.all_games.sort(key=lambda g: (get_h(g, "Event"), get_h(g, "Date")))

        # Mark the database as modified
        self.is_dirty = True

        # Optional: Refresh the UI if a list is visible
        if hasattr(self, 'update_ui_after_sort'):
            self.update_ui_after_sort()

    def manage_pgn_file(self):
        """
        Opens a window to manage the games in self.all_games with checkboxes
        to remove, keep (leave), or invert selections.
        """
        if not hasattr(self, 'all_games') or not self.all_games:
            messagebox.showwarning("Warning", "No games in database to manage.")
            return

        # Use board theme colors for consistency
        bg_color =  self.selected_theme["light"]
        header_color = self.selected_theme["dark"]
        text_on_dark = "#ffffff"

        manage_win = tk.Toplevel(self.master)
        manage_win.title("Manage PGN Database")
        manage_win.geometry("600x700")
        manage_win.configure(bg=bg_color)
        manage_win.grab_set()  # Make window modal

        # Header
        tk.Label(manage_win, text=f"Total Games: {len(self.all_games)}",
                 font=("Segoe UI", 12, "bold"), bg=header_color, fg=text_on_dark, pady=10).pack(fill=tk.X)

        # --- Scrollable List Container ---
        container = tk.Frame(manage_win, bg="white", relief=tk.SOLID, borderwidth=1)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        canvas = tk.Canvas(container, bg="white", highlightthickness=0)
        # Using the thick scrollbar style defined earlier
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview, style="Thick.Vertical.TScrollbar")
        scrollable_frame = tk.Frame(canvas, bg="white")

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_win = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_win, width=e.width))

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Track checkbox states
        # Using a list of BooleanVars to link with checkboxes
        check_vars = []

        for i, game in enumerate(self.all_games):
            var = tk.BooleanVar(value=False)
            check_vars.append(var)

            row = tk.Frame(scrollable_frame, bg="white")
            row.pack(fill=tk.X, pady=2, padx=5)

            # Extract headers for display
            w = game.headers.get("White", "Unknown")
            b = game.headers.get("Black", "Unknown")
            res = game.headers.get("Result", "*")

            lbl_text = f"{i + 1:03d}. {w} - {b} ({res})"

            # Checkbox at the end of the row
            tk.Label(row, text=lbl_text, bg="white", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)
            tk.Checkbutton(row, variable=var, bg="white", activebackground="white").pack(side=tk.RIGHT, padx=10)

        # --- Button Actions ---
        def get_selected_indices():
            return [i for i, var in enumerate(check_vars) if var.get()]

        def do_remove():
            indices = get_selected_indices()
            if not indices: return
            if messagebox.askyesno("Confirm", f"Remove {len(indices)} selected games?"):
                # Delete from end to start to avoid index shifts
                for i in sorted(indices, reverse=True):
                    self.all_games.pop(i)
                manage_win.destroy()
                self._update_after_manage()
                self.is_dirty = True

        def do_leave():
            indices = get_selected_indices()
            if not indices: return
            if messagebox.askyesno("Confirm", f"Keep only {len(indices)} selected games and remove others?"):
                # Rebuild list with only selected items
                self.all_games = [self.all_games[i] for i in indices]
                manage_win.destroy()
                self._update_after_manage()
                self.is_dirty = True

        def do_invert():
            for var in check_vars:
                var.set(not var.get())

        # --- Bottom Button Frame ---
        btn_frame = tk.Frame(manage_win, bg=bg_color)
        btn_frame.pack(fill=tk.X, pady=20, padx=20)

        # Styling buttons with board theme
        btn_style = {"bg": header_color, "fg": text_on_dark, "font": ("Segoe UI", 10, "bold"), "pady": 5}

        tk.Button(btn_frame, text="Invert", command=do_invert, **btn_style).pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                                 padx=5)
        tk.Button(btn_frame, text="Remove Selected", command=do_remove, **btn_style).pack(side=tk.LEFT, expand=True,
                                                                                          fill=tk.X, padx=5)

    def _update_after_manage(self):
        """ Helper to refresh the main app state after modifying all_games. """
        # Hier kun je bijv. de stats herberekenen of de huidige puzzel verversen
        messagebox.showinfo("Success", "Database updated successfully.")
        if hasattr(self, 'update_stats'): self.update_stats()

    def split_pgn_file(self):
        # Basic check if a file was previously loaded
        if not hasattr(self, 'last_filepath') or not self.last_filepath:
            messagebox.showwarning("Warning", "No PGN file loaded to split.")
            return

        directory = os.path.dirname(self.last_filepath)
        base_name = os.path.splitext(os.path.basename(self.last_filepath))[0]

        # 1. Ask for the number of games per file
        # Defaulting to 20 as requested
        n = simpledialog.askinteger("Split PGN", "Number of games per file:",
                                    initialvalue=20, minvalue=1)
        if not n: return

        # 2. Ask for the zip filename
        zip_name = simpledialog.askstring("Zip Name", "Enter name for the zip file:",
                                          initialvalue=f"{base_name}_split.zip")
        if not zip_name: return
        if not zip_name.endswith('.zip'): zip_name += '.zip'

        zip_path = os.path.join(directory, zip_name)

        try:
            with open(self.last_filepath, 'r', encoding='utf-8') as pgn_file:
                # Prepare to write to zip
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                    game_count = 0
                    file_index = 1
                    current_batch = []

                    while True:
                        # Read game by game
                        game = chess.pgn.read_game(pgn_file)
                        if game is None:
                            # Handle the last remaining batch
                            if current_batch:
                                self._write_batch_to_zip(zip_out, current_batch, file_index, base_name)
                            break

                        current_batch.append(str(game))
                        game_count += 1

                        # If batch is full, write it and reset
                        if len(current_batch) >= n:
                            self._write_batch_to_zip(zip_out, current_batch, file_index, base_name)
                            current_batch = []
                            file_index += 1

            messagebox.showinfo("Done", f"Successfully split into {file_index} files inside:\n{zip_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to split PGN: {e}")

    def _write_batch_to_zip(self, zip_obj, batch, index, base_name):
        """
        Helper to write a list of games into a single PGN file inside a zip.
        """
        file_in_zip = f"{base_name}_{index:03d}.pgn"
        # Combine games with double newlines (PGN standard)
        content = "\n\n".join(batch)
        zip_obj.writestr(file_in_zip, content)

    def load_pgn_file(self):
        """
        Opens a dialog to select a PGN file and loads all games from it.
        """
        initial_dir = None
        directory = None
        if hasattr(self, 'last_filepath') and self.last_filepath:
            # Extract the directory from the path
            directory = os.path.dirname(self.last_filepath)

        # Check if the directory is valid, and exists
        if os.path.isdir(directory):
            initial_dir = directory
        dialog = TouchFileDialog(self.master, initialdir=initial_dir)
        self.master.wait_window(dialog)
        if dialog.result:
            self.set_filepath(dialog.result)
            with open(self.last_filepath, 'r', encoding='utf-8') as f:
                pgn_content = f.read()
            self.current_game_index = 0
            self._load_game_from_content(pgn_content)

    def save_pgn_file(self):
        """
        Saves all games in self.all_games to a PGN file, preserving order.
        """
        # Check if the list exists and is not empty
        if not hasattr(self, 'all_games') or not self.all_games:
            messagebox.showwarning("Save Failed", "No games in the database to save.", parent=self.master)
            return
        # Extract directory and filename from last_filepath
        initial_dir = None
        initial_file = None

        if hasattr(self, 'last_filepath') and self.last_filepath:
            # Split the path into directory and file name
            initial_dir = os.path.dirname(self.last_filepath)
            initial_file = os.path.basename(self.last_filepath)
        # Ask the user where to save the file
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pgn",
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")],
            title="Save PGN Database",
            initialdir=initial_dir,  # Pre-select the last used folder
            initialfile=initial_file # Pre-fill the last used filename
        )

        if filepath:
            try:
                # Important: Ensure the current active game in the UI is updated
                # in the self.all_games list before saving, if you made changes.
                # 1. Update the game's headers with the modified meta-tags from the UI
                self.store_meta_data()

                with open(filepath, 'w', encoding='utf-8') as f:
                    # We use FileExporter for clean PGN formatting
                    for game in self.all_games:
                        # Export each game one by one
                        exporter = chess.pgn.FileExporter(f)
                        game.accept(exporter)
                        # Add extra newlines between games for readability
                        f.write("\n\n")
                    self.is_dirty = False
                self.set_filepath(filepath)

                messagebox.showinfo("Save Complete", f"Database successfully saved ({len(self.all_games)} games).", parent=self.master)

            except Exception as e:
                messagebox.showerror("Saving Error", f"Could not save the database: {e}", parent=self.master)
    def store_pgn_file(self, filepath):
        """
        Saves all games in self.all_games to a PGN file, preserving order.
        """
        # Check if the list exists and is not empty
        if not hasattr(self, 'all_games') or not self.all_games:
            messagebox.showwarning("Save Failed", "No games in the database to save.", parent=self.master)
            return

        try:
                # Important: Ensure the current active game in the UI is updated
                # in the self.all_games list before saving, if you made changes.
                # 1. Update the game's headers with the modified meta-tags from the UI
                self.store_meta_data()

                with open(filepath, 'w', encoding='utf-8') as f:
                    # We use FileExporter for clean PGN formatting
                    for game in self.all_games:
                        # Export each game one by one
                        exporter = chess.pgn.FileExporter(f)
                        game.accept(exporter)
                        # Add extra newlines between games for readability
                        f.write("\n\n")
                    self.is_dirty = False
                self.set_filepath(filepath)
                print("saved all to:", filepath)

        except Exception as e:
                messagebox.showerror("Saving Error", f"Could not save the database: {e}", parent=self.master)

    def _load_game_from_content(self, pgn_content):
        """
        Reads all games from the PGN content, stores them, and switches to the first game.
        """
        try:
            pgn = StringIO(pgn_content)
            self.all_games = []
            while True:
                game = chess.pgn.read_game(pgn)
                if game is None:
                    break
                self.all_games.append(game)

            if not self.all_games:
                messagebox.showerror("Error", "Could not read PGN. Invalid game or empty file.", parent=self.master)
                self.game = None
                self.current_game_index = -1
                self.move_list = []
                self.update_state() # Reset UI
                return
            if self.current_game_index >= len(self.all_games):
                self.current_game_index = len(self.all_games) - 1
            # Switch to the first game
            self._switch_to_game(self.current_game_index)

        except Exception as e:
            messagebox.showerror("Error", f"Error reading PGN: {e}", parent=self.master)


    # --- UI Component Setup ---

    def _setup_header_frame(self, master, meta_frame, nav_comment_frame, comment_frame, comment_display_frame):
        """
        Sets up the top section of the UI: Meta-tags, Navigation, and Commentary Controls.
        """
        # Label for Game Index
        self.game_index_label = tk.Label(meta_frame, text="No Game Loaded", font=('Arial', 9, 'bold'), fg='darkgreen')
        self.game_index_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

        tags = ["Event", "White", "Black", "Result"]
        for i, tag in enumerate(tags):
            tk.Label(meta_frame, text=f"{tag}:", font=('Arial', 9, 'bold')).grid(row=i+1, column=0, sticky="w")
            entry = tk.Entry(meta_frame, width=35)
            entry.grid(row=i+1, column=1, sticky="w", padx=5, pady=1)
            self.meta_entries[tag] = entry # Store the Entry widget


        # 2. Navigation and Current Move section (center in the header)


        # Current Move Notation
        tk.Label(nav_comment_frame, text="Current Move:", font=('Arial', 10, 'bold')).pack(pady=5)
        self.notation_label = tk.Label(nav_comment_frame, text="Starting Position", font=('Arial', 14, 'bold'),
                                       fg='blue')
        self.notation_label.pack(pady=5)

        # Navigation Buttons
        nav_buttons_frame = tk.Frame(nav_comment_frame)
        nav_buttons_frame.pack(pady=10)

        # Buttons with shorter text and smaller fixed width
        # 1. Previous Game
        self.prev_game_button = tk.Button(nav_buttons_frame, text="<<", command=lambda: self._navigate_game(-1),
                                          width=2, bg='#fff0e6')  # Width reduced
        self.prev_game_button.pack(side=tk.LEFT, padx=(5, 3))

        # 2a. First Move
        self.first_button = tk.Button(nav_buttons_frame, text="|<", command=self.go_first_move,
                                     width=2)  # Width reduced
        self.first_button.pack(side=tk.LEFT, padx=3)
        # 2. Previous Move
        self.prev_button = tk.Button(nav_buttons_frame, text="<", command=self.go_back_move,
                                     width=3)  # Width reduced
        self.prev_button.pack(side=tk.LEFT, padx=3)

        # 3. Next Move
        self.next_button = tk.Button(nav_buttons_frame, text=">", command=self.go_forward_move,
                                     width=3)  # Width reduced
        self.next_button.pack(side=tk.LEFT, padx=3)
        # 3b. Last Move
        self.last_button = tk.Button(nav_buttons_frame, text=">|", command=self.go_last_move,
                                     width=2)  # Width reduced
        self.last_button.pack(side=tk.LEFT, padx=3)

        # 4. Next Game
        self.next_game_button = tk.Button(nav_buttons_frame, text=">>", command=lambda: self._navigate_game(1),
                                          width=2, bg='#fff0e6')  # Width reduced
        self.next_game_button.pack(side=tk.LEFT, padx=(3, 5))


        # Make the wraplength dynamic and use fill=tk.X and sticky=tk.N
        # By removing wraplength or making it much larger and using fill=tk.X,
        # the label will fill the available width of the parent (nav_comment_frame).
        self.setup_comment_display(comment_display_frame)
        # Use fill=tk.X to make the label take the full width of nav_comment_frame
        self.comment_display.pack(fill=tk.X, padx=5, pady=(0, 10))
        self.variation_btn_frame = tk.Frame(nav_comment_frame, bg='white') # bg ter demo, kan weg
        self.variation_btn_frame.pack(fill=tk.X, padx=5, pady=(0, 10))
        # 3. Commentary Controls section (right in the header)

        # --- BUTTON FOR VARIATIONS ---
        self.manage_variations_button = tk.Button(comment_frame, text="Manage Variations", command=self._open_variation_manager, width=25, bg='#fff9c4')
        self.manage_variations_button.pack(pady=5)

        # Store button references directly for robust access
        self.insert_edit_comment_button = tk.Button(comment_frame, text="Insert/Edit Comment", command=self.manage_comment, width=25, bg='#d9e7ff')
        self.insert_edit_comment_button.pack(pady=5)

        self.delete_comment_button = tk.Button(comment_frame, text="Delete Comment", command=lambda: self.manage_comment(delete=True), width=25, bg='#ffd9d9')
        self.delete_comment_button.pack(pady=5)

    def setup_comment_display(self, comment_display_frame):
        # Configuration
        self.num_lines_limit = 6 if self.touch_screen else 3
        self.comment_display = tk.Label(comment_display_frame, text="", bg="white", relief="sunken")
        self.comment_display.pack(fill="both", expand=True)
        self.all_comment_chunks = []

        # # Create the manager and tell it how many "lines" (chunks) to show
        self.comment_manager = CommentManager(self.comment_display, lines_per_page=2 if self.touch_screen else 2)
        # self.num_lines_limit = 6 if self.touch_screen else 3


    def set_comment_text(self, text):
        """
        Wraps the input text into lines based on width and resets view to page 0.
        """
        self.comment_manager.set_comments(text)


    def _navigate_game(self, step):
        """
        Navigates to the previous (-1) or next (1) game in self.all_games.

        :param step: -1 for previous game, 1 for next game.
        """
        if not self.all_games:
            return

        new_index = self.current_game_index + step

        # Check if the new index is within bounds
        if 0 <= new_index < len(self.all_games):
            self._switch_to_game(new_index)
        else:
            # Optional: Inform the user that the end or beginning has been reached
            if step == -1:
                print("Already at the first game.")
            else:
                print("Already at the last game.")

        # Ensure buttons are correctly enabled/disabled after the jump
        self.update_state()

    def update_variation_buttons(self, game_node):
        """
        Updates the variation buttons below the commentary.
        :param game_node: The current game node (e.g., from python-chess).
        """
        # 1. Clear the frame completely (remove old buttons)
        for widget in self.variation_btn_frame.winfo_children():
            widget.destroy()

        # 2. Retrieve possible moves from this position
        # (Assuming python-chess structure, adapt if necessary)
        variations = game_node.variations

        # 3. Logic: Only show buttons if there is more than 1 continuation.
        # If there is only 1 move, it is simply the main line.
        if len(variations) > 1:

            # Add a small label (optional, for clarity)
            lbl = tk.Label(self.variation_btn_frame, text="Continuation:", font=('Arial', 8, 'italic'))
            lbl.pack(side=tk.LEFT, padx=(0, 5))

            for i, variation in enumerate(variations):
                # Get the move text (e.g., "e4" or "Nf3")
                # In python-chess, variation[0] is the move, use .san() for readability
                # The node is a GameNode, which serves as the root of the variation.
                # We need to wrap it in a temporary Game structure to use the standard PGN export.

                # Create a temporary game object starting from the move to get the PGN string
                temp_game = chess.pgn.Game()

                # FIX: Use the corrected function signature: add_variation(node)
                temp_game.add_variation(variation)

                # Get the PGN string for the variation (which starts with the next move number)
                #pgn_string = re.sub(r'\{[^}]*\}', '', str(temp_game)) # Remove curly brace comments for cleaner view

                # Clean up the string to remove headers and just show the moves
                # This is a crude way to get just the moves starting from the first move of the variation
                move_text = str(str(variation)[:10]).replace("...","").split(" ")[1]#pgn_string.split('\n')[-1].strip()
                #move_text = variation.move.san()
                #print("move-text", move_text)

                # Create the button
                btn = tk.Button(
                    self.variation_btn_frame,
                    text=move_text,
                    font=('Arial', 8),
                    bg='#e0f7fa', # Light blue color
                    # IMPORTANT: Use v=variation to capture the correct value in the lambda
                    command=lambda v=variation: self.follow_variation(i, v)
                )
                btn.pack(side=tk.LEFT, padx=2)

        # If there are 0 or 1 moves, the frame remains empty.

    def follow_variation(self, i, variation_node):
        """
        Called when a variation button is clicked.
        """
        if i == 0:
            self.go_forward_move()
            return
        self.select_variation(self._get_current_node(), self.current_move_index, variation_node)
        self.go_forward_move()
        # current_node = self._get_current_node()
        # previous_current_move_index = self.current_move_index

    def select_variation(self, current_node, previous_current_move_index, variation_node):
        self.stored_moves.append([current_node, current_node.variations[0], previous_current_move_index])
        current_node.promote_to_main(variation_node)
        self.init_move_list()

        self._populate_move_listbox()
        self.current_move_index = previous_current_move_index
        self.update_state()

    def _update_meta_entries(self):
        """
        Fills the metadata Entry widgets with values from the newly loaded game.
        """
        # If no game is loaded, clear the fields
        if not self.game:
            for tag, entry in self.meta_entries.items():
                entry.delete(0, tk.END)
            return

        for tag, entry in self.meta_entries.items():
            entry.delete(0, tk.END)
            value = self.game.headers.get(tag, "Unknown")
            entry.insert(0, value)

    def _setup_main_columns(self, master, board_frame, moves_frame):
        """
        Sets up the two columns below the header: Chess Diagram and Move List.
        """
        #tk.Label(board_frame, text="Chess Diagram", font=('Arial', 12, 'bold')).pack(pady=5)
        move_listbox_width = 50
        width = 8*(self.square_size - 5) + move_listbox_width
        self.canvas = tk.Canvas(board_frame, width=width, height=8*(self.square_size),bg='lightgray')
        self.canvas.pack(padx=5, pady=5)
        # Make the canvas responsive
        board_frame.bind('<Configure>', self._on_canvas_resize)



        # Header Frame for Label and Button
        moves_header_frame = tk.Frame(moves_frame)
        moves_header_frame.pack(fill=tk.X, pady=5)
        # ===============================================

        # OPTIONAl BUTTON: 'Clear variation'
        self.clear_variation_button = tk.Button(
            moves_header_frame,
            text="Clear ❌",
            fg="red", # Mkae the button red to make the status clear
            command=self.restore_variation
        )
        # by default the button is INVISIBLE
        self.clear_variation_button.pack_forget()

        # Store the reference to the Label
        self.move_list_label = tk.Label(
            moves_header_frame,
            text="Move List (Main Line)",
            font=('Arial', 12, 'bold')
        )
        self.move_list_label.pack(side=tk.LEFT, padx=(5, 0))

        # The callback 'self._on_move_selected' will be created in the next step
        # English: Decide which strategy to use once
        if self.move_list_type == "TouchMoveListColor":
            self.move_list_widget = LegacyMoveListController(self, moves_frame, self._on_move_selected)
        else:
            self.move_list_widget = PrettyMoveListController(self, moves_frame, self._on_pretty_move_selected)

        # English: The widget is accessible through the controller for layout
        self.move_list_widget.widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _on_move_selected(self, index):
        """ Callback for the TouchMoveListColor widget. """
        if self.current_move_index != index:
            self.current_move_index = index
            self.update_state()  # Updates your board and logic

    def _on_pretty_move_selected(self, node, type_label):
        """ Callback for the PrettyMoveListColor widget. """
        if type_label == "Regulier":
            # A chess ply is the count of half-moves.
            # If your index starts at 0 for move 1. e4, we subtract 1 from the ply.
            move_index = node.ply() - 1

            if self.current_move_index != move_index:
                self.current_move_index = move_index
                self.update_state()  # Board updates to this specific position
        elif type_label == "Variant":
            # Step 1 - Identify all nodes in the chain that need promotion
            promotion_path = []
            current = node
            # Climb up to the root, collecting nodes that are not
            # yet the primary variation (index 0).
            while current and current.parent:
                if current.parent.variations[0] != current:
                    # This node is a variation, it needs to be promoted
                    promotion_path.append(current)
                current = current.parent
            # Step 2 - Reverse the path!
            # We must promote the highest ancestor first so the history stack
            # (stored_moves) is built in the correct chronological order.
            promotion_path.reverse()
            # Step 3 - Execute the promotions using your existing logic
            for branch_node in promotion_path:
                parent = branch_node.parent
                try:
                    var_index = parent.variations.index(branch_node)
                    split_ply = parent.ply()
                    # Call your logic for each level of the nesting
                    self.select_variation(parent, split_ply, branch_node)
                except (ValueError, AttributeError):
                    continue
            # Step 4 - Finalize the state
            # Now the clicked node is guaranteed to be on the main line.
            self.current_move_index = node.ply() - 1
            # Refresh UI
            self.move_list_widget.update_view(self.game, self.move_list)
            return
            self.move_list_widget.load_pgn(self.game)
            self.update_state()
            self.move_list_widget.highlight_node(node)

    def show_clear_variation_button(self):
        """
        Manages the visibility of the 'Clear Variation'-button
        """
        if len(self.stored_moves) > 0:
            # Set the button VISIBLE
            self.clear_variation_button.pack(side=tk.LEFT, padx=5)
            # Change the text of the label
            self.move_list_label.config(text="Moves (Variation)")
        else:
            # Hide the button
            self.clear_variation_button.pack_forget()
            # Restore the label
            self.move_list_label.config(text="Moves (Main Line)")

    # --- State Update Logic ---

    def _populate_move_listbox(self):
        """
        Refactored to use the TouchMoveListColor widget.
        """
        self.move_list_widget.update_view(self.game, self.move_list)
        return
        if not self.move_list_type == "TouchMoveListColor":
            self.move_list_widget.load_pgn(self.game)
            return
        # Clear the existing list
        self.move_list_widget.delete(0, tk.END)

        if not self.game:
            return
        self.move_tags = []
        for i, node in enumerate(self.move_list):
            prev_board = node.parent.board()
            move_num = (i // 2) + 1

            # Build the string for the Regex to parse
            if prev_board.turn == chess.WHITE:
                prefix = f"{move_num}. "
            else:
                # Check if we need '...' for black's first move in a list
                if i == 0 or self.move_list[i - 1].parent.board().turn == chess.WHITE:
                    prefix = f"{move_num}... "
                else:
                    prefix = "    "  # Space for alignment

            san_move = prev_board.san(node.move)
            new_comment = node.comment.strip().replace('\n', ' ')

            new_comment = new_comment[:6]+new_comment[6:40].replace(" ","\u00A0")
            # Format comments for our Regex: {Comment}
            comment_text = f"{{{new_comment}}}" if node.comment and node.comment.strip() else ""

            # Variation indicators (can be colored as variations using parentheses)
            variation_text = f"({len(node.variations) - 1})" if len(node.variations) > 1 else ""

            full_line = f"{prefix}{san_move}{variation_text}{comment_text}"

            # Insert into the new widget - it handles the tags/colors!
            # Determine the tag based on whose turn it was
            current_tag = "" if prev_board.turn == chess.WHITE else "line_grey"
            if i in self.top_5_major_set:
                current_tag = "line_major"
            if i in self.top_5_minor_set:
                current_tag = "line_minor"
            # The widget's insert method now uses this tag to color the move
            self.move_tags.append(current_tag)
            self.move_list_widget.insert(tk.END, full_line, tag_override=current_tag)

    def update_move_listbox_selection(self):
        """
        Synchronizes the widget selection with the current move index.
        """
        self.move_list_widget.set_selection(self.current_move_index, self.game)
        return
        if self.move_list_type == "TouchMoveListColor":
            if 0 <= self.current_move_index < self.move_list_widget.size():
                self.move_list_widget.selection_set(self.current_move_index)
            else:
                self.move_list_widget.selection_clear()
        else:
            #get move self.current_move_index from self.game
            #pass this move to self.move_list_widget.highlight_node(node)
            # Start at the beginning of the game
            current_node = self.game

            # Traverse the main line until reaching the target index
            # Note: ply 1 is the first move, current_move_index is likely 0-based
            for _ in range(self.current_move_index + 1):
                next_node = current_node.next()
                if next_node is not None:
                    current_node = next_node
                else:
                    # Stop if the game is shorter than the index
                    break

            # Pass the found node to your new highlight method
            self.move_list_widget.highlight_node(current_node)


    def _get_board_at_index(self, index):
        """
        Calculates the board position after the move at the given index.
        Index -1 is the starting position.
        """
        if not self.game:
            return chess.Board()

        board = self.game.board() # Starting board (FEN or default)
        for i in range(index + 1):
            if i < len(self.move_list):
                try:
                    board.push(self.move_list[i].move)
                except:
                    pass
        return board

    def _get_current_node(self):
        """
        Returns the GameNode object of the current move.
        Returns the main game node if index is -1.
        """
        if self.current_move_index >= 0 and self.current_move_index < len(self.move_list):
            return self.move_list[self.current_move_index]
        elif self.current_move_index == -1 and self.game:
            # Return the root node (which is the game object itself)
            return self.game
        return None

    # --- Move Navigation ---

    def go_first_move(self):
        """ Go to the first move. """
        if len(self.move_list) > 0:
            self.current_move_index = -1
            self.move_list_widget.scroll_to_start()
            self.update_state()

    def go_forward_move(self):
        """ Go to the next move. """
        if self.current_move_index < len(self.move_list) - 1:
            self.current_move_index += 1
            self.update_state()

    def go_back_move(self):
        """ Go to the previous move. """
        if self.current_move_index > -1:
            self.current_move_index -= 1
            self.update_state()

    def go_last_move(self):
        """ Go to the last move. """
        if len(self.move_list) > 0:
            self.current_move_index = len(self.move_list) - 1
            self.update_state()

    # --- Update Functions ---

    def update_state(self):
        """
        Updates all UI components based on the current move index.
        """
        if not self.game:
            # If no game is loaded, ensure a clean start
            self.board = chess.Board()
            self.update_board_display()
            self.notation_label.config(text="No Game Loaded")
            self.set_comment_text("—")
            self.prev_button.config(state=tk.DISABLED)
            self.next_button.config(state=tk.DISABLED)
            if self.insert_edit_comment_button: self.insert_edit_comment_button.config(state=tk.DISABLED)
            if self.delete_comment_button: self.delete_comment_button.config(state=tk.DISABLED)
            if self.manage_variations_button: self.manage_variations_button.config(state=tk.DISABLED)
            self._update_game_navigation_state()
            self.show_clear_variation_button()
            return

        self.board = self._get_board_at_index(self.current_move_index)

        self.update_board_display()
        self.update_move_listbox_selection()
        self.update_move_notation()
        self.update_comment_display()
        self._update_game_navigation_state() # Update game navigation as well
        # Update Variations-Menu buttons using entryconfig
        prev_alternative_state = tk.NORMAL if len(self.stored_moves) > 0 else tk.DISABLED

        # Index 0 is "Previous Game", Index 1 is "Next Game"
        if self.variations_menu:
            self.variations_menu.entryconfig(0, state=prev_alternative_state)
            self.variations_menu.entryconfig(1, state=prev_alternative_state)


        # Update move navigation button states
        self.prev_button.config(state=tk.NORMAL if self.current_move_index > -1 else tk.DISABLED)
        self.first_button.config(state=tk.NORMAL if self.current_move_index > -1 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if self.current_move_index < len(self.move_list) - 1 else tk.DISABLED)
        self.last_button.config(state=tk.NORMAL if self.current_move_index < len(self.move_list) - 1 else tk.DISABLED)
        self.prev_game_button.config(state=tk.NORMAL if self.current_game_index > 0 and len(self.all_games) > 1 else tk.DISABLED)
        self.next_game_button.config(state=tk.NORMAL if self.current_game_index < len(self.all_games) - 1 and len(self.all_games) > 1 else tk.DISABLED)

        # Annotation buttons are active if a node is selected (current_move_index >= -1)
        annotation_state = tk.NORMAL if self.current_move_index >= -1 else tk.DISABLED

        if self.insert_edit_comment_button:
            self.insert_edit_comment_button.config(state=annotation_state)
        if self.delete_comment_button:
            self.delete_comment_button.config(state=annotation_state)
        if self.manage_variations_button:
            self.manage_variations_button.config(state=annotation_state)
        self.update_variation_buttons(self._get_current_node())
        self.show_clear_variation_button()


    def update_move_notation(self):
        """
        Updates the label with the notation of the current move.
        """
        node = self._get_current_node()
        if node and self.current_move_index != -1:
            # Use the notation of the move itself
            prev_board = node.parent.board()
            notation = prev_board.san(node.move)
            move_num = (self.current_move_index // 2) + 1

            if prev_board.turn == chess.WHITE: # White's move
                text = f"{move_num}. {notation}"
            else: # Black's move
                text = f"{move_num}... {notation}"
            self.notation_label.config(text=text)
        else:
            self.notation_label.config(text="Starting Position")

    def update_comment_display(self):
        """
        Updates the label with the commentary of the current move or starting position.
        """
        node = self._get_current_node()
        # The game root node can also have a comment
        comment = node.comment.strip() if node and node.comment and node.comment.strip() else "—"
        self.set_comment_text(comment)

    def update_listbox_item(self, index):
        """
        Updates a single item in the listbox after changing commentary or variations.
        """
        if index < 0 or index >= len(self.move_list):
            return

        node = self.move_list[index]
        prev_board = node.parent.board()

        # Generate the new text for the item
        move_num = (index // 2) + 1

        # Determine prefix
        if prev_board.turn == chess.WHITE:
            prefix = f"{move_num}. "
        else:
            prefix = f"{move_num}... " if index % 2 == 1 else "    "

        try:
            san_move = prev_board.san(node.move)
        except:
             san_move = node.move.uci()

        comment_text = f" ({node.comment.strip()})" if node.comment and node.comment.strip() else ""
        variation_indicator = f" [+ {len(node.variations)} V]" if len(node.variations) > 0 else ""

        new_list_item_text = f"{prefix}{san_move}{comment_text}{variation_indicator}"

        line_number = index + 1
        # remove the old line
        self.move_list_widget.delete(line_number)
        # Add the new text on the right position
        self.move_list_widget.insert(index, new_list_item_text, tag_override=self.move_tags[index])
        self._populate_move_listbox()
        self.update_state()


    # --- Commentary Logic ---

    def _open_commentary_editor(self, node, current_move_text):
        """
        Opens a custom Toplevel window with a multi-line Text widget.
        """
        dialog = tk.Toplevel(self.master)
        dialog.title(f"Edit Commentary for {current_move_text}")
        dialog.transient(self.master)
        dialog.grab_set() # Make the dialog modal

        current_comment = node.comment.strip() if node.comment else ""

        tk.Label(dialog, text=f"Commentary for {current_move_text}:", padx=10, pady=5).pack(anchor='w')

        text_frame = tk.Frame(dialog, padx=10, pady=5)
        text_frame.pack(fill='both', expand=True)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            height=10,
            width=50,
            font=('Arial', 10)
        )
        text_widget.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.config(command=text_widget.yview)

        text_widget.insert(tk.END, current_comment)

        button_frame = tk.Frame(dialog, pady=10)
        button_frame.pack()

        def save_comment():
            self.is_dirty = True
            new_comment = text_widget.get("1.0", tk.END).strip()
            node.comment = new_comment
            if self.current_move_index != -1: # Only update listbox item if it's not the root
                self.update_listbox_item(self.current_move_index)
                self._populate_move_listbox()
            self.update_comment_display()
            dialog.destroy()

        def cancel_edit():
            dialog.destroy()

        tk.Button(button_frame, text="Save", command=save_comment, width=15, bg='#d9ffc7').pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Cancel", command=cancel_edit, width=15, bg='#ffe0e0').pack(side=tk.LEFT, padx=10)

        # Center the dialog
        self.master.update_idletasks()
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        position_x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (dialog_width // 2)
        position_y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (dialog_height // 2)
        dialog.geometry(f'+{position_x}+{position_y}')

        self.master.wait_window(dialog)

    def handle_classify_opening_button(self):
        # 1. Initialize once in your app
        self.classifier = OpeningClassifier("eco.json")

        # 2. Use it whenever a game is loaded or a move is made
        opening_info = self.classifier.annotate_opening(self.game)

        if opening_info:
            self.update_state()
            self._populate_move_listbox()
            self.is_dirty = True
        else:
            #self.eco_label.config(text="ECO: ---")
            #self.opening_name_label.config(text="Unknown Opening")
            pass

    def handle_analyze_db_button(self):
        """
        Starts a sequential analysis of all games in the loaded database.
        """
        if not self.all_games:
            messagebox.showwarning("Analysis", "No games loaded in the database to analyze.")
            return

        # Ask for confirmation as this might take a while
        msg = f"Do you want to analyze all {len(self.all_games)} games? This may take some time."
        if not messagebox.askyesno("Analyze Database", msg):
            return

        sf_path = self.ENGINE_PATH
        self.classifier = OpeningClassifier("eco.json")

        # We use an index to track which game we are currently analyzing
        self.current_db_analysis_index = 0
        # Create the shared UI once
        analysis_ui = AnalysisProgressUI(self.master, title="Batch Analysis")
        # Prepare the dictionary for the AnalysisManager
        ui_bridge = {
            'window': analysis_ui.window,
            'db_label': analysis_ui.db_label,
            'status_label': analysis_ui.status_label,
            'progress_bar': analysis_ui.progress_bar
        }

        def analyze_next_game():
            """Helper function to analyze the next game in the list."""
            if self.current_db_analysis_index < len(self.all_games):
                # 1. Select the game
                current_game = self.all_games[self.current_db_analysis_index]
                # 2. Annotate opening (fast, so we do it on the main thread)
                self.classifier.annotate_opening(current_game)

                # Create a nice description for the popup
                white = current_game.headers.get("White", "Unknown")
                black = current_game.headers.get("Black", "Unknown")
                game_desc = f"Game {self.current_db_analysis_index + 1} of {len(self.all_games)}\n{white} vs {black}"

                self.analyzer = AnalysisManager(
                    root=self.master,
                    pgn_game=current_game,
                    stockfish_path=self.ENGINE_PATH,
                    on_finished_callback=go_to_next_game,
                    depth_limit=self.engine_depth,
                    db_info=game_desc  # Pass the game-info,
                    , check_previous=True,external_progress_ui = ui_bridge
                )
                self.analyzer.start()
                self.is_dirty = True
            else:
                # Everything is finished!
                analysis_ui.destroy()
                self.update_state()
                self._populate_move_listbox()
                messagebox.showinfo("Analysis Complete", "All games in the database have been analyzed.")

        def go_to_next_game():
            # Check if the user pressed 'Stop All' in the UI
            if self.current_db_analysis_index >= len(self.all_games) or analysis_ui.is_cancelled:
                analysis_ui.destroy()
                messagebox.showinfo("Finished", "Analysis process completed or stopped.")
                return
            """Callback that triggers the next game analysis."""
            self.current_db_analysis_index += 1
            # Use after(100) to give the UI a tiny bit of breathing room between games
            self.master.after(100, analyze_next_game)

        # Start the first game
        analyze_next_game()

    def _clear_variations_func(self):
        """
        Clears all side-variations from every move in the mainline,
        keeping only the primary moves played.
        """
        # 1. Ask for confirmation
        confirm = messagebox.askyesno(
            "Clear Variations",
            "Are you sure you want to remove all analysis variations? \n\nThis will only keep the main moves played in the game.",
            parent=self.master
        )

        if not confirm:
            return

        try:
            # 2. Start at the root of the game
            node = self.game

            # 3. Iterate through the mainline
            while not node.is_end():
                # The next move in the mainline is always the first variation (index 0)
                main_variation = node.variation(0)

                # We want to keep index 0, but delete all other indices
                # By setting node.variations to only contain the mainline, we drop the rest
                node.variations = [main_variation]

                # Move to the next move in the mainline
                node = main_variation

            # 4. Optional: Clear the root comment/header if desired
            # self.game.comment = ""

            # 5. Update UI
            self.is_dirty = True  # Mark as changed for saving
            self.update_state()
            self._populate_move_listbox()  # Ensure the move list/tree is refreshed

            messagebox.showinfo("Success", "All variations have been cleared.", parent=self.master)

        except Exception as e:
            messagebox.showerror("Error", f"Could not clear variations: {e}", parent=self.master)
    def handle_analyze_button(self):
        # Path to your Stockfish executable
        sf_path = self.ENGINE_PATH  # Or your Windows/Mac path

        # Define what should happen when it's done (e.g., refresh your move list)
        def refresh_ui():
            messagebox.showinfo("Analysis Complete", "Game analyzed successfully!", parent=self.master)
            self.update_state()
            self._populate_move_listbox()
            print("Analysis successfully integrated into the UI.")

        self.classifier = OpeningClassifier("eco.json")
        self.classifier.annotate_opening(self.game)

        # Create the manager and start
        self.analyzer = AnalysisManager(
            root=self.master,
            pgn_game=self.game,
            stockfish_path=sf_path,
            on_finished_callback=refresh_ui,
            depth_limit=self.engine_depth
        )
        self.analyzer.start()
        self.is_dirty = True

    def manage_comment(self, delete=False):
        """
        Manages the commentary for the currently selected move or starting position.
        """
        node = self._get_current_node()
        if not node:
            messagebox.showinfo("Information", "Please select a move or the starting position to manage commentary.", parent=self.master)
            return

        current_move_text = self.notation_label.cget('text')

        if delete:
            self.is_dirty = True
            node.comment = ""
            if self.current_move_index != -1: # Only update listbox item if it's not the root
                self.update_listbox_item(self.current_move_index)
                self._populate_move_listbox()
            self.update_comment_display()
            messagebox.showinfo("Commentary", f"Commentary deleted for {current_move_text}.", parent=self.master)
        else:
            # Open the custom multi-line editor
            self._open_commentary_editor(node, current_move_text)

     #--- Engine Helper Functions ---

    def _format_score(self, score: chess.engine.PovScore, turn: chess.Color) -> str:
        """
        Formats the chess.engine.PovScore object into a human-readable string.
        """
        if score.is_mate():
            mate_in = score.mate()
            if mate_in > 0:
                return f"M{mate_in}" # Mate in N
            elif mate_in < 0:
                return f"M{-mate_in}" # Mated in N
            else:
                return "M0"
        else:
            # If we have a normal centipawn score (no DTM), return it.
            return score.pov(turn)


    async def get_engine(self, enginepath, threads):
        engine_name = ""

        ###########################################################################
        # Initialize the engine
        ###########################################################################

        try:
            # CHANGE 2: Store the transport object globally (Note: `engine_transport` is unused in the return)
            engine_transport, engine = await chess.engine.popen_uci(enginepath)
            await engine.configure({
                "Threads": threads
            })
            # previous_enginepath = enginepath # This variable is not used in this scope
        except FileNotFoundError:
            errormsg = "Engine '{}' was not found. Aborting...".format(enginepath)
            print(errormsg)
            raise
        except PermissionError:
            errormsg = "Engine '{}' could not be executed. Aborting...".format(
                enginepath)
            print(errormsg)
            raise

        return engine

    async def _get_engine_suggestions(self, board: chess.Board, num_moves: int, depth: int) -> list | None:
        """
        Communicates with the Stockfish engine to get the top 'num_moves' variations.
        Returns a list of dictionaries with move info or None on error.
        """
        engine = None

        try:
            # Try to launch the engine
            engine = await self.get_engine( self.ENGINE_PATH, 8)

            # Set the engine hash table size (optional, but good practice)
            await engine.configure({"Hash": 16})

            # Analyze the position
            info = await engine.analyse(board, chess.engine.Limit(depth=depth), multipv=num_moves)

            suggestions = []
            for entry in info:
                # Ensure the entry has a Principal Variation (PV)
                if not entry.get("pv"):
                    continue

                score = entry.get("score")
                score_str = self._format_score(score, board.turn) if score else "N/A"

                # Get the principal variation (PV) as a list of moves
                pv: list[chess.Move] = entry.get("pv", [])

                # Convert the first move to SAN for easy reading
                first_move_san = board.san(pv[0])

                # Convert the rest of the PV to SAN string for display
                pv_board = board.copy()
                pv_notation = ""
                for i, move in enumerate(pv):
                    move_num = (board.fullmove_number * 2 - (0 if board.turn == chess.WHITE else 1) + i + 1) // 2

                    if pv_board.turn == chess.WHITE:
                        pv_notation += f" {move_num}. "
                    elif i == 0:
                        pv_notation += f" {move_num}... "

                    pv_notation += pv_board.san(move)
                    pv_board.push(move)

                suggestions.append({
                    'move_san': first_move_san,
                    'pv': pv,
                    'score_str': score_str,
                    'depth': depth,
                    'pv_notation': pv_notation.strip()
                })

            return suggestions

        except FileNotFoundError:
            messagebox.showerror("Engine Error", f"Stockfish engine not found at path: {self.ENGINE_PATH}. Please check the path and permissions.", parent=self.master)
            return None
        except Exception as e:
            messagebox.showerror("Engine Error", f"An error occurred while communicating with the engine: {e}", parent=self.master)
            return None
        finally:
            # IMPORTANT: Always close the engine process
            if engine:
                await engine.quit()

    # --- New Variation Logic ---

    def _open_engine_suggestion_dialog(self, _populate_variations):
        """
        The main function to request, display, and add an engine-suggested variation.
        """
        previous_current_move_index = self.current_move_index
        current_node = self._get_current_node()
        if not current_node:
            messagebox.showinfo("Information", "No game loaded.", parent=self.master)
            return

        current_board = current_node.board()

        if current_board.is_game_over():
            messagebox.showinfo("Information", "Game is over. Cannot add new variations.", parent=self.master)
            return

        # 1. Get suggestions from the engine (Blocking call)
        # Note: Tkinter UI will freeze during this time. For a large app, use threading.
        self.engine_status_label = tk.Label(self.master, text="Analyzing... Please wait...", fg="red")
        self.engine_status_label.pack(side=tk.BOTTOM, fill=tk.X)
        self.master.update()

        suggestions = asyncio.run(self._get_engine_suggestions(
            current_board,
            num_moves=self.ENGINE_MULTI_PV,
            depth=self.ENGINE_DEPTH
        ))
        #remove analyze-label
        self.engine_status_label.destroy()

        if not suggestions:
            # Error message is handled inside _get_engine_suggestions
            return

        # 2. Open a selection dialog
        dialog = tk.Toplevel(self.master)
        dialog.title("Engine Suggestions (Depth " + str(self.ENGINE_DEPTH) + ")")
        dialog.transient(self.master)
        dialog.grab_set()

        tk.Label(dialog, text=f"Top {len(suggestions)} suggested moves for {current_board.turn}:", font=('Arial', 10, 'bold')).pack(padx=10, pady=5)

        listbox_frame = tk.Frame(dialog, padx=10, pady=5)
        listbox_frame.pack(fill='both', expand=True)

        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Listbox to show suggestions
        suggestion_listbox = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            height=min(len(suggestions), 10),
            width=80,
            font=('Consolas', 10)
        )
        suggestion_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.config(command=suggestion_listbox.yview)

        # Populate Listbox
        for i, sug in enumerate(suggestions):
            # Format: [Rank] [SAN Move] (Score) | [Principal Variation]
            list_item = f"[{i+1}.] {sug['move_san']} ({sug['score_str']}) | {sug['pv_notation']}"
            suggestion_listbox.insert(tk.END, list_item)

        # 3. Handle selection
        def select_and_add():
            selection = suggestion_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a move to add as a variation.", parent=self.master)
                return

            selected_index = selection[0]
            selected_sug = suggestions[selected_index]

            # The new variation will start at the De nieuwe variatie zal beginnen bij de current_node
            previous_node = current_node
            new_variation_root = None # Dit wordt de eerste node van de variatie

            # Loop over de Principal Variation (PV) moves
            for i, move in enumerate(selected_sug['pv']):


                if i == 0:
                    # The first move is added to the current node
                    new_node = previous_node.add_variation(move)
                    new_variation_root = new_node
                    self.is_dirty = True

                    # Add comment to the first move of the variation
                    new_node.comment = (
                        f"Engine analysis ({selected_sug['score_str']} at depth {selected_sug['depth']}): {selected_sug['pv_notation']}"
                    )
                else:
                    # The next moves are added as an alternative of the previous node
                    new_node = previous_node.add_variation(move)

                # The new node becomes the previous for the next iteration
                previous_node = new_node


            if new_variation_root:

                messagebox.showinfo("Success", f"Variation starting with {selected_sug['move_san']} added successfully.", parent=self.master)
                # 5. Update UI
                self.current_move_index = previous_current_move_index
                if self.current_move_index != -1:
                    self.update_listbox_item(self.current_move_index)
                if _populate_variations:
                    _populate_variations()

                self.update_state()

            dialog.destroy()
        # Buttons
        button_frame = tk.Frame(dialog, pady=10)
        button_frame.pack()

        tk.Button(button_frame, text="Add Selected Variation", command=select_and_add, width=25, bg='#d9ffc7').pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=25, bg='#ffe0e0').pack(side=tk.LEFT, padx=10)

        # Center the dialog
        self.master.update_idletasks()
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        position_x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (dialog_width // 2)
        position_y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (dialog_height // 2)
        dialog.geometry(f'+{position_x}+{position_y}')

        self.master.wait_window(dialog)

    def update_meta_header(self):
        if self.last_filepath:
            # get the filename from the path
            filename = os.path.basename(self.last_filepath)
            try:
                self.meta_frame.config(text=f"Game Meta-Tags ({filename})")
            except:
                pass
        else:
            try:
                self.meta_frame.config(text="Game Meta-Tags (No file loaded)")
            except:
                pass

    # --- Variation Management Logic (NEW) ---

    def _open_variation_manager(self):
        """
        Opens a dialog to view, edit, add, and delete variations for the current node.
        """
        previous_current_move_index = self.current_move_index
        current_node = self._get_current_node()
        if not current_node:
            messagebox.showinfo("Information", "Please select a move or the starting position to manage variations.", parent=self.master)
            return

        dialog = tk.Toplevel(self.master)
        dialog.title(f"Manage Variations for: {self.notation_label.cget('text')}")
        dialog.transient(self.master)
        dialog.grab_set()

        tk.Label(dialog, text="Select a variation to activate/delete:", font=('Arial', 10, 'bold')).pack(padx=10, pady=5)

        listbox_frame = tk.Frame(dialog, padx=10, pady=5)
        listbox_frame.pack(fill='both', expand=True)

        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        variation_listbox = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            height=10,
            width=70,
            font=('Consolas', 10)
        )
        variation_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.config(command=variation_listbox.yview)

        # Populate the listbox with current variations
        def _populate_variations():
            variation_listbox.delete(0, tk.END)
            for i, variation_start_node in enumerate(self._get_current_node().variations):
                # The node is a GameNode, which serves as the root of the variation.
                # We need to wrap it in a temporary Game structure to use the standard PGN export.

                # Create a temporary game object starting from the move to get the PGN string
                temp_game = chess.pgn.Game()

                # FIX: Use the corrected function signature: add_variation(node)
                temp_game.add_variation(variation_start_node)

                # Get the PGN string for the variation (which starts with the next move number)
                #pgn_string = re.sub(r'\{[^}]*\}', '', str(temp_game)) # Remove curly brace comments for cleaner view

                # Clean up the string to remove headers and just show the moves
                # This is a crude way to get just the moves starting from the first move of the variation
                move_text = str(variation_start_node)#pgn_string.split('\n')[-1].strip()

                # The first move of the variation is always at index 0 of the variations list
                variation_listbox.insert(tk.END, f"[{i+1}] {move_text}")

        _populate_variations()

        # Button Functions
        #variation(move): Retrieves a child node by either the move or the variation index
        #remove_variation(move) to delete a variation
        #promote_to_main(move): Changes a given variation to become the main line of play.

        def _activate_selected_variation():
            selection = variation_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a variation to edit.", parent=self.master)
                return

            index = selection[0]
            variation_node = current_node.variations[index]
            self.select_variation(current_node, previous_current_move_index, variation_node)


        def _add_new_variation():
            """Opens dialog to add a new variation."""
            self._add_new_variation(_populate_variations)


        def _delete_selected_variation():
            selection = variation_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a variation to delete.", parent=self.master)
                return

            index = selection[0]

            # The chess.pgn.GameNode variation list is a standard list.
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete Variation {index+1}?", parent=dialog):
                self.is_dirty = True
                del current_node.variations[index]
                _populate_variations()
                if self.current_move_index != -1:
                    self.update_listbox_item(self.current_move_index) # Update indicator

        # Buttons
        button_frame = tk.Frame(dialog, pady=10)
        button_frame.pack()

        tk.Button(button_frame, text="Add New Variation", command=_add_new_variation, width=20, bg='#d9ffc7').pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Activate variation", command=_activate_selected_variation, width=20, bg='#fff9c4').pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Delete Selected", command=_delete_selected_variation, width=20, bg='#ffe0e0').pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Close", command=dialog.destroy, width=20).pack(side=tk.LEFT, padx=5)

        # Center the dialog
        self.master.update_idletasks()
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        position_x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (dialog_width // 2)
        position_y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (dialog_height // 2)
        dialog.geometry(f'+{position_x}+{position_y}')

        self.master.wait_window(dialog)

    def _add_new_variation(self,_populate_variations = None):
            """Opens dialog to add a new variation."""
            self._open_engine_suggestion_dialog(_populate_variations)


    def manual_move(self):
        self.is_manual = True
        messagebox.showinfo("Information", "Enter move on chess-board.", parent=self.master)
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

    def restore_variation(self):
        """
        Restores a stored variation and updates the board state instantly.
        """
        if len(self.stored_moves) == 0:
            messagebox.showinfo("Information", "No variations to restore.", parent=self.master)
            return

        # 1. Pop the stored state
        base_node, move_to_restore, index_move_to_restore = self.stored_moves.pop()

        # 2. Promote the variation in the PGN tree
        base_node.promote_to_main(move_to_restore)

        # 3. Rebuild the main move_list
        self.init_move_list()

        # 4. INSTANT BOARD UPDATE
        # Get the board object directly from the node at the target index
        if 0 <= index_move_to_restore < len(self.move_list):
            target_node = self.move_list[index_move_to_restore]
            # This replaces the while loop with go_forward_move()
            self.board = target_node.board()
            self.current_move_index = index_move_to_restore
        else:
            # If the index is out of bounds or at start, reset to game start
            self.board = self.game.board()
            self.current_move_index = -1

        # 5. SYNC GUI
        self._populate_move_listbox()

        # Redraw everything once
        self.update_state()

    def restore_all_variations(self):
        while len(self.stored_moves) > 0:
            self.restore_variation()
    # --- Board Drawing Logic ---

    def _on_canvas_resize(self, event):
        """
        Redraws the board when the window size changes.
        """
        self.update_board_display()

    def update_board_display(self):
        """
        Redraws the chess diagram using Unicode pieces.
        """
        if not self.board:
            return

        # Current size of the Canvas
        board_size = min(self.canvas.winfo_width(), self.canvas.winfo_height())
        if board_size < 100:
            board_size = 400

        self.canvas.delete("all")

        square_size = self.square_size#board_size / 8
        self.colors = (self.selected_theme["light"], self.selected_theme["dark"])
        #colors = ("#F0D9B5", "#B58863")  # Light and dark square colors

        # Unicode pieces (White: Uppercase, Black: Lowercase)
        piece_map = {
            'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
        }

        self.canvas.delete("all")

        # 1. Iterate through all chess squares (0 to 63)
        for square_index in chess.SQUARES:
            rank = chess.square_rank(square_index)
            file = chess.square_file(square_index)

            # Get GUI coordinates from helper
            x1, y1, x2, y2 = self._get_square_coords(rank, file)

            # Determine square color
            color_index = (rank + file) % 2
            fill_color = self.colors[1 - color_index]  # Ensuring consistent light/dark logic
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline="black", tags="square")

            # 2. Draw Algebraic Notation (Labels)
            self._draw_notation(x1, y1, x2, y2, rank, file, color_index)

            # 3. Draw the Piece (Image or Unicode fallback)
            self._draw_single_piece(square_index, x1, y1, x2, y2)

        # 4. Highlight the Last Move
        self._highlight_last_move()

        # Ensure correct layering
        self.canvas.tag_raise("highlight", "square")
        self.canvas.tag_raise("piece")
        self.canvas.tag_raise("notation")

    def _draw_notation(self, x1, y1, x2, y2, rank, file, color_index):
        """Draws rank and file characters on the edges of the board."""
        file_char = chr(ord('a') + file)
        rank_char = str(rank + 1)
        label_color = self.colors[color_index]  # Contrast color

        # Draw Rank (1-8) on the left-most visible squares
        if (not self.swap_colours and file == 0) or (self.swap_colours and file == 7):
            self.canvas.create_text(x1 + 3, y1 + 3, text=rank_char, anchor="nw",
                                    font=('Arial', 8), fill=label_color, tags="notation")

        # Draw File (a-h) on the bottom-most visible squares
        if (not self.swap_colours and rank == 0) or (self.swap_colours and rank == 7):
            self.canvas.create_text(x2 - 3, y2 - 3, text=file_char, anchor="se",
                                    font=('Arial', 8), fill=label_color, tags="notation")

    def _draw_single_piece(self, square_index, x1, y1, x2, y2):
        """Draws a piece using either a PNG image or a Unicode character fallback."""
        piece = self.board.piece_at(square_index)
        if not piece:
            return

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        symbol = piece.symbol()

        # Use PNG images if ImageManager is available
        if self.image_manager and symbol in self.image_manager.images:
            piece_img = self.image_manager.images.get(symbol)
            self.canvas.create_image(center_x, center_y, image=piece_img, tags="piece")

        # Fallback to Unicode characters
        else:
            piece_map = {'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
                         'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'}
            piece_char = piece_map.get(symbol, '?')

            # Adjust size for touch screens
            piece_size = int(self.square_size * 0.7)
            if hasattr(self, 'touch_screen') and self.touch_screen:
                piece_size = int(piece_size * 0.7)

            self.canvas.create_text(center_x, center_y, text=piece_char,
                                    font=('Arial', piece_size, 'bold'), fill='black', tags="piece")

    def _highlight_last_move(self):
        """Highlights the 'from' and 'to' squares of the current move."""
        if self.current_move_index < 0 or not self.move_list:
            return

        last_move = self.move_list[self.current_move_index].move
        for sq in [last_move.from_square, last_move.to_square]:
            r, f = chess.square_rank(sq), chess.square_file(sq)
            x1, y1, x2, y2 = self._get_square_coords(r, f)

            # Using a semi-transparent effect if supported, otherwise solid highlight
            self.canvas.create_rectangle(x1, y1, x2, y2, fill='#ffe066',
                                         outline="black", stipple='gray50', tags="highlight")

    def _setup_canvas_bindings(self):
        """Binds the left mouse click to the processing method."""
        # <Button-1> is the left mouse button
        self.canvas.bind("<Button-1>", self._handle_click)
        print("Canvas click handler is set up.")


    def _handle_click(self, event):
        """
        Handles a click event on the Canvas.
        Priority 1: Execute move.
        Priority 2: Select piece.
        Priority 3: Navigation (left/right half if no move was made).
        """
        click_x = event.x
        click_y = event.y

        # Determine the square clicked (in chess.Square format)
        col_index = int(click_x / self.square_size)
        row_index = int(click_y / self.square_size)

        # Convert GUI (top-down, 0-7) to chess.Square index (bottom-up)
        clicked_square = chess.square(col_index, 7 - row_index)

        piece_on_square = self.board.piece_at(clicked_square)

        # -----------------------------------------------------------
        # STEP 1: Check for move or deselect
        # -----------------------------------------------------------
        if self.is_manual and self.selected_square is not None:
            self.is_manual = False

            # A piece is already selected, so this is the destination square (to_square)
            from_square = self.selected_square
            to_square = clicked_square

            # Try to make the move (e.g., e2e4, d7d5, etc.)
            # Because we have a GUI, the most direct way to attempt the move is via UCI
            try:
                # Create a move object. For promotions (like a7a8q) we need a 'q'.
                # We assume a simple move here (no automatic promotion handling in this simple logic)
                move_uci = chess.square_name(from_square) + chess.square_name(to_square)

                # Check for promotion: if it is a pawn on the 7th rank moving to the 8th rank
                if self.board.piece_type_at(from_square) == chess.PAWN and chess.square_rank(to_square) in (0, 7) and chess.square_rank(from_square) != chess.square_rank(to_square):
                    # Add standard 'q' as promotion choice; you can expand this later with a prompt
                    move_uci += 'q'

                # Validate and execute the move
                move = chess.Move.from_uci(move_uci)

                if move in self.board.legal_moves:
                    print(f"Valid move: {move.uci()}. Executing...")
                    self._add_move_as_variation(move)
                    self.selected_square = None
                    self._clear_selection_highlight()
                    messagebox.showinfo("Information", f"Valid move: {move.uci()} added...", parent=self.master)

                    return # Handled, stop click processing

                else:
                    # Invalid move. Reset selection, but continue to see if the user wants to select a NEW piece
                    print("Invalid move. Selection reset.")
                    self.selected_square = None
                    self._clear_selection_highlight()

            except Exception as e:
                # This catches errors such as a faulty UCI string or other chess exceptions
                print(f"Error trying to make the move: {e}. Selection reset.")
                self.selected_square = None
                self._clear_selection_highlight()

        # -----------------------------------------------------------
        # STEP 2: New Selection
        # -----------------------------------------------------------
        # If the click contains a piece of the current player's color, select this piece.
        if self.is_manual and piece_on_square and piece_on_square.color == self.board.turn:

            # Select the new square
            self.selected_square = clicked_square
            print(f"Piece selected at: {chess.square_name(clicked_square)}")
            self._draw_selection_highlight(clicked_square)
            return # Handled, stop click processing

        # -----------------------------------------------------------
        # STEP 3: Navigation (only if no piece is selected and the move failed)
        # -----------------------------------------------------------

        # If we reach here, the click was not used to make a valid move
        # and either an empty square was clicked, or an invalid piece.

        board_width = 8 * self.square_size
        halfway_x = board_width / 2

        # If an empty square is clicked or a selection is canceled
        if not self.is_manual and (self.selected_square is None or (clicked_square == self.selected_square)):

            # Clear any remaining selection
            self.selected_square = None
            self._clear_selection_highlight()

            # The original navigation logic
            if click_x < halfway_x:
                side = "Left half of the board (Navigation: Back)"
                self.go_back_move()
            else:
                side = "Right half of the board (Navigation: Forward)"
                self.go_forward_move()

            # Display navigation info in the console (optional)
            file_char = chr(ord('a') + col_index)
            rank_char = str(8 - row_index)
            square_notation = f"{file_char}{rank_char}"
            # print(f"Navigation click on: {square_notation}. {side}")

    def _add_move_as_variation(self, move):
        self._get_current_node().add_variation(move)
        # 5. Update UI
        if self.current_move_index != -1:
            self.update_listbox_item(self.current_move_index)


    def _clear_selection_highlight(self):
        """Removes the active selection highlight from the Canvas."""
        if self.highlight_item:
            self.canvas.delete(self.highlight_item)
            self.highlight_item = None

    def _draw_selection_highlight(self, square):
        """Draws the highlight on the selected square."""
        self._clear_selection_highlight() # First remove the old highlight

        # Calculate the GUI coordinates of the square
        col = chess.square_file(square)
        row = 7 - chess.square_rank(square)
        x1 = col * self.square_size
        y1 = row * self.square_size
        x2 = x1 + self.square_size
        y2 = y1 + self.square_size

        # Draw the highlight
        self.highlight_item = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#22ff22", # Green border
            width=3,           # Thicker border
            tags="selection_highlight" # Tag for easy removal
        )
        # Ensure the highlight is below the pieces
        self.canvas.tag_lower(self.highlight_item, "piece")

    def analyze_eval_changes(self):
        """
        Creates and analyzes the evaluation array to find the 5 largest swings
        and 5 moderate changes in the game.
        """
        evaluations = []  # Separate array to store numerical evaluations

        node = self.game
        while node.variations:
            node = node.variation(0)

            # Extract evaluation from the comment
            eval_val = None
            if node.comment:
                # Regex to find the first decimal or integer (positive or negative)
                # Matches formats like "0.15", "+1.20", "-0.50", or "10"
                match = re.search(r"[-+]?\d*\.\d+|\d+", node.comment)
                if match:
                    try:
                        eval_val = float(match.group())
                    except ValueError:
                        eval_val = None

            # Append the found value or None if no evaluation exists for this move
            evaluations.append(eval_val)
        changes = []

        val_prev = None
        # Loop through evaluations starting from the second move
        for i in range(0, len(evaluations)):
            val_current = evaluations[i]

            # Only calculate if both moves have a valid numerical evaluation
            if val_current is not None:
                # The absolute difference represents the "impact" of the move
                if  val_prev is not None:
                    diff = abs(val_current - val_prev)
                    changes.append({
                        'index': i,
                        'diff': diff,
                        'move_num': (i // 2) + 1,
                        'color': "White" if i % 2 == 0 else "Black"
                    })
                val_prev = val_current

        if not changes:
            return None  # Return None if no evaluations were available

        # Sort the changes by the magnitude of the difference (highest first)
        sorted_changes = sorted(changes, key=lambda x: x['diff'], reverse=True)

        # Major changes: The top 5 absolute highest swings (likely blunders)
        top_5_major = sorted_changes[:5]
        self.top_5_major_set = {item['index'] for item in top_5_major}

        # Minor changes: A secondary group (e.g., positions 6 to 10)
        # representing significant but less catastrophic mistakes.
        top_5_minor = sorted_changes[5:10]
        self.top_5_minor_set = {item['index'] for item in top_5_minor}


def parse_args():
    """
    Define an argument parser and return the parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='annotator',
        description='store chess game in a PGN file '
        'based on user input')
    parser.add_argument("--pgn_game", "-p",
                        help="Set the name of the pgn game",
                        default="")
    #engine_name
    parser.add_argument("--engine_name", "-e",
                        help="Set the directory and name of the engine",
                        default="")

    parser.add_argument("--piece_set", "-s",
                        help="Set the piece-set for chess-pieces",
                        default=None)
    parser.add_argument("--board", "-o",
                        help="Set the color theme of the board",
                        default=None)
    parser.add_argument("--square_size", "-q",
                        help="Set the square-size for the board",
                        type=int,
                        default=None)
    return parser.parse_args()
# ----------------------------------------------------------------------
# 1. PIECE IMAGE MANAGER (THE FACTORY/SINGLETON)
# This class is responsible for loading all images once from the disk.
# ----------------------------------------------------------------------
class PieceImageManager1:
    """
    Manages loading and caching of chess piece images.
    Supports selecting a specific set (e.g., set '2' for bK2.svg).
    """

    def __init__(self, square_size, image_dir_path, set_identifier="staunty"):
        """
        :param set_identifier: The ID of the desired set ('1', '2', '3', etc.).
                                This is used to select the correct filename.
        """
        self.square_size = square_size
        self.image_dir_path = image_dir_path
        self.set_identifier = str(set_identifier) # Ensure it is a string
        self.images = {} # Dictionary to store ImageTk.PhotoImage objects

        # Base prefixes (wK = White King, bQ = Black Queen)
        self.piece_map = {
            'K': 'wK', 'Q': 'wQ', 'R': 'wR', 'B': 'wB', 'N': 'wN', 'P': 'wP',
            'k': 'bK', 'q': 'bQ', 'r': 'bR', 'b': 'bB', 'n': 'bN', 'p': 'bP',
        }

        self._load_images()

    def _load_images(self):
        """
        Loads and resizes images from the SELECTED SET.
        Searches first for an SVG, then a PNG, with the set-identifier attached.
        """
        # Clear old images to prevent Garbage Collector issues during reloading
        self.images = {}

        image_dir = BASE_DIR = Path(__file__).resolve().parent / self.image_dir_path
        print(f"Loading chess set '{self.set_identifier}' from: {image_dir}")

        for symbol, base_prefix in self.piece_map.items():

            # The dynamic prefix: e.g., 'wK2' or 'bN3'
            filename_prefix = f"{base_prefix}"

            # List of file formats to attempt, in order of preference
            # As seen in your directory: wK2.svg, wK3.svg, or wK1.png
            extensions = ['.svg', '.png']

            img = None
            image_path = None

            for ext in extensions:
                image_path = os.path.join(image_dir, self.set_identifier, f"{filename_prefix}{ext}")

                if os.path.exists(image_path):
                    try:
                        if ext == '.svg':
                            # SVGs require Cairosvg (requires installation)
                            #print(f"Loading SVG: {image_path}")
                            # Cairosvg logic needs to be added here.
                            # Because cairosvg is external, we keep generic PNG/fallback logic active.

                            # If cairosvg logic is implemented:
                            png_bytes = cairosvg.svg2png(url=image_path)
                            img = Image.open(BytesIO(png_bytes))

                            # Fallback: We omit extensive SVG loading logic from this example
                            # to minimize dependencies, unless explicitly requested.
                            # We proceed with attempting PNG.
                            # continue # Skip SVG load for simplicity if cairosvg not set up

                        elif ext == '.png':
                            # Load PNG (always works with Pillow)
                            img = Image.open(image_path)
                            break # File found, stop the loop

                    except Exception as e:
                        print(f"Error loading {image_path}: {e}")
                        img = None # On error, attempt next extension

            # Check if an image was successfully loaded
            if img:
                # 1. Resize image
                img = img.resize((self.square_size, self.square_size), Image.Resampling.LANCZOS)

                # 2. Convert to Tkinter format and store
                self.images[symbol] = ImageTk.PhotoImage(img)
            else:
                print(f"Warning: No image found for set {self.set_identifier} and piece {symbol}. Leaving blank.")

        if self.images:
            print(f"Chess set '{self.set_identifier}' loaded successfully.")
        else:
            print(f"Error: No chess pieces loaded. Verify if files exist: *K{self.set_identifier}.(png/svg)")

# Main execution block
if __name__ == "__main__":
    args = parse_args()
    preferences = load_preferences()

    last_pgn_file = preferences.get("last_pgn_filepath", "")
    current_game_index = preferences.get("current_game_index", "")
    engine_name_preferences = preferences.get("engine", "")
    square_size = preferences.get("square_size", 80)
    piece_set1 = preferences.get("piece_set", "staunty")
    engine_depth = preferences.get("engine_depth", 17)
    board1 = preferences.get("board", "red")

    pgn_game = args.pgn_game if args.pgn_game else last_pgn_file
    engine_name = args.engine_name if args.engine_name else engine_name_preferences
    piece_set = args.piece_set if args.piece_set else piece_set1
    board = args.board if args.board else board1
    IMAGE_DIRECTORY = "Images/piece"
    SQUARE_SIZE = args.square_size if args.square_size else square_size # Size of the squares in pixels
    # 2. Initialize the Asset Manager (LOADS IMAGES ONCE)
    # If this fails (e.g., FileNotFoundError), the program stops here.
    root = tk.Tk()
    asset_manager = PieceImageManager1(SQUARE_SIZE, IMAGE_DIRECTORY, piece_set)
    app = ChessAnnotatorApp(root, pgn_game, engine_name, image_manager = asset_manager, square_size = SQUARE_SIZE-5, current_game_index = current_game_index, piece_set = piece_set, board=board, engine_depth=engine_depth)

    root.mainloop()
#example call
##python3 pgn_editor.py --pgn_game "/home/user/Schaken/2025-12-11-Anton-Gerrit-annotated.pgn" --engine_name "/home/user/Schaken/stockfish-python/Python-Easy-Chess-GUI/Engines/stockfish-ubuntu-x86-64-avx2"
