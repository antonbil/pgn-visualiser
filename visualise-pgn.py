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
[Event "FIDE World Cup 2025"]
[Site "Goa IND"]
[Date "2025.11.08"]
[Round "3.2"]
[White "Van Foreest,Jorden"]
[Black "Sarana,A"]
[Result "1-0"]
[WhiteTitle "GM"]
[BlackTitle "GM"]
[WhiteElo "2693"]
[BlackElo "2675"]
[ECO "C55"]
[Opening "Italian Game: Two Knights Defense, Modern Bishop's Opening"]
[WhiteFideId "1039784"]
[BlackFideId "24133795"]
[EventDate "2025.11.01"]
[EventType "k.o."]
[WhiteACPL "26"]
[BlackACPL "-698"]
[Annotator "Stockfish 17"]

{ Stockfish 17 } 1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. d3 { C55 Italian Game: Two
Knights Defense, Modern Bishop's Opening } 4... Be7 $9 { +0.26 } ( 4... Bc5 5.
O-O d6 6. c3 a6 7. a4 O-O 8. h3 Ba7 9. a5 { +0.15/22 } ) 5. Nc3 $6 { +0.25 } (
5. a4 O-O 6. O-O a5 7. Nc3 d6 8. Re1 Bg4 9. h3 Bh5 { +0.28/20 } ) 5... d6 6. a4
a5 $9 { +0.31 } ( 6... O-O 7. O-O Na5 8. Ba2 c5 9. Nd2 Be6 10. Nc4 Nxc4 11. Bxc4
{ +0.26/20 } ) 7. O-O O-O 8. Re1 h6 9. h3 Re8 $9 { +0.30 } ( 9... Be6 10. b3 Re8
11. Bb2 Bf8 12. Bb5 Bd7 13. Ne2 Nb8 14. Bxd7 { +0.21/23 } ) 10. Be3 $6 { +0.25 }
( 10. d4 Nxd4 { +0.25/18 } ) 10... Bf8 $9 { +0.40 } ( 10... Be6 { +0.18/19 } )
11. g4 Nh7 12. Kh2 Be6 13. Rg1 $6 { +0.09 } ( 13. Bb5 Be7 14. Nd5 Rf8 15. Bxc6
bxc6 16. Nxe7+ Qxe7 17. Rg1 Bd7 { +0.25/17 } ) 13... Be7 $9 { +0.50 } ( 13...
Bxc4 14. dxc4 Be7 15. Nd5 Bg5 16. Nxg5 hxg5 17. h4 Nd4 18. Bxd4 { +0.13/21 } )
14. Nd5 Ng5 $9 { +0.98 } ( 14... Bg5 15. Nxg5 hxg5 16. h4 Ne7 17. Nxe7+ Rxe7 18.
hxg5 Bxc4 19. dxc4 { +0.45/19 } ) 15. Nd2 $2 { +0.39 } ( 15. Nh4 { +0.92/18 } )
15... Nh7 16. Nf3 Ng5 $9 { +0.95 } ( 16... Bg5 { +0.51/16 } ) 17. Nh4 Nh7 $9 {
+1.19 } ( 17... Nb4 18. Nxe7+ { +0.75/18 } ) 18. Nf5 $2 { -0.11 } ( 18. Nxe7+
Qxe7 19. Nf5 Qd8 20. Bb5 d5 21. Qf3 Bd7 22. Bxc6 bxc6 { +1.34/22 } ) 18... Bg5
19. Bb5 Bd7 $9 { +0.80 } ( 19... Rf8 20. Qe2 Bxd5 21. exd5 Ne7 22. Bxg5 hxg5 23.
Nxe7+ Qxe7 24. d4 { -0.42/19 } ) 20. Qf3 Nb4 21. Bxd7 Qxd7 22. h4 Nxd5 23. exd5
Bxe3 24. fxe3 e4 25. dxe4 $2 { +0.64 } ( 25. Qf4 Nf8 26. Qf2 Ng6 27. d4 f6 28.
Rgf1 Rf8 29. Kg3 Rf7 { +0.76/20 } ) 25... Re5 26. g5 hxg5 27. Qh3 Qd8 28. Rg4 f6
29. Rh1 $6 { +0.44 } ( 29. Rag1 Qf8 30. hxg5 Nxg5 31. Rxg5 fxg5 32. Rxg5 Rae8
33. Kg2 Qf6 { +0.55/24 } ) 29... Qe8 30. hxg5 $6 { +0.24 } ( 30. Kg1 Qg6 31. b3
Rf8 32. Kg2 Rfe8 33. Qf3 Qf7 34. c4 Rf8 { +0.42/22 } ) 30... fxg5 31. Kg2 Qg6
32. Qg3 Rae8 33. Rxh7 Qxh7 34. Rxg5 Kh8 $9 { +7.54 } ( 34... R8e7 35. Qg4 Rxe4
36. Nxe7+ Rxe7 37. Qc8+ Kf7 38. Rf5+ Kg6 39. Rf3 { +0.00/42 } ) 35. Rh5 g6 $9 {
Mate in 3 } ( 35... Rxf5 36. Rxh7+ Kxh7 37. exf5 Kh8 38. Qg6 Re7 39. Kf3 Kg8 40.
e4 { +7.44/26 } ) 36. Qxg6 1-0


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


def get_all_significant_blunders(pgn_string):
    """
    Identificeert ALLE zetten die een significant verlies in voordeel veroorzaakten (> 50 cp).
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
            # Dit is de 0-gebaseerde index in de complete zetlijst
            'full_move_index': len(moves_made_so_far)
        }
        moves_made_so_far.append(move_data)

        # --- BLUNDER BEREKENING ---
        if eval_after_cp is not None:
            if player_who_moved == chess.WHITE:
                # Verlies van voordeel voor Wit is (Vorige Eval - Nieuwe Eval)
                blunder_score = eval_before_cp - eval_after_cp
                player_str = "Wit"
            else:
                # Verlies van voordeel voor Zwart is (Nieuwe Eval - Vorige Eval)
                blunder_score = eval_after_cp - eval_before_cp
                player_str = "Zwart"

            # Als de blunder significant is (verlies van meer dan 50 centipawns)
            if blunder_score > 0:
                blunders.append({
                    'score': blunder_score,
                    'fen': fen_before_move,
                    'move_text': f"{move_number}. {'...' if player_who_moved == chess.BLACK else ''}{move_san}",
                    'player': player_str,
                    'eval_before': eval_before_cp / 100.0,
                    'eval_after': eval_after_cp / 100.0,
                    'full_move_history': list(moves_made_so_far),
                    'move_index': len(moves_made_so_far) - 1  # Index van de zet
                })

        # --- ZET UITVOEREN EN EVALUATIE BIJHOUDEN ---
        try:
            board.push(node.move)
        except Exception as e:
            print(f"!!! FOUT !!! Kan zet '{move_san}' niet uitvoeren op het bord: {e}")
            return blunders

        if eval_after_cp is not None:
            # Voor de volgende zet wordt de 'eval_after' van deze zet de 'prev_eval'
            prev_eval_cp = eval_after_cp

    return blunders


def select_key_positions(all_blunders):
    """
    Selecteert de blunders op basis van de nieuwe logica:
    1. Grootste blunder uit elk van de 3 gelijke delen van de partij.
    2. Top 3 van de overgebleven blunders (wereldwijd).
    """
    if not all_blunders:
        return []

    # Bepaal het totale aantal halve zetten (inclusief de laatste zet in de blunderlijst)
    total_half_moves = all_blunders[-1]['full_move_history'][-1]['full_move_index'] + 1

    # Gebruik een set om te voorkomen dat we dezelfde blunder twee keer selecteren
    selected_indices = set()
    selected_blunders = []

    # 1. Verdeel de partij in 3 (bijna) gelijke delen
    part_size = total_half_moves // 3

    # Bepaal de bereiken op basis van de 0-gebaseerde zet-index
    ranges = [
        (0, part_size),  # Deel 1 (Openings/Vroeg Middenspel)
        (part_size, 2 * part_size),  # Deel 2 (Middenspel)
        (2 * part_size, total_half_moves)  # Deel 3 (Laat Middenspel/Eindspel)
    ]

    print(f"Totale halve zetten: {total_half_moves}. Deelgrootte: {part_size}.")

    # Selecteer de grootste blunder in elk deel
    for i in [1,2]:
      for part_num, (start_index, end_index) in enumerate(ranges):
        best_in_part = None
        max_score = -1

        for blunder in all_blunders:
            move_idx = blunder['move_index']

            # Controleer of de zet binnen het huidige bereik valt
            if start_index <= move_idx < end_index:
                if blunder['score'] > max_score and move_idx not in selected_indices:
                    max_score = blunder['score']
                    best_in_part = blunder

        if best_in_part:
            best_in_part['source'] = f"Grootste Blunder in Deel {part_num + 1}"
            selected_blunders.append(best_in_part)
            selected_indices.add(best_in_part['move_index'])

    # 2. Selecteer de top 3 van de overgebleven blunders
    remaining_blunders = sorted(
        [b for b in all_blunders if b['move_index'] not in selected_indices],
        key=lambda x: x['score'],
        reverse=True
    )

    # Voeg de top 3 toe aan de selectie
    for i in range(min(3, len(remaining_blunders))):
        remaining_blunders[i]['source'] = f"Wereldwijde Top {i + 1} (Resterend)"
        selected_blunders.append(remaining_blunders[i])
        selected_indices.add(remaining_blunders[i]['move_index'])

    # Sorteer de geselecteerde blunders chronologisch voor weergave
    selected_blunders.sort(key=lambda x: x['move_index'])

    return selected_blunders


# --- TKINTER KLASSE ---

class ChessBlunderViewer:
    """
    Tkinter applicatie om de top blunders uit een geanalyseerd PGN weer te geven.
    """

    def __init__(self, master, pgn_string):
        self.master = master

        # Voer de geavanceerde analyse uit
        print("Start volledige analyse van PGN...")
        all_blunders = get_all_significant_blunders(pgn_string)
        print(f"Volledige analyse voltooid. {len(all_blunders)} significante blunders gevonden (> 50 cp verlies).")

        self.sorted_blunders = select_key_positions(all_blunders)
        self.num_blunders = len(self.sorted_blunders)

        master.title(f"Schaakpartij Analyse: {self.num_blunders} Kritieke Posities Geselecteerd")

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
        title = f"Positie {index + 1}: {blunder_data.get('source', 'Blunder')} - {blunder_data['move_text']}"
        diagram_block = tk.LabelFrame(blunder_row_frame,
                                      text=title,
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
            # We moeten de FEN parsen, de move toevoegen, en dan de from_square bepalen.
            # Echter, de FEN is de positie *VOOR* de zet.
            # We gebruiken de board.parse_san op de huidige board staat (FEN VOOR de zet)
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
        pgn_block = tk.LabelFrame(blunder_row_frame, text="PGN Zetten sinds de vorige kritieke positie",
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
        """Tekent alle geselecteerde diagrammen in chronologische volgorde."""
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
        self.content_frame.update_idletasks()
        self.blunder_canvas.config(scrollregion=self.blunder_canvas.bbox("all"))


# --- HOOFD EXECUTIE ---

if __name__ == "__main__":
    try:
        root = tk.Tk()
        # Stel de initiële grootte in op 1200x800
        root.geometry("1200x800")
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