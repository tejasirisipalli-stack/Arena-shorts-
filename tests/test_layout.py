"""Layout, typography and geometry tests for the JANASEVA NEWS short.

These run against the text shaper and the map data, not the encoder, so they are
fast enough to run on every change.
"""
import json, os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import janaseva_short as J
import news_timeline as TL


class TestTimeline(unittest.TestCase):
    def test_schedule_is_exactly_sixty_seconds(self):
        self.assertEqual(sum(TL.SCHEDULE), TL.TOTAL_FRAMES)
        self.assertEqual(len(TL.SCHEDULE), len(TL.SCENES))

    def test_every_scene_has_narration_and_captions(self):
        self.assertEqual(len(TL.SCENES), len(TL.SUBS))
        self.assertEqual(len(TL.SCENES), len(TL.VO_IDS))
        self.assertEqual(len(TL.SCENES), len(TL.VO_SECONDS))
        for s in TL.SCENES:
            self.assertTrue(s['label'] and s['head'] and s['footnote'])

    def test_narration_timeline_files_exist(self):
        for vid in TL.VO_IDS:
            self.assertTrue(os.path.exists(f'assets/{vid}.mp3'), vid)

    def test_every_scene_has_a_little_slack(self):
        """Narration must fit its slot at the plan tempo, or the scene would clip."""
        for i, (sec, frames) in enumerate(zip(TL.VO_SECONDS, TL.SCHEDULE)):
            speech = sec / TL.TEMPO
            slot = frames / TL.FPS
            self.assertLess(speech, slot, f'scene {i + 1} narration overflows')
            self.assertGreater(slot - speech, 0.01, f'scene {i + 1} has no breathing room')

    def test_cues_stay_inside_their_scene(self):
        for i, rows in enumerate(TL.proportional_cues()):
            start = TL.scene_start(i)
            end = start + TL.SCHEDULE[i] / TL.FPS
            for _text, a, b, _hi in rows:
                # cue windows are rounded to milliseconds for the .srt sidecar
                self.assertGreaterEqual(a, start - 0.01)
                self.assertLessEqual(b, end + 0.01)


class TestTypography(unittest.TestCase):
    def test_telugu_shaping_produces_ink(self):
        for text in ('ఏపీకి 3 లక్షల ఇళ్లు!', '₹3,600 కోట్లు', 'బుర్రిపాలెం',
                     'శివరాజ్ సింగ్ చౌహాన్', 'జనసేవ న్యూస్',
                     'నిజమైన సమాచారం • ప్రజల కోసం వార్తలు'):
            img = J.textimg(text, 48, '#ffffff')
            self.assertGreater(img.width, 10, text)
            self.assertGreater(img.height, 10, text)

    def test_latin_and_the_rupee_sign_render(self):
        self.assertGreater(J.textimg('JANASEVA NEWS', 40).width, 10)
        self.assertGreater(J.textimg('₹14 కోట్లు', 40).width, 10)

    def test_headlines_fit_the_safe_width(self):
        for s in TL.SCENES:
            for text, _accent, size in s['head']:
                self.assertLessEqual(J.tw(text, size), 920, text)

    def test_subtitle_cues_fit_the_caption_plate(self):
        width = (J.SUB_BOX[2] - J.SUB_BOX[0]) - 96
        for rows in TL.SUBS:
            for text, *_ in rows:
                self.assertEqual(len(J.wrap2(text, 44, width)), 1,
                                 f'cue wraps to two lines: {text}')

    def test_headlines_are_short_enough_to_scan(self):
        for s in TL.SCENES:
            for text, _accent, _size in s['head']:
                self.assertLessEqual(len(text.split(' ')), 8, text)

    def test_captions_are_telugu_only(self):
        # "3D" is the technology's own name and stays in Latin in Telugu news copy.
        allow = {'3D'}
        for rows in TL.SUBS:
            for text, *_ in rows:
                stripped = text
                for token in allow:
                    stripped = stripped.replace(token, '')
                latin = [c for c in stripped if c.isascii() and c.isalpha()]
                self.assertEqual(latin, [], f'Latin letters in caption: {text}')

    def test_no_emoji_in_on_screen_copy(self):
        """Emoji fall outside the merged font and would render as blank boxes."""
        text = ' '.join([h[0] for s in TL.SCENES for h in s['head']] +
                        [s['chip'] for s in TL.SCENES] +
                        [s['footnote'] for s in TL.SCENES] + [TL.PAYOFF])
        for ch in text:
            self.assertLess(ord(ch), 0x1F000, f'emoji in on-screen copy: {ch!r}')


class TestMapGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = J.map_data()

    def test_rings_are_normalised(self):
        for dist in self.d['districts']:
            for x, y in dist['rings']:
                self.assertTrue(0 <= x <= 1 and 0 <= y <= 1, dist['name'])

    def test_all_andhra_pradesh_districts_present(self):
        names = [x['name'] for x in self.d['districts']]
        self.assertEqual(len(names), 13)
        for n in ('Guntur', 'Krishna', 'Visakhapatnam', 'Anantapur'):
            self.assertIn(n, names)

    def test_tenali_falls_inside_guntur(self):
        gun = next(x for x in self.d['districts'] if x['name'] == 'Guntur')
        self.assertTrue(J._inside(self.d['tenali'], gun['rings']))

    def test_pins_land_inside_the_state(self):
        rings = [x['rings'] for x in self.d['districts']]
        pins = J.pin_points(52)
        self.assertEqual(len(pins), 52)
        for p in pins:
            self.assertTrue(any(J._inside(p, r) for r in rings), p)

    def test_pins_are_deterministic(self):
        self.assertEqual(J.pin_points(52), J.pin_points(52))


class TestFrameAssembly(unittest.TestCase):
    def test_frames_are_full_resolution_and_never_black(self):
        import numpy as np
        for idx in (0, 3, 6):
            dur = TL.SCHEDULE[idx] / TL.FPS
            for t in (0.05, dur * 0.5, dur - 0.05):
                im = J.frame(idx, t, TL.scene_start(idx) + t, active_cue=None)
                self.assertEqual(im.size, (1080, 1920))
                a = np.asarray(im.convert('L'), dtype='float32')
                self.assertGreater(float(a.mean()), 12, f'scene {idx + 1} frame too dark')
                self.assertGreater(float(a.std()), 8, f'scene {idx + 1} frame is flat')

    def test_frame_renders_with_a_caption(self):
        text, _a, _b, hi = TL.proportional_cues()[6][1]
        im = J.frame(6, 2.0, TL.scene_start(6) + 2.0, active_cue=(text, hi))
        self.assertEqual(im.size, (1080, 1920))


if __name__ == '__main__':
    unittest.main()
