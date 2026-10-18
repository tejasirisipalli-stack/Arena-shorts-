"""Smoke tests for the Venus day-vs-year Telugu short (venus_layout.py)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import venus_layout as VL


class VenusShortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        VL.setup([3, 7, 7, 7, 6, 5, 5], [0, 3, 10, 17, 24, 30, 35], np.zeros(400))

    def test_telugu_shaping(self):
        im = VL.textimg('శుక్రగ్రహం', 48)
        self.assertGreater(im.width, 40)
        self.assertGreater(im.height, 20)

    def test_keyed_avatar_transparent_corners(self):
        a = np.asarray(VL.AVATARS[4]).astype(np.int16)[..., 3]
        self.assertLess(a[:40, :40].mean(), 20)
        h, w = a.shape
        self.assertGreater(a[h // 2:h // 2 + 200, w // 2 - 60:w // 2 + 60].mean(), 200)

    def test_frame_renders(self):
        im = VL.frame(0, 1.0, 1.0, 30)
        self.assertEqual(im.size, (VL.W, VL.H))
        self.assertEqual(im.mode, 'RGB')

    def test_keywords_fit_width(self):
        for sc in VL.SCENES:
            for text, _, _, _, size, _ in sc['kw']:
                for w in text.split(' '):
                    self.assertLessEqual(VL.textimg(w, size).width, VL.W - 120)

    def test_seven_scenes_seven_looks_moves(self):
        self.assertEqual(len(VL.SCENES), 7)
        cams = {sc['cam'][0] for sc in VL.SCENES}
        self.assertGreaterEqual(len(cams), 5)          # 3-6 camera angle families
        looks = [sc['look'] for sc in VL.SCENES]
        for a, b in zip(looks, looks[1:]):
            self.assertNotEqual(a, b)                  # dress changes every scene


if __name__ == '__main__':
    unittest.main()
