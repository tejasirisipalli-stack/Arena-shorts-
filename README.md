# JANASEVA NEWS — Telugu YouTube Shorts pipeline

**Current deliverable:** `output/ap_3lakh_houses_telugu_short.mp4`
60.00 s • 1080×1920 (9:16) • 30 fps • H.264 High + AAC 48 kHz • Telugu female narration,
Telugu on-screen copy and Telugu subtitles • faceless, no presenter.

The bulletin reports the PMAY-Gramin housing announcement for Andhra Pradesh: 3 lakh
houses sanctioned (~₹3,600 crore) at a function in Burripalem, Tenali constituency,
Guntur district, attended by Union Minister Shivraj Singh Chouhan and Chief Minister
Nara Chandrababu Naidu; the rise from the ~76,000 originally indicated; the 177-house
3D concrete printing pilot (~₹14 crore, ~6-month target); and the *possible* further
3 lakh in a later phase.

Facts are limited to the verified brief. **The video never says 9 lakh houses are already
sanctioned**, and `qa_check.py` fails the build if such a claim is introduced. The current
3 lakh sanction and any future allocation are drawn in visibly different styles
(solid + tick vs dashed + clock) and are never summed on screen.

## Repository layout

| File | Purpose |
| --- | --- |
| `news_timeline.py` | Single source of truth: scene order, durations, headlines, narration text, subtitle cues, highlighted figures. |
| `janaseva_short.py` | The compositor. Shaping (HarfBuzz + FreeType), kinetic typography, map renderer, subtitles, frame assembly. |
| `make_video.py` | Retimes the narration, snaps subtitle cues to real pauses, mixes the audio, renders 1800 frames and encodes the MP4. |
| `make_music.py` | Synthesises the news music bed and all SFX with numpy — no third-party audio. |
| `make_subtitles.py` | Writes the Telugu `.srt` / `.vtt` sidecars from the same cue timeline. |
| `build_map_assets.py` | Downloads and normalises the Andhra Pradesh district geometry into `assets/map/ap_outline.json`. |
| `qa_check.py` | Fact and format QA on the rendered file. |
| `legacy_vsp_short.py`, `newsroom_layout.py` | The earlier Visakhapatnam/GVMC short, kept for reference. Not used by the current render. |

## Rebuild

```bash
pip install pillow imageio-ffmpeg uharfbuzz freetype-py numpy
python3 build_map_assets.py      # only needed if assets/map/ap_outline.json is missing
python3 make_music.py            # writes build/music.wav and build/sfx.wav
python3 make_video.py            # writes output/ap_3lakh_houses_telugu_short.mp4 (~6 min)
python3 make_subtitles.py        # writes the .srt / .vtt sidecars
python3 qa_check.py              # fact and format checks on the finished file
```

`assets/vo1..vo8.mp3` are the per-scene narration recordings. `news_timeline.VO_SECONDS`
records their durations and `make_video.py` asserts the files still match, so the scene
plan cannot silently drift from the audio. `.gitignore` keeps the intermediate
`build/*.wav` retimes out of Git.

## How the timeline works

`news_timeline.SCHEDULE` holds the frame count of each chapter; it sums to exactly 1800
frames (60.000 s at 30 fps). Every chapter's narration recording is compressed by
`TL.TEMPO` and padded into its own slot, so scene changes land on the plan and no word is
clipped. Subtitle cues are **not** placed on a proportional estimate: `make_video.py`
reads the retimed narration back, finds the real pauses, and nudges each cue boundary onto
the nearest one.

## Visual and editorial rules

* **No AI-generated politicians.** The event scene is a generic function-venue
  illustration with the two leaders introduced in typography only. Every photograph in the
  video is an AI-made illustration and is labelled on screen as `ఏఐతో రూపొందించిన దృశ్యం`.
  No real event footage exists in the video, so nothing can be mistaken for it.
* **Telugu integrity.** All text is shaped a whole word at a time through HarfBuzz, so
  conjuncts and vowel signs cannot be broken or distorted. Emoji are avoided entirely;
  the house and check marks are vector drawings, so no glyph can fall back to a blank box.
* **Safe area.** Content stays inside y = 88…1600 for Shorts UI; `qa_check.py` and the
  layout constants in `janaseva_short.py` keep it there.
* **Audio priority.** The music bed is ducked under the voice with a 10 ms envelope
  follower, so narration is always clearly on top.

## Credits and licensing

* **Font** — `assets/Merged.ttf` is a merged Noto Telugu/Latin face, SIL Open Font
  License 1.1 (`assets/FONT-LICENSE.txt`).
* **Map geometry** — district boundaries from the open
  [`ishawakankar/India_Districts`](https://github.com/ishawakankar/India_Districts)
  dataset, simplified and projected by `build_map_assets.py` into a state outline and
  district rings. Administrative boundaries are factual data, and the map is drawn as a
  current affairs graphic with no claim of official endorsement. **This repository carries
  no explicit licence** — for a commercial release, swap in boundaries from an
  explicitly-licensed source (e.g. an open government boundary set) and re-run
  `build_map_assets.py`.
* **Photography** — every image in `assets/ap_housing/` was generated for this project.
  They are illustrations, not records of the Burripalem event.
* **Audio** — narration is synthesised from the scripts in `news_timeline.VO_TEXT`;
  music and SFX are generated by `make_music.py`. No third-party music or SFX.
* **No government or political-party logos** are reproduced anywhere in the video or the
  thumbnail, and no official document or quotation is depicted.
