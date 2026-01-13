# Chess Tactics Master

A robust Python application for training chess puzzles from your own PGN databases. This app tracks your score, provides hints, and supports various PGN formats.

## ✨ Features
* **Flexible PGN Import**: Supports standard PGNs and specific "training" formats where the first move is an introductory move by the opponent.
* **Progress Tracking**: Saves your score and solved puzzles per file in a local JSON database.
* **Recent Files**: Quickly switch between different puzzle sets (e.g., Mate in 3, Endgames, Middlegame tactics).
* **Analysis Mode**: Review the full solution and play through variations in a separate detail window after solving.
* **Smart UI**: Automatic board orientation (flipping) based on the side to move.
* **English Codebase**: All internal logic and comments are maintained in English for consistency.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone [https://github.com/YOUR-USERNAME/chess-tactics-master.git](https://github.com/YOUR-USERNAME/chess-tactics-master.git)
   cd chess-tactics-master
   ```
2. **Install dependencies**: This app requires python-chess and Pillow.

```bash
pip install python-chess Pillow
```
Resources: Ensure a folder named Images/ is present containing the chess piece icons (e.g., wP.png, bR.png, etc.).

## 🚀 Usage
Start the application using:

```bash

python puzzle_manager.py [your_file.pgn]
```
If no file is provided, the app starts with an example puzzle, allowing you to select a file via File -> Load PGN.
## 📂 PGN Formats
The app automatically detects two types of PGN files:

Standard PGN: The solution starts at the very first move in the PGN.

Training PGN: If player names contain "White wins" or "Black wins", the first move is treated as the opponent's "setup move," and the puzzle starts immediately after.

## ⚙️ Configuration
The app automatically generates two types of files:

- config.json: Stores the list of recently opened files.
- [filename]_results.json: Stores your score and history for that specific database.

## 📝 License
This project is open-source. Feel free to modify and improve it!
