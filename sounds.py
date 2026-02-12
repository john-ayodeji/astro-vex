import math
from array import array

import pygame

from constants import SOUND_DEFAULT_VOLUME


class SoundManager:
    def __init__(self):
        self.enabled = True
        self.volume = SOUND_DEFAULT_VOLUME
        self.available = False
        self.sounds = {}

        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=1)
            self.available = True
        except pygame.error:
            self.available = False
            return

        self.sounds["shoot"] = self._generate_tone(900, 0.06, 0.2, wave="square")
        self.sounds["explosion"] = self._generate_tone(120, 0.18, 0.3, wave="saw")
        self.sounds["menu_move"] = self._generate_tone(600, 0.04, 0.15)
        self.sounds["menu_select"] = self._generate_tone(760, 0.07, 0.2)
        self.sounds["powerup"] = self._generate_tone(1050, 0.12, 0.2)
        self.sounds["hit"] = self._generate_tone(220, 0.16, 0.25)
        self.sounds["bomb_drop"] = self._generate_tone(420, 0.1, 0.2)
        self.sounds["respawn"] = self._generate_tone(520, 0.2, 0.2)

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))

    def toggle_enabled(self):
        self.enabled = not self.enabled

    def play(self, name):
        if not self.available or not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        sound.set_volume(self.volume)
        sound.play()

    def _generate_tone(self, frequency, duration_seconds, amplitude, wave="sine"):
        sample_rate = 44100
        sample_count = int(sample_rate * duration_seconds)
        samples = array("h")
        max_int16 = 32767

        for i in range(sample_count):
            t = i / sample_rate
            phase = 2 * math.pi * frequency * t
            if wave == "square":
                value = 1.0 if math.sin(phase) >= 0 else -1.0
            elif wave == "saw":
                period = 1 / frequency
                value = ((t % period) / period) * 2 - 1
            else:
                value = math.sin(phase)
            samples.append(int(value * amplitude * max_int16))

        return pygame.mixer.Sound(buffer=samples.tobytes())
