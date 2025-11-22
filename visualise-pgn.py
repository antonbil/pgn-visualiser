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
[Round "1.2"]
[White "Caruana,F"]
[Black "Nakamura,Hi"]
[Result "0-1"]
[WhiteTitle "GM"]
[BlackTitle "GM"]
[WhiteElo "2776"]
[BlackElo "2804"]
[ECO "D10"]
[Opening "Slav Defense: Exchange Variation"]
[Variation "exchange variation"]
[WhiteFideId "2020009"]
[BlackFideId "2016192"]
[EventDate "2025.05.26"]
[WhiteACPL "-114"]
[BlackACPL "2"]
[Annotator "Stockfish 17"]

{ Stockfish 17 } 1. d4 d5 2. c4 c6 3. cxd5 { D10 Slav Defense: Exchange
Variation } 3... cxd5 4. Nc3 Nf6 5. Bf4 Nc6 6. e3 a6 7. Nf3 $6 { +0.12 } ( 7.
Be2 Bf5 8. Nf3 Nh5 9. Be5 e6 10. O-O Be7 11. Ne1 Nf6 { +0.20/18 } ) 7... Bg4 8.
h3 Bxf3 9. Qxf3 e6 10. Bd3 Bd6 $9 { +0.14 } ( 10... Rc8 11. O-O Bd6 12. Bg5 Be7
13. Rac1 O-O 14. a3 h6 15. Bh4 { +0.15/21 } ) 11. Bg5 Be7 12. O-O O-O 13. Rac1
h6 $9 { +0.19 } ( 13... Rc8 14. Qd1 h6 15. Bh4 Na5 16. Qe2 Ne8 17. Bxe7 Qxe7 18.
Rc2 { +0.16/15 } ) 14. Bh4 Ne8 15. Bg3 Bd6 16. Na4 $6 { +0.18 } ( 16. a3 Na5 17.
Na4 Bxg3 18. Qxg3 Nc4 19. Rc2 Ned6 20. Ra1 a5 { +0.26/19 } ) 16... Bxg3 $9 {
+0.31 } ( 16... Qa5 17. Nc5 Bxc5 18. Rxc5 Qxa2 19. Bf4 Qb3 20. Bc2 Qb6 21. Qg3 {
+0.08/19 } ) 17. Qxg3 Nd6 18. Nc5 $6 { +0.11 } ( 18. Rc3 Re8 19. Qg4 Rc8 20.
Rfc1 Nb4 21. Rxc8 Nxc8 22. Bb1 Re7 { +0.25/15 } ) 18... Rc8 19. a3 a5 $9 { +0.15 }
( 19... Qe7 20. Rc2 a5 21. Na4 Na7 22. Rfc1 Rxc2 23. Rxc2 Rc8 24. Rc5 { +0.13/22 } )
20. Qg4 { +0.07 } ( 20. Rc2 Na7 21. Rfc1 Qe7 22. h4 Rfd8 23. h5 Rc6 24. Nb3 Rxc2
{ +0.16/17 } ) 20... Qe7 $9 { +0.11 } ( 20... Ne7 21. h4 b6 22. Na4 b5 23. Rxc8
Qxc8 24. Nc5 a4 25. b3 { +0.09/21 } ) 21. Qd1 { +0.09 } ( 21. Rc2 e5 22. dxe5
Nxe5 23. Qd4 b5 24. Be2 a4 25. Rfc1 Ndc4 { +0.13/14 } ) 21... b6 22. Na4 b5 23.
Nc3 Na7 $9 { +0.22 } ( 23... Qb7 24. a4 bxa4 25. Nxa4 Rfd8 26. Rc3 e5 27. dxe5
Nxe5 28. Rxc8 { +0.12/17 } ) 24. Qe2 Qd7 25. b3 Rc6 26. Rc2 $6 { +0.15 } ( 26.
Qd2 Rfc8 27. Ne2 Qd8 28. h4 Qb6 29. Rxc6 Nxc6 30. Rc1 b4 { +0.20/20 } ) 26...
Rfc8 27. Rfc1 g6 $9 { +0.20 } ( 27... Qb7 28. Na2 Qb6 29. Qd1 g6 30. Nc3 Kg7 31.
h4 Qb7 32. Ne2 { +0.14/22 } ) 28. h4 $6 { +0.12 } ( 28. Qd2 Qd8 29. Ne2 Qb6 30.
h4 b4 31. a4 Rxc2 32. Rxc2 Rc6 { +0.23/20 } ) 28... Kg7 $9 { +0.17 } ( 28...
R8c7 29. Na2 Rxc2 30. Rxc2 Qc8 31. Rxc7 Qxc7 32. Qe1 Nac8 33. Qd2 { +0.16/18 } )
29. g3 { +0.10 } ( 29. Na2 { +0.19/19 } ) 29... R8c7 30. Qd2 Qc8 31. Ne2 Rxc2
32. Rxc2 Rxc2 33. Bxc2 Nc6 34. Qc3 b4 35. axb4 Nxb4 36. Qxc8 Nxc8 37. Bb1 Nd6
38. Nc3 f5 39. f3 g5 { -0.09 } ( 39... Nc6 40. Bd3 { -0.11/23 } ) 40. hxg5 hxg5
41. Kf2 Nc6 42. Bd3 $9 { -0.12 } ( 42. Na4 Kf7 43. Nc5 Ke7 44. Bc2 Nb4 45. Bd3
f4 46. Bb1 Nc6 { -0.12/20 } ) 42... Kf6 43. f4 $9 { -0.60 } ( 43. Na4 f4 44. g4
Nf7 45. Nc3 Nb4 46. Bb1 Nd8 47. Ne2 Ndc6 { -0.17/20 } ) 43... Nb4 $6 { -0.15 } (
43... g4 44. Ke1 Ne7 45. Kd1 Ng8 46. Na4 Kf7 47. Nc5 Ke7 48. Ke2 { -0.56/22 } )
44. Ke2 g4 45. Kd2 $9 { -0.36 } ( 45. Bb5 Nf7 46. Kd1 Nh6 47. Na4 Ke7 48. Nc5
Ng8 49. Nd7 Kd6 { -0.37/28 } ) 45... Ke7 $6 { -0.36 } ( 45... Ne8 46. Bb5 Ng7
47. Ke2 Nh5 48. Kf2 Kf7 49. Na4 Nf6 50. Nc5 { -0.37/27 } ) 46. Bb5 Kd8 $6 {
-0.33 } ( 46... Nf7 47. Na4 Nh6 48. Ke1 Ng8 49. Nc5 Nf6 50. Kf2 Na2 51. Bd3 {
-0.38/27 } ) 47. Ba4 $9 { -0.42 } ( 47. Ke2 Nf7 48. Kd2 Nh6 49. Na4 Ng8 50. Nc5
Ke7 51. Ke2 Nf6 { -0.37/26 } ) 47... Na6 48. Bb5 $9 { -0.49 } ( 48. Bc6 Nc7 {
-0.40/24 } ) 48... Nc7 49. Bc6 Kc8 $6 { -0.30 } ( 49... Nc8 50. Bb5 Ne7 51. Bd3
Ng8 52. Na4 Nf6 53. Nc5 Nh5 54. Nb7+ { -0.41/25 } ) 50. Ke2 $9 { -0.37 } ( 50.
Kc2 Kd8 51. Ba4 Na6 52. Kd1 Nb4 53. Ke1 Ke7 54. Kd1 Nf7 { -0.33/27 } ) 50... Kd8
51. Kd2 $9 { -0.39 } ( 51. Ke1 Ke7 52. Kd2 Nf7 53. Kc2 Na6 54. Bb5 Nb4+ 55. Kd2
Nh6 { -0.32/26 } ) 51... Na6 52. Ba4 $9 { -0.33 } ( 52. Bb5 Nb4 53. Ke1 Ke7 54.
Kd2 Nf7 55. Na4 Nh6 56. Ke1 Ng8 { -0.30/24 } ) 52... Ke7 53. Bb5 Nb4 $6 { -0.29 }
( 53... Nc7 54. Bc6 Nf7 55. Kc1 Na6 56. Bb5 Nb4 57. Kd1 Nh6 58. Na4 { -0.35/27 } )
54. Ba4 $9 { -0.33 } ( 54. Ke2 Nf7 55. Bd3 Kd7 56. Bb5+ Kd8 57. Na4 Na2 58. Bd3
Nd6 { -0.31/22 } ) 54... Nf7 55. Bb5 Nh6 56. Bd3 $9 { -0.74 } ( 56. Na4 {
-0.32/26 } ) 56... Ng8 57. Bb1 Nf6 58. Ke1 $9 { -0.73 } ( 58. Ke2 Nc6 59. Na4
Nd8 60. Nc5 Nd7 61. Nd3 Kd6 62. Bc2 Kc7 { -0.61/21 } ) 58... Kd6 59. Na4 Nd7 60.
Ke2 $9 { -0.56 } ( 60. Nb2 Kc6 61. Nd1 Kb6 62. Nc3 Na6 63. Bd3 Nc7 64. Kd2 Kc6 {
-0.65/25 } ) 60... Kc6 $2 { -0.71 } ( 60... Na6 61. Nc3 Nc7 62. Bd3 Ne8 63. Bb5
Ng7 64. Na4 Nh5 65. Kf2 { -0.70/26 } ) 61. Ke1 $9 { -0.70 } ( 61. Nc3 Na6 62.
Bc2 Nc7 63. Bd3 Kd6 64. Ke1 Ne8 65. Bb5 Ng7 { -0.63/23 } ) 61... Na6 62. Bd3 Nc7
63. Nc3 Nf6 64. Na4 Nce8 $6 { -0.26 } ( 64... Nd7 { -0.41/21 } ) 65. Nc5 Ng7 $6
{ -0.15 } ( 65... Nd6 66. Nxe6 { -0.27/21 } ) 66. Na4 $9 { -2.46 } ( 66. Ke2 Kb6
67. Ke1 Nfe8 68. Nxe6 Nxe6 69. Bxf5 N6g7 70. Bxg4 Nf6 { -0.23/21 } ) 66... Ne4
67. Bxe4 $9 { -4.22 } ( 67. Ba6 Nxg3 68. Nb2 Ne4 69. Bf1 Ne8 70. Nd3 Kb6 71. Ne5
N8f6 { -2.28/20 } ) 67... fxe4 68. Nc3 $9 { -5.50 } ( 68. Nc5 Nf5 69. Nxe6 Nxe3
70. Nf8 Nc2+ 71. Kd1 Nxd4 72. Ng6 Kd6 { -3.62/17 } ) 68... Nf5 69. Kf2 $9 {
-5.76 } ( 69. Kd2 Nxg3 70. Na4 Kb5 71. Nc5 Kb4 72. Nxe6 Kxb3 73. Ng7 a4 {
-5.20/18 } ) 69... Kb6 70. Na4+ $9 { -6.00 } ( 70. Kf1 Nxe3+ 71. Ke1 Nf5 72. Ne2
Kb5 73. Kd1 Kb4 74. Kc2 a4 { -5.04/17 } ) 70... Kb5 71. Nc5 Kb4 72. Nb7 $9 {
-6.50 } ( 72. Ke2 Nxg3+ 73. Ke1 Nf5 74. Kf2 g3+ 75. Kg2 Nxe3+ 76. Kxg3 Nf5+ {
-5.76/19 } ) 72... Kxb3 73. Nxa5+ Kc3 74. Nb7 $9 { -7.47 } ( 74. Ke1 Nxe3 75.
Nc6 Nc2+ 76. Kd1 Nxd4 77. Ne5 Nf5 78. Nxg4 d4 { -6.42/19 } ) 74... Kd2 75. Nc5
$9 { -7.22 } ( 75. Na5 Nxe3 76. Nb3+ Kc3 77. Nc5 Nf5 78. Ke1 Nxd4 79. Nd7 e3 {
-6.23/18 } ) 75... Nxe3 76. Nb3+ Kc3 77. Nc5 Nf5 78. Nxe6 $9 { Mate in 5 } ( 78.
Ke1 Nxd4 79. Kd1 e3 80. Na4+ Kd3 81. Nc5+ Kc4 82. Na4 Nf5 { -6.50/17 } ) 78...
Kd2 0-1

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
                    'move_index': len(moves_made_so_far) - 1 # Index van de zet
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

        # Sorteer de geselecteerde blunders op zetnummer (chronologisch)
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
        self.content_frame.update_idletasks()
        self.blunder_canvas.config(scrollregion=self.blunder_canvas.bbox("all"))


# --- HOOFD EXECUTIE ---

if __name__ == "__main__":
    try:
        root = tk.Tk()
        # Stel de initiële grootte in op 1200x800 (een gangbare laptop resolutie)
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