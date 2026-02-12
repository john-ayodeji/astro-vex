import json
import socket
import threading

from constants import MULTIPLAYER_SERVER_HOST, MULTIPLAYER_SERVER_PORT


class MultiplayerClient:
    def __init__(self, host=MULTIPLAYER_SERVER_HOST, port=MULTIPLAYER_SERVER_PORT):
        self.host = host
        self.port = port
        self.sock = None
        self.file = None
        self.running = False
        self.lock = threading.Lock()
        self.thread = None

        self.connected = False
        self.player_id = None
        self.player_name = "You"
        self.player_color = "#ffffff"
        self.room_id = None
        self.room_size = 0
        self.players = {}
        self.global_leaderboard = []

    def connect(self, timeout=3.0):
        self.sock = socket.create_connection((self.host, self.port), timeout=timeout)
        self.file = self.sock.makefile("r", encoding="utf-8", newline="\n")
        self.running = True
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()

    def close(self):
        self.running = False
        if self.file is not None:
            try:
                self.file.close()
            except OSError:
                pass
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass

    def send_state(self, x, y, rotation, score, lives, name="You"):
        if not self.connected or self.sock is None:
            return

        payload = {
            "type": "state_update",
            "x": x,
            "y": y,
            "rotation": rotation,
            "score": score,
            "lives": lives,
            "name": name,
        }

        with self.lock:
            try:
                self.sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            except OSError:
                self.running = False
                self.connected = False

    def _reader_loop(self):
        try:
            for raw in self.file:
                if not self.running:
                    break
                raw = raw.strip()
                if not raw:
                    continue

                message = json.loads(raw)
                message_type = message.get("type")
                if message_type == "welcome":
                    self.player_id = message.get("player_id")
                    self.player_name = message.get("name", self.player_name)
                    self.player_color = message.get("color", self.player_color)
                    self.room_id = message.get("room_id")
                    self.room_size = int(message.get("room_size", 0))
                    self.connected = True
                elif message_type == "room_state":
                    players = {}
                    for entry in message.get("players", []):
                        players[entry["player_id"]] = entry
                    self.players = players
                    self.global_leaderboard = message.get("global_leaderboard", [])
        except (OSError, json.JSONDecodeError, ValueError):
            pass
        finally:
            self.connected = False
            self.running = False
