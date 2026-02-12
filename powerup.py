import pygame.draw

from circleshape import CircleShape
from constants import POWERUP_RADIUS


class PowerUp(CircleShape):
    kind = "base"
    color = "white"

    def __init__(self, x, y):
        super().__init__(x, y, POWERUP_RADIUS)

    def draw(self, screen):
        pygame.draw.circle(
            screen,
            self.color,
            (self.position.x, self.position.y),
            self.radius,
            2,
        )

    def update(self, dt):
        self.position += self.velocity * dt
        self.wrap_position()


class ShieldPowerUp(PowerUp):
    kind = "shield"
    color = "deepskyblue"


class SpeedPowerUp(PowerUp):
    kind = "speed"
    color = "springgreen"
