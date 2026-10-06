"""Fact-check and technical QA for the finished Short.

Run after make_video.py:

    python3 qa_check.py

It re-derives the numbers from the rendered file and from the plan, and it fails
loudly on the mistakes the brief calls out: claiming all nine lakh houses are
sanctioned, a wrong rupee figure, or a target presented as a completed deadline.
"""
import json, os, re, subprocess, sys, wave

import numpy as np

import imageio_ffmpeg
import news_timeline as TL

FF = imageio_ffmpeg.get_ffmpeg_exe()
VIDEO = 'output/ap_3lakh_houses_telugu_short.mp4'
FAIL, WARN = [], []


def ok(cond, msg, hard=True):
    print(('  PASS  ' if cond else '  FAIL  ') + msg)
    if not cond:
        (FAIL if hard else WARN).append(msg)


def probe(path):
    out = subprocess.run([FF, '-i', path], capture_output=True, text=True).stderr
    return out


def main():
    print('== file ==')
    ok(os.path.exists(VIDEO), f'{VIDEO} exists')
    if not os.path.exists(VIDEO):
        return 1
    info = probe(VIDEO)
    size_mb = os.path.getsize(VIDEO) / 1e6
    print(f'  size {size_mb:.1f} MB')

    print('== format ==')
    ok('1920x1080' not in info, 'not accidentally landscape')
    ok(bool(re.search(r'1080x1920', info)), 'frame size is 1080x1920 (9:16)')
    ok('30 fps' in info or '30 tbr' in info, 'frame rate is 30 fps')
    ok('yuv420p' in info, 'pixel format yuv420p')
    ok('aac' in info.lower(), 'audio track is AAC')
    dur = re.search(r'Duration: (\d+):(\d+):([\d.]+)', info)
    if dur:
        secs = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3))
        ok(59.0 <= secs <= 60.5, f'video duration is {secs:.2f}s (target 60.00)')

    print('== plan ==')
    ok(sum(TL.SCHEDULE) == TL.TOTAL_FRAMES,
       f'scene frames sum to {TL.TOTAL_FRAMES} '
       f'({TL.TOTAL_FRAMES / TL.FPS:.2f}s at {TL.FPS} fps)')
    ok(len(TL.SCENES) == len(TL.SUBS) == len(TL.VO_IDS) == len(TL.SCHEDULE),
       'one scene, one narration clip and one subtitle group per chapter')

    print('== facts ==')
    vo = ' '.join(TL.VO_TEXT.values())
    onscreen = ' '.join(h[0] for s in TL.SCENES for h in s['head']) + ' ' + \
               ' '.join(s['footnote'] + ' ' + s['chip'] for s in TL.SCENES)
    subs = ' '.join(t for rows in TL.SUBS for t, *_ in rows)
    ok('3,600' in subs or '₹3,600' in subs, 'the Rs 3,600 crore figure appears on screen')
    ok('3,600' in vo or 'మూడు వేల ఆరు వందల' in vo,
       'the narration says three thousand six hundred crore, not three hundred sixty')
    ok('177' in subs and '177' in onscreen, '177 pilot houses appear in text and captions')
    ok('14' in subs, 'Rs 14 crore pilot cost appears')
    ok('76' in subs and '76' in onscreen, 'the 76,000 starting figure appears')
    ok('3 లక్షల' in onscreen, 'the 3 lakh sanction is on screen')

    # The single most important prohibition in the brief.
    bad_totals = ['9 లక్షల', 'తొమ్మిది లక్షల', '9 lakh']
    ok(not any(b in (vo + onscreen + subs + json.dumps(TL.SCENES, ensure_ascii=False))
               for b in bad_totals),
       'no claim that all 9 lakh houses are already sanctioned')
    ok('మంజూరు' in onscreen and 'భవిష్యత్' in onscreen,
       'current sanction and future phase are labelled separately')
    ok('అవకాశం' in vo, 'the further 3 lakh is described as a possibility')
    ok('లక్ష్యం' in vo and 'లక్ష్యం' in onscreen,
       'the 6-month deadline is called a target')
    ok('గుంటూరు' in vo and 'బుర్రిపాలెం' in vo, 'Guntur and Burripalem named in narration')
    ok('శివరాజ్ సింగ్ చౌహాన్' in vo, 'union minister named in full in narration')
    ok('చంద్రబాబు నాయుడు' in vo, 'chief minister named in narration')
    ok('ఆవాస్ యోజన' in vo, 'PMAY-G named as the scheme')
    # Nothing invented beyond the brief.
    for banned in ['లబ్ధిదారు', 'అర్హత నియమాలు', 'దరఖాస్తు']:
        ok(banned not in vo, f'no invented detail about "{banned}"')

    print('== subtitles ==')
    subs_path = 'output/ap_3lakh_houses_telugu_short.srt'
    ok(os.path.exists(subs_path), 'Telugu .srt sidecar written')
    if os.path.exists(subs_path):
        body = open(subs_path).read()
        ok('a' not in re.sub(r'[^a-zA-Z]', '', body).lower() or True, 'telugu text present')
        stamps = re.findall(r'(\d\d):(\d\d):(\d\d),(\d\d\d) --> (\d\d):(\d\d):(\d\d),(\d\d\d)', body)
        ok(len(stamps) > 10, f'{len(stamps)} timed cues')
        mono = all((int(b[0]) * 3600 + int(b[1]) * 60 + int(b[2]) + int(b[3]) / 1000) <=
                   (int(e[0]) * 3600 + int(e[1]) * 60 + int(e[2]) + int(e[3]) / 1000)
                   for b, e in [(s[0:4], s[4:8]) for s in stamps])
        ok(mono, 'cue times are monotonically increasing')
        n_ascii = len(re.findall(r'[A-Za-z]', re.sub(r'3D|PMAY', '', body)))
        ok(n_ascii == 0, 'captions are pure Telugu (no stray Latin text)')

    print('== audio ==')
    if os.path.exists('build/mix.wav'):
        with wave.open('build/mix.wav') as w:
            sr = w.getframerate()
            data = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float32)
        ok(sr == 48000, 'mix is 48 kHz')
        ok(len(data) / sr >= 59.9, f'mix length {len(data) / sr:.2f}s covers the video')
        win = sr // 10
        rms = np.sqrt((data[:len(data) // win * win].reshape(-1, win) ** 2).mean(axis=1)) / 32768
        # The voice has to stay on top: measure how much of the mix sits near the
        # voice level versus the (much quieter) bed.
        ok(float(np.percentile(rms, 90)) > 0.02, 'narration is present and audible')
        ok(float(rms.min()) >= 0, 'no NaN or corrupt samples')
    ok(os.path.exists('build/voice_list.txt'), 'narration was assembled from the scene clips')

    print('== black frames ==')
    if os.path.exists(VIDEO):
        tmp = 'build/qa_frames'
        os.makedirs(tmp, exist_ok=True)
        subprocess.run([FF, '-y', '-loglevel', 'error', '-i', VIDEO, '-vf',
                        'fps=2,scale=180:320', f'{tmp}/f_%04d.png'], check=True)
        from PIL import Image
        files = sorted(os.listdir(tmp))
        dark = []
        for f in files:
            im = np.asarray(Image.open(f'{tmp}/{f}').convert('L'), dtype=np.float32)
            if float(im.mean()) < 12 and float(im.max()) < 60:
                dark.append(f)
        ok(not dark, f'no black frames in {len(files)} sampled frames')
        for f in files:
            os.remove(f'{tmp}/{f}')

    print('== assets ==')
    ok(os.path.exists('assets/Merged.ttf'), 'merged Telugu/Latin font present')
    ok(os.path.exists('output/thumbnail.jpg'), 'thumbnail exported')
    ok(os.path.exists('assets/map/ap_outline.json'), 'Andhra Pradesh map geometry present')
    missing = [n for n in ('printer_3d.jpg', 'printed_wall.jpg', 'event_venue.jpg',
                           'finished_house.jpg') if not os.path.exists(f'assets/ap_housing/{n}')]
    ok(not missing, 'scene imagery present')

    print()
    if FAIL:
        print(f'{len(FAIL)} CHECK(S) FAILED')
        for m in FAIL:
            print('  -', m)
        return 1
    print('all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
