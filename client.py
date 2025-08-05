import socket
import threading
import json
import tkinter as tk
from tkinter import simpledialog, messagebox
import sys

HOST = '127.0.0.1'  # IMPORTANT: Use '127.0.0.1' for localhost, or the actual IP of the server machine
PORT = 5555      # The port used by the server

class PictionaryClient:
    def __init__(self, master): # Initialize the client with the main window
        self.master = master # Store the master window reference
        master.title("Scribble") 
        master.geometry("1000x700")

        self.username = None # Username for the player
        self.sock = None
        self.is_drawer = False
        self.current_word = "????" # Actual word for drawer, '????' for guessers
        self.current_word_length = None # Length for guessers
        self.game_status = 'waiting' # 'waiting', 'playing', 'round_end', 'game_over'
        self.current_round = 0
        self.max_rounds = 0

        self.drawing_history = [] # Stores drawing commands received

        # --- GUI Elements ---
        self.create_widgets() # Create the GUI elements

        self.ask_username() # Ask for username before connecting to the server

    def create_widgets(self):
        # Top Frame for Game Info
        top_frame = tk.Frame(self.master, bd=2, relief="groove")
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.status_label = tk.Label(top_frame, text="Status: Waiting for game to start...", font=("Arial", 12))
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.round_label = tk.Label(top_frame, text="Round: N/A", font=("Arial", 12))
        self.round_label.pack(side=tk.LEFT, padx=10)

        self.drawer_label = tk.Label(top_frame, text="Drawer: N/A", font=("Arial", 12))
        self.drawer_label.pack(side=tk.LEFT, padx=10)

        self.word_label = tk.Label(top_frame, text="Word: ????", font=("Arial", 12, "bold"))
        self.word_label.pack(side=tk.LEFT, padx=10)

        self.timer_label = tk.Label(top_frame, text="Time: --", font=("Arial", 12))
        self.timer_label.pack(side=tk.RIGHT, padx=10)

        # Drawing Canvas
        self.canvas_frame = tk.Frame(self.master, bd=2, relief="sunken")
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(self.canvas_frame, bg="white", width=600, height=400)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.end_draw)

        # Right Panel for Chat and Controls
        right_panel = tk.Frame(self.master, bd=2, relief="groove", width=300)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)
        right_panel.pack_propagate(False) # Prevent frame from shrinking

        # Scoreboard
        self.score_label = tk.Label(right_panel, text="Scores:", font=("Arial", 10, "bold"))
        self.score_label.pack(pady=5)
        self.scoreboard = tk.Label(right_panel, text="", justify=tk.LEFT, font=("Arial", 10))
        self.scoreboard.pack(pady=5, padx=5, fill=tk.X)

        # Notification Area (SERVER messages)
        self.notification_label = tk.Label(right_panel, text="Notifications:", font=("Arial", 10, "bold"))
        self.notification_label.pack(pady=5)
        self.notification_display = tk.Text(right_panel, state=tk.DISABLED, wrap=tk.WORD, height=5, width=40, bg="#e0e0e0")
        self.notification_display.pack(padx=5, pady=2, fill=tk.X)

        # Guess/Hint/Chat Area (Player messages)
        self.guess_chat_label = tk.Label(right_panel, text="Guesses, Hints & Chat:", font=("Arial", 10, "bold"))
        self.guess_chat_label.pack(pady=5)
        self.guess_chat_display = tk.Text(right_panel, state=tk.DISABLED, wrap=tk.WORD, height=15, width=40)
        self.guess_chat_display.pack(padx=5, pady=2, fill=tk.BOTH, expand=True)

        self.chat_entry = tk.Entry(right_panel, width=40)
        self.chat_entry.pack(pady=2, padx=5, fill=tk.X)
        self.chat_entry.bind("<Return>", self.send_chat_input)
        self.send_button = tk.Button(right_panel, text="Send", command=self.send_chat_input)
        self.send_button.pack(pady=2)


        # --- MODIFICATION: Drawing Tools now use the GRID layout manager ---
        self.tool_frame = tk.Frame(right_panel, bd=1, relief="ridge")
        self.tool_frame.pack(pady=10, padx=5, fill=tk.X)

        self.color_var = tk.StringVar(value="black")
        self.colors = ["black", "red", "blue", "green", "orange", "purple", "brown"]
        
        # Row 0: Color swatches
        for i, color in enumerate(self.colors):
            btn = tk.Button(self.tool_frame, bg=color, width=3, height=1, command=lambda c=color: self.set_color(c))
            btn.grid(row=0, column=i, padx=2, pady=2)
        
        # Row 1: Eraser Button (now includes the white color swatch)
        self.eraser_button = tk.Button(self.tool_frame, text="Eraser", command=lambda: self.set_color("white"))
        self.eraser_button.grid(row=1, column=0, columnspan=len(self.colors), sticky="ew", padx=2, pady=3)

        # Row 2: Pen Size Slider. This should now be clearly visible.
        self.pen_size_var = tk.IntVar(value=3)
        self.pen_size_label = tk.Label(self.tool_frame, text="Pen Size:")
        self.pen_size_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=2)
        self.pen_size_slider = tk.Scale(self.tool_frame, from_=1, to=15, orient=tk.HORIZONTAL, variable=self.pen_size_var, showvalue=0)
        self.pen_size_slider.grid(row=2, column=2, columnspan=len(self.colors)-2, sticky="ew")

        # Row 3: Control Buttons
        button_frame = tk.Frame(self.tool_frame)
        button_frame.grid(row=3, column=0, columnspan=len(self.colors), pady=5)
        
        self.undo_button = tk.Button(button_frame, text="Undo", command=self.send_undo_request)
        self.undo_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = tk.Button(button_frame, text="Clear Canvas", command=self.clear_my_canvas)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.tool_frame.pack_forget() # Hide by default

        # Ready Button
        self.ready_button = tk.Button(self.master, text="Ready to Play", command=self.send_ready)
        self.ready_button.pack(pady=10)

        # Store last drawing position
        self.last_x = None
        self.last_y = None

    def ask_username(self):
        self.username = simpledialog.askstring("Username", "Enter your username:", parent=self.master)
        if not self.username:
            self.master.destroy()
            sys.exit()
        self.connect_to_server()

    def connect_to_server(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            self.add_to_notification(f"Connected to server at {HOST}:{PORT}")

            join_message = json.dumps({'type': 'join', 'data': {'username': self.username}}) + '\n'
            self.sock.sendall(join_message.encode('utf-8'))

            threading.Thread(target=self.listen_for_messages, daemon=True).start()

        except ConnectionRefusedError:
            messagebox.showerror("Connection Error", "Could not connect to the server. Is it running? Is the IP correct?")
            self.master.destroy()
            sys.exit()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.master.destroy()
            sys.exit()

    def listen_for_messages(self):
        buffer = ""
        while True:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    try:
                        message = json.loads(line)
                        self.process_server_message(message)
                    except json.JSONDecodeError as e:
                        print(f"JSON Decode Error: {e} - Data: {line}")
                    except Exception as e:
                        print(f"Error processing message: {e}")
            except OSError as e:
                print(f"Socket error or closed: {e}")
                break
            except Exception as e:
                print(f"Unhandled error in listen_for_messages: {e}")
                break
        self.add_to_notification("Disconnected from server.")
        if self.sock:
            self.sock.close()
            self.sock = None
        if self.game_status != 'game_over':
            self.master.after(0, lambda: messagebox.showinfo("Disconnected", "You have been disconnected from the server."))
            self.master.after(0, self.master.destroy)
            self.master.after(0, sys.exit)


    def process_server_message(self, message):
        msg_type = message.get('type')
        msg_data = message.get('data')

        self.master.after(0, lambda: self.update_gui(msg_type, msg_data))

    def update_gui(self, msg_type, msg_data):
        if msg_type == 'drawing_update':
            self.draw_line_on_canvas(msg_data)
        elif msg_type == 'full_drawing_update': 
            self.clear_canvas_gui()
            self.drawing_history = [] 
            for draw_cmd in msg_data['drawing_data']:
                self.draw_line_on_canvas(draw_cmd) 
        elif msg_type == 'chat_message':
            self.add_to_guess_chat(msg_data['username'], msg_data['message']) 
        elif msg_type == 'guess_hint_message': 
            self.add_to_guess_chat(msg_data['username'], msg_data['message'])
        elif msg_type == 'notification':
            self.add_to_notification(msg_data['message'])
        elif msg_type == 'new_round':
            self.game_status = 'playing'
            self.drawer_label.config(text=f"Drawer: {msg_data['drawer']}")
            self.is_drawer = (self.username == msg_data['drawer'])
            self.current_round = msg_data['current_round']
            self.max_rounds = msg_data['max_rounds']
            self.round_label.config(text=f"Round: {self.current_round}/{self.max_rounds}")
            self.status_label.config(text="Status: Drawing")
            self.clear_canvas_gui()
            self.drawing_history = []
            self.guess_chat_display.config(state=tk.NORMAL) 
            self.guess_chat_display.delete(1.0, tk.END)
            self.guess_chat_display.config(state=tk.DISABLED)

            if self.is_drawer:
                self.current_word = msg_data['word'] 
                self.word_label.config(text=f"Word: {self.current_word}")
                self.tool_frame.pack(pady=10, padx=5, fill=tk.X)
                self.add_to_notification(f"You are drawing! Your word is: {self.current_word}")
                self.send_button.config(text="Send Hint/Chat") 
            else:
                self.current_word = '????' 
                self.current_word_length = msg_data['word_length']
                if self.current_word_length is not None:
                    self.word_label.config(text=f"Word: {'_ ' * self.current_word_length}") 
                    self.add_to_notification(f"{msg_data['drawer']} is drawing. Guess the {self.current_word_length}-letter word!")
                else:
                    self.word_label.config(text=f"Word: ????")
                    self.add_to_notification(f"{msg_data['drawer']} is drawing. Guess the word!")
                self.tool_frame.pack_forget()
                self.send_button.config(text="Send Guess/Chat") 
            self.ready_button.pack_forget()

        elif msg_type == 'round_end':
            self.game_status = 'round_end'
            self.status_label.config(text="Status: Round Ended!")
            self.word_label.config(text=f"Word: {msg_data['correct_word']}") 
            self.is_drawer = False
            self.tool_frame.pack_forget()
            self.clear_canvas_gui()
            self.drawing_history = []
            self.send_button.config(text="Send Chat") 

            self.update_scores(msg_data['current_scores'])
            self.add_to_notification(msg_data['message'])

        elif msg_type == 'game_over':
            self.game_status = 'game_over'
            self.status_label.config(text="Status: Game Over!")
            self.word_label.config(text="Word: N/A")
            self.drawer_label.config(text="Drawer: N/A")
            self.round_label.config(text="Round: N/A")
            self.timer_label.config(text="Time: --")
            self.is_drawer = False
            self.tool_frame.pack_forget()
            self.clear_canvas_gui()
            self.drawing_history = []
            self.send_button.config(text="Send Chat")

            self.update_scores(msg_data['final_scores'])
            self.add_to_notification(msg_data['message'])

            winner_text = "No winner."
            if msg_data['winner']:
                winner_score = msg_data['final_scores'].get(msg_data['winner'], 0)
                winner_text = f"The winner is {msg_data['winner']} with a score of {winner_score}!"
            
            response = messagebox.askquestion("Game Over!", f"Game Over!\n\nFinal Scores:\n{self.scoreboard.cget('text')}\n\n{winner_text}\n\nWould you like to play again?", type=messagebox.YESNO)
            if response == 'yes':
                self.reset_game_state()
                self.send_ready()
            else:
                self.on_closing() 

            self.ready_button.pack(pady=10) 

        elif msg_type == 'current_state':
            self.game_status = msg_data['status']
            self.drawer_label.config(text=f"Drawer: {msg_data['drawer'] or 'N/A'}")

            self.is_drawer = (self.username == msg_data['drawer']) 
            if self.game_status == 'playing':
                if self.is_drawer:
                    self.current_word = msg_data['word']
                    self.word_label.config(text=f"Word: {self.current_word}")
                    self.tool_frame.pack(pady=10, padx=5, fill=tk.X)
                    self.send_button.config(text="Send Hint/Chat")
                else:
                    self.current_word_length = msg_data['word_length']
                    if self.current_word_length is not None:
                        self.word_label.config(text=f"Word: {'_ ' * self.current_word_length}") 
                    else:
                        self.word_label.config(text="Word: ????")
                    self.tool_frame.pack_forget()
                    self.send_button.config(text="Send Guess/Chat")
            else:
                self.word_label.config(text="Word: ????")
                self.tool_frame.pack_forget()
                self.send_button.config(text="Send Chat")


            self.round_label.config(text=f"Round: {msg_data['current_round']}/{msg_data['max_rounds'] or 'N/A'}")
            self.update_scores(msg_data['score'])
            for draw_cmd in msg_data['drawing_data']:
                self.draw_line_on_canvas(draw_cmd)
            for username, text in msg_data['guesses']: 
                self.add_to_guess_chat(username, text)
            self.add_to_notification("Welcome to Scribble! Click 'Ready to Play' to start.")
            if self.game_status == 'waiting' and all(score == 0 for score in msg_data['score'].values()):
                self.ready_button.config(state=tk.NORMAL, text="Ready to Play")


        elif msg_type == 'player_list_update': 
            self.update_scores(msg_data['scores'])

        elif msg_type == 'clear_canvas_event':
            self.clear_canvas_gui()
            self.drawing_history = []
        elif msg_type == 'timer_update':
            self.timer_label.config(text=f"Time: {msg_data['time_left']}s")
        elif msg_type == 'error':
            messagebox.showerror("Server Error", msg_data['message'])
            if msg_data['message'] == "Username already taken.":
                self.master.destroy()
                root = tk.Tk()
                client = PictionaryClient(root)
                root.mainloop()

    def add_to_notification(self, message):
        self.notification_display.config(state=tk.NORMAL)
        self.notification_display.insert(tk.END, f"SERVER: {message}\n")
        self.notification_display.config(state=tk.DISABLED)
        self.notification_display.see(tk.END)

    def add_to_guess_chat(self, username, message):
        self.guess_chat_display.config(state=tk.NORMAL)
        self.guess_chat_display.insert(tk.END, f"{username}: {message}\n")
        self.guess_chat_display.config(state=tk.DISABLED)
        self.guess_chat_display.see(tk.END)

    def update_scores(self, scores):
        score_text = "Scores:\n"
        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        for user, score in sorted_scores:
            score_text += f"{user}: {score}\n"
        self.scoreboard.config(text=score_text)

    # --- Drawing Logic ---
    def start_draw(self, event):
        if self.is_drawer and self.game_status == 'playing':
            self.last_x, self.last_y = event.x, event.y
            x, y = event.x, event.y
            color = self.color_var.get()
            pen_size = self.pen_size_var.get()
            self.canvas.create_line((x, y, x, y), fill=color, width=pen_size, capstyle=tk.ROUND)
            draw_cmd = (x, y, x, y, color, pen_size)
            self.send_message('drawing_point', draw_cmd)

    def draw(self, event):
        if self.is_drawer and self.game_status == 'playing':
            x, y = event.x, event.y
            color = self.color_var.get()
            pen_size = self.pen_size_var.get()

            if self.last_x is not None and self.last_y is not None:
                self.canvas.create_line((self.last_x, self.last_y, x, y), fill=color, width=pen_size, capstyle=tk.ROUND, smooth=tk.TRUE)
                draw_cmd = (self.last_x, self.last_y, x, y, color, pen_size)
                self.send_message('drawing_point', draw_cmd)
            
            self.last_x, self.last_y = x, y

    def end_draw(self, event):
        self.last_x = None
        self.last_y = None
        if self.is_drawer and self.game_status == 'playing':
            self.send_message('end_stroke', {})

    def draw_line_on_canvas(self, draw_cmd):
        if draw_cmd is None:
            return

        if len(draw_cmd) == 6:
            x1, y1, x2, y2, color, pen_size = draw_cmd
            self.canvas.create_line((x1, y1, x2, y2), fill=color, width=pen_size, capstyle=tk.ROUND, smooth=tk.TRUE)
            self.drawing_history.append(draw_cmd)
        else:
            print(f"Unknown drawing command format received: {draw_cmd}")


    def clear_canvas_gui(self):
        self.canvas.delete("all")

    def clear_my_canvas(self):
        if self.is_drawer and self.game_status == 'playing':
            self.send_message('clear_canvas', {})

    def send_undo_request(self):
        if self.is_drawer and self.game_status == 'playing':
            self.send_message('undo_last_draw', {})
        else:
            self.add_to_notification("You can only undo if you are the drawer.")

    def set_color(self, color):
        self.color_var.set(color)

    def send_chat_input(self, event=None):
        text = self.chat_entry.get().strip()
        self.chat_entry.delete(0, tk.END)
        if not text:
            return
        self.send_message('chat_input', {'text': text})

    def send_message(self, message_type, data):
        if self.sock:
            try:
                full_message = json.dumps({'type': message_type, 'data': data}) + '\n'
                self.sock.sendall(full_message.encode('utf-8'))
            except OSError as e:
                print(f"Error sending message (socket might be closed): {e}")
                self.master.after(0, lambda: messagebox.showerror("Connection Error", "Lost connection to server."))
                self.master.after(0, self.master.destroy)
                self.master.after(0, sys.exit)
            except Exception as e:
                print(f"Error sending message: {e}")

    def send_ready(self):
        if self.game_status == 'waiting' or self.game_status == 'game_over':
            self.send_message('ready', {})
            self.ready_button.config(state=tk.DISABLED, text="Waiting for others...")
            self.game_status = 'waiting'
            self.clear_canvas_gui()
            self.drawing_history = []
            self.guess_chat_display.config(state=tk.NORMAL)
            self.guess_chat_display.delete(1.0, tk.END)
            self.guess_chat_display.config(state=tk.DISABLED)
            self.notification_display.config(state=tk.NORMAL)
            self.notification_display.delete(1.0, tk.END)
            self.notification_display.config(state=tk.DISABLED)
            self.update_scores({})
            self.status_label.config(text="Status: Waiting for game to start...")
            self.word_label.config(text="Word: ????")
            self.drawer_label.config(text="Drawer: N/A")
            self.round_label.config(text="Round: N/A")
            self.timer_label.config(text="Time: --")


    def reset_game_state(self):
        self.is_drawer = False
        self.current_word = "????"
        self.current_word_length = None
        self.game_status = 'waiting'
        self.current_round = 0
        self.max_rounds = 0
        self.drawing_history = []

        self.clear_canvas_gui()
        self.guess_chat_display.config(state=tk.NORMAL)
        self.guess_chat_display.delete(1.0, tk.END)
        self.guess_chat_display.config(state=tk.DISABLED)
        self.notification_display.config(state=tk.NORMAL)
        self.notification_display.delete(1.0, tk.END)
        self.notification_display.config(state=tk.DISABLED)

        self.status_label.config(text="Status: Waiting for game to start...")
        self.round_label.config(text="Round: N/A")
        self.drawer_label.config(text="Drawer: N/A")
        self.word_label.config(text="Word: ????")
        self.timer_label.config(text="Time: --")
        self.update_scores({})

        self.tool_frame.pack_forget()
        self.send_button.config(text="Send Chat")
        self.ready_button.config(state=tk.NORMAL, text="Ready to Play")


    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit the game?"):
            if self.sock:
                print("Closing socket...")
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                    self.sock.close()
                except OSError as e:
                    print(f"Error during socket shutdown/close: {e}")
            self.master.destroy()
            sys.exit()

# Main execution
if __name__ == "__main__":
    root = tk.Tk()
    client = PictionaryClient(root)
    root.protocol("WM_DELETE_WINDOW", client.on_closing)
    root.mainloop()