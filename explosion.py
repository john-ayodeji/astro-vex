import pygame

from constants import LINE_WIDTH, EXPLOSION_DURATION_SECONDS, EXPLOSION_GROWTH_SCALE


class Explosion(pygame.sprite.Sprite):
    def __init__(self, x, y, radius):
        if hasattr(self, "containers"):
            super().__init__(self.containers)
        else:
            super().__init__()

        self.position = pygame.Vector2(x, y)
        self.base_radius = radius
        self.age = 0

    def update(self, dt):
        self.age += dt
        if self.age >= EXPLOSION_DURATION_SECONDS:
            self.kill()

    def draw(self, screen):
        progress = min(1, self.age / EXPLOSION_DURATION_SECONDS)
        radius = self.base_radius * (1 + (EXPLOSION_GROWTH_SCALE - 1) * progress)
        line_width = max(1, int(LINE_WIDTH * (2 - progress)))

        pygame.draw.circle(
            screen,
            "white",
            (self.position.x, self.position.y),
            radius,
            line_width,
        )
