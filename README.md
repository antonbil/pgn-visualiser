# PGN Events Visualiser

This Python project is a desktop application built using *tkinter* that
analyzes chess games in PGN (Portable Game Notation) format. It
identifies the most significant \"events\" (moves leading to a large
loss or gain of centipawn advantage) and visualizes these critical
positions on a graphical chessboard.

The tool automatically selects up to 6 key positions based on an
advanced methodology: the biggest event from each of the three main
phases of the game (opening, middlegame, endgame) plus the top three
remaining events globally by score.

## Features

-   **Advanced **Event** Detection:** Calculates the loss/gain in
    centipawns (cp) for every move based on embedded Stockfish
    evaluation comments in the PGN.
-   **Critical Position Selection:** Uses an algorithm to select the
    most instructive events across the entire game.
-   **Visual Board Display:** Shows the state of the chessboard *before*
    the blundering move was played.
-   **Detailed Analysis:** Provides the exact centipawn score before and
    after the move, and the total advantage lost.
-   **PGN Snippets:** Displays the PGN notation, including variations,
    for the moves leading up to the displayed position.

## Installation

This program requires the *python-chess* library.

1.  **Clone the repository:**

    *git clone
    \[https://github.com/antonbil/pgn-visualiser.git\](https://github.com/antonbil/pgn-visualiser.git)*

    *cd pgn-visualiser*

2.  **Install the required library:**

    *pip install python-chess*

## Usage

1.  **Run the script:**

    *python visualise-pgn.py*

2.  View and Interact:
    The application will launch and display initial metadata.
    Load Simulation: Click the "Select PGN FIle" button. This action performs two functions:

    1. It loads a PGN game from file, instantly updating all displayed metadata (players, result, ELOs).
    2. It saves the PGN file path to the configuration file.

Configuration File:

The application manages its state using the following configuration file:

    *settings/config.json*
    
This file stores the default_directory and lastLoadedPgnPath settings, which are loaded on startup and updated every time a new PGN is loaded (simulated or real).

## Code Highlights

### *get_all_significant_blunders(pgn_string)*

This function is the core of the analysis.

1.  It reads the PGN and iterates through every move in the main line.
2.  It extracts the evaluation (*eval_after_cp*) from the comment of the
    current move.
3.  It compares the evaluation *before* the move (*eval_before_cp*) with
    the evaluation *after* the move.
4.  It calculates the absolute loss in advantage. For White, this is
    *eval_before - eval_after*; for Black, it is *eval_after -
    eval_before*.
5.  Moves with a loss greater than 50 centipawns are collected as
    \"blunders.\"

### *select_key_positions(all_blunders)*

This algorithm ensures a balanced analysis across the entire game.

-   It divides the game into three roughly equal parts (opening,
    middlegame, endgame).
-   It selects the biggest blunder from **each** of these three
    sections.
-   It then adds the top 3 remaining blunders with the highest score.
-   This results in a maximum of 6 visual diagrams covering the most
    critical moments of the game.

### *\_format_pgn_history(move_list)*

This function is responsible for the clean display of the PGN fragments,
ensuring correct notation for move numbers, comments, and most
importantly, the **variations** as specified in the PGN standard.

## About the Developer

-   **Name:** Anton Bil
-   **Email:** anton.bil.167@gmail.com
-   **GitHub:** <https://github.com/antonbil/pgn-visualiser>

Feel free to report bugs or submit pull requests!
