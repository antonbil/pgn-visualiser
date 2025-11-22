# Dit programma vereist de 'python-chess' bibliotheek.
# Installatie: pip install python-chess

import tkinter as tk
from tkinter import font
import chess
import chess.pgn
import io
import re

# --- PGN DATA VOOR DEMONSTRATIE ---
PGN_WITH_BLUNDERS = """
[Event "13th Norway Chess 2025"]
[Site "Stavanger NOR"]
[Date "2025.05.26"]
[Round "1.3"]
[White "Carlsen,M"]
[Black "Gukesh,D"]
[Result "1-0"]
[WhiteTitle "GM"]
[BlackTitle "GM"]
[WhiteElo "2837"]
[BlackElo "2787"]
[ECO "D01"]
[Opening "Queen's Pawn Game: Chigorin Variation"]
[WhiteFideId "1503014"]
[BlackFideId "46616543"]
[EventDate "2025.05.26"]
[WhiteACPL "1"]
[BlackACPL "-107"]
[Annotator "Stockfish 17"]

{ Stockfish 17 } 1. d4 Nf6 2. Nc3 d5 { D01 Queen's Pawn Game: Chigorin Variation }
3. Bf4 c5 4. e3 Bg4 5. Be2 { +0.00 } ( 5. f3 Bd7 6. Nb5 Bxb5 7. Bxb5+ Nc6 8. c3
e6 9. Ne2 Be7 { +0.02/23 } ) 5... Bxe2 6. Ncxe2 $9 { -0.18 } ( 6. Qxe2 a6 {
-0.01/21 } ) 6... Nc6 { -0.08 } ( 6... e6 7. Nf3 Be7 8. O-O O-O 9. c3 Nbd7 10.
a4 a5 11. h3 { -0.16/23 } ) 7. Nf3 e6 8. c3 Be7 9. Ng3 $9 { -0.18 } ( 9. dxc5
Bxc5 10. Ned4 Qb6 11. O-O O-O 12. Nxc6 Qxc6 13. Qe2 Ne4 { -0.17/20 } ) 9... O-O
10. Qe2 h6 $6 { -0.18 } ( 10... Nd7 11. h4 Re8 12. Rd1 Rc8 13. a3 a6 14. Nh5
cxd4 15. exd4 { -0.23/18 } ) 11. Rd1 $9 { -0.23 } ( 11. Ne5 { -0.18/17 } ) 11...
Qa5 12. a3 Rfd8 $6 { -0.17 } ( 12... a6 13. O-O Qb5 14. Qc2 Rac8 15. Rfe1 Rfd8
16. h3 Na5 17. Ne5 { -0.25/20 } ) 13. h4 $9 { -0.24 } ( 13. Ne5 Nxe5 14. Bxe5
Nd7 15. f4 Qa6 16. Qg4 g6 17. h4 Rac8 { -0.21/20 } ) 13... Qa4 14. Ne5 Nxe5 15.
Bxe5 Nd7 16. Bf4 Qa6 { +0.07 } ( 16... Rac8 17. Nh5 Bf8 18. O-O g6 19. Ng3 Bg7
20. Rfe1 Re8 21. e4 { -0.23/22 } ) 17. Qf3 $9 { -0.21 } ( 17. Qxa6 bxa6 18. Kd2
Nb6 19. Kc2 Rd7 20. h5 Rb7 21. Ra1 f6 { +0.10/24 } ) 17... Bd6 { +0.06 } ( 17...
Bf8 { -0.24/20 } ) 18. Nh5 Bxf4 19. Qxf4 e5 $9 { +0.32 } ( 19... cxd4 20. Qxd4
e5 21. Qxd5 Rac8 22. Qd3 Qxd3 23. Rxd3 Nc5 24. Rxd8+ { +0.09/19 } ) 20. Qg3 $6 {
+0.17 } ( 20. dxe5 Qg6 21. g4 Re8 22. Rxd5 Nxe5 23. O-O Nxg4 24. Ng3 Nf6 {
+0.28/25 } ) 20... Qg6 21. Qxg6 fxg6 22. Ng3 exd4 $9 { +0.26 } ( 22... Rac8 23.
Ne2 Rc6 24. O-O cxd4 25. cxd4 Rc2 26. Nc3 Rxb2 27. Nxd5 { +0.22/24 } ) 23. cxd4
c4 24. Ne2 b5 25. Nc3 $6 { +0.19 } ( 25. Rb1 Nf6 26. f3 a5 27. b3 b4 28. Kd2
Rab8 29. axb4 axb4 { +0.26/22 } ) 25... Nf6 26. Rb1 Rab8 $9 { +0.27 } ( 26...
Rdb8 27. b4 a5 28. f3 axb4 29. axb4 Ra3 30. Kd2 Rba8 31. Kc2 { +0.16/25 } ) 27.
f3 a5 28. b4 cxb3 29. Rxb3 b4 30. axb4 Rxb4 31. Ra3 { +0.10 } ( 31. Rxb4 axb4
32. Ne2 g5 33. hxg5 hxg5 34. Kd2 Ra8 35. Rb1 Ra4 { +0.19/24 } ) 31... Re8 32.
Kd2 { +0.00 } ( 32. Kf2 Rb2+ 33. Ne2 Ng4+ 34. fxg4 Rf8+ 35. Kg3 Rxe2 36. Rc1
Rff2 { +0.10/25 } ) 32... Rb2+ 33. Kd3 Rxg2 34. Rxa5 Rg3 35. Rf1 g5 36. hxg5
Rxg5 37. Rfa1 h5 38. Ra8 Rxa8 39. Rxa8+ Kh7 40. e4 dxe4+ 41. fxe4 h4 42. e5 h3
43. exf6 h2 44. f7 Rg3+ 45. Kd2 h1=Q 46. f8=Q Qh6+ $9 { +4.08 } ( 46... Rg2+ 47.
Kd3 Rg3+ 48. Kc2 Qg2+ 49. Kb3 Qd5+ 50. Kb2 Qg2+ { +0.00/45 } ) 47. Kc2 Qg6+ $9 {
+4.23 } ( 47... Rg2+ 48. Kb3 Qe6+ 49. Ka3 Rc2 50. Qc5 Rh2 51. d5 Qe1 52. Kb3 {
+3.79/17 } ) 48. Kb2 Qb6+ 49. Ka2 Rg2+ $9 { +4.35 } ( 49... Qb7 50. Qh8+ Kg6 51.
Qe8+ Kh6 52. Qe6+ Kh7 53. Qe4+ Qxe4 54. Nxe4 { +3.74/19 } ) 50. Ka3 Qb2+ $9 {
+6.51 } ( 50... Qc6 51. Qf5+ Rg6 52. Qh3+ Rh6 53. Qd3+ Rg6 54. Ra5 Kg8 55. Kb3 {
+4.20/15 } ) 51. Ka4 Qxc3 $9 { Mate in 13 } ( 51... Qc2+ 52. Kb4 Qb2+ 53. Kc4
Rf2 54. Qh8+ Kg6 55. Ra7 Rf7 56. Qe8 { +5.86/16 } ) 52. Qh8+ Kg6 53. Ra6+ Kf5
54. Qf8+ Ke4 $9 { Mate in 7 } ( 54... Kg4 55. Rg6+ Kh5 56. Qf5+ Kh4 57. Qe4+ Kh5
58. Rxg2 Qc4+ 59. Ka5 Qc3+ 60. Kb5 Qb3+ 61. Kc6 Qa4+ 62. Kd6 Qb4+ 63. Kd7 Qb5+
64. Ke7 Qb4+ 65. Kf7 Qc4+ 66. Kf8 Qb4+ 67. Qe7 Qb8+ 68. Qe8+ Qxe8+ 69. Kxe8 g5
70. Kf7 Kh4 71. Ke6 g4 72. Kf5 g3 73. Kf4 Kh3 74. Rxg3+ Kh2 75. Rg5 Kh3 76. Rg4
Kh2 77. d5 Kh3 78. d6 Kh2 79. d7 Kh3 80. d8=Q Kh2 81. Qh4# ) 55. Re6+ 1-0
"""


# --- UTILITY FUNCTIES VOOR EVALUATIE EN PGN ---

def get_cp_from_comment(comment):
    """
    Extraheert de centipawn-waarde uit de PGN-commentaar.
    """
    if not comment:
        return None
    try:
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
        # Fout bij parsen, negeer deze comment
        return None


def _format_pgn_history(move_list):
    """
    Formateert een lijst van zet-data in een multi-line PGN snippet voor weergave.
    """
    if not move_list:
        return "Startpositie (eerste zet van de partij)."

    output = []
    current_line = ""

    for move in move_list:
        move_number = move['move_number']
        move_san = move['san']
        player = move['player']

        if player == chess.WHITE:
            # Start met zetnummer voor Wit
            if current_line:
                output.append(current_line.strip())
            current_line = f"{move_number}. {move_san}"
        else:
            # Voeg de zet van Zwart toe
            current_line += f" {move_san}"

        # Voeg de engine commentaar (evaluatie) toe
        if move.get('comment'):
            # Verwijder de evaluatie uit de commentaar om deze leesbaarder te maken
            clean_comment = re.sub(r'\s*([#]?[-+]?\d+\.?\d*)(?:/\d+)?\s*|\[%eval\s*([#]?[-]?\d+\.?\d*)\]', '',
                                   move['comment']).strip()
            if clean_comment:
                current_line += f" {{{clean_comment}}}"

    if current_line:
        output.append(current_line.strip())

    return "\n".join(output)


def find_top_blunders(pgn_string, top_n=3):
    """
    Identificeert de top N zetten die het grootste verlies in voordeel veroorzaakten.
    De analyse retourneert nu ook de PGN geschiedenis (alle zetten tot aan de blunderpositie).
    """
    pgn_io = io.StringIO(pgn_string)
    game = chess.pgn.read_game(pgn_io)

    if not game:
        print("Fout: Kon geen schaakpartij lezen uit de PGN-string.")
        return []

    blunders = []
    board = game.board()
    prev_eval_cp = 0
    # Lijst van ALLE zetten, inclusief de zet die de blunder veroorzaakte
    moves_made_so_far = []

    # Itereren over de hoofdlijn
    for node in game.mainline():
        if node.move is None:
            continue

        eval_before_cp = prev_eval_cp
        eval_after_cp = get_cp_from_comment(node.comment)

        fen_before_move = board.fen()
        move_number = board.fullmove_number
        player_who_moved = board.turn

        # --- SAN CONVERSIE ---
        move_san = None
        try:
            move_san = board.san(node.move)
        except Exception as e:
            print(f"Waarschuwing: Fout bij SAN-conversie voor zet {move_number} ({e})")
            continue

            # Voeg de data van de ZET die net is gecontroleerd toe aan de geschiedenis
        move_data = {
            'move_number': move_number,
            'player': player_who_moved,
            'san': move_san,
            'comment': node.comment,
            'full_move_index': len(moves_made_so_far)
        }
        moves_made_so_far.append(move_data)

        # --- BLUNDER BEREKENING ---
        if eval_after_cp is not None:
            if player_who_moved == chess.WHITE:
                blunder_score = eval_before_cp - eval_after_cp
                player_str = "Wit"
            else:
                blunder_score = eval_after_cp - eval_before_cp
                player_str = "Zwart"

            # Als de blunder significant is
            if blunder_score > 50:
                blunders.append({
                    'score': blunder_score,
                    'fen': fen_before_move,
                    'move_text': f"{move_number}. {'...' if player_who_moved == chess.BLACK else ''}{move_san}",
                    'player': player_str,
                    'eval_before': eval_before_cp / 100.0,
                    'eval_after': eval_after_cp / 100.0,
                    # Hier slaan we de hele lijst van zetten op, inclusief de blunderzet.
                    'full_move_history': list(moves_made_so_far),
                    # Index van de zet die de blunder veroorzaakte (nodig voor cumulatieve weergave)
                    'move_index': len(moves_made_so_far) - 1
                })

        # --- ZET UITVOEREN ---
        try:
            board.push(node.move)
        except Exception as e:
            print(f"!!! FOUT !!! Kan zet '{move_san}' niet uitvoeren op het bord: {e}")
            return blunders

        # Update de vorige evaluatie voor de volgende zet
        if eval_after_cp is not None:
            prev_eval_cp = eval_after_cp

    # Sorteer eerst op blundergrootte en selecteer de top N
    blunders.sort(key=lambda x: x['score'], reverse=True)
    return blunders[:top_n]


# --- TKINTER KLASSE ---

class ChessBlunderViewer:
    """
    Tkinter applicatie om de top blunders uit een geanalyseerd PGN weer te geven.
    """

    def __init__(self, master, pgn_string, num_blunders=3):
        self.master = master
        master.title(f"Top {num_blunders} Schaakblunders Analyse")

        self.square_size = 60
        self.board_size = self.square_size * 8
        self.num_blunders = num_blunders

        self.color_light = "#F0D9B5"
        self.color_dark = "#B58863"
        self.piece_font = font.Font(family="Arial", size=int(self.square_size * 0.5), weight="bold")

        print("Start analyse van PGN...")
        blunders = find_top_blunders(pgn_string, self.num_blunders)
        print(f"Analyse voltooid. {len(blunders)} significante blunders gevonden.")

        # NIEUW: Sorteer de geselecteerde blunders op zetnummer (chronologisch)
        # De move_text begint met het zetnummer, wat werkt voor simpele sortering.
        self.sorted_blunders = sorted(blunders, key=lambda x: int(x['move_text'].split('.')[0]))

        # --- UI SETUP ---
        main_frame = tk.Frame(master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.blunder_canvas = tk.Canvas(main_frame)
        self.blunder_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=self.blunder_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        self.blunder_canvas.configure(yscrollcommand=scrollbar.set)
        # Configureer scrollregion wanneer het canvas van grootte verandert
        self.blunder_canvas.bind('<Configure>',
                                 lambda e: self.blunder_canvas.configure(scrollregion=self.blunder_canvas.bbox("all")))

        self.content_frame = tk.Frame(self.blunder_canvas)
        self.blunder_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        self.draw_blunder_diagrams()

    def draw_pieces(self, canvas, board):
        """Tekent de stukken op een gegeven Canvas."""
        piece_symbols = {
            'P': '\u2659', 'N': '\u2658', 'B': '\u2657', 'R': '\u2656', 'Q': '\u2655', 'K': '\u2654',
            'p': '\u265F', 'n': '\u265E', 'b': '\u265D', 'r': '\u265C', 'q': '\u265B', 'k': '\u265A'
        }

        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                rank = chess.square_rank(square)
                file = chess.square_file(square)

                tk_row = 7 - rank
                tk_col = file

                x = tk_col * self.square_size + self.square_size / 2
                y = tk_row * self.square_size + self.square_size / 2

                color = "white" if piece.color == chess.WHITE else "black"
                symbol = piece_symbols[piece.symbol()]

                canvas.create_text(x, y, text=symbol, fill=color, font=self.piece_font, tags="piece")

    def draw_blunder_diagram(self, parent_frame, blunder_data, pgn_snippet_text, index):
        """
        Tekent één blok met diagram in kolom 0 en de cumulatieve PGN-geschiedenis in kolom 1.
        """

        # --- GEZAMENLIJK CONTAINER FRAME ---
        blunder_row_frame = tk.Frame(parent_frame, padx=20, pady=15, bd=1, relief=tk.SUNKEN)
        blunder_row_frame.pack(fill="x", expand=True)  # Gebruik pack voor de rijen

        # --- KOLOM 0: DIAGRAM & INFO (Links) ---
        diagram_block = tk.LabelFrame(blunder_row_frame,
                                      text=f"Blunder {index + 1}: {blunder_data['player']} - {blunder_data['move_text']}",
                                      padx=10, pady=10, font=("Helvetica", 12, "bold"), bd=2, relief=tk.GROOVE)
        diagram_block.pack(side=tk.LEFT, padx=10, pady=5, fill="y", anchor="n")

        # 1. Info Label
        info_text = (
            f"Zet die de blunder veroorzaakte: {blunder_data['move_text']}\n"
            f"Verlies: {blunder_data['score'] / 100.0:.2f} P\n"
            f"Eval VOOR zet: {blunder_data['eval_before']:.2f} | Eval NA zet: {blunder_data['eval_after']:.2f}"
        )
        tk.Label(diagram_block, text=info_text, justify=tk.LEFT, pady=5).pack(anchor="w")

        # 2. Canvas voor het bord
        board_canvas = tk.Canvas(diagram_block, width=self.board_size, height=self.board_size,
                                 borderwidth=0, highlightthickness=1, highlightbackground="black")
        board_canvas.pack(pady=10)

        # Initialiseer het bord met de FEN VOOR de blunder
        board = chess.Board(blunder_data['fen'])

        # Teken het bord
        for r in range(8):
            for c in range(8):
                x1 = c * self.square_size
                y1 = r * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                color = self.color_light if (r + c) % 2 == 0 else self.color_dark
                board_canvas.create_rectangle(x1, y1, x2, y2, fill=color, tags="square")

        # Teken de stukken
        self.draw_pieces(board_canvas, board)

        # Markeer het startvierkant van de blunderzet
        try:
            move_san = blunder_data['move_text'].split()[-1].strip('.')
            move_to_highlight = board.parse_san(move_san)
            from_square = move_to_highlight.from_square

            from_rank = 7 - chess.square_rank(from_square)
            from_file = chess.square_file(from_square)

            x1 = from_file * self.square_size
            y1 = from_rank * self.square_size

            # Voeg een gele markering toe aan het startvierkant
            board_canvas.create_rectangle(x1, y1, x1 + self.square_size, y1 + self.square_size,
                                          outline="#FFC300", width=4, tags="highlight")
        except Exception:
            pass

        # --- KOLOM 1: PGN SNIPPET (Rechts) ---
        pgn_block = tk.LabelFrame(blunder_row_frame, text="PGN Zetten sinds de vorige blunder",
                                  padx=10, pady=10, font=("Helvetica", 12, "bold"), bd=2, relief=tk.GROOVE)
        pgn_block.pack(side=tk.RIGHT, padx=10, pady=5, fill=tk.BOTH, expand=True)

        # Text widget voor de PGN-tekst
        pgn_text_widget = tk.Text(pgn_block, height=14, width=50, wrap=tk.WORD, font=("Consolas", 10))

        # Voeg de cumulatieve tekst in
        pgn_text_widget.insert(tk.END, pgn_snippet_text)
        pgn_text_widget.config(state=tk.DISABLED)

        pgn_text_widget.pack(fill=tk.BOTH, expand=True)

        pgn_scrollbar = tk.Scrollbar(pgn_block, command=pgn_text_widget.yview)
        pgn_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        pgn_text_widget.config(yscrollcommand=pgn_scrollbar.set)

    def draw_blunder_diagrams(self):
        """Tekent alle top blunderdiagrammen in chronologische volgorde."""
        if not self.sorted_blunders:
            tk.Label(self.content_frame, text="Geen significante blunders (>= 50 cp) gevonden in de PGN-data.",
                     pady=50, padx=20).pack()
            return

        # De index van de laatste zet die in het VORIGE blok is getoond
        last_move_index = -1

        for i, blunder in enumerate(self.sorted_blunders):
            # De blunderzet is de laatste zet in de full_move_history.
            # De index van de zet die de blunder veroorzaakt is opgeslagen in 'move_index'.
            current_move_index = blunder['move_index']

            # Selecteer alleen de zetten die NIEUW zijn sinds de laatste getoonde blunder
            moves_to_display = blunder['full_move_history'][last_move_index + 1: current_move_index + 1]

            # Formatteer de PGN voor weergave
            pgn_snippet = _format_pgn_history(moves_to_display)

            # Teken het diagram en de PGN
            self.draw_blunder_diagram(self.content_frame, blunder, pgn_snippet, i)

            # Update de teller voor de volgende iteratie
            last_move_index = current_move_index

        # Zorg ervoor dat de scrollregio wordt bijgewerkt
        self.content_frame.update_idletasks()  # Gebruik de correcte update methode
        self.blunder_canvas.config(scrollregion=self.blunder_canvas.bbox("all"))


# --- HOOFD EXECUTIE ---

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ChessBlunderViewer(root, PGN_WITH_BLUNDERS)
        root.mainloop()
    except ImportError:
        error_msg = ("Fout: De 'python-chess' bibliotheek is niet geïnstalleerd.\n"
                     "Installeer deze met: pip install python-chess")
        error_root = tk.Tk()
        error_root.title("Installatie Vereist")
        tk.Label(error_root, text=error_msg, padx=20, pady=20).pack()
        tk.Button(error_root, text="Sluiten", command=error_root.destroy).pack(pady=10)
        error_root.mainloop()
    except Exception as e:
        print(f"Er is een onverwachte fout opgetreden: {e}")