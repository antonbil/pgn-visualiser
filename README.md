# PGN Utilities Suite & Event Visualiser

This Python project is a collection of desktop applications built using *tkinter* for comprehensive handling, editing, and analysis of chess games in PGN (Portable Game Notation) format.

The core application, `visualise-pgn.py`, analyzes games, identifies critical **events** (moves leading to a large centipawn advantage swing), and displays these key positions graphically.

## 🎯 Core Functionality (`visualise-pgn.py`)

The Event Visualiser automatically selects up to 6 key positions based on an advanced methodology: the biggest event from each of the three main phases of the game (opening, middlegame, endgame) plus the top three remaining events globally by score.

### Features

* **Advanced Event Detection:** Calculates the loss/gain in centipawns (cp) for every move based on embedded Stockfish evaluation comments in the PGN.
* **Critical Position Selection:** Uses an algorithm to select the most instructive events across the entire game, ensuring coverage of all game phases.
* **Visual Board Display:** Shows the state of the chessboard *before* the relevant move was played.
* **Detailed Analysis:** Provides the exact centipawn score before and after the move, and the total advantage lost.
* **PGN Snippets:** Displays the PGN notation, including variations, for the moves leading up to the displayed position.

## 📦 Project Structure and Stand-alone Scripts

The suite consists of three main runnable scripts:

| Script Name | Purpose | Stand-alone Usage |
| :--- | :--- | :--- |
| **`visualise-pgn.py`** | **Primary Tool.** Loads and analyzes PGNs, identifying and visualizing key events. | Requires a PGN file with evaluation comments. |
| **`pgn_entry.py`** | Provides a GUI for manual input and saving of a chess game into a PGN file. | Used for creating new PGN files. |
| **`pgn_editor.py`** | GUI tool for modifying an existing PGN file, including editing variations and comments. | Used for general PGN maintenance and correction. |

## ⚙️ Installation

This program requires the *python-chess* library.

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/antonbil/pgn-visualiser.git](https://github.com/antonbil/pgn-visualiser.git)
    cd pgn-visualiser
    ```

2.  **Install the required libraries:**
    ```bash
    pip install python-chess Pillow cairosvg
    ```

## ▶️ Usage and Startup Parameters

You can start the main analysis application (`visualise-pgn.py`) or the editor/entry tools. Startup parameters can override settings saved in the `config.json` file.

### Running the Main Visualiser

```bash
python visualise-pgn.py
```
### Command-line Arguments (for `pgn_editor.py` and `visualise-pgn.py`)

The applications accept the following command-line arguments to customize the launch environment:

| Argument | Shorthand | Description | `config.json` Key |
| :--- | :--- | :--- | :--- |
| `--pgn_game` | `-p` | Set the path to the PGN file to load on startup. | `lastLoadedPgnPath` |
| `--engine_name` | `-e` | Set the directory and name of the Stockfish engine executable. | `engine_path` |
| `--piece_set` | `-s` | Set the graphic style (piece set) for the chessboard. | `piece_set` |
| `--board` | `-o` | Set the color theme of the board squares (e.g., 'red', 'blue'). | `board` |
| `--square_size` | `-q` | Set the pixel size for each square on the chessboard. | `square_size` |

Example to launch the editor with specific visual settings:
```bash
python pgn_editor.py -p "my_game.pgn" -s "alpha" -q 70
```
## 📂 Configuration File

The application manages its state and default settings using the following configuration file:

* `settings/config.json`

This file is loaded on startup and updated every time relevant settings are changed in the GUI (e.g., loading a new PGN, changing piece set).

**Current structure of `config.json`:**

```json
{
    "default_directory": "/home/user/Chess",
    "lastLoadedPgnPath": "/home/user/Schaken/2025-december.pgn",
    "engine_path": "",
    "piece_set": "staunty",
    "square_size": 80,
    "board": "red"
}
```
## 💻 Code Highlights (The Engine of Analysis)

### `get_all_significant_moves(pgn_string)`

This function is the core of the event detection analysis.

1.  It reads the PGN and iterates through every move in the main line.
2.  It extracts the evaluation (*eval_after\_cp*) from the comment of the current move.
3.  It compares the evaluation *before* the move (*eval_before\_cp*) with the evaluation *after* the move.
4.  It calculates the absolute difference in advantage. For White, this is *eval\_before - eval\_after*; for Black, it is *eval\_after - eval\_before*.
5.  Moves with a difference greater than 50 centipawns are collected as "relevant."

### `select_key_positions`

This algorithm ensures a balanced analysis across the entire game.

* It divides the game into three roughly equal parts (opening, middlegame, endgame).
* It selects the biggest difference (the largest event) from **each** of these three sections.
* It then adds the top 3 remaining differences with the highest score globally.
* This results in a maximum of 6 visual diagrams covering the most critical moments of the game.

### `_format_pgn_history(move_list)`

This function is responsible for the clean display of the PGN fragments, ensuring correct notation for move numbers, comments, and most importantly, the **variations** as specified in the PGN standard.

## 🧑‍💻 About the Developer

* **Name:** Anton Bil
* **Email:** anton.bil.167@gmail.com
* **GitHub:** <https://github.com/antonbil/pgn-visualiser>

Feel free to report bugs or submit pull requests!
