# astro-vex

![astro-vex Logo](assets/logo.svg)

`astro-vex` is a fast arcade space shooter built with Python + Pygame.

## Features
- Animated home screen with starfield and moving ships.
- Main menu options: `Start`, `Settings`, `Quit`.
- Scene/state-based game flow:
- Home
- Playing
- Respawning
- Paused
- Game Over
- Settings
- In-game pause menu options: `Resume`, `Restart`, `Home`, `Settings`, `Quit`.
- Game over menu options: `Restart`, `Home`, `Settings`, `Quit`.
- 3-second respawn countdown overlay before gameplay continues.
- Player movement with acceleration, drag, and speed cap.
- Screen wrapping for player, shots, asteroids, bombs, and power-ups.
- Lumpy asteroid visuals (irregular polygons).
- Triangular player hitbox (ship is not circular for collisions).
- Multiple weapon types:
- `1` Single
- `2` Spread
- `3` Rapid
- Shield and speed power-ups.
- Bomb system with fuse and blast radius (`B` to drop).
- Score and lives HUD.
- Sound effects for combat, menu navigation, hits, respawn, and pickups.
- Settings menu for sound on/off and master volume.

## Controls
- `W` / `S`: Thrust forward / reverse thrust
- `A` / `D`: Rotate left / right
- `Space`: Fire weapon
- `1` / `2` / `3`: Switch weapon
- `B`: Drop bomb
- `Esc`: Pause / back from menus
- `Arrow Keys`: Menu navigation
- `Enter` or `Space`: Confirm menu selection

## Run Locally
1. Create and activate a Python virtual environment.
2. Install dependencies.
3. Run:

```bash
python main.py
```

## Project Structure
- `main.py`: Scene management, menus, gameplay loop, HUD, respawn/game over flow.
- `player.py`: Ship movement, weapons, bombs, power-up state, triangle collision.
- `asteroids.py`: Asteroid behavior, splitting, lumpy rendering.
- `asteroidfield.py`: Asteroid spawn system.
- `shot.py`: Bullet entity.
- `bomb.py`: Bomb entity and detonation.
- `powerup.py`: Shield/speed power-up entities.
- `explosion.py`: Explosion effect sprite.
- `sounds.py`: Runtime-generated sound effects manager.
- `circleshape.py`: Shared sprite base with wrapping/collision helpers.
- `logger.py`: JSONL event/state logging.
- `assets/logo.svg`: Project logo used in README.

## Contributions
Contributions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Implement and test your change.
4. Update `README.md` for any user-facing behavior change.
5. Open a pull request with a clear summary.

## Notes
- Generated logs are ignored by git: `game_state.jsonl`, `game_events.jsonl`.
- Gameplay tuning values are centralized in `constants.py`.
- Per your request, every future feature change should also update this README.
