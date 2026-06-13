import math

def clip(f, lo=-1.0, hi=1.0):
    return lo if f < lo else hi if f > hi else f

def spring(x, k=1.0):
    return clip(-k * x)

def wall(x, x_wall=0.6, k_wall=8.0):
    if x > x_wall:
        return clip(-k_wall * (x - x_wall))
    if x < -x_wall:
        return clip(-k_wall * (x + x_wall))
    return 0.0

def bump(x, A=1.0, sigma=0.18):
    return clip(A * (x / sigma) * math.exp(-(x * x) / (2 * sigma * sigma)))

def dip(x, A=1.0, sigma=0.18):
    return clip(-A * (x / sigma) * math.exp(-(x * x) / (2 * sigma * sigma)))

def toggle(x, A=1.0):
    return clip(A * math.sin(math.pi * x))

def detents(x, A=0.8, pitch=0.25):
    return clip(-A * math.sin(2.0 * math.pi * x / pitch))

def texture(x, A=0.25, pitch=0.05):
    return clip(-A * math.sin(2.0 * math.pi * x / pitch))

EFFECTS = {
    "1": ("spring",  spring),
    "2": ("wall",    wall),
    "3": ("bump",    bump),
    "4": ("dip",     dip),
    "5": ("toggle",  toggle),
    "6": ("detents", detents),
    "7": ("texture", texture),
}
