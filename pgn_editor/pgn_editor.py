import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from io import StringIO
import chess
import chess.pgn
import re # For simple PGN cleaning
import asyncio

# Required: pip install python-chess

class ChessAnnotatorApp:
    def __init__(self, master, pgn_game, engine_name, hide_file_load = False):
        print("parameters:",pgn_game, engine_name)
        self.master = master
        self.hide_file_load = hide_file_load
        master.title("PGN Chess Annotator")

        # --- Data Initialization ---
        self.all_games = []      # List of all chess.pgn.Game objects in the PGN file
        self.current_game_index = -1 # Index of the current game in all_games
        self.game = None         # The current chess.pgn.Game object
        self.board = None        # The current chess.Board object
        self.move_list = []      # List of all GameNode objects in the main variation
        self.current_move_index = -1 # Index in move_list. -1 = starting position
        self.meta_entries = {}   # Dictionary to store the Entry widgets for meta-tags
        self.game_menu = None    # Reference to the Game Menu for updating item states

        # Store button references for robust access
        self.insert_edit_comment_button = None
        self.manage_variations_button = None # New button reference
        self.delete_comment_button = None
        if engine_name is None or len(engine_name) == 0:
            self.ENGINE_PATH = "/home/user/Schaken/stockfish-python/Python-Easy-Chess-GUI/Engines/stockfish-ubuntu-x86-64-avx2"
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

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be3 e6 7. f3 Be7 8. Qd2 Qc7 9. O-O-O Nc6 10. g4 Bd7 11. h4 h6 12. Be2 Nxd4 13. Bxd4 e5 14. Be3 b5 15. a3 Rc8 16. g5 Nh5 17. Nd5 Qxc2+ 18. Qxc2 Rxc2+ 19. Kxc2 Ng3 (19... O-O-O 20. Nb4 Kb7 21. Nd5 Kc8) 20. Rhe1 Nxe2 21. Rxe2 hxg5 22. hxg5 Rh3 23. Rf2 Bd8 24. Rdd2 Be6 25. Nb4 a5 26. Na2 Kd7 27. Nc3 b4 28. Nd5 bxa3 29. bxa3 f5 30. gxf6 gxf6 31. Bb6 Rh8 32. Bxd8 Kxd8 33. Nxf6 Ke7 34. Nd5+ Kf7 35. f4 Rh3 36. fxe5+ Kg6 37. Rf6+ Kg5 38. Rxe6 dxe5 39. Rxe5+ Kg4 40. Nf6+ Kf4 41. Rxa5 1-0

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
        self._setup_header_frame(master)
        self._setup_main_columns(master)

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
        game_menu.add_separator()
        game_menu.add_command(label="Choose Game...", command=self._open_game_chooser)

        self.game_menu = game_menu

        # Bind shortcuts
        master.bind('<Control-Left>', lambda e: self.go_game(-1))
        master.bind('<Control-Right>', lambda e: self.go_game(1))

    # --- Game Chooser Logic ---

    def _open_game_chooser(self):
        """if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    pgn_content = f.read()
                self._load_game_from_content(pgn_content)
            except Exception as e:
                messagebox.showerror("Loading Error", f"Could not read the file: {e}")
        Opens a Toplevel dialog to choose a game from the all_games list.
        """
        if not self.all_games:
            messagebox.showinfo("Information", "No PGN games are currently loaded.")
            return

        dialog = tk.Toplevel(self.master)
        dialog.title("Choose Game")
        dialog.transient(self.master)
        dialog.grab_set()

        tk.Label(dialog, text="Select a game from the list:", font=('Arial', 10, 'bold')).pack(padx=10, pady=5)

        listbox_frame = tk.Frame(dialog, padx=10, pady=5)
        listbox_frame.pack(fill='both', expand=True)

        # Scrollbar and Listbox
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        game_listbox = tk.Listbox(
            listbox_frame,
            yscrollcommand=scrollbar.set,
            height=15,
            width=60,
            font=('Consolas', 10)
        )
        game_listbox.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.config(command=game_listbox.yview)

        # Populate the listbox
        for i, game in enumerate(self.all_games):
            white = game.headers.get("White", "???")
            black = game.headers.get("Black", "???")
            result = game.headers.get("Result", "*-*")
            event = game.headers.get("Event", "Untitled")

            list_item = f"Game {i+1}: {white} - {black} ({result}) | {event}"
            game_listbox.insert(tk.END, list_item)

        # Pre-select the current game
        if self.current_game_index != -1:
            game_listbox.selection_set(self.current_game_index)
            game_listbox.see(self.current_game_index)

        def select_game(event=None):
            """
            Switches to the selected game and closes the dialog.
            """
            selection = game_listbox.curselection()
            if selection:
                selected_index = selection[0]
                if selected_index != self.current_game_index:
                    self._switch_to_game(selected_index)
                dialog.destroy()
            else:
                messagebox.showwarning("Selection Error", "Please select a game from the list.")

        # Bind double-click to select action
        game_listbox.bind('<Double-Button-1>', select_game)

        # Buttons
        button_frame = tk.Frame(dialog, pady=10)
        button_frame.pack()

        tk.Button(button_frame, text="Select Game", command=select_game, width=15, bg='#d9ffc7').pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, width=15, bg='#ffe0e0').pack(side=tk.LEFT, padx=10)

        self.master.update_idletasks()
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        position_x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (dialog_width // 2)
        position_y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (dialog_height // 2)
        dialog.geometry(f'+{position_x}+{position_y}')

        self.master.wait_window(dialog)


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


    # --- File & Load Logic ---

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
                with open(filepath, 'r', encoding='utf-8') as f:
                    pgn_content = f.read()
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

            # Switch to the first game
            self._switch_to_game(0)

        except Exception as e:
            messagebox.showerror("Error", f"Error reading PGN: {e}")


    # --- UI Component Setup ---

    def _setup_header_frame(self, master):
        """
        Sets up the top section of the UI: Meta-tags, Navigation, and Commentary Controls.
        """
        header_frame = tk.Frame(master, bd=2, relief=tk.RAISED, padx=10, pady=5)
        header_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        # 1. Game Meta-Tags section (left in the header)
        meta_frame = tk.LabelFrame(header_frame, text="Game Meta-Tags", padx=5, pady=5)
        meta_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

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
        nav_comment_frame = tk.Frame(header_frame)
        nav_comment_frame.pack(side=tk.LEFT, padx=30, fill=tk.Y)

        # Current Move Notation
        tk.Label(nav_comment_frame, text="Current Move:", font=('Arial', 10, 'bold')).pack(pady=5)
        self.notation_label = tk.Label(nav_comment_frame, text="Starting Position", font=('Arial', 14, 'bold'), fg='blue')
        self.notation_label.pack(pady=5)

        # Navigation Buttons
        nav_buttons_frame = tk.Frame(nav_comment_frame)
        nav_buttons_frame.pack(pady=10)
        self.prev_button = tk.Button(nav_buttons_frame, text="<< Previous", command=self.go_back_move, width=10)
        self.prev_button.pack(side=tk.LEFT, padx=5)
        self.next_button = tk.Button(nav_buttons_frame, text="Next >>", command=self.go_forward_move, width=10)
        self.next_button.pack(side=tk.LEFT, padx=5)

        # 3. Commentary Controls section (right in the header)
        comment_frame = tk.LabelFrame(header_frame, text="Annotation Tools", padx=10, pady=5)
        comment_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=5)

        # --- NEW BUTTON FOR VARIATIONS ---
        self.manage_variations_button = tk.Button(comment_frame, text="Manage Variations", command=self._open_variation_manager, width=25, bg='#fff9c4')
        self.manage_variations_button.pack(pady=5)

        # Store button references directly for robust access
        self.insert_edit_comment_button = tk.Button(comment_frame, text="Insert/Edit Comment", command=self.manage_comment, width=25, bg='#d9e7ff')
        self.insert_edit_comment_button.pack(pady=5)

        self.delete_comment_button = tk.Button(comment_frame, text="Delete Commentary", command=lambda: self.manage_comment(delete=True), width=25, bg='#ffd9d9')
        self.delete_comment_button.pack(pady=5)

        # Display the current move's commentary
        tk.Label(comment_frame, text="Current Commentary:", font=('Arial', 9, 'bold')).pack(pady=5)
        self.comment_display = tk.Label(comment_frame, text="—", wraplength=250, justify=tk.LEFT, relief=tk.SUNKEN, padx=5, pady=5, height=3)
        self.comment_display.pack(fill=tk.X)

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

    def _setup_main_columns(self, master):
        """
        Sets up the two columns below the header: Chess Diagram and Move List.
        """
        main_frame = tk.Frame(master, padx=10, pady=10)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Column 1 (Left): Chess Diagram
        board_frame = tk.Frame(main_frame)
        board_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        tk.Label(board_frame, text="Chess Diagram", font=('Arial', 12, 'bold')).pack(pady=5)
        self.canvas = tk.Canvas(board_frame, width=400, height=400, bg='lightgray')
        self.canvas.pack(padx=5, pady=5)
        # Make the canvas responsive
        board_frame.bind('<Configure>', self._on_canvas_resize)


        # Column 2 (Right): Move List
        moves_frame = tk.Frame(main_frame)
        moves_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        tk.Label(moves_frame, text="Move List (Main Line)", font=('Arial', 12, 'bold')).pack(pady=5)

        scrollbar = tk.Scrollbar(moves_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.move_listbox = tk.Listbox(
            moves_frame,
            yscrollcommand=scrollbar.set,
            height=25,
            width=50, # Increased width to accommodate variations indicator
            font=('Consolas', 10)
        )
        self.move_listbox.pack(side=tk.LEFT, fill=tk.Y)
        scrollbar.config(command=self.move_listbox.yview)

        # Bind Listbox selection to board update
        self.move_listbox.bind('<<ListboxSelect>>', self._on_move_listbox_select)

    # --- State Update Logic ---

    def _populate_move_listbox(self):
        """
        Fills the Listbox with all moves, including any commentaries and variation indicators.
        """
        self.move_listbox.delete(0, tk.END)
        if not self.game:
            return

        # Start with a fresh board to calculate SAN notation correctly
        base_board = self.game.board()

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
            self.move_listbox.insert(tk.END, list_item)

    def _on_move_listbox_select(self, event):
        """
        Updates the status upon selecting a Listbox item.
        """
        selection = self.move_listbox.curselection()
        if not selection:
            # Allow clicking off the listbox to select the start position
            if self.current_move_index != -1:
                self.current_move_index = -1
                self.update_state()
            return

        selected_index = selection[0]
        if self.current_move_index != selected_index:
            self.current_move_index = selected_index
            self.update_state()


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
            self.comment_display.config(text="—")
            self.prev_button.config(state=tk.DISABLED)
            self.next_button.config(state=tk.DISABLED)
            if self.insert_edit_comment_button: self.insert_edit_comment_button.config(state=tk.DISABLED)
            if self.delete_comment_button: self.delete_comment_button.config(state=tk.DISABLED)
            if self.manage_variations_button: self.manage_variations_button.config(state=tk.DISABLED)
            self._update_game_navigation_state()
            return

        self.board = self._get_board_at_index(self.current_move_index)

        self.update_board_display()
        self.update_move_listbox_selection()
        self.update_move_notation()
        self.update_comment_display()
        self._update_game_navigation_state() # Update game navigation as well

        # Update move navigation button states
        self.prev_button.config(state=tk.NORMAL if self.current_move_index > -1 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if self.current_move_index < len(self.move_list) - 1 else tk.DISABLED)

        # Annotation buttons are active if a node is selected (current_move_index >= -1)
        annotation_state = tk.NORMAL if self.current_move_index >= -1 else tk.DISABLED

        if self.insert_edit_comment_button:
            self.insert_edit_comment_button.config(state=annotation_state)
        if self.delete_comment_button:
            self.delete_comment_button.config(state=annotation_state)
        if self.manage_variations_button:
            self.manage_variations_button.config(state=annotation_state)


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
        self.comment_display.config(text=comment)

    def update_move_listbox_selection(self):
        """
        Synchronizes the selection in the Listbox.
        """
        self.move_listbox.selection_clear(0, tk.END)
        if self.current_move_index != -1:
            self.move_listbox.selection_set(self.current_move_index)
            self.move_listbox.see(self.current_move_index)

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

        list_item = f"{prefix}{san_move}{comment_text}{variation_indicator}"

        # Replace the old item
        self.move_listbox.delete(index)
        self.move_listbox.insert(index, list_item)
        self.update_move_listbox_selection() # Restore selection

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
            logger.critical(errormsg)
            raise
        except PermissionError:
            errormsg = "Engine '{}' could not be executed. Aborting...".format(
                enginepath)
            logger.critical(errormsg)
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
        tk.Label(self.master, text="Analyzing... Please wait...", fg="red").pack(side=tk.BOTTOM, fill=tk.X)#, tags="engine_status"
        self.master.update()

        suggestions = asyncio.run(self._get_engine_suggestions(
            current_board,
            num_moves=self.ENGINE_MULTI_PV,
            depth=self.ENGINE_DEPTH
        ))

        #self.master.nametowidget('.').delete("engine_status") # Remove temporary label

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

                # 5. Update UI
                if self.current_move_index != -1:
                    self.update_listbox_item(self.current_move_index)
                _populate_variations()

                messagebox.showinfo("Success", f"Variation starting with {selected_sug['move_san']} added successfully.")

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
        current_node = self._get_current_node()
        if not current_node:
            messagebox.showinfo("Information", "Please select a move or the starting position to manage variations.")
            return

        dialog = tk.Toplevel(self.master)
        dialog.title(f"Manage Variations for: {self.notation_label.cget('text')}")
        dialog.transient(self.master)
        dialog.grab_set()

        tk.Label(dialog, text="Select a variation to edit/delete:", font=('Arial', 10, 'bold')).pack(padx=10, pady=5)

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
            current_node.promote_to_main(variation_node)
            previous_current_move_index = self.current_move_index
            self.move_list = []
            node = self.game
            while node.variations:
                # Always follow the main (first) variation
                node = node.variation(0)
                self.move_list.append(node)

            self._populate_move_listbox()
            self.current_move_index = previous_current_move_index
            self.update_state()


        def _add_new_variation():
            """Opens dialog to add a new variation."""
            self._open_engine_suggestion_dialog(_populate_variations)
            return
            new_pgn = simpledialog.askstring(
                "Add New Variation",
                "Enter the PGN sequence for the new variation (starting with the first move, e.g., 'Bd3 Nc6'):",
                parent=dialog
            )

            if new_pgn:
                try:
                    # Create a board reflecting the position *before* the variation starts
                    temp_board = current_node.board()

                    # Read the PGN sequence starting from the current position
                    # We pass the board state to ensure correct SAN parsing
                    new_game = chess.pgn.read_game(StringIO(new_pgn), board=temp_board)

                    if new_game is None or not new_game.variations:
                        raise ValueError("Could not parse valid move sequence.")

                    # Add the new variation (it should have one variation)
                    # FIX: Use the corrected function signature: add_variation(node)
                    current_node.add_variation(new_game.variations[0])

                    _populate_variations()
                    if self.current_move_index != -1:
                        self.update_listbox_item(self.current_move_index) # Update indicator
                    messagebox.showinfo("Success", "New variation added successfully.")

                except Exception as e:
                    messagebox.showerror("Error", f"Failed to parse or add variation. Check PGN format. Error: {e}")


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

        square_size = board_size / 8
        colors = ("#F0D9B5", "#B58863")  # Light and dark square colors

        # Unicode pieces (White: Uppercase, Black: Lowercase)
        piece_map = {
            'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
        }

        # Draw squares and pieces
        for row in range(8):
            for col in range(8):
                x1 = col * square_size
                y1 = row * square_size
                x2 = x1 + square_size
                y2 = y1 + square_size

                # Square color
                color_index = (row + col) % 2
                fill_color = colors[color_index]
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, tags="square")

                # Algebraic notation (for the border)
                file_char = chr(ord('a') + col)
                rank_char = str(8 - row)

                if col == 0:
                    self.canvas.create_text(x1 + 3, y1 + 3, text=rank_char, anchor="nw", font=('Arial', 8), fill=colors[1 - color_index])
                if row == 7:
                    self.canvas.create_text(x2 - 3, y2 - 3, text=file_char, anchor="se", font=('Arial', 8), fill=colors[1 - color_index])

                # Place the piece
                square_index = chess.square(col, 7 - row)
                piece = self.board.piece_at(square_index)

                if piece:
                    piece_char = piece_map.get(piece.symbol())
                    self.canvas.create_text(
                        x1 + square_size / 2,
                        y1 + square_size / 2,
                        text=piece_char,
                        font=('Arial', int(square_size * 0.7), 'bold'),
                        fill='black',
                        tags="piece"
                    )

        # Highlight the last move
        if self.current_move_index >= 0:
            last_move = self.move_list[self.current_move_index].move
            from_sq = last_move.from_square
            to_sq = last_move.to_square

            def get_coords(sq):
                # Helper to get GUI coordinates
                col = chess.square_file(sq)
                row = 7 - chess.square_rank(sq)
                x1 = col * square_size
                y1 = row * square_size
                x2 = x1 + square_size
                y2 = y1 + square_size
                return x1, y1, x2, y2

            # Highlight the 'from' and 'to' squares
            for sq in [from_sq, to_sq]:
                x1, y1, x2, y2 = get_coords(sq)
                self.canvas.create_rectangle(x1, y1, x2, y2, fill='#ffe066', stipple='gray50', tags="highlight")

            # Ensure pieces are drawn above the highlights
            self.canvas.tag_raise("piece")
            self.canvas.tag_raise("highlight", "square")


# Main execution block
if __name__ == "__main__":
    root = tk.Tk()
    app = ChessAnnotatorApp(root)
    root.mainloop()
