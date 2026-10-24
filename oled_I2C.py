# microtween.py - non-blocking tween / animation engine for MicroPython
#
# Animate ANY value over time (servo angle, PWM duty, OLED x/y, LED brightness)
# without blocking your main loop.
#
# Example:
#   from microtween import Tweener, Tween, Sequence, Parallel, Wait, out_bounce
#
#   tw = Tweener()
#   tw.add(Sequence(
#       Tween(0, 90, 800, out_bounce, on_update=lambda v: servo(int(v))),
#       Wait(300),
#       Parallel(
#           Tween(90, 0, 500, on_update=lambda v: servo(int(v))),
#           Tween(0, 100, 500, on_update=lambda v: oled_x(int(v))),
#       ),
#   ))
#   while tw.busy():
#       tw.update()      # call as often as you like
#       # ... do other work here ...

import time
import math

_ticks = time.ticks_ms
_diff = time.ticks_diff
_add = time.ticks_add


# ---------- easing functions: take p in [0, 1], return ~[0, 1] ----------
def linear(p):
    return p


def in_quad(p):
    return p * p


def out_quad(p):
    return p * (2 - p)


def in_out_quad(p):
    return 2 * p * p if p < 0.5 else -1 + (4 - 2 * p) * p


def in_out_cubic(p):
    return 4 * p * p * p if p < 0.5 else 1 - ((-2 * p + 2) ** 3) / 2


def out_back(p):
    c1 = 1.70158
    c3 = c1 + 1
    q = p - 1
    return 1 + c3 * q * q * q + c1 * q * q


def out_elastic(p):
    if p <= 0:
        return 0
    if p >= 1:
        return 1
    return (2 ** (-10 * p)) * math.sin((p * 10 - 0.75) * (2 * math.pi / 3)) + 1


def out_bounce(p):
    n1, d1 = 7.5625, 2.75
    if p < 1 / d1:
        return n1 * p * p
    if p < 2 / d1:
        p -= 1.5 / d1
        return n1 * p * p + 0.75
    if p < 2.5 / d1:
        p -= 2.25 / d1
        return n1 * p * p + 0.9375
    p -= 2.625 / d1
    return n1 * p * p + 0.984375


# ---------- animation primitives ----------
# Every primitive has: begin(now) and step(now) -> True while still running.
class Tween:
    """Animate a value from `a` to `b` in `ms` milliseconds.

    repeat: extra cycles after the first (-1 = forever)
    yoyo:   reverse direction on every other cycle
    """

    def __init__(self, a, b, ms, ease=linear, on_update=None, on_done=None,
                 delay=0, repeat=0, yoyo=False):
        self.a, self.b = a, b
        self.ms = max(1, int(ms))
        self.ease = ease
        self.on_update = on_update
        self.on_done = on_done
        self.delay = delay
        self.repeat = repeat
        self.yoyo = yoyo
        self.value = a
        self.done = True
        self._t0 = 0

    def begin(self, now=None):
        now = _ticks() if now is None else now
        self._t0 = _add(now, self.delay)
        self.done = False

    def step(self, now):
        if self.done:
            return False
        dt = _diff(now, self._t0)
        if dt < 0:  # still in the start delay
            return True
        n, dt = divmod(dt, self.ms)
        finished = self.repeat >= 0 and n > self.repeat
        if finished:
            n, dt = self.repeat, self.ms
        p = dt / self.ms
        if self.yoyo and (n & 1):
            p = 1 - p
        self.value = self.a + (self.b - self.a) * self.ease(p)
        if self.on_update:
            self.on_update(self.value)
        if finished:
            self.done = True
            if self.on_done:
                self.on_done()
            return False
        return True

    def stop(self):
        self.done = True


class Wait(Tween):
    """Pause inside a Sequence."""

    def __init__(self, ms, on_done=None):
        super().__init__(0, 0, ms, on_done=on_done)


class Sequence:
    """Run items one after another."""

    def __init__(self, *items, on_done=None):
        self.items = items
        self.on_done = on_done
        self.done = True
        self._i = 0

    def begin(self, now=None):
        now = _ticks() if now is None else now
        self._i = 0
        self.done = not self.items
        if self.items:
            self.items[0].begin(now)

    def step(self, now):
        if self.done:
            return False
        if not self.items[self._i].step(now):
            self._i += 1
            if self._i >= len(self.items):
                self.done = True
                if self.on_done:
                    self.on_done()
                return False
            self.items[self._i].begin(now)
        return True

    def stop(self):
        self.done = True


class Parallel:
    """Run items at the same time; finishes when all are finished."""

    def __init__(self, *items, on_done=None):
        self.items = items
        self.on_done = on_done
        self.done = True
        self._live = []

    def begin(self, now=None):
        now = _ticks() if now is None else now
        self._live = list(self.items)
        self.done = not self._live
        for it in self._live:
            it.begin(now)

    def step(self, now):
        if self.done:
            return False
        self._live = [it for it in self._live if it.step(now)]
        if not self._live:
            self.done = True
            if self.on_done:
                self.on_done()
            return False
        return True

    def stop(self):
        self.done = True


class Tweener:
    """The engine. Add animations, then call update() from your main loop."""

    def __init__(self):
        self._active = []

    def add(self, anim):
        anim.begin(_ticks())
        self._active.append(anim)
        return anim

    def update(self):
        now = _ticks()
        self._active = [a for a in self._active if a.step(now)]

    def busy(self):
        return bool(self._active)

    def clear(self):
        for a in self._active:
            a.stop()
        self._active = []

    def run(self, sleep_ms=5):
        """Blocking helper: run until everything finishes."""
        while self._active:
            self.update()
            time.sleep_ms(sleep_ms)


# ---------- EASY MODE (for beginners) ----------
# Style names you can use:
#   "line"    constant speed        "smooth"  slow start, slow end
#   "bounce"  bounces like a ball   "elastic" springy
#   "back"    overshoots a little   "slow_start" / "slow_end"
STYLES = {
    "line": linear, "smooth": in_out_quad, "bounce": out_bounce,
    "elastic": out_elastic, "back": out_back,
    "slow_start": in_quad, "slow_end": out_quad,
}


class Animator:
    """Easiest way to use microtween:

        a = Animator()
        a.go("x", 0, 100, 2, "bounce")   # x goes 0 -> 100 in 2 seconds
        while True:
            a.update()
            print(a.get("x"))
    """

    def __init__(self):
        self.v = {}
        self._tw = Tweener()

    def go(self, name, start, end, seconds, style="smooth", loop=True):
        self.v[name] = start

        def setter(val):
            self.v[name] = val

        self._tw.add(Tween(start, end, seconds * 1000, STYLES[style],
                           on_update=setter,
                           repeat=-1 if loop else 0, yoyo=loop))

    def get(self, name):
        return int(self.v[name])

    def update(self):
        self._tw.update()