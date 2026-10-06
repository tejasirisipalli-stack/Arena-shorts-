"""Renders the JANASEVA NEWS 60-second Telugu housing Short.

Pipeline
  1. Compress each narration clip by TL.TEMPO and pad/trim it into its scene slot,
     asserting the measured durations still match news_timeline.VO_SECONDS.
  2. Read the retimed narration back, detect the real pauses inside each scene, and
     snap the subtitle cues onto them, so captions follow the voice instead of an
     estimate.
  3. Normalise the voice, then mix the music bed and SFX under it with sidechain
     ducking.
  4. Render 1800 frames at 1080x1920 and encode H.264/AAC, 30 fps, 60.000 s.

Usage:  python3 make_video.py            # full render
        python3 make_video.py --sheet     # contact sheet only, no encode
"""
import math, os, subprocess, sys, wave

import numpy as np

import imageio_ffmpeg
from PIL import Image

import janaseva_short as J
import news_timeline as TL

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = J.W, J.H, J.FPS
SR = 48000
VIDEO = 'output/ap_3lakh_houses_telugu_short.mp4'


def run(args, **kw):
    return subprocess.run(args, check=True, capture_output=True, **kw)


def wav_read(path):
    with wave.open(path) as f:
        assert f.getsampwidth() == 2, path
        n = f.getnframes()
        data = np.frombuffer(f.readframes(n), dtype='<i2').astype(np.float32) / 32768.0
        if f.getnchannels() == 2:
            data = data.reshape(-1, 2).mean(axis=1)
        return data, f.getframerate()


def wav_write(path, data, sr=SR):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = (np.clip(data, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(pcm.tobytes())


# --- step 1: per-scene narration -------------------------------------------
def build_voice():
    """Compress each narration clip into its scene slot and pad to the frame.

    Returns the measured *source* duration of every clip so the caller can check
    news_timeline still describes the files on disk.
    """
    os.makedirs('build', exist_ok=True)
    sources = []
    for i, (vid, frames) in enumerate(zip(TL.VO_IDS, TL.SCHEDULE)):
        src = f'assets/{vid}.mp3'
        dry = f'build/src{i}.wav'
        run([FF, '-y', '-loglevel', 'error', '-i', src, '-ar', str(SR), '-ac', '1', dry])
        raw, _ = wav_read(dry)
        sources.append(len(raw) / SR)
        slot = frames / FPS
        speech = sources[-1] / TL.TEMPO
        if speech > slot - 0.025:
            raise SystemExit(f'{vid}: {speech:.3f}s of speech does not fit the '
                             f'{slot:.3f}s slot (raise TL.TEMPO)')
        # Compress to the plan, then pad with silence so the scene starts on its
        # own frame boundary and the last word is never clipped.
        run([FF, '-y', '-loglevel', 'error', '-i', dry, '-af',
             # Only a short fade-in: the clips already end on silence, and with
             # this little slack a fade-out would clip the final word.
             f'atempo={TL.TEMPO},apad,atrim=duration={slot},afade=t=in:d=0.02',
             '-ar', str(SR), '-ac', '1', f'build/retimed{i}.wav'])
    return sources


def snap_cues(voice, sr=SR):
    """Subtitle timing driven by the pauses actually present in the narration.

    Each cue gets a proportional slot; the slot boundaries are then nudged onto
    the nearest quiet sample inside a small search window, so a caption changes on
    a breath rather than halfway through a word.
    """
    total = voice.shape[0]
    win = int(0.02 * sr)
    n = total // win
    frames = voice[:n * win].reshape(n, win)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    quiet = rms < max(0.012, float(np.percentile(rms, 25)) * 0.45)

    # Candidate boundaries: the middle of every quiet stretch.
    bnd = []
    k = 0
    while k < n:
        if quiet[k]:
            j = k
            while j < n and quiet[j]:
                j += 1
            bnd.append(((k + j) / 2) * win / sr)      # seconds, not samples
            k = j
        else:
            k += 1

    out, start = [], 0
    for i, cues in enumerate(TL.SUBS):
        scene_frames = TL.SCHEDULE[i]
        t0, t1 = start / FPS, (start + scene_frames) / FPS
        weights = [c[1] for c in cues]
        tot = sum(weights)
        edges = []
        acc = 0.0
        for w in weights[:-1]:
            acc += w
            target = t0 + (t1 - t0) * acc / tot
            near = [b for b in bnd if abs(b - target) < 0.55 and t0 + .25 < b < t1 - .25]
            edges.append(min(near, key=lambda b: abs(b - target)) if near else target)
        bounds = [t0] + edges + [t1]
        rows = []
        for (text, _w, hi), a, b in zip(cues, bounds[:-1], bounds[1:]):
            rows.append((text, round(a, 3), round(b, 3), hi))
        out.append(rows)
        start += scene_frames
    return out


# --- step 3: audio mix ------------------------------------------------------
def mix_audio(cues):
    subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i',
                    'build/voice_list.txt', '-af',
                    'loudnorm=I=-15:TP=-1.5:LRA=9', '-ar', str(SR), '-ac', '1',
                    'build/voice_norm.wav'], check=True)
    voice, _ = wav_read('build/voice_norm.wav')
    need = int(round(TL.TOTAL_FRAMES / FPS * SR))
    voice = np.pad(voice, (0, max(0, need - voice.shape[0])))[:need]

    music, _ = wav_read('build/music.wav')
    sfx, _ = wav_read('build/sfx.wav')
    music = np.pad(music, (0, max(0, need - music.shape[0])))[:need]
    sfx = np.pad(sfx, (0, max(0, need - sfx.shape[0])))[:need]

    # Ducking envelope: follow the voice with a fast attack and a slow release.
    win = 480                                     # 10 ms
    n = need // win
    env = np.sqrt((voice[:n * win].reshape(n, win) ** 2).mean(axis=1) + 1e-12)
    env = np.convolve(env, np.ones(9) / 9, mode='same')
    env = np.interp(np.arange(need), np.arange(n) * win, env)
    duck = 1.0 - 0.62 * np.clip(env / 0.05, 0, 1) ** 0.6
    duck = np.convolve(duck, np.ones(2048) / 2048, mode='same')
    duck = np.clip(duck, 0.30, 1.0)

    mixed = voice * 1.0 + music * 0.34 * duck + sfx * 0.30 * duck
    peak = float(np.max(np.abs(mixed))) or 1.0
    mixed = mixed / peak * 0.92
    wav_write('build/mix.wav', mixed)
    return mixed


def voice_lists():
    with open('build/voice_list.txt', 'w') as f:
        for i in range(len(TL.SCHEDULE)):
            f.write(f"file 'retimed{i}.wav'\n")


def cue_at(rows, absolute):
    for text, a, b, hi in rows:
        if a <= absolute < b:
            return (text, hi)
    return None


# --- step 4: render ---------------------------------------------------------
def render(cues):
    os.makedirs('output', exist_ok=True)
    cmd = [FF, '-y', '-loglevel', 'error',
           '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-i', 'build/mix.wav',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
           '-profile:v', 'high', '-level', '4.1',
           '-c:a', 'aac', '-ar', '48000', '-b:a', '192k',
           '-metadata:s:a:0', 'language=tel',
           '-movflags', '+faststart', '-t', f'{TL.TOTAL_FRAMES / FPS:.3f}', VIDEO]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    absolute = 0.0
    for idx, frames in enumerate(TL.SCHEDULE):
        for k in range(frames):
            t = k / FPS
            cue = cue_at(cues[idx], absolute)
            im = J.frame(idx, t, absolute, active_cue=cue)
            proc.stdin.write(im.tobytes())
            if idx == 0 and k == 45:
                im.save('output/thumbnail.jpg', quality=94)
            absolute += 1 / FPS
        print(f'  scene {idx + 1}/{len(TL.SCHEDULE)} done ({absolute:.2f} s)', flush=True)
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError('ffmpeg encode failed')
    print('wrote', VIDEO)


def main():
    if '--sheet' in sys.argv:
        for i, sc in enumerate(TL.SCENES):
            J.frame(i, (TL.SCHEDULE[i] / FPS) * .6, TL.scene_start(i) + 1.0,
                    active_cue=None).save(f'/tmp/scene{i + 1}.png')
        print('sheet written to /tmp')
        return

    print('1/4 compressing narration ...')
    measured = build_voice()
    for vid, got, want in zip(TL.VO_IDS, measured, TL.VO_SECONDS):
        if abs(got - want) > 0.35:
            raise SystemExit(f'{vid}: narration file is {got:.2f}s, '
                             f'news_timeline says {want:.2f}s')
        print(f'   {vid}: {got:.2f}s source -> {got / TL.TEMPO:.2f}s in slot')
    voice_lists()
    print('2/4 snapping subtitle cues to narration pauses ...')
    raw = np.concatenate([wav_read(f'build/retimed{i}.wav')[0]
                          for i in range(len(TL.SCHEDULE))])
    cues = snap_cues(raw)
    for i, rows in enumerate(cues):
        print(f'   scene {i + 1}: ' +
              ' | '.join(f'{a:.2f}-{b:.2f} {t[:18]}' for t, a, b, _ in rows))
    print('3/4 mixing voice, music and SFX ...')
    mix_audio(cues)
    print('4/4 rendering frames ...')
    render(cues)


if __name__ == '__main__':
    main()
