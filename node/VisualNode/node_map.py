#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Map Visualization Node for CV Studio

This node provides interactive map visualization using:
- contextily: For downloading OpenStreetMap tiles
- matplotlib: For rendering maps with GPS points
- Pillow: For image processing
- Dear PyGui: For displaying maps in the node editor

Features:
- Downloads OpenStreetMap tiles with contextily
- Renders maps with GPS points (lat, lon)
- Converts rendered maps into textures
- Displays textures inside dpg.node_editor nodes
- Supports zoom and bounding box auto-scaling
- Implements local tile caching
- Updates textures dynamically when new GPS points are added
"""
import time
import json
import os
import tempfile
import hashlib
import math
import traceback
import concurrent.futures
from datetime import datetime
from io import BytesIO

import numpy as np
import cv2
from PIL import Image
import dearpygui.dearpygui as dpg
import requests

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode

# Import matplotlib for map rendering
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

# Import contextily for OpenStreetMap tile downloading
try:
    import contextily as ctx
    CONTEXTILY_AVAILABLE = True
except ImportError:
    print("Warning: contextily not installed. Map rendering will be limited.")
    CONTEXTILY_AVAILABLE = False

# Optional Pillow extras for higher-quality post-processing
try:
    from PIL import ImageDraw, ImageFilter, ImageEnhance
    PIL_DRAW_AVAILABLE = True
except ImportError:  # Pillow is required, but be defensive
    PIL_DRAW_AVAILABLE = False

# Cache directory for map tiles and generated maps
# contextily has its own caching mechanism, but we create this for compatibility
CACHE_DIR = os.path.join(tempfile.gettempdir(), 'cv_studio_map_cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# Map rendering constants
MIN_RANGE_METERS = 1000      # Minimum range for single points (1 km)
DEFAULT_RANGE_METERS = 10000  # Default range when min is needed (10 km)
MAP_PADDING_FACTOR = 0.15     # Padding around bounding box (15%)

# Moving-point marker styling (applied to points carrying ``is_moving=True``).
# Producers (e.g. CoordinateExamples / RoutePlayer / GPSMovementSimulator) can
# flag the "currently moving" coordinate with ``is_moving=True`` and optionally
# override the scale/alpha per-point via ``marker_scale`` / ``marker_alpha``.
MOVING_POINT_SCALE = 4.0     # Marker is rendered ~4x larger than a normal one
MOVING_POINT_ALPHA = 0.5     # Marker is rendered semi-transparent


def _moving_marker_style(point):
    """Return (scale, alpha_factor) for a coordinate point.

    Points carrying ``is_moving=True`` are rendered enlarged and translucent
    so they stand out as the current position along an animated trajectory.
    The scale defaults to :data:`MOVING_POINT_SCALE` and the alpha factor to
    :data:`MOVING_POINT_ALPHA`, but each can be overridden per-point via the
    optional ``marker_scale`` and ``marker_alpha`` keys.

    Static markers (``is_moving`` absent or falsy) are returned unchanged
    (``scale=1.0``, ``alpha_factor=1.0``).
    """
    try:
        is_moving = bool(point.get("is_moving"))
    except AttributeError:
        return 1.0, 1.0
    if not is_moving:
        return 1.0, 1.0
    try:
        scale = float(point.get("marker_scale", MOVING_POINT_SCALE))
    except (TypeError, ValueError):
        scale = MOVING_POINT_SCALE
    try:
        alpha_factor = float(point.get("marker_alpha", MOVING_POINT_ALPHA))
    except (TypeError, ValueError):
        alpha_factor = MOVING_POINT_ALPHA
    # Guard against pathological values.
    if scale <= 0:
        scale = 1.0
    alpha_factor = max(0.0, min(1.0, alpha_factor))
    return scale, alpha_factor


def _scaled_alpha(base, factor):
    """Multiply an 8-bit alpha channel by ``factor`` and clamp to [0, 255]."""
    return max(0, min(255, int(round(base * factor))))


# Keys that should never be offered as colour metrics in the Map node.
# Anything else found on incoming points (numeric values in [0, 1]) is a
# valid candidate for the green→yellow→orange→red gradient.
METRIC_NONE = "(none)"
_METRIC_EXCLUDED_KEYS = {
    "lat", "lon", "latitude", "longitude",
    "name", "ship_name", "info", "mmsi", "callsign",
    "is_moving", "marker_scale", "marker_alpha",
}


def _metric_gradient_color(value, alpha=255):
    """Return an RGBA tuple for a percentage ``value`` in [0, 1].

    The gradient walks through green → yellow → orange → red so that
    values close to 1 (e.g. high "secousses" / jolts) are visually loud.
    Values outside [0, 1] are clamped. Non-numeric values return a neutral
    grey so callers can fall back gracefully when no metric is available.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return (170, 170, 170, alpha)
    if math.isnan(v):
        return (170, 170, 170, alpha)
    v = max(0.0, min(1.0, v))

    # Three linear segments between four anchor colours.
    # 0.00 → green   (0,   180, 0)
    # 0.50 → yellow  (240, 220, 0)
    # 0.75 → orange  (255, 140, 0)
    # 1.00 → red     (220, 30,  0)
    stops = [
        (0.00, (0, 180, 0)),
        (0.50, (240, 220, 0)),
        (0.75, (255, 140, 0)),
        (1.00, (220, 30, 0)),
    ]
    for (t0, c0), (t1, c1) in zip(stops[:-1], stops[1:]):
        if v <= t1:
            span = max(1e-9, t1 - t0)
            t = (v - t0) / span
            r = int(round(c0[0] + (c1[0] - c0[0]) * t))
            g = int(round(c0[1] + (c1[1] - c0[1]) * t))
            b = int(round(c0[2] + (c1[2] - c0[2]) * t))
            return (r, g, b, alpha)
    r, g, b = stops[-1][1]
    return (r, g, b, alpha)


def _metric_candidate_keys(points):
    """Return the list of keys eligible for the metric selector.

    A key is eligible when it appears at least once on a point with a
    numeric value in [0, 1] and is not a built-in/spatial key.
    """
    keys = []
    seen = set()
    for pt in points or ():
        if not isinstance(pt, dict):
            continue
        for k, v in pt.items():
            if k in _METRIC_EXCLUDED_KEYS or k.startswith("_"):
                continue
            if k in seen:
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if math.isnan(fv) or fv < 0.0 or fv > 1.0:
                continue
            seen.add(k)
            keys.append(k)
    return keys

# Simplified continental outlines for map context visualization
# These are rough approximations to give geographic context in the map view
# Format: {region_name: (longitude_coords, latitude_coords)}
SIMPLIFIED_CONTINENTS = {
    'europe': {
        'bounds': {'lon': (-15, 40), 'lat': (35, 70)},
        'outline': {
            'lon': [-10, 15, 30, 30, 15, 0, -10, -10],
            'lat': [35, 35, 40, 60, 70, 65, 50, 35]
        }
    },
    'north_america': {
        'bounds': {'lon': (-130, -60), 'lat': (25, 50)},
        'outline': {
            'lon': [-125, -125, -70, -70, -125],
            'lat': [25, 50, 50, 25, 25]
        }
    },
    'asia': {
        'bounds': {'lon': (60, 140), 'lat': (20, 50)},
        'outline': {
            'lon': [60, 140, 140, 100, 60, 60],
            'lat': [20, 20, 50, 50, 40, 20]
        }
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# Enhanced OSM Tile Management (inspired by DearPyGui OSM implementation)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Tile provider registry
# ─────────────────────────────────────────────────────────────────────────────
# Each entry describes a tile source:
#   url         : URL template with {z}/{x}/{y} placeholders. May contain {s}
#                 (subdomain), which is substituted from `subdomains`.
#   url_hidpi   : Optional URL template used when the user enables HiDPI/@2x
#                 rendering. Same placeholders; serves 512px tiles.
#   tile_size   : Native tile size in pixels (almost always 256).
#   max_zoom    : Maximum supported zoom level for this provider.
#   attribution : Short attribution string overlaid on the rendered map.
#   subdomains  : Optional list of subdomains used to substitute `{s}`.
#   labels_url  : Optional URL template for a transparent labels-only layer
#                 that can be composited on top of the basemap.
#   labels_url_hidpi : Optional HiDPI variant of `labels_url`.
#
# Adding a new provider only requires appending an entry here — the rest of
# the rendering pipeline reads everything through this registry.
TILE_PROVIDERS = {
    "OSM Standard": {
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "url_hidpi": None,
        "tile_size": 256,
        "max_zoom": 19,
        "attribution": "© OpenStreetMap contributors",
        "subdomains": None,
        "labels_url": None,
        "labels_url_hidpi": None,
    },
    "CartoDB Positron": {
        "url": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "url_hidpi": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
        "tile_size": 256,
        "max_zoom": 20,
        "attribution": "© OpenStreetMap contributors, © CARTO",
        "subdomains": ["a", "b", "c", "d"],
        "labels_url": "https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png",
        "labels_url_hidpi": "https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}@2x.png",
    },
    "CartoDB Dark Matter": {
        "url": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
        "url_hidpi": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "tile_size": 256,
        "max_zoom": 20,
        "attribution": "© OpenStreetMap contributors, © CARTO",
        "subdomains": ["a", "b", "c", "d"],
        "labels_url": "https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}.png",
        "labels_url_hidpi": "https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}@2x.png",
    },
    "Esri World Imagery": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "url_hidpi": None,
        "tile_size": 256,
        "max_zoom": 19,
        "attribution": "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics",
        "subdomains": None,
        # Esri reference overlay (place names, boundaries)
        "labels_url": "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        "labels_url_hidpi": None,
    },
    "OpenTopoMap": {
        "url": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "url_hidpi": None,
        "tile_size": 256,
        "max_zoom": 17,
        "attribution": "© OpenTopoMap (CC-BY-SA), © OpenStreetMap contributors",
        "subdomains": ["a", "b", "c"],
        "labels_url": None,
        "labels_url_hidpi": None,
    },
    # ── Satellite imagery providers ─────────────────────────────────────────
    # IGN Géoportail (France) — free open-data endpoint, no API key required.
    # Orthophotos for mainland France and overseas territories.
    "IGN Satellite": {
        "url": (
            "https://data.geopf.fr/wmts"
            "?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0"
            "&LAYER=ORTHOIMAGERY.ORTHOPHOTOS"
            "&TILEMATRIXSET=PM"
            "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}"
            "&STYLE=normal&FORMAT=image/jpeg"
        ),
        "url_hidpi": None,
        "tile_size": 256,
        "max_zoom": 20,
        "attribution": "© IGN – Géoportail",
        "subdomains": None,
        "labels_url": None,
        "labels_url_hidpi": None,
    },
    # Bing Maps Virtual Earth aerial imagery (quadkey URL scheme).
    # The ``quadkey`` flag tells ``get_osm_tile`` to convert XYZ → quadkey.
    "Bing Satellite": {
        "url": "https://ecn.t{s}.tiles.virtualearth.net/tiles/a{quadkey}.jpeg?g=1",
        "url_hidpi": None,
        "tile_size": 256,
        "max_zoom": 19,
        "attribution": "© Microsoft, Maxar",
        "subdomains": ["0", "1", "2", "3"],
        "labels_url": None,
        "labels_url_hidpi": None,
        # When True, get_osm_tile converts (z,x,y) → quadkey and substitutes
        # {quadkey} in the URL template instead of using .format(z=…, x=…, y=…).
        "quadkey": True,
    },
    # Yandex Satellite — publicly accessible tile CDN.
    "Yandex Satellite": {
        "url": "https://sat0{s}.maps.yandex.net/tiles?l=sat&z={z}&x={x}&y={y}&scale=1&lang=ru_RU",
        "url_hidpi": None,
        "tile_size": 256,
        "max_zoom": 19,
        "attribution": "© Yandex",
        "subdomains": ["1", "2", "3", "4"],
        "labels_url": None,
        "labels_url_hidpi": None,
    },
}

DEFAULT_PROVIDER = "OSM Standard"

# OSM tile configuration (kept for backward compatibility with existing tests)
TILE_SIZE = 256
OSM_TILE_URL = TILE_PROVIDERS[DEFAULT_PROVIDER]["url"]
OSM_HEADERS = {"User-Agent": "CV_Studio/1.0 (+https://github.com/hackolite/CV_Studio)"}
OSM_CACHE_DIR = os.path.join(tempfile.gettempdir(), '.osm_cache')
os.makedirs(OSM_CACHE_DIR, exist_ok=True)


def get_provider(name):
    """Return the provider entry for `name`, falling back to OSM if missing."""
    return TILE_PROVIDERS.get(name) or TILE_PROVIDERS[DEFAULT_PROVIDER]


def provider_tile_size(provider, hidpi=False):
    """Effective on-canvas tile size: 2× the native size when HiDPI is on
    *and* the provider exposes an HiDPI URL template."""
    base = int(provider.get("tile_size", 256))
    if hidpi and provider.get("url_hidpi"):
        return base * 2
    return base


def _provider_cache_dir(provider_name, hidpi=False):
    """Return (and create) a cache directory namespaced by provider + density.

    Switching providers without a namespace would serve mismatched PNGs from
    cache (e.g. OSM tiles painted under a Positron request), which is why we
    isolate the directories per source.
    """
    safe = "".join(c if c.isalnum() else "_" for c in provider_name)
    suffix = "@2x" if hidpi else ""
    path = os.path.join(OSM_CACHE_DIR, safe + suffix)
    os.makedirs(path, exist_ok=True)
    return path


def _xy_to_quadkey(tile_x, tile_y, zoom):
    """Convert XYZ tile coordinates to a Bing Maps quadkey string.

    Bing Maps uses a quadtree key (quadkey) instead of the standard
    ``{z}/{x}/{y}`` scheme. Each level interleaves one bit from x and one bit
    from y, encoded as a digit 0–3, reading from the most-significant bit.
    """
    quadkey = []
    for i in range(zoom, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if tile_x & mask:
            digit += 1
        if tile_y & mask:
            digit += 2
        quadkey.append(str(digit))
    return "".join(quadkey)


# ─────────────────────────────────────────────────────────────────────────────
# Background tile prefetch
# ─────────────────────────────────────────────────────────────────────────────
# At speeds ≥ 50 km/h the viewport shifts fast enough that uncached tiles on
# the leading edge cause visible stutters. A small thread-pool pre-downloads
# a ring of tiles around the visible area so they are already on disk before
# the renderer needs them.  The pool is kept small (4 workers) so it does not
# starve the tile server or the main thread.
_PREFETCH_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="tile_prefetch"
)
# Extra tile rows/columns to prefetch beyond each edge of the visible grid.
_PREFETCH_MARGIN = 3


def _prefetch_tiles_bg(center_lat, center_lon, zoom, tile_x0, tile_y0,
                       tiles_x, tiles_y, provider_name, hidpi=False):
    """Submit background downloads for tiles in a margin ring outside the
    currently-rendered grid so they are already cached the next time the
    viewport shifts (e.g. at 50 km/h the vehicle moves ~14 m/s).

    Only tiles not already on disk are submitted; already-cached tiles are
    skipped immediately. Fire-and-forget: the caller does not need to await
    the returned futures.
    """
    provider = get_provider(provider_name)
    use_hidpi = bool(hidpi and provider.get("url_hidpi"))
    cache_dir = _provider_cache_dir(provider_name, hidpi=use_hidpi)

    margin = _PREFETCH_MARGIN
    # Extend the rendered grid by ±margin in both axes.
    # x_end / y_end are exclusive upper bounds for range() so we add margin+1
    # to include the last tile of the margin (tile_x0 + tiles_x + margin).
    x_start = tile_x0 - margin
    y_start = tile_y0 - margin
    x_end = tile_x0 + tiles_x + margin + 1
    y_end = tile_y0 + tiles_y + margin + 1

    futures = []
    for ty in range(y_start, y_end):
        for tx in range(x_start, x_end):
            # Skip tiles already covered by the current render pass.
            # assemble_osm_map renders range(tiles_x+1) × range(tiles_y+1),
            # i.e. x in [tile_x0 … tile_x0+tiles_x] and y in [tile_y0 … tile_y0+tiles_y].
            if (tile_x0 <= tx <= tile_x0 + tiles_x and
                    tile_y0 <= ty <= tile_y0 + tiles_y):
                continue
            cache_path = os.path.join(cache_dir, f"{zoom}_{tx}_{ty}.png")
            if os.path.exists(cache_path):
                continue
            try:
                fut = _PREFETCH_EXECUTOR.submit(
                    get_osm_tile, zoom, tx, ty, True, provider_name, use_hidpi
                )
                futures.append(fut)
            except RuntimeError:
                # Executor shut down (e.g. during process exit); ignore.
                pass
    return futures


def lat_lon_to_tile_float(lat, lon, zoom):
    """
    Convert lat/lon to fractional tile coordinates at a given zoom level.
    
    This provides sub-pixel accuracy for tile positioning, allowing precise
    alignment of GPS coordinates on the assembled map.
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        zoom: OSM zoom level (1-19)
    
    Returns:
        Tuple of (tile_x, tile_y) as floats
    """
    n = 2 ** zoom
    fx = (lon + 180.0) / 360.0 * n
    fy = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return fx, fy


def lat_lon_to_pixel_on_map(lat, lon, origin_fx, origin_fy, zoom):
    """
    Convert lat/lon to pixel coordinates on an assembled tile map.
    
    This uses fractional tile coordinates to achieve sub-pixel accuracy,
    ensuring GPS points are positioned exactly where they should be.
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        origin_fx: Fractional tile X coordinate of map's top-left corner
        origin_fy: Fractional tile Y coordinate of map's top-left corner
        zoom: OSM zoom level
    
    Returns:
        Tuple of (pixel_x, pixel_y) as floats
    """
    fx, fy = lat_lon_to_tile_float(lat, lon, zoom)
    px = (fx - origin_fx) * TILE_SIZE
    py = (fy - origin_fy) * TILE_SIZE
    return px, py


def _fit_zoom_for_trace(lats, lons, width_px, height_px,
                        tile_size=256, padding=0.25, min_zoom=3, max_zoom=17):
    """Compute the OSM zoom level that fits all trace points in the viewport.

    Uses the standard Web-Mercator tile formula: at zoom *z* the world is
    ``tile_size × 2^z`` pixels wide, so ``tile_size × 2^z / 360`` pixels
    cover one degree of longitude.  We solve for *z* such that the padded
    bounding box exactly fills the smaller of *width_px* × *height_px*.

    Args:
        lats: Iterable of latitude values.
        lons: Iterable of longitude values.
        width_px: Viewport width in pixels.
        height_px: Viewport height in pixels.
        tile_size: Native tile size in pixels (default 256).
        padding: Fractional padding added around the bounding box (default 25 %).
        min_zoom: Lower bound for the returned zoom (default 3).
        max_zoom: Upper bound for the returned zoom (default 17).

    Returns:
        Integer zoom level in [min_zoom, max_zoom].
    """
    lats = list(lats)
    lons = list(lons)
    if not lats or not lons:
        return max(min_zoom, 10)

    lat_span = max(lats) - min(lats)
    lon_span = max(lons) - min(lons)

    # Ensure a minimum span so a perfectly straight N–S or E–W route does not
    # produce an infinite zoom level.
    lat_span = max(lat_span, 0.001)
    lon_span = max(lon_span, 0.001)

    # Add symmetric padding.
    lat_span *= (1.0 + padding)
    lon_span *= (1.0 + padding)

    # At zoom z: pixels_per_degree_lon = tile_size * 2^z / 360
    # We want  tile_size * 2^z / 360 * lon_span  <=  width_px
    # => z <= log2(width_px * 360 / (tile_size * lon_span))
    z_lon = math.log2(width_px * 360.0 / (tile_size * lon_span))

    # For latitude we use the same cylindrical approximation (treating degrees
    # of latitude as equivalent to degrees of longitude for the purpose of
    # bounding-box fitting, which is accurate for small extents in mid-latitudes).
    z_lat = math.log2(height_px * 360.0 / (tile_size * lat_span))

    zoom = int(min(z_lon, z_lat))
    return max(min_zoom, min(max_zoom, zoom))


def get_osm_tile(z, x, y, use_cache=True, provider_name=None, hidpi=False):
    """
    Download a map tile from the configured provider or retrieve from cache.

    Args:
        z, x, y: Standard XYZ tile coordinates.
        use_cache: Whether to use the on-disk cache (default: True).
        provider_name: Name of the provider in `TILE_PROVIDERS`. Defaults to
            OSM standard for backwards compatibility with callers that still
            pass only (z, x, y).
        hidpi: If True and the provider exposes an `url_hidpi` template, fetch
            the @2x variant (returned image will be 2× the native tile size).

    Returns:
        PIL Image (RGBA), or a gray fallback tile on failure.
    """
    provider_name = provider_name or DEFAULT_PROVIDER
    provider = get_provider(provider_name)
    use_hidpi = bool(hidpi and provider.get("url_hidpi"))
    tile_px = provider_tile_size(provider, hidpi=use_hidpi)

    # Namespaced cache so different providers / densities never collide
    cache_dir = _provider_cache_dir(provider_name, hidpi=use_hidpi)
    cache_path = os.path.join(cache_dir, f"{z}_{x}_{y}.png")

    if use_cache and os.path.exists(cache_path):
        try:
            img = Image.open(cache_path).convert("RGBA")
            return img
        except Exception as e:
            print(f"Map node: Cache read error for tile {z}/{x}/{y}: {e}")
            try:
                os.remove(cache_path)
            except OSError:
                pass

    # Build the URL (optionally substituting {s} with a subdomain)
    url_tpl = provider["url_hidpi"] if use_hidpi else provider["url"]
    subdomains = provider.get("subdomains")
    if subdomains and "{s}" in url_tpl:
        # Deterministic subdomain selection — spreads load and is stable for
        # a given tile so repeated requests can be cached upstream too.
        sub = subdomains[(x + y) % len(subdomains)]
        url_tpl = url_tpl.replace("{s}", sub)

    if provider.get("quadkey"):
        # Bing and similar providers use a quadkey instead of z/x/y.
        qk = _xy_to_quadkey(x, y, z)
        url = url_tpl.replace("{quadkey}", qk)
    else:
        url = url_tpl.format(z=z, x=x, y=y)

    try:
        print(f"Map node: Downloading tile {z}/{x}/{y} from {provider_name}...")
        response = requests.get(url, headers=OSM_HEADERS, timeout=8)
        response.raise_for_status()

        img = Image.open(BytesIO(response.content)).convert("RGBA")

        if use_cache:
            try:
                img.save(cache_path)
            except Exception as e:
                print(f"Map node: Cache write error for tile {z}/{x}/{y}: {e}")

        return img
    except Exception as e:
        print(f"Map node: Download error for tile {z}/{x}/{y}: {e}")
        # Gray fallback at the right pixel size so the canvas math stays valid
        return Image.new("RGBA", (tile_px, tile_px), (180, 180, 180, 255))


def get_labels_tile(z, x, y, use_cache=True, provider_name=None, hidpi=False):
    """
    Download a transparent labels-only tile for the given provider, or None
    if the provider has no labels overlay configured.
    """
    provider = get_provider(provider_name or DEFAULT_PROVIDER)
    labels_url_hidpi = provider.get("labels_url_hidpi")
    use_hidpi = bool(hidpi and labels_url_hidpi)
    labels_url = labels_url_hidpi if use_hidpi else provider.get("labels_url")
    if not labels_url:
        return None

    tile_px = provider_tile_size(provider, hidpi=use_hidpi)

    cache_dir = _provider_cache_dir((provider_name or DEFAULT_PROVIDER) + "__labels", hidpi=use_hidpi)
    cache_path = os.path.join(cache_dir, f"{z}_{x}_{y}.png")

    if use_cache and os.path.exists(cache_path):
        try:
            return Image.open(cache_path).convert("RGBA")
        except Exception:
            try:
                os.remove(cache_path)
            except OSError:
                pass

    subdomains = provider.get("subdomains")
    if subdomains and "{s}" in labels_url:
        sub = subdomains[(x + y) % len(subdomains)]
        labels_url = labels_url.replace("{s}", sub)
    # Labels overlays never use quadkey; always use z/x/y substitution.
    url = labels_url.format(z=z, x=x, y=y)

    try:
        response = requests.get(url, headers=OSM_HEADERS, timeout=8)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        if use_cache:
            try:
                img.save(cache_path)
            except Exception:
                pass
        return img
    except Exception as e:
        print(f"Map node: Labels tile {z}/{x}/{y} fetch failed: {e}")
        # Transparent fallback — composition becomes a no-op
        return Image.new("RGBA", (tile_px, tile_px), (0, 0, 0, 0))


def assemble_osm_map(center_lat, center_lon, zoom, tiles_x=3, tiles_y=3,
                     progress_callback=None, provider_name=None, hidpi=False,
                     with_labels=False):
    """
    Assemble a map centered exactly on the given coordinates.

    Downloads the necessary tiles from the requested provider and composes
    them with sub-pixel accuracy so that the requested center lands on the
    image center. Optionally composites a transparent labels-only layer on
    top (Google-Hybrid style).

    Args:
        center_lat, center_lon: Geographic center of the map.
        zoom: Tile zoom level.
        tiles_x, tiles_y: Tile grid size (in tiles, before the +1 padding).
        progress_callback: Optional fn(current, total, all_cached) for UI.
        provider_name: Entry of `TILE_PROVIDERS` to use; defaults to OSM.
        hidpi: Request @2x tiles when the provider supports it (4× pixels).
        with_labels: When True, fetch and composite the provider's labels
            overlay (no-op if the provider has none).

    Returns:
        Tuple of (pil_image, origin_fx, origin_fy, cache_stats).
        Pixel size of the returned image is `tile_size_px * tiles_x` ×
        `tile_size_px * tiles_y`, where `tile_size_px` depends on HiDPI.
    """
    provider_name = provider_name or DEFAULT_PROVIDER
    provider = get_provider(provider_name)
    use_hidpi = bool(hidpi and provider.get("url_hidpi"))
    tile_px = provider_tile_size(provider, hidpi=use_hidpi)

    # Calculate fractional tile position of center
    fx, fy = lat_lon_to_tile_float(center_lat, center_lon, zoom)

    # Top-left corner of the grid (in fractional tile units)
    origin_fx = fx - tiles_x / 2.0
    origin_fy = fy - tiles_y / 2.0

    tile_x0 = int(math.floor(origin_fx))
    tile_y0 = int(math.floor(origin_fy))

    # Sub-pixel offsets, scaled to the effective on-canvas tile size
    off_x = int((origin_fx - tile_x0) * tile_px)
    off_y = int((origin_fy - tile_y0) * tile_px)

    map_w = tile_px * tiles_x
    map_h = tile_px * tiles_y
    canvas = Image.new("RGBA", (map_w + tile_px, map_h + tile_px))
    labels_canvas = Image.new("RGBA", (map_w + tile_px, map_h + tile_px)) if with_labels else None

    tiles_from_cache = 0
    tiles_downloaded = 0
    total_tiles = (tiles_y + 1) * (tiles_x + 1)

    print(f"Map node: Assembling {total_tiles} tiles at zoom {zoom} "
          f"(provider={provider_name}, hidpi={use_hidpi})...")

    # Count downloads needed (provider-aware cache directory)
    base_cache_dir = _provider_cache_dir(provider_name, hidpi=use_hidpi)
    tiles_need_download = 0
    for row in range(tiles_y + 1):
        for col in range(tiles_x + 1):
            z, x, y = zoom, tile_x0 + col, tile_y0 + row
            cache_path = os.path.join(base_cache_dir, f"{z}_{x}_{y}.png")
            if not os.path.exists(cache_path):
                tiles_need_download += 1

    if tiles_need_download == 0 and progress_callback:
        progress_callback(0, 0, True)

    tiles_downloaded_so_far = 0
    for row in range(tiles_y + 1):
        for col in range(tiles_x + 1):
            z, x, y = zoom, tile_x0 + col, tile_y0 + row
            cache_path = os.path.join(base_cache_dir, f"{z}_{x}_{y}.png")
            was_cached = os.path.exists(cache_path)

            tile = get_osm_tile(z, x, y, provider_name=provider_name, hidpi=use_hidpi)
            if tile is not None:
                canvas.paste(tile, (col * tile_px, row * tile_px))
                if was_cached:
                    tiles_from_cache += 1
                else:
                    tiles_downloaded += 1
                    tiles_downloaded_so_far += 1
                    if progress_callback:
                        progress_callback(tiles_downloaded_so_far, tiles_need_download, False)

            # Optional labels overlay (transparent PNG) – composited at the end
            if labels_canvas is not None:
                lab = get_labels_tile(z, x, y, provider_name=provider_name, hidpi=use_hidpi)
                if lab is not None:
                    # Normalize labels tile to the same pixel size as the base
                    # tile to handle providers without HiDPI labels.
                    if lab.size != (tile_px, tile_px):
                        lab = lab.resize((tile_px, tile_px), Image.LANCZOS)
                    labels_canvas.paste(lab, (col * tile_px, row * tile_px), lab)

    print(f"Map node: Tile cache summary - {tiles_from_cache} from cache, "
          f"{tiles_downloaded} downloaded, {total_tiles} total")

    final_img = canvas.crop((off_x, off_y, off_x + map_w, off_y + map_h))
    if labels_canvas is not None:
        labels_crop = labels_canvas.crop((off_x, off_y, off_x + map_w, off_y + map_h))
        final_img = Image.alpha_composite(final_img, labels_crop)

    cache_stats = {
        'cached': tiles_from_cache,
        'downloaded': tiles_downloaded,
        'total': total_tiles,
        'provider': provider_name,
        'hidpi': use_hidpi,
        'tile_px': tile_px,
    }

    # Background-prefetch a ring of tiles beyond the rendered grid so that
    # movement at high speeds (≥ 50 km/h) does not cause stutters when
    # the viewport shifts to a neighbouring tile row/column.
    _prefetch_tiles_bg(
        center_lat, center_lon, zoom,
        tile_x0, tile_y0, tiles_x, tiles_y,
        provider_name, hidpi=use_hidpi,
    )

    return final_img, origin_fx, origin_fy, cache_stats


class FactoryNode:
    node_label = 'Map'
    node_tag = 'Map'
    

    def __init__(self):
        pass


    def add_node(
        self,
        parent,
        node_id,
        pos=[0, 0],
        opencv_setting_dict=None,
        callback=None,
    ):

        node = Node()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        # Map controls
        node.tag_node_zoom_name = node.tag_node_name + ':Zoom'
        node.tag_node_zoom_value_name = node.tag_node_name + ':ZoomValue'
        node.tag_node_size_name = node.tag_node_name + ':MapSize'
        node.tag_node_size_value_name = node.tag_node_name + ':MapSizeValue'
        node.tag_node_cache_name = node.tag_node_name + ':UseCache'
        node.tag_node_cache_value_name = node.tag_node_name + ':UseCacheValue'
        node.tag_node_status_name = node.tag_node_name + ':Status'
        node.tag_node_status_value_name = node.tag_node_name + ':StatusValue'
        # Pan controls
        node.tag_node_pan_x_value_name = node.tag_node_name + ':PanXValue'
        node.tag_node_pan_y_value_name = node.tag_node_name + ':PanYValue'
        # Download progress bar
        node.tag_node_progress_name = node.tag_node_name + ':Progress'
        # Visual / provider controls
        node.tag_node_provider_value_name = node.tag_node_name + ':ProviderValue'
        node.tag_node_hidpi_value_name = node.tag_node_name + ':HiDPIValue'
        node.tag_node_labels_value_name = node.tag_node_name + ':LabelsValue'
        # Metric (colour-by) selector + persistent trace toggle
        node.tag_node_metric_value_name = node.tag_node_name + ':MetricValue'
        node.tag_node_trace_value_name = node.tag_node_name + ':TraceValue'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        # Create initial preview image
        black_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):

            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='JSON with lat/lon',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Zoom slider
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_int(
                    tag=node.tag_node_zoom_value_name,
                    label="",
                    width=small_window_w,
                    default_value=10,
                    min_value=1,
                    max_value=20,
                    clamped=True,
                )

            # Tile provider (style) selector
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_provider_value_name,
                    label="",
                    items=list(TILE_PROVIDERS.keys()),
                    default_value=DEFAULT_PROVIDER,
                    width=small_window_w,
                )

            # HiDPI / @2x tiles
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_hidpi_value_name,
                    label="HiDPI tiles (@2x)",
                    default_value=False,
                )

            # Labels overlay (transparent labels layer composited on top)
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_labels_value_name,
                    label="Labels overlay",
                    default_value=False,
                )

            # Metric (colour-by) selector. The items list is refreshed on
            # every update() from the keys actually present in the input
            # JSON. Picking a metric colours the markers (and persistent
            # trace) on a green→yellow→orange→red gradient over [0, 1].
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_metric_value_name,
                    label="Metric",
                    items=[METRIC_NONE],
                    default_value=METRIC_NONE,
                    width=small_window_w - 60,
                )

            # Trace toggle: when on, every "moving" point received is
            # appended to a persistent history that is drawn as a coloured
            # polyline. When the trip ends (no more moving point in the
            # incoming data) the map auto-fits to show the whole trace.
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_trace_value_name,
                    label="Trace",
                    default_value=False,
                    callback=lambda s, a, u: Node.on_trace_toggle(s, a, u),
                    user_data=(node, node_id),
                )

            # Map size slider (for bounding box adjustment)
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_size_value_name,
                    label="",
                    width=small_window_w,
                    default_value=1.0,
                    min_value=0.5,
                    max_value=5.0,
                    clamped=True,
                )

            # Pan X slider (horizontal translation: left/right)
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_pan_x_value_name,
                    label="",
                    width=small_window_w,
                    default_value=0.0,
                    min_value=-1.0,
                    max_value=1.0,
                    clamped=True,
                )

            # Pan Y slider (vertical translation: up/down)
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_pan_y_value_name,
                    label="",
                    width=small_window_w,
                    default_value=0.0,
                    min_value=-1.0,
                    max_value=1.0,
                    clamped=True,
                )

            # Cache checkbox
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_cache_value_name,
                    label="Cache Maps",
                    default_value=True,
                )

            # Download progress bar
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_progress_bar(
                    label="Download Progress",
                    tag=node.tag_node_progress_name,
                    default_value=0.0,
                    overlay="",
                    width=small_window_w,
                    show=False,  # Initially hidden, will show only when downloading
                )

            # Status text
            with dpg.node_attribute(
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_status_value_name,
                    default_value='No data',
                )

        return node


class Node(DpgNodeABC):
    _ver = "0.0.1"
    node_label = 'Map'
    node_tag = 'Map'

    TYPE_BOOLEAN = "BOOLEAN"
    TYPE_TEXT = "TEXT"
    TYPE_IMAGE = "IMAGE"
    TYPE_FLOAT = "FLOAT"
    TYPE_INT = "INT"
    TYPE_TIME_MS = "TIME_MS"
    TYPE_JSON = "JSON"

    def __init__(self):
        self.last_map_path = None
        self.point_data = []
        self._opencv_setting_dict = None
        # contextily handles its own caching internally
        # We keep these for compatibility with tests
        self.cached_tiles = {}
        self.cache_center = None
        self.cache_radius = 2
        # Pan offset tracking (in meters, Web Mercator)
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        # Persistent trace history of moving points: list of dicts with
        # ``lat``, ``lon`` and ``metric`` (float in [0, 1] or None).
        self._trace_history = []
        # Whether we already auto-fitted the view after a trip ended. Used
        # to avoid permanently locking the view when the user pans/zooms
        # post-trip.
        self._trace_fitted = False
        # Tracks whether the previous frame contained a moving point. The
        # transition "had moving → has none" marks the end of a trip and
        # triggers the auto-fit.
        self._had_moving_previously = False


    @staticmethod
    def on_trace_toggle(sender, app_data, user_data):
        """Reset trace history whenever the user toggles the Trace switch."""
        node, _node_id = user_data
        node._trace_history = []
        node._trace_fitted = False
        node._had_moving_previously = False


    @staticmethod
    def lat_lon_to_web_mercator(lat, lon):
        """
        Convert latitude/longitude to Web Mercator coordinates (EPSG:3857).
        This is the projection system used by most web mapping services.
        """
        # Earth radius in meters
        R = 6378137.0
        
        # Convert to radians
        lon_rad = math.radians(lon)
        lat_rad = math.radians(lat)
        
        # Web Mercator formulas
        x = R * lon_rad
        y = R * math.log(math.tan(math.pi / 4 + lat_rad / 2))
        
        return x, y


    @staticmethod
    def web_mercator_to_lat_lon(x, y):
        """
        Convert Web Mercator coordinates (EPSG:3857) to latitude/longitude.
        """
        # Earth radius in meters
        R = 6378137.0
        
        # Inverse Web Mercator formulas
        lon = math.degrees(x / R)
        lat = math.degrees(2 * math.atan(math.exp(y / R)) - math.pi / 2)
        
        return lat, lon


    def _calculate_extent(self, points, zoom_level=None, size_factor=1.0, pan_offset_x=0.0, pan_offset_y=0.0):
        """
        Calculate the bounding box extent in Web Mercator coordinates.
        
        Args:
            points: List of points with 'lat' and 'lon' keys
            zoom_level: Optional zoom level (not used, kept for compatibility)
            size_factor: Factor to scale the bounding box (default 1.0)
                        Values < 1.0 zoom in (smaller view area)
                        Values > 1.0 zoom out (larger view area)
            pan_offset_x: Horizontal pan offset as fraction of range (-1.0 to 1.0)
            pan_offset_y: Vertical pan offset as fraction of range (-1.0 to 1.0)
        
        Returns:
            Tuple of (west, south, east, north) in Web Mercator coordinates
        """
        if not points:
            # Default view: world centered at (0, 0)
            return (-20037508.34, -20037508.34, 20037508.34, 20037508.34)
        
        # Convert all points to Web Mercator
        mercator_coords = [self.lat_lon_to_web_mercator(p['lat'], p['lon']) for p in points]
        
        # Get bounding box
        xs = [coord[0] for coord in mercator_coords]
        ys = [coord[1] for coord in mercator_coords]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        # Calculate center point
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # Get range
        x_range = max_x - min_x
        y_range = max_y - min_y
        
        # Ensure minimum range for single points or very close points
        if x_range < MIN_RANGE_METERS:  # Less than 1km
            x_range = DEFAULT_RANGE_METERS  # Use 10km as minimum range
        if y_range < MIN_RANGE_METERS:
            y_range = DEFAULT_RANGE_METERS
        
        # Add base padding (15%)
        x_range_padded = x_range * (1.0 + MAP_PADDING_FACTOR * 2)
        y_range_padded = y_range * (1.0 + MAP_PADDING_FACTOR * 2)
        
        # Apply size factor: scale the range around center
        # size_factor < 1.0 = zoom in (smaller range)
        # size_factor > 1.0 = zoom out (larger range)
        final_x_range = x_range_padded * size_factor
        final_y_range = y_range_padded * size_factor
        
        # Calculate extent from center
        west = center_x - final_x_range / 2
        east = center_x + final_x_range / 2
        south = center_y - final_y_range / 2
        north = center_y + final_y_range / 2
        
        # Apply pan offsets (as a fraction of the final range)
        pan_x_meters = pan_offset_x * final_x_range
        pan_y_meters = pan_offset_y * final_y_range
        
        west += pan_x_meters
        east += pan_x_meters
        south += pan_y_meters
        north += pan_y_meters
        
        return (west, south, east, north)


    @staticmethod
    def _metric_value(point, metric_key):
        """Return a float in [0, 1] or ``None`` for the metric key on a point."""
        if not metric_key or metric_key == METRIC_NONE or not isinstance(point, dict):
            return None
        if metric_key not in point:
            return None
        try:
            v = float(point[metric_key])
        except (TypeError, ValueError):
            return None
        if math.isnan(v):
            return None
        return max(0.0, min(1.0, v))

    def _record_trace(self, points, metric_key, trace_enabled):
        """Append moving points to the trace history and report trip phase.

        Returns a tuple ``(end_of_trip, history_snapshot)`` where
        ``end_of_trip`` is True when the previous frame contained a moving
        point and the current frame does not, signalling the end of the
        recorded trip. ``history_snapshot`` is a (possibly empty) copy of
        the persistent trace ready to be drawn / used for an auto-fit.
        """
        if not trace_enabled:
            # Trace is off: drop the history so toggling it back on starts
            # from a fresh trip.
            self._trace_history = []
            self._trace_fitted = False
            self._had_moving_previously = False
            return False, []

        has_moving = False
        for pt in points or ():
            if not isinstance(pt, dict) or not pt.get('is_moving'):
                continue
            has_moving = True
            try:
                lat = float(pt['lat'])
                lon = float(pt['lon'])
            except (TypeError, ValueError, KeyError):
                continue
            entry = {
                'lat': lat,
                'lon': lon,
                'metric': self._metric_value(pt, metric_key),
            }
            # Avoid recording exact duplicates back-to-back (the trip
            # might emit the same coordinate while paused).
            if self._trace_history:
                last = self._trace_history[-1]
                if last['lat'] == lat and last['lon'] == lon:
                    last['metric'] = entry['metric']
                    self._had_moving_previously = True
                    return False, list(self._trace_history)
            self._trace_history.append(entry)
            # A new moving point arrived: the trip is in progress, so the
            # next "no moving point" frame will count as a new end-of-trip.
            self._trace_fitted = False

        end_of_trip = self._had_moving_previously and not has_moving and len(self._trace_history) >= 2
        self._had_moving_previously = has_moving
        return end_of_trip, list(self._trace_history)


    @classmethod
    def create_for_testing(cls):
        """Factory method for creating node instances in tests"""
        node = object.__new__(cls)
        node._opencv_setting_dict = {}
        node.last_map_path = None
        node.point_data = []
        node.cached_tiles = {}
        node.cache_center = None
        node.cache_radius = 2
        node.pan_offset_x = 0.0
        node.pan_offset_y = 0.0
        node._trace_history = []
        node._trace_fitted = False
        node._had_moving_previously = False
        return node


    def _render_map_with_trace(
        self,
        points,
        small_window_w, small_window_h,
        tag_node_zoom_value_name,
        tag_node_size_value_name,
        tag_node_cache_value_name,
        tag_node_pan_x_value_name,
        tag_node_pan_y_value_name,
        tag_node_provider_value_name,
        tag_node_hidpi_value_name,
        tag_node_labels_value_name,
        tag_node_metric_value_name,
        tag_node_trace_value_name,
        tag_node_progress_name,
        tag_node_status_value_name,
    ):
        """Single rendering entry point used by both JSON input branches.

        Reads the Metric / Trace controls, updates the trace history, decides
        which points to render and whether the trip just ended, then calls
        the underlying tile renderer with the metric/trace context.
        """
        zoom_level = dpg_get_value(tag_node_zoom_value_name)
        size_factor = dpg_get_value(tag_node_size_value_name)
        use_cache = dpg_get_value(tag_node_cache_value_name)
        pan_x = dpg_get_value(tag_node_pan_x_value_name)
        pan_y = dpg_get_value(tag_node_pan_y_value_name)
        provider_name = dpg_get_value(tag_node_provider_value_name) or DEFAULT_PROVIDER
        hidpi = bool(dpg_get_value(tag_node_hidpi_value_name))
        labels_overlay = bool(dpg_get_value(tag_node_labels_value_name))
        metric_key = dpg_get_value(tag_node_metric_value_name) or METRIC_NONE
        trace_enabled = bool(dpg_get_value(tag_node_trace_value_name))
        if use_cache is None:
            use_cache = True
        if pan_x is None:
            pan_x = 0.0
        if pan_y is None:
            pan_y = 0.0

        # Refresh the metric combo with the keys actually present on the
        # current input (numeric values in [0, 1]).
        try:
            available = [METRIC_NONE] + _metric_candidate_keys(points)
            dpg.configure_item(tag_node_metric_value_name, items=available)
            if metric_key not in available:
                metric_key = METRIC_NONE
                dpg_set_value(tag_node_metric_value_name, METRIC_NONE)
        except Exception:
            pass

        # Update trace history and detect end-of-trip transitions.
        end_of_trip, trace_history = self._record_trace(
            points, metric_key, trace_enabled,
        )

        # Decide which points drive the bbox / are drawn as markers.
        render_points = points
        if end_of_trip and trace_history and not self._trace_fitted:
            # Trip just ended: auto-fit to the full recorded trace by
            # using the trace as the points for the bbox computation.
            print(
                f"Map node: Trip ended, auto-fitting view to {len(trace_history)} "
                f"trace point(s)"
            )
            render_points = [{
                'lat': h['lat'],
                'lon': h['lon'],
                'name': '',
                'info': '',
            } for h in trace_history]

            # Auto-zoom: compute the OSM zoom level that fits the whole
            # trace in the viewport so the map zooms out from the live-
            # tracking view to show the full route start-to-end.
            trace_lats = [h['lat'] for h in trace_history]
            trace_lons = [h['lon'] for h in trace_history]
            fit_zoom = _fit_zoom_for_trace(
                trace_lats, trace_lons,
                small_window_w, small_window_h,
            )
            try:
                dpg_set_value(tag_node_zoom_value_name, fit_zoom)
            except Exception:
                pass
            zoom_level = fit_zoom

            self._trace_fitted = True

        if not render_points:
            return None, None

        return self._create_preview_image(
            render_points, small_window_w, small_window_h,
            zoom_level, size_factor, pan_x, pan_y, tag_node_progress_name,
            provider_name=provider_name, hidpi=hidpi, labels_overlay=labels_overlay,
            metric_key=metric_key, trace_history=trace_history,
        )


    def update(
        self,
        node_id: int,
        connection_list: list[list[str]],
        node_image_dict: dict[str, any],
        node_result_dict: dict[str, any],
        node_audio_dict: dict[str, any],
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_input01_value_name = tag_node_name + ':' + self.TYPE_JSON + ':Input01Value'
        tag_node_output01_value_name = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        tag_node_output02_value_name = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        tag_node_zoom_value_name = tag_node_name + ':ZoomValue'
        tag_node_size_value_name = tag_node_name + ':MapSizeValue'
        tag_node_cache_value_name = tag_node_name + ':UseCacheValue'
        tag_node_status_value_name = tag_node_name + ':StatusValue'
        tag_node_pan_x_value_name = tag_node_name + ':PanXValue'
        tag_node_pan_y_value_name = tag_node_name + ':PanYValue'
        tag_node_progress_name = tag_node_name + ':Progress'
        tag_node_provider_value_name = tag_node_name + ':ProviderValue'
        tag_node_hidpi_value_name = tag_node_name + ':HiDPIValue'
        tag_node_labels_value_name = tag_node_name + ':LabelsValue'
        tag_node_metric_value_name = tag_node_name + ':MetricValue'
        tag_node_trace_value_name = tag_node_name + ':TraceValue'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        if use_pref_counter:
            start_time = time.perf_counter()

        # Find connected source for JSON data
        connection_info_src = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_JSON:
                connection_info_src = connection_info[0]
                connection_info_src = connection_info_src.split(':')[:2]
                connection_info_src = ':'.join(connection_info_src)
                break
        
        # Get input JSON data from node_result_dict (correct approach)
        input_value = node_result_dict.get(connection_info_src, None)
        
        # Log received data for debugging
        if connection_info_src:
            if input_value is not None:
                print(f"Map node: Received data from {connection_info_src}")
                print(f"Map node: Data type: {type(input_value).__name__}")
                if isinstance(input_value, (list, dict)):
                    try:
                        import json as json_module
                        json_str = json_module.dumps(input_value, indent=2)
                        print(f"Map node: JSON data (first 500 chars):\n{json_str[:500]}")
                    except Exception as e:
                        print(f"Map node: Could not serialize data: {e}")
                elif isinstance(input_value, str):
                    print(f"Map node: String data (length {len(input_value)}): {input_value[:100]}")
            else:
                print(f"Map node: No data received from {connection_info_src}")
        
        # Initialize output image
        preview_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
        
        if input_value is not None:
            # Reset the no-data flag since we have data now
            if hasattr(self, '_no_data_logged'):
                self._no_data_logged = False
                
            try:
                # Parse JSON data
                if isinstance(input_value, str):
                    # Handle empty or whitespace-only strings
                    if not input_value.strip():
                        print("Map node: Received empty JSON string")
                        dpg_set_value(tag_node_status_value_name, "Waiting for data...")
                        # Skip further processing for empty input
                    else:
                        print(f"Map node: Received JSON string (length: {len(input_value)})")
                        data = json.loads(input_value)
                        
                        # Log the structure of received data
                        if isinstance(data, dict):
                            print(f"Map node: JSON contains keys: {list(data.keys())}")
                            if 'boats' in data:
                                print(f"Map node: Found {len(data.get('boats', []))} boats in data")
                        elif isinstance(data, list):
                            print(f"Map node: JSON is a list with {len(data)} items")

                        # Extract points with latitude and longitude
                        points = self._extract_lat_lon_from_json(data)
                        
                        if points:
                            print(f"Map node: Extracted {len(points)} points with lat/lon")
                            self.point_data = points

                            result = self._render_map_with_trace(
                                points, small_window_w, small_window_h,
                                tag_node_zoom_value_name,
                                tag_node_size_value_name,
                                tag_node_cache_value_name,
                                tag_node_pan_x_value_name,
                                tag_node_pan_y_value_name,
                                tag_node_provider_value_name,
                                tag_node_hidpi_value_name,
                                tag_node_labels_value_name,
                                tag_node_metric_value_name,
                                tag_node_trace_value_name,
                                tag_node_progress_name,
                                tag_node_status_value_name,
                            )
                            if result is not None and result[0] is not None:
                                preview_image, cache_stats = result

                            # Update status with empty text (labels removed as requested)
                            dpg_set_value(tag_node_status_value_name, "")
                        else:
                            # No points in the current frame, but if trace is
                            # on and history exists this can mark the end of
                            # the trip → still call the renderer so the
                            # auto-fit kicks in.
                            result = self._render_map_with_trace(
                                [], small_window_w, small_window_h,
                                tag_node_zoom_value_name,
                                tag_node_size_value_name,
                                tag_node_cache_value_name,
                                tag_node_pan_x_value_name,
                                tag_node_pan_y_value_name,
                                tag_node_provider_value_name,
                                tag_node_hidpi_value_name,
                                tag_node_labels_value_name,
                                tag_node_metric_value_name,
                                tag_node_trace_value_name,
                                tag_node_progress_name,
                                tag_node_status_value_name,
                            )
                            if result is not None and result[0] is not None:
                                preview_image, cache_stats = result
                                dpg_set_value(tag_node_status_value_name, "")
                            else:
                                status_msg = "No lat/lon in data"
                                print(f"Map node: {status_msg}")
                                dpg_set_value(tag_node_status_value_name, status_msg)
                else:
                    print(f"Map node: Received JSON object (type: {type(input_value).__name__})")
                    data = input_value

                    # Log the structure of received data
                    if isinstance(data, dict):
                        print(f"Map node: JSON contains keys: {list(data.keys())}")
                        if 'boats' in data:
                            print(f"Map node: Found {len(data.get('boats', []))} boats in data")
                    elif isinstance(data, list):
                        print(f"Map node: JSON is a list with {len(data)} items")

                    # Extract points with latitude and longitude
                    points = self._extract_lat_lon_from_json(data)

                    if points:
                        print(f"Map node: Extracted {len(points)} points with lat/lon")
                        self.point_data = points

                        result = self._render_map_with_trace(
                            points, small_window_w, small_window_h,
                            tag_node_zoom_value_name,
                            tag_node_size_value_name,
                            tag_node_cache_value_name,
                            tag_node_pan_x_value_name,
                            tag_node_pan_y_value_name,
                            tag_node_provider_value_name,
                            tag_node_hidpi_value_name,
                            tag_node_labels_value_name,
                            tag_node_metric_value_name,
                            tag_node_trace_value_name,
                            tag_node_progress_name,
                            tag_node_status_value_name,
                        )
                        if result is not None and result[0] is not None:
                            preview_image, cache_stats = result

                        # Update status with empty text (labels removed as requested)
                        dpg_set_value(tag_node_status_value_name, "")
                    else:
                        # Empty frame: may trigger end-of-trip auto-fit.
                        result = self._render_map_with_trace(
                            [], small_window_w, small_window_h,
                            tag_node_zoom_value_name,
                            tag_node_size_value_name,
                            tag_node_cache_value_name,
                            tag_node_pan_x_value_name,
                            tag_node_pan_y_value_name,
                            tag_node_provider_value_name,
                            tag_node_hidpi_value_name,
                            tag_node_labels_value_name,
                            tag_node_metric_value_name,
                            tag_node_trace_value_name,
                            tag_node_progress_name,
                            tag_node_status_value_name,
                        )
                        if result is not None and result[0] is not None:
                            preview_image, cache_stats = result
                            dpg_set_value(tag_node_status_value_name, "")
                        else:
                            status_msg = "No lat/lon in data"
                            print(f"Map node: {status_msg}")
                            dpg_set_value(tag_node_status_value_name, status_msg)
                    
            except json.JSONDecodeError as e:
                error_msg = f"JSON parse error: {str(e)[:60]}"
                print(f"Map node: {error_msg}")
                dpg_set_value(tag_node_status_value_name, error_msg)
            except Exception as e:
                error_msg = f"Error: {str(e)[:40]}"
                print(f"Map node: Error processing data: {e}")
                dpg_set_value(tag_node_status_value_name, error_msg)
        else:
            # No input data
            if not hasattr(self, '_no_data_logged') or not self._no_data_logged:
                print("Map node: Waiting for input data...")
                self._no_data_logged = True

        # Convert preview to DPG texture and update
        preview_texture = self.convert_cv_to_dpg(
            preview_image,
            small_window_w,
            small_window_h,
        )
        dpg_set_value(tag_node_output01_value_name, preview_texture)

        if use_pref_counter:
            elapsed_time = (time.perf_counter() - start_time) * 1000
            dpg_set_value(tag_node_output02_value_name, elapsed_time)

        return {"image": preview_image, "json": None, "audio": None}




    def _extract_lat_lon_from_json(self, data):
        """Extract latitude and longitude from JSON data.

        Any extra keys present on each input record are preserved on the
        returned point dictionaries (e.g. ``is_moving``, ``secousses`` or any
        other numeric metric the user might want to colour-code on the map).
        """
        points = []

        def _make_point(src, lat_key, lon_key):
            """Build a point dict, copying any extra keys verbatim."""
            try:
                lat = float(src[lat_key])
                lon = float(src[lon_key])
            except (TypeError, ValueError, KeyError):
                return None
            pt = {
                'lat': lat,
                'lon': lon,
                'name': src.get('name', src.get('ship_name', 'Point')),
                'info': src.get('info', src.get('mmsi', '')),
            }
            # Preserve all remaining keys (metrics, flags, etc.) so the
            # Map node can offer them as colour-mapped metrics.
            for k, v in src.items():
                if k in (lat_key, lon_key, 'name', 'ship_name'):
                    continue
                pt.setdefault(k, v)
            return pt

        # Handle different JSON structures
        if isinstance(data, dict):
            # Check for AIS boat data structure
            if 'boats' in data:
                for boat in data['boats']:
                    if isinstance(boat, dict) and 'latitude' in boat and 'longitude' in boat:
                        pt = _make_point(boat, 'latitude', 'longitude')
                        if pt is not None:
                            points.append(pt)
            # Check for direct lat/lon in dict
            elif 'latitude' in data and 'longitude' in data:
                pt = _make_point(data, 'latitude', 'longitude')
                if pt is not None:
                    points.append(pt)
            elif 'lat' in data and 'lon' in data:
                pt = _make_point(data, 'lat', 'lon')
                if pt is not None:
                    points.append(pt)
            # Check for nested data
            else:
                for key, value in data.items():
                    if isinstance(value, (list, dict)):
                        points.extend(self._extract_lat_lon_from_json(value))

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    if 'latitude' in item and 'longitude' in item:
                        pt = _make_point(item, 'latitude', 'longitude')
                        if pt is not None:
                            points.append(pt)
                    elif 'lat' in item and 'lon' in item:
                        pt = _make_point(item, 'lat', 'lon')
                        if pt is not None:
                            points.append(pt)

        return points


    def _generate_cache_key(self, points, zoom_level, size_factor):
        """
        Generate a cache key based on map parameters.
        
        Args:
            points: List of coordinate points
            zoom_level: Map zoom level
            size_factor: View size factor
            
        Returns:
            Hash string to use as cache key
        """
        # Create a string representation of key parameters
        # Sort points to ensure consistent ordering
        sorted_points = sorted(points, key=lambda p: (p['lat'], p['lon']))
        
        # Build key from essential data
        key_data = {
            'points': [(p['lat'], p['lon']) for p in sorted_points[:100]],  # Limit to first 100 points
            'zoom': zoom_level,
            'size': round(size_factor, 2),
        }
        
        # Generate hash
        key_str = json.dumps(key_data, sort_keys=True)
        cache_key = hashlib.md5(key_str.encode()).hexdigest()
        
        return cache_key

    # HTML map generation disabled - functionality removed
    # def _generate_map(self, points, zoom_level, size_factor, use_cache=True):
    #     """Generate an HTML map with Leaflet using folium with optional caching"""
    #     # This method has been disabled to remove HTML rendering functionality


    def _create_preview_image(self, points, width, height, zoom_level=10, size_factor=1.0, pan_x=0.0, pan_y=0.0, progress_tag=None,
                              provider_name=None, hidpi=False, labels_overlay=False,
                              metric_key=METRIC_NONE, trace_history=None):
        """
        Create a map visualization image using enhanced OSM tile rendering.
        
        This method:
        1. Tries direct OSM tile assembly with sub-pixel accuracy (preferred)
        2. Falls back to contextily rendering if direct method fails
        3. Falls back to matplotlib-only rendering if both fail
        
        Args:
            points: List of points with 'lat' and 'lon' keys
            width: Width of output image in pixels
            height: Height of output image in pixels
            zoom_level: OSM tile zoom level (1-20)
            size_factor: View size factor (0.5-5.0)
            pan_x: Horizontal pan offset (-1.0 to 1.0)
            pan_y: Vertical pan offset (-1.0 to 1.0)
            progress_tag: Optional DearPyGUI tag for progress bar updates
            provider_name: Tile provider entry (key of TILE_PROVIDERS)
            hidpi: When True, request @2x tiles where supported (4x pixels)
            labels_overlay: When True, composite the provider's labels layer

        Returns:
            Tuple of (numpy array in BGR format, cache_stats dict) or (numpy array, None) for fallbacks
        """
        if not points:
            preview = np.zeros((height, width, 3), dtype=np.uint8)
            return preview, None
        
        print(f"Map node: Creating preview with zoom={zoom_level}, size={size_factor}, provider={provider_name}, hidpi={hidpi}")
        
        # Try direct OSM tile rendering first (enhanced method)
        try:
            return self._render_with_direct_osm_tiles(
                points, width, height, zoom_level, size_factor, pan_x, pan_y, progress_tag,
                provider_name=provider_name, hidpi=hidpi, labels_overlay=labels_overlay,
                metric_key=metric_key, trace_history=trace_history,
            )
        except Exception as e:
            print(f"Map node: Direct OSM rendering failed: {e}")
            traceback.print_exc()
            print("Map node: Falling back to contextily rendering")
        
        # Try contextily rendering as fallback
        if CONTEXTILY_AVAILABLE:
            try:
                return self._render_with_contextily(points, width, height, zoom_level, size_factor, pan_x, pan_y), None
            except Exception as e:
                print(f"Map node: Error rendering with contextily: {e}")
                traceback.print_exc()
                print("Map node: Falling back to matplotlib-only rendering")
        
        # Final fallback to matplotlib rendering without basemap
        return self._render_with_matplotlib(points, width, height), None


    def _render_with_direct_osm_tiles(self, points, width, height, zoom_level=10, size_factor=1.0, pan_x=0.0, pan_y=0.0, progress_tag=None,
                                      provider_name=None, hidpi=False, labels_overlay=False,
                                      metric_key=METRIC_NONE, trace_history=None):
        """
        Enhanced map rendering: direct tile download + sub-pixel assembly,
        provider-aware, optional HiDPI / labels overlay, anti-aliased markers
        and trail, final Lanczos downscale for clean detail.

        Strategy for higher visual fidelity:
          * Tiles are fetched at the provider's native size (256 px) or @2x
            (512 px) when HiDPI is enabled.
          * Markers and the trail polyline are drawn with Pillow's
            anti-aliased ImageDraw at the tile-native resolution and then
            composited on the basemap (no jagged cv2 circles).
          * The final crop to (width, height) goes through PIL.Image.LANCZOS
            (high-quality resampling), instead of cv2.INTER_AREA.

        Returns:
            Tuple of (numpy array in BGR format, cache_stats dict)
        """
        if not points:
            img = np.zeros((height, width, 3), dtype=np.uint8)
            img[:] = (224, 216, 173)  # Light blue-gray
            return img, None

        provider_name = provider_name or DEFAULT_PROVIDER
        provider = get_provider(provider_name)

        # Effective on-canvas tile size for the chosen provider / density
        tile_px = provider_tile_size(provider, hidpi=hidpi)
        # Clamp the requested zoom to whatever the provider actually supports
        zoom_level = max(1, min(int(zoom_level), int(provider.get("max_zoom", 19))))

        try:
            # Center on the average GPS location
            lats = [p['lat'] for p in points]
            lons = [p['lon'] for p in points]
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)

            # Pan offsets — same heuristic as before, kept for stability
            lat_range = max(lats) - min(lats) if len(set(lats)) > 1 else 0.01
            lon_range = max(lons) - min(lons) if len(set(lons)) > 1 else 0.01
            center_lat -= pan_y * lat_range * 0.5
            center_lon += pan_x * lon_range * 0.5

            # Tile grid sized to cover at least the target viewport. At HiDPI
            # the on-canvas tile is twice as big so we need fewer of them.
            tiles_x = max(3, (width + tile_px - 1) // tile_px)
            tiles_y = max(3, (height + tile_px - 1) // tile_px)

            print(f"Map node (direct OSM): Assembling {tiles_x}x{tiles_y} tiles "
                  f"at zoom {zoom_level} (provider={provider_name}, hidpi={hidpi}, tile_px={tile_px})")
            print(f"Map node (direct OSM): Center: ({center_lat:.6f}, {center_lon:.6f})")

            def update_progress(current, total, from_cache):
                if progress_tag and dpg.does_item_exist(progress_tag):
                    if from_cache:
                        dpg.hide_item(progress_tag)
                    elif total > 0:
                        progress = current / total
                        dpg.set_value(progress_tag, progress)
                        dpg.configure_item(progress_tag, overlay=f"Downloading: {current}/{total} tiles")
                        dpg.show_item(progress_tag)

            pil_map, origin_fx, origin_fy, cache_stats = assemble_osm_map(
                center_lat, center_lon, zoom_level, tiles_x, tiles_y,
                update_progress,
                provider_name=provider_name, hidpi=hidpi,
                with_labels=labels_overlay,
            )

            # Ensure RGBA so the marker overlay alpha-composites correctly
            if pil_map.mode != "RGBA":
                pil_map = pil_map.convert("RGBA")

            # Anti-aliased markers + trail drawn on a transparent overlay.
            # We do this at the tile-native resolution and only downscale at
            # the very end, which acts as supersampling (SSAA).
            map_w, map_h = pil_map.size

            if PIL_DRAW_AVAILABLE:
                overlay_img = Image.new("RGBA", (map_w, map_h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay_img)

                # Compute pixel positions in the assembled (large) image
                px_positions = []
                for point in points:
                    px, py = lat_lon_to_pixel_on_map(
                        point['lat'], point['lon'],
                        origin_fx, origin_fy, zoom_level,
                    )
                    # `lat_lon_to_pixel_on_map` is in units of the native
                    # tile size (256). When HiDPI doubles the on-canvas tile
                    # size we need to scale positions accordingly.
                    scale = tile_px / float(TILE_SIZE)
                    px *= scale
                    py *= scale
                    px_positions.append((px, py))

                # Markers: drop shadow + halo + filled dot + white rim.
                # Computed up-front because the trace width below is matched
                # to the moving-point's outer diameter.
                r_outer = max(7, int(9 * (tile_px / float(TILE_SIZE))))
                r_inner = max(3, int(4 * (tile_px / float(TILE_SIZE))))

                # Persistent trace (if any): draw the historic polyline first
                # so live markers stay on top. When a metric key is in use,
                # each segment is coloured by the average metric of its two
                # endpoints, mapped through the green→yellow→orange→red
                # gradient.
                #
                # The trace width is scaled proportionally to the zoom level
                # so the polyline stays visually thin when the map is zoomed
                # out to show the full route (e.g. at end-of-trip auto-fit).
                # At a typical street-level zoom (≈15) the full marker-sized
                # width is used; at lower zoom levels it shrinks linearly down
                # to a minimum of 2 px so the route remains visible without
                # dominating the map.
                moving_r_outer = max(1, int(round(r_outer * MOVING_POINT_SCALE)))
                _base_trace_w = max(2, moving_r_outer * 2)
                _zoom_scale = max(0.15, zoom_level / 15.0)
                trace_w = max(2, int(_base_trace_w * _zoom_scale))
                trace_alpha = _scaled_alpha(255, MOVING_POINT_ALPHA)
                # Non-trace live trail keeps its original (narrower) styling.
                live_trail_halo_w = max(6, int(8 * (tile_px / float(TILE_SIZE))))
                live_trail_line_w = max(2, int(3 * (tile_px / float(TILE_SIZE))))

                trace_pts = list(trace_history or [])
                if len(trace_pts) >= 2:
                    trace_px = []
                    for h in trace_pts:
                        tpx, tpy = lat_lon_to_pixel_on_map(
                            h['lat'], h['lon'],
                            origin_fx, origin_fy, zoom_level,
                        )
                        scale_h = tile_px / float(TILE_SIZE)
                        trace_px.append((tpx * scale_h, tpy * scale_h))

                    use_metric = (
                        metric_key and metric_key != METRIC_NONE
                        and any(h.get('metric') is not None for h in trace_pts)
                    )
                    if use_metric:
                        # Per-segment gradient colouring.
                        for (a, b), (ha, hb) in zip(
                            zip(trace_px[:-1], trace_px[1:]),
                            zip(trace_pts[:-1], trace_pts[1:]),
                        ):
                            ma = ha.get('metric')
                            mb = hb.get('metric')
                            vals = [v for v in (ma, mb) if v is not None]
                            if not vals:
                                color = (220, 30, 0, trace_alpha)
                            else:
                                avg = sum(vals) / len(vals)
                                color = _metric_gradient_color(avg, alpha=trace_alpha)
                            draw.line([a, b], fill=color, width=trace_w,
                                      joint="curve")
                    else:
                        draw.line(trace_px, fill=(220, 30, 0, trace_alpha),
                                  width=trace_w, joint="curve")

                # Live-points trail (only when no persistent trace is
                # available, to preserve the original behaviour for
                # non-trace use cases).
                if not trace_pts and len(px_positions) >= 2:
                    draw.line(px_positions, fill=(255, 255, 255, 200),
                              width=live_trail_halo_w, joint="curve")
                    draw.line(px_positions, fill=(220, 30, 0, 235),
                              width=live_trail_line_w, joint="curve")
                for point, (fpx, fpy) in zip(points, px_positions):
                    # Per-point scaling / transparency for "moving" markers.
                    # A point flagged ``is_moving=True`` is rendered larger and
                    # semi-transparent so it stands out as the current position
                    # along a route without hiding the trail or the basemap.
                    scale, alpha_factor = _moving_marker_style(point)
                    r_outer_pt = max(1, int(round(r_outer * scale)))
                    r_inner_pt = max(1, int(round(r_inner * scale)))
                    if (fpx < -r_outer_pt or fpx >= map_w + r_outer_pt or
                            fpy < -r_outer_pt or fpy >= map_h + r_outer_pt):
                        continue
                    # When a metric is selected and the point carries a
                    # value, colour the marker on the gradient instead of
                    # the default red-orange.
                    metric_v = self._metric_value(point, metric_key)
                    if metric_v is not None:
                        inner_fill = _metric_gradient_color(
                            metric_v, alpha=_scaled_alpha(255, alpha_factor),
                        )
                        halo_fill = _metric_gradient_color(
                            metric_v, alpha=_scaled_alpha(110, alpha_factor),
                        )
                    else:
                        inner_fill = (220, 30, 0, _scaled_alpha(255, alpha_factor))
                        halo_fill = (255, 80, 0, _scaled_alpha(90, alpha_factor))
                    # Soft drop shadow (offset 1-2 px, semi-transparent black)
                    draw.ellipse(
                        (fpx - r_outer_pt + 1, fpy - r_outer_pt + 2,
                         fpx + r_outer_pt + 1, fpy + r_outer_pt + 2),
                        fill=(0, 0, 0, _scaled_alpha(70, alpha_factor)),
                    )
                    # Outer halo ring (semi-transparent metric colour)
                    draw.ellipse(
                        (fpx - r_outer_pt, fpy - r_outer_pt,
                         fpx + r_outer_pt, fpy + r_outer_pt),
                        fill=halo_fill,
                    )
                    # Inner solid dot + thin white rim for contrast
                    draw.ellipse(
                        (fpx - r_inner_pt, fpy - r_inner_pt,
                         fpx + r_inner_pt, fpy + r_inner_pt),
                        fill=inner_fill,
                        outline=(255, 255, 255, _scaled_alpha(230, alpha_factor)),
                        width=1,
                    )

                pil_map = Image.alpha_composite(pil_map, overlay_img)

                # Attribution strip in the lower-right corner
                attribution = provider.get("attribution") or ""
                if attribution:
                    self._draw_attribution(pil_map, attribution)

            # High-quality resampling to the requested viewport size.
            # Pillow's LANCZOS preserves detail much better than cv2.INTER_AREA
            # when downscaling tile imagery.
            if pil_map.size != (width, height):
                pil_map = pil_map.resize((width, height), Image.LANCZOS)

            # Convert to BGR for the rest of the DPG/OpenCV pipeline
            rgb = pil_map.convert("RGB")
            map_array = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)

            if progress_tag and dpg.does_item_exist(progress_tag):
                dpg.set_value(progress_tag, 0.0)
                dpg.configure_item(progress_tag, overlay="")
                dpg.hide_item(progress_tag)

            print(f"Map node (direct OSM): Rendered {len(points)} points successfully")
            return map_array, cache_stats

        except Exception as e:
            print(f"Map node (direct OSM): Error rendering with direct tiles: {e}")
            traceback.print_exc()
            return self._render_with_contextily(points, width, height, zoom_level, size_factor, pan_x, pan_y), None


    @staticmethod
    def _draw_attribution(pil_map, attribution):
        """Draw a small, semi-transparent attribution label in the lower-right
        corner of the image. Required by tile usage policies and also acts as
        a nice visual finishing touch."""
        if not PIL_DRAW_AVAILABLE:
            return
        try:
            from PIL import ImageFont
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
            draw = ImageDraw.Draw(pil_map)
            text = str(attribution)
            # Measure text (Pillow ≥10 uses textbbox; older uses textsize)
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            except Exception:
                tw, th = (len(text) * 6, 11)
            pad = 3
            w, h = pil_map.size
            x0 = max(0, w - tw - 2 * pad - 4)
            y0 = max(0, h - th - 2 * pad - 4)
            box = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (255, 255, 255, 170))
            pil_map.paste(box, (x0, y0), box)
            draw.text((x0 + pad, y0 + pad), text, fill=(40, 40, 40, 230), font=font)
        except Exception as e:
            # Non-fatal: just skip the attribution overlay
            print(f"Map node: attribution overlay skipped: {e}")


    def _render_with_contextily(self, points, width, height, zoom_level=10, size_factor=1.0, pan_x=0.0, pan_y=0.0):
        """
        Render map using contextily for OSM tiles and matplotlib for points.
        
        This is the primary rendering method that:
        1. Creates a matplotlib figure
        2. Plots GPS points in Web Mercator projection
        3. Adds OSM basemap tiles using contextily
        4. Converts to numpy array for DPG texture
        
        Args:
            points: List of points with 'lat' and 'lon' keys
            width: Width of output image in pixels
            height: Height of output image in pixels
            zoom_level: OSM tile zoom level (1-18)
            size_factor: View size factor (0.5-5.0)
            pan_x: Horizontal pan offset (-1.0 to 1.0)
            pan_y: Vertical pan offset (-1.0 to 1.0)
        
        Returns:
            numpy array in BGR format
        """
        print(f"Map node: _render_with_contextily called with zoom={zoom_level}, size={size_factor}, pan=({pan_x}, {pan_y})")
        
        # Convert points to Web Mercator coordinates
        mercator_points = []
        for point in points:
            x, y = self.lat_lon_to_web_mercator(point['lat'], point['lon'])
            mp = {
                'x': x,
                'y': y,
                'name': point.get('name', 'Point'),
                'lat': point['lat'],
                'lon': point['lon']
            }
            # Preserve "moving" markers metadata for the rendering pass below.
            if point.get('is_moving'):
                mp['is_moving'] = True
                if 'marker_scale' in point:
                    mp['marker_scale'] = point['marker_scale']
                if 'marker_alpha' in point:
                    mp['marker_alpha'] = point['marker_alpha']
            mercator_points.append(mp)
        
        print(f"Map node: Converted {len(mercator_points)} points to Web Mercator")
        
        # Calculate extent (bounding box) with size_factor and pan offsets
        xs = [p['x'] for p in mercator_points]
        ys = [p['y'] for p in mercator_points]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        print(f"Map node: Initial bounds - X: [{min_x:.2f}, {max_x:.2f}], Y: [{min_y:.2f}, {max_y:.2f}]")
        
        # Add padding using the same logic as _calculate_extent
        x_range = max_x - min_x
        y_range = max_y - min_y
        
        # Ensure minimum range for single points or very close points
        if x_range < MIN_RANGE_METERS:
            x_range = DEFAULT_RANGE_METERS
            print(f"Map node: X range too small, using default: {DEFAULT_RANGE_METERS}m")
        if y_range < MIN_RANGE_METERS:
            y_range = DEFAULT_RANGE_METERS
            print(f"Map node: Y range too small, using default: {DEFAULT_RANGE_METERS}m")
        
        # Apply size factor (direct multiplication: smaller factor = smaller range = zoom in)
        # size_factor < 1.0 = zoom in (smaller range)
        # size_factor = 1.0 = normal view
        # size_factor > 1.0 = zoom out (larger range)
        x_range = x_range * size_factor
        y_range = y_range * size_factor
        print(f"Map node: Range after size_factor ({size_factor}): X={x_range:.2f}m, Y={y_range:.2f}m")
        
        min_x -= x_range * MAP_PADDING_FACTOR
        max_x += x_range * MAP_PADDING_FACTOR
        min_y -= y_range * MAP_PADDING_FACTOR
        max_y += y_range * MAP_PADDING_FACTOR
        
        print(f"Map node: After padding ({MAP_PADDING_FACTOR}): X: [{min_x:.2f}, {max_x:.2f}], Y: [{min_y:.2f}, {max_y:.2f}]")
        
        # Apply pan offsets
        total_x_range = max_x - min_x
        total_y_range = max_y - min_y
        
        pan_x_meters = pan_x * total_x_range
        pan_y_meters = pan_y * total_y_range
        
        min_x += pan_x_meters
        max_x += pan_x_meters
        min_y += pan_y_meters
        max_y += pan_y_meters
        
        print(f"Map node: After pan ({pan_x}, {pan_y}): X: [{min_x:.2f}, {max_x:.2f}], Y: [{min_y:.2f}, {max_y:.2f}]")
        
        # Create figure
        dpi = 600
        fig_width = width / dpi
        fig_height = height / dpi
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        print(f"Map node: Created figure {fig_width}x{fig_height} inches at {dpi} DPI")
        
        # Plot points in Web Mercator coordinates
        for point in mercator_points:
            scale, alpha_factor = _moving_marker_style(point)
            ax.plot(point['x'], point['y'], 'o',
                   color='red', markersize=10 * scale,
                   markeredgecolor='darkred', markeredgewidth=2,
                   markerfacecolor='yellow', alpha=alpha_factor, zorder=5)
        
        # Set axis limits
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        
        # Set background colors BEFORE attempting to load tiles
        # This ensures a proper background is visible whether tiles load or not
        ax.set_facecolor('#ADD8E6')  # Light blue background for axes
        fig.patch.set_facecolor('#E0F2F7')  # Light blue background for figure
        
        # Add OSM basemap using contextily
        # Use the zoom_level parameter from the slider
        basemap_loaded = False
        try:
            print(f"Map node: Attempting to load OSM tiles with zoom={zoom_level}")
            print(f"Map node: Using provider: {ctx.providers.OpenStreetMap.Mapnik}")
            print(f"Map node: CRS: EPSG:3857 (Web Mercator)")
            
            ctx.add_basemap(ax, crs='EPSG:3857', source=ctx.providers.OpenStreetMap.Mapnik,
                          zoom=zoom_level, attribution=None)
            basemap_loaded = True
            print("✓ Map node: OpenStreetMap tiles loaded successfully")
        except Exception as e:
            print(f"⚠ Map node: Could not load OpenStreetMap tiles")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Error message: {e}")
            traceback.print_exc()
            print("  Using fallback: light blue background without tiles")
            # Background already set above - points will still be visible
        
        # Hide axes completely - we don't want to show x,y coordinates (Web Mercator values)
        # The map tiles provide the geographic context, not numeric coordinates
        ax.set_xlabel('')
        ax.set_ylabel('')
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Set title with status indicator
        title_text = f'Map View - {len(points)} point(s)'
        if not basemap_loaded:
            title_text += ' (no tiles)'
        ax.set_title(title_text, fontsize=10, pad=10)
        
        # Tight layout
        plt.tight_layout(pad=0.5)
        
        # Render to image
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        
        # Convert to numpy array
        image = np.asarray(canvas.buffer_rgba())[:, :, :3]
        
        # Convert RGB to BGR for OpenCV
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        # Clean up
        plt.close(fig)
        
        return image


    def _render_with_matplotlib(self, points, width, height):
        """Fallback: Create a map visualization image with matplotlib (original implementation)"""
        if not points:
            preview = np.zeros((height, width, 3), dtype=np.uint8)
            return preview
        
        # Get bounds
        lats = [p['lat'] for p in points]
        lons = [p['lon'] for p in points]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Add padding to avoid points on edges
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        
        if lat_range == 0:
            lat_range = 0.1  # Small default range for single point
        if lon_range == 0:
            lon_range = 0.1
        
        padding = 0.15
        plot_min_lat = min_lat - lat_range * padding
        plot_max_lat = max_lat + lat_range * padding
        plot_min_lon = min_lon - lon_range * padding
        plot_max_lon = max_lon + lon_range * padding
        
        # Create figure with matplotlib
        dpi = 600
        fig_width = width / dpi
        fig_height = height / dpi
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        
        # Set background color (light blue for water)
        ax.set_facecolor('#ADD8E6')
        fig.patch.set_facecolor('#E0F2F7')
        
        # Draw grid lines (representing latitude/longitude grid)
        ax.grid(True, linestyle='--', linewidth=0.5, color='#888888', alpha=0.3)
        
        # Draw a simple coastline approximation (rectangular land masses)
        # This is a simplified representation - for actual coastlines, use cartopy or basemap
        self._draw_simplified_map_features(ax, plot_min_lon, plot_max_lon, plot_min_lat, plot_max_lat)
        
        # Plot points
        for point in points:
            scale, alpha_factor = _moving_marker_style(point)
            ax.plot(point['lon'], point['lat'], 'o', color='red',
                   markersize=8 * scale,
                   markeredgecolor='darkred', markeredgewidth=1.5,
                   markerfacecolor='yellow', alpha=alpha_factor, zorder=5)
        
        # Set axis limits
        ax.set_xlim(plot_min_lon, plot_max_lon)
        ax.set_ylim(plot_min_lat, plot_max_lat)
        
        # Hide coordinate tick values for cleaner map display
        # The fallback map shows simplified geographic features instead of precise coordinates
        ax.set_xlabel('')
        ax.set_ylabel('')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f'Map View - {len(points)} point(s)', fontsize=10, pad=10)
        
        # Set aspect ratio to maintain geographic proportions
        # Use cos(mean_lat) to approximate the aspect ratio
        # Clamp mean_lat to avoid division by zero at poles
        mean_lat = (min_lat + max_lat) / 2
        mean_lat = np.clip(mean_lat, -85, 85)  # Avoid extreme polar regions
        aspect_ratio = 1.0 / np.cos(np.radians(mean_lat))
        # Clamp aspect ratio to reasonable range
        aspect_ratio = np.clip(aspect_ratio, 0.1, 10.0)
        ax.set_aspect(aspect_ratio)
        
        # Tight layout to minimize margins
        plt.tight_layout(pad=0.5)
        
        # Render to image using FigureCanvasAgg
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        
        # Convert to numpy array
        image = np.asarray(canvas.buffer_rgba())[:, :, :3]
        
        # Convert RGB to BGR for OpenCV
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        # Clean up
        plt.close(fig)
        
        return image
    
    def _draw_simplified_map_features(self, ax, min_lon, max_lon, min_lat, max_lat):
        """Draw simplified map features (land approximation)
        
        Uses predefined continental outlines to provide geographic context.
        These are rough approximations - for precise coastlines, use cartopy or basemap.
        """
        # Determine if we're looking at a specific region
        lon_center = (min_lon + max_lon) / 2
        lat_center = (min_lat + max_lat) / 2
        
        # Check each continent and draw if we're viewing that region
        for continent_name, continent_data in SIMPLIFIED_CONTINENTS.items():
            bounds = continent_data['bounds']
            lon_bounds = bounds['lon']
            lat_bounds = bounds['lat']
            
            # Check if view center falls within this continent's bounds
            if (lon_bounds[0] < lon_center < lon_bounds[1] and 
                lat_bounds[0] < lat_center < lat_bounds[1]):
                # Draw the continent outline
                outline = continent_data['outline']
                ax.fill(outline['lon'], outline['lat'], 
                       color='#90EE90', alpha=0.3, zorder=1,
                       label=f'{continent_name.title()} (approx)')
                break  # Only draw one continent to avoid clutter
        
        # For other regions or zoomed views, just show water background
        # The grid and colors will still give a map-like appearance


    def close(self, node_id: int):
        pass


    def add_node(
        self,
        parent,
        node_id,
        pos,
        width,
        height,
        opencv_setting_dict,
    ):
        """Required abstract method - not used in this implementation"""
        pass


    def get_setting_dict(self, node_id):
        """Get node settings for saving"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_zoom_value_name = tag_node_name + ':ZoomValue'
        tag_node_size_value_name = tag_node_name + ':MapSizeValue'
        tag_node_cache_value_name = tag_node_name + ':UseCacheValue'
        tag_node_pan_x_value_name = tag_node_name + ':PanXValue'
        tag_node_pan_y_value_name = tag_node_name + ':PanYValue'
        tag_node_provider_value_name = tag_node_name + ':ProviderValue'
        tag_node_hidpi_value_name = tag_node_name + ':HiDPIValue'
        tag_node_labels_value_name = tag_node_name + ':LabelsValue'
        tag_node_metric_value_name = tag_node_name + ':MetricValue'
        tag_node_trace_value_name = tag_node_name + ':TraceValue'

        return {
            'zoom': dpg_get_value(tag_node_zoom_value_name),
            'size': dpg_get_value(tag_node_size_value_name),
            'cache': dpg_get_value(tag_node_cache_value_name),
            'pan_x': dpg_get_value(tag_node_pan_x_value_name),
            'pan_y': dpg_get_value(tag_node_pan_y_value_name),
            'provider': dpg_get_value(tag_node_provider_value_name),
            'hidpi': dpg_get_value(tag_node_hidpi_value_name),
            'labels_overlay': dpg_get_value(tag_node_labels_value_name),
            'metric': dpg_get_value(tag_node_metric_value_name),
            'trace': dpg_get_value(tag_node_trace_value_name),
        }


    def set_setting_dict(self, node_id, setting_dict):
        """Set node settings when loading"""
        tag_node_name = str(node_id) + ':' + self.node_tag
        tag_node_zoom_value_name = tag_node_name + ':ZoomValue'
        tag_node_size_value_name = tag_node_name + ':MapSizeValue'
        tag_node_cache_value_name = tag_node_name + ':UseCacheValue'
        tag_node_pan_x_value_name = tag_node_name + ':PanXValue'
        tag_node_pan_y_value_name = tag_node_name + ':PanYValue'
        tag_node_provider_value_name = tag_node_name + ':ProviderValue'
        tag_node_hidpi_value_name = tag_node_name + ':HiDPIValue'
        tag_node_labels_value_name = tag_node_name + ':LabelsValue'
        tag_node_metric_value_name = tag_node_name + ':MetricValue'
        tag_node_trace_value_name = tag_node_name + ':TraceValue'

        if 'zoom' in setting_dict:
            dpg_set_value(tag_node_zoom_value_name, setting_dict['zoom'])
        if 'size' in setting_dict:
            dpg_set_value(tag_node_size_value_name, setting_dict['size'])
        if 'cache' in setting_dict:
            dpg_set_value(tag_node_cache_value_name, setting_dict['cache'])
        if 'pan_x' in setting_dict:
            dpg_set_value(tag_node_pan_x_value_name, setting_dict['pan_x'])
        if 'pan_y' in setting_dict:
            dpg_set_value(tag_node_pan_y_value_name, setting_dict['pan_y'])
        if 'provider' in setting_dict and setting_dict['provider'] in TILE_PROVIDERS:
            dpg_set_value(tag_node_provider_value_name, setting_dict['provider'])
        if 'hidpi' in setting_dict:
            dpg_set_value(tag_node_hidpi_value_name, bool(setting_dict['hidpi']))
        if 'labels_overlay' in setting_dict:
            dpg_set_value(tag_node_labels_value_name, bool(setting_dict['labels_overlay']))
        if 'metric' in setting_dict and setting_dict['metric']:
            try:
                dpg_set_value(tag_node_metric_value_name, str(setting_dict['metric']))
            except Exception:
                pass
        if 'trace' in setting_dict:
            dpg_set_value(tag_node_trace_value_name, bool(setting_dict['trace']))


    def convert_cv_to_dpg(self, image, width, height):
        """Convert OpenCV image to DearPyGUI texture format"""
        resize_image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        data = np.flip(resize_image, 2)
        data = data.ravel()
        data = np.asarray(data, dtype=np.float32)
        texture_data = np.true_divide(data, 255.0)
        return texture_data
