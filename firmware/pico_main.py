import time, math, sys
import board, busio, digitalio, supervisor

USE_LOADCELL   = True
LOOP_HZ        = 80
RANGE_DEG      = 40.0
FORCE_FS       = 120000
I_MAX_MA       = 800
KPF            = 0.6
KD             = 0.04
TELEM_DIV      = 2

def clip(f, lo=-1.0, hi=1.0):
    return lo if f < lo else hi if f > hi else f

def spring(x):  return clip(-1.0 * x)
def wall(x):
    if x >  0.6: return clip(-8.0 * (x - 0.6))
    if x < -0.6: return clip(-8.0 * (x + 0.6))
    return 0.0
def bump(x):    return clip( (x / 0.18) * math.exp(-(x * x) / (2 * 0.18 * 0.18)))
def dip(x):     return clip(-(x / 0.18) * math.exp(-(x * x) / (2 * 0.18 * 0.18)))
def toggle(x):  return clip(math.sin(math.pi * x))
def detents(x): return clip(-0.8 * math.sin(2.0 * math.pi * x / 0.25))
def texture(x): return clip(-0.25 * math.sin(2.0 * math.pi * x / 0.05))

EFFECTS = {"1": ("spring", spring), "2": ("wall", wall), "3": ("bump", bump),
           "4": ("dip", dip), "5": ("toggle", toggle), "6": ("detents", detents),
           "7": ("texture", texture)}
effect_key = "6"

class AS5600:
    ADDR = 0x36
    REG_RAW_ANGLE = 0x0C

    def __init__(self, i2c):
        self.i2c = i2c
        self.buf = bytearray(2)
        self.prev = self._raw()
        self.turns = 0
        self.zero = 0.0
        self.zero_here()

    def _raw(self):
        while not self.i2c.try_lock():
            pass
        try:
            self.i2c.writeto_then_readfrom(self.ADDR,
                                           bytes([self.REG_RAW_ANGLE]), self.buf)
        finally:
            self.i2c.unlock()
        return ((self.buf[0] << 8) | self.buf[1]) & 0x0FFF

    def counts(self):
        r = self._raw()
        d = r - self.prev
        if d > 2048:   self.turns -= 1
        elif d < -2048: self.turns += 1
        self.prev = r
        return self.turns * 4096 + r

    def zero_here(self):
        self.zero = self.counts()

    def angle_deg(self):
        return (self.counts() - self.zero) * 360.0 / 4096.0

class HX711:
    def __init__(self, dt_pin, sck_pin):
        self.dt = digitalio.DigitalInOut(dt_pin)
        self.dt.direction = digitalio.Direction.INPUT
        self.sck = digitalio.DigitalInOut(sck_pin)
        self.sck.direction = digitalio.Direction.OUTPUT
        self.sck.value = False
        self.offset = 0
        time.sleep(0.5)
        self.tare()

    def ready(self):
        return not self.dt.value

    def read(self):
        while not self.ready():
            pass
        v = 0
        for _ in range(24):
            self.sck.value = True
            v = (v << 1) | (1 if self.dt.value else 0)
            self.sck.value = False
        self.sck.value = True
        self.sck.value = False
        if v & 0x800000:
            v -= 0x1000000
        return v

    def tare(self, n=16):
        s = 0
        for _ in range(n):
            s += self.read()
        self.offset = s // n

    def force_norm(self):
        return clip((self.read() - self.offset) / FORCE_FS)

i2c = busio.I2C(scl=board.GP5, sda=board.GP4, frequency=400_000)
enc = AS5600(i2c)
cell = HX711(board.GP2, board.GP3) if USE_LOADCELL else None
uart = busio.UART(tx=board.GP0, rx=board.GP1, baudrate=115200, timeout=0)

print("# haptic paddle up. keys: 1-7 select effect, z = re-zero angle")
x_prev = 0.0
v_filt = 0.0
t0 = time.monotonic()
t_prev = t0
n = 0
period = 1.0 / LOOP_HZ

while True:
    if USE_LOADCELL:
        F_meas = cell.force_norm()
    else:
        while time.monotonic() - t_prev < period:
            pass
        F_meas = 0.0

    t = time.monotonic()
    dt = t - t_prev
    t_prev = t

    x = clip(enc.angle_deg() / RANGE_DEG)
    if dt > 0:
        v_raw = (x - x_prev) / dt
        v_filt += 0.25 * (v_raw - v_filt)
    x_prev = x

    name, fn = EFFECTS[effect_key]
    F_des = fn(x)
    i_norm = clip(F_des + KPF * (F_des - F_meas) - KD * v_filt)
    i_mA = int(i_norm * I_MAX_MA)

    uart.write(("C%d\n" % i_mA).encode())

    n += 1
    if n % TELEM_DIV == 0:
        print("T,%.3f,%.3f,%.3f,%.3f" % (t - t0, x, F_meas, i_norm))
    while supervisor.runtime.serial_bytes_available:
        c = sys.stdin.read(1)
        if c in EFFECTS:
            effect_key = c
            print("# effect -> " + EFFECTS[c][0])
        elif c == "z":
            enc.zero_here()
            print("# angle re-zeroed")
