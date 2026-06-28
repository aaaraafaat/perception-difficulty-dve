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