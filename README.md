# Scribbler-Game---Socket-Programming
# 🎨 Scribble (Pictionary Multiplayer Game)

Welcome to **Scribble** – a real-time, multiplayer Pictionary game built with Python. Challenge your friends to guess the word you’re drawing, or show off your artistic skills as the drawer. This project consists of a server and client application using sockets, threading, and a beautiful Tkinter GUI.

---

## 🚀 Features

- **Multiplayer Support:** Play with 2 or more players on the same local network or over the internet.
- **Real-time Drawing Sync:** The drawer’s strokes appear instantly on all guessers’ canvases.
- **Robust GUI:** Clean, responsive Tkinter interface with:
  - Drawing canvas
  - Color selection and pen size controls
  - Eraser, Undo, and Clear Canvas tools
  - Live scoreboard and round info
  - Notifications and chat/guess area
- **Round System:** Each player gets a turn as the drawer. The number of rounds scales with player count.
- **Word Selection:** Random word is chosen for each round from a rich word bank.
- **Guessing & Hints:** Guessers type their guesses; drawers can send hints.
- **Scoring System:** Earn points based on how quickly you guess correctly.
- **Timer:** Each round has a countdown. If time runs out, no points are awarded.
- **Game Over Screen:** See final scores and the winner; option to play again.
- **Robust Networking:** Handles disconnects, duplicate usernames, and edge cases gracefully.

---

## 🖥️ Requirements

- **Python 3.x**
- **Tkinter** (usually included in standard Python installations)

No external packages needed!

---

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>
   ```

2. **(Optional) Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Ensure Tkinter is available:**
   - On most systems, Tkinter is pre-installed.
   - If you encounter issues, install with:
     - **Ubuntu/Debian:** `sudo apt-get install python3-tk`
     - **Mac:** Usually included
     - **Windows:** Included with Python installer

---

## 🏃‍♂️ Getting Started

### 1. **Start the Server**

Run on the host machine:
```bash
python server.py
```
- Default host: `0.0.0.0` (listens on all interfaces)
- Default port: `5555`

### 2. **Start Clients**

On each player’s machine:
```bash
python client.py
```
- Enter your username.
- Enter the server’s IP address (edit `HOST` in `client.py` if not on localhost).

### 3. **Play!**

- Click “Ready to Play” once all players are connected.
- One player becomes the drawer; others guess.
- Chat, draw, guess, and compete for the top score!

---

## 🌟 Game Flow

1. **Connection:** Players join and enter unique usernames.
2. **Ready Up:** Click “Ready to Play” to signal readiness.
3. **Rounds:** Each round, a player draws a randomly selected word.
4. **Guessing:** Other players try to guess the word via chat.
5. **Scoring:** Correct guessers earn points based on speed.
6. **Rotation:** Drawer rotates each round.
7. **Game Over:** After all rounds, scores are displayed. Play again or exit.

---

## ⚙️ Configuration

- **Host/Port:** Change `HOST` and `PORT` in `server.py` and `client.py` to run over LAN or internet.
- **Word Bank:** Add more words to the `WORDS` list in `server.py`.
- **Minimum Players:** Change `MIN_PLAYERS` in `server.py` (default: 2).

---

## 🛠️ Code Structure

- `server.py`: Manages connections, game state, timers, word selection, scoring, and broadcasts.
- `client.py`: Handles GUI, drawing, chat/guess input, server communication, and user state.

---

## 🔒 Security Notes

- This is a demo project for educational use. It’s not hardened for public deployment.
- Uses plain TCP sockets; no encryption.
- For WAN play, ensure proper port forwarding and firewall settings. Never expose to the internet without understanding the risks.

---


## 🎥 Screenshots
<img width="3060" height="1819" alt="scribble1" src="https://github.com/user-attachments/assets/f1aa333c-bee3-4bbc-8b3c-1c0bcbf7c18b" />
<img width="1532" height="946" alt="scribble2" src="https://github.com/user-attachments/assets/04421110-db88-4daf-a44c-9cea1e8592fd" />
<img width="1206" height="904" alt="scribble3" src="https://github.com/user-attachments/assets/18a83ccc-2b51-4316-8b0e-ef27354b94c6" />



Happy Drawing & Guessing! 🖌️✨
