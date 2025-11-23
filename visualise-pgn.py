# This program requires the 'python-chess' library.
# Installation: pip install python-chess
import os
import tkinter as tk
from tkinter import font
import chess
import chess.pgn
import io
import re
# The Pillow (PIL) library is required to robustly load PNGs in Tkinter.
from PIL import Image, ImageTk

# --- PGN DATA FOR DEMONSTRATION ---
PGN_WITH_BLUNDERS = """
[Event "13th Norway Chess 2025"]
[Site "Stavanger NOR"]
[Date "2025.05.29"]
[Round "4.1"]
[White "Carlsen,M"]
[Black "Erigaisi,Arjun"]
[Result "1-0"]
[WhiteTitle "GM"]
[BlackTitle "GM"]
[WhiteElo "2837"]
[BlackElo "2782"]
[ECO "A36"]
[Opening "English Opening: Symmetrical Variation, Symmetrical Variation"]
[Variation "ultra-symmetrical variation"]
[WhiteFideId "1503014"]
[BlackFideId "35009192"]
[EventDate "2025.05.26"]
[WhiteACPL "8"]
[BlackACPL "-131"]
[Annotator "Stockfish 17"]

{ Stockfish 17 } 1. c4 c5 2. g3 g6 3. Bg2 Bg7 4. Nc3 Nc6 { A36 English Opening:
Symmetrical Variation, Symmetrical Variation } 5. Rb1 $6 { +0.16 } ( 5. e3 e6 6.
Nge2 Nge7 7. d4 cxd4 8. exd4 d5 9. cxd5 Nxd5 { +0.15/21 } ) 5... Nf6 6. a3 a5 7.
d3 e6 $9 { +0.31 } ( 7... O-O 8. Nh3 Rb8 9. Nf4 Ne8 10. h4 b6 11. Nb5 h6 12. Bd2
{ +0.06/24 } ) 8. Nf3 O-O 9. Be3 $6 { +0.15 } ( 9. Bf4 d5 10. O-O Re8 11. cxd5
Nxd5 12. Bg5 Qc7 13. Qd2 b6 { +0.30/20 } ) 9... Qe7 $9 { +0.46 } ( 9... b6 10.
d4 d6 11. O-O Bb7 12. d5 exd5 13. cxd5 Ne7 14. Bg5 { +0.21/23 } ) 10. Na4 $6 {
+0.16 } ( 10. Qc1 d6 11. Bg5 Qd7 12. Bh6 b6 13. h4 Bb7 14. h5 Nd4 { +0.47/19 } )
10... d6 11. O-O Rb8 12. d4 cxd4 13. Nxd4 Nxd4 14. Bxd4 b5 15. cxb5 Rxb5 16. Nc3
$6 { +0.16 } ( 16. b4 axb4 17. axb4 Nd5 18. Bxg7 Kxg7 19. Qd4+ Qf6 20. Rfd1 Qxd4
{ +0.27/20 } ) 16... Rb8 17. Qa4 Bb7 18. Bxb7 Qxb7 19. Qxa5 e5 20. Be3 d5 21.
Bg5 d4 22. Bxf6 Bxf6 23. Nd5 Bg5 24. Nb4 Bd2 25. Qxe5 Bxb4 26. axb4 Qxb4 27.
Rfd1 Rfe8 28. Qf4 $6 { +0.17 } ( 28. Qf6 Re6 29. Qf4 Rxe2 30. Rxd4 Qb3 31. Qf6
Ree8 32. Rd2 Rb6 { +0.20/23 } ) 28... Rxe2 29. Rxd4 Qb7 $9 { +0.37 } ( 29... Qb3
30. Rd7 Rbe8 31. h4 Qe6 32. Rdd1 Re4 33. Qf3 Rb4 34. h5 { +0.25/21 } ) 30. Qf6
Re6 $9 { +1.42 } ( 30... h5 31. b4 Rbe8 32. Rd8 Rxd8 33. Qxd8+ Kh7 34. Qd3 Re4
35. b5 { +0.37/24 } ) 31. Rd8+ Rxd8 32. Qxd8+ Kg7 33. Qd4+ Kg8 34. b4 h5 $9 {
+1.39 } ( 34... Qb8 35. Rd1 Qe8 36. h4 h5 37. Qb2 Kh7 38. b5 Re2 39. Qb3 {
+1.35/23 } ) 35. b5 Rb6 $9 { +2.70 } ( 35... Re4 36. Qd8+ Kh7 37. h4 Re2 38. Qd4
Re4 39. Qb2 Qb6 40. Rc1 { +1.38/26 } ) 36. Re1 Qb8 37. Re8+ Qxe8 38. Qxb6 Qe1+
39. Kg2 Qe4+ 40. Kf1 Qd3+ $9 { +2.82 } ( 40... Qc4+ 41. Ke1 Qb4+ 42. Ke2 h4 43.
Qc6 Qb2+ 44. Kf3 h3 45. b6 { +2.58/23 } ) 41. Ke1 Qc3+ $9 { +2.77 } ( 41... h4
42. gxh4 Qc3+ 43. Ke2 Qc4+ 44. Kd2 Qb4+ 45. Kd3 Kh7 46. h5 { +2.54/21 } ) 42.
Ke2 Qc2+ $9 { +3.01 } ( 42... h4 43. gxh4 Qc4+ 44. Kd2 Kh7 45. Ke3 Qxh4 46. Qc5
Qxh2 47. b6 { +2.62/20 } ) 43. Ke3 Qc3+ $9 { +3.28 } ( 43... Qb3+ 44. Kd4 h4 45.
gxh4 Qa2 46. Ke5 Qc4 47. Kd6 Qxh4 48. Kc6 { +2.81/24 } ) 44. Ke4 Qc4+ 45. Ke5
Kg7 $9 { +3.77 } ( 45... h4 46. Kd6 Qd3+ 47. Kc7 Qf5 48. gxh4 Kh7 49. Kb7 Qd7+
50. Kb8 { +2.99/25 } ) 46. h4 Qd3 $9 { +4.07 } ( 46... Kh7 47. Kd6 Qe6+ 48. Kc7
Qe7+ 49. Kc8 Qe8+ 50. Kb7 g5 51. hxg5 { +3.46/23 } ) 47. Qc5 Qf5+ $9 { +5.94 } (
47... g5 48. hxg5 Qd2 49. Ke4 Qe2+ 50. Kd5 Qe6+ 51. Kd4 Qa2 52. Ke3 { +3.82/23 } )
48. Kd6 1-0


"""


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
                r'\s*([#]?[-+]?\d+\.?\d*)(?:/\d+)?\s*|\[%eval\s*([#]?[-]?\d+\.?\d*)\]|\s*\([^\)]*\)',
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

def get_all_significant_blunders(pgn_string):
    """
    Identifies ALL moves that caused a significant loss in advantage (> 50 cp).
    """
    pgn_io = io.StringIO(pgn_string)
    game = chess.pgn.read_game(pgn_io)

    if not game:
        print("Error: Could not read chess game from PGN string.")
        return []

    blunders = []
    board = game.board()
    prev_eval_cp = 0
    # List of ALL moves, including the move that caused the blunder
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

        # --- BLUNDER CALCULATION ---
        if eval_after_cp is not None:
            if player_who_moved == chess.WHITE:
                # Loss of advantage for White is (Previous Eval - New Eval)
                blunder_score = eval_before_cp - eval_after_cp
                player_str = "White"
            else:
                # Loss of advantage for Black is (New Eval - Previous Eval)
                blunder_score = eval_after_cp - eval_before_cp
                player_str = "Black"

            # If the blunder is significant (loss of more than 50 centipawns)
            if blunder_score > 0: # KEEPING THE '0' AS PER USER INSTRUCTION
                blunders.append({
                    'score': blunder_score,
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
            return blunders

        if eval_after_cp is not None:
            # For the next move, the 'eval_after' of this move becomes the 'prev_eval'
            prev_eval_cp = eval_after_cp

    return blunders


def select_key_positions(all_blunders):
    """
    Selects the blunders based on the new logic:
    1. Biggest blunder from each of the 3 equal parts of the game.
    2. Top 3 of the remaining blunders (globally).
    """
    if not all_blunders:
        return []

    # Determine the total number of half-moves (including the last move in the blunder list)
    total_half_moves = all_blunders[-1]['full_move_history'][-1]['full_move_index'] + 1

    # Use a set to prevent selecting the same blunder twice
    selected_indices = set()
    selected_blunders = []

    # 1. Divide the game into 3 (almost) equal parts
    part_size = total_half_moves // 3

    # Determine the ranges based on the 0-based move index
    ranges = [
        (0, part_size),  # Part 1 (Opening/Early Middlegame)
        (part_size, 2 * part_size),  # Part 2 (Middlegame)
        (2 * part_size, total_half_moves)  # Part 3 (Late Middlegame/Endgame)
    ]

    print(f"Total half-moves: {total_half_moves}. Part size: {part_size}.")

    # Select the biggest blunder in each part
    for part_num, (start_index, end_index) in enumerate(ranges):
        best_in_part = None
        max_score = -1

        for blunder in all_blunders:
            move_idx = blunder['move_index']

            # Check if the move falls within the current range
            if start_index <= move_idx < end_index:
                if blunder['score'] > max_score and move_idx not in selected_indices:
                    max_score = blunder['score']
                    best_in_part = blunder

        if best_in_part:
            best_in_part['source'] = f"Biggest Blunder in Part {part_num + 1}"
            selected_blunders.append(best_in_part)
            selected_indices.add(best_in_part['move_index'])

    # 2. Select the top 3 of the remaining blunders
    remaining_blunders = sorted(
        [b for b in all_blunders if b['move_index'] not in selected_indices],
        key=lambda x: x['score'],
        reverse=True
    )

    # Add the top 3 to the selection
    for i in range(min(3, len(remaining_blunders))):
        remaining_blunders[i]['source'] = f"Global Top {i + 1} (Remaining)"
        selected_blunders.append(remaining_blunders[i])
        selected_indices.add(remaining_blunders[i]['move_index'])

    # Sort the selected blunders chronologically for display
    selected_blunders.sort(key=lambda x: x['move_index'])

    return selected_blunders

# --- TKINTER CLASS ---

class ChessBlunderViewer:
    """
    Tkinter application to display the top blunders from an analyzed PGN.
    """

    def __init__(self, master, pgn_string, image_dir_path):
        self.master = master
        # ADJUST THIS PATH to the location of your directory 'pgn-visualiser/Images/60'

        self.image_dir_path = image_dir_path

        self.piece_images = {}  # Crucial: here we store the loaded PhotoImage objects

        # Mapping from chess.Piece.symbol() to the filename prefix
        self.piece_map = {
            'K': 'wK', 'Q': 'wQ', 'R': 'wR', 'B': 'wB', 'N': 'wN', 'P': 'wP',
            'k': 'bK', 'q': 'bQ', 'r': 'bR', 'b': 'bB', 'n': 'bN', 'p': 'bP',
        }

        # Perform the advanced analysis
        print("Starting full PGN analysis...")
        all_blunders = get_all_significant_blunders(pgn_string)
        print(f"Full analysis complete. {len(all_blunders)} significant blunders found (> 50 cp loss).")

        self.sorted_blunders = select_key_positions(all_blunders)
        self.num_blunders = len(self.sorted_blunders)

        master.title(f"Chess Game Analysis: {self.num_blunders} Critical Positions Selected")

        self.square_size = 60
        self.board_size = self.square_size * 8

        self.color_light = "#F0D9B5"
        self.color_dark = "#B58863"
        self.piece_font = font.Font(family="Arial", size=int(self.square_size * 0.5), weight="bold")

        # --- UI SETUP ---
        main_frame = tk.Frame(master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.blunder_canvas = tk.Canvas(main_frame)
        self.blunder_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=self.blunder_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.blunder_canvas.configure(yscrollcommand=scrollbar.set)
        # Configure scroll region when the canvas size changes
        self.blunder_canvas.bind('<Configure>',
                                 lambda e: self.blunder_canvas.configure(scrollregion=self.blunder_canvas.bbox("all")))

        self.content_frame = tk.Frame(self.blunder_canvas)
        self.blunder_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        self._load_piece_images()

        self.draw_blunder_diagrams()

    def _load_piece_images(self):
        """
        Loads and resizes the PNG images and saves them as ImageTk.PhotoImage objects.
        This is essential to prevent garbage collection in Tkinter.
        """
        try:
            for symbol, filename_prefix in self.piece_map.items():
                # Assemble the full path
                image_path = os.path.join(self.image_dir_path, f"{filename_prefix}.png")

                # 1. Load the image using PIL (Pillow)
                img = Image.open(image_path)

                # 2. Adjust the size to the size of a square
                img = img.resize((self.square_size, self.square_size), Image.Resampling.LANCZOS)

                # 3. Convert to a Tkinter-compatible format and save
                self.piece_images[symbol] = ImageTk.PhotoImage(img)

            print(f"Chess images successfully loaded from: {self.image_dir_path}")

        except FileNotFoundError:
            print(f"Error: The directory or files were not found at {self.image_dir_path}.")
            print("Make sure the path is correct and that the filenames are correct (wK.png, bQ.png, etc.).")
            print("Also check if you have installed the Pillow (PIL) library (pip install Pillow).")
        except Exception as e:
            print(f"An unexpected error occurred while loading the images: {e}")

    def draw_board(self):
        """Draws the chessboard (only the squares)."""
        color1 = "#D18B47"  # Light brown
        color2 = "#FFCE9E"  # Beige

        for r in range(8):
            for c in range(8):
                x1 = c * self.square_size
                y1 = r * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                # Swap colors
                color = color1 if (r + c) % 2 == 0 else color2
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, tags="square")

    # THIS IS THE MODIFIED FUNCTION:
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
                if symbol in self.piece_images:
                    piece_img = self.piece_images[symbol]

                    # 3. Draw the image in the center of the square
                    canvas.create_image(
                        x, y,
                        image=piece_img,
                        tags="piece"  # Use tags for easy removal/movement later
                    )
                # If the image is not loaded, the piece is skipped.
    def draw_blunder_diagram(self, parent_frame, blunder_data, pgn_snippet_text, index):
        """
        Draws one block with a diagram in column 0 and the cumulative PGN history in column 1.
        """

        # --- JOINT CONTAINER FRAME ---
        blunder_row_frame = tk.Frame(parent_frame, padx=20, pady=15, bd=1, relief=tk.SUNKEN)
        blunder_row_frame.pack(fill="x", expand=True)  # Use pack for the rows

        # --- COLUMN 0: DIAGRAM & INFO (Left) ---
        title = f"Position {index + 1}: {blunder_data.get('source', 'Blunder')} - {blunder_data['move_text']}"
        diagram_block = tk.LabelFrame(blunder_row_frame,
                                      text=title,
                                      padx=10, pady=10, font=("Helvetica", 12, "bold"), bd=2, relief=tk.GROOVE)
        diagram_block.pack(side=tk.LEFT, padx=10, pady=5, fill="y", anchor="n")

        # 1. Info Label
        info_text = (
            f"Move that caused the blunder: {blunder_data['move_text']}\n"
            f"Loss: {blunder_data['score'] / 100.0:.2f} P\n"
            f"Eval BEFORE move: {blunder_data['eval_before']:.2f} | Eval AFTER move: {blunder_data['eval_after']:.2f}"
        )
        tk.Label(diagram_block, text=info_text, justify=tk.LEFT, pady=5).pack(anchor="w")

        # 2. Canvas for the board
        board_canvas = tk.Canvas(diagram_block, width=self.board_size, height=self.board_size,
                                 borderwidth=0, highlightthickness=1, highlightbackground="black")
        board_canvas.pack(pady=10)

        # Initialize the board with the FEN BEFORE the blunder
        board = chess.Board(blunder_data['fen'])

        # Draw the board
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

        # Mark the starting square of the blundering move
        try:
            # We need to parse the FEN, add the move, and then determine the from_square.
            # However, the FEN is the position *BEFORE* the move.
            # We use board.parse_san on the current board state (FEN BEFORE the move)
            move_san = blunder_data['move_text'].split()[-1].strip('.')
            move_to_highlight = board.parse_san(move_san)
            from_square = move_to_highlight.from_square

            from_rank = 7 - chess.square_rank(from_square)
            from_file = chess.square_file(from_square)

            x1 = from_file * self.square_size
            y1 = from_rank * self.square_size

            # Add a yellow highlight to the starting square
            board_canvas.create_rectangle(x1, y1, x1 + self.square_size, y1 + self.square_size,
                                          outline="#FFC300", width=4, tags="highlight")
        except Exception:
            pass

        # --- COLUMN 1: PGN SNIPPET (Right) ---
        pgn_block = tk.LabelFrame(blunder_row_frame, text="PGN Moves since the last critical position",
                                  padx=10, pady=10, font=("Helvetica", 12, "bold"), bd=2, relief=tk.GROOVE)
        pgn_block.pack(side=tk.RIGHT, padx=10, pady=5, fill=tk.BOTH, expand=True)

        # Text widget for the PGN text
        pgn_text_widget = tk.Text(pgn_block, height=14, width=50, wrap=tk.WORD, font=("Consolas", 10))

        # Insert the cumulative text
        pgn_text_widget.insert(tk.END, pgn_snippet_text)
        pgn_text_widget.config(state=tk.DISABLED)

        pgn_text_widget.pack(fill=tk.BOTH, expand=True)

        pgn_scrollbar = tk.Scrollbar(pgn_block, command=pgn_text_widget.yview)
        pgn_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        pgn_text_widget.config(yscrollcommand=pgn_scrollbar.set)

    def draw_blunder_diagrams(self):
        """Draws all selected diagrams in chronological order."""
        if not self.sorted_blunders:
            tk.Label(self.content_frame, text="No significant blunders (>= 50 cp) found in the PGN data.",
                     pady=50, padx=20).pack()
            return

        # The index of the last move shown in the PREVIOUS block
        last_move_index = -1

        for i, blunder in enumerate(self.sorted_blunders):
            # The blundering move is the last move in the full_move_history.
            # The index of the move that caused the blunder is stored in 'move_index'.
            current_move_index = blunder['move_index']

            # Select only the moves that are NEW since the last displayed blunder
            moves_to_display = blunder['full_move_history'][last_move_index + 1: current_move_index + 1]

            # Format the PGN for display
            pgn_snippet = _format_pgn_history(moves_to_display)

            # Draw the diagram and the PGN
            self.draw_blunder_diagram(self.content_frame, blunder, pgn_snippet, i)

            # Update the counter for the next iteration
            last_move_index = current_move_index

        # Ensure the scroll region is updated
        self.content_frame.update_idletasks()
        self.blunder_canvas.config(scrollregion=self.blunder_canvas.bbox("all"))

# --- HOOFD EXECUTIE ---

if __name__ == "__main__":
    try:
        root = tk.Tk()
        # Set the initial size to 1200x800
        root.geometry("1200x800")
        IMAGE_DIRECTORY = "Images/60"
        app = ChessBlunderViewer(root, PGN_WITH_BLUNDERS, IMAGE_DIRECTORY)
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