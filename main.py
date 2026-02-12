import random
import time
from collections import deque

import pygame

from achievements import AchievementTracker
from asteroids import Asteroid
from asteroidfield import AsteroidField
from bomb import Bomb
from constants import (
    ASTEROID_MIN_RADIUS,
    GAME_TITLE,
    MULTIPLAYER_SERVER_HOST,
    MULTIPLAYER_SERVER_PORT,
    NETWORK_SEND_INTERVAL_SECONDS,
    PARALLAX_LAYER_COUNTS,
    PARALLAX_LAYER_SPEEDS,
    PLAYER_RESPAWN_COUNTDOWN_SECONDS,
    PLAYER_RESPAWN_INVULNERABLE_SECONDS,
    PLAYER_STARTING_LIVES,
    POWERUP_SPAWN_SECONDS,
    SCREEN_HEIGHT,
    SCREEN_SHAKE_BASE_DURATION_SECONDS,
    SCREEN_SHAKE_BOMB_INTENSITY,
    SCREEN_SHAKE_BOSS_DEATH_INTENSITY,
    SCREEN_SHAKE_EXPLOSION_INTENSITY,
    SCREEN_WIDTH,
    WAVE_DURATION_SECONDS,
)
from drone import CompanionDrone
from explosion import Explosion
from logger import log_event, log_state
from multiplayer_client import MultiplayerClient
from player import Player
from powerup import ShieldPowerUp, SpeedPowerUp
from shot import Shot
from sounds import SoundManager


STATE_HOME = "home"
STATE_PLAYING = "playing"
STATE_RESPAWNING = "respawning"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "game_over"
STATE_SETTINGS = "settings"
STATE_LEADERBOARD = "leaderboard"
STATE_LOGIN = "login"
STATE_ROUND_OVER = "round_over"


def make_parallax_layers():
    layers = []
    for count, speed in zip(PARALLAX_LAYER_COUNTS, PARALLAX_LAYER_SPEEDS):
        stars = []
        for _ in range(count):
            stars.append(
                {
                    "x": random.uniform(0, SCREEN_WIDTH),
                    "y": random.uniform(0, SCREEN_HEIGHT),
                    "speed": speed,
                    "size": max(1, int(speed / 24)),
                }
            )
        layers.append(stars)
    return layers


def make_home_ships(count):
    ships = []
    for _ in range(count):
        direction = random.choice((-1, 1))
        x = random.uniform(0, SCREEN_WIDTH)
        if direction < 0:
            x = SCREEN_WIDTH - x
        ships.append(
            {
                "x": x,
                "y": random.uniform(80, SCREEN_HEIGHT - 80),
                "speed": random.uniform(30, 80) * direction,
                "size": random.uniform(0.5, 1.1),
                "phase": random.uniform(0, 6.283),
                "color": random.choice(["#7dd3fc", "#a7f3d0", "#fca5a5", "#fcd34d"]),
            }
        )
    return ships


def draw_center_text(screen, font, text, y, color="white"):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, y))
    screen.blit(text_surface, text_rect)


def draw_panel(screen, x, y, width, height, alpha=170):
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill((7, 14, 28, alpha))
    pygame.draw.rect(panel, (60, 130, 180, 210), panel.get_rect(), 2, border_radius=16)
    screen.blit(panel, (x, y))


def ship_hull_points(position, rotation, radius):
    forward = pygame.Vector2(0, 1).rotate(rotation)
    right = pygame.Vector2(0, 1).rotate(rotation + 90)
    nose = position + forward * radius * 1.25
    tail = position - forward * radius * 0.95
    left_wing = position - forward * radius * 0.45 - right * radius * 0.9
    right_wing = position - forward * radius * 0.45 + right * radius * 0.9
    left_hull = position + forward * radius * 0.25 - right * radius * 0.55
    right_hull = position + forward * radius * 0.25 + right * radius * 0.55
    canopy = position + forward * radius * 0.2
    return [nose, right_hull, right_wing, tail, left_wing, left_hull], canopy


def draw_remote_ship(screen, x, y, rotation, color, name, radius=20):
    position = pygame.Vector2(x, y)
    hull, canopy = ship_hull_points(position, rotation, radius)
    pygame.draw.polygon(screen, color, hull)
    pygame.draw.polygon(screen, "white", hull, 2)
    pygame.draw.circle(screen, "white", (canopy.x, canopy.y), radius * 0.2, 1)

    font = pygame.font.SysFont(None, 22)
    text = font.render(name, True, color)
    rect = text.get_rect(center=(x, y - radius - 12))
    screen.blit(text, rect)


def draw_parallax_background(screen, layers):
    screen.fill((4, 8, 20))
    shades = [(130, 148, 190), (180, 205, 240), (230, 240, 255)]
    for i, stars in enumerate(layers):
        color = shades[min(i, len(shades) - 1)]
        for star in stars:
            pygame.draw.circle(screen, color, (star["x"], star["y"]), star["size"])


def draw_home_background(screen, layers, home_ships, elapsed):
    draw_parallax_background(screen, layers)

    for ship in home_ships:
        wobble = 12 * pygame.math.Vector2(0, 1).rotate(elapsed * 60 + ship["phase"]).y
        cx = ship["x"]
        cy = ship["y"] + wobble
        scale = ship["size"]
        position = pygame.Vector2(cx, cy)
        hull, canopy = ship_hull_points(position, 0, 20 * scale)
        pygame.draw.polygon(screen, ship["color"], hull)
        pygame.draw.polygon(screen, "white", hull, 2)
        pygame.draw.circle(screen, "white", (canopy.x, canopy.y), 3, 1)


def update_parallax(layers, dt):
    for stars in layers:
        for star in stars:
            star["y"] += star["speed"] * dt
            if star["y"] > SCREEN_HEIGHT:
                star["y"] = 0
                star["x"] = random.uniform(0, SCREEN_WIDTH)


def update_home_background(home_ships, dt):
    for ship in home_ships:
        ship["x"] += ship["speed"] * dt
        margin = 70
        if ship["speed"] > 0 and ship["x"] > SCREEN_WIDTH + margin:
            ship["x"] = -margin
            ship["y"] = random.uniform(80, SCREEN_HEIGHT - 80)
        elif ship["speed"] < 0 and ship["x"] < -margin:
            ship["x"] = SCREEN_WIDTH + margin
            ship["y"] = random.uniform(80, SCREEN_HEIGHT - 80)


def main():
    pygame.init()
    pygame.display.set_caption(GAME_TITLE)

    clock = pygame.time.Clock()
    dt = 0
    elapsed = 0
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    title_font = pygame.font.SysFont(None, 96)
    menu_font = pygame.font.SysFont(None, 42)
    hud_font = pygame.font.SysFont(None, 28)
    overlay_font = pygame.font.SysFont(None, 76)
    sub_font = pygame.font.SysFont(None, 24)

    sounds = SoundManager()
    achievements = AchievementTracker()

    parallax_layers = make_parallax_layers()
    home_ships = make_home_ships(5)

    menu_options = {
        STATE_HOME: ["Start Solo", "Start Online", "Leaderboard", "Login", "Settings", "Quit"],
        STATE_PAUSED: ["Resume", "Restart", "Home", "Settings", "Quit"],
        STATE_GAME_OVER: ["Restart", "Home", "Settings", "Quit"],
        STATE_SETTINGS: ["Sound", "Volume", "Back"],
        STATE_LEADERBOARD: ["Back"],
        STATE_ROUND_OVER: ["View Results", "Home"],
    }
    menu_index = {
        STATE_HOME: 0,
        STATE_PAUSED: 0,
        STATE_GAME_OVER: 0,
        STATE_SETTINGS: 0,
        STATE_LEADERBOARD: 0,
        STATE_ROUND_OVER: 0,
    }

    settings_return_state = STATE_HOME
    state = STATE_HOME

    game = {}
    score = 0
    lives = PLAYER_STARTING_LIVES
    powerup_spawn_timer = 0
    respawn_invulnerable_timer = 0
    respawn_countdown_timer = 0
    game_over_score = 0
    wave_number = 1
    wave_timer = 0

    online_client = None
    online_mode = False
    network_send_timer = 0
    status_message = ""
    status_until = 0
    achievement_toasts = deque()
    player_profile_name = "Guest"
    login_name = ""
    login_error = ""
    online_round_over = False
    online_winner_id = None
    online_standings = []
    last_auto_connect_attempt = -999.0

    shake_timer = 0
    shake_intensity = 0

    def trigger_shake(intensity, duration=SCREEN_SHAKE_BASE_DURATION_SECONDS):
        nonlocal shake_timer, shake_intensity
        shake_timer = max(shake_timer, duration)
        shake_intensity = max(shake_intensity, intensity)

    def set_status(message, duration=3):
        nonlocal status_message, status_until
        status_message = message
        status_until = elapsed + duration

    def on_player_action(action_name):
        if action_name == "shoot":
            sounds.play("shoot")
        elif action_name == "bomb_drop":
            sounds.play("bomb_drop")
            trigger_shake(SCREEN_SHAKE_BOMB_INTENSITY, SCREEN_SHAKE_BASE_DURATION_SECONDS)

    def close_online_client():
        nonlocal online_client, online_mode
        if online_client is not None:
            online_client.close()
        online_client = None
        online_mode = False

    def create_game_world(player_color="white", player_name="You"):
        updatable = pygame.sprite.Group()
        drawable = pygame.sprite.Group()
        asteroids = pygame.sprite.Group()
        shots = pygame.sprite.Group()
        bombs = pygame.sprite.Group()
        powerups = pygame.sprite.Group()

        Player.containers = (updatable, drawable)
        Asteroid.containers = (asteroids, updatable, drawable)
        Shot.containers = (shots, updatable, drawable)
        Bomb.containers = (bombs, updatable, drawable)
        ShieldPowerUp.containers = (powerups, updatable, drawable)
        SpeedPowerUp.containers = (powerups, updatable, drawable)
        CompanionDrone.containers = (updatable, drawable)
        Explosion.containers = (updatable, drawable)
        AsteroidField.containers = (updatable,)

        player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, color=player_color, name=player_name)
        player.action_callback = on_player_action
        asteroid_field = AsteroidField()
        drone = CompanionDrone(player, asteroids)

        return {
            "updatable": updatable,
            "drawable": drawable,
            "asteroids": asteroids,
            "shots": shots,
            "bombs": bombs,
            "powerups": powerups,
            "player": player,
            "drone": drone,
            "asteroid_field": asteroid_field,
        }

    def start_new_game(use_online=False):
        nonlocal game, score, lives, powerup_spawn_timer
        nonlocal respawn_invulnerable_timer, respawn_countdown_timer, state
        nonlocal online_mode, network_send_timer, wave_number, wave_timer

        if not use_online:
            close_online_client()

        player_color = "white"
        player_name = "You"
        if use_online and online_client is not None and online_client.connected:
            player_color = online_client.player_color
            player_name = online_client.player_name

        game = create_game_world(player_color=player_color, player_name=player_name)
        score = 0
        lives = PLAYER_STARTING_LIVES
        powerup_spawn_timer = 0
        respawn_invulnerable_timer = 0
        respawn_countdown_timer = 0
        network_send_timer = 0
        wave_number = 1
        wave_timer = 0
        achievements.start_new_run()
        achievement_toasts.clear()
        online_mode = use_online
        state = STATE_PLAYING
        log_event("game_started", online=online_mode)

    def connect_online():
        nonlocal online_client
        close_online_client()
        online_client = MultiplayerClient()

        try:
            online_client.connect()
        except OSError:
            close_online_client()
            set_status("Unable to reach multiplayer server", duration=4)
            return False

        deadline = time.monotonic() + 2.5
        while time.monotonic() < deadline and not online_client.connected:
            time.sleep(0.02)

        if not online_client.connected:
            close_online_client()
            set_status("Server timeout", duration=4)
            return False

        if player_profile_name and player_profile_name != "Guest":
            online_client.player_name = player_profile_name

        set_status(f"Joined room {online_client.room_id}", duration=3)
        return True

    def change_state(next_state):
        nonlocal state
        state = next_state

    def handle_menu_action(action):
        nonlocal settings_return_state, running, login_name, login_error
        if action == "Start Solo":
            sounds.play("menu_select")
            start_new_game(use_online=False)
        elif action == "Start Online":
            sounds.play("menu_select")
            if connect_online():
                start_new_game(use_online=True)
        elif action == "Resume":
            sounds.play("menu_select")
            change_state(STATE_PLAYING)
        elif action == "Restart":
            sounds.play("menu_select")
            start_new_game(use_online=online_mode)
        elif action == "Home":
            sounds.play("menu_select")
            close_online_client()
            change_state(STATE_HOME)
        elif action == "Leaderboard":
            sounds.play("menu_select")
            if online_client is None or not online_client.connected:
                connect_online()
            change_state(STATE_LEADERBOARD)
            menu_index[STATE_LEADERBOARD] = 0
        elif action == "Login":
            sounds.play("menu_select")
            login_name = "" if player_profile_name == "Guest" else player_profile_name
            login_error = ""
            change_state(STATE_LOGIN)
        elif action == "Settings":
            sounds.play("menu_select")
            settings_return_state = state
            change_state(STATE_SETTINGS)
        elif action == "Quit":
            sounds.play("menu_select")
            running = False

    def reset_player_for_respawn():
        player = game["player"]
        player.position = pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        player.velocity = pygame.Vector2(0, 0)
        player.rotation = 0

    def add_score_for_asteroid(asteroid):
        nonlocal score
        if asteroid.radius <= ASTEROID_MIN_RADIUS:
            score += 100
        elif asteroid.radius <= ASTEROID_MIN_RADIUS * 2:
            score += 50
        else:
            score += 20

    def auto_connect_on_home():
        nonlocal last_auto_connect_attempt
        if state != STATE_HOME or online_mode:
            return
        if online_client is not None and online_client.connected:
            return
        if elapsed - last_auto_connect_attempt < 6:
            return
        last_auto_connect_attempt = elapsed
        connect_online()

    def ordinal(n):
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    def recompute_online_standings():
        nonlocal online_round_over, online_winner_id, online_standings
        if not online_mode or online_client is None:
            online_round_over = False
            online_winner_id = None
            online_standings = []
            return

        players = list(online_client.players.values())
        if not players:
            online_round_over = False
            online_winner_id = None
            online_standings = []
            return

        alive = [p for p in players if int(p.get("lives", 0)) > 0]
        eliminated = [p for p in players if int(p.get("lives", 0)) <= 0]
        alive_sorted = sorted(alive, key=lambda p: int(p.get("score", 0)), reverse=True)
        eliminated_sorted = sorted(eliminated, key=lambda p: int(p.get("score", 0)), reverse=True)
        online_standings = alive_sorted + eliminated_sorted

        if len(alive_sorted) == 1 and len(players) >= 2:
            online_round_over = True
            online_winner_id = alive_sorted[0].get("player_id")
        else:
            online_round_over = False
            online_winner_id = None

    running = True
    while running:
        elapsed += dt
        auto_connect_on_home()
        update_parallax(parallax_layers, dt)
        update_home_background(home_ships, dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if state == STATE_PLAYING and event.key == pygame.K_ESCAPE:
                    sounds.play("menu_move")
                    change_state(STATE_PAUSED)

                elif state == STATE_RESPAWNING and event.key == pygame.K_ESCAPE:
                    sounds.play("menu_move")
                    change_state(STATE_PAUSED)

                elif state == STATE_PLAYING and event.key == pygame.K_u and game:
                    drone = game.get("drone")
                    if drone and drone.alive() and drone.upgrade():
                        sounds.play("drone_upgrade")
                        set_status(f"Drone upgraded to Lv {drone.level}", duration=2)
                    else:
                        set_status("Drone cannot upgrade further", duration=2)

                elif state == STATE_LOGIN:
                    if event.key == pygame.K_ESCAPE:
                        sounds.play("menu_move")
                        change_state(STATE_HOME)
                    elif event.key == pygame.K_BACKSPACE:
                        login_name = login_name[:-1]
                        login_error = ""
                    elif event.key == pygame.K_RETURN:
                        stripped = login_name.strip()
                        if not stripped:
                            login_error = "Name cannot be empty."
                        else:
                            player_profile_name = stripped[:16]
                            login_error = ""
                            sounds.play("menu_select")
                            change_state(STATE_HOME)
                    else:
                        if event.unicode and event.unicode.isprintable():
                            if len(login_name) < 16:
                                login_name += event.unicode
                                login_error = ""
                elif state in (STATE_HOME, STATE_PAUSED, STATE_GAME_OVER, STATE_SETTINGS, STATE_LEADERBOARD, STATE_ROUND_OVER):
                    if event.key == pygame.K_UP:
                        menu_index[state] = (menu_index[state] - 1) % len(menu_options[state])
                        sounds.play("menu_move")
                    elif event.key == pygame.K_DOWN:
                        menu_index[state] = (menu_index[state] + 1) % len(menu_options[state])
                        sounds.play("menu_move")
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if state == STATE_SETTINGS:
                            current = menu_options[STATE_SETTINGS][menu_index[STATE_SETTINGS]]
                            if current == "Sound":
                                sounds.toggle_enabled()
                                sounds.play("menu_select")
                            elif current == "Back":
                                sounds.play("menu_select")
                                change_state(settings_return_state)
                        elif state == STATE_LEADERBOARD:
                            current = menu_options[STATE_LEADERBOARD][menu_index[STATE_LEADERBOARD]]
                            if current == "Back":
                                sounds.play("menu_select")
                                change_state(STATE_HOME)
                        elif state == STATE_ROUND_OVER:
                            current = menu_options[STATE_ROUND_OVER][menu_index[STATE_ROUND_OVER]]
                            if current == "View Results":
                                sounds.play("menu_select")
                                change_state(STATE_GAME_OVER)
                            elif current == "Home":
                                sounds.play("menu_select")
                                close_online_client()
                                change_state(STATE_HOME)
                        else:
                            current = menu_options[state][menu_index[state]]
                            handle_menu_action(current)
                    elif state == STATE_SETTINGS and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        current = menu_options[STATE_SETTINGS][menu_index[STATE_SETTINGS]]
                        if current == "Volume":
                            delta = 0.05 if event.key == pygame.K_RIGHT else -0.05
                            sounds.set_volume(sounds.volume + delta)
                            sounds.play("menu_move")
                    elif event.key == pygame.K_ESCAPE:
                        if state == STATE_SETTINGS:
                            sounds.play("menu_move")
                            change_state(settings_return_state)
                        elif state == STATE_LEADERBOARD:
                            sounds.play("menu_move")
                            change_state(STATE_HOME)
                        elif state == STATE_ROUND_OVER:
                            sounds.play("menu_move")
                            change_state(STATE_GAME_OVER)
                        elif state == STATE_PAUSED:
                            sounds.play("menu_move")
                            change_state(STATE_PLAYING)

        if state == STATE_PLAYING:
            log_state()
            game["updatable"].update(dt)

            wave_timer += dt
            if wave_timer >= WAVE_DURATION_SECONDS:
                wave_timer -= WAVE_DURATION_SECONDS
                wave_number += 1
                achievements.on_wave_change(wave_number)

            if respawn_invulnerable_timer > 0:
                respawn_invulnerable_timer -= dt

            powerup_spawn_timer += dt
            if powerup_spawn_timer >= POWERUP_SPAWN_SECONDS:
                powerup_spawn_timer = 0
                powerup_class = random.choice((ShieldPowerUp, SpeedPowerUp))
                powerup = powerup_class(
                    random.uniform(40, SCREEN_WIDTH - 40),
                    random.uniform(40, SCREEN_HEIGHT - 40),
                )
                powerup.velocity = pygame.Vector2(
                    random.uniform(-40, 40),
                    random.uniform(-40, 40),
                )
                log_event("powerup_spawned", kind=powerup.kind)

            for powerup in list(game["powerups"]):
                if game["player"].collides_with(powerup):
                    if powerup.kind == "shield":
                        game["player"].apply_shield()
                    else:
                        game["player"].apply_speed_boost()
                    sounds.play("powerup")
                    log_event("powerup_collected", kind=powerup.kind)
                    powerup.kill()

            for bomb in list(game["bombs"]):
                if bomb.ready_to_detonate():
                    blast_position, blast_radius = bomb.detonate()
                    sounds.play("explosion")
                    trigger_shake(SCREEN_SHAKE_BOMB_INTENSITY, SCREEN_SHAKE_BASE_DURATION_SECONDS * 1.4)
                    log_event("bomb_detonated")

                    hit_count = 0
                    for asteroid in list(game["asteroids"]):
                        if asteroid.position.distance_to(blast_position) <= blast_radius + asteroid.radius:
                            hit_count += 1
                            add_score_for_asteroid(asteroid)
                            achievements.record_asteroid_destroyed(elapsed)
                            was_boss = asteroid.is_boss
                            asteroid.split()
                            if was_boss:
                                sounds.play("boss_death")
                                trigger_shake(
                                    SCREEN_SHAKE_BOSS_DEATH_INTENSITY,
                                    SCREEN_SHAKE_BASE_DURATION_SECONDS * 2,
                                )
                    achievements.record_bomb_detonation(hit_count)

            drone = game.get("drone")
            for asteroid in list(game["asteroids"]):
                if not asteroid.alive():
                    continue

                player = game["player"]
                if respawn_invulnerable_timer <= 0 and player.collides_with(asteroid):
                    if player.has_shield():
                        player.consume_shield()
                        asteroid.split()
                        sounds.play("explosion")
                        trigger_shake(SCREEN_SHAKE_EXPLOSION_INTENSITY)
                        log_event("shield_block")
                        continue

                    sounds.play("hit")
                    log_event("player_hit")
                    achievements.mark_player_hit()
                    lives -= 1

                    if lives <= 0:
                        if online_mode and online_client is not None:
                            online_client.send_state(
                                player.position.x,
                                player.position.y,
                                player.rotation,
                                score,
                                lives,
                                name=player.name,
                            )
                        game_over_score = score
                        menu_index[STATE_GAME_OVER] = 0
                        change_state(STATE_GAME_OVER)
                        break

                    reset_player_for_respawn()
                    respawn_countdown_timer = PLAYER_RESPAWN_COUNTDOWN_SECONDS
                    change_state(STATE_RESPAWNING)
                    break

                if drone and drone.alive() and asteroid.collides_with(drone):
                    drone.damage(1)
                    asteroid.split()
                    trigger_shake(SCREEN_SHAKE_EXPLOSION_INTENSITY)
                    if not drone.alive():
                        set_status("Drone destroyed", duration=2.5)

                for shot in list(game["shots"]):
                    if asteroid.collides_with(shot):
                        add_score_for_asteroid(asteroid)
                        achievements.record_asteroid_destroyed(elapsed)
                        shot.kill()
                        was_boss = asteroid.is_boss
                        asteroid.split()
                        sounds.play("explosion")
                        trigger_shake(SCREEN_SHAKE_EXPLOSION_INTENSITY)
                        if was_boss:
                            sounds.play("boss_death")
                            trigger_shake(
                                SCREEN_SHAKE_BOSS_DEATH_INTENSITY,
                                SCREEN_SHAKE_BASE_DURATION_SECONDS * 2,
                            )
                        log_event("asteroid_shot")
                        break

            for notification in achievements.pop_notifications():
                achievement_toasts.append((notification, elapsed + 4))

            has_boss = any(a.is_boss for a in game["asteroids"])
            enemy_count = len(game["asteroids"])
            if has_boss:
                sounds.update_music_mode("boss")
            elif enemy_count >= 12:
                sounds.update_music_mode("intense")
            else:
                sounds.update_music_mode("calm")

            if online_mode and online_client is not None:
                network_send_timer += dt
                if network_send_timer >= NETWORK_SEND_INTERVAL_SECONDS:
                    network_send_timer = 0
                    player = game["player"]
                    online_client.send_state(
                        player.position.x,
                        player.position.y,
                        player.rotation,
                        score,
                        lives,
                        name=player.name,
                    )
                recompute_online_standings()
                if online_round_over and state == STATE_PLAYING:
                    game_over_score = score
                    menu_index[STATE_ROUND_OVER] = 0
                    change_state(STATE_ROUND_OVER)

        elif state == STATE_RESPAWNING:
            sounds.update_music_mode("calm")
            respawn_countdown_timer -= dt
            if respawn_countdown_timer <= 0:
                respawn_countdown_timer = 0
                respawn_invulnerable_timer = PLAYER_RESPAWN_INVULNERABLE_SECONDS
                sounds.play("respawn")
                log_event("player_respawn", lives_remaining=lives)
                change_state(STATE_PLAYING)
        elif state in (STATE_HOME, STATE_SETTINGS, STATE_PAUSED, STATE_GAME_OVER, STATE_LEADERBOARD, STATE_LOGIN, STATE_ROUND_OVER):
            sounds.update_music_mode("calm")

        if state in (STATE_HOME,) or (state == STATE_SETTINGS and settings_return_state == STATE_HOME):
            frame_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            draw_home_background(frame_surface, parallax_layers, home_ships, elapsed)
        else:
            frame_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            draw_parallax_background(frame_surface, parallax_layers)
            if game:
                for item in game["drawable"]:
                    item.draw(frame_surface)

                player = game["player"]
                shield_text = f"Shield: {player.shield_timer:.1f}s" if player.has_shield() else "Shield: off"
                speed_text = (
                    f"Speed: {player.speed_boost_timer:.1f}s"
                    if player.speed_boost_timer > 0
                    else "Speed: off"
                )
                drone = game.get("drone")
                drone_text = "Drone: down"
                if drone and drone.alive():
                    drone_text = f"Drone Lv{drone.level} HP {drone.health}/{drone.max_health}"
                mode_text = "Online" if online_mode else "Solo"
                hud_text = (
                    f"{mode_text}  Wave: {wave_number}  Score: {score}  Lives: {lives}  "
                    f"Weapon: {player.weapon_name()}  Bombs: {player.bombs}"
                )
                frame_surface.blit(hud_font.render(hud_text, True, "white"), (20, 20))
                frame_surface.blit(hud_font.render(shield_text, True, "deepskyblue"), (20, 48))
                frame_surface.blit(hud_font.render(speed_text, True, "springgreen"), (20, 76))
                frame_surface.blit(hud_font.render(drone_text, True, "#67e8f9"), (20, 104))

                if online_mode and online_client is not None:
                    for pid, data in online_client.players.items():
                        if pid == online_client.player_id:
                            continue
                        draw_remote_ship(
                            frame_surface,
                            data.get("x", 0),
                            data.get("y", 0),
                            data.get("rotation", 0),
                            data.get("color", "#ffffff"),
                            data.get("name", "Pilot"),
                            radius=18,
                        )

                    recompute_online_standings()
                    room_board = online_standings[:6]
                    draw_panel(frame_surface, SCREEN_WIDTH - 300, 16, 270, 190, alpha=160)
                    frame_surface.blit(
                        hud_font.render(f"Room {online_client.room_id}", True, "#93c5fd"),
                        (SCREEN_WIDTH - 282, 28),
                    )
                    for i, entry in enumerate(room_board):
                        name = entry.get("name", "Pilot")
                        player_score = entry.get("score", 0)
                        color = entry.get("color", "white")
                        lives_left = int(entry.get("lives", 0))
                        status = "OUT" if lives_left <= 0 else ordinal(i + 1)
                        if online_round_over and entry.get("player_id") == online_winner_id:
                            status = "WINNER"
                        line = f"{status:<6} {name[:10]}  {player_score}"
                        frame_surface.blit(hud_font.render(line, True, color), (SCREEN_WIDTH - 282, 54 + i * 24))

                    if online_client.global_leaderboard:
                        draw_panel(frame_surface, SCREEN_WIDTH - 300, 212, 270, 192, alpha=150)
                        frame_surface.blit(hud_font.render("Global", True, "#facc15"), (SCREEN_WIDTH - 282, 224))
                        for i, entry in enumerate(online_client.global_leaderboard[:6]):
                            line = f"{ordinal(i + 1):<6} {entry['name'][:10]} {entry['score']}"
                            frame_surface.blit(
                                hud_font.render(line, True, entry.get("color", "white")),
                                (SCREEN_WIDTH - 282, 250 + i * 22),
                            )

        if state == STATE_HOME:
            draw_center_text(frame_surface, title_font, GAME_TITLE.upper(), 110, color="white")
            draw_center_text(frame_surface, sub_font, "Pilot. Survive. Split the swarm.", 156, color="#93c5fd")
            draw_center_text(
                frame_surface,
                sub_font,
                f"Online server: {MULTIPLAYER_SERVER_HOST}:{MULTIPLAYER_SERVER_PORT}",
                182,
                color="#94a3b8",
            )
            draw_center_text(
                frame_surface,
                sub_font,
                f"Pilot: {player_profile_name}",
                204,
                color="#cbd5e1",
            )

            draw_panel(frame_surface, SCREEN_WIDTH // 2 - 240, 230, 480, 320)
            for i, option in enumerate(menu_options[STATE_HOME]):
                color = "#4ade80" if i == menu_index[STATE_HOME] else "white"
                draw_center_text(frame_surface, menu_font, option, 276 + i * 46, color=color)

        elif state == STATE_PAUSED:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            frame_surface.blit(overlay, (0, 0))
            draw_panel(frame_surface, SCREEN_WIDTH // 2 - 220, 130, 440, 320)
            draw_center_text(frame_surface, overlay_font, "PAUSED", 180, color="white")
            for i, option in enumerate(menu_options[STATE_PAUSED]):
                color = "#4ade80" if i == menu_index[STATE_PAUSED] else "white"
                draw_center_text(frame_surface, menu_font, option, 260 + i * 42, color=color)

        elif state == STATE_SETTINGS:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            frame_surface.blit(overlay, (0, 0))
            draw_panel(frame_surface, SCREEN_WIDTH // 2 - 290, 110, 580, 320)
            draw_center_text(frame_surface, overlay_font, "SETTINGS", 160, color="white")

            sound_status = "On" if sounds.enabled else "Off"
            volume_percent = int(sounds.volume * 100)
            rendered_options = [
                f"Sound: {sound_status}",
                f"Volume: {volume_percent}%  (Left/Right)",
                "Back",
            ]

            for i, option in enumerate(rendered_options):
                color = "#4ade80" if i == menu_index[STATE_SETTINGS] else "white"
                draw_center_text(frame_surface, menu_font, option, 250 + i * 50, color=color)

            draw_center_text(frame_surface, sub_font, "Esc to return", 390, color="#94a3b8")

        elif state == STATE_LEADERBOARD:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            frame_surface.blit(overlay, (0, 0))
            draw_panel(frame_surface, SCREEN_WIDTH // 2 - 280, 110, 560, 420)
            draw_center_text(frame_surface, overlay_font, "LEADERBOARD", 160, color="white")

            if not online_client or not online_client.connected:
                draw_center_text(
                    frame_surface,
                    sub_font,
                    "Connect to the server to load the global leaderboard.",
                    230,
                    color="#cbd5e1",
                )
                draw_center_text(
                    frame_surface,
                    sub_font,
                    "Start Online or wait here after connecting.",
                    258,
                    color="#94a3b8",
                )
            elif online_client.global_leaderboard:
                for i, entry in enumerate(online_client.global_leaderboard[:10]):
                    line = f"{ordinal(i + 1):<6} {entry['name'][:16]} {entry['score']}"
                    frame_surface.blit(
                        menu_font.render(line, True, entry.get("color", "white")),
                        (SCREEN_WIDTH // 2 - 220, 220 + i * 28),
                    )
            else:
                draw_center_text(frame_surface, sub_font, "Leaderboard is warming up...", 240, color="#cbd5e1")

            for i, option in enumerate(menu_options[STATE_LEADERBOARD]):
                color = "#4ade80" if i == menu_index[STATE_LEADERBOARD] else "white"
                draw_center_text(frame_surface, menu_font, option, 500 + i * 42, color=color)

        elif state == STATE_GAME_OVER:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            frame_surface.blit(overlay, (0, 0))
            draw_panel(frame_surface, SCREEN_WIDTH // 2 - 250, 110, 500, 360)
            draw_center_text(frame_surface, overlay_font, "GAME OVER", 166, color="orangered")
            if online_mode and online_round_over and online_winner_id == online_client.player_id:
                draw_center_text(frame_surface, menu_font, "YOU WIN!", 210, color="#4ade80")
            elif online_mode and online_round_over and online_winner_id:
                winner_name = None
                for entry in online_standings:
                    if entry.get("player_id") == online_winner_id:
                        winner_name = entry.get("name", "Winner")
                        break
                if winner_name:
                    draw_center_text(frame_surface, sub_font, f"Winner: {winner_name}", 208, color="#facc15")
            draw_center_text(frame_surface, menu_font, f"Final Score: {game_over_score}", 230, color="white")
            for i, option in enumerate(menu_options[STATE_GAME_OVER]):
                color = "#4ade80" if i == menu_index[STATE_GAME_OVER] else "white"
                draw_center_text(frame_surface, menu_font, option, 290 + i * 46, color=color)

        elif state == STATE_ROUND_OVER:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            frame_surface.blit(overlay, (0, 0))
            draw_panel(frame_surface, SCREEN_WIDTH // 2 - 260, 120, 520, 340)
            draw_center_text(frame_surface, overlay_font, "ROUND OVER", 180, color="white")
            if online_winner_id:
                winner_name = None
                for entry in online_standings:
                    if entry.get("player_id") == online_winner_id:
                        winner_name = entry.get("name", "Winner")
                        break
                if winner_name:
                    draw_center_text(frame_surface, menu_font, f"Winner: {winner_name}", 240, color="#facc15")
            draw_center_text(frame_surface, sub_font, "Gameplay paused", 280, color="#94a3b8")
            for i, option in enumerate(menu_options[STATE_ROUND_OVER]):
                color = "#4ade80" if i == menu_index[STATE_ROUND_OVER] else "white"
                draw_center_text(frame_surface, menu_font, option, 330 + i * 46, color=color)

        elif state == STATE_RESPAWNING:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 110))
            frame_surface.blit(overlay, (0, 0))
            countdown_display = max(1, int(respawn_countdown_timer) + 1)
            draw_center_text(frame_surface, overlay_font, f"RESPAWNING {countdown_display}", SCREEN_HEIGHT // 2 - 20)
            draw_center_text(frame_surface, sub_font, "Get ready...", SCREEN_HEIGHT // 2 + 28, color="lightgray")

        elif state == STATE_LOGIN:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            frame_surface.blit(overlay, (0, 0))
            draw_panel(frame_surface, SCREEN_WIDTH // 2 - 280, 140, 560, 320)
            draw_center_text(frame_surface, overlay_font, "LOGIN", 200, color="white")
            draw_center_text(frame_surface, sub_font, "Enter a pilot name to appear on the leaderboard.", 240, color="#cbd5e1")
            name_display = login_name if login_name else "_"
            draw_center_text(frame_surface, menu_font, name_display[:16], 290, color="#facc15")
            draw_center_text(frame_surface, sub_font, "Enter to save, Esc to cancel", 340, color="#94a3b8")
            if login_error:
                draw_center_text(frame_surface, sub_font, login_error, 370, color="#fca5a5")

        now_toasts = deque()
        for notification, expiry in achievement_toasts:
            if elapsed < expiry:
                now_toasts.append((notification, expiry))
        achievement_toasts = now_toasts

        if achievement_toasts:
            notification, _ = achievement_toasts[0]
            draw_panel(frame_surface, SCREEN_WIDTH // 2 - 280, 16, 560, 64, alpha=190)
            draw_center_text(
                frame_surface,
                sub_font,
                f"Achievement Unlocked: {notification['title']} - {notification['description']}",
                48,
                color="#fef08a",
            )

        if status_message and elapsed < status_until:
            draw_panel(frame_surface, SCREEN_WIDTH // 2 - 220, SCREEN_HEIGHT - 72, 440, 46, alpha=180)
            draw_center_text(frame_surface, sub_font, status_message, SCREEN_HEIGHT - 49, color="#cbd5e1")

        shake_offset = pygame.Vector2(0, 0)
        if shake_timer > 0:
            shake_timer -= dt
            shake_offset.x = random.randint(-int(shake_intensity), int(shake_intensity))
            shake_offset.y = random.randint(-int(shake_intensity), int(shake_intensity))
            shake_intensity = max(0, shake_intensity * 0.9)

        screen.fill((0, 0, 0))
        screen.blit(frame_surface, (int(shake_offset.x), int(shake_offset.y)))

        pygame.display.flip()
        dt = clock.tick(60) / 1000

    close_online_client()


if __name__ == "__main__":
    main()
