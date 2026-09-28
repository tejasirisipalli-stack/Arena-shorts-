import unittest
import uharfbuzz as hb
from PIL import ImageChops
import make_video as video
import newsroom_layout


class LayoutTests(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(sum(video.DURS), 55)

    def test_six_distinct_ai_scene_visuals(self):
        self.assertEqual(len(newsroom_layout.SCENE_IMAGES), 6)
        self.assertEqual(len({im.tobytes() for im in newsroom_layout.SCENE_IMAGES}), 6)
        self.assertTrue(video.textimg('ఏఐతో రూపొందించిన దృశ్యం', 16).getbbox())

    def test_headline_and_caption_glyphs(self):
        font = hb.Font(video.face)
        hb.ot_font_set_funcs(font)
        strings = video.LABEL + [s for group in video.HEADS + video.CAPS for s in group]
        for text in strings:
            with self.subTest(text=text):
                buffer = hb.Buffer()
                buffer.add_str(text)
                buffer.guess_segment_properties()
                hb.shape(font, buffer)
                self.assertTrue(all(info.codepoint != 0 for info in buffer.glyph_infos))

    def test_all_scene_frames(self):
        start = 0
        for i, duration in enumerate(video.DURS):
            for t in (0, 0.2, 2.5, duration - 1 / video.FPS):
                with self.subTest(scene=i, time=t):
                    frame = video.frame(i, t, start + t)
                    self.assertEqual(frame.size, (720, 1280))
                    self.assertEqual(frame.mode, 'RGB')
            start += duration

    def test_animation_changes_frames(self):
        for i in range(6):
            first = video.frame(i, 2, 2)
            second = video.frame(i, 3, 3)
            self.assertIsNotNone(ImageChops.difference(first, second).getbbox())


if __name__ == '__main__':
    unittest.main()
