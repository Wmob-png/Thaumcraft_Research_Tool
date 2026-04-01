import os
import random

import pygame

from resources import asset_path


class AnimatedGIF:
    def __init__(self, filename, scale=1.0):
        self.frames = []
        self.durations = []
        self.current_frame = 0
        self.timer = 0
        self.loaded = False
        self.loop = True
        self.finished = False
        self.filename = filename

        self._load_gif(filename, scale)

    def _load_gif(self, filename, scale):
        try:
            from PIL import Image
        except ImportError:
            return

        try:
            path = asset_path(filename)
        except Exception:
            return

        if not os.path.exists(path):
            return

        try:
            pil_image = Image.open(path)

            frame_count = 0
            while True:
                try:
                    pil_image.seek(frame_count)

                    frame = pil_image.copy()

                    if frame.mode == "P":
                        frame = frame.convert("RGBA")
                    elif frame.mode != "RGBA":
                        frame = frame.convert("RGBA")

                    if scale != 1.0:
                        new_size = (int(frame.width * scale), int(frame.height * scale))
                        frame = frame.resize(new_size, Image.NEAREST)

                    mode = frame.mode
                    size = frame.size
                    data = frame.tobytes()

                    pygame_surface = pygame.image.fromstring(data, size, mode).convert_alpha()
                    self.frames.append(pygame_surface)

                    duration = pil_image.info.get("duration", 100)
                    if duration == 0:
                        duration = 100
                    self.durations.append(duration)

                    frame_count += 1
                except EOFError:
                    break

            if frame_count > 0:
                self.loaded = True

        except Exception:
            self.loaded = False

    def reset(self):
        self.current_frame = 0
        self.timer = 0
        self.finished = False

    def update(self, dt_ms):
        if not self.loaded or len(self.frames) == 0:
            return False

        if self.finished and not self.loop:
            return False

        looped = False
        self.timer += dt_ms

        current_duration = self.durations[self.current_frame]
        while self.timer >= current_duration:
            self.timer -= current_duration
            self.current_frame += 1

            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                    looped = True
                else:
                    self.current_frame = len(self.frames) - 1
                    self.finished = True
                    break

            current_duration = self.durations[self.current_frame]

        return looped

    def get_current_frame(self):
        if not self.loaded or len(self.frames) == 0:
            return None
        return self.frames[self.current_frame]

    def is_finished(self):
        return self.finished

    def get_size(self):
        if self.frames:
            return self.frames[0].get_size()
        return (0, 0)


class CatButtonManager:
    STATE_IDLE = "idle"
    STATE_WALK = "walk"
    STATE_CHEER = "cheer"
    STATE_SPIN = "spin"

    RANDOM_STATES = [STATE_IDLE, STATE_WALK]

    def __init__(self, switch_chance=0.05):
        self.idle_gif = None
        self.walk_gif = None
        self.cheer_gif = None
        self.spin_gif = None

        self.current_state = self.STATE_WALK
        self.loaded = False
        self.switch_chance = switch_chance

        self._scaled_cache = {}
        self._last_size = None

        self._load_animations()

    def _load_animations(self):
        try:
            self.idle_gif = AnimatedGIF("CAT_idle_1.gif")
            self.idle_gif.loop = True

            self.walk_gif = AnimatedGIF("CAT_walk_1.gif")
            self.walk_gif.loop = True

            self.cheer_gif = AnimatedGIF("CAT_win_cheer_1.gif")
            self.cheer_gif.loop = False

            self.spin_gif = AnimatedGIF("CAT_spining_1.gif")
            self.spin_gif.loop = False

            self.loaded = self.idle_gif.loaded or self.walk_gif.loaded

            if self.loaded:
                if self.walk_gif.loaded:
                    self.current_state = self.STATE_WALK
                elif self.idle_gif.loaded:
                    self.current_state = self.STATE_IDLE

        except Exception:
            self.loaded = False

    def _get_random_state(self):
        available = []
        if self.idle_gif and self.idle_gif.loaded:
            available.append(self.STATE_IDLE)
        if self.walk_gif and self.walk_gif.loaded:
            available.append(self.STATE_WALK)

        if not available:
            return self.current_state

        if len(available) > 1 and self.current_state in available:
            available.remove(self.current_state)

        return random.choice(available)

    def _get_looping_gif(self):
        if self.current_state == self.STATE_IDLE:
            return self.idle_gif
        elif self.current_state == self.STATE_WALK:
            return self.walk_gif
        return None

    def trigger_spin(self):
        if self.spin_gif and self.spin_gif.loaded:
            self.current_state = self.STATE_SPIN
            self.spin_gif.reset()

    def trigger_cheer(self):
        if self.cheer_gif and self.cheer_gif.loaded:
            self.current_state = self.STATE_CHEER
            self.cheer_gif.reset()

    def _return_to_random_state(self):
        new_state = self._get_random_state()
        self.current_state = new_state

        gif = self._get_looping_gif()
        if gif:
            gif.reset()

    def update(self, dt_ms):
        if not self.loaded:
            return

        if self.current_state in self.RANDOM_STATES:
            gif = self._get_looping_gif()
            if gif and gif.loaded:
                looped = gif.update(dt_ms)

                if looped:
                    if random.random() < self.switch_chance:
                        new_state = self._get_random_state()
                        if new_state != self.current_state:
                            self.current_state = new_state
                            new_gif = self._get_looping_gif()
                            if new_gif:
                                new_gif.reset()

        elif self.current_state == self.STATE_CHEER:
            if self.cheer_gif and self.cheer_gif.loaded:
                self.cheer_gif.update(dt_ms)

                if self.cheer_gif.is_finished():
                    self._return_to_random_state()

        elif self.current_state == self.STATE_SPIN:
            if self.spin_gif and self.spin_gif.loaded:
                self.spin_gif.update(dt_ms)

                if self.spin_gif.is_finished():
                    self._return_to_random_state()

    def get_current_frame(self):
        if self.current_state == self.STATE_IDLE and self.idle_gif:
            return self.idle_gif.get_current_frame()
        elif self.current_state == self.STATE_WALK and self.walk_gif:
            return self.walk_gif.get_current_frame()
        elif self.current_state == self.STATE_CHEER and self.cheer_gif:
            return self.cheer_gif.get_current_frame()
        elif self.current_state == self.STATE_SPIN and self.spin_gif:
            return self.spin_gif.get_current_frame()
        return None

    def _get_current_gif(self):
        if self.current_state == self.STATE_IDLE:
            return self.idle_gif
        elif self.current_state == self.STATE_WALK:
            return self.walk_gif
        elif self.current_state == self.STATE_CHEER:
            return self.cheer_gif
        elif self.current_state == self.STATE_SPIN:
            return self.spin_gif
        return None

    def draw_in_button(self, screen, rect, active=True, scale_mult=1.0):
        frame = self.get_current_frame()
        if not frame:
            return

        min_dim = min(rect.width, rect.height)
        if min_dim <= 0:
            return

        target_size = int(min_dim * 0.9 * scale_mult)
        target_size = min(target_size, min_dim)

        gif = self._get_current_gif()
        if gif:
            cache_key = (self.current_state, gif.current_frame, target_size)
        else:
            cache_key = None

        if target_size != self._last_size:
            self._scaled_cache.clear()
            self._last_size = target_size

        if cache_key and cache_key in self._scaled_cache:
            scaled_frame = self._scaled_cache[cache_key]
        else:
            scaled_frame = pygame.transform.scale(frame, (target_size, target_size))

            if cache_key:
                self._scaled_cache[cache_key] = scaled_frame

                if len(self._scaled_cache) > 100:
                    keys_to_remove = list(self._scaled_cache.keys())[:50]
                    for k in keys_to_remove:
                        del self._scaled_cache[k]

        if not active:
            scaled_frame = scaled_frame.copy()
            scaled_frame.set_alpha(80)

        frame_rect = scaled_frame.get_rect(center=rect.center)
        screen.blit(scaled_frame, frame_rect)