"""Builds the Venus day-vs-year Telugu short (1080x1920, 24 fps).

Pipeline: per-scene Telugu narration -> single loudness-normalised track ->
speech envelope drives the presenter's lip motion -> venus_layout composites
animated space B-roll, oil-painting cards, kinetic Telugu typography and the
chroma-keyed presenter -> H.264/AAC MP4 in output/.
"""
import subprocess, wave, sys
import numpy as np
import imageio_ffmpeg
import venus_layout as VL

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = VL.W, VL.H, VL.FPS
LEAD, OFF, GAP, TAIL = 0.60, 0.12, 0.45, 1.30
AUDIO = [f'assets/audio/s{i}.wav' for i in range(1, 8)]
OUT = 'output/venus_day_year_telugu_short.mp4'

def sec_of(f):
    with wave.open(f) as w: return w.getnframes() / w.getframerate()

def timeline():
    durs, offs = [], []
    for i, f in enumerate(AUDIO):
        off = LEAD if i == 0 else OFF
        gap = TAIL if i == len(AUDIO) - 1 else GAP
        offs.append(off); durs.append(off + sec_of(f) + gap)
    starts, acc = [], 0.0
    for d in durs: starts.append(acc); acc += d
    return durs, starts, offs, acc

def build_narration(starts, offs, total):
    sr = 48000
    buf = np.zeros(int(total * sr) + sr, np.float32)
    for i, f in enumerate(AUDIO):
        with wave.open(f) as w:
            s = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        st = int((starts[i] + offs[i]) * sr)
        buf[st:st + len(s)] += s
    buf = np.tanh(buf * 1.1) * 0.9
    with wave.open('assets/audio/narration_raw.wav', 'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', 'assets/audio/narration_raw.wav',
                    '-af', 'loudnorm=I=-16:TP=-1.5:LRA=9', '-ar', '48000', '-ac', '1',
                    'assets/audio/narration_venus.wav'], check=True)

def envelope(path, nframes):
    """Per-frame speech amplitude for lip sync (fast attack, smooth release)."""
    with wave.open(path) as w:
        s = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    per = 48000 // FPS
    n = len(s) // per
    rms = np.sqrt((s[:n * per].reshape(n, per) ** 2).mean(axis=1) + 1e-9)
    rms = np.clip(rms / max(1e-6, np.percentile(rms, 92)), 0, 1.4)
    env = np.zeros(n); prev = 0.0
    for k in range(n):
        prev = rms[k] if rms[k] > prev else prev * 0.80 + 0.20 * rms[k]
        env[k] = prev
    env = np.clip((env - 0.10) / 0.72, 0, 1.15)
    if n < nframes: env = np.concatenate([env, np.zeros(nframes - n)])
    return env[:nframes]

PREVIEW = [(0, 1.2), (1, 2.0), (1, 4.4), (2, 1.2), (2, 4.2), (3, 3.4), (4, 3.0), (5, 1.6), (5, 3.8), (6, 2.0)]

def render(preview=False):
    durs, starts, offs, total = timeline()
    print('total seconds', round(total, 2), flush=True)
    if not preview:
        build_narration(starts, offs, total)
        nframes = int(total * FPS)
        env = envelope('assets/audio/narration_venus.wav', nframes)
    else:
        nframes = int(total * FPS)
        env = np.zeros(nframes)
        for i in range(7):  # fake speaking envelope so previews show open mouths
            a, b = int((starts[i] + offs[i]) * FPS), int((starts[i] + durs[i]) * FPS)
            env[a:b] = np.abs(np.sin(np.arange(b - a) * 0.9)) * 0.8
    VL.setup(durs, starts, env)
    cmd = [FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-vcodec', 'rawvideo',
           '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-i', 'assets/audio/narration_venus.wav',
           '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-ar', '48000', '-metadata:s:a:0', 'language=tel', '-b:a', '192k',
           '-movflags', '+faststart', OUT]
    p = None if preview else subprocess.Popen(cmd, stdin=subprocess.PIPE)
    g = 0
    for idx, d in enumerate(durs):
        print('Rendering scene', idx + 1, flush=True)
        for k in range(round(d * FPS)):
            t = k / FPS
            im = VL.frame(idx, t, starts[idx] + t, g)
            if preview and any(idx == a and abs(t - b) < 0.5 / FPS for a, b in PREVIEW):
                im.resize((540, 960)).save(f'output/preview_s{idx + 1}.jpg', quality=90)
            if not preview and idx == 1 and k == int(2.2 * FPS):
                im.resize((540, 960)).save('output/venus_thumbnail.jpg', quality=92)
            if not preview:
                p.stdin.write(im.tobytes())
            g += 1
    if preview:
        print('previews written'); return
    p.stdin.close()
    if p.wait(): raise RuntimeError('Encoding failed')
    print('Finished:', OUT)

if __name__ == '__main__':
    render(preview='--preview' in sys.argv)
