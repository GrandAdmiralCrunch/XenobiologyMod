"""Xenobiology — synthesizes the Kerbin bird and mammal calls (22.05 kHz mono 16-bit WAVs) into Sounds/.
Usage:  python synth_calls.py <out_dir>
Every call is built from oscillators, noise and formant band-passes; nothing is sampled."""
import sys, os, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 22050
rng = np.random.default_rng(7)

def t_(dur): return np.arange(int(dur * SR)) / SR
def env(n, a=0.01, r=0.1, shape=1.0):
    e = np.ones(n); na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na) ** shape; e[-nr:] *= np.linspace(1, 0, nr) ** shape
    return e
def osc(freq, kind="sine"):
    """freq: array (Hz per sample)."""
    ph = 2 * np.pi * np.cumsum(freq) / SR
    if kind == "sine": return np.sin(ph)
    if kind == "saw": return 2 * ((ph / (2 * np.pi)) % 1.0) - 1
    if kind == "square": return np.sign(np.sin(ph))
    if kind == "brass": return sum(np.sin(ph * k) / k ** 0.8 for k in range(1, 9))
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)
def lp(x, f, order=2): return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)
def hp(x, f, order=2): return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)
def noise(n): return rng.standard_normal(n)
def place(total, parts):
    out = np.zeros(int(total * SR))
    for start, x in parts:
        i = int(start * SR); j = min(len(out), i + len(x)); out[i:j] += x[: j - i]
    return out
def save(path, x, peak=0.85):
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    fade = min(len(x) // 4, int(0.02 * SR)); x[-fade:] *= np.linspace(1, 0, fade)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype("<i2").tobytes())

def jay_note(dur=0.22, f0=2300):
    t = t_(dur); f = f0 * (1.08 - 0.25 * t / dur)
    x = osc(f, "saw") * (1 + 0.6 * np.sin(2 * np.pi * 70 * t)) + 0.5 * noise(len(t))
    return bp(x, 1400, 4200) * env(len(t), 0.01, 0.08)
def bluejeb(): return place(0.75, [(0.0, jay_note()), (0.3, jay_note(0.2, 2200))])

def hawk():
    t = t_(1.7); f = 3300 - 1200 * (t / 1.7) ** 0.7 + 60 * np.sin(2 * np.pi * 9 * t)
    x = osc(f, "saw") * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 38 * t))) + 0.8 * noise(len(t))
    return bp(x, 1500, 5000) * env(len(t), 0.06, 0.9, 1.5)

def hoot(dur, f0=360):
    t = t_(dur); f = f0 * (1 + 0.05 * np.sin(np.pi * t / dur))
    x = osc(f) + 0.15 * osc(2 * f) + 0.06 * lp(noise(len(t)), 900)
    return x * env(len(t), 0.06, dur * 0.5, 1.5)
def owl(): return place(2.6, [(0.0, hoot(0.55)), (0.75, hoot(0.18, 380)), (0.97, hoot(0.35)), (1.5, hoot(0.5, 345)), (2.05, hoot(0.45, 340))])

def quack(dur=0.24, f0=260):
    t = t_(dur); f = f0 * (1.15 - 0.3 * t / dur)
    x = osc(f, "saw") + 0.3 * noise(len(t))
    x = bp(x, 700, 1700) * 1.5 + bp(x, 2200, 3200) * 0.6
    return x * env(len(t), 0.015, 0.1)
def duck(): return place(1.25, [(0.0, quack(0.3)), (0.38, quack(0.22, 245)), (0.68, quack(0.2, 235)), (0.95, quack(0.18, 225))])

def honk(dur=0.5, f0=440):
    t = t_(dur); f = f0 * (1 + 0.03 * np.sin(2 * np.pi * 5 * t))
    x = osc(f, "brass") + 0.15 * noise(len(t))
    return (bp(x, 400, 2200) + 0.4 * bp(x, 2500, 3500)) * env(len(t), 0.04, 0.2)
def swan(): return place(1.4, [(0.0, honk(0.45)), (0.6, honk(0.6, 410))])

def pelican():                    # mostly silent birds: a low, breathy grunt
    t = t_(0.7); x = lp(noise(len(t)), 500) * (1 + 0.8 * np.sin(2 * np.pi * 28 * t)) + 0.3 * osc(np.full(len(t), 95.0), "saw")
    return lp(x, 700) * env(len(t), 0.05, 0.3)

def turkey():
    t = t_(1.3); f = 700 + 250 * np.sin(2 * np.pi * 2.2 * t) * np.exp(-t)
    gob = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 16 * t))       # rapid gobble flutter
    x = osc(f, "saw") * lp(gob, 60) + 0.25 * noise(len(t))
    return bp(x, 500, 2600) * env(len(t), 0.03, 0.4)

def bray(dur, f0):
    t = t_(dur); f = f0 * (1 + 0.15 * np.sin(np.pi * t / dur)) + 30 * np.sin(2 * np.pi * 22 * t)
    x = osc(f, "saw") + 0.4 * noise(len(t))
    return (bp(x, 500, 1500) + 0.5 * bp(x, 1800, 3000)) * env(len(t), 0.03, 0.08)
def penguin(): return place(1.9, [(0.0, bray(0.18, 520)), (0.22, bray(0.18, 560)), (0.45, bray(0.2, 600)), (0.72, bray(0.75, 480))])

def boom(dur=0.6, f0=95):
    t = t_(dur); f = f0 * (1 + 0.1 * np.sin(np.pi * t / dur))
    x = osc(f) + 0.3 * osc(2 * f) + 0.08 * lp(noise(len(t)), 300)
    return x * env(len(t), 0.12, 0.35, 1.5)
def ostrich(): return place(2.7, [(0.0, boom(0.5, 110)), (0.65, boom(0.5, 105)), (1.3, boom(1.2, 90))])

def capybara():                   # soft purring clicks and a little whistle
    t = t_(1.0); clicks = (np.sin(2 * np.pi * 24 * t) > 0.8).astype(float)
    x = bp(noise(len(t)) * lp(clicks, 200), 300, 1500) + 0.25 * osc(1300 + 200 * np.sin(2 * np.pi * 1.2 * t)) * (t > 0.7)
    return x * env(len(t), 0.02, 0.15)

def bison():
    t = t_(1.6); f = 72 + 10 * np.sin(np.pi * t / 1.6)
    x = osc(f, "saw") * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 11 * t))) + 0.4 * lp(noise(len(t)), 400)
    return lp(x, 650) * env(len(t), 0.15, 0.6, 1.3)

def bear():
    t = t_(1.7); f = 90 + 25 * np.sin(2 * np.pi * 0.7 * t) + 8 * noise(len(t))
    x = osc(f, "saw") * (0.5 + 0.5 * lp(np.abs(noise(len(t))), 40) * 3) + 0.7 * lp(noise(len(t)), 900)
    return (lp(x, 900) + 0.3 * bp(x, 900, 1800)) * env(len(t), 0.1, 0.5, 1.2)

def wolf():
    t = t_(3.6)
    f = np.interp(t, [0, 0.5, 1.4, 2.6, 3.6], [380, 690, 720, 600, 470]) * (1 + 0.012 * np.sin(2 * np.pi * 5.5 * t))
    x = osc(f) + 0.22 * osc(2 * f) + 0.06 * osc(3 * f) + 0.04 * bp(noise(len(t)), 500, 2000)
    return x * env(len(t), 0.35, 1.2, 1.4)

def horse():                      # whinny: a high, shaking neigh falling into a snort
    t = t_(1.6)
    f = np.interp(t, [0, 0.15, 0.9, 1.3, 1.6], [500, 1100, 750, 420, 300]) * (1 + 0.06 * np.sin(2 * np.pi * 28 * t))
    x = osc(f, "saw") + 0.3 * noise(len(t))
    x = (bp(x, 600, 2600) + 0.5 * bp(x, 2800, 4000)) * env(len(t), 0.04, 0.35)
    snort = lp(noise(int(0.3 * SR)), 900) * env(int(0.3 * SR), 0.01, 0.2)
    return place(2.1, [(0.0, x), (1.7, snort * 0.6)])

def beluga():                     # "canary of the sea": chirps, squeals and clicks
    parts = []; tt = 0.0
    for k in range(9):
        d = rng.uniform(0.08, 0.3); t = t_(d)
        f0, f1 = rng.uniform(1500, 3500), rng.uniform(1200, 5000)
        parts.append((tt, osc(np.linspace(f0, f1, len(t))) * env(len(t), 0.01, d * 0.4))); tt += d + rng.uniform(0.03, 0.15)
    for k in range(14):
        parts.append((tt + k * 0.03, bp(noise(int(0.008 * SR)), 2000, 6000)))
    return place(tt + 0.6, parts)

def anaconda():                   # long sandy hiss
    t = t_(1.8)
    x = hp(noise(len(t)), 2500) * (0.7 + 0.3 * np.sin(2 * np.pi * 3 * t))
    return bp(x, 2500, 8000) * env(len(t), 0.2, 0.6)

CALLS = dict(bluejeb_call=bluejeb, hawk_scream=hawk, owl_hoot=owl, duck_quack=duck, swan_honk=swan, pelican_grunt=pelican,
             turkey_gobble=turkey, penguin_bray=penguin, ostrich_boom=ostrich, capybara_purr=capybara, bison_grunt=bison,
             bear_growl=bear, wolf_howl=wolf, horse_whinny=horse, beluga_song=beluga, anaconda_hiss=anaconda)

# ---- the Emberwood birds
def ember_note(dur, f0, f1):
    t = t_(dur); f = np.linspace(f0, f1, len(t)) * (1 + 0.03 * np.sin(2 * np.pi * 38 * t))
    return (osc(f) + 0.25 * osc(f * 2)) * env(len(t), 0.005, dur * 0.4)
def emberwing():                   # a bright, rolling trill that drops at the end, then two clear notes
    parts = [(0.03 + k * 0.055, ember_note(0.045, 4200 - k * 60, 3700 - k * 60)) for k in range(12)]
    parts += [(0.8, ember_note(0.14, 3100, 3500)), (1.0, ember_note(0.18, 3400, 2600))]
    return place(1.3, parts)
def drum_beat(f0=55):
    t = t_(0.16); f = f0 * (1.3 - 0.3 * t / 0.16)
    return (osc(f) + 0.4 * lp(noise(len(t)), 300)) * env(len(t), 0.004, 0.13, 1.5)
def drummer():                     # slow wing-beats that speed up into a rolling drum
    times, t, gap = [], 0.0, 0.55
    while t < 3.2: times.append(t); t += gap; gap = max(0.07, gap * 0.8)
    return place(3.6, [(tt, drum_beat(55 + 5 * (i % 2))) for i, tt in enumerate(times)])
def gloamowl():                    # a soft, falling, tremulous trill
    t = t_(1.6); f = 620 * (1 - 0.32 * t / 1.6)
    am = 0.55 + 0.45 * np.sin(2 * np.pi * 15 * t)
    x = (osc(f) + 0.15 * osc(f * 2)) * am * env(len(t), 0.08, 0.5)
    return place(2.0, [(0.0, lp(x + 0.04 * noise(len(t)), 1800))])
def streamdart():                  # sharp, high piping peeps
    return place(0.9, [(k * 0.16, ember_note(0.07, 5200, 4700)) for k in range(5)])
CALLS.update(emberwing_trill=emberwing, drummer_drum=drummer, gloamowl_trill=gloamowl, streamdart_peep=streamdart)

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    only = sys.argv[2:]
    for name, fn in CALLS.items():
        if only and name not in only: continue
        save(os.path.join(out, name + ".wav"), fn()); print("wrote", name)
