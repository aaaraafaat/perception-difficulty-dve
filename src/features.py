"""Image feature functions for perception-difficulty estimation.

Each function takes one image (as a BGR array, the format OpenCV loads) and
returns a single number, or an intermediate map for visualization. Features are
training-free and computed at the image's native resolution. New features are
added as further functions in this file.
"""
import cv2
import numpy as np


def dark_channel_map(image_bgr, patch_size=15):
    """Return the dark-channel image (single channel, same height and width).

    The dark channel is the per-pixel minimum across the colour channels,
    followed by a local minimum over a square patch of side `patch_size`. In a
    clear image most patches contain something genuinely dark, so this stays
    low; haze lifts those dark values toward grey.
    """
    min_across_channels = np.min(image_bgr, axis=2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (patch_size, patch_size))
    return cv2.erode(min_across_channels, kernel)


def dark_channel_score(image_bgr, patch_size=15):
    """Return the mean dark-channel value, scaled to the range 0 to 1.

    Lower means deep darks are still present (clear); higher means the darks
    have washed out toward grey (more haze).
    """
    dark = dark_channel_map(image_bgr, patch_size)
    return float(dark.mean() / 255.0)

def saturation_score(image_bgr):
    """Return the mean saturation, scaled to the range 0 to 1.

    Saturation is the colourfulness of each pixel. Fog drains colour toward
    grey, so haze lowers this value. Lower means washed-out / greyer; higher
    means stronger colour. Computed from the HSV form of the image.
    """
    image_hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    saturation_channel = image_hsv[:, :, 1]  # the S channel, 0 to 255
    return float(saturation_channel.mean() / 255.0)