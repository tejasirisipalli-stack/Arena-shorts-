"""Writes the Telugu subtitle sidecar for the finished short.

The cue windows come from exactly the same pause-snapped timeline the renderer
uses, so the .srt matches the burned-in captions and the narration. The .vtt is
the same track with the highlight styling dropped.
"""
import os, sys

import numpy as np

import make_video as MV
import news_timeline as TL


def srt_time(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def vtt_time(sec):
    return srt_time(sec).replace(',', '.')


def build_cues():
    raw = np.concatenate([MV.wav_read(f'build/retimed{i}.wav')[0]
                          for i in range(len(TL.SCHEDULE))])
    return MV.snap_cues(raw)


def main():
    cues = build_cues()
    os.makedirs('output', exist_ok=True)
    n = 0
    with open('output/ap_3lakh_houses_telugu_short.srt', 'w') as f:
        for rows in cues:
            for text, a, b, _hi in rows:
                n += 1
                f.write(f'{n}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n\n')
    with open('output/ap_3lakh_houses_telugu_short.vtt', 'w') as f:
        f.write('WEBVTT\n\n')
        for i, rows in enumerate(cues):
            for text, a, b, _hi in rows:
                f.write(f'{vtt_time(a)} --> {vtt_time(b)}\n{text}\n\n')
    print(f'wrote {n} Telugu subtitle cues')
    for i, rows in enumerate(cues):
        print(f'  scene {i + 1}: ' + ' | '.join(f'{a:.2f} {t[:20]}' for t, a, b, _ in rows))


if __name__ == '__main__':
    main()
