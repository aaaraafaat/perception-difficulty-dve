# Work log

## 2026-06-28 — Setup and load RTTS
Copied the RTTS dataset (4322 images) from Google Drive to Colab local disk for
fast access, and made the feature functions in src/features.py importable.
The full eight-dataset inventory is deferred to its own step, done later when
needed; RTTS is the focus for the fog-feature stage.

## 2026-06-28 — Feature 1: dark-channel score (RTTS)
Computed dark-channel score for all 4322 RTTS images.
Saved: results/tables/features_RTTS.csv, results/figures/dark_channel_RTTS.png.
Score range: min 0.004, mean 0.452, max ~0.83; sane spread.

Visual check (six images, sorted low to high score): the cue does NOT cleanly
track fog. Lowest-scoring image is a hazy orange night scene (darkness keeps its
dark pixels low -> reads as clear). Mid-range ordering unreliable: a grey-sky
clear image scores high (bright sky lifts the score), and far-background fog with
a clear foreground gives mixed scores (whole-image averaging). Confirms one cue
conflates fog with night, bright sky, and haze location. Motivates additional
cues and fusion.

## 2026-06-28 — Feature 2: saturation (RTTS)
Added saturation_score to src/features.py, computed for all 4322 RTTS images.
Range: min 0.000, mean 0.115, max 0.961 (low-heavy with a tail, consistent with
haze draining colour across much of the dataset).

The thick haze is illuminated by strong orange streetlights and vehicle headlights. Instead of desaturating the image into a neutral gray, the fog scatters the colorful light, creating a highly saturated orange glow across the entire frame.

Discovery — cue reliability is condition-dependent: the six lowest dark-channel
images are all thick-haze night scenes lit by orange streetlights and headlights.
Saturation was added on the assumption "fog drains colour, so haze -> low
saturation", but these scenes violate it — the haze is lit by strong coloured
light and scatters it into a highly saturated orange glow, so here more haze
produces more saturation, not less. The relationship between a cue and fog is not
fixed; it can flip with the lighting condition. This motivates condition-aware
fusion rather than naive averaging.



## 2026-06-28 — Feature 3: brightness (RTTS)
Added brightness_score to src/features.py, computed for all 4322 RTTS images.
Range: min 0.107, mean 0.575, max 0.943 (wide spread — separates night from day).

Visual check of the extremes (verified by inspection):
- Lowest brightness: 5 of 6 are night scenes (3 are near-duplicates of one
  scene), 1 is daytime heavy fog. Brightness flags "dark scene" — usually night,
  but dense daytime fog can also read dark. Strong but imperfect night-flag.
- Highest dark-channel images are genuine dense DAYTIME fog (not bright-sky false
  alarms): the dark channel is reliable at the foggy end.
- Highest-saturation and lowest-dark-channel groups are nearly the same files
  (4 exact matches + 2 more of the same orange-haze population). The images the
  dark channel calls "clearest" are the most saturated — the two cues carry
  independent information and disagree on identical images.

Read across all three cues: no single cue is trustworthy alone; their failures
are condition-dependent and different cues fail on different conditions (dark
channel misses night + orange haze; saturation flags the orange haze; brightness
flags darkness). Supports condition-aware fusion over naive averaging.

## 2026-06-28 — Understanding the dark-channel score, and what brightness adds

What the dark-channel score actually measures. It does not see fog directly. It
measures how dark the darkest parts of an image are. The idea is that a clear
photo always has some genuinely dark spots (shadows, dark objects), and fog — a
pale veil of scattered light — lifts those dark spots toward grey. So if dark
spots survive, the image is probably clear and the score is low; if the darks are
erased, the image is probably foggy and the score is high. It is a proxy, not a
measurement: it infers fog from missing darkness.

Important caveat for the thesis. The dark channel prior (He et al. 2009) was
created to REMOVE haze from photos, not to measure it. It assumes that in normal
daytime outdoor images, most small patches contain at least one very dark pixel.
That is a statistical regularity, not a proven law. Using it as a fog-strength
score is a convenient borrowing, and it breaks whenever an image has dark pixels
for a reason other than clear air. So in this work the dark-channel score is a
widely-used physics-based proxy whose assumption fails under specific conditions —
not a proven fog sensor.

The single property that explains most failures. The dark channel really behaves
like a "how grey / how washed-out is this image" detector. Fog usually makes a
scene pale and grey, which is why the score often works. But the score reacts to
greyness, not fog itself, so it is fooled three ways:
- Night / dark scenes: full of genuinely dark pixels (unlit sky, dark buildings),
  so the score stays low and reads "clear" even in thick haze. The cue cannot tell
  "dark because clear air" from "dark because no light".
- Coloured light (e.g. orange streetlights in haze): strong colour always has at
  least one low channel, so the darkest-pixel value stays low and reads "clear",
  even though the scene is full of fog.
- Grey but clear scenes (overcast flat light, grey roads, grey concrete, pale
  grey sky): grey means all colour channels are high together, no dark pixels, so
  the score reads high and looks foggy when it is not. (This matches the earlier
  observation in the base thesis that grey content fools the dark channel.)
In short: the dark channel and fog only agree when the greyness is caused by fog
and nothing else.

What brightness adds. Brightness is the overall light level (mean of the V
channel). Computed for all 4322 RTTS images; range 0.11 to 0.94, a wide spread
that separates night from day. Looking at the six darkest images: five were night
scenes (three were near-duplicates of one scene) and one was daytime heavy fog. So
brightness flags "dark scene", which is usually night but sometimes dense fog —
a strong but imperfect night flag. This matters because night is the dark
channel's main blind spot, so brightness is the cue that can later warn us "do
not trust the dark channel here".

What I still need to check properly (next step). Six images at fixed points can
mislead — one night image at the bottom does not tell me whether there are five
such cases or fifty. The better check is to view a large sorted strip (about 50
images) ordered by the dark-channel score, to actually see where night scenes,
orange-haze scenes, and grey-but-clear scenes sit, and to watch how brightness
moves together with the dark channel across the whole range.