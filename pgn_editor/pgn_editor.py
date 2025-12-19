import json
import tkinter as tk
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
import textwrap

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
            self.board_var.get()  # Sends the selected name (e.g., "Red")
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
            messagebox.showwarning("Selection Error", "Please select a game from the list.")
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

class ChessAnnotatorApp:
    def __init__(self, master, pgn_game, engine_name, hide_file_load = False, image_manager = None, square_size = 75, current_game_index = -1, piece_set = "", board="Standard", swap_colours = False):
        print("parameters:",pgn_game, engine_name, hide_file_load, image_manager, square_size, current_game_index, piece_set, board)
        self.last_filepath = pgn_game
        self.theme_name=board
        self.master = master
        self.piece_set = piece_set
        self.square_size = square_size if square_size else 75
        self.image_manager = image_manager
        self.default_pgn_dir = ""
        self.hide_file_load = hide_file_load
        self.is_manual = False
        self.selected_square = None
        self.highlight_item = None
        self.swap_colours = swap_colours
        master.title("PGN Chess Annotator")
        # Find the theme
        self.selected_theme = next(
            (theme for theme in BOARD_THEMES if theme["name"] == self.theme_name),
            BOARD_THEMES[0] # Use Standard as fallback
        )

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
        self.ENGINE_DEPTH = 18

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
        self.setup_ui( master)

        self._setup_header_frame(master, self.meta_frame, self.nav_comment_frame, self.comment_frame, self.comment_display_frame)

        self._setup_main_columns(master,self.board_frame,self.moves_frame)

        master.update_idletasks()

        self.set_screen_position(master)

        if not(pgn_game is None or len(pgn_game) == 0):
            try:
                with open(pgn_game, 'r', encoding='utf-8') as f:
                    pgn_content = f.read()
                self._load_game_from_content(pgn_content)
            except Exception as e:
                messagebox.showerror("Loading Error", f"Could not read the file: {e}")
        else:
            # Initialize UI status with the sample game
            self._load_game_from_content(self.sample_pgn)
        self._setup_canvas_bindings()

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


        if is_compact_layout:
            self.touch_screen = True

            # --- 2. Create Frames ---
            # These must always be created before we place or fill them.
            self._setup_menu_bar(master)

            # Main containers
            main_frame = tk.Frame(master, padx=10, pady=10)
            main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

            # Column 1 (Left): Chess Diagram
            column1_frame = tk.Frame(main_frame)
            column1_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

            # Column 2: Move List
            column2_frame = tk.Frame(main_frame, width=400)
            column2_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
            column2_frame.pack_propagate(False)

            # Column 3: Tools/Meta
            column3_frame = tk.Frame(main_frame)
            column3_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

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
            comment_display_frame = tk.Frame(column1_frame)
            comment_display_frame.pack(side=tk.TOP, padx=5, fill=tk.X)
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
            file_menu.add_separator()
        file_menu.add_command(label="Exit", command=master.destroy)

        # Game Menu
        game_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Game", menu=game_menu)
        game_menu.add_command(label="Previous Game", command=lambda: self.go_game(-1), state=tk.DISABLED, accelerator="Ctrl+Left")
        game_menu.add_command(label="Next Game", command=lambda: self.go_game(1), state=tk.DISABLED, accelerator="Ctrl+Right")
        game_menu.add_command(label="Choose Game...", command=self._open_game_chooser)
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
        Called via root.protocol("WM_DELETE_WINDOW", ...).
        """
        self.save_preferences_class()

        # 3. Close the app
        self.master.destroy()

    def save_preferences_class(self):
        # 1. Collect data
        preferences_data = {
            "default_directory": self.default_pgn_dir,
            "last_pgn_filepath": self.last_filepath,
            "current_game_index": self.current_game_index,
            "engine": self.ENGINE_PATH,
            "square_size": self.square_size + 5,
            "piece_set": self.piece_set,
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
            messagebox.showinfo("Information", "No PGN games are currently loaded.")
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
            messagebox.showinfo("Navigation", "This is the beginning or end of the PGN collection.")

    def _switch_to_game(self, index):
        """
        Sets the current game, rebuilds the move list, and resets the UI.
        """
        if 0 <= index < len(self.all_games):
            self.current_game_index = index
            self.game = self.all_games[index]

            # Reset moves and position
            self.move_list = []
            node = self.game
            while node.variations:
                # Always follow the main (first) variation
                node = node.variation(0)
                self.move_list.append(node)

            self.current_move_index = -1
            self.board = self.game.board()

            self._update_meta_entries()
            self._populate_move_listbox()
            self.show_clear_variation_button()
            self.update_state()

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
            "square_size": self.square_size,
            "board": self.theme_name
        }


        SettingsDialog(self.master, current_settings, self._save_config_wrapper)

    def _save_config_wrapper(self, *args):
        self.save_preferences_class()
        # Update the internal attributes after saving
        self.default_pgn_dir = args[0]
        self.ENGINE_PATH = args[2]
        self.piece_set = args[3]
        self.square_size = args[4]
        self.theme_name = args[5]
        self.update_state()

    # --- File & Load Logic ---

    def load_pgn_file(self):
        """
        Opens a dialog to select a PGN file and loads all games from it.
        """
        initial_dir = None
        if hasattr(self, 'last_filepath') and self.last_filepath:
            # Extract the directory from the path
            directory = os.path.dirname(self.last_filepath)

        # 3. Controleer of de map geldig is en bestaat
        if os.path.isdir(directory):
            initial_dir = self.default_pgn_dir
        filepath = filedialog.askopenfilename(
            defaultextension=".pgn",
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")],
            title="Choose a PGN file to load",
            initialdir=initial_dir
        )
        if filepath:
            try:
                self.last_filepath = filepath
                with open(filepath, 'r', encoding='utf-8') as f:
                    pgn_content = f.read()
                self.current_game_index = 0
                self._load_game_from_content(pgn_content)
            except Exception as e:
                messagebox.showerror("Loading Error", f"Could not read the file: {e}")

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
                while len(self.stored_moves) > 0:
                    self.restore_variation()

                # 1. Update the game's headers with the modified meta-tags from the UI
                for tag, entry in self.meta_entries.items():
                    self.game.headers[tag] = entry.get()

                # 2. Convert the game object to PGN format (including all commentaries)
                pgn_output = str(self.game)

                # 3. Write to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(pgn_output)

                messagebox.showinfo("Save Complete", f"Game successfully saved to:\n{filepath}")

            except Exception as e:
                messagebox.showerror("Saving Error", f"Could not save the file: {e}")

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
                messagebox.showerror("Error", "Could not read PGN. Invalid game or empty file.")
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
            messagebox.showerror("Error", f"Error reading PGN: {e}")


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

        # 2. Previous Move
        self.prev_button = tk.Button(nav_buttons_frame, text="< Move", command=self.go_back_move,
                                     width=6)  # Width reduced
        self.prev_button.pack(side=tk.LEFT, padx=3)

        # 3. Next Move
        self.next_button = tk.Button(nav_buttons_frame, text="Move >", command=self.go_forward_move,
                                     width=6)  # Width reduced
        self.next_button.pack(side=tk.LEFT, padx=3)

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
        self.all_comment_chunks = []
        self.current_page = 0

        self.comment_display = tk.Label(
            comment_display_frame,
            text="No comment for this move.",
            font=('Arial', 9),
            bg='lightgray',
            relief=tk.SUNKEN,
            # Set height to limit + 2 to ensure space for the indicator and a gap
            height=self.num_lines_limit + 2,
            wraplength=450,
            justify=tk.LEFT,
            anchor=tk.NW,
            cursor="hand2"
        )
        self.comment_display.grid(row=0, column=0, sticky='ew', padx=5, pady=(0, 10))

        # Bind the click event for paging
        self.comment_display.bind("<Button-1>", self._toggle_comment_page)

    def set_comment_text(self, text):
        """
        Wraps the input text into lines based on width and resets view to page 0.
        """
        if not text or text.strip() == "":
            text = "No comment for this move."

        # Use textwrap to break the string into a list of lines fitting the widget width
        # Adjust 'width' (character count) if the wraplength changes
        wrapper = textwrap.TextWrapper(width=65)
        self.all_comment_chunks = wrapper.wrap(text)

        self.current_page = 0
        self._update_label_view()

    def _update_label_view(self):
        """
        Updates the label text to show the current page's lines and a visibility indicator.
        """
        if not self.all_comment_chunks:
            self.comment_display.config(text="No comment for this move.")
            return

        # Calculate start and end indices for the current page
        start = self.current_page * self.num_lines_limit
        end = start + self.num_lines_limit

        current_lines = self.all_comment_chunks[start:end]

        # Padding: Fill empty lines if the page is not full.
        # This keeps the "[ CLICK FOR MORE ]" indicator at a fixed vertical position.
        while len(current_lines) < self.num_lines_limit:
            current_lines.append("")

        display_text = "\n".join(current_lines)

        # Append the paging indicator at the bottom
        if end < len(self.all_comment_chunks):
            display_text += "\n\n[ CLICK FOR MORE... ]"
        elif self.current_page > 0:
            display_text += "\n\n[ CLICK: BACK TO START ]"
        else:
            # Add empty space for short comments to maintain consistent layout height
            display_text += "\n\n"

        self.comment_display.config(text=display_text)

    def _toggle_comment_page(self, event):
        """
        Cycles to the next page of comments. Safe against infinite loops.
        """
        if not self.all_comment_chunks:
            return

        total_chunks = len(self.all_comment_chunks)

        # Increment page index
        self.current_page += 1

        # If the next page starts beyond the available lines, reset to the first page
        if (self.current_page * self.num_lines_limit) >= total_chunks:
            self.current_page = 0

        self._update_label_view()

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
        self.move_list = []
        node = self.game
        while node.variations:
            # Always follow the main (first) variation
            node = node.variation(0)
            self.move_list.append(node)

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
            text="Clear Variation ❌",
            fg="red", # Mkae the button red to make the status clear
            command=self.restore_variation
        )
        # by default the button is INVISIBLE
        self.clear_variation_button.pack_forget()

        # Store the refrence to the Label
        self.move_list_label = tk.Label(
            moves_header_frame,
            text="Move List (Main Line)",
            font=('Arial', 12, 'bold')
        )
        self.move_list_label.pack(side=tk.LEFT, padx=(5, 0))

        # 1. Create the Canvas (the viewport)
        # Ensure the Canvas fills the space previously occupied by the Listbox
        self.moves_canvas = tk.Canvas(moves_frame, borderwidth=0, highlightthickness=0)
        self.moves_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 2. Create the Scrollbar and link it to the Canvas
        scrollbar = tk.Scrollbar(moves_frame, orient=tk.VERTICAL, command=self.moves_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.moves_canvas.config(yscrollcommand=scrollbar.set)

        # 3. Create an 'Inner Frame' INSIDE the Canvas
        self.canvas_inner_frame = tk.Frame(self.moves_canvas)

        # 4. Remove the Listbox and place a Frame for the Labels
        # We no longer need self.move_listbox as a widget; we now use the inner_frame.
        # HOWEVER, for compatibility with your other code, we could point self.move_listbox to a dummy.
        # BUT: We need to select the labels. We will store the labels in a list.
        self.move_labels = []  # New list to store the label widgets

        # 5. Attach the Inner Frame to the Canvas
        self.canvas_window_id = self.moves_canvas.create_window(
            (0, 0),
            window=self.canvas_inner_frame,
            anchor="nw",
            tags="inner_frame"
        )


    def show_clear_variation_button(self):
        """
        Manages the visibility of the 'Clear Variation'-button
        """
        if len(self.stored_moves) > 0:
            # Set the button VISIBLE
            self.clear_variation_button.pack(side=tk.LEFT, padx=5)
            # Change the text of the label
            self.move_list_label.config(text="Move List (Variation)")
        else:
            # Hide the button
            self.clear_variation_button.pack_forget()
            # Restore the label
            self.move_list_label.config(text="Move List (Main Line)")

    # --- State Update Logic ---

    def _populate_move_listbox(self):
        """
        Fills the Listbox with all moves, including any commentaries and variation indicators.
        """
        # 1. Empty the Inner Frame
        for widget in self.canvas_inner_frame.winfo_children():
            widget.destroy()
        self.move_labels.clear()
        if not self.game:
            return


        for i, node in enumerate(self.move_list):

            # The board *before* the move
            prev_board = node.parent.board()

            # Calculate Notation Prefix
            move_num = (i // 2) + 1
            if prev_board.turn == chess.WHITE:
                prefix = f"{move_num}. "
            else:
                # This logic is complex, simpler to just use spaces if not the first move of black
                prefix = f"{move_num}... " if prev_board.turn == chess.BLACK and (i == 0 or self.move_list[i-1].parent.board().turn == chess.WHITE) else "    "

            # Generate the notation (SAN)
            try:
                san_move = prev_board.san(node.move)
            except:
                 san_move = node.move.uci() # Fallback

            # Add commentary if present
            comment_text = f" ({node.comment.strip()})" if node.comment and node.comment.strip() else ""

            # Variation indicator
            variation_indicator = f" [+ {len(node.variations)-1} V]" if len(node.variations) > 1 else ""

            list_item = f"{prefix}{san_move}{comment_text}{variation_indicator}"
            #self.move_listbox.insert(tk.END, list_item)
            # create and bind Label
            label = ttk.Label(
                self.canvas_inner_frame,
                text=list_item,
                font=('Consolas', 10),
                anchor='w',
                padding=(5, 2), # Voeg wat padding toe
                background='white', # Standaard kleur
                cursor='hand2'
            )
            label.pack(fill=tk.X, pady=0)

            # Store the index in the Label-object for selection
            label.list_index = i

            # Bind Touch-events for scrolling
            label.bind("<ButtonPress-1>", self._start_scroll)
            label.bind("<B1-Motion>", self._do_scroll)
            label.bind("<ButtonRelease-1>", self._on_release_or_select)

            self.move_labels.append(label) # Sla het label op
        self._update_scroll_region()

    def _start_scroll(self, event):
        """Registers the absolute starting position of the click."""
        self._start_y = event.y_root
        self._is_dragging = False
        self.moves_canvas.focus_set()
        return "break"

    def _do_scroll(self, event):
        """Calculates the delta and shifts the Canvas content."""
        MIN_DRAG_DISTANCE = 5

        # 1. Start Drag Check
        if not self._is_dragging:
            if abs(event.y_root - self._start_y) > MIN_DRAG_DISTANCE:
                self._is_dragging = True
                self._last_y = event.y_root  # Initialize _last_y with absolute Y
            else:
                return

        # 2. Scroll with delta (y_root ensures coordinate independence)
        delta = self._last_y - event.y_root
        self.moves_canvas.yview_scroll(int(delta / 4), "units")
        self._last_y = event.y_root

        # 3. Cancel selection
        # self.move_listbox.selection_clear(0, tk.END) # Important: clear selection during scroll

        return "break"

    def _on_canvas_configure(self, event):
        """Adjusts the width of the inner frame and updates the scrollregion."""

        self.moves_canvas.update_idletasks()

        # 1. Force the Inner Frame to match the WIDTH of the Canvas (NOT HEIGHT!)
        self.moves_canvas.itemconfig(self.canvas_window_id, width=event.width)

        # 2. Update the scrollregion
        self._update_scroll_region()  # Call the helper function

    def _update_scroll_region(self):
        """Helper to set the scrollregion (crucial for scrolling)."""

        self.moves_canvas.update_idletasks()
        bbox = self.moves_canvas.bbox("all")

        if bbox:
            canvas_height = self.moves_canvas.winfo_height()

            if bbox[3] > canvas_height:
                # Content is longer than viewport: allow scrolling
                self.moves_canvas.config(scrollregion=bbox)
            else:
                # Content is shorter than viewport: disable scrolling
                self.moves_canvas.config(scrollregion=(0, 0, bbox[2], canvas_height))

    def _on_release_or_select(self, event):
        """Handles selection by changing the Label color."""

        if self._is_dragging:
            self._is_dragging = False
            return

        # First, clear all previous selections (reset all labels to white)
        for lbl in self.move_labels:
            lbl.config(background='white')

        # Find which label was clicked
        widget_clicked = event.widget

        # Check if the clicked widget is a label that we created
        if isinstance(widget_clicked, ttk.Label) and hasattr(widget_clicked, 'list_index'):
            index = widget_clicked.list_index

            # Visually set the selection
            widget_clicked.config(background='#0078D7', foreground='white')  # Blue for selection

            # Call your update logic (replace this with your ChessAnnotator logic)
            if self.current_move_index != index:
                self.current_move_index = index
                self.update_state()  # Your function to update the board

        self._is_dragging = False

    def update_move_listbox_selection(self):
        """
        Synchronizes the Label selection with the current move index.
        """

        # Clear all selections
        for lbl in self.move_labels:
            lbl.config(background='white', foreground='black')

        if 0 <= self.current_move_index < len(self.move_labels):
            # Select the target label
            target_label = self.move_labels[self.current_move_index]
            target_label.config(background='#0078D7', foreground='white')

            # Scroll to the item in the Canvas
            # This is the Canvas-specific way to scroll to an item
            target_label.update_idletasks()
            self.moves_canvas.yview_moveto


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
                board.push(self.move_list[i].move)
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
        self.next_button.config(state=tk.NORMAL if self.current_move_index < len(self.move_list) - 1 else tk.DISABLED)
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

    def update_move_listbox_selection(self):
        """
        Synchronizes the selection in the Listbox.
        """
        # Reset all labels to default colors
        for lbl in self.move_labels:
            lbl.config(background='white', foreground='black')

        if 0 <= self.current_move_index < len(self.move_labels):

            # The index is valid: perform selection
            target_label = self.move_labels[self.current_move_index]

            # 1. SELECT THE ITEM (visually)
            # Set the selected colors
            target_label.config(background='#0078D7', foreground='white')

            # 2. SCROLL TO THE ITEM (simulates .see() functionality)

            # First: ensure the widget is fully rendered to determine its Y-position
            target_label.update_idletasks()

            # Get the absolute Y-position of the top of the label within the Canvas
            label_y_position = target_label.winfo_y()

            # Calculate the scroll fraction needed to position this point.
            # We scroll so that the label appears in the center of the viewport for better visibility.

            canvas_height = self.moves_canvas.winfo_height()
            label_height = target_label.winfo_height()

            # Determine the target Y-position in the Canvas view:
            # We aim to place the center of the label in the center of the canvas
            target_y = label_y_position - (canvas_height / 2) + (label_height / 2)

            # Ensure the target position is not negative
            if target_y < 0:
                target_y = 0

            # Retrieve the maximum scrollable height (bbox[3])
            self.moves_canvas.update_idletasks()
            bbox = self.moves_canvas.bbox("all")
            if bbox:
                max_scroll_height = bbox[3]

                # Ensure the target does not exceed the bottom of the content
                if target_y > (max_scroll_height - canvas_height):
                    target_y = max_scroll_height - canvas_height

                # Perform the scroll: yview_moveto requires a fraction (0.0 to 1.0)
                scroll_fraction = target_y / max_scroll_height
                self.moves_canvas.yview_moveto(scroll_fraction)

        # Optional: If index is -1 (starting position), ensure we

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

        # Fetch the> Label-object from the stored list
        target_label = self.move_labels[index]

        # Use .config() to change the 'text' attribute
        target_label.config(text=new_list_item_text)


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
            new_comment = text_widget.get("1.0", tk.END).strip()
            node.comment = new_comment
            if self.current_move_index != -1: # Only update listbox item if it's not the root
                self.update_listbox_item(self.current_move_index)
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


    def manage_comment(self, delete=False):
        """
        Manages the commentary for the currently selected move or starting position.
        """
        node = self._get_current_node()
        if not node:
            messagebox.showinfo("Information", "Please select a move or the starting position to manage commentary.")
            return

        current_move_text = self.notation_label.cget('text')

        if delete:
            node.comment = ""
            if self.current_move_index != -1: # Only update listbox item if it's not the root
                self.update_listbox_item(self.current_move_index)
            self.update_comment_display()
            messagebox.showinfo("Commentary", f"Commentary deleted for {current_move_text}.")
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
            messagebox.showerror("Engine Error", f"Stockfish engine not found at path: {self.ENGINE_PATH}. Please check the path and permissions.")
            return None
        except Exception as e:
            messagebox.showerror("Engine Error", f"An error occurred while communicating with the engine: {e}")
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
            messagebox.showinfo("Information", "No game loaded.")
            return

        current_board = current_node.board()

        if current_board.is_game_over():
            messagebox.showinfo("Information", "Game is over. Cannot add new variations.")
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
                messagebox.showwarning("Warning", "Please select a move to add as a variation.")
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

                messagebox.showinfo("Success", f"Variation starting with {selected_sug['move_san']} added successfully.")
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

    # --- Variation Management Logic (NEW) ---

    def _open_variation_manager(self):
        """
        Opens a dialog to view, edit, add, and delete variations for the current node.
        """
        previous_current_move_index = self.current_move_index
        current_node = self._get_current_node()
        if not current_node:
            messagebox.showinfo("Information", "Please select a move or the starting position to manage variations.")
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
            for i, variation_start_node in enumerate(current_node.variations):
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
                messagebox.showwarning("Warning", "Please select a variation to edit.")
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
                messagebox.showwarning("Warning", "Please select a variation to delete.")
                return

            index = selection[0]

            # The chess.pgn.GameNode variation list is a standard list.
            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete Variation {index+1}?", parent=dialog):
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
        messagebox.showinfo("Information", "Enter move on chess-board.")
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
            messagebox.showinfo("Information", "No variations to restore.")
            return

        # 1. Pop the stored state
        base_node, move_to_restore, index_move_to_restore = self.stored_moves.pop()

        # 2. Promote the variation in the PGN tree
        base_node.promote_to_main(move_to_restore)

        # 3. Rebuild the main move_list
        self.move_list = []
        node = self.game
        while node.variations:
            node = node.variation(0)  # Follow the new main line
            self.move_list.append(node)

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
                    messagebox.showinfo("Information", f"Valid move: {move.uci()} added...")

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

        print(f"Loading chess set '{self.set_identifier}' from: {self.image_dir_path}")

        for symbol, base_prefix in self.piece_map.items():

            # The dynamic prefix: e.g., 'wK2' or 'bN3'
            filename_prefix = f"{base_prefix}"

            # List of file formats to attempt, in order of preference
            # As seen in your directory: wK2.svg, wK3.svg, or wK1.png
            extensions = ['.svg', '.png']

            img = None
            image_path = None

            for ext in extensions:
                image_path = os.path.join(self.image_dir_path, self.set_identifier, f"{filename_prefix}{ext}")

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
    app = ChessAnnotatorApp(root, pgn_game, engine_name, image_manager = asset_manager, square_size = SQUARE_SIZE-5, current_game_index = current_game_index, piece_set = piece_set, board=board)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
#example call
##python3 pgn_editor.py --pgn_game "/home/user/Schaken/2025-12-11-Anton-Gerrit-annotated.pgn" --engine_name "/home/user/Schaken/stockfish-python/Python-Easy-Chess-GUI/Engines/stockfish-ubuntu-x86-64-avx2"
