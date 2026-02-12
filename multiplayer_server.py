import json
import os
import random
import socket
import threading
import uuid

from constants import MULTIPLAYER_ROOM_SIZE, MULTIPLAYER_SERVER_HOST, MULTIPLAYER_SERVER_PORT


PALETTE = [
    "#7dd3fc",
    "#fca5a5",
    "#86efac",
    "#fcd34d",
    "#c4b5fd",
    "#f9a8d4",
    "#67e8f9",
    "#fdba74",
]


class Room:
    def __init__(self, room_id):
        self.room_id = room_id
        self.clients = {}
        self.lock = threading.Lock()

    def to_payload(self):
        players = []
        for client in self.clients.values():
            players.append(
                {
                    "player_id": client.player_id,
                    "name": client.name,
                    "color": client.color,
                    "x": client.x,
                    "y": client.y,
                    "rotation": client.rotation,
                    "score": client.score,
                    "lives": client.lives,
                }
            )
        return {"type": "room_state", "room_id": self.room_id, "players": players}


class ClientState:
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.file = sock.makefile("r", encoding="utf-8", newline="\n")
        self.player_id = str(uuid.uuid4())[:8]
        self.name = f"Pilot-{self.player_id[:4]}"
        self.color = random.choice(PALETTE)
        self.room = None
        self.x = 0
        self.y = 0
        self.rotation = 0
        self.score = 0
        self.lives = 0


def send_json(sock, payload):
    sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))


rooms = {}
rooms_lock = threading.Lock()
leaderboard_lock = threading.Lock()
leaderboard_path = os.path.join(os.path.dirname(__file__), "leaderboard.json")
global_leaderboard = {}


def load_global_leaderboard():
    try:
        with open(leaderboard_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def save_global_leaderboard():
    tmp_path = f"{leaderboard_path}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(global_leaderboard, handle)
        os.replace(tmp_path, leaderboard_path)
    except OSError:
        pass


def get_or_create_room():
    with rooms_lock:
        candidates = [room for room in rooms.values() if len(room.clients) < MULTIPLAYER_ROOM_SIZE]
        if candidates:
            return random.choice(candidates)

        room_id = str(uuid.uuid4())[:6]
        room = Room(room_id)
        rooms[room_id] = room
        return room


def broadcast_room_state(room):
    with leaderboard_lock:
        top_scores = sorted(global_leaderboard.items(), key=lambda item: item[1]["score"], reverse=True)[:10]
    payload = room.to_payload()
    payload["global_leaderboard"] = [
        {"name": entry["name"], "score": entry["score"], "color": entry["color"]}
        for _, entry in top_scores
    ]
    dead = []
    with room.lock:
        for client in room.clients.values():
            try:
                send_json(client.sock, payload)
            except OSError:
                dead.append(client.player_id)

        for player_id in dead:
            room.clients.pop(player_id, None)


def remove_client(client):
    room = client.room
    if room is None:
        return

    with room.lock:
        room.clients.pop(client.player_id, None)
        is_empty = len(room.clients) == 0

    if is_empty:
        with rooms_lock:
            rooms.pop(room.room_id, None)
    else:
        broadcast_room_state(room)


def handle_client(sock, addr):
    client = ClientState(sock, addr)
    room = get_or_create_room()
    client.room = room

    with room.lock:
        room.clients[client.player_id] = client

    send_json(
        sock,
        {
            "type": "welcome",
            "player_id": client.player_id,
            "name": client.name,
            "color": client.color,
            "room_id": room.room_id,
            "room_size": MULTIPLAYER_ROOM_SIZE,
        },
    )
    broadcast_room_state(room)

    try:
        for raw in client.file:
            raw = raw.strip()
            if not raw:
                continue

            message = json.loads(raw)
            message_type = message.get("type")
            if message_type != "state_update":
                continue

            client.x = float(message.get("x", client.x))
            client.y = float(message.get("y", client.y))
            client.rotation = float(message.get("rotation", client.rotation))
            client.score = int(message.get("score", client.score))
            client.lives = int(message.get("lives", client.lives))
            if message.get("name"):
                client.name = str(message["name"])[:24]
            if client.name:
                with leaderboard_lock:
                    current = global_leaderboard.get(client.name)
                    if not current or client.score >= int(current.get("score", 0)):
                        global_leaderboard[client.name] = {
                            "name": client.name,
                            "score": client.score,
                            "color": client.color,
                        }
                        save_global_leaderboard()

            broadcast_room_state(room)

    except (OSError, json.JSONDecodeError, ValueError):
        pass
    finally:
        remove_client(client)
        try:
            client.file.close()
        except OSError:
            pass
        try:
            client.sock.close()
        except OSError:
            pass


def main():
    global global_leaderboard
    global_leaderboard = load_global_leaderboard()
    print(f"Starting multiplayer server on {MULTIPLAYER_SERVER_HOST}:{MULTIPLAYER_SERVER_PORT}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((MULTIPLAYER_SERVER_HOST, MULTIPLAYER_SERVER_PORT))
    server.listen()

    try:
        while True:
            sock, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(sock, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()


if __name__ == "__main__":
    main()
