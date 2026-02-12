from collections import deque


class AchievementTracker:
    def __init__(self):
        self.unlocked = set()
        self.notifications = deque()
        self.demolition_window = deque()
        self.current_wave = 1
        self.damage_taken_in_wave = False

    def start_new_run(self):
        self.unlocked.clear()
        self.notifications.clear()
        self.demolition_window.clear()
        self.current_wave = 1
        self.damage_taken_in_wave = False

    def mark_player_hit(self):
        self.damage_taken_in_wave = True

    def on_wave_change(self, new_wave):
        if new_wave <= self.current_wave:
            return

        if not self.damage_taken_in_wave:
            self._unlock(
                "untouchable",
                "Untouchable",
                "Survived a full wave without taking damage",
            )

        self.current_wave = new_wave
        self.damage_taken_in_wave = False

    def record_asteroid_destroyed(self, now_seconds):
        self.demolition_window.append(now_seconds)
        while self.demolition_window and now_seconds - self.demolition_window[0] > 10:
            self.demolition_window.popleft()

        if len(self.demolition_window) >= 50:
            self._unlock(
                "demolitionist",
                "Demolitionist",
                "Destroyed 50 asteroids within 10 seconds",
            )

    def record_bomb_detonation(self, objects_hit):
        if objects_hit >= 10:
            self._unlock(
                "overkill",
                "Overkill",
                "Detonated a bomb that hit 10+ objects",
            )

    def pop_notifications(self):
        notes = list(self.notifications)
        self.notifications.clear()
        return notes

    def _unlock(self, key, title, description):
        if key in self.unlocked:
            return
        self.unlocked.add(key)
        self.notifications.append(
            {
                "key": key,
                "title": title,
                "description": description,
            }
        )
