import math
import random

import pygame.draw

from constants import LINE_WIDTH, ASTEROID_MIN_RADIUS
from circleshape import CircleShape
from explosion import Explosion
from logger import log_event


class Asteroid(CircleShape):
    def __init__(self, x, y, radius):
        super().__init__(x, y, radius)
        self.shape_points = self._generate_lumpy_points()

    def draw(self, screen):
        world_points = [
            (self.position.x + point.x, self.position.y + point.y)
            for point in self.shape_points
        ]
        pygame.draw.polygon(screen, "white", world_points, LINE_WIDTH)

    def update(self, dt):
        self.position += self.velocity * dt
        self.wrap_position()

    def split(self):
        Explosion(self.position.x, self.position.y, self.radius)
        self.kill()

        if self.radius <= ASTEROID_MIN_RADIUS:
            return

        log_event("asteroid_split")
        angle = random.uniform(20, 50)
        velocity_1 = self.velocity.rotate(angle)
        velocity_2 = self.velocity.rotate(-angle)
        new_radius = self.radius - ASTEROID_MIN_RADIUS

        asteroid_1 = Asteroid(self.position.x, self.position.y, new_radius)
        asteroid_2 = Asteroid(self.position.x, self.position.y, new_radius)
        asteroid_1.velocity = velocity_1 * 1.2
        asteroid_2.velocity = velocity_2 * 1.2

    def _generate_lumpy_points(self):
        points = []
        vertex_count = random.randint(9, 13)
        for i in range(vertex_count):
            angle = (2 * math.pi * i) / vertex_count
            radius_scale = random.uniform(0.75, 1.25)
            r = self.radius * radius_scale
            points.append(pygame.Vector2(math.cos(angle) * r, math.sin(angle) * r))
        return points
