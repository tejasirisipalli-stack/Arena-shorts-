# Janaseva News — Telugu YouTube Short

Main deliverable: `output/vsp_gvmc_news_telugu_short.mp4` — 55 seconds, 1080×1920 (9:16), 24 fps, H.264/AAC, 48 kHz audio. Telugu voice and on-screen copy are preserved. The six-scene story stays on the selected narration and timing.

## Visual redesign

- **Every scene now has its own photo-realistic AI-generated image**: a Visakhapatnam-inspired coastal view, a generic municipal campus, a fictional staff training workshop, an illustrative political coordination meeting with invented people, official-looking but blank desk paperwork, and a dusk coastal-city view.
- Each image is shown in a portrait media window, individually labelled in Telugu as AI-generated, and receives subtle animated camera pan/zoom plus studio light accents.
- Cyan/red virtual newsroom, kinetic extruded metallic Telugu headlines, holographic panels and ward tiles, animated checklists/calendar, transitions and an interactive-looking end-card CTA.
- Political meeting and civic scenes are **illustrations, not actual event footage**. People and buildings are generic, no real official or public figure is depicted, and the paperwork is not a real government notice. Election claims remain attributed and the notification/schedule caveat stays prominent.

The realistic images are generated stills—not recorded video. Camera movement and transitions animate the presentation without implying that the pictured events actually occurred. A photo of the city is not evidence of a specific GVMC activity. The image label and upload description disclose the AI illustrations.

See `output/youtube_metadata_te.md` for the Telugu title, description, exact keyword `vsp gvmc news`, source links and upload notes. `output/thumbnail.jpg` is the revised video thumbnail; `output/realistic-layout-review.jpg` is a six-scene design preview.

## Rebuild and test

Install Python packages `pillow imageio-ffmpeg uharfbuzz freetype-py`; DejaVu Sans Bold must be available in `/usr/share/fonts/truetype/dejavu/`.

Run `python make_video.py` from the repository root. `newsroom_layout.py` provides the compositor. `assets/realistic/scene1.jpg` through `scene6.jpg` are the generated visual assets; narration WAVs, the merged Telugu/Latin Noto font and its license are also included. Intermediate retimed audio is ignored by Git.

Run `python -m unittest discover -s tests` for frame and text-shaping smoke tests. The completed MP4 can be fully decoded with FFmpeg to validate the export.
