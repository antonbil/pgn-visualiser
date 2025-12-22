
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import chess
import chess.pgn
import os
from PIL import Image, ImageTk
import cairosvg
import io
import re
import argparse
from io import BytesIO

def parse_args():
    """
    Define an argument parser and return the parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='annotator',
        description='store chess game in a PGN file '
        'based on user input')
    parser.add_argument("--piece_set", "-p",
                        help="Set the piece-set for chess-pieces",
                        default="staunty")

    return parser.parse_args()

# ----------------------------------------------------------------------
# 1. PIECE IMAGE MANAGER (THE FACTORY/SINGLETON)
# This class is responsible for loading all images once from the disk.
# ----------------------------------------------------------------------
class PieceImageManager1:
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

        print(f"Laden van schaakset '{self.set_identifier}' uit: {self.image_dir_path}")

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
                            print(f"Laden SVG: {image_path}")
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
                        print(f"Fout bij het laden van {image_path}: {e}")
                        img = None # Bij fout, probeer volgende extensie

            # Controleer of we een afbeelding hebben geladen
            if img:
                # 2. Afmetingen aanpassen
                img = img.resize((self.square_size, self.square_size), Image.Resampling.LANCZOS)

                # 3. Converteren naar Tkinter-formaat en opslaan
                self.images[symbol] = ImageTk.PhotoImage(img)
            else:
                print(f"Waarschuwing: Geen afbeelding gevonden voor set {self.set_identifier} en stuk {symbol}. Laat leeg.")

        if self.images:
            print(f"Schaakset '{self.set_identifier}' succesvol geladen.")
        else:
            print(f"Fout: Geen schaakstukken geladen. Controleer of de bestanden bestaan: *K{self.set_identifier}.(png/svg)")

class PGNEntryApp:
    """
    Applicatie voor het invoeren van schaakpartijen via bordklikken en het genereren van een PGN-bestand.
    """
    def __init__(self, master, image_manager, pgn_filepath = None, square_size = 60):
        self.master = master
        self.pgn_filepath = pgn_filepath
        self.image_manager = image_manager
        master.protocol("WM_DELETE_WINDOW", self.handle_close)
        self.file_path = ""
        master.title("PGN Invoer Applicatie")

        # --- Configuraties ---
        self.square_size = square_size
        self.color_light = "#F0D9B5"
        self.color_dark = "#B58863"
        self.selected_color = "#FF8080" # Kleur voor geselecteerd veld

        # --- Schaakdata Initialisatie ---
        self.board = chess.Board() # Het huidige schaakbord
        self.move_history = []     # Lijst van zetten (chess.Move objecten)
        self.selected_square = None # Het laatst geselecteerde veld

        self.piece_map = {
            'K': 'wK', 'Q': 'wQ', 'R': 'wR', 'B': 'wB', 'N': 'wN', 'P': 'wP',
            'k': 'bK', 'q': 'bQ', 'r': 'bR', 'b': 'bB', 'n': 'bN', 'p': 'bP',
        }

        self._create_widgets()
        self._draw_board()
        self._draw_pieces()

    def _create_widgets(self):
        """Maakt alle UI-elementen (headers, bord, zetlijst) aan."""

        # Hoofdframe met drie secties: Header, Diagram, Zetten
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Header Frame (Boven: PGN Metadatavelden)
        header_frame = ttk.LabelFrame(main_frame, text="PGN Headers", padding="10")
        header_frame.pack(fill='x', pady=5)
        self._create_header_inputs(header_frame)

        # 2. Game Frame (Midden: Bord en Listbox)
        game_frame = ttk.Frame(main_frame)
        game_frame.pack(fill=tk.BOTH, expand=True)
        game_frame.grid_columnconfigure(0, weight=1) # Canvas kolom
        game_frame.grid_columnconfigure(1, weight=1) # Listbox kolom
        game_frame.grid_rowconfigure(0, weight=1)

        # Canvas voor het Schaakbord
        self.board_canvas = tk.Canvas(
            game_frame,
            width=self.square_size * 8,
            height=self.square_size * 8,
            bg='white'
        )
        self.board_canvas.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        self.board_canvas.bind("<Button-1>", self._on_board_click)


        # Frame voor de Listbox en Knoppen
        moves_frame = ttk.Frame(game_frame)
        moves_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
        moves_frame.grid_columnconfigure(0, weight=1)
        moves_frame.grid_rowconfigure(0, weight=1)

        self._create_move_list_widgets(moves_frame)

    def _create_header_inputs(self, parent_frame):
        """Maakt de invoervelden voor PGN-metadata aan."""
        self.header_vars = {}
        fields = ["Event", "Site", "Date", "White", "Black", "Result"]

        for i, field in enumerate(fields):
            label = ttk.Label(parent_frame, text=f"{field}:")
            label.grid(row=i, column=0, sticky='w', padx=5, pady=2)

            var = tk.StringVar()
            entry = ttk.Entry(parent_frame, textvariable=var, width=40)
            entry.grid(row=i, column=1, sticky='ew', padx=5, pady=2)
            self.header_vars[field] = var

        # Standaardwaarden
        self.header_vars["Event"].set("Oefenpartij")
        self.header_vars["White"].set("Speler Wit")
        self.header_vars["Black"].set("Speler Zwart")
        self.header_vars["Result"].set("*")
        self.header_vars["Date"].set(tk.PhotoImage().tk.call('clock', 'format', tk.PhotoImage().tk.call('clock', 'seconds'), '-format', '%Y.%m.%d'))

        parent_frame.grid_columnconfigure(1, weight=1)

    def _create_move_list_widgets(self, parent_frame):
        """Maakt de Listbox voor zetten, de knoppen en het nieuwe meldingen-Label."""

        # 0. MELDEGEBIED: Label voor meldingen (NIEUWE RIJ 0)
        self.message_label = ttk.Label(
            parent_frame,
            text="Start een partij door op een veld te klikken.",
            relief=tk.FLAT,  # Je kunt hier SUNKEN of GROOVE gebruiken voor meer zichtbaarheid
            anchor='w',      # Lijn links uit
            wraplength=300   # Voorkomt te breed worden op kleinere schermen
        )
        # Plaats het label in rij 0. Het neemt 3 kolommen in beslag (0, 1, 2)
        self.message_label.grid(row=0, column=0, columnspan=3, sticky='ew', padx=5, pady=(0, 5))

        # 1. LISTBOX met Scrollbar (NU IN RIJ 1)

        # De Listbox en Scrollbar staan nu in rij 1, niet meer in rij 0
        # Listbox neemt twee kolommen in
        self.move_listbox = tk.Listbox(parent_frame, height=20, font=("Consolas", 10), selectmode=tk.SINGLE)
        self.move_listbox.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(0, 10))

        # Scrollbar
        scrollbar = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL, command=self.move_listbox.yview)
        scrollbar.grid(row=1, column=2, sticky='ns', pady=(0, 10))
        self.move_listbox.config(yscrollcommand=scrollbar.set)

        # Zorg ervoor dat de Listbox verticaal uitrekt:
        parent_frame.grid_rowconfigure(1, weight=1)

        # 2. Knoppen (NU IN RIJ 2)

        button_frame = ttk.Frame(parent_frame)
        # Knoppen staan nu in rij 2
        button_frame.grid(row=2, column=0, columnspan=3, sticky='ew')

        ttk.Button(button_frame, text="Zet Ongedaan Maken", command=self._undo_move).pack(side=tk.LEFT, expand=True, fill='x', padx=5)
        ttk.Button(button_frame, text="PGN Opslaan...", command=self._save_pgn).pack(side=tk.LEFT, expand=True, fill='x', padx=5)

        # De Listbox (kolom 0 van de Listbox in parent_frame) moet horizontaal uitrekken
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(1, weight=1)

    def _draw_board(self):
        """Tekent de schaakbordvakjes."""
        self.board_canvas.delete("all")

        for r in range(8):
            for c in range(8):
                x1 = c * self.square_size
                y1 = r * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                color = self.color_light if (r + c) % 2 == 0 else self.color_dark
                tag = f"square_{chess.square_name(chess.square(c, 7-r))}"
                self.board_canvas.create_rectangle(x1, y1, x2, y2, fill=color, tags=("square", tag))

    def _draw_pieces(self):
        """
        Draws the pieces on a given Canvas, using PNG images.

        The original code that used Unicode characters has been replaced by code
        that uses the preloaded PNG images via canvas.create_image.
        """
        # First, delete any existing pieces
        self.board_canvas.delete("piece")
        # Current size of the Canvas
        board_size = min(self.board_canvas.winfo_width(), self.board_canvas.winfo_height())
        if board_size < 100:
            board_size = 400
        print("board_size", board_size)

        self.board_canvas.delete("all")

        square_size = self.square_size
        colors = ("#F0D9B5", "#B58863")  # Light and dark square colors
        # Unicode pieces (White: Uppercase, Black: Lowercase)
        piece_map = {
            'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
        }

        # Draw squares and pieces
        # print("self.image_manager.images")
        # for item in self.image_manager.images:
        #     print(item)
        # print("end self.image_manager.images")
        for row in range(8):
            for col in range(8):
                x1 = col * square_size
                y1 = row * square_size
                x2 = x1 + square_size
                y2 = y1 + square_size

                # Square color
                color_index = (row + col) % 2
                fill_color = colors[color_index]
                self.board_canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, tags="square")

                # Algebraic notation (for the border)
                file_char = chr(ord('a') + col)
                rank_char = str(8 - row)

                if col == 0:
                    self.board_canvas.create_text(x1 + 3, y1 + 3, text=rank_char, anchor="nw", font=('Arial', 8), fill=colors[1 - color_index])
                if row == 7:
                    self.board_canvas.create_text(x2 - 3, y2 - 3, text=file_char, anchor="se", font=('Arial', 8), fill=colors[1 - color_index])

                # Place the piece
                square_index = chess.square(col, 7 - row)
                piece = self.board.piece_at(square_index)

                if piece:
                    symbol = piece.symbol()
                    print(symbol)
                    if self.image_manager is None:
                     piece_char = piece_map.get(piece.symbol())
                     self.board_canvas.create_text(
                         x1 + square_size / 2,
                         y1 + square_size / 2,
                         text=piece_char,
                         font=('Arial', int(square_size * 0.7), 'bold'),
                         fill='black',
                         tags="piece"
                     )
                    else:
                     if symbol in self.image_manager.images:
                        # We retrieve the cached image from the manager
                        piece_img = self.image_manager.images.get(symbol)

                        # 3. Draw the image in the center of the square
                        self.board_canvas.create_image(
                            x1 + square_size / 2,
                            y1 + square_size / 2,
                            image=piece_img,
                            tags="piece"  # Use tags for easy removal/movement later
                        )
        return

        for square in chess.SQUARES:
            piece = self.board.piece_at(square)

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
                if symbol in self.image_manager.images:
                    # We retrieve the cached image from the manager
                    piece_img = self.image_manager.images.get(symbol)
                    print("symbol", symbol)
                    try:
                        # 3. Draw the image in the center of the square
                        self.board_canvas.create_image(
                            x, y,
                            image=piece_img,
                            tags="piece"  # Use tags for easy removal/movement later
                        )
                    except Exception as e:
                        print(e)

                # If the image is not loaded, the piece is skipped.


    def _on_board_click(self, event):
        """Verwerkt een klik op het schaakbord."""

        # Converteer pixelcoördinaten naar schaakveld (0-63)
        col = event.x // self.square_size
        row = event.y // self.square_size
        # Schaakveld in de range 0-63 (A1=0, H8=63)
        clicked_square = chess.square(col, 7 - row)

        if self.selected_square is None:
            self.message_label.config(text="")
            # Eerste klik: Selecteer een veld als er een stuk op staat van de juiste kleur
            if self.board.piece_at(clicked_square) and self.board.piece_at(clicked_square).color == self.board.turn:
                self.selected_square = clicked_square
                self._draw_board() # Herteken om de selectie te tonen
                self._draw_pieces()

                x1 = col * self.square_size
                y1 = row * self.square_size

                # Add a yellow highlight to the starting square
                self.board_canvas.create_rectangle(x1, y1, x1 + self.square_size, y1 + self.square_size,
                                            outline="#FFC300", width=4, tags="highlight")
                self.board_canvas.tag_raise("highlight", "square")
                self.board_canvas.tag_raise("text")
            else:
                # Klik op een leeg veld of een vijandelijk stuk
                print("Geen geldig stuk van de huidige speler geselecteerd.")
        else:
            # Tweede klik: Probeer de zet uit te voeren
            source_square = self.selected_square
            target_square = clicked_square

            # Reset selectie
            self.selected_square = None
            self._draw_board() # Herteken om de selectie te verwijderen
            self._draw_pieces()
            # Probeer de zet uit te voeren
            self._make_move(source_square, target_square)

    def _make_move(self, source, target):
        """Probeert een zet uit te voeren op basis van de bron- en doelvelden."""

        # Probeer de zet te creëren (standaard zet, promotie indien nodig)
        move = chess.Move(source, target)

        # Controleer voor promotie
        piece = self.board.piece_at(source)
        if piece and piece.piece_type == chess.PAWN and chess.square_rank(target) in [0, 7]:
            # Voor eenvoud, vraag de gebruiker om de promotie (meestal Q)
            # In een geavanceerde app zou hier een dialoogvenster komen.
            move = chess.Move(source, target, promotion=chess.QUEEN)

        if move in self.board.legal_moves:
            # Geldige zet: voer uit en update
            self.board.push(move)
            self.move_history.append(move)
            self._update_ui_after_move()

        else:
            # Ongeldige zet
            print(f"Ongeldige zet: {chess.square_name(source)}{chess.square_name(target)}")
            # Probeer alternatieve promoties voor het geval de standaard Q faalt (zeer zeldzaam)
            if piece and piece.piece_type == chess.PAWN and chess.square_rank(target) in [0, 7]:
                #messagebox.showerror("Ongeldige Zet", f"Ongeldige promotie naar Koningin. Probeer een andere veldcombinatie.")
                self.message_label.config(text="Ongeldige promotie.")
            else:
                #messagebox.showerror("Ongeldige Zet", "Dit is geen geldige zet.")
                self.message_label.config(text="Ongeldige zet! Probeer opnieuw.")

    def _update_ui_after_move(self):
        """Verfrist het bord en de zettenlijst na een zet."""
        self._draw_board()
        self._draw_pieces()
        self._update_move_list()

    def _update_move_list(self):
        """Actualiseert de Listbox met de geschiedenis van de zetten."""
        self.move_listbox.delete(0, tk.END)
        temp_board = chess.Board()
        move_text = []

        # Herbouw de zettenreeks en PGN-notatie
        for i, move in enumerate(self.move_history):
            try:
                # Zetnummer wordt alleen bij oneven index getoond (Witte zet)
                if i % 2 == 0:
                    move_number = (i // 2) + 1
                    prefix = f"{move_number}. "
                else:
                    prefix = ""

                # Formatteer de zet
                notation = temp_board.san(move)
                temp_board.push(move)

                move_text.append(prefix + notation)
            except Exception as e:
                # Dit zou niet mogen gebeuren met legale zetten, maar voor de zekerheid
                move_text.append(f"?? ({move.uci()})")
                break # Stop bij de eerste foute zet

        # Splits de zetten in paren voor de Listbox weergave
        listbox_entries = []
        for i in range(0, len(move_text), 2):
            white_move = move_text[i]
            black_move = move_text[i+1] if i + 1 < len(move_text) else ""

            # Formatteer als "1. e4 e5"
            entry = f"{white_move:<10} {black_move}"
            listbox_entries.append(entry)

        for entry in listbox_entries:
            self.move_listbox.insert(tk.END, entry)

        # Scroll naar de laatste zet
        self.move_listbox.see(tk.END)

    def _undo_move(self):
        """Haalt de laatste zet ongedaan."""
        if self.move_history:
            self.board.pop()
            self.move_history.pop()
            self._update_ui_after_move()
        else:
            messagebox.showinfo("Actie", "Er zijn geen zetten om ongedaan te maken.")

    def handle_close(self):
        """
        Deze functie wordt aangeroepen wanneer op het kruisje wordt geklikt.
        """

        # 1. Verwerk of Print de waarde van self.file_path
        print(f"Venster gesloten. De waarde van file_path is: {self.file_path}")

        # Optioneel: Gebruik de waarde voor verdere verwerking, bijv. teruggeven aan een ouder-venster.
        if not self.pgn_filepath is None and len(self.file_path) > 0:
            self.pgn_filepath.set(self.file_path)

        # 2. Sluit het venster handmatig
        # Aannemende dat 'master' het hoofdvenster is van deze klasse.
        self.master.destroy()

    def _save_pgn(self):
        """Genereert het PGN-bestand en slaat het op naar een bestand."""
        if not self.move_history:
            messagebox.showwarning("Opslaan Mislukt", "Voer eerst zetten in om een PGN te genereren.", parent=self.master)
            return

        # 1. Creeër de PGN Game instantie
        game = chess.pgn.Game()

        # 2. Stel de headers in
        for field, var in self.header_vars.items():
            game.headers[field] = var.get()

        # 3. Voeg de zetten toe
        node = game
        for move in self.move_history:
            node = node.add_variation(move)

        # 4. Formatteer naar PGN-string
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        pgn_string = game.accept(exporter)

        # 5. Opslaan via dialoogvenster
        file_path = filedialog.asksaveasfilename(
            parent=self.master,
            defaultextension=".pgn",
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")],
            title="Sla PGN-bestand op"
        )

        if file_path:
            self.file_path = file_path
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(pgn_string)
                messagebox.showinfo("Succes", f"PGN succesvol opgeslagen naar:\n{file_path}", parent=self.master)
            except Exception as e:
                messagebox.showerror("Fout bij Opslaan", f"Kon het bestand niet opslaan: {e}", parent=self.master)

if __name__ == '__main__':

    args = parse_args()

    piece_set = args.piece_set # New
    # Initializeer Tkinter
    root = tk.Tk()

    # Gebruik een try/except om te vangen als de 'chess' library ontbreekt in de omgeving
    try:
        IMAGE_DIRECTORY = "Images/piece"
        SQUARE_SIZE = 60  # Size of the squares in pixels
        # 2. Initialize the Asset Manager (LOADS IMAGES ONCE)
        # If this fails (e.g., FileNotFoundError), the program stops here.
        asset_manager = PieceImageManager1(60, IMAGE_DIRECTORY, piece_set)

        app = PGNEntryApp(root, asset_manager)
        root.mainloop()
    except Exception as e:
        # Dit is puur een melding voor de gebruiker indien ze de app lokaal draaien
        error_msg = (
            "Er is een opstartfout opgetreden. Controleer of de 'python-chess' "
            "bibliotheek is geïnstalleerd (bijv. via 'pip install python-chess').\n"
            f"Fout: {e}"
        )
        print(error_msg)
        tk.messagebox.showerror("Opstartfout", error_msg)
