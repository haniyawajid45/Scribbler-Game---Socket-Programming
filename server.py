import socket
import threading
import json
import random
import time

HOST = '0.0.0.0'  # Standard loopback interface address (localhost)
PORT = 5555       # Port to listen on (non-privileged ports are > 1023)

# Game State
clients = {}  # {client_socket: (username, address)}
game_state = {
    'status': 'waiting',  # 'waiting', 'playing', 'round_end', 'game_over'
    'drawer': None,       # username of the current drawer
    'word': None,         # current word to draw
    'drawing_data': [],   # list of (x1, y1, x2, y2, color, pen_size) tuples and None as stroke separators
    'guesses': [],        # list of (username, text) tuples (includes guesses and hints)
    'score': {},          # {username: score}
    'players_ready': 0,   # count of players who clicked "Ready"
    'current_round': 0,
    'max_rounds': 0,      # Will be set dynamically based on player count
    'round_timer': 90,    # 1.5 minutes per round (90 seconds)
    'round_start_time': 0,
    'player_order': [],   # To manage drawer rotation
    'current_drawer_index': -1
}

# --- Game Configuration ---
WORDS = [
    "apple", "house", "car", "tree", "ocean", "mountain", "keyboard", "robot", "galaxy", "pizza",
    "bicycle", "book", "camera", "chair", "cloud", "coffee", "dragon", "elephant", "flower", "guitar",
    "hamburger", "ice cream", "jellyfish", "kite", "lamp", "moon", "notebook", "octopus", "penguin", "rainbow",
    "snake", "star", "sun", "table", "telephone", "umbrella", "volcano", "watermelon", "xylophone", "zebra",
    "backpack", "bridge", "castle", "diamond", "fireworks", "globe", "headphones", "island", "jacket", "ketchup",
    "lemon", "magnet", "newspaper", "orange", "pillow", "queen", "rocket", "scissors", "television", "unicorn",
    "violin", "window", "yarn", "zipper", "acorn", "barrel", "candle", "door", "envelope", "feather", "glasses",
    "hat", "igloo", "jungle", "koala", "ladder", "mirror", "needle", "onion", "paint", "quilt", "river",
    "sandwich", "teapot", "vampire", "whale", "x-ray", "yogurt", "zeppelin"
]
MIN_PLAYERS = 2 # Minimum players to start the game

def broadcast(message_type, data, exclude_socket=None):
    """Sends a message to all connected clients."""
    full_message = json.dumps({'type': message_type, 'data': data}) + '\n'
    for client_socket in list(clients.keys()): # Use list() to avoid RuntimeError: dictionary changed size during iteration
        if client_socket != exclude_socket:
            try:
                client_socket.sendall(full_message.encode('utf-8'))
            except Exception as e:
                print(f"Error broadcasting to {clients.get(client_socket, ('unknown', ''))[0]}: {e}")
                remove_client(client_socket)

def send_to_client(client_socket, message_type, data):
    """Sends a specific message to a single client."""
    full_message = json.dumps({'type': message_type, 'data': data}) + '\n'
    try:
        client_socket.sendall(full_message.encode('utf-8'))
    except Exception as e:
        print(f"Error sending to {clients.get(client_socket, ('unknown', ''))[0]}: {e}")
        remove_client(client_socket)

def remove_client(client_socket):
    """Removes a disconnected client."""
    if client_socket in clients:
        username, addr = clients.pop(client_socket)
        print(f"Client {username} disconnected.")
        
        game_state['score'].pop(username, None)
        
        if username in game_state['player_order']:
            game_state['player_order'].remove(username)
            if game_state['current_drawer_index'] >= len(game_state['player_order']):
                game_state['current_drawer_index'] = 0 if game_state['player_order'] else -1

        broadcast('notification', {'message': f"{username} has left the game."})
        broadcast('player_list_update', {'scores': game_state['score']})
        
        if game_state['drawer'] == username and game_state['status'] == 'playing':
            print(f"{username} (the drawer) left. Ending round.")
            end_round()
        
        if game_state['status'] != 'waiting' and len(clients) < MIN_PLAYERS:
            print("Not enough players to continue. Ending game.")
            broadcast('notification', {'message': "Not enough players to continue. Game Over!"})
            end_game()

    try:
        client_socket.close()
    except Exception as e:
        print(f"Error closing socket for disconnected client: {e}")


def start_new_round():
    """Initializes a new drawing round."""
    game_state['status'] = 'playing'
    game_state['current_round'] += 1
    
    player_usernames = list(game_state['score'].keys())

    if len(player_usernames) < MIN_PLAYERS:
        broadcast('notification', {'message': "Not enough players to start a new round. Game Over!"})
        end_game()
        return

    if game_state['current_round'] > game_state['max_rounds']:
        end_game()
        return

    if not game_state['player_order']:
        game_state['player_order'] = player_usernames
        random.shuffle(game_state['player_order'])
        game_state['current_drawer_index'] = -1
    
    game_state['current_drawer_index'] = (game_state['current_drawer_index'] + 1) % len(game_state['player_order'])
    game_state['drawer'] = game_state['player_order'][game_state['current_drawer_index']]
    game_state['word'] = random.choice(WORDS)
    game_state['drawing_data'].clear()
    game_state['guesses'].clear()
    game_state['round_start_time'] = time.time()

    print(f"--- Round {game_state['current_round']}/{game_state['max_rounds']} | Drawer: {game_state['drawer']}, Word: {game_state['word']} ---")

    for sock, (username, _) in clients.items():
        is_drawer = (username == game_state['drawer'])
        send_to_client(sock, 'new_round', {
            'drawer': game_state['drawer'],
            'word': game_state['word'] if is_drawer else '????',
            'word_length': len(game_state['word']) if not is_drawer else None,
            'current_round': game_state['current_round'],
            'max_rounds': game_state['max_rounds'],
        })
    broadcast('notification', {'message': f"Round {game_state['current_round']}! {game_state['drawer']} is drawing."})

def end_round(guesser_username=None):
    """Ends the current drawing round."""
    game_state['status'] = 'round_end'
    message = f"Round over! The word was '{game_state['word']}'."
    if guesser_username:
        message += f" {guesser_username} guessed correctly!"
    
    broadcast('round_end', {
        'message': message,
        'correct_word': game_state['word'],
        'current_scores': game_state['score']
    })

    threading.Timer(5.0, start_new_round_or_end_game).start()

def start_new_round_or_end_game():
    if game_state['current_round'] >= game_state['max_rounds']:
        end_game()
    else:
        start_new_round()

def end_game():
    """Ends the entire game and determines the winner."""
    game_state['status'] = 'game_over'
    winner = None
    if game_state['score']:
        winner = max(game_state['score'], key=game_state['score'].get)

    message = "Game Over!"
    if winner:
        message += f" The winner is {winner} with {game_state['score'][winner]} points!"

    broadcast('game_over', {
        'message': message,
        'final_scores': game_state['score'],
        'winner': winner
    })
    
    print(f"Game Over. Final Scores: {game_state['score']}")
    # Reset for a new game
    game_state.update({
        'status': 'waiting',
        'drawer': None,
        'word': None,
        'drawing_data': [],
        'guesses': [],
        'players_ready': 0,
        'current_round': 0,
        'player_order': [],
        'current_drawer_index': -1,
    })
    for user in game_state['score']:
        game_state['score'][user] = 0

def game_timer_tick():
    """Handles the round timer."""
    if game_state['status'] == 'playing':
        elapsed = time.time() - game_state['round_start_time']
        remaining = max(0, game_state['round_timer'] - elapsed)
        broadcast('timer_update', {'time_left': int(remaining)})

        if remaining == 0:
            end_round()
    
    threading.Timer(1.0, game_timer_tick).start()

def handle_client(conn, addr):
    """Handles incoming messages from a single client."""
    print(f"New connection from {addr}")
    username = None
    buffer = ""
    try:
        # First message must be 'join'
        initial_data = conn.recv(1024).decode('utf-8')
        if not initial_data: return
        
        buffer += initial_data
        if '\n' in buffer:
            line, buffer = buffer.split('\n', 1)
            msg = json.loads(line)
            
            if msg['type'] == 'join':
                username = msg['data']['username']
                if username in [u for u, _ in clients.values()]:
                    send_to_client(conn, 'error', {'message': "Username already taken."})
                    return
                
                clients[conn] = (username, addr)
                game_state['score'][username] = 0
                
                broadcast('notification', {'message': f"{username} has joined the game!"})
                broadcast('player_list_update', {'scores': game_state['score']})

                send_to_client(conn, 'current_state', {
                    'status': game_state['status'],
                    'drawer': game_state['drawer'],
                    'word': game_state['word'] if game_state['drawer'] == username else '????',
                    'word_length': len(game_state['word']) if game_state['status'] == 'playing' and game_state['drawer'] != username else None,
                    'drawing_data': game_state['drawing_data'],
                    'guesses': game_state['guesses'],
                    'score': game_state['score'],
                    'current_round': game_state['current_round'],
                    'max_rounds': game_state['max_rounds']
                })
            else:
                return
        else:
            return

        # Main message loop
        while True:
            data = conn.recv(4096).decode('utf-8')
            if not data: break
            
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if not line: continue
                
                msg = json.loads(line)
                msg_type = msg.get('type')
                msg_data = msg.get('data')

                is_drawer = (username == game_state['drawer'])
                
                if msg_type == 'drawing_point' and is_drawer:
                    game_state['drawing_data'].append(msg_data)
                    broadcast('drawing_update', msg_data, exclude_socket=conn)

                elif msg_type == 'end_stroke' and is_drawer:
                    game_state['drawing_data'].append(None)

                elif msg_type == 'clear_canvas' and is_drawer:
                    game_state['drawing_data'].clear()
                    broadcast('clear_canvas_event', {})

                elif msg_type == 'undo_last_draw' and is_drawer:
                    if game_state['drawing_data']:
                        try:
                            if game_state['drawing_data'][-1] is None:
                                game_state['drawing_data'].pop()
                            
                            while game_state['drawing_data'] and game_state['drawing_data'][-1] is not None:
                                game_state['drawing_data'].pop()
                            
                            broadcast('full_drawing_update', {'drawing_data': game_state['drawing_data']})
                        except IndexError:
                            broadcast('full_drawing_update', {'drawing_data': []})
                    else:
                        send_to_client(conn, 'notification', {'message': "Nothing to undo."})

                elif msg_type == 'chat_input':
                    text = msg_data.get('text', '').strip()
                    if not text: continue

                    if game_state['status'] == 'playing':
                        if is_drawer:
                            game_state['guesses'].append((f"HINT from {username}", text))
                            broadcast('guess_hint_message', {'username': f"HINT from {username}", 'message': text})
                        else: # It's a guess
                            game_state['guesses'].append((username, text))
                            broadcast('guess_hint_message', {'username': username, 'message': text})
                            if text.lower() == game_state['word'].lower():
                                time_left = game_state['round_timer'] - (time.time() - game_state['round_start_time'])
                                points = 10 + int(5 * (time_left / game_state['round_timer']))
                                game_state['score'][username] += points
                                # --- MODIFICATION: The following line has been removed ---
                                # game_state['score'][game_state['drawer']] += 5 
                                end_round(guesser_username=username)
                    else: # General chat
                        broadcast('chat_message', {'username': username, 'message': text})

                elif msg_type == 'ready':
                    if game_state['status'] in ['waiting', 'game_over']:
                        game_state['players_ready'] += 1
                        broadcast('notification', {'message': f"{username} is ready! ({game_state['players_ready']}/{len(clients)} ready)"})
                        
                        if len(clients) >= MIN_PLAYERS and game_state['players_ready'] == len(clients):
                            game_state['max_rounds'] = len(clients) * 3 
                            game_state['players_ready'] = 0 
                            start_new_round()

    except (ConnectionResetError, json.JSONDecodeError) as e:
        print(f"Connection error with {username or addr}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred with client {username or addr}: {e}")
    finally:
        if conn in clients:
            remove_client(conn)


def start_server():
    """Starts the main server listener."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"🎨 Scribble server listening on {HOST}:{PORT}")
        threading.Thread(target=game_timer_tick, daemon=True).start()

        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            client_thread.start()

    except OSError as e:
        print(f"Failed to start server: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()