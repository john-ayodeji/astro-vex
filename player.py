import pygame

from bomb import Bomb
from circleshape import CircleShape
from constants import (
    PLAYER_RADIUS,
    LINE_WIDTH,
    PLAYER_TURN_SPEED,
    PLAYER_SPEED,
    PLAYER_SHOOT_SPEED,
    PLAYER_ACCELERATION,
    PLAYER_DRAG,
    WEAPON_SINGLE_COOLDOWN_SECONDS,
    WEAPON_SPREAD_COOLDOWN_SECONDS,
    WEAPON_RAPID_COOLDOWN_SECONDS,
    WEAPON_SPREAD_ANGLE_DEGREES,
    SHIELD_DURATION_SECONDS,
    SPEED_BOOST_DURATION_SECONDS,
    SPEED_BOOST_MULTIPLIER,
    PLAYER_BOMB_COOLDOWN_SECONDS,
    BOMB_STARTING_COUNT,
)
from shot import Shot


class Player(CircleShape):
    WEAPON_NAMES = ["Single", "Spread", "Rapid"]

    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_RADIUS)
        self.rotation = 0
        self.shoot_cooldown_timer = 0
        self.bomb_cooldown_timer = 0
        self.space_was_pressed = False
        self.b_was_pressed = False
        self.weapon_1_was_pressed = False
        self.weapon_2_was_pressed = False
        self.weapon_3_was_pressed = False
        self.weapon_mode = 0
        self.shield_timer = 0
        self.speed_boost_timer = 0
        self.bombs = BOMB_STARTING_COUNT
        self.action_callback = None

    def triangle(self):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        right = pygame.Vector2(0, 1).rotate(self.rotation + 90) * self.radius / 1.5
        a = self.position + forward * self.radius
        b = self.position - forward * self.radius - right
        c = self.position - forward * self.radius + right
        return [a, b, c]

    def draw(self, screen):
        pygame.draw.polygon(screen, "white", self.triangle(), LINE_WIDTH)

        if self.shield_timer > 0:
            pygame.draw.circle(
                screen,
                "deepskyblue",
                (self.position.x, self.position.y),
                self.radius + 8,
                2,
            )

    def rotate(self, dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def shoot(self):
        if self.shoot_cooldown_timer > 0:
            return

        base_velocity = pygame.Vector2(0, 1).rotate(self.rotation) * PLAYER_SHOOT_SPEED

        if self.weapon_mode == 0:
            shot = Shot(self.position.x, self.position.y)
            shot.velocity = base_velocity
            self.shoot_cooldown_timer = WEAPON_SINGLE_COOLDOWN_SECONDS
            self._emit_action("shoot")
            return

        if self.weapon_mode == 1:
            for angle in (-WEAPON_SPREAD_ANGLE_DEGREES, 0, WEAPON_SPREAD_ANGLE_DEGREES):
                shot = Shot(self.position.x, self.position.y)
                shot.velocity = base_velocity.rotate(angle)
            self.shoot_cooldown_timer = WEAPON_SPREAD_COOLDOWN_SECONDS
            self._emit_action("shoot")
            return

        shot_left = Shot(self.position.x, self.position.y)
        shot_left.velocity = base_velocity.rotate(-5)
        shot_right = Shot(self.position.x, self.position.y)
        shot_right.velocity = base_velocity.rotate(5)
        self.shoot_cooldown_timer = WEAPON_RAPID_COOLDOWN_SECONDS
        self._emit_action("shoot")

    def drop_bomb(self):
        if self.bombs <= 0 or self.bomb_cooldown_timer > 0:
            return

        bomb = Bomb(self.position.x, self.position.y)
        bomb.velocity = self.velocity * 0.5
        self.bombs -= 1
        self.bomb_cooldown_timer = PLAYER_BOMB_COOLDOWN_SECONDS
        self._emit_action("bomb_drop")

    def apply_shield(self):
        self.shield_timer = SHIELD_DURATION_SECONDS

    def apply_speed_boost(self):
        self.speed_boost_timer = SPEED_BOOST_DURATION_SECONDS

    def has_shield(self):
        return self.shield_timer > 0

    def consume_shield(self):
        self.shield_timer = 0

    def weapon_name(self):
        return self.WEAPON_NAMES[self.weapon_mode]

    def collides_with(self, other):
        if not hasattr(other, "position") or not hasattr(other, "radius"):
            return super().collides_with(other)

        triangle = self.triangle()
        circle_center = other.position
        circle_radius = other.radius

        if self._point_in_triangle(circle_center, triangle):
            return True

        for point in triangle:
            if point.distance_to(circle_center) <= circle_radius:
                return True

        for i in range(3):
            a = triangle[i]
            b = triangle[(i + 1) % 3]
            closest = self._closest_point_on_segment(circle_center, a, b)
            if closest.distance_to(circle_center) <= circle_radius:
                return True

        return False

    def update(self, dt):
        self.shoot_cooldown_timer -= dt
        self.bomb_cooldown_timer -= dt
        self.shield_timer = max(0, self.shield_timer - dt)
        self.speed_boost_timer = max(0, self.speed_boost_timer - dt)

        keys = pygame.key.get_pressed()

        if keys[pygame.K_a]:
            self.rotate(-dt)

        if keys[pygame.K_d]:
            self.rotate(dt)

        if keys[pygame.K_w]:
            self.accelerate(dt)

        if keys[pygame.K_s]:
            self.accelerate(-dt)

        if keys[pygame.K_SPACE] and not self.space_was_pressed:
            self.shoot()
        self.space_was_pressed = keys[pygame.K_SPACE]

        if keys[pygame.K_b] and not self.b_was_pressed:
            self.drop_bomb()
        self.b_was_pressed = keys[pygame.K_b]

        if keys[pygame.K_1] and not self.weapon_1_was_pressed:
            self.weapon_mode = 0
        if keys[pygame.K_2] and not self.weapon_2_was_pressed:
            self.weapon_mode = 1
        if keys[pygame.K_3] and not self.weapon_3_was_pressed:
            self.weapon_mode = 2

        self.weapon_1_was_pressed = keys[pygame.K_1]
        self.weapon_2_was_pressed = keys[pygame.K_2]
        self.weapon_3_was_pressed = keys[pygame.K_3]

        self.position += self.velocity * dt

        drag_multiplier = max(0, 1 - PLAYER_DRAG * dt)
        self.velocity *= drag_multiplier
        if self.velocity.length() < 1:
            self.velocity = pygame.Vector2(0, 0)

        speed_cap = PLAYER_SPEED
        if self.speed_boost_timer > 0:
            speed_cap *= SPEED_BOOST_MULTIPLIER

        if self.velocity.length() > speed_cap:
            self.velocity.scale_to_length(speed_cap)

        self.wrap_position()

    def accelerate(self, dt):
        thrust_direction = pygame.Vector2(0, 1).rotate(self.rotation)
        acceleration = PLAYER_ACCELERATION
        if self.speed_boost_timer > 0:
            acceleration *= SPEED_BOOST_MULTIPLIER
        self.velocity += thrust_direction * acceleration * dt

    def _point_in_triangle(self, p, triangle):
        a, b, c = triangle
        b1 = self._sign(p, a, b) < 0
        b2 = self._sign(p, b, c) < 0
        b3 = self._sign(p, c, a) < 0
        return b1 == b2 == b3

    def _sign(self, p1, p2, p3):
        return (p1.x - p3.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p3.y)

    def _closest_point_on_segment(self, p, a, b):
        ab = b - a
        if ab.length_squared() == 0:
            return a
        t = (p - a).dot(ab) / ab.length_squared()
        t = max(0, min(1, t))
        return a + ab * t

    def _emit_action(self, action_name):
        if callable(self.action_callback):
            self.action_callback(action_name)
