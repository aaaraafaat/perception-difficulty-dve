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


## 2026-06-28 — Dataset description: RTTS and the computed feature set (for thesis)

Dataset. The primary dataset for this stage is RTTS (Real-world Task-driven
Testing Set), from the RESIDE benchmark. It contains 4,322 real photographs taken
in genuine hazy and foggy outdoor conditions — not synthetic fog — which makes it
suitable for studying how degradation behaves in the real world. The images vary
in size and in scene type (daytime haze, night scenes, scenes lit by coloured
street and vehicle lighting), and this variety is important: it is exactly what
exposes where a single fog cue succeeds or fails.

Why real fog matters here. Synthetic fog is added to clear images at a known,
controlled strength, which is useful for checking that a cue responds to fog at
all. Real fog has no such ground-truth strength label and comes mixed with other
conditions (night, coloured light, varied content). RTTS is therefore used to
test whether cues that seem to measure fog still hold up once these real-world
confounds are present.

Features computed. For every one of the 4,322 images, seven training-free,
physics- or image-statistics-based features were computed directly from the
image, with no learning or labelled data required. Each is a single number per
image:
- Dark-channel score — how far the darkest regions have been lifted toward grey
  (the standard dark-channel-prior haze proxy).
- Saturation — average colour vividness; fog usually drains colour toward grey.
- Brightness — overall light level; separates dark/night scenes from bright ones.
- Contrast — spread from dark to light; fog flattens it.
- Entropy — amount of detail / tonal variety; fog smooths the scene.
- Sharpness — crispness of edges; fog blurs them.
- Noise — pixel-level grain; most relevant to dark / low-light scenes.

Verified value ranges (all 4,322 images). Each feature was range-checked to
confirm it behaves sensibly: 
dark-channel 0.00–0.88 (mean 0.45); 
saturation 0.00–0.96 (mean 0.12, low-heavy, consistent with haze draining colour);
brightness 0.11–0.94 (mean 0.57, wide enough to separate night from day);
contrast 0.06–0.81 (mean 0.39); 
entropy 3.29–7.90 bits (mean 6.94, near the 8-bit ceiling, indicating generally detailed images); 
sharpness 0.001–1.00 (mean 0.24, bunched low — most images are not razor-sharp); noise 0.005–0.53 (mean 0.07, low, as RTTS is not a heavy-grain dataset). 

Sharpness and noise are both concentrated at the low end, so they may prove weaker discriminators than the others — to be confirmed by the correlation analysis.

Output. All features are stored as one row per image in
results/tables/features_RTTS.csv, the per-dataset feature table that the
correlation and failure analysis read from.

## 2026-06-28 — What the seven features show on RTTS (observations)

After computing all seven features on the 4,322 RTTS images, the value ranges
were examined to understand how each behaves on real fog, before any deeper
analysis.

All seven produce sensible, varied numbers — none is stuck at one value or
collapsed. This means each feature is at least responding to something in the
images and is worth keeping for the comparison.

Two features stand out as likely to be weak on this dataset. Sharpness and noise
are both bunched at the low end: most images have low sharpness (median around
0.13) and low noise (median around 0.05), with only a few images higher. In plain
terms, RTTS images are mostly not razor-sharp and mostly not grainy, so these two
features do not spread the images out much. A feature that gives nearly the same
value to most images cannot separate easy from hard images well, so sharpness and
noise may turn out to be poor indicators here. This is a tentative read from the
spread alone; the correlation analysis will confirm whether they carry useful
information or not.

The other five — dark channel, saturation, brightness, contrast, entropy — each
spread the images across a wide range, so each has the potential to distinguish
between images. Whether they distinguish them in a way that matches actual fog is
the next question.

Key point to carry forward. A wide spread only means a feature *can* tell images
apart; it does not prove the feature tells them apart by fog rather than by
something else (night, colour, grey content). The earlier discovery — that
single cues are fooled by night, coloured light, and grey scenes — means a good
spread is necessary but not sufficient. The real test is how the features relate
to each other and, ultimately, to detection difficulty.

## 2026-06-28 — Colour findings: saturation, colourfulness, and their gap (RTTS)

Two colour-based features were examined on the 4,322 RTTS images: saturation
(average colour vividness) and colourfulness (the variety and spread of colours).
They measure related but different things, and comparing them revealed how colour
behaves under fog and coloured lighting.

Finding 1 — the two cues agree on grey fog, disagree on coloured haze.
On dense grey fog scenes, both saturation and colourfulness drop together toward
zero (fog washes the scene to grey, removing both vividness and variety). On
scenes lit by a single strong coloured light — the orange streetlight and
headlight haze — they split sharply: saturation is extremely high (top of the
dataset, ~0.80–0.96) because every pixel is vivid orange, but colourfulness is
only moderate because there is just one colour, not many. So the two cues are
redundant on grey scenes and carry different information on coloured scenes.

Finding 2 — the useful colour signal is the GAP between the two cues, not either
one alone. A large saturation-minus-colourfulness gap means "vivid because of one
coloured light source" (the orange-haze signature). A small gap with both low
means grey fog. This is a concrete example of why combining cues matters: neither
saturation nor colourfulness alone identifies coloured-light haze, but their
difference does.

Finding 3 — low colourfulness is an independent fog signal, but with a caveat.
The least-colourful images are dense grey fog (or near-greyscale) scenes, so low
colourfulness does flag fog — and it does so via colour, independently of the
dark channel, which flags fog via missing darkness. However, at the extreme it
goes to exactly zero and coincides with zero saturation, so at that extreme the
two colour cues become redundant.

Finding 4 — high colourfulness picks out genuinely multicoloured (clearer)
scenes, and correctly excludes the orange-haze scenes. The most-colourful images
have many real colours and low dark-channel scores (the dark channel also reads
them as clearer). The single-colour orange-haze scenes do NOT appear in this
group, confirming colourfulness separates "many real colours" (clear) from "one
strong colour" (coloured haze).

Open question to investigate next. Several of the lowest-colourfulness images read
exactly 0.000 on both colour cues, yet by eye they are foggy colour scenes that
should retain at least a little colour — they should not lose colour entirely.
This suggests some images may be true greyscale FILES (stored with no colour at
all, R=G=B everywhere), which would force both colour cues to exactly zero for a
reason unrelated to fog. If so, this is a dataset confound to identify and handle
separately, not extreme decolourising fog. To be checked by counting the
exactly-zero images and testing whether their colour channels are identical.

## 2026-06-28 — Greyscale image artefact in RTTS (dataset cleaning)

During analysis of the colour-based features, 46 of the 4,322 RTTS images were
found to be true greyscale images — that is, their red, green, and blue channels
are identical at every pixel, so the image contains no colour information at all.
These were identified using the standard definition of a greyscale image
(pixel-wise equality of the three colour channels), not a score threshold, making
the identification exact and unambiguous.

These 46 images are a dataset artefact rather than a property of the scene: their
zero colourfulness and zero saturation arise because the files are stored without
colour, not because fog has removed it. Left unaddressed, they would be
misinterpreted by any colour-based degradation measure as maximally
decolourised — the appearance of extreme fog — and would therefore distort
colour-dependent analysis. A pixel-level check confirmed that all 46, and only
these 46, are greyscale: every greyscale image scored exactly zero on both colour
cues, and no additional near-greyscale images were hidden above zero.

Accordingly, the 46 greyscale images are flagged with a dedicated indicator and
excluded from colour-based analysis, while being retained in the dataset and
reported as a documented characteristic of RTTS. This represents 1.1% of the
dataset. Identifying and isolating this artefact, rather than allowing it to pass
silently into the colour features, is part of ensuring that measured colour
behaviour reflects genuine scene degradation and not file-format effects.

## Saving the greyscale flag, and a colour-clean copy

The `is_greyscale` flag is added to the feature table and saved, so every image
stays in the main file but greyscale images remain identifiable. A second file is
also written with the 46 greyscale images removed — a colour-clean version for the
colour-based analysis, so those black-and-white files cannot distort the colour
features. The original full table is kept; nothing is deleted.

## 2026-06-28 — Data cleaning summary: greyscale and near-duplicate images (RTTS)

Two dataset artefacts were identified and handled before analysis, each by an
exact, content-based test rather than a score threshold, and each flagged rather
than deleted so the dataset count remains documented and recoverable.

Greyscale images. 46 of the 4,322 RTTS images are true greyscale (red, green, and
blue channels identical at every pixel), identified by pixel-wise channel
equality. These contain no colour information, so they read as maximally
decolourised on any colour-based measure for a file-format reason unrelated to
fog, and would otherwise distort colour analysis. They are flagged (is_greyscale)
and excluded from colour-based analysis.

Near-duplicate images. Near-duplicates were identified by perceptual hashing,
which compares image content rather than feature scores (visually different scenes
can share nearly identical scores, so scores cannot be used for this). The
matching distance was selected empirically: a sweep showed loose thresholds
collapse the grouping (distance 20 drew 3,871 images into a few clusters; 15 and
10 grouped clearly different scenes), so distance 6 was adopted as the strictest
setting that still captured genuine near-duplicates (distances 6 and 7 were
identical). Inspection of the resulting groups confirmed 28 genuine groups (25
pairs and 3 triples) of same-scene frames — some captured only moments apart with
a vehicle or pedestrian having moved slightly, some at minor angle changes. Two
false-match groups were removed by hand: one pair of near-featureless images (a
flat dark-grey texture and a bright hazy sky) the hash confused for lack of
distinguishing structure, and one pair of different subjects sharing a single
figure-against-hazy-background composition — both known limitations of perceptual
hashing, caught by inspection rather than accepted on the score. This leaves 31
images flagged as near-duplicates (is_duplicate), with one image retained per
group.

Cleaned analysis set. Removing the 46 greyscale and 31 near-duplicate images (no
image was both) leaves 4,245 images for the cleaned analysis set, approximately
1.8% of the dataset removed. The full table retains all images and flags; the
cleaned table is used for the feature analysis.

## 2026-06-28 — Feature-score near-duplicates: an alternative detection method (recorded, not removed)

A second, complementary way of finding near-duplicate images was explored: instead
of comparing image content (as perceptual hashing does), images were compared on
their measured properties — the eight feature scores (dark channel, saturation,
brightness, contrast, entropy, sharpness, noise, colourfulness), each scaled to a
common 0-1 range, with similarity measured as the Euclidean distance across all
eight together. Two images close on this combined distance are near-identical in
every measured property at once.

Applied to the cleaned set (greyscale and perceptual-hash duplicates already
removed), this method surfaced additional near-duplicates that perceptual hashing
had missed. The number of pairs grew sharply with the distance threshold — 2 pairs
at distance 0.01, 23 pairs at 0.02, and 108 pairs at 0.03 — so 0.02 marks the
tight region where pairs are still predominantly genuine. Inspection of the 23
pairs at distance 0.02 found that 20 were genuine near-duplicate frames of the same
scene (same camera position, lighting, and conditions, captured seconds apart),
and 3 were same-viewpoint images with different objects present (for example, one
versus two vehicles).

These were recorded but deliberately NOT removed from the analysis set. The
same-viewpoint-different-object pairs are ambiguous: because the objects present
differ, they may be legitimately distinct observations for a detection-difficulty
study rather than redundant duplicates, so removing them could discard real data.
Accordingly, the affected images are flagged with a feature_near_duplicate
indicator in the full table, leaving the decision of whether to exclude them to any
future work, while the cleaned analysis set is unchanged at 4,245 images.

This also establishes a methodological point: feature-score similarity is a usable
alternative duplicate-finding method, complementary to perceptual hashing — each
catches some near-duplicates the other misses — but it is unreliable as a
standalone duplicate detector, because the boundary between genuine duplicates and
merely similar scenes blurs as the threshold loosens (108 pairs by distance 0.03).
Content-based hashing remains the primary method; feature similarity is a useful
secondary check.

## 2026-06-28 — Stage 1 complete (session close)

Stage 1 (RTTS feature extraction and cleaning) is finished and saved.

Done:
- RTTS loaded (4,322 images), copied to local disk for fast access.
- Eight training-free features computed and range-verified: dark channel,
  saturation, brightness, contrast, entropy, sharpness, noise, colourfulness.
- Two confounds found and handled (flagged, not deleted): 46 greyscale images
  (R=G=B), and 31 near-duplicates across 28 groups (perceptual hash, distance 6).
- Feature-score near-duplicates recorded as an optional flag (feature_near_duplicate),
  not removed.
- Saved: features_RTTS.csv (master, all images + flags) and features_RTTS_clean.csv
  (cleaned analysis set, 4,245 images).
- Notebook: 01_rtts_feature_extraction_and_cleaning.ipynb.

Next session:
- Optional first: Restart and run all on notebook 01 to confirm reproducibility.
- Start notebook 02 (analysis): load features_RTTS_clean.csv and build the
  correlation table across the eight features — the first numerical view of which
  cues agree, which are redundant, and which are weak (sharpness and noise
  suspected weak; saturation/colourfulness overlap on grey scenes).

Correlation plot:
## What the feature correlation shows

The eight features were correlated against each other (Spearman, on the 4,245-image
clean set) to see which measure the same thing and which are independent. This
matters because the argument for combining cues only holds if the cues actually
carry different information. Four findings stand out.

1. Two pairs are strongly redundant. Noise and sharpness correlate at 0.96 — almost
perfectly — because both react to fine high-frequency detail; on this data they are
essentially the same signal, and carrying both adds little. Saturation and
colourfulness correlate at 0.83: they overlap heavily (both drop as colour drains in
fog) but are not identical. That remaining difference is exactly the orange-haze case
found earlier — high saturation but lower colourfulness when a scene is flooded by a
single coloured light.

2. The dark channel and brightness are strongly entangled (0.82). This is the night
confound expressed as a number: the dark-channel score rises with image brightness,
so brighter images read as foggier and darker images as clearer — the exact failure
seen in night scenes, which the dark channel scores as clear. A large part of what
the dark-channel score reflects is simply how bright the image is, not how foggy.

3. Contrast and entropy are related (0.73). Both capture how much variation and detail
a scene holds, and fog flattens both. They overlap but each still adds something.

4. Several features are genuinely independent. Brightness is close to zero correlation
with contrast, colourfulness, and noise, so it carries information none of those do —
which is why it is useful as a flag for the night condition.

Overall, the eight features collapse into roughly four independent groups:
brightness with dark channel (illumination and haze, entangled); saturation with
colourfulness (colour); contrast with entropy (detail and richness); and noise with
sharpness (fine high-frequency detail, nearly identical). So there are about four
distinct signals, not eight. This is the basis for combining cues: mixing cues from
different groups adds information, while mixing within a group does not — and one of
the near-identical pair (noise or sharpness) could be dropped with little loss. It
also quantifies the dark channel's contamination by illumination, supporting the
finding that it is not a clean fog measure on its own.

The dark channel's failures are the coloured scenes
Colouring the dark-channel vs brightness scatter by saturation links two confounds in one picture. The main diagonal cloud — images that follow the expected relationship — is low saturation (greyish fog). The points that fall off the trend, bright images scored as low dark-channel ("clear"), are high saturation. These are the brightly coloured scenes (such as orange-lit haze). So the dark channel under-reads fog precisely when the scene is bright and vividly coloured: the brightness confound and the colour confound are not separate problems but the same images. The dark channel is least trustworthy exactly where the scene carries strong colour.