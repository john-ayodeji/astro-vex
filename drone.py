import pygame

from circleshape import CircleShape
from constants import (
    DRONE_BASE_COOLDOWN_SECONDS,
    DRONE_BASE_HEALTH,
    DRONE_BASE_RANGE,
    DRONE_MAX_LEVEL,
    DRONE_RADIUS,
    DRONE_SHOT_SPEED,
)
from shot import Shot


class CompanionDrone(CircleShape):
    def __init__(self, player, asteroids_group):
        super().__init__(player.position.x, player.position.y, DRONE_RADIUS)
        self.player = player
        self.asteroids_group = asteroids_group
        self.level = 1
        self.max_health = DRONE_BASE_HEALTH
        self.health = self.max_health
        self.range = DRONE_BASE_RANGE
        self.cooldown = DRONE_BASE_COOLDOWN_SECONDS
        self.cooldown_timer = 0
        self.orbit_angle = 0

    def draw(self, screen):
        color = "#67e8f9" if self.health > 1 else "#fca5a5"
        pygame.draw.circle(screen, color, (self.position.x, self.position.y), self.radius)
        pygame.draw.circle(screen, "white", (self.position.x, self.position.y), self.radius, 1)

        # small health bar
        bar_w = 26
        bar_h = 4
        ratio = max(0, self.health / self.max_health)
        x = self.position.x - bar_w / 2
        y = self.position.y - self.radius - 10
        pygame.draw.rect(screen, "#334155", (x, y, bar_w, bar_h))
        pygame.draw.rect(screen, "#22c55e", (x, y, bar_w * ratio, bar_h))

    def update(self, dt):
        if not self.player.alive():
            return

        self.orbit_angle += 110 * dt
        offset = pygame.Vector2(0, 1).rotate(self.orbit_angle) * 38
        self.position = self.player.position + offset

        self.cooldown_timer -= dt
        target = self._nearest_target()
        if target is not None and self.cooldown_timer <= 0:
            direction = target.position - self.position
            if direction.length_squared() > 0:
                direction = direction.normalize()
                shot = Shot(self.position.x, self.position.y)
                shot.velocity = direction * DRONE_SHOT_SPEED
                self.cooldown_timer = self.cooldown

    def damage(self, amount=1):
        self.health -= amount
        if self.health <= 0:
            self.kill()

    def upgrade(self):
        if self.level >= DRONE_MAX_LEVEL:
            return False

        self.level += 1
        self.max_health += 1
        self.health = self.max_health
        self.range += 40
        self.cooldown = max(0.18, self.cooldown * 0.82)
        return True

    def _nearest_target(self):
        best = None
        best_dist = self.range
        for asteroid in self.asteroids_group:
            dist = asteroid.position.distance_to(self.position)
            if dist <= best_dist:
                best = asteroid
                best_dist = dist
        return best
