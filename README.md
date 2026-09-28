# Janaseva News — Telugu YouTube Short

Deliverable: `output/vsp_gvmc_news_telugu_short.mp4` (55 seconds, 1080×1920, 24 fps, H.264/AAC).

Also included: thumbnail and Telugu YouTube metadata with sources and the keyword `vsp gvmc news`.

The supplied six passages use the selected synthetic female Telugu voice. Scene timing is adjusted to 9 / 8 / 7 / 11 / 8 / 12 seconds to retain the complete narration at an intelligible pace. Visuals combine an actual coastline photograph with animated illustrative civic graphics, not actual meeting or GVMC office footage. Text is shaped with HarfBuzz for proper Telugu conjuncts.

## Rebuild

Install Python packages `pillow imageio-ffmpeg uharfbuzz freetype-py`; DejaVu Sans Bold must be available in `/usr/share/fonts/truetype/dejavu/`.

Run `python make_video.py` from this directory. The selected narration files, merged Telugu/Latin Noto font and its license, and coastline image are included. A complete FFmpeg decode of the export was tested successfully.

Review current election announcements and the photo source/licensing before publishing. See `output/youtube_metadata_te.md` for source links and editorial notes.
