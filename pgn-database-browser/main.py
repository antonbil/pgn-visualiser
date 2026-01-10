import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import chess.pgn
from pathlib import Path
from collections import Counter
import os, sys
import json

PREF_FILE = "configuration.json"

def load_preferences():
    default_prefs = {
        "base_directory": "~/Schaken",
        "export_directory": "~/Schaken/temp",
        "export_filename": "generated.pgn",
        "page_size": 200,
    "file_page_size": 30,
    "editor_path": "/home/user/Schaken/stockfish-python/Python-Easy-Chess-GUI/annotator/pgn-visualiser/",
                   "display_path": "/home/user/Schaken/stockfish-python/Python-Easy-Chess-GUI/annotator/test/"
    }

    if os.path.exists(PREF_FILE):
        try:
            with open(PREF_FILE, "r") as f:
                return {**default_prefs, **json.load(f)}
        except Exception as e:
            print(f"Error while loading preferences.json: {e}")

    return default_prefs


# Load preferences at the start
PREFS = load_preferences()

# Define the absolute path to the directory WHERE the folder 'pgn_editor' is located
editor_path = PREFS["editor_path"]

if editor_path not in sys.path:
    sys.path.append(editor_path)

# Now you can import as if it were in your local directory
try:
    from pgn_editor.pgn_editor import ChessAnnotatorApp, PieceImageManager1
    print("Annotator successfully imported!")
except ImportError as e:
    print(f"Could not find the annotator at {editor_path}: {e}")

# Define the absolute path to the directory WHERE the folder 'pgn_editor' is located
display_path = PREFS["display_path"]

if display_path not in sys.path:
    sys.path.append(display_path)

# Now you can import as if it were in your local directory
try:
    from visualise_pgn import ChessEventViewer
    print("ChessEventViewer successfully imported!")
except ImportError as e:
    print(f"Could not find the annotator at {editor_path}: {e}")

class TouchMoveListColor(tk.Frame):
    """
    A streamlined, touch-friendly list replacement for the Library.
    Supports basic highlighting, smooth scrolling, and momentum.
    """

    def __init__(self, parent, move_pairs=None, select_callback=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.move_pairs = move_pairs if move_pairs else []
        self.select_callback = select_callback
        self.selected_index = None

        # --- UI Setup ---
        # --- UI Setup ---
        self.text_area = tk.Text(
            self,
            font=("Segoe UI", 13),  # Increased base font size
            wrap=tk.NONE,
            bg="white",
            padx=10,
            pady=10,
            cursor="arrow",
            highlightthickness=0,
            bd=0,
            state=tk.DISABLED,
            undo=False,
            exportselection=False,
            # Spacing makes the lines much easier to tap with fingers
            spacing1=8,  # Extra space above the line
            spacing3=8  # Extra space below the line
        )
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text_area.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.configure(yscrollcommand=self.scrollbar.set)

        # Basic tag configuration for highlighting
        self.text_area.tag_configure("highlight", background="#cfe2f3")

        # --- Event Bindings ---
        self.text_area.bind("<Button-1>", self._on_drag_start)
        self.text_area.bind("<B1-Motion>", self._on_drag_motion)
        self.text_area.bind("<ButtonRelease-1>", self._on_tap)

        # Scrolling and momentum variables
        self.drag_start_y = 0
        self.start_scroll_pos = 0
        self.scrolled_too_far = False
        self.last_y = 0
        self.velocity = 0
        self.momentum_id = None
        self.text_area.tag_configure("game_count", foreground="#888888")  # Grey color
        # A very light grey (#f9f9f9) or a soft blue-grey (#f2f4f6) works well
        self.text_area.tag_configure("odd_row", background="#f2f4f6")
        # Ensure the selection highlight stays on top of the row color
        self.text_area.tag_raise("highlight", "odd_row")
        if self.move_pairs:
            self._populate()

    def _populate(self):
        """ Clears and fills the text area with initial move pairs. """
        self.delete(0, tk.END)
        for i, move in enumerate(self.move_pairs):
            self.insert(tk.END, move)

    def _on_drag_start(self, event):
        """ Handles the initial press and cancels active momentum. """
        if self.momentum_id:
            self.after_cancel(self.momentum_id)
            self.momentum_id = None

        self.drag_start_y = event.y
        self.last_y = event.y
        self.start_scroll_pos = self.text_area.yview()[0]
        self.scrolled_too_far = False
        self.velocity = 0

        # Ensure the text_area gains focus for keyboard shortcuts
        self.text_area.focus_set()
        return "break"

    def _on_drag_motion(self, event):
        """ Tracks movement to perform scrolling and calculate velocity. """
        delta_y = event.y - self.drag_start_y
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
        """ Handles the release event to trigger selection or momentum. """
        if self.scrolled_too_far:
            if abs(self.velocity) > 2:
                self._apply_momentum(self.velocity)
            return "break"

        index_str = self.text_area.index(f"@{event.x},{event.y}")
        line_index = int(index_str.split('.')[0]) - 1

        # Selection logic is usually handled by the subclass MultiSelectTouchList
        if self.select_callback:
            self.select_callback(line_index)
        return "break"

    def _apply_momentum(self, current_velocity):
        """ Smoothly continues scrolling after a fast swipe. """
        friction = 0.92
        new_velocity = current_velocity * friction
        if abs(new_velocity) > 0.5:
            height = self.text_area.winfo_height()
            if height > 1:
                current_pos = self.text_area.yview()[0]
                new_scroll_pos = current_pos - (new_velocity / height)
                self.text_area.yview_moveto(max(0, min(1, new_scroll_pos)))
                self.momentum_id = self.after(10, lambda: self._apply_momentum(new_velocity))

    # --- Public API ---
    def insert(self, index, text):
        """
        Inserts text with alternating background colors and
        automatic color tagging for game counts.
        """
        self.text_area.config(state=tk.NORMAL)

        # Determine the current line number to decide on background color
        # index 'end-1c' gives the position before the final newline
        line_number = int(self.text_area.index("end-1c").split('.')[0])

        # Decide which tag to use for the background
        line_tag = "odd_row" if line_number % 2 == 0 else ""

        # Regex to find text within parentheses
        import re
        parts = re.split(r'(\(.+?\))', text)

        for part in parts:
            # Combine the background tag with the functional tags
            tags = [line_tag] if line_tag else []

            if part.startswith('(') and part.endswith(')'):
                tags.append("game_count")
                self.text_area.insert(tk.END, part, tuple(tags))
            else:
                self.text_area.insert(tk.END, part, tuple(tags))

        # Add the newline and apply the background tag to it as well
        # to ensure the color covers the full width.
        self.text_area.insert(tk.END, "\n", line_tag if line_tag else None)
        self.text_area.config(state=tk.DISABLED)

    def delete(self, first, last=None):
        """ Deletes lines based on zero-based index. """
        self.text_area.config(state=tk.NORMAL)
        if first == 0 and (last == tk.END or last is None):
            self.text_area.delete("1.0", tk.END)
        else:
            self.text_area.delete(f"{first + 1}.0", f"{last + 1}.0" if last else f"{first + 2}.0")
        self.text_area.config(state=tk.DISABLED)

    def selection_set(self, index):
        """ Applies the highlight tag to a specific line. """
        start = f"{index + 1}.0"
        end = f"{index + 1}.end + 1c"
        self.text_area.tag_add("highlight", start, end)

    def selection_clear(self):
        """ Removes the highlight tag from all text. """
        self.text_area.tag_remove("highlight", "1.0", tk.END)

    def get_selected_indices(self):
        """ Returns a list of all line indices that are currently highlighted. """
        ranges = self.text_area.tag_ranges("highlight")
        indices = []
        for i in range(0, len(ranges), 2):
            start_line = int(ranges[i].string.split('.')[0]) - 1
            indices.append(start_line)
        return indices

    def see(self, index):
        """ Ensures the specified line is visible in the view. """
        self.text_area.see(f"{index + 1}.0")

class MultiSelectTouchList(TouchMoveListColor):
    """
    Subclass that uses an internal state to manage Ctrl-clicks
    and prevent premature callback execution.
    """

    def __init__(self, parent, move_pairs=None, select_callback=None, parent_tab=None, **kwargs):
        super().__init__(parent, move_pairs, select_callback, **kwargs)
        self.parent_tab = parent_tab
        self.ctrl_active = False
        # Define a tab stop at 300 pixels
        self.text_area.config(tabs=(400,))

    def _on_drag_start(self, event):
        """ Capture state and block default behavior. """
        # Check if a context menu was just active
        if self.parent_tab and getattr(self.parent_tab, 'context_menu_active', False):
            # Manually close the menu
            self.parent_tab.context_menu.unpost()
            return "break"  # Block the start of a selection/drag
        if self.momentum_id:
            self.after_cancel(self.momentum_id)
            self.momentum_id = None

        self.drag_start_y = event.y
        self.last_y = event.y
        self.start_scroll_pos = self.text_area.yview()[0]
        self.scrolled_too_far = False
        self.velocity = 0

        # Update the internal state based on the Control key
        self.ctrl_active = (event.state & 0x0004) != 0

        return "break"

    def _on_tap(self, event):
        """ Handle selection and conditionally trigger callback. """
        # Check if a context menu was just active
        if self.parent_tab and getattr(self.parent_tab, 'context_menu_active', False):
            # Consume the event so no selection happens
            return "break"
        if self.scrolled_too_far:
            if abs(self.velocity) > 2:
                self._apply_momentum(self.velocity)
            return "break"

        index_str = self.text_area.index(f"@{event.x},{event.y}")
        line_index = int(index_str.split('.')[0]) - 1

        # We use the state we captured at the start of the click
        if self.ctrl_active:
            # Multi-select: just toggle, don't fire the callback yet
            # This allows the user to select multiple items peacefully
            self.toggle_selection(line_index)
            print("Ctrl-click: Selection toggled, callback suppressed.")
        else:
            # Normal click: reset selection and fire callback
            self.clear_selection()
            self.selection_set(line_index)

            if self.select_callback:
                print("Normal click: Triggering callback.")
                self.select_callback(line_index)

        return "break"

    def toggle_selection(self, index):
        """
        Toggles the 'highlight' tag for a specific row.
        """
        start = f"{index + 1}.0"
        end = f"{index + 1}.end + 1c"

        # Retrieve all tags at the clicked position
        tags = self.text_area.tag_names(start)

        if "highlight" in tags:
            self.text_area.tag_remove("highlight", start, end)
        else:
            self.text_area.tag_add("highlight", start, end)

    def get_selected_indices(self):
        """
        Returns a list of all row indices currently highlighted.
        """
        selected = []
        # Get total number of lines in the text widget
        try:
            total_lines = int(self.text_area.index('end-1c').split('.')[0])
            for i in range(total_lines):
                if "highlight" in self.text_area.tag_names(f"{i + 1}.0"):
                    selected.append(i)
        except Exception:
            pass
        return selected

    def clear_selection(self):
        """
        Removes all highlighting from the widget.
        """
        self.text_area.tag_remove("highlight", "1.0", tk.END)

    def select_all(self):
        """Applies the 'highlight' tag to all text."""
        self.text_area.tag_add("highlight", "1.0", "end")


class LibraryTab(ttk.Frame):
    def __init__(self, parent, label_text, data_index, on_select_callback):
        super().__init__(parent)
        self.data_index = data_index
        self.on_select_callback = on_select_callback
        self.search_var = tk.StringVar()
        self.current_keys = []

        self._setup_ui()
        self._setup_context_menu()

    def _setup_ui(self):
        """ Creates the search entry and the touch-friendly list. """
        # 1. Search Frame (Top)
        s_frame = ttk.Frame(self)
        s_frame.pack(fill=tk.X, pady=5, padx=5)

        self.entry = ttk.Entry(s_frame, textvariable=self.search_var)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Bind Enter key to search
        self.entry.bind("<Return>", lambda e: self._on_search_click())

        search_btn = ttk.Button(
            s_frame,
            text="Search",
            command=self._on_search_click
        )
        search_btn.pack(side=tk.LEFT)

        # 2. Touch List (Bottom - fills remaining space)
        self.touch_list = MultiSelectTouchList(
            self,
            move_pairs=[],
            select_callback=self._on_item_tapped,
            parent_tab=self # Pass reference to access context_menu_active
        )
        self.touch_list.pack(fill=tk.BOTH, expand=True)
        self.touch_list.text_area.config(takefocus=True)

        # Right-click bindings
        self.touch_list.text_area.bind("<Button-3>", self._show_context_menu)
        self.touch_list.text_area.bind("<Button-2>", self._show_context_menu)
        # Keyboard Bindings for the Library List
        self.touch_list.text_area.bind("<Control-a>", self._select_all)
        self.touch_list.text_area.bind("<Control-A>", self._select_all)
        self.touch_list.text_area.bind("<Escape>", self._clear_selection)

    def _setup_context_menu(self):
        """ Initializes the right-click menu. """
        self.context_menu_active = False  # State flag
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(
            label="Open Selected Games",
            command=self._handle_context_open
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Select All", command=self._select_all)
        self.context_menu.add_command(label="Clear Selection", command=self.touch_list.clear_selection)

    def _show_context_menu(self, event):
        index_str = self.touch_list.text_area.index(f"@{event.x},{event.y}")
        line_index = int(index_str.split('.')[0]) - 1

        if line_index not in self.touch_list.get_selected_indices():
            if not (event.state & 0x0004):
                self.touch_list.clear_selection()
            self.touch_list.selection_set(line_index)

        try:
            self.context_menu_active = True
            self.context_menu.post(event.x_root, event.y_root)
            self.context_menu.focus_set()

            # Use a wrapper to reset the flag when the menu closes
            self.context_menu.bind("<FocusOut>", self._on_menu_close)
        except Exception as e:
            print(f"Context menu error: {e}")

    def _on_menu_close(self, event=None):
        """ Closes the menu and resets the flag after a tiny delay. """
        self.context_menu.unpost()
        # We use a small delay (100ms) so that a click that closes the menu
        # is still caught by the 'if self.context_menu_active' check.
        # Keep the shield active for 100ms to block the 'ButtonRelease' (tap)
        self.after(100, self._reset_menu_flag)

    def _reset_menu_flag(self):
        self.context_menu_active = False

    def _handle_context_open(self):
        """ Triggered by the menu to open the combined game list. """
        # We manually trigger the selection callback of the browser
        self.on_select_callback(self, self.data_index)

    def get_selected_keys(self):
        """ Returns the actual names/years for all highlighted lines. """
        selected_indices = self.touch_list.get_selected_indices()
        return [self.current_keys[i] for i in selected_indices if i < len(self.current_keys)]

    def _on_item_tapped(self, index):
        """ Callback from touch list (Standard tap). """
        self.on_select_callback(self, self.data_index)
    def _on_search_click(self):
        self.master.master.refresh_current_tab()

    def get_selected_keys(self):
        """Returns all names/years that are currently highlighted."""
        selected_indices = self.touch_list.get_selected_indices()
        return [self.current_keys[i] for i in selected_indices if i < len(self.current_keys)]

    def _select_all(self, event=None):
        self.touch_list.select_all()
        return "break"

    def _clear_selection(self, event=None):
        self.touch_list.clear_selection()
        return "break"


    def _invert_selection(self, event=None):
        """Inverts the selection for every line."""
        for i in range(len(self.current_keys)):
            self.touch_list.toggle_selection(i)
        return "break"

class GlobalLibraryBrowser(tk.Tk):
    def __init__(self):
        super().__init__()
        # Load preferences
        self.prefs = self._load_preferences()
        self.directory = Path(self.prefs["base_directory"]).expanduser()
        self.tab_keys = ["player", "opening", "year", "file"]

        self.title(f"Chess Library Browser - {self.directory}")
        self.geometry("700x650")

        self.page_size = self.prefs.get("page_size", 35)

        # Data storage
        self._reset_indexes()

        # Initialize UI and Menu
        self._setup_menu()
        self._setup_ui()

        # Start scanning
        self.after(100, self._scan_all_databases)

    def _reset_indexes(self):
        """Initializes or clears all data indexes and pagination counters."""
        self.player_index = {}
        self.opening_index = {}
        self.year_index = {}
        self.file_index = {}

        self.player_start = 0
        self.opening_start = 0
        self.year_start = 0
        self.file_start = 0

    def _setup_menu(self):
        """Creates the top menu bar."""
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)

        # File Menu
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)

        file_menu.add_command(label="Open Directory...", command=self.change_directory)
        file_menu.add_command(label="Refresh Library", command=self.refresh_library, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        # Select Menu
        select_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Select", menu=select_menu)
        select_menu.add_command(label="Select All", command=self._menu_select_all, accelerator="Ctrl+A")
        # Clear Selection option
        select_menu.add_command(label="Clear Selection", command=self._menu_clear_selection, accelerator="Escape")
        select_menu.add_command(label="Invert Selection", command=self._menu_invert_selection, accelerator="Ctrl+I")
        # Settings Menu
        settings_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Settings", menu=settings_menu)

        settings_menu.add_command(label="Set Export Directory...",
                                  command=lambda: self._set_pref_path("export_directory"))
        settings_menu.add_command(label="Set Editor Path...",
                                  command=lambda: self._set_pref_path("editor_path"))
        settings_menu.add_command(label="Set Display Path...",
                                  command=lambda: self._set_pref_path("display_path"))
        settings_menu.add_separator()
        settings_menu.add_command(label="Set Library Page Size...",
                                  command=self._set_page_size_pref)
        settings_menu.add_command(label="Set Game-list Page Size...",
                                  command=self._set_page_size_games_pref)

        # Tools Menu
        tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Statistics", command=self.show_statistics)
        # Shortcut binding for F5
        self.bind("<F5>", lambda e: self.refresh_library())

    def _load_preferences(self):
        default = {"base_directory": "~/Chess", "page_size": 35}
        try:
            if os.path.exists(PREF_FILE):
                with open(PREF_FILE, "r") as f:
                    return {**default, **json.load(f)}
        except:
            pass
        return default

    def _setup_ui(self):
        # 1. Progression (at the top)
        self.prog_frame = ttk.Frame(self)
        self.prog_frame.pack(fill=tk.X, padx=10, pady=5)
        self.prog_label = ttk.Label(self.prog_frame, text="Ready to scan...")
        self.prog_label.pack(side=tk.LEFT)
        self.prog_bar = ttk.Progressbar(self.prog_frame, mode='determinate')
        self.prog_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

        self.notebook = ttk.Notebook(self)

        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._update_nav_labels())

        # 3. NOW CREATE THE TABS (passing self.notebook as parent)
        self.tabs = {}
        self.tabs["player"] = LibraryTab(self.notebook, "Player Name", self.player_index, self._on_select)
        self.tabs["opening"] = LibraryTab(self.notebook, "Opening (ECO)", self.opening_index, self._on_select)
        self.tabs["year"] = LibraryTab(self.notebook, "Year", self.year_index, self._on_select)

        self.notebook.add(self.tabs["player"], text=" Players ")
        self.notebook.add(self.tabs["opening"], text=" Openings ")
        self.notebook.add(self.tabs["year"], text=" Years ")
        self.tabs["file"] = LibraryTab(self.notebook, "Database File", self.file_index, self._on_select)
        self.notebook.add(self.tabs["file"], text=" Databases ")
        # 3. Navigation Frame: at the bottom, outside the tabs
        nav_frame = ttk.Frame(self)
        nav_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        # Previous Button
        self.btn_prev = ttk.Button(nav_frame, text="<<", command=self._prev_page, width=5)
        self.btn_prev.pack(side=tk.LEFT, padx=5)

        # The Slider (Scale)
        # We use tk.Scale because it's easier to style for touch than ttk.Scale
        self.page_slider = tk.Scale(
            nav_frame,
            from_=0,
            to=100,  # This will be updated dynamically
            orient=tk.HORIZONTAL,
            showvalue=False,  # We show the value in our own label
            command=self._on_slider_move,
            sliderlength=40,  # Bigger handle for fingers
            width=20,  # Thicker bar
            bd=0,
            highlightthickness=0
        )
        self.page_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Next Button
        self.btn_next = ttk.Button(nav_frame, text=">>", command=self._next_page, width=5)
        self.btn_next.pack(side=tk.LEFT, padx=5)

        # Page Label (showing the current range)
        self.page_label = ttk.Label(nav_frame, text="0 - 0", width=15, anchor="center")
        self.page_label.pack(side=tk.LEFT, padx=5)
        # pack notebook last
        self.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

    def _get_current_context(self):
        tab_idx = self.notebook.index(self.notebook.select())
        mapping = {
            0: ("player", self.player_index, self.tabs["player"].search_var.get(), self.player_start),
            1: ("opening", self.opening_index, self.tabs["opening"].search_var.get(), self.opening_start),
            2: ("year", self.year_index, self.tabs["year"].search_var.get(), self.year_start),
            3: ("file", self.file_index, self.tabs["file"].search_var.get(), self.file_start)
        }
        return mapping.get(tab_idx)

    def refresh_current_tab(self):
        context, _, _, _ = self._get_current_context()
        refresh_methods = {
            "player": self._display_players,
            "opening": self._display_openings,
            "year": self._display_years,
            "file": self._display_files
        }
        refresh_methods[context]()

    def _on_slider_move(self, value):
        """
        Handles slider movement. Translates the page number from the slider
        to the starting index of the current active tab.
        """
        # Convert slider value to integer page number
        new_page = int(float(value))
        new_start = new_page * self.page_size

        context, _, _, _ = self._get_current_context()

        # Check if the start index actually changed to avoid redundant refreshes
        if context == "player" and self.player_start != new_start:
            self.player_start = new_start
            self._display_players()
        elif context == "opening" and self.opening_start != new_start:
            self.opening_start = new_start
            self._display_openings()
        elif context == "year" and self.year_start != new_start:
            self.year_start = new_start
            self._display_years()
        elif context == "file" and self.file_start != new_start:
            self.file_start = new_start
            self._display_files()

        # Update the labels to reflect the new range
        self._update_nav_labels()

    def _next_page(self):
        context, _, _, _ = self._get_current_context()
        if context == "player":
            if self.player_start + self.page_size < len(self.player_index):
                self.player_start += self.page_size
                self._display_players()
        elif context == "opening":
            if self.opening_start + self.page_size < len(self.opening_index):
                self.opening_start += self.page_size
                self._display_openings()
        elif context == "year":
            if self.year_start + self.page_size < len(self.year_index):
                self.year_start += self.page_size
                self._display_years()
        elif context == "file":
            if self.file_start + self.page_size < len(self.file_index):
                self.file_start += self.page_size
                self._display_files()
        self._update_nav_labels()

    def _prev_page(self):
        context, _, _, _ = self._get_current_context()
        if context == "player":
            self.player_start = max(0, self.player_start - self.page_size)
            self._display_players()
        elif context == "opening":
            self.opening_start = max(0, self.opening_start - self.page_size)
            self._display_openings()
        elif context == "year":
            self.year_start = max(0, self.year_start - self.page_size)
            self._display_years()
        elif context == "file":
            self.file_start = max(0, self.file_start - self.page_size)
            self._display_files()
        self._update_nav_labels()

    def _update_nav_labels(self):
        """
        Synchronizes the slider range, slider position, and page labels
        based on the current active tab's data and scroll position.
        """
        context, _, _, _ = self._get_current_context()

        # 1. Determine current start index and total items for the active tab
        if context == "player":
            current_start = self.player_start
            total_items = len(self.player_index)
        elif context == "opening":
            current_start = self.opening_start
            total_items = len(self.opening_index)
        elif context == "year":
            current_start = self.year_start
            total_items = len(self.year_index)
        else:  # file
            current_start = self.file_start
            total_items = len(self.file_index)

        # 2. Calculate pagination values
        total_pages = (total_items + self.page_size - 1) // self.page_size
        current_page = current_start // self.page_size

        # 3. Update the Slider widget
        # We temporarily disable the command to prevent a feedback loop
        self.page_slider.config(command="")
        self.page_slider.config(to=max(0, total_pages - 1))
        self.page_slider.set(current_page)
        self.page_slider.config(command=self._on_slider_move)

        # 4. Update the Range Label (e.g., "1 - 200 of 5000")
        end_item = min(current_start + self.page_size, total_items)
        if total_items == 0:
            self.page_label.config(text="No items")
        else:
            self.page_label.config(text=f"{current_start + 1} - {end_item} of {total_items}")

        # 5. Update Button States (Disable if at boundaries)
        self.btn_prev.config(state=tk.NORMAL if current_start > 0 else tk.DISABLED)

    def _save_preferences(self):
        """Saves current directory and other settings to configuration.json."""
        try:
            with open(PREF_FILE, "w") as f:
                json.dump(self.prefs, f, indent=4)
        except Exception as e:
            print(f"Failed to save preferences: {e}")

    def _menu_select_all(self):
        """Finds the currently active tab and triggers its select_all method."""
        # Get the index of the currently selected tab in the notebook
        current_tab_idx = self.notebook.index(self.notebook.select())

        # Map the index to our tab objects

        if current_tab_idx < len(self.tab_keys):
            target_key = self.tab_keys[current_tab_idx]
            target_tab = self.tabs[target_key]

            # Call the select_all method of that specific LibraryTab instance
            target_tab._select_all()

    def _menu_clear_selection(self):
        """Triggers clear_selection on the currently active tab."""
        current_tab_idx = self.notebook.index(self.notebook.select())
        if current_tab_idx < len(self.tab_keys):
            self.tabs[self.tab_keys[current_tab_idx]]._clear_selection()

    def _menu_invert_selection(self):
        """Triggers invert_selection on the currently active tab."""
        current_tab_idx = self.notebook.index(self.notebook.select())
        if current_tab_idx < len(self.tab_keys):
            self.tabs[self.tab_keys[current_tab_idx]]._invert_selection()

    def _scan_all_databases(self):
        files = list(self.directory.glob('*.pgn'))
        self.prog_bar['maximum'] = len(files)

        for i, pgn_file in enumerate(files):
            self.prog_label.config(text=f"Scanning: {pgn_file.name}")
            self.prog_bar['value'] = i + 1
            self.update()

            try:
                with open(pgn_file, encoding='utf-8', errors='ignore') as f:
                    game_idx = 0
                    while True:
                        offset = f.tell()
                        headers = chess.pgn.read_headers(f)
                        if headers is None: break

                        # 1. Index Players
                        for tag in ["White", "Black"]:
                            name = headers.get(tag, "Unknown")
                            if name not in self.player_index: self.player_index[name] = []
                            self.player_index[name].append((str(pgn_file), offset, game_idx))

                        # 2. Index Opening
                        eco = headers.get("ECO", "???")
                        opening_name = headers.get("Opening", "Unknown")
                        full_op = f"{eco} - {opening_name}"
                        if full_op not in self.opening_index: self.opening_index[full_op] = []
                        self.opening_index[full_op].append((str(pgn_file), offset, game_idx))

                        # 3. Index Year
                        date_str = headers.get("Date", "????")
                        year = date_str[:4] if len(date_str) >= 4 else "Unknown"

                        # Validate if it is a number, otherwise "Unknown"
                        if not year.isdigit(): year = "Unknown"

                        if year not in self.year_index: self.year_index[year] = []
                        self.year_index[year].append((str(pgn_file), offset, game_idx))

                        # 4. Index Database File
                        file_key = pgn_file.name
                        if file_key not in self.file_index:
                            self.file_index[file_key] = []
                        self.file_index[file_key].append((str(pgn_file), offset, game_idx))

                        game_idx += 1
            except Exception as e:
                print(f"Error in {pgn_file}: {e}")

        self._display_players()
        self._display_openings()
        self._display_years()
        self._display_files()
        self.prog_frame.pack_forget()

    def change_directory(self):
        """Prompts the user to select a new directory and rescans it."""
        new_dir = filedialog.askdirectory(initialdir=self.directory, title="Select PGN Directory")
        if new_dir:
            self.directory = Path(new_dir)
            self.title(f"Chess Library Browser - {self.directory}")

            # Update preferences (optional, if you want it to persist)
            self.prefs["base_directory"] = str(self.directory)
            self._save_preferences()

            self.refresh_library()

    def _set_pref_path(self, pref_key):
        """Universal method to modify a path in the settings."""
        current_path = PREFS.get(pref_key, "~")
        new_path = tk.filedialog.askdirectory(
            initialdir=os.path.expanduser(current_path),
            title=f"Select {pref_key.replace('_', ' ').title()}"
        )
        if new_path:
            self.prefs[pref_key] = new_path
            self._save_preferences()
            print(f"Updated {pref_key}: {new_path}")

    def _set_page_size_pref(self):
        """Dialog to modify the page_size of the library."""
        current_val = PREFS.get("page_size", 20)
        new_val = tk.simpledialog.askinteger(
            "Settings", "Enter items per page in library:",
            initialvalue=current_val, minvalue=10, maxvalue=2000
        )
        if new_val:
            PREFS["page_size"] = new_val
            print(f"Updated page_size: {new_val}")

    def _set_page_size_games_pref(self):
        """Dialog to modify the page_size of the game-list."""
        current_val = PREFS.get("file_page_size", 20)
        new_val = tk.simpledialog.askinteger(
            "Settings", "Enter items per page in games-list:",
            initialvalue=current_val, minvalue=10, maxvalue=2000
        )
        if new_val:
            PREFS["file_page_size"] = new_val
            print(f"Updated page_size: {new_val}")

    def refresh_library(self):
        """Full reset and rescan of the current directory."""
        self._reset_indexes()

        # Show progress bar
        self.prog_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        self.prog_label.config(text=f"Scanning: {self.directory}...")
        self.prog_bar['value'] = 0

        self.after(100, self._scan_all_databases)

    def _display_players(self):
        self._fill_list("player", self.player_index,
                        self.tabs["player"].search_var.get(), self.player_start)
        self._update_nav_labels()

    def _display_openings(self):
        self._fill_list("opening", self.opening_index,
                        self.tabs["opening"].search_var.get(), self.opening_start, sort_by_count=False, ascending=True)
        self._update_nav_labels()

    def _display_years(self):
        self._fill_list("year", self.year_index,
                        self.tabs["year"].search_var.get(), self.year_start, sort_by_count=False)
        self._update_nav_labels()

    def _display_files(self):
        self._fill_list("file", self.file_index,
                        self.tabs["file"].search_var.get(), self.file_start)
        self._update_nav_labels()

    def _fill_list(self, tab_key, data_index, filter_term, start_index, sort_by_count=True, ascending=False):
        tab = self.tabs[tab_key]

        # 1. Clear current list
        tab.touch_list.delete(0, tk.END)
        tab.current_keys = []

        # 2. Filter and Sort
        filtered_items = [item for item in data_index.items()
                          if not filter_term or filter_term.lower() in item[0].lower()]

        if sort_by_count:
            sorted_items = sorted(filtered_items, key=lambda x: len(x[1]), reverse=not ascending)
        else:
            sorted_items = sorted(filtered_items, key=lambda x: x[0], reverse=not ascending)

        page_items = sorted_items[start_index: start_index + self.page_size]

        # 3. Insert into TouchMoveListColor
        for name, games in page_items:
            # We use a simple format. The 'insert' method will handle the regex.
            # Since this isn't PGN, the regex won't find move numbers/variants,
            # so it will just insert it as plain text.
            # 1. Replace regular spaces with hard spaces (\u00A0)
            clean_name = name.replace(' ', '\u00A0')

            # 2. Construct the line with a Tab character
            # 1. Replace regular spaces with hard spaces (\u00A0)
            clean_name = name.replace(' ', '\u00A0')

            # 2. Construct the line with a Tab character
            if tab_key == "opening":
                key = f"{len(games)}".rjust(3, '0')
                display_line = f"({key}){clean_name}"
            else:
                display_line = f"{clean_name}\t({len(games)} games)"

            tab.touch_list.insert(tk.END, display_line)

            tab.current_keys.append(name)

    def show_statistics(self):
        """Calculates and displays database statistics in a new window."""
        # Total counts
        total_files = len(self.file_index)
        # Sum up all games from the file index
        total_games = sum(len(games) for games in self.file_index.values())
        total_players = len(self.player_index)
        total_openings = len(self.opening_index)

        # Calculate result distribution and date range
        results = {"1-0": 0, "0-1": 0, "1/2-1/2": 0, "*": 0}
        years = [int(y) for y in self.year_index.keys() if y.isdigit()]

        # Create Statistics Window
        stats_win = tk.Toplevel(self)
        stats_win.title("Library Statistics")
        stats_win.geometry("400x450")
        stats_win.resizable(False, False)

        content = ttk.Frame(stats_win, padding="20")
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(content, text="Database Overview", font=("Helvetica", 14, "bold")).pack(pady=(0, 15))

        # Helper to add rows
        def add_stat(label, value):
            row = ttk.Frame(content)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, font=("Helvetica", 10)).pack(side=tk.LEFT)
            ttk.Label(row, text=str(value), font=("Helvetica", 10, "bold")).pack(side=tk.RIGHT)

        add_stat("Total PGN Files:", total_files)
        add_stat("Total Games:", total_games)
        add_stat("Unique Players:", total_players)
        add_stat("Unique Openings:", total_openings)

        if years:
            add_stat("Oldest Game:", min(years))
            add_stat("Newest Game:", max(years))

        ttk.Separator(content, orient='horizontal').pack(fill=tk.X, pady=15)

        ttk.Label(content, text="Game Distribution (by Year count)", font=("Helvetica", 11, "bold")).pack(pady=(0, 5))

        # Show top 3 most active years
        top_years = sorted(self.year_index.items(), key=lambda x: len(x[1]), reverse=True)[:3]
        for yr, games in top_years:
            add_stat(f"Year {yr}:", f"{len(games)} games")

        ttk.Button(content, text="Close", command=stats_win.destroy).pack(side=tk.BOTTOM, pady=(20, 0))

    def _on_select(self, tab, data_index):
        """Collects games from selected items in the TouchMoveListColor."""
        # IMPORTANT: 'tab' is now a LibraryTab instance, not a Treeview
        selected_names = tab.get_selected_keys()

        if not selected_names:
            return

        combined_data = []
        for key in selected_names:
            key = str(key).strip()
            if key in data_index:
                combined_data.extend(data_index[key])

        if combined_data:
            if len(selected_names) > 3:
                window_title = f"Multiple Selection ({len(selected_names)} items)"
            else:
                window_title = ", ".join(selected_names)

            # Open the Game List Viewer
            GlobalGameListWindow(self, window_title, combined_data)

class GlobalGameListWindow(tk.Toplevel):
    def __init__(self, parent, player_name, game_data):
        super().__init__(parent)
        self.chess_annotator_app = None
        self.title(f"Games of {player_name}")
        self.geometry("1200x650")  # Slightly larger for touch

        self.game_data = game_data
        self.prefs = parent.prefs
        self.page_size = self.prefs.get("file_page_size", 20)
        self.current_page = 0

        # Track sort status
        self.sort_status = {
            "date": False, "white": True, "black": True,
            "result": True, "file": True
        }

        self._setup_styles()
        self._setup_context_menu()
        self._setup_ui()
        self._setup_window_menu()
        self.refresh_page()

    def _setup_styles(self):
        """
        Configures a touch-friendly Treeview style with larger text
        and tighter vertical margins.
        """
        style = ttk.Style()

        # Increase font to 12 or 13 for better legibility.
        # Keeping rowheight at 35 makes the margins smaller
        # because the text takes up more of that vertical space.
        tree_font = ("Segoe UI", 13)
        header_font = ("Segoe UI Bold", 12)

        style.configure("Touch.Treeview",
                        rowheight=40,
                        font=tree_font)

        style.configure("Touch.Treeview.Heading",
                        font=header_font)

        # Ensure the selection color is still clearly visible with larger text
        style.map("Touch.Treeview",
                  background=[('selected', '#0078d7')],
                  foreground=[('selected', 'white')])

        # Wide scrollbar for easier thumb-scrolling
        style.configure("Vertical.TScrollbar", arrowsize=25, width=25)

    def _setup_ui(self):
        # Top Info Frame
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        self.lbl_info = ttk.Label(info_frame, text="", font=("Segoe UI", 10, "italic"))
        self.lbl_info.pack(side=tk.LEFT)

        # Main List Frame
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        self.columns = ("date", "white", "black", "result", "file")
        self.tree = ttk.Treeview(
            list_frame,
            columns=self.columns,
            show='headings',
            style="Touch.Treeview"
        )

        for col in self.columns:
            self.tree.heading(col, text=self._get_col_label(col),
                              command=lambda c=col: self._sort_by(c))

        self.tree.column("date", width=100, anchor="center")
        self.tree.column("white", width=200)
        self.tree.column("black", width=200)
        self.tree.column("result", width=80, anchor="center")
        self.tree.column("file", width=250)

        # Configure the alternating row color
        self.tree.tag_configure("odd_row", background="#f2f4f6")
        # The even row stays white by default, but you can define it explicitly if needed
        self.tree.tag_configure("even_row", background="white")

        # Wide scrollbar
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                               command=self.tree.yview, style="Vertical.TScrollbar")
        self.tree.configure(yscroll=scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Pagination Footer
        nav_frame = ttk.Frame(self)
        nav_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=15, padx=10)

        # Smaller width for buttons to make room for the slider
        self.btn_prev = ttk.Button(nav_frame, text="  <<  ", command=self._prev_page, width=6)
        self.btn_prev.pack(side=tk.LEFT, padx=5)

        # Finger-friendly slider
        self.page_slider = tk.Scale(
            nav_frame,
            from_=0,
            to=100,  # Dynamic
            orient=tk.HORIZONTAL,
            showvalue=False,
            command=self._on_slider_move,
            sliderlength=40,  # Touch target size
            width=20,  # Bar thickness
            bd=0,
            highlightthickness=0
        )
        self.page_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        self.btn_next = ttk.Button(nav_frame, text="  >>  ", command=self._next_page, width=6)
        self.btn_next.pack(side=tk.LEFT, padx=5)

        # Status Label
        self.lbl_page = ttk.Label(nav_frame, text="Page 1 of X", width=20, anchor="center")
        self.lbl_page.pack(side=tk.LEFT, padx=5)

        # Bindings
        self.tree.bind("<Double-1>", self._on_select)
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Button-2>", self._show_context_menu)
        # Keyboard Bindings for the Game Treeview
        self.tree.bind("<Control-a>", self._select_all)
        self.tree.bind("<Control-A>", self._select_all)
        self.tree.bind("<Escape>", self._clear_selection)
        self.tree.bind("<Control-i>", self._invert_selection)
        self.tree.bind("<Control-I>", self._invert_selection)

        # Ensure the treeview can receive focus for these shortcuts to work
        self.tree.focus_set()

    def _setup_window_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File/Action Menu
        action_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Actions", menu=action_menu)
        action_menu.add_command(label="Save Games (Current Sort)", command=self._save_all_games)
        action_menu.add_separator()
        action_menu.add_command(label="Close Window", command=self.destroy)

        # Selection Menu
        select_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Select", menu=select_menu)
        select_menu.add_command(label="Select All", command=self._select_all, accelerator="Ctrl+A")
        select_menu.add_command(label="Clear Selection", command=self._clear_selection, accelerator="Esc")
        select_menu.add_command(label="Invert Selection", command=self._invert_selection, accelerator="Ctrl+I")

    def _on_slider_move(self, value):
        """ Handles slider scrubbing. Updates the current page and refreshes. """
        new_page = int(float(value))
        if new_page != self.current_page:
            self.current_page = new_page
            self.refresh_page()

    def refresh_page(self):
        """ Loads only the items for the current page and syncs UI elements. """
        self.tree.delete(*self.tree.get_children())

        total_games = len(self.game_data)
        total_pages = (total_games + self.page_size - 1) // self.page_size

        # Ensure current_page stays within bounds
        self.current_page = max(0, min(self.current_page, total_pages - 1))

        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, total_games)

        # 1. Update the Slider position and range without triggering _on_slider_move
        self.page_slider.config(command="")
        self.page_slider.config(to=max(0, total_pages - 1))
        self.page_slider.set(self.current_page)
        self.page_slider.config(command=self._on_slider_move)

        # 2. Update Label and Button states
        self.lbl_page.config(text=f"Page {self.current_page + 1} of {total_pages}")
        self.btn_prev.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL if (self.current_page + 1) < total_pages else tk.DISABLED)

        # 3. Populate the Treeview
        page_items = self.game_data[start_idx:end_idx]
        for i, (file_path, offset, original_index) in enumerate(page_items):
            try:
                # Determine if the row is even or odd for the background color
                # i + 1 because the user sees page starting at 1
                row_tag = "odd_row" if i % 2 != 0 else "even_row"

                # Combine the row color tag with any metadata tags (file_path, offset, etc.)
                all_tags = (row_tag, file_path, offset, original_index)

                with open(file_path, encoding='utf-8', errors='ignore') as f:
                    f.seek(offset)
                    headers = chess.pgn.read_headers(f)
                    short_filename = os.path.basename(file_path)

                    self.tree.insert("", tk.END, values=(
                        headers.get("Date", "????.??.??"),
                        headers.get("White", "Unknown"),
                        headers.get("Black", "Unknown"),
                        headers.get("Result", "*"),
                        short_filename
                    ), tags=all_tags)  # Apply the tags here
            except Exception as e:
                print(f"Error loading game: {e}")

    def _next_page(self):
        """ Moves to the next page if available. """
        total_pages = (len(self.game_data) + self.page_size - 1) // self.page_size
        if (self.current_page + 1) < total_pages:
            self.current_page += 1
            self.refresh_page()

    def _prev_page(self):
        """ Moves to the previous page if available. """
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_page()

    def _sort_by(self, col):
        """ Sorts the entire dataset and returns to the first page. """
        ascending = self.sort_status[col]

        # Sort logic for the underlying data
        # Note: We need to peek at headers to sort by column index
        # For simplicity in this demo, we sort the stored game_data list
        # In a real app, you might want a cached list of headers for sorting
        self.game_data.sort(reverse=not ascending, key=lambda x: self._get_sort_key(x, col))

        self.sort_status[col] = not ascending
        self.current_page = 0  # Reset to first page after sort
        self.refresh_page()

    def _get_sort_key(self, data_item, col):
        # We need to read headers once to sort.
        # For performance, usually, you'd cache these headers in a list.
        path, offset, _ = data_item
        with open(path, encoding='utf-8', errors='ignore') as f:
            f.seek(offset)
            headers = chess.pgn.read_headers(f)
            val = headers.get(col.capitalize(), "")
            return val.lower()

    # The logic methods (identical to LibraryTab but directly on self.tree)
    def _select_all(self, event=None):
        self.tree.selection_set(self.tree.get_children())
        return "break"

    def _clear_selection(self, event=None):
        self.tree.selection_remove(self.tree.selection())
        return "break"

    def _invert_selection(self, event=None):
        all_items = self.tree.get_children()
        selected = self.tree.selection()
        new_sel = [i for i in all_items if i not in selected]
        self.tree.selection_set(new_sel)
        return "break"

    def _get_col_label(self, col):
        labels = {"date": "Date", "white": "White", "black": "Black",
                  "result": "Result", "file": "Source File"}
        return labels.get(col, col)

    def _load_games(self):
        try:
            for file_path, offset, original_index in self.game_data:
                with open(file_path, encoding='utf-8', errors='ignore') as f:
                    f.seek(offset)
                    headers = chess.pgn.read_headers(f)
                    short_filename = os.path.basename(file_path)

                    self.tree.insert("", tk.END, values=(
                        headers.get("Date", "????.??.??"),
                        headers.get("White", "Unknown"),
                        headers.get("Black", "Unknown"),
                        headers.get("Result", "*"),
                        short_filename
                    ), tags=(file_path, offset, original_index))  # Use the original index
        except Exception as e:
            print(f"Error: {e}")

    def _sort_by(self, col):
        """Sorts the table by the selected column"""
        # Get all data from treeview
        data = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]

        # Toggle sort order for next click
        ascending = self.sort_status[col]

        # Sort (case-insensitive for text)
        data.sort(reverse=not ascending, key=lambda x: x[0].lower())

        # Move items in the treeview to the new order
        for index, (val, item) in enumerate(data):
            self.tree.move(item, '', index)

        # Flip direction for next time
        self.sort_status[col] = not ascending

        # Update heading text to indicate direction (optional)
        for c in self.columns:
            prefix = ""
            if c == col:
                prefix = "↑ " if ascending else "↓ "
            self.tree.heading(c, text=prefix + self._get_col_label(c))

    def _save_all_games(self):
        """Saves the games in the order currently displayed in the table"""
        export_path = Path(PREFS["export_directory"]).expanduser()
        export_path.mkdir(parents=True, exist_ok=True)
        file_name = export_path / PREFS["export_filename"]

        # We use Treeview items because they determine the sort order
        items = self.tree.get_children()

        if not items:
            return

        try:
            count = 0
            with open(file_name, "w", encoding="utf-8") as export_file:
                for item in items:
                    # Get source information from Treeview row tags
                    file_path, offset = self.tree.item(item, "tags")

                    with open(file_path, encoding='utf-8', errors='ignore') as source_file:
                        source_file.seek(offset)
                        game = chess.pgn.read_game(source_file)
                        if game:
                            export_file.write(str(game) + "\n\n")
                            count += 1

            tk.messagebox.showinfo("Success", f"{count} games saved in the selected order:\n{file_name}")

        except Exception as e:
            tk.messagebox.showerror("Error", f"Save failed: {e}")

    def _setup_context_menu(self):
        """ Initializes the right-click menu for the game list. """
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Remove item", command=self._remove_item)
        self.context_menu.add_command(label="Remove all from this DB", command=self._remove_db)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Display Raw PGN", command=self._display_raw)
        self.context_menu.add_command(label="Open in Annotator", command=self._display_game)

    def _show_context_menu(self, event):
        """Displays the context menu on the selected row"""
        item = self.tree.identify_row(event.y)
        if item:
            if item not in self.tree.selection():
                self.tree.selection_set(item)

            # Show the menu
            try:
                self.context_menu.post(event.x_root, event.y_root)
                # Force menu to grab focus
                self.context_menu.focus_set()
            finally:
                # If menu loses focus (clicking outside), close it
                self.context_menu.bind("<FocusOut>", lambda e: self.context_menu.unpost())

    def _remove_item(self):
        """Removes the selected games from the list"""
        selected_items = self.tree.selection()
        for item in selected_items:
            self.tree.delete(item)

    def _display_game(self):
        """Displays the raw PGN text of the selected game in a new window."""
        selected = self.tree.selection()
        if not selected:
            return

        # Get data from tags
        tags = self.tree.item(selected[0], "tags")
        print("tags:", tags)
        file_path = tags[1]
        offset = tags[3]
        # Convert game_index to an integer!
        game_index = int(tags[3])

        # Create a new window for the annotator
        new_window = tk.Toplevel(self)
        new_window.title(f"Annotator - Game {game_index}")
        print(f"Call ChessEventViewer - Game {game_index}")

        # Call the app with the parameters
        app = ChessEventViewer(new_window,
                               file_path, 80, None, "", file_path,
                               "", "staunty", current_game_index=game_index)

    def _display_raw(self):
        """Displays the raw PGN text of the selected game in a new window."""
        selected = self.tree.selection()
        if not selected:
            return

        # Retrieve location data from the tags
        file_path, offset, _ = self.tree.item(selected[0], "tags")

        try:
            # 1. Read the game
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                f.seek(int(offset))
                game = chess.pgn.read_game(f)
                if game is None:
                    return
                pgn_text = str(game)

            # 2. Create a new window
            raw_win = tk.Toplevel(self)
            raw_win.title(f"Raw PGN - {game.headers.get('White', '???')} vs {game.headers.get('Black', '???')}")
            raw_win.geometry("600x500")

            # 3. Add a Text widget (with scrollbar)
            from tkinter import scrolledtext
            text_area = scrolledtext.ScrolledText(raw_win, wrap=tk.WORD, font=("Courier New", 11))
            text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # 4. Add the text and make it 'read-only'
            text_area.insert(tk.INSERT, pgn_text)
            text_area.configure(state=tk.DISABLED)

            # Optional: Close button
            ttk.Button(raw_win, text="Close", command=raw_win.destroy).pack(pady=5)

        except Exception as e:
            tk.messagebox.showerror("Error", f"Could not load raw data: {e}")

    def _remove_db(self):
        """Removes all games originating from the same source file"""
        selected_items = self.tree.selection()
        if not selected_items:
            return

        # Get the file path of the selected row (stored in tags)
        target_file, _, _ = self.tree.item(selected_items[0], "tags")

        # Loop through all rows in the table and remove those with the same path
        all_items = self.tree.get_children()
        count = 0
        for item in all_items:
            file_path, _, _ = self.tree.item(item, "tags")
            if file_path == target_file:
                self.tree.delete(item)
                count += 1

        # Optional: short message in the console or status bar
        print(f"Removed: {count} games from {os.path.basename(target_file)}")

    def _on_select(self, event):
        item = self.tree.selection()
        if not item:
            return

        # Retrieve the data from the tags
        tags = self.tree.item(item[0], "tags")
        print("tags:", tags)
        file_path = tags[1]
        offset = tags[3]
        # Convert the game_index to an integer!
        game_index = int(tags[3])
        if self.chess_annotator_app is None:

            # Create a new window for the annotator
            new_window = tk.Toplevel(self)
            new_window.title(f"Annotator - Game {game_index}")
            print(f"Call Annotator - Game {game_index}")
            SQUARE_SIZE = 50
            IMAGE_DIRECTORY = "Images/piece"
            piece_set = "staunty"
            asset_manager = PieceImageManager1(SQUARE_SIZE, IMAGE_DIRECTORY, piece_set)
            # Call the app with the parameters
            self.chess_annotator_app = ChessAnnotatorApp(
                new_window,
                file_path,  # pgn_game (full path)
                "",  # Must be available in parent
                hide_file_load=True,
                image_manager=asset_manager,
                square_size=SQUARE_SIZE,
                current_game_index=game_index,
                call_back=self.annotator_callback)
        else:
            self.chess_annotator_app.display_game_externally(file_path, game_index)

    def annotator_callback(self, param):
        print("return from annotator in db-app")
        self.chess_annotator_app = None


if __name__ == "__main__":
    app = GlobalLibraryBrowser()
    app.mainloop()