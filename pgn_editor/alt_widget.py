import tkinter as tk
import chess.pgn
import io
import re

class TouchMoveList(tk.Text):
    def __init__(self, master, **kwargs):
        # Initialize the text widget with specific styles for chess PGN
        super().__init__(master, **kwargs)
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

    def load_pgn(self, pgn_string):
        # Parse the PGN string using the python-chess library
        pgn_io = io.StringIO(pgn_string)
        game = chess.pgn.read_game(pgn_io)
        if game:
            self.node_to_index = {} # Reset de mapping
            self.config(state="normal")
            self.delete("1.0", tk.END)
            self._process_main_line(game)
            self.config(state="disabled")
            return game, self.node_to_index

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
        """
        Highlights the node with a high-visibility red background.
        """
        # Remove old highlights
        self.tag_remove("active_move", "1.0", tk.END)
        self.tag_remove("active_line", "1.0", tk.END)

        if node in self.node_to_index:
            start, end = self.node_to_index[node]

            # Apply the prominent red highlight
            self.tag_add("active_move", start, end)

            # Highlight the background of the entire row
            line_num = start.split('.')[0]
            self.tag_add("active_line", f"{line_num}.0", f"{line_num}.end")

            # Center the move in the widget so it's not hidden at the edge
            # We scroll to the position but with an offset of 2 lines for context
            self.see(f"{line_num}.0 - 2 lines")

            # Force UI refresh
            self.update_idletasks()

    def _on_move_click(self, node, type_label):
        # Handle the click and print details as requested
        print(f"KLIK -> Type: {type_label:15} | Zet: {node.san()}")

# --- Demo Setup ---
if __name__ == "__main__":
    root = tk.Tk()
    root.title("PGN Variant Display Fix")

    # English: Test string demonstrating '2. Nf3 d6' vs '2. Nf3 (2... Nc6) 2... d6'
    sample = """
{ Analysis by Stockfish 17 (Depth 17, T=0.25) } 1. e4 { 0.29 } 1... d6 { 0.52 }
( 1... e5 { 0.25 (+0.27) } 2. Nf3 Nc6 3. Bb5 a6 ) 2. d4 { 0.49 } 2... Nf6
{ 0.45 } 3. Nc3 { 0.47 } 3... g6 { 0.72 B07 Pirc Defense } 4. Be3 { 0.73 } 4...
a6 { 0.80 } 5. Qd2 { 0.75 } ( 5. h3 Bg7 6. Nf3 O-O 7. a4 Nc6 8. Be2 e6
{ Caruana,F (2799)-Grischuk,A (2782) Saint Louis 2017 } ) 5... b5 { 0.73 } 6.
f3 { 0.59 } 6... Nbd7 { 0.63 } 7. O-O-O { 0.67 } 7... Nb6 { 0.62 } 8. g4 $6
{ 0.10 } ( 8. Bd3 { 0.65 (+0.55) } 8... c6 9. e5 Nfd5 10. Nxd5 ) 8... Bb7 $6
{ 0.70 } ( 8... b4 { 0.02 (+0.68) } 9. Nb1 a5 10. c4 Ba6 ) 9. Nh3 { 0.26 } ( 9.
g5 Nfd7 10. h4 c5 11. dxc5 dxc5 12. h5 Bg7 13. h6 Be5 14. f4 Bc7
{ Morozevich,A (2731)-Onischuk,V (2594) Dubai 2014 } ) ( 9. g5 { 0.72 (+0.46) }
9... Nh5 10. d5 e5 11. dxe6 ) 9... Nfd7 { 0.63 } ( 9... Bg7 { 0.21 (+0.42) }
10. a3 Nfd7 11. Nf4 c5 ) 10. Be2 $2 { -0.51 } ( 10. Nf4 { 0.51 (+1.02) } 10...
Bg7 11. h4 c5 12. dxc5 ) 10... e6 $6 { 0.26 } ( 10... b4 { -0.54 (+0.8) } 11.
Nb1 c5 12. d5 h6 ) 11. Bg5 $6 { -0.22 } ( 11. a3 { 0.31 (+0.53) } 11... Bg7 12.
Bg5 Qb8 13. Bh6 ) 11... Be7 { -0.19 } 12. Qe3 { -0.63 } ( 12. a3
{ -0.32 (+0.31) } 12... h5 13. Bxe7 Qxe7 14. Qe3 ) 12... Bxg5 { -0.37 } 13.
Nxg5 { -0.42 } 13... h6 { -0.32 } 14. Nh3 { -0.32 } 14... Qh4 { 0.01 } ( 14...
c5 { -0.37 (+0.38) } 15. a3 Qe7 16. dxc5 dxc5 ) 15. Nf2 { 0.11 } 15... O-O-O
{ 0.12 } 16. f4 $6
{ -0.70 Giri must have underestimated Black's answer. White's pieces are not
placed well for this advance. }
( 16. Nd3 { -0.04 (+0.66) } 16... Rdf8 17. b3 f5 18. gxf5 ) 16... f5 { -0.66 }
17. Bf3 $6
{ -1.24 Giri decides to give up a
piece, but there's not enough compensation. }
( 17. Bd3 ) ( 17. a3 { -0.64 (+0.6) } 17... Nf6 18. Rhg1 fxe4 19. Nfxe4 ) 17...
b4 $1 { -1.24 Quite
killing. } 18. exf5 $2 { -2.35 } ( 18. Ne2 Nc4 ) ( 18. Nb1
fxe4 19. Bxe4 ( 19. Nxe4 Nd5 { and f4
falls } ) 19... Bxe4 20. Nxe4 Qxg4 ) (
18. Nb1 { -1.25 (+1.1) } 18... fxe4 19. Bxe4 Bxe4 20. Nxe4 ) 18... bxc3
{ -2.34 } 19. fxe6 { -2.66 } 19... cxb2+ { -2.70 } 20. Kb1 { -2.43 } 20... Nf6
{ -2.42 } 21. Bxb7+ { -2.94 } ( 21. Ne4 { -2.55 (+0.39) } 21... Nxg4 22. Qb3
Nf6 23. Nxf6 ) 21... Kxb7 { -2.94 } 22. Qf3+ { -2.81 } 22... d5 $6 { -2.24 } (
22... Ka7 { -2.84 (+0.6) } 23. d5 Nfxd5 24. a4 Ne7 ) 23. Nd3 { -1.93 } 23...
Ne4 { -2.28 } 24. Nc5+ { -2.34 } 24... Ka7 { -2.12 } 25. Qa3 $2 { -3.32 } ( 25.
Nxe4 { -2.23 (+1.09) } 25... dxe4 26. Qxe4 Qxg4 27. Qe5 ) 25... Nxc5 { -3.30 }
26. Qxc5 { -3.14 } 26... Kb7 { -3.34 }
"""

    view = TouchMoveList(root, width=80, height=20)
    view.pack(padx=10, pady=10)
    game, node_to_index = view.load_pgn(sample)
    # print("node_to_index", node_to_index)
    view.highlight_node(list(node_to_index.keys())[40])

    root.mainloop()
