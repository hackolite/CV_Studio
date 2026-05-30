# -*- coding: utf-8 -*-
"""
Elegant Apple-style splash screen for CvStudio.dev.

Features:
- Dark cinematic background
- Vector-drawn geometric logo (camera aperture / lens motif)
- Smooth fade-in animation with eased progress and pulsed fading
- Ambient design sound (airplane interior chime)
- Minimalist typography
"""
import math
import time
import threading
import dearpygui.dearpygui as dpg
import numpy as np
import sounddevice as sd


# ─── Design Tokens ──────────────────────────────────────────────────────────
_BG_COLOR = (13, 13, 15, 255)           # Near-black background
_ACCENT = (0, 122, 255, 255)            # Apple blue
_ACCENT_SOFT = (0, 122, 255, 120)       # Subtle glow
_TEXT_PRIMARY = (245, 245, 247, 255)    # White text
_TEXT_SECONDARY = (142, 142, 147, 255)  # Gray subtitle
_TEXT_TERTIARY = (99, 99, 102, 255)     # Subtle hint
_PROGRESS_BG = (38, 38, 40, 255)        # Track color
_PROGRESS_FG = (0, 122, 255, 255)       # Fill color

# ─── Tags ────────────────────────────────────────────────────────────────────
_SPLASH_WIN = "___splash_apple_win"
_SPLASH_THEME = "___splash_apple_theme"
_SPLASH_DRAW = "___splash_apple_drawlist"

# ─── Dimensions ──────────────────────────────────────────────────────────────
_SPLASH_W = 680
_SPLASH_H = 420


def _ease_out_cubic(t: float) -> float:
    """Eased progress curve for smooth animation."""
    return 1.0 - pow(1.0 - t, 3)


def _ease_in_out_sine(t: float) -> float:
    """Smooth sine ease for fade."""
    return -(math.cos(math.pi * t) - 1.0) / 2.0



def _generate_cabin_chime(duration: float = 2.8, sr: int = 44100) -> np.ndarray:
    """
    Generate an ambient airplane-cabin-style design chime.
    Soft layered tones with gentle attack and release.
    """
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    # Soft fundamental tone (C5 ~523 Hz) with harmonics
    tone = 0.0
    freqs = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6 – major chord
    amps = [0.30, 0.20, 0.15, 0.08]

    for freq, amp in zip(freqs, amps):
        tone += amp * np.sin(2.0 * np.pi * freq * t)

    # Subtle low sub-bass warmth (like cabin hum)
    tone += 0.05 * np.sin(2.0 * np.pi * 120.0 * t)

    # Envelope: smooth attack + sustained + gentle release
    attack = 0.4
    release = 0.8
    env = np.ones_like(t)
    attack_samples = int(attack * sr)
    release_samples = int(release * sr)
    # Smooth sine attack
    env[:attack_samples] = np.sin(np.linspace(0, np.pi / 2, attack_samples)) ** 2
    # Smooth sine release
    env[-release_samples:] = np.sin(np.linspace(np.pi / 2, 0, release_samples)) ** 2

    tone *= env

    # Normalize to safe volume
    peak = np.max(np.abs(tone))
    if peak > 0:
        tone = tone / peak * 0.35

    return tone.astype(np.float32)


def _play_splash_sound(duration: float = 2.8):
    """Play the splash chime in a background thread (non-blocking)."""
    try:
        audio = _generate_cabin_chime(duration=duration)
        sd.play(audio, samplerate=44100)
    except Exception:
        pass  # Sound is non-critical; fail silently


def _draw_logo_vectors(drawlist, cx: float, cy: float, radius: float, alpha: float):
    """
    Draw the CvStudio logo using DearPyGui vector primitives.
    A modern camera aperture design with clean geometric lines.
    """
    a = int(255 * alpha)
    accent = (0, 122, 255, a)
    accent_dim = (0, 90, 200, int(a * 0.5))
    accent_glow = (60, 160, 255, int(a * 0.3))

    # Outer circle (thin, elegant)
    dpg.draw_circle(
        center=(cx, cy),
        radius=radius,
        color=accent,
        thickness=2.0,
        parent=drawlist,
    )

    # Inner glow ring
    dpg.draw_circle(
        center=(cx, cy),
        radius=radius * 0.88,
        color=accent_glow,
        thickness=1.0,
        parent=drawlist,
    )

    # Aperture blades (6 triangular segments)
    num_blades = 6
    inner_r = radius * 0.35
    outer_r = radius * 0.75
    blade_half_angle = math.pi / 14.0

    for i in range(num_blades):
        angle = (2.0 * math.pi * i) / num_blades - math.pi / 2.0

        # Blade vertices
        p1 = (
            cx + inner_r * math.cos(angle - blade_half_angle * 0.6),
            cy + inner_r * math.sin(angle - blade_half_angle * 0.6),
        )
        p2 = (
            cx + outer_r * math.cos(angle - blade_half_angle),
            cy + outer_r * math.sin(angle - blade_half_angle),
        )
        p3 = (
            cx + outer_r * math.cos(angle + blade_half_angle),
            cy + outer_r * math.sin(angle + blade_half_angle),
        )
        p4 = (
            cx + inner_r * math.cos(angle + blade_half_angle * 0.6),
            cy + inner_r * math.sin(angle + blade_half_angle * 0.6),
        )

        # Draw blade as filled quad
        dpg.draw_quad(
            p1=p1, p2=p2, p3=p3, p4=p4,
            color=accent_dim,
            fill=accent_dim,
            parent=drawlist,
        )

        # Blade edge lines for crispness
        dpg.draw_line(
            p1=p2, p2=p3,
            color=accent,
            thickness=1.2,
            parent=drawlist,
        )

    # Center dot with glow
    dpg.draw_circle(
        center=(cx, cy),
        radius=radius * 0.12,
        color=accent,
        fill=accent,
        parent=drawlist,
    )
    dpg.draw_circle(
        center=(cx, cy),
        radius=radius * 0.18,
        color=accent_glow,
        thickness=1.5,
        parent=drawlist,
    )

    # Crosshair lines (subtle, technical feel)
    line_inner = radius * 0.9
    line_outer = radius * 1.0
    cross_color = (0, 122, 255, int(a * 0.25))
    for i in range(4):
        angle = (math.pi / 2.0) * i
        p_start = (cx + line_inner * math.cos(angle), cy + line_inner * math.sin(angle))
        p_end = (cx + line_outer * math.cos(angle), cy + line_outer * math.sin(angle))
        dpg.draw_line(p1=p_start, p2=p_end, color=cross_color, thickness=1.0, parent=drawlist)


def _draw_text_label(drawlist, text: str, cx: float, y: float, font_size: float,
                     color: tuple, alpha: float):
    """Draw text centered at position. DearPyGui draw_text is top-left aligned."""
    # Approximate character width for centering
    char_w = font_size * 0.52
    text_w = len(text) * char_w
    x = cx - text_w / 2.0
    r, g, b, _ = color
    a = int(255 * alpha)
    dpg.draw_text(
        pos=(x, y),
        text=text,
        color=(r, g, b, a),
        size=font_size,
        parent=drawlist,
    )


def _draw_progress_bar(drawlist, cx: float, y: float, width: float, progress: float,
                       alpha: float):
    """Draw a thin, elegant progress bar."""
    bar_h = 3.0
    x_start = cx - width / 2.0
    a = alpha

    # Background track
    dpg.draw_rectangle(
        pmin=(x_start, y),
        pmax=(x_start + width, y + bar_h),
        color=(0, 0, 0, 0),
        fill=(38, 38, 40, int(200 * a)),
        rounding=2.0,
        parent=drawlist,
    )

    # Filled portion
    if progress > 0.005:
        fill_w = width * progress
        dpg.draw_rectangle(
            pmin=(x_start, y),
            pmax=(x_start + fill_w, y + bar_h),
            color=(0, 0, 0, 0),
            fill=(0, 122, 255, int(220 * a)),
            rounding=2.0,
            parent=drawlist,
        )


def _create_splash_theme():
    """Create a borderless, clean dark theme for the splash window."""
    if dpg.does_item_exist(_SPLASH_THEME):
        return
    with dpg.theme(tag=_SPLASH_THEME):
        with dpg.theme_component(dpg.mvWindowAppItem):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, _BG_COLOR, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 18, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0, category=dpg.mvThemeCat_Core)


def show_splash_screen(duration_seconds: float = 2.8, steps: int = 90):
    """
    Display an elegant Apple-style splash screen with animated logo and progress.

    Args:
        duration_seconds: Total display time.
        steps: Number of animation frames (higher = smoother).
    """
    steps = max(1, int(steps))
    duration_seconds = max(0.0, float(duration_seconds))
    _create_splash_theme()

    # Get viewport dimensions
    vp_w = dpg.get_viewport_client_width()
    vp_h = dpg.get_viewport_client_height()
    if vp_w <= 0 or vp_h <= 0:
        vp_w = dpg.get_viewport_width()
        vp_h = dpg.get_viewport_height()

    # Center the splash
    splash_x = max(0, int((vp_w - _SPLASH_W) / 2))
    splash_y = max(0, int((vp_h - _SPLASH_H) / 2))

    # Create splash window
    with dpg.window(
        tag=_SPLASH_WIN,
        pos=(splash_x, splash_y),
        width=_SPLASH_W,
        height=_SPLASH_H,
        no_title_bar=True,
        no_move=True,
        no_resize=True,
        no_close=True,
        no_collapse=True,
        no_scrollbar=True,
        no_saved_settings=True,
        no_background=False,
    ):
        dpg.add_drawlist(
            tag=_SPLASH_DRAW,
            width=_SPLASH_W,
            height=_SPLASH_H,
        )

    dpg.bind_item_theme(_SPLASH_WIN, _SPLASH_THEME)

    # Layout constants – center logo precisely in the drawlist
    logo_cx = _SPLASH_W / 2.0
    logo_cy = _SPLASH_H * 0.36
    logo_radius = 52.0
    title_y = logo_cy + logo_radius + 32
    subtitle_y = title_y + 36
    progress_y = _SPLASH_H - 50
    progress_w = _SPLASH_W * 0.35

    # Start ambient sound in background thread
    threading.Thread(
        target=_play_splash_sound,
        args=(duration_seconds,),
        daemon=True,
    ).start()

    # Pulsed fading parameters
    pulse_freq = 1.8  # Hz – gentle breathing pulse
    pulse_depth = 0.15  # 15% intensity variation

    # Animation loop
    frame_time = duration_seconds / float(steps) if duration_seconds > 0 else 0
    for step in range(steps):
        t = float(step + 1) / float(steps)
        elapsed = t * duration_seconds

        # Clear drawlist
        dpg.delete_item(_SPLASH_DRAW, children_only=True)

        # Background fill (ensures full coverage)
        dpg.draw_rectangle(
            pmin=(0, 0),
            pmax=(_SPLASH_W, _SPLASH_H),
            color=(0, 0, 0, 0),
            fill=_BG_COLOR,
            rounding=18.0,
            parent=_SPLASH_DRAW,
        )

        # Subtle radial gradient effect (concentric circles centered on logo)
        for i in range(5):
            r = 180 - i * 30
            grad_alpha = int(6 - i)
            dpg.draw_circle(
                center=(logo_cx, logo_cy),
                radius=r,
                color=(0, 0, 0, 0),
                fill=(0, 122, 255, grad_alpha),
                parent=_SPLASH_DRAW,
            )

        # Fade-in alpha with pulsed breathing effect
        base_fade = _ease_in_out_sine(min(1.0, t * 2.5))  # Fade completes at ~40%
        pulse = 1.0 - pulse_depth * (0.5 + 0.5 * math.sin(2.0 * math.pi * pulse_freq * elapsed))
        fade = base_fade * pulse

        # Draw logo
        _draw_logo_vectors(_SPLASH_DRAW, logo_cx, logo_cy, logo_radius, fade)

        # Title: "CvStudio.dev"
        _draw_text_label(
            _SPLASH_DRAW, "CvStudio.dev",
            logo_cx, title_y, 28.0,
            _TEXT_PRIMARY, fade,
        )

        # Subtitle
        _draw_text_label(
            _SPLASH_DRAW, "Computer Vision Studio",
            logo_cx, subtitle_y, 15.0,
            _TEXT_SECONDARY, fade * 0.8,
        )

        # Progress bar (appears after fade-in)
        progress_alpha = _ease_in_out_sine(max(0.0, (t - 0.2) / 0.8))
        progress_value = _ease_out_cubic(t)
        _draw_progress_bar(
            _SPLASH_DRAW, logo_cx, progress_y,
            progress_w, progress_value, progress_alpha * pulse,
        )

        # Version / status text
        if t > 0.3:
            status_alpha = _ease_in_out_sine(min(1.0, (t - 0.3) / 0.4))
            _draw_text_label(
                _SPLASH_DRAW, "Initializing…",
                logo_cx, progress_y + 14, 11.0,
                _TEXT_TERTIARY, status_alpha * 0.7 * pulse,
            )

        # Render frame
        dpg.render_dearpygui_frame()
        if frame_time > 0:
            time.sleep(frame_time)

    # Hold the final frame briefly for polish
    time.sleep(0.15)

    # Stop any remaining sound playback
    try:
        sd.stop()
    except Exception:
        pass

    # Cleanup
    if dpg.does_item_exist(_SPLASH_WIN):
        dpg.delete_item(_SPLASH_WIN)
    if dpg.does_item_exist(_SPLASH_THEME):
        dpg.delete_item(_SPLASH_THEME)
