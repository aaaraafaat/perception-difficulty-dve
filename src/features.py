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

    Dark channel: per-pixel minimum over B, G, R, then a local minimum over a
    square patch (He, Sun & Tang 2009, Eq. 5; patch 15 as in the original).
    Erosion with a rectangular kernel implements the patch-minimum filter.
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
    """Mean perceived luminance: mean of the grayscale image, normalised to
    [0, 1]. Grayscale (luminance) is used rather than the HSV value channel so
    that a saturated single-colour cast (e.g. orange dust) is not mistaken for
    brightness.
    """
    grey = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(grey.mean() / 255.0)

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

def colourfulness_score(image_bgr):
    """Return image colourfulness (Hasler-Susstrunk metric), scaled to roughly 0-1.

    Colourfulness measures the variety and spread of colours, not just average
    vividness. A scene lit by a single coloured source (e.g. orange haze) is
    vivid but contains little colour variety, so it scores LOW here even when
    saturation is high - which is how this separates one-colour scenes from
    genuinely multicoloured ones. Higher means a wider range of colours.
    """
    # Read channels explicitly by name to avoid any positional swap.
    blue = image_bgr[:, :, 0].astype("float")
    green = image_bgr[:, :, 1].astype("float")
    red = image_bgr[:, :, 2].astype("float")

    # Opponent-colour differences (Hasler-Susstrunk).
    red_green = red - green
    yellow_blue = 0.5 * (red + green) - blue

    # Combine the spread (std) and the offset (mean) of both opponent channels.
    std_combined = np.sqrt(red_green.std() ** 2 + yellow_blue.std() ** 2)
    mean_combined = np.sqrt(red_green.mean() ** 2 + yellow_blue.mean() ** 2)
    colourfulness = std_combined + 0.3 * mean_combined

    # The metric ranges ~0 to ~150 in practice; /150 keeps typical values in 0-1.
    return float(colourfulness / 150.0)

def airlight_estimate(image_bgr, patch_size=15, top_fraction=0.001):
    """Estimate the atmospheric light (airlight) colour of an image.

    Atmospheric light A. Candidates: the top 0.1% brightest pixels of the dark
    channel (He, Sun & Tang 2009). A is the MEAN colour of the candidates - a
    deliberate robustness deviation from the original rule (single brightest input
    pixel), so isolated saturated pixels cannot set A alone. Estimation variants
    are surveyed in Lee et al. 2016. The 1e-6 floor guards the later division.
    """
    dark = dark_channel_map(image_bgr, patch_size)
    top_count = max(1, int(dark.size * top_fraction))
    flat_indices = np.argpartition(dark.ravel(), -top_count)[-top_count:]
    rows, cols = np.unravel_index(flat_indices, dark.shape)
    return image_bgr[rows, cols].reshape(-1, 3).mean(axis=0)


def transmission_map(image_bgr, patch_size=15, omega=0.95):
    """Estimate the per-pixel transmission map t in [1 − omega, 1].

    Transmission t = 1 - omega * dark(I / A), omega = 0.95 (He, Sun & Tang
    2009, Eq. 12), per channel normalization by A, at native resolution. The
    dark(I/A) term is clipped to [0, 1] as a measurement guard: regions brighter
    than A in all channels would otherwise drive t negative, a case He handles at
    restoration via the t0 floor, which is not used here because this function
    measures rather than restores. The coarse (unrefined) transmission is used:
    matting/guided-filter refinement re-aligns t to object edges for artifact-free
    dehazing and is unnecessary for an image-mean measurement.
    """
    airlight = np.maximum(airlight_estimate(image_bgr, patch_size), 1e-6)
    normalized = image_bgr.astype(np.float64) / airlight
    min_across_channels = normalized.min(axis=2).astype(np.float32)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (patch_size, patch_size))
    dark_of_normalized = cv2.erode(min_across_channels, kernel)
    return 1.0 - omega * np.clip(dark_of_normalized, 0.0, 1.0)


def dcp_severity_score(image_bgr, patch_size=15, omega=0.95):
    """Return the DCP fog-severity score: the mean of (1 - transmission).

    Fog severity = mean(1 - t), the average veil fraction, in [0, omega].
    Algebraically omega * mean(dark(I/A)): a mean-dark-channel density index on
    the airlight-normalized image. Dark-channel density indices are validated
    against labelled Cityscapes fog levels at ~0.98 accuracy (Guo, Wang & Li
    2022); this specific aggregation is the definition adopted by this study.
    """
    transmission = transmission_map(image_bgr, patch_size, omega)
    return float((1.0 - transmission).mean())




"""____"""






def median_brightness_score(image_bgr):
    """Median perceived luminance: median of the grayscale image (0-255).
    Grayscale is used rather than the HSV value channel so a saturated
    single-colour cast is not mistaken for brightness; the median resists
    bright point sources (headlights, lamps) in night scenes.
    """
    grey = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(np.median(grey))

def orange_index_score(image_bgr):
    """Warm-cast strength: mean(R) - mean(B), in -255..255; positive = warm
    (orange/sepia) cast. Sand and dust scatter blue more than red, giving a
    wavelength-dependent per-channel airlight (Wei et al. 2025); a strong
    positive value flags the coloured-dust condition that violates the DCP's
    achromatic-airlight assumption.
    """
    channel_means = image_bgr.reshape(-1, 3).mean(axis=0)  # B, G, R
    return float(channel_means[2] - channel_means[0])


def channel_spread_score(image_bgr):
    """Colour-cast magnitude regardless of hue: max - min of the three channel
    means, in 0-255. Near zero for achromatic scenes; large under any
    single-colour illumination or atmospheric cast.
    """
    channel_means = image_bgr.reshape(-1, 3).mean(axis=0)
    return float(channel_means.max() - channel_means.min())


def rms_contrast_score(image_bgr):
    """RMS contrast: standard deviation of grey intensity / 255 (Peli 1990).
    The fog veil compresses the intensity range, lowering contrast.
    """
    grey = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(grey.std() / 255.0)


def upper_contrast_score(image_bgr, upper_fraction=0.5):
    """RMS contrast of the upper image region (top half by default). In road
    scenes the upper region holds the far field, where fog suppresses contrast
    first; a fog witness independent of the dark channel (Bronte, Bergasa &
    Alcantarilla 2009; Hautiere et al. 2006).
    """
    grey = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    upper_region = grey[: int(grey.shape[0] * upper_fraction), :]
    return float(upper_region.std() / 255.0)