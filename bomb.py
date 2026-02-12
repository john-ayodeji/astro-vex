import pygame.draw

from circleshape import CircleShape
from constants import BOMB_RADIUS, BOMB_FUSE_SECONDS, BOMB_BLAST_RADIUS
from explosion import Explosion


class Bomb(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, BOMB_RADIUS)
        self.fuse_timer = BOMB_FUSE_SECONDS
        self.detonated = False

    def draw(self, screen):
        pygame.draw.circle(
            screen,
            "white",
            (self.position.x, self.position.y),
            self.radius,
            1,
        )

    def update(self, dt):
        self.position += self.velocity * dt
        self.wrap_position()
        self.fuse_timer -= dt

    def ready_to_detonate(self):
        return self.fuse_timer <= 0 and not self.detonated

    def detonate(self):
        self.detonated = True
        Explosion(self.position.x, self.position.y, BOMB_BLAST_RADIUS / 2)
        blast_position = self.position.copy()
        self.kill()
        return blast_position, BOMB_BLAST_RADIUS
