"""Synthesises the news music bed and the broadcast SFX for the 60-second short.

Everything here is generated from scratch with numpy, so the finished video ships
with no third-party audio rights attached. Output:

    build/music.wav   low-volume modern news bed, exactly 60 s
    build/sfx.wav     whooshes, number impacts, map sweeps and stingers

Both are mixed under the narration by make_video.py (sidechain ducking, so the
voice always wins).
"""
import math, os, wave
import numpy as np

import news_timeline as TL

SR = 48000
DUR = TL.TOTAL_FRAMES / TL.FPS          # 60.0 s


# --- primitives --------------------------------------------------------------
def bandpass(x, lo, hi, soft=0.25):
    """Zero-phase band-pass by shaping the spectrum. `soft` widens the skirts."""
    n = len(x)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    lo_w = max(lo * soft, 1.0)
    hi_w = max(hi * soft, 1.0)
    gain = np.ones_like(freqs)
    gain *= 1 / (1 + (lo_w / np.maximum(freqs, 1e-6)) ** 2) ** 0.5      # high-pass
    gain *= 1 / (1 + (freqs / max(hi_w, 1.0)) ** 2) ** 0.5              # low-pass
    return np.fft.irfft(spec * gain, n=n)


def add_at(dst, src, at):
    """Mix src into dst at sample offset `at`, clipping to the buffer."""
    i = int(round(at * SR))
    if i >= len(dst):
        return
    if i < 0:
        src = src[-i:]
        i = 0
    n = min(len(src), len(dst) - i)
    dst[i:i + n] += src[:n]


def env_ad(n, attack, decay, curve=3.0):
    """Attack/decay amplitude envelope, both times in seconds."""
    a = max(1, int(attack * SR))
    d = max(1, n - a)
    out = np.empty(n)
    out[:a] = np.linspace(0, 1, a, endpoint=False) ** 0.6
    out[a:] = np.exp(-np.linspace(0, curve, d))
    return out


def sine(freq, n, phase=0.0):
    t = np.arange(n) / SR
    return np.sin(2 * math.pi * freq * t + phase)


def sweep_tone(f0, f1, n):
    """Exponential frequency sweep with a continuous phase."""
    t = np.arange(n) / SR
    T = n / SR
    if abs(f1 - f0) < 1e-6:
        return np.sin(2 * math.pi * f0 * t)
    k = math.log(f1 / f0) / T
    return np.sin(2 * math.pi * f0 * (np.exp(k * t) - 1) / k)


def soft_clip(x, drive=1.0):
    return np.tanh(x * drive)


# --- whoosh: overlap-add swept band of noise ---------------------------------
def whoosh(dur, f_lo, f_hi, seed=0, airy=0.9, tone=0.25):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    # Amplitude envelope: quick swell, longer tail.
    t = np.linspace(0, 1, n)
    amp = np.sin(math.pi * np.clip(t, 0, 1)) ** 1.6

    seg = 32
    edges = np.linspace(0, n, seg + 1).astype(int)
    win = np.hanning(max(2, edges[1] - edges[0] + 1))[:edges[1] - edges[0]]
    out = np.zeros(n)
    wsum = np.zeros(n) + 1e-9
    for k in range(seg):
        i0, i1 = edges[k], edges[k + 1]
        cut = f_lo + (f_hi - f_lo) * (k / (seg - 1))
        chunk = bandpass(noise[i0:i1], cut * 0.55, cut * 1.9, soft=0.45)
        if len(chunk) != len(win):
            w = np.hanning(len(chunk))
        else:
            w = win
        out[i0:i1] += chunk * w
        wsum[i0:i1] += w
    out = out / wsum

    # A faint swept sine underneath gives the whoosh a tonal centre.
    out = out * airy + sweep_tone(max(60.0, f_lo * 0.30), max(90.0, f_hi * 0.22), n) * tone
    out *= amp
    peak = np.max(np.abs(out)) or 1.0
    return out / peak


def impact(seed=1, low=58.0, drop=0.55):
    rng = np.random.default_rng(seed)
    n = int(0.85 * SR)
    body = sweep_tone(low, low * drop, n) * env_ad(n, 0.004, 0.85, curve=4.4)
    crack = bandpass(rng.standard_normal(int(0.09 * SR)), 900, 6000)
    crack = np.pad(crack, (0, n - len(crack))) * env_ad(n, 0.001, 0.09, curve=5.0)
    out = body * 1.0 + crack * 0.32
    return out / (np.max(np.abs(out)) or 1.0)


def bell(freq=1046.5, dur=1.1, seed=2):
    n = int(dur * SR)
    out = np.zeros(n)
    for k, (mult, gain, decay) in enumerate([(1.0, 1.0, 3.4), (2.02, 0.42, 4.6),
                                              (3.01, 0.20, 6.0), (4.98, 0.09, 7.5)]):
        out += sine(freq * mult, n) * gain * np.exp(-np.linspace(0, decay, n))
    return out / (np.max(np.abs(out)) or 1.0)


def stinger(seed=3, dur=1.9):
    """Soft major-ish news stinger with a fast rise."""
    n = int(dur * SR)
    out = np.zeros(n)
    for f, g, dec in [(220.0, 1.0, 2.6), (329.63, 0.8, 2.9), (440.0, 0.6, 3.2),
                      (554.37, 0.35, 3.6), (659.25, 0.22, 4.0)]:
        out += sine(f, n) * g * np.exp(-np.linspace(0, dec, n))
    sub = sine(110.0, n) * np.exp(-np.linspace(0, 2.2, n))
    out = out * 0.75 + sub * 0.5
    out *= np.clip(np.linspace(0, 4, n), 0, 1) ** 0.5
    return out / (np.max(np.abs(out)) or 1.0)


def click(seed=4):
    rng = np.random.default_rng(seed)
    n = int(0.035 * SR)
    out = bandpass(rng.standard_normal(n), 1800, 9000, soft=0.4)
    out *= env_ad(n, 0.0008, 0.035, curve=4.0)
    return out / (np.max(np.abs(out)) or 1.0)


def riser(dur=1.6, f0=180, f1=1500, seed=5):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    noise = bandpass(rng.standard_normal(n), 300, 7000, soft=0.5)
    noise *= np.linspace(0, 1, n) ** 2.2
    tone = sweep_tone(f0, f1, n) * np.linspace(0, 1, n) ** 2.4 * 0.35
    out = noise * 0.7 + tone
    return out / (np.max(np.abs(out)) or 1.0)


# --- music bed ---------------------------------------------------------------
BEAT = 0.6                                  # 100 BPM
BAR = BEAT * 4
CHORDS = [                                  # A minor - F - C - G
    (110.00, [220.00, 261.63, 329.63]),
    (87.31, [174.61, 220.00, 261.63]),
    (130.81, [261.63, 329.63, 392.00]),
    (98.00, [196.00, 246.94, 293.66]),
]


def pad_chord(freqs, dur, seed):
    """Soft detuned pad with a slow attack, band-limited to stay out of the way."""
    n = int(dur * SR)
    out = np.zeros(n)
    for i, f in enumerate(freqs):
        for det, g in ((-0.6, 0.55), (0.0, 1.0), (0.7, 0.5)):
            out += sine(f + det, n, phase=i + det) * g
        out += sine(f * 2, n, phase=i * 0.7) * 0.16      # gentle octave shimmer
        out += sine(f * 0.5, n, phase=i * 1.3) * 0.30    # body
    atk = int(dur * 0.22 * SR)
    rel = int(dur * 0.30 * SR)
    env = np.ones(n)
    env[:atk] = np.linspace(0, 1, atk) ** 1.5
    env[n - rel:] = np.linspace(1, 0, rel) ** 1.5
    out *= env
    return out / (np.max(np.abs(out)) or 1.0)


def make_music():
    total = int(DUR * SR)
    music = np.zeros(total)

    # Chord bed: one bar per chord, cycling through the progression.
    nb = int(math.ceil(DUR / BAR))
    for b in range(nb):
        root, triad = CHORDS[b % 4]
        at = b * BAR
        chunk = pad_chord(triad, BAR * 1.18, seed=b)          # overlap into next bar
        chunk = bandpass(chunk, 120, 2600, soft=0.5)
        add_at(music, chunk * 0.30, at)
        add_at(music, sine(root * 0.5, int(BAR * 1.3 * SR)) *
               env_ad(int(BAR * 1.3 * SR), 0.25, BAR * 1.3, curve=1.1) * 0.22, at)

    # Slow sub drone holding the whole bed together.
    n = total
    t = np.arange(n) / SR
    drone = (sine(55.0, n) * 0.55 + sine(82.5, n) * 0.22 + sine(110.0, n) * 0.12)
    drone *= 0.75 + 0.25 * np.sin(2 * math.pi * 0.035 * t)
    music += bandpass(drone, 30, 300, soft=0.5) * 0.20

    # Rhythm: soft kick on 1 and 3, rim on 2 and 4, hats on every eighth.
    kick = impact(seed=11, low=62.0, drop=0.48)
    rim = bandpass(np.random.default_rng(12).standard_normal(int(0.05 * SR)), 1200, 5200)
    rim *= env_ad(len(rim), 0.001, 0.05, curve=4.5)
    hat = bandpass(np.random.default_rng(13).standard_normal(int(0.045 * SR)), 5000, 11000)
    hat *= env_ad(len(hat), 0.0006, 0.045, curve=5.5)

    beat_i = 0
    while beat_i * BEAT < DUR:
        at = beat_i * BEAT
        in_bar = beat_i % 4
        if in_bar in (0, 2):
            add_at(music, kick * 0.55, at)
        if in_bar in (1, 3):
            add_at(music, rim * 0.13, at)
        add_at(music, hat * (0.055 if in_bar % 2 == 0 else 0.034), at)
        add_at(music, hat * 0.022, at + BEAT / 2)            # offbeat hat
        beat_i += 1

    # Sparse pluck arpeggio, deliberately quiet and slightly off the grid.
    pluck_notes = []
    for b in range(nb):
        _, triad = CHORDS[b % 4]
        for k, step in enumerate((0.0, 0.75, 1.5, 2.25, 3.0)):
            pluck_notes.append((b * BAR + step * BEAT, triad[(k + b) % 3] * 2))
    for at, f in pluck_notes:
        if at >= DUR:
            continue
        nd = int(0.42 * SR)
        pl = sine(f, nd) * env_ad(nd, 0.003, 0.42, curve=6.5)
        pl += sine(f * 2, nd) * env_ad(nd, 0.003, 0.42, curve=8.0) * 0.22
        add_at(music, pl * 0.055, at)

    # Structure: quiet under the hook, open up after the location scene, and
    # lift again into the 3D printing reveal.
    t = np.arange(total) / SR
    def ramp(a, b, lo, hi):
        return np.clip((t - a) / max(b - a, 1e-6), 0, 1) * (hi - lo) + lo
    gain = np.full(total, 0.62)
    gain *= np.where(t < 6.0, ramp(0.0, 2.0, 0.55, 1.0), 1.0)
    gain *= np.where((t >= 19.0) & (t < 30.3), ramp(19.0, 21.5, 1.0, 1.06), 1.0)
    gain *= np.where((t >= 30.3) & (t < 45.9), ramp(30.3, 32.5, 1.06, 1.16), 1.0)
    gain *= np.where(t >= 53.6, ramp(53.6, 55.0, 1.0, 0.8), 1.0)
    music *= gain

    # Clean fade in/out so the bed never starts or ends abruptly.
    fade = int(0.35 * SR)
    music[:fade] *= np.linspace(0, 1, fade)
    music[-int(1.2 * SR):] *= np.linspace(1, 0, int(1.2 * SR))
    return music / (np.max(np.abs(music)) or 1.0)


def make_sfx():
    sfx = np.zeros(int(DUR * SR) + SR)          # a little tail past the end

    def start(i):
        return sum(TL.SCHEDULE[:i]) / TL.FPS

    # Transition whooshes at every scene boundary (scene 1 gets the intro hit).
    for i in range(len(TL.SCHEDULE)):
        at = start(i)
        if i == 0:
            add_at(sfx, whoosh(0.75, 700, 5200, seed=20), 0.02)
            add_at(sfx, stinger(seed=21) * 0.85, 0.0)
            continue
        up = i % 2 == 0
        w = whoosh(0.55, 500, 4800, seed=20 + i) if up else whoosh(0.55, 4400, 620, seed=20 + i)
        add_at(sfx, w * 0.5, at - 0.22)
        if i == 1:                                    # map sweep into the location scene
            add_at(sfx, riser(1.1, 220, 2200, seed=31) * 0.30, at - 0.9)
            add_at(sfx, bell(783.99, 1.0) * 0.24, at + 0.05)
        if i == 4:                                    # 3D printing reveal
            add_at(sfx, bell(1174.66, 1.2) * 0.30, at + 0.05)
        if i == 7:                                    # CTA
            add_at(sfx, stinger(seed=41) * 0.7, at)
            add_at(sfx, bell(1318.51, 1.1) * 0.2, at + 0.12)

    # Number landings: the hook total, the 3 lakh counter, the 177/14 crore card
    # and the future-allocation comparison.
    for at, kind in [(2.55, 'imp'), (2.95, 'bell'), (26.10, 'imp'), (26.45, 'bell'),
                     (30.35, 'imp'), (34.55, 'bell'), (48.85, 'imp'), (49.2, 'bell')]:
        if kind == 'imp':
            add_at(sfx, impact(seed=50 + int(at)) * 0.55, at)
        else:
            add_at(sfx, bell(1046.5, 0.9) * 0.22, at)

    # Light counting ticks while the counters climb.
    for at in np.arange(0.9, 2.55, 0.085):
        add_at(sfx, click(seed=int(at * 100)) * 0.10, at)
    for at in np.arange(20.6, 26.10, 0.085):
        add_at(sfx, click(seed=int(at * 100)) * 0.13, at)

    return sfx / (np.max(np.abs(sfx)) or 1.0)


def write_wav(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = soft_clip(data, 1.0)
    pcm = (np.clip(data, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f'wrote {path} ({len(pcm) / SR:.2f} s)')


if __name__ == '__main__':
    write_wav('build/music.wav', make_music())
    write_wav('build/sfx.wav', make_sfx())
