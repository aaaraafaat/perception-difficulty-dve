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

def brightness_score(image_bgr):
    """Return the mean brightness, scaled to the range 0 to 1.

    Brightness is the overall light level of the image. Computed as the mean of
    the V (value) channel of the HSV form, which is the per-pixel maximum across
    colour channels. Low means a dark or night scene; high means a bright one.
    """
    image_hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    value_channel = image_hsv[:, :, 2]  # the V channel, 0 to 255
    return float(value_channel.mean() / 255.0)

def contrast_score(image_bgr):
    """Return image contrast as the standard deviation of brightness, scaled to 0-1.

    Contrast is how widely the image ranges from dark to light. Fog flattens
    everything toward mid-grey, so haze lowers contrast. Lower means flat/foggy;
    higher means a punchy dark-to-light range.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(gray.std() / 128.0)  # /128 keeps typical values in 0-1


def entropy_score(image_bgr):
    """Return the brightness entropy in bits (typically 0 to 8).

    Entropy measures how much detail / variety of brightness values the image
    holds. A clear scene is full of texture and varied tones (high entropy); fog
    smooths the scene toward uniform grey (low entropy). Higher means more
    detail; lower means smoothed-out / foggy.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    histogram = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
    probabilities = histogram / histogram.sum()
    probabilities = probabilities[probabilities > 0]  # ignore empty bins
    return float(-(probabilities * np.log2(probabilities)).sum())


def sharpness_score(image_bgr):
    """Return image sharpness (variance of the Laplacian), scaled toward 0-1.

    Sharpness measures how crisp the edges and fine detail are. Fog blurs edges,
    so haze lowers sharpness. Lower means blurred / foggy; higher means crisp
    detail. Capped at 1.0 since very sharp images can exceed the scaling range.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    laplacian_variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return float(min(laplacian_variance / 1000.0, 1.0))  # /1000 and cap at 1


def noise_score(image_bgr):
    """Return an estimate of image noise / grain, scaled toward 0-1.

    Noise is random pixel-level grain, most visible in dark / night / low-light
    scenes. Estimated as the difference between the image and a slightly blurred
    version (blurring removes fine grain). Higher means grainier; relevant for
    flagging night and low-light images. Capped at 1.0.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype("float")
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    noise_estimate = np.abs(gray - blurred).mean()
    return float(min(noise_estimate / 20.0, 1.0))  # /20 and cap at 1