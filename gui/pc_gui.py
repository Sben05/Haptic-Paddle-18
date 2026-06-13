import argparse, math, sys, os, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "haptic_effects"))
from haptic_effects import EFFECTS

RANGE_DEG = 40.0

class Demo:
    def __init__(self):
        self.t0 = time.time()
        self.key = "6"
    def read(self):
        t = time.time() - self.t0
        x = 0.95 * math.sin(2 * math.pi * 0.15 * t)
        name, fn = EFFECTS[self.key]
        F_des = fn(x)
        F = F_des + 0.05 * math.sin(2 * math.pi * 7 * t)
        i = max(-1.0, min(1.0, F_des + 0.6 * (F_des - F)))
        return t, x, F, i
    def send(self, c):
        if c in EFFECTS:
            self.key = c

class Live:
    def __init__(self, port):
        import serial
        self.ser = serial.Serial(port, 115200, timeout=0)
        self.last = (0.0, 0.0, 0.0, 0.0)
        self.key = "6"
    def read(self):
        while True:
            line = self.ser.readline().decode(errors="ignore").strip()
            if not line:
                return self.last
            if line.startswith("T,"):
                try:
                    _, t, x, F, i = line.split(",")
                    self.last = (float(t), float(x), float(F), float(i))
                except ValueError:
                    pass
            elif line.startswith("#"):
                print(line)
    def send(self, c):
        self.ser.write(c.encode())
        if c in EFFECTS:
            self.key = c

def build(src, screenshot=None):
    import matplotlib
    if screenshot:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.animation import FuncAnimation

    fig = plt.figure(figsize=(12.5, 4.6), dpi=110)
    fig.canvas.manager.set_window_title("ME433 haptic paddle") if not screenshot else None
    ax_dial = fig.add_subplot(1, 3, 1)
    ax_bars = fig.add_subplot(1, 3, 2)
    ax_eff  = fig.add_subplot(1, 3, 3)

    th = np.linspace(math.radians(90 - RANGE_DEG), math.radians(90 + RANGE_DEG), 80)
    ax_dial.plot(np.cos(th), np.sin(th), color="#999", lw=2)
    for s in (-1, 0, 1):
        a = math.radians(90 - s * RANGE_DEG)
        ax_dial.plot([0.92 * math.cos(a), 1.0 * math.cos(a)],
                     [0.92 * math.sin(a), 1.0 * math.sin(a)], color="#999", lw=2)
    needle, = ax_dial.plot([0, 0], [0, 0.88], color="#b03030", lw=4,
                           solid_capstyle="round")
    txt = ax_dial.text(0, -0.18, "", ha="center", fontsize=11)
    ax_dial.set_xlim(-1.15, 1.15); ax_dial.set_ylim(-0.3, 1.15)
    ax_dial.set_aspect("equal"); ax_dial.axis("off")
    ax_dial.set_title("paddle position")

    bars = ax_bars.bar(["F meas", "i des"], [0, 0],
                       color=["#2a6a2a", "#2a4a8a"], width=0.55)
    ax_bars.axhline(0, color="#888", lw=0.8)
    ax_bars.set_ylim(-1.1, 1.1); ax_bars.set_title("normalized force and current")
    ax_bars.grid(alpha=0.25, axis="y")

    X = np.linspace(-1, 1, 400)
    curve, = ax_eff.plot([], [], color="#b03030", lw=2)
    dot, = ax_eff.plot([], [], "o", color="#15314f", ms=9)
    ax_eff.axhline(0, color="#999", lw=0.8); ax_eff.axvline(0, color="#999", lw=0.8)
    ax_eff.set_xlim(-1, 1); ax_eff.set_ylim(-1.1, 1.1)
    ax_eff.set_xlabel("x"); ax_eff.set_ylabel("F")
    ax_eff.grid(alpha=0.25)

    state = {"key": src.key}
    def draw_curve():
        name, fn = EFFECTS[state["key"]]
        curve.set_data(X, [fn(float(v)) for v in X])
        ax_eff.set_title("effect %s: %s   (keys 1-7, z)" % (state["key"], name))
    draw_curve()

    def update(_):
        t, x, F, i = src.read()
        a = math.radians(90 - x * RANGE_DEG)
        needle.set_data([0, 0.88 * math.cos(a)], [0, 0.88 * math.sin(a)])
        txt.set_text("x = %+.2f   (%.1f deg)" % (x, x * RANGE_DEG))
        for b, v in zip(bars, (F, i)):
            b.set_height(v)
        if src.key != state["key"]:
            state["key"] = src.key
            draw_curve()
        dot.set_data([x], [EFFECTS[state["key"]][1](x)])
        return needle, txt, *bars, curve, dot

    def on_key(ev):
        if ev.key and (ev.key in EFFECTS or ev.key == "z"):
            src.send(ev.key)
    fig.canvas.mpl_connect("key_press_event", on_key)
    fig.suptitle("haptic paddle live view   Shreeniket Bendre  HW18",
                 fontsize=11)
    plt.tight_layout(rect=[0, 0, 1, 0.94])

    if screenshot:
        for k in range(12):
            update(k); time.sleep(0.05)
        fig.savefig(screenshot, facecolor="white", bbox_inches="tight")
        print("saved", screenshot)
        return
    anim = FuncAnimation(fig, update, interval=33, cache_frame_data=False)
    plt.show()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", help="serial port, e.g. /dev/ttyACM0 or COM5")
    p.add_argument("--demo", action="store_true", help="run without hardware")
    p.add_argument("--screenshot", help="save one frame to this file and exit")
    a = p.parse_args()
    src = Live(a.port) if (a.port and not a.demo) else Demo()
    build(src, screenshot=a.screenshot)
