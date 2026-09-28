# Janaseva News — Telugu YouTube Short

Deliverable: `output/vsp_gvmc_news_telugu_short.mp4` (55 seconds, 1080×1920, 24 fps, H.264/AAC, 48 kHz audio).

Also included: thumbnail, six-scene layout preview, and Telugu YouTube metadata with sources and the keyword `vsp gvmc news`.

## Modern newsroom redesign

- AI-generated virtual broadcast studio with cyan/red lighting, reflective stage, and animated camera push.
- Extruded, beveled metallic Telugu headlines with staggered kinetic entrances.
- Animated holographic rings, perspective floor, light particles, and diagonal transition wipes.
- Three-dimensional ward tiles with a count-up, floating document/calendar panels, and animated lower thirds.
- Photo-based city motion inserts, explicitly labelled as a city photograph. These are not filmed live-action video.

The supplied six passages retain the selected synthetic female Telugu voice. Scene timing remains 9 / 8 / 7 / 11 / 8 / 12 seconds. Graphics are illustrative, not footage of an actual GVMC office or political meeting. Text uses HarfBuzz shaping for Telugu conjuncts. Political goals remain labelled as claims rather than outcomes.

## Rebuild

Install Python packages `pillow imageio-ffmpeg uharfbuzz freetype-py`; DejaVu Sans Bold must be available in `/usr/share/fonts/truetype/dejavu/`.

Run `python make_video.py` from this directory. `newsroom_layout.py` provides the compositor; `make_video.py` shapes text, retimes narration, and encodes the video. Selected narration, merged Telugu/Latin Noto font and its license, city photograph, and generated studio background are included. Intermediate retimed audio is ignored by Git.

Run `python -m unittest discover -s tests` for frame/text smoke tests. The final export was also fully decoded with FFmpeg to check for audio/video errors.

Review current election announcements and the photo source/licensing before publishing. See `output/youtube_metadata_te.md` for source links and editorial notes.
