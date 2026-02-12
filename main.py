import random

import pygame

from asteroids import Asteroid
from asteroidfield import AsteroidField
from bomb import Bomb
from constants import (
    ASTEROID_MIN_RADIUS,
    GAME_TITLE,
    PLAYER_RESPAWN_COUNTDOWN_SECONDS,
    PLAYER_RESPAWN_INVULNERABLE_SECONDS,
    PLAYER_STARTING_LIVES,
    POWERUP_SPAWN_SECONDS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from explosion import Explosion
from logger import log_event, log_state
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


def make_stars(count):
    stars = []
    for _ in range(count):
        stars.append(
            {
                "x": random.uniform(0, SCREEN_WIDTH),
                "y": random.uniform(0, SCREEN_HEIGHT),
                "speed": random.uniform(12, 70),
                "size": random.randint(1, 3),
            }
        )
    return stars


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
            }
        )
    return ships


def draw_center_text(screen, font, text, y, color="white"):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, y))
    screen.blit(text_surface, text_rect)


def draw_home_background(screen, stars, home_ships, elapsed):
    screen.fill((4, 8, 20))

    for star in stars:
        pygame.draw.circle(screen, (220, 230, 255), (star["x"], star["y"]), star["size"])

    for ship in home_ships:
        wobble = 12 * pygame.math.Vector2(0, 1).rotate(elapsed * 60 + ship["phase"]).y
        cx = ship["x"]
        cy = ship["y"] + wobble
        scale = ship["size"]
        points = [
            (cx, cy - 24 * scale),
            (cx - 16 * scale, cy + 18 * scale),
            (cx + 16 * scale, cy + 18 * scale),
        ]
        pygame.draw.polygon(screen, (200, 235, 255), points, 2)
        pygame.draw.line(
            screen,
            (90, 220, 255),
            (cx, cy + 20 * scale),
            (cx, cy + 34 * scale),
            2,
        )


def update_home_background(stars, home_ships, dt):
    for star in stars:
        star["y"] += star["speed"] * dt
        if star["y"] > SCREEN_HEIGHT:
            star["y"] = 0
            star["x"] = random.uniform(0, SCREEN_WIDTH)

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
    menu_font = pygame.font.SysFont(None, 46)
    hud_font = pygame.font.SysFont(None, 30)
    overlay_font = pygame.font.SysFont(None, 76)
    sub_font = pygame.font.SysFont(None, 28)

    sounds = SoundManager()

    stars = make_stars(140)
    home_ships = make_home_ships(4)

    menu_options = {
        STATE_HOME: ["Start", "Settings", "Quit"],
        STATE_PAUSED: ["Resume", "Restart", "Home", "Settings", "Quit"],
        STATE_GAME_OVER: ["Restart", "Home", "Settings", "Quit"],
        STATE_SETTINGS: ["Sound", "Volume", "Back"],
    }
    menu_index = {
        STATE_HOME: 0,
        STATE_PAUSED: 0,
        STATE_GAME_OVER: 0,
        STATE_SETTINGS: 0,
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

    def on_player_action(action_name):
        if action_name == "shoot":
            sounds.play("shoot")
        elif action_name == "bomb_drop":
            sounds.play("bomb_drop")

    def create_game_world():
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
        Explosion.containers = (updatable, drawable)
        AsteroidField.containers = (updatable,)

        player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        player.action_callback = on_player_action
        asteroid_field = AsteroidField()

        return {
            "updatable": updatable,
            "drawable": drawable,
            "asteroids": asteroids,
            "shots": shots,
            "bombs": bombs,
            "powerups": powerups,
            "player": player,
            "asteroid_field": asteroid_field,
        }

    def start_new_game():
        nonlocal game, score, lives, powerup_spawn_timer
        nonlocal respawn_invulnerable_timer, respawn_countdown_timer, state
        game = create_game_world()
        score = 0
        lives = PLAYER_STARTING_LIVES
        powerup_spawn_timer = 0
        respawn_invulnerable_timer = 0
        respawn_countdown_timer = 0
        state = STATE_PLAYING
        log_event("game_started")

    def change_state(next_state):
        nonlocal state
        state = next_state

    def handle_menu_action(action):
        nonlocal settings_return_state, state, running
        if action == "Start":
            sounds.play("menu_select")
            start_new_game()
        elif action == "Resume":
            sounds.play("menu_select")
            change_state(STATE_PLAYING)
        elif action == "Restart":
            sounds.play("menu_select")
            start_new_game()
        elif action == "Home":
            sounds.play("menu_select")
            change_state(STATE_HOME)
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

    running = True
    while running:
        elapsed += dt
        update_home_background(stars, home_ships, dt)

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

                elif state in (STATE_HOME, STATE_PAUSED, STATE_GAME_OVER, STATE_SETTINGS):
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
                        elif state == STATE_PAUSED:
                            sounds.play("menu_move")
                            change_state(STATE_PLAYING)

        if state == STATE_PLAYING:
            log_state()
            game["updatable"].update(dt)

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
                    log_event("bomb_detonated")
                    for asteroid in list(game["asteroids"]):
                        if asteroid.position.distance_to(blast_position) <= blast_radius + asteroid.radius:
                            add_score_for_asteroid(asteroid)
                            asteroid.split()

            for asteroid in list(game["asteroids"]):
                if not asteroid.alive():
                    continue

                player = game["player"]
                if respawn_invulnerable_timer <= 0 and player.collides_with(asteroid):
                    if player.has_shield():
                        player.consume_shield()
                        asteroid.split()
                        sounds.play("explosion")
                        log_event("shield_block")
                        continue

                    sounds.play("hit")
                    log_event("player_hit")
                    lives -= 1

                    if lives <= 0:
                        game_over_score = score
                        menu_index[STATE_GAME_OVER] = 0
                        change_state(STATE_GAME_OVER)
                        break

                    reset_player_for_respawn()
                    respawn_countdown_timer = PLAYER_RESPAWN_COUNTDOWN_SECONDS
                    change_state(STATE_RESPAWNING)
                    break

                for shot in list(game["shots"]):
                    if asteroid.collides_with(shot):
                        add_score_for_asteroid(asteroid)
                        shot.kill()
                        asteroid.split()
                        sounds.play("explosion")
                        log_event("asteroid_shot")
                        break

        elif state == STATE_RESPAWNING:
            respawn_countdown_timer -= dt
            if respawn_countdown_timer <= 0:
                respawn_countdown_timer = 0
                respawn_invulnerable_timer = PLAYER_RESPAWN_INVULNERABLE_SECONDS
                sounds.play("respawn")
                log_event("player_respawn", lives_remaining=lives)
                change_state(STATE_PLAYING)

        if state in (STATE_HOME,) or (state == STATE_SETTINGS and settings_return_state == STATE_HOME):
            draw_home_background(screen, stars, home_ships, elapsed)
        else:
            screen.fill((0, 0, 0))
            if game:
                for item in game["drawable"]:
                    item.draw(screen)

                player = game["player"]
                shield_text = f"Shield: {player.shield_timer:.1f}s" if player.has_shield() else "Shield: off"
                speed_text = (
                    f"Speed: {player.speed_boost_timer:.1f}s"
                    if player.speed_boost_timer > 0
                    else "Speed: off"
                )
                hud_text = (
                    f"Score: {score}  Lives: {lives}  Weapon: {player.weapon_name()}  "
                    f"Bombs: {player.bombs}"
                )
                screen.blit(hud_font.render(hud_text, True, "white"), (20, 20))
                screen.blit(hud_font.render(shield_text, True, "deepskyblue"), (20, 50))
                screen.blit(hud_font.render(speed_text, True, "springgreen"), (20, 80))

        if state == STATE_HOME:
            draw_center_text(screen, title_font, GAME_TITLE.upper(), 120, color="white")
            draw_center_text(screen, sub_font, "Pilot. Survive. Split the swarm.", 170, color="lightskyblue")
            draw_center_text(screen, sub_font, "Use arrow keys + Enter", 205, color="gray")

            for i, option in enumerate(menu_options[STATE_HOME]):
                color = "springgreen" if i == menu_index[STATE_HOME] else "white"
                draw_center_text(screen, menu_font, option, 280 + i * 45, color=color)

        elif state == STATE_PAUSED:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, (0, 0))
            draw_center_text(screen, overlay_font, "PAUSED", 140, color="white")
            for i, option in enumerate(menu_options[STATE_PAUSED]):
                color = "springgreen" if i == menu_index[STATE_PAUSED] else "white"
                draw_center_text(screen, menu_font, option, 240 + i * 44, color=color)

        elif state == STATE_SETTINGS:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))
            draw_center_text(screen, overlay_font, "SETTINGS", 120, color="white")

            sound_status = "On" if sounds.enabled else "Off"
            volume_percent = int(sounds.volume * 100)
            rendered_options = [
                f"Sound: {sound_status}",
                f"Volume: {volume_percent}%  (Left/Right)",
                "Back",
            ]

            for i, option in enumerate(rendered_options):
                color = "springgreen" if i == menu_index[STATE_SETTINGS] else "white"
                draw_center_text(screen, menu_font, option, 230 + i * 50, color=color)

            draw_center_text(screen, sub_font, "Esc to return", 390, color="gray")

        elif state == STATE_GAME_OVER:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            draw_center_text(screen, overlay_font, "GAME OVER", 120, color="orangered")
            draw_center_text(screen, menu_font, f"Final Score: {game_over_score}", 185, color="white")
            for i, option in enumerate(menu_options[STATE_GAME_OVER]):
                color = "springgreen" if i == menu_index[STATE_GAME_OVER] else "white"
                draw_center_text(screen, menu_font, option, 255 + i * 44, color=color)

        elif state == STATE_RESPAWNING:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 110))
            screen.blit(overlay, (0, 0))
            countdown_display = max(1, int(respawn_countdown_timer) + 1)
            draw_center_text(screen, overlay_font, f"RESPAWNING {countdown_display}", SCREEN_HEIGHT // 2 - 20)
            draw_center_text(screen, sub_font, "Get ready...", SCREEN_HEIGHT // 2 + 28, color="lightgray")

        pygame.display.flip()
        dt = clock.tick(60) / 1000


if __name__ == "__main__":
    main()
