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
        self.music_mode = None
        self.music_channel = None
        self.music_loops = {}

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
        self.sounds["boss_death"] = self._generate_tone(70, 0.5, 0.35, wave="saw")
        self.sounds["drone_upgrade"] = self._generate_tone(980, 0.15, 0.2)

        self.music_channel = pygame.mixer.Channel(6)
        self.music_loops["calm"] = self._generate_tone(140, 1.2, 0.07)
        self.music_loops["intense"] = self._generate_tone(210, 0.9, 0.09, wave="square")
        self.music_loops["boss"] = self._generate_tone(92, 1.1, 0.1, wave="saw")

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        if self.music_channel is not None:
            self.music_channel.set_volume(self.volume * 0.4)

    def toggle_enabled(self):
        self.enabled = not self.enabled
        if not self.enabled and self.music_channel is not None:
            self.music_channel.stop()
        elif self.enabled and self.music_mode is not None:
            self.update_music_mode(self.music_mode)

    def play(self, name):
        if not self.available or not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        sound.set_volume(self.volume)
        sound.play()

    def update_music_mode(self, mode):
        if not self.available:
            return
        if mode == self.music_mode:
            return

        self.music_mode = mode
        if not self.enabled:
            self.music_channel.stop()
            return

        loop = self.music_loops.get(mode)
        if loop is None:
            self.music_channel.stop()
            return

        loop.set_volume(self.volume * 0.4)
        self.music_channel.play(loop, loops=-1)

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
