#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Coordinate Examples Node

This node provides a dropdown list with predefined coordinate examples
that can be used with the Map visualization node. No external server required.

Examples include:
- AISTRACKER: Sample boat positions (AIS-like data)
- World Cities: Major cities around the world
- European Ports: Maritime port coordinates
- GPS Movement Simulation: Simulates moving objects with random paths
- None: No data output
"""

import json
import random
import math
import time
import dearpygui.dearpygui as dpg
import requests

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode


# GPS Movement Simulation name constant
GPS_SIMULATION_NAME = "GPS Movement Simulation"

# Roissy Airport Planes name constant
ROISSY_PLANES_NAME = "Roissy Airport Planes"

# Road Route name constant (drives a moving point along a road route
# computed between a start address and an end address at a given speed).
ROAD_ROUTE_NAME = "Road Route"

# Public OSM-based endpoints used by the Road Route mode. Both are
# free/no-key services; please keep request volume modest and identify
# this app via the User-Agent header (Nominatim usage policy).
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_PHOTON_URL = "https://photon.komoot.io/api"
_OSRM_ROUTE_URL = "https://router.project-osrm.org/route/v1/driving"
_HTTP_USER_AGENT = "CV_Studio/CoordinateExamples (https://github.com/hackolite/CV_Studio)"


# Predefined coordinate examples compatible with Map node format
# All examples now have points within 1 km for better detail visibility
# Note: Example names are preserved for compatibility, but coordinates are clustered for detailed visualization
COORDINATE_EXAMPLES = {
    "None": [],
    "AISTRACKER": [
        {"latitude": 43.2985, "longitude": 5.3708, "name": "Vessel Alpha", "mmsi": "123456789"},
        {"latitude": 43.2965, "longitude": 5.3738, "name": "Vessel Beta", "mmsi": "234567890"},
        {"latitude": 43.2935, "longitude": 5.3698, "name": "Vessel Gamma", "mmsi": "345678901"},
        {"latitude": 43.2965, "longitude": 5.3668, "name": "Vessel Delta", "mmsi": "456789012"},
        {"latitude": 43.2965, "longitude": 5.3698, "name": "Vessel Epsilon", "mmsi": "567890123"},
    ],
    "World Cities": [
        {"latitude": 48.8585, "longitude": 2.3522, "name": "Point A"},
        {"latitude": 48.8566, "longitude": 2.3552, "name": "Point B"},
        {"latitude": 48.8546, "longitude": 2.3522, "name": "Point C"},
        {"latitude": 48.8566, "longitude": 2.3492, "name": "Point D"},
        {"latitude": 48.8586, "longitude": 2.3492, "name": "Point E"},
        {"latitude": 48.8546, "longitude": 2.3492, "name": "Point F"},
    ],
    "European Ports": [
        {"latitude": 52.3706, "longitude": 4.9041, "name": "Port Zone A"},
        {"latitude": 52.3676, "longitude": 4.9071, "name": "Port Zone B"},
        {"latitude": 52.3646, "longitude": 4.9041, "name": "Port Zone C"},
        {"latitude": 52.3676, "longitude": 4.9011, "name": "Port Zone D"},
        {"latitude": 52.3706, "longitude": 4.9011, "name": "Port Zone E"},
        {"latitude": 52.3646, "longitude": 4.9011, "name": "Port Zone F"},
    ],
    "Mediterranean Sea": [
        {"latitude": 43.7132, "longitude": 7.2620, "name": "Point North"},
        {"latitude": 43.7102, "longitude": 7.2650, "name": "Point East"},
        {"latitude": 43.7072, "longitude": 7.2620, "name": "Point Center"},
        {"latitude": 43.7102, "longitude": 7.2590, "name": "Point West"},
        {"latitude": 43.7132, "longitude": 7.2590, "name": "Point Northwest"},
        {"latitude": 43.7072, "longitude": 7.2590, "name": "Point Southwest"},
    ],
}


class GPSMovementSimulator:
    """
    Simulates GPS movement for various objects.
    Generates random paths simulating realistic movement patterns.
    
    This simulator records position at T0 (initial time) and calculates
    subsequent positions at T1, T2, etc. based on walking speed (4 km/h).
    """
    
    def __init__(self, num_objects=5, center_lat=48.8566, center_lon=2.3522):
        """
        Initialize the GPS movement simulator.
        
        Args:
            num_objects: Number of moving objects to simulate
            center_lat: Center latitude for the simulation area
            center_lon: Center longitude for the simulation area
        """
        self.num_objects = num_objects
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.objects = []
        self.start_time = time.time()
        self.t0_positions = {}  # Store initial positions (T0) for each object
        self._initialize_objects()
    
    def _initialize_objects(self):
        """Initialize objects with random starting positions and velocities.
        
        Records T0 (initial position) for each object for reference.
        """
        random.seed(42)  # Use a seed for reproducible "random" movements
        
        for i in range(self.num_objects):
            # Random starting position within ~10km radius
            radius_km = random.uniform(0.5, 10)
            angle = random.uniform(0, 2 * math.pi)
            
            # Convert km to degrees (approximate)
            lat_offset = (radius_km / 111.0) * math.cos(angle)
            lon_offset = (radius_km / (111.0 * math.cos(math.radians(self.center_lat)))) * math.sin(angle)
            
            # Calculate initial position (T0)
            initial_lat = self.center_lat + lat_offset
            initial_lon = self.center_lon + lon_offset
            
            obj = {
                'id': i,
                'name': f'Vehicle-{i+1:03d}',
                'lat': initial_lat,
                'lon': initial_lon,
                'speed_kmh': 4,  # km/h (walking speed)
                'direction': random.uniform(0, 2 * math.pi),  # radians
                'pattern': random.choice(['linear', 'circular', 'random_walk']),
                # ``secousses`` is a dummy 0..1 metric (e.g. road bumpiness)
                # that drifts slowly over time. It starts in a quiet zone and
                # is updated via a bounded random walk in ``update_positions``
                # so visualisations can map it onto a green→yellow→orange→red
                # gradient.
                'secousses': random.uniform(0.05, 0.25),
                # Internal velocity used to keep the random walk smooth.
                '_secousses_drift': random.uniform(-0.01, 0.01),
            }
            self.objects.append(obj)
            
            # Record T0 position for reference
            self.t0_positions[i] = {
                'lat': initial_lat,
                'lon': initial_lon,
                'time': self.start_time
            }
            
            # Log T0 position
            print(f"GPS Simulator: Object {i} T0 position recorded - "
                  f"lat={initial_lat:.6f}, lon={initial_lon:.6f} at t={0:.1f}s")
    
    def update_positions(self, time_elapsed=None):
        """
        Update positions of all objects based on elapsed time.
        
        Calculates new position (T1, T2, ...) from initial position (T0)
        based on walking speed of 4 km/h.
        
        Args:
            time_elapsed: Time in seconds since start. If None, uses actual elapsed time.
        """
        if time_elapsed is None:
            time_elapsed = time.time() - self.start_time
        
        for obj in self.objects:
            # Calculate distance traveled from T0 at 4 km/h
            # Distance = speed * time
            distance_km = (obj['speed_kmh'] / 3600.0) * time_elapsed

            # Update position based on pattern
            if obj['pattern'] == 'linear':
                self._update_linear(obj, time_elapsed, distance_km)
            elif obj['pattern'] == 'circular':
                self._update_circular(obj, time_elapsed)
            else:  # random_walk
                self._update_random_walk(obj, time_elapsed)

            # Drift the ``secousses`` metric using a small, bounded random
            # walk so it varies plausibly (slow progression in [0, 1])
            # without sudden jumps. The drift itself is also smoothed so the
            # series oscillates softly between calm and shaky periods.
            obj['_secousses_drift'] = max(
                -0.04,
                min(0.04, obj['_secousses_drift'] + random.uniform(-0.01, 0.01)),
            )
            new_secousses = obj['secousses'] + obj['_secousses_drift']
            # Bounce off the [0, 1] walls so the value stays in range
            # without sticking at the boundaries.
            if new_secousses < 0.0:
                new_secousses = -new_secousses
                obj['_secousses_drift'] = -obj['_secousses_drift']
            elif new_secousses > 1.0:
                new_secousses = 2.0 - new_secousses
                obj['_secousses_drift'] = -obj['_secousses_drift']
            obj['secousses'] = new_secousses
            
            # Log position update at specific intervals (approximately every 10 seconds)
            # Use modulo with tolerance since time_elapsed is a float
            if time_elapsed > 0 and (int(time_elapsed) % 10 == 0 and time_elapsed - int(time_elapsed) < 0.5):
                t0 = self.t0_positions.get(obj['id'])
                if t0:
                    print(f"GPS Simulator: Object {obj['id']} T{int(time_elapsed)} position - "
                          f"lat={obj['lat']:.6f}, lon={obj['lon']:.6f}, "
                          f"distance from T0={distance_km:.3f}km")
    
    def _update_linear(self, obj, time_elapsed, distance_km):
        """Update position with linear movement.
        
        Calculates position at time T based on T0 position and walking speed.
        
        Args:
            obj: Object dictionary
            time_elapsed: Time in seconds since T0
            distance_km: Distance traveled in km at 4 km/h
        """
        # Get T0 position
        t0 = self.t0_positions.get(obj['id'])
        if not t0:
            # Fallback if T0 not recorded (shouldn't happen)
            t0 = {'lat': obj['lat'], 'lon': obj['lon']}
        
        # Convert distance to degrees based on direction
        lat_change = (distance_km / 111.0) * math.cos(obj['direction'])
        lon_change = (distance_km / (111.0 * math.cos(math.radians(t0['lat'])))) * math.sin(obj['direction'])
        
        # Calculate new position from T0 + movement
        new_lat = t0['lat'] + lat_change
        new_lon = t0['lon'] + lon_change
        
        # Only apply wrapping if object strays too far from center (>15km)
        base_lat = self.center_lat
        base_lon = self.center_lon
        distance_from_center = math.sqrt((new_lat - base_lat)**2 + (new_lon - base_lon)**2)
        
        if distance_from_center > 0.15:  # ~16.5 km from center
            # Wrap around to keep within bounds
            obj['lat'] = base_lat + ((new_lat - base_lat) % 0.2) - 0.1
            obj['lon'] = base_lon + ((new_lon - base_lon) % 0.2) - 0.1
        else:
            # No wrapping needed, just use the calculated position
            obj['lat'] = new_lat
            obj['lon'] = new_lon
    
    def _update_circular(self, obj, time_elapsed):
        """Update position with circular movement."""
        # Angular velocity (radians per second)
        angular_velocity = obj['speed_kmh'] / (20.0 * 111.0)  # Assumes ~20km radius
        
        angle = angular_velocity * time_elapsed + obj['direction']
        radius_deg = 0.1  # ~11km radius
        
        obj['lat'] = self.center_lat + radius_deg * math.cos(angle)
        obj['lon'] = self.center_lon + radius_deg * math.sin(angle)
    
    def _update_random_walk(self, obj, time_elapsed):
        """Update position with random walk pattern."""
        # Change direction slightly at each update
        obj['direction'] += random.uniform(-0.3, 0.3)
        
        # Small movement step
        step_size = 0.001  # ~111 meters
        obj['lat'] += step_size * math.cos(obj['direction'])
        obj['lon'] += step_size * math.sin(obj['direction'])
        
        # Keep within bounds
        max_dist = 0.15
        dist_from_center = math.sqrt(
            (obj['lat'] - self.center_lat)**2 + 
            (obj['lon'] - self.center_lon)**2
        )
        if dist_from_center > max_dist:
            # Turn back toward center
            obj['direction'] = math.atan2(
                self.center_lon - obj['lon'],
                self.center_lat - obj['lat']
            )
    
    def get_coordinates(self):
        """
        Get current coordinates of all objects.
        
        Returns:
            List of coordinate dictionaries compatible with Map node
        """
        coordinates = []
        for obj in self.objects:
            coordinates.append({
                'latitude': obj['lat'],
                'longitude': obj['lon'],
                'name': obj['name'],
                'info': f"{obj['pattern']} - {obj['speed_kmh']:.1f} km/h",
                # Flag for the Map node: this point is currently moving and
                # should be rendered larger and semi-transparent so it stands
                # out from static markers.
                'is_moving': True,
                # Dummy 0..1 metric: bumpiness/jolts experienced by the
                # vehicle along the trip. Consumers (e.g. the Map node) can
                # pick it via a "metric" selector to colour the marker and
                # trail with a green→yellow→orange→red gradient.
                'secousses': round(obj['secousses'], 4),
            })
        return coordinates
    
    def get_t0_positions(self):
        """
        Get initial (T0) positions of all objects.
        
        Returns:
            Dictionary mapping object ID (int) to T0 position data.
            Example: {0: {'lat': 48.8566, 'lon': 2.3522, 'time': 1708123456.789}}
        """
        return self.t0_positions.copy()


class RoissyPlanesTracker:
    """
    Tracks planes approaching Roissy-Charles de Gaulle Airport using OpenSky Network API.
    Detects planes that are approaching for landing based on altitude, speed, and vertical rate.
    """
    
    # Zone Roissy-Charles de Gaulle Airport (CDG)
    LAMIN = 48.90  # Minimum latitude
    LAMAX = 49.10  # Maximum latitude
    LOMIN = 2.35   # Minimum longitude
    LOMAX = 2.75   # Maximum longitude
    
    URL = "https://opensky-network.org/api/states/all"
    
    def __init__(self):
        """Initialize the Roissy planes tracker."""
        self.last_fetch_time = 0
        self.fetch_interval = 20  # Fetch every 20 seconds to avoid rate limiting
        self.cached_planes = []
    
    def get_planes(self):
        """
        Fetch planes in the Roissy airport area from OpenSky Network API.
        
        Returns:
            List of plane state vectors from the API
        """
        params = {
            "lamin": self.LAMIN,
            "lamax": self.LAMAX,
            "lomin": self.LOMIN,
            "lomax": self.LOMAX
        }
        
        try:
            r = requests.get(self.URL, params=params, timeout=10)
            
            if r.status_code != 200:
                print(f"RoissyPlanesTracker: API returned status {r.status_code}")
                return []
            
            data = r.json()
            return data.get("states", [])
        
        except requests.exceptions.Timeout:
            print("RoissyPlanesTracker: Request timeout")
            return []
        except requests.exceptions.RequestException as e:
            print(f"RoissyPlanesTracker: Request error: {e}")
            return []
        except Exception as e:
            print(f"RoissyPlanesTracker: Error fetching planes: {e}")
            return []
    
    def detect_landing(self, planes):
        """
        Detect planes that are approaching for landing.
        
        Criteria:
        - Altitude < 1500 meters
        - Speed < 300 km/h
        - Vertical rate < -1 m/s (descending)
        
        Args:
            planes: List of plane state vectors from OpenSky API
        
        Returns:
            List of dictionaries with approaching plane information
        """
        approaching = []
        
        for p in planes:
            callsign = p[1]
            lat = p[6]
            lon = p[5]
            alt = p[7]       # meters
            speed = p[9]     # m/s
            vertical = p[11]  # m/s (descent)
            
            if not lat or not lon:
                continue
            
            # Skip if essential data is missing
            if speed is None or alt is None or vertical is None:
                continue
            
            speed_kmh = speed * 3.6
            
            # Approach criteria
            if (
                alt < 1500 and
                speed_kmh < 300 and
                vertical < -1
            ):
                approaching.append({
                    "callsign": callsign.strip() if callsign else "Unknown",
                    "alt": int(alt),
                    "speed": int(speed_kmh),
                    "vertical": round(vertical, 1),
                    "lat": lat,
                    "lon": lon
                })
        
        return approaching
    
    def get_coordinates(self):
        """
        Get current coordinates of approaching planes.
        Fetches fresh data from API if enough time has elapsed.
        
        Returns:
            List of coordinate dictionaries compatible with Map node
        """
        current_time = time.time()
        
        # Check if we need to fetch fresh data
        if current_time - self.last_fetch_time >= self.fetch_interval:
            print(f"RoissyPlanesTracker: Fetching planes from OpenSky API...")
            planes = self.get_planes()
            approaching = self.detect_landing(planes)
            
            # Convert to coordinate format
            coordinates = []
            for p in approaching:
                coordinates.append({
                    'latitude': p['lat'],
                    'longitude': p['lon'],
                    'name': f"✈️ {p['callsign']}",
                    'info': f"Alt: {p['alt']}m, Speed: {p['speed']}km/h, Descent: {p['vertical']}m/s",
                    # Approaching planes are in motion: render them as enlarged
                    # semi-transparent markers on the Map node.
                    'is_moving': True,
                })
            
            self.cached_planes = coordinates
            self.last_fetch_time = current_time
            
            print(f"RoissyPlanesTracker: Found {len(coordinates)} approaching planes")
        
        return self.cached_planes


def _haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in kilometres."""
    r = 6371.0088  # mean Earth radius
    rlat1 = math.radians(lat1)
    rlat2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2
         + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.asin(min(1.0, math.sqrt(a)))
    return r * c


def _parse_latlon_literal(address):
    """If ``address`` is a bare ``"lat, lon"`` literal, return the tuple."""
    if not address:
        return None
    parts = [p.strip() for p in address.replace(";", ",").split(",")]
    if len(parts) != 2:
        return None
    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError:
        return None
    if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
        return (lat, lon)
    return None


def _query_nominatim(address, timeout):
    """Query Nominatim and return ``[(lat, lon), ...]`` ranked by relevance."""
    resp = requests.get(
        _NOMINATIM_URL,
        params={
            "q": address,
            "format": "json",
            "limit": 5,
            "addressdetails": 0,
        },
        headers={
            "User-Agent": _HTTP_USER_AGENT,
            "Accept-Language": "fr,en;q=0.8",
        },
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise requests.exceptions.HTTPError(
            f"Nominatim HTTP {resp.status_code}", response=resp,
        )
    data = resp.json() or []
    results = []
    for item in data:
        try:
            results.append((float(item["lat"]), float(item["lon"])))
        except (KeyError, TypeError, ValueError):
            continue
    return results


def _query_photon(address, timeout):
    """Query Photon (Komoot) as a fallback geocoder. Returns ``[(lat, lon), ...]``."""
    resp = requests.get(
        _PHOTON_URL,
        params={"q": address, "limit": 5, "lang": "fr"},
        headers={"User-Agent": _HTTP_USER_AGENT},
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise requests.exceptions.HTTPError(
            f"Photon HTTP {resp.status_code}", response=resp,
        )
    data = resp.json() or {}
    results = []
    for feature in data.get("features", []) or []:
        try:
            lon, lat = feature["geometry"]["coordinates"][:2]
            results.append((float(lat), float(lon)))
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    return results


def geocode_address(address, timeout=10, retries=2):
    """Resolve a free-text address to ``(lat, lon)``.

    Robust against transient network failures and short-lived service
    outages:

    1. Accepts a bare ``"lat, lon"`` literal so the user can bypass
       geocoding entirely when the API is flaky.
    2. Tries Nominatim first (OSM official) with up to ``retries+1``
       attempts and a small back-off between tries.
    3. Falls back to Photon (Komoot, also OSM-based) so an outage or rate
       limit on a single provider does not break the Road Route mode.

    Returns ``None`` only when every provider failed to return a usable
    result. Errors are logged so the UI can keep a visible trace.
    """
    if not address or not str(address).strip():
        return None
    address = str(address).strip()

    # 1) Direct "lat, lon" input bypasses any HTTP call.
    literal = _parse_latlon_literal(address)
    if literal is not None:
        return literal

    providers = (
        ("nominatim", _query_nominatim),
        ("photon", _query_photon),
    )

    last_error = None
    for provider_name, provider in providers:
        for attempt in range(max(1, retries + 1)):
            try:
                results = provider(address, timeout)
            except requests.exceptions.RequestException as e:
                last_error = e
                print(
                    f"geocode_address: {provider_name} request error "
                    f"(attempt {attempt + 1}) for '{address}': {e}"
                )
            except (ValueError, KeyError, IndexError, TypeError) as e:
                last_error = e
                print(
                    f"geocode_address: {provider_name} parse error "
                    f"(attempt {attempt + 1}) for '{address}': {e}"
                )
            else:
                if results:
                    return results[0]
                print(
                    f"geocode_address: {provider_name} no result "
                    f"(attempt {attempt + 1}) for '{address}'"
                )
                # No need to retry the same provider on an empty result.
                break
            # Linear back-off before retrying the same provider.
            time.sleep(min(1.0 + attempt * 0.5, 3.0))

    if last_error is not None:
        print(f"geocode_address: all providers failed for '{address}': {last_error}")
    return None


def fetch_driving_route(start_lat_lon, end_lat_lon, timeout=15):
    """Fetch a driving route polyline from OSRM.

    ``start_lat_lon`` / ``end_lat_lon`` are ``(lat, lon)`` tuples.
    Returns a list of ``(lat, lon)`` waypoints along the road, or ``None``
    on failure / empty response.
    """
    try:
        slat, slon = start_lat_lon
        elat, elon = end_lat_lon
        url = f"{_OSRM_ROUTE_URL}/{slon},{slat};{elon},{elat}"
        resp = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson"},
            headers={"User-Agent": _HTTP_USER_AGENT},
            timeout=timeout,
        )
        if resp.status_code != 200:
            print(f"fetch_driving_route: HTTP {resp.status_code}")
            return None
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            print(f"fetch_driving_route: bad response code={data.get('code')}")
            return None
        coords = data["routes"][0]["geometry"]["coordinates"]
        # GeoJSON returns [lon, lat] pairs; convert to (lat, lon).
        return [(float(lat), float(lon)) for lon, lat in coords]
    except requests.exceptions.RequestException as e:
        print(f"fetch_driving_route: request error: {e}")
        return None
    except (ValueError, KeyError, IndexError, TypeError) as e:
        print(f"fetch_driving_route: parse error: {e}")
        return None


class RouteTripPlayer:
    """Replays a driving route between two addresses at a chosen speed.

    The route is fetched once from OSRM (driving profile) and is then
    sampled along its length based on elapsed wall-clock time and the
    configured speed. Each call to :meth:`get_coordinates` returns the
    current position (one moving point) so the Map node can accumulate
    a persistent trace as the trip progresses.

    The player is "lazy": no network call is made until :meth:`start`
    succeeds. ``is_ready`` becomes True once a usable route is loaded.
    Geocoding/route-fetching errors are stored in :attr:`error` and the
    player stays idle (emitting no coordinates) so the Map remains
    empty until the user fixes the inputs and presses Start again.
    """

    def __init__(self, start_address, end_address, speed_kmh,
                 geocoder=None, router=None):
        self.start_address = start_address or ""
        self.end_address = end_address or ""
        try:
            self.speed_kmh = max(0.1, float(speed_kmh))
        except (TypeError, ValueError):
            self.speed_kmh = 50.0
        # Stored as None when the defaults are wanted; resolved at start()
        # time so monkeypatching ``geocode_address`` / ``fetch_driving_route``
        # at the module level (e.g. in tests) takes effect.
        self._geocoder = geocoder
        self._router = router
        self.route = []  # list of (lat, lon)
        self.cum_km = []  # cumulative km along the route for each waypoint
        self.total_km = 0.0
        self.start_time = None
        self.is_ready = False
        self.finished = False
        self.error = None
        # Simulated road-bumpiness metric in [0, 1] — same bounded random-walk
        # as GPSMovementSimulator so the Map node can colour the route trace on
        # a green→yellow→orange→red gradient.
        self._secousses = random.uniform(0.05, 0.25)
        self._secousses_drift = random.uniform(-0.01, 0.01)

        # --- OBD2 simulation state (bounded random walks) ---
        # All values are floats so the flat dict output passes the Chart node's
        # ``all(isinstance(v, (int, float)) for v in values)`` guard.

        # Régime moteur (RPM): typical urban 1500–2500, highway 2000–3000
        self._rpm = random.uniform(1400.0, 1800.0)
        self._rpm_drift = random.uniform(-20.0, 20.0)

        # Température moteur (°C): warms up to ~88–92 °C operating temp
        self._coolant_temp = 55.0          # cold start
        self._coolant_target = 90.0          # standard engine operating temperature

        # Consommation instantanée (L/100 km)
        self._consumption = random.uniform(7.0, 9.0)
        self._consumption_drift = random.uniform(-0.1, 0.1)

        # Position pédale d'accélérateur (%)
        self._throttle = random.uniform(15.0, 25.0)
        self._throttle_drift = random.uniform(-0.5, 0.5)

        # Charge moteur (%)
        self._engine_load = random.uniform(30.0, 45.0)
        self._engine_load_drift = random.uniform(-0.4, 0.4)

        # Débit d'air MAF (g/s)
        self._maf = random.uniform(8.0, 12.0)
        self._maf_drift = random.uniform(-0.1, 0.1)

        # Niveau carburant (%) — starts high and decreases slowly
        self._fuel_level = random.uniform(70.0, 90.0)

        # Tension batterie (V): 13.8–14.2 V while engine running
        self._battery_voltage = random.uniform(13.7, 14.2)
        self._battery_drift = random.uniform(-0.02, 0.02)

        # Codes défauts actifs (DTC count): usually 0, rarely 1
        self._dtc_count = 0.0

    def start(self):
        """Geocode the addresses and fetch the route. Returns True on success."""
        self.error = None
        geocoder = self._geocoder or geocode_address
        router = self._router or fetch_driving_route
        start = geocoder(self.start_address)
        if start is None:
            self.error = f"Cannot geocode start address: '{self.start_address}'"
            print(f"RouteTripPlayer: {self.error}")
            return False
        end = geocoder(self.end_address)
        if end is None:
            self.error = f"Cannot geocode end address: '{self.end_address}'"
            print(f"RouteTripPlayer: {self.error}")
            return False
        route = router(start, end)
        if not route or len(route) < 2:
            self.error = "Cannot compute driving route between the two addresses"
            print(f"RouteTripPlayer: {self.error}")
            return False
        # Pre-compute cumulative distances along the polyline.
        cum = [0.0]
        for i in range(1, len(route)):
            d = _haversine_km(route[i - 1][0], route[i - 1][1],
                              route[i][0], route[i][1])
            cum.append(cum[-1] + d)
        self.route = route
        self.cum_km = cum
        self.total_km = cum[-1]
        self.start_time = time.time()
        self.finished = False
        self.is_ready = True
        print(
            f"RouteTripPlayer: route loaded, "
            f"{len(route)} waypoints, total={self.total_km:.3f} km, "
            f"speed={self.speed_kmh:.1f} km/h, "
            f"ETA={3600.0 * self.total_km / self.speed_kmh:.1f}s"
        )
        return True

    def _position_at(self, distance_km):
        """Linearly interpolate the route polyline at ``distance_km``."""
        if not self.route:
            return None
        if distance_km <= 0:
            return self.route[0]
        if distance_km >= self.total_km:
            return self.route[-1]
        # Binary-search for the segment containing distance_km.
        lo, hi = 0, len(self.cum_km) - 1
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if self.cum_km[mid] <= distance_km:
                lo = mid
            else:
                hi = mid
        seg_start = self.cum_km[lo]
        seg_end = self.cum_km[hi]
        seg_len = max(1e-9, seg_end - seg_start)
        t = (distance_km - seg_start) / seg_len
        lat1, lon1 = self.route[lo]
        lat2, lon2 = self.route[hi]
        return (lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t)

    def set_speed(self, speed_kmh):
        """Adjust playback speed without losing already-travelled distance."""
        try:
            new_speed = max(0.1, float(speed_kmh))
        except (TypeError, ValueError):
            return
        if abs(new_speed - self.speed_kmh) < 1e-6:
            return
        # Preserve the distance already travelled when we change tempo,
        # by rebasing start_time so the current position stays put.
        if self.is_ready and self.start_time is not None:
            elapsed = time.time() - self.start_time
            travelled_km = (self.speed_kmh / 3600.0) * elapsed
            self.speed_kmh = new_speed
            self.start_time = time.time() - (travelled_km / (new_speed / 3600.0))
        else:
            self.speed_kmh = new_speed

    def _advance_obd2(self, moving):
        """Advance all OBD2 bounded random walks by one step.

        All values are kept as Python ``float`` so that the returned dict
        satisfies the Chart node's ``all(isinstance(v, (int, float)) …)``
        guard without any special casing.
        """
        # Secousses (road bumpiness)
        self._secousses_drift = max(
            -0.04,
            min(0.04, self._secousses_drift + random.uniform(-0.01, 0.01)),
        )
        new_sec = self._secousses + self._secousses_drift
        if new_sec < 0.0:
            new_sec = -new_sec
            self._secousses_drift = -self._secousses_drift
        elif new_sec > 1.0:
            new_sec = 2.0 - new_sec
            self._secousses_drift = -self._secousses_drift
        self._secousses = new_sec

        # Température moteur — ramp toward operating temp, then small jitter
        if self._coolant_temp < self._coolant_target:
            self._coolant_temp = min(
                self._coolant_target,
                self._coolant_temp + random.uniform(0.3, 0.8),
            )
        else:
            self._coolant_temp = max(
                self._coolant_target - 5.0,
                min(
                    self._coolant_target + 2.0,
                    self._coolant_temp + random.uniform(-0.3, 0.3),
                ),
            )

        # RPM — bounded walk around a centre that depends on speed
        rpm_center = 800.0 + self.speed_kmh * 18.0   # rough proportionality
        rpm_center = max(800.0, min(4200.0, rpm_center))
        self._rpm_drift = max(
            -150.0,
            min(150.0, self._rpm_drift + random.uniform(-30.0, 30.0)),
        )
        self._rpm = max(
            750.0,
            min(4500.0, rpm_center + self._rpm_drift),
        )

        # Pédale d'accélérateur (%)
        self._throttle_drift = max(
            -2.0,
            min(2.0, self._throttle_drift + random.uniform(-0.4, 0.4)),
        )
        self._throttle = max(
            5.0,
            min(85.0, self._throttle + self._throttle_drift),
        )

        # Charge moteur (%)
        self._engine_load_drift = max(
            -2.0,
            min(2.0, self._engine_load_drift + random.uniform(-0.3, 0.3)),
        )
        self._engine_load = max(
            10.0,
            min(90.0, self._engine_load + self._engine_load_drift),
        )

        # Débit d'air MAF (g/s) — follows RPM loosely
        maf_center = 3.0 + self._rpm / 300.0
        self._maf_drift = max(
            -0.5,
            min(0.5, self._maf_drift + random.uniform(-0.1, 0.1)),
        )
        self._maf = max(
            2.0,
            min(30.0, maf_center + self._maf_drift),
        )

        # Consommation instantanée (L/100 km) — roughly proportional to load
        cons_center = 2.0 + self._engine_load / 6.0
        self._consumption_drift = max(
            -0.5,
            min(0.5, self._consumption_drift + random.uniform(-0.1, 0.1)),
        )
        self._consumption = max(
            0.5,
            min(20.0, cons_center + self._consumption_drift),
        )

        # Niveau carburant (%) — drains very slowly
        if moving:
            self._fuel_level = max(0.0, self._fuel_level - 0.002)

        # Tension batterie (V)
        self._battery_drift = max(
            -0.05,
            min(0.05, self._battery_drift + random.uniform(-0.01, 0.01)),
        )
        self._battery_voltage = max(
            12.0,
            min(14.8, self._battery_voltage + self._battery_drift),
        )

        # Codes défauts (DTC) — stays 0, very rarely flips to 1 then back
        if self._dtc_count == 0.0 and random.random() < 0.001:
            self._dtc_count = 1.0
        elif self._dtc_count > 0.0 and random.random() < 0.05:
            self._dtc_count = 0.0

    def get_coordinates(self):
        """Return the current position as a flat numeric dict (Chart + Map compatible).

        The dict is a **flat mapping of floats** so the Chart node's
        ``all(isinstance(v, (int, float)) …)`` guard is satisfied and each
        OBD2 key becomes a plottable time-series.  The Map node reads
        ``latitude`` / ``longitude`` directly from the dict and treats all
        other numeric keys as optional colour-metric candidates.

        Returns an **empty list** (``[]``) when the player is not ready
        (geocoding failed or :meth:`start` was never called), keeping
        backward-compatibility with the idle / error paths.

        Once the end of the route is reached, ``is_moving`` is set to
        ``0.0`` so the Map node detects the end of the trip and triggers
        the auto-fit zoom.
        """
        if not self.is_ready or self.start_time is None:
            return []
        elapsed = max(0.0, time.time() - self.start_time)
        distance_km = (self.speed_kmh / 3600.0) * elapsed
        reached_end = distance_km >= self.total_km
        pos = self._position_at(distance_km)
        if pos is None:
            return []
        lat, lon = pos
        # ``is_moving=0.0`` on the final frame signals "trip ended" to
        # the Map node so it can auto-fit on the accumulated trace.
        moving_flag = 0.0 if reached_end else 1.0
        if reached_end:
            self.finished = True

        # Advance all OBD2 metrics one step.
        self._advance_obd2(moving=not reached_end)

        # Return a flat numeric dict.  All values MUST be int or float so
        # the Chart node processes the dict as a generic numeric time-series.
        return {
            # --- GPS position (used by the Map node) ---
            "latitude": round(lat, 7),
            "longitude": round(lon, 7),
            # 1.0 = en déplacement, 0.0 = arrêté / fin de trajet
            "is_moving": moving_flag,
            # --- OBD2 véhicule simulé ---
            "rpm": round(self._rpm, 1),
            "speed_kmh": round(self.speed_kmh + random.uniform(-2.0, 2.0), 1),
            "coolant_temp_c": round(self._coolant_temp, 1),
            "instant_consumption_l100": round(self._consumption, 2),
            "throttle_pos": round(self._throttle, 1),
            "engine_load": round(self._engine_load, 1),
            "maf_g_s": round(self._maf, 2),
            "fuel_level_pct": round(self._fuel_level, 2),
            "battery_voltage": round(self._battery_voltage, 3),
            "dtc_count": self._dtc_count,
            # Road-bumpiness metric in [0, 1] for colour-coded trace
            "secousses": round(self._secousses, 4),
        }


def get_example_names():
    """Get list of available example names for the dropdown."""
    # Static examples first, then add GPS simulation, Roissy planes and Road Route
    static_names = list(COORDINATE_EXAMPLES.keys())
    return static_names + [GPS_SIMULATION_NAME, ROISSY_PLANES_NAME, ROAD_ROUTE_NAME]


class FactoryNode:
    node_label = 'CoordinateExamples'
    node_tag = 'CoordinateExamples'
    
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
        """Adds a Coordinate Examples node with a dropdown to select predefined coordinate datasets."""
        
        # Generate node instance
        node = Node()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        
        # Dropdown tag for example selection
        node.tag_node_dropdown_name = node.tag_node_name + ':Dropdown'
        node.tag_node_dropdown_value_name = node.tag_node_name + ':DropdownValue'
        
        # Start/Stop button tag (used to begin the GPS trip)
        node.tag_node_start_name = node.tag_node_name + ':Start'
        node.tag_node_start_button_name = node.tag_node_name + ':StartButton'

        # Road Route input tags (address de départ, adresse d'arrivée, vitesse)
        node.tag_node_route_start_name = node.tag_node_name + ':RouteStart'
        node.tag_node_route_start_value_name = node.tag_node_name + ':RouteStartValue'
        node.tag_node_route_end_name = node.tag_node_name + ':RouteEnd'
        node.tag_node_route_end_value_name = node.tag_node_name + ':RouteEndValue'
        node.tag_node_route_speed_name = node.tag_node_name + ':RouteSpeed'
        node.tag_node_route_speed_value_name = node.tag_node_name + ':RouteSpeedValue'

        # Status text tag
        node.tag_node_status_name = node.tag_node_name + ':Status'
        node.tag_node_status_value_name = node.tag_node_name + ':StatusValue'
        
        # Output tags (JSON type for coordinates)
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01Value'
        
        node._opencv_setting_dict = opencv_setting_dict

        small_window_w = 200

        # Create yellow theme for JSON button
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 128, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 64, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0, 255))

        # Create node in the GUI
        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # Dropdown for selecting example dataset
            with dpg.node_attribute(
                tag=node.tag_node_dropdown_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_node_dropdown_value_name,
                    items=get_example_names(),
                    label="Example",
                    default_value="AISTRACKER",
                    width=small_window_w - 60,
                    callback=lambda s, a, u: Node.on_selection_change(s, a, u),
                    user_data=(node, node_id),
                )
            
            # Road Route inputs: departure address, arrival address and
            # tempo speed (km/h). They are reserved for the "Road Route"
            # option and are hidden for all other dropdown choices so they
            # cannot accidentally affect the other modes.
            _route_visible = (
                dpg.get_value(node.tag_node_dropdown_value_name)
                == ROAD_ROUTE_NAME
            )
            with dpg.node_attribute(
                tag=node.tag_node_route_start_name,
                attribute_type=dpg.mvNode_Attr_Static,
                show=_route_visible,
            ):
                dpg.add_input_text(
                    tag=node.tag_node_route_start_value_name,
                    label="From",
                    default_value="Paris, France",
                    width=small_window_w - 50,
                    hint="Departure address",
                )
            with dpg.node_attribute(
                tag=node.tag_node_route_end_name,
                attribute_type=dpg.mvNode_Attr_Static,
                show=_route_visible,
            ):
                dpg.add_input_text(
                    tag=node.tag_node_route_end_value_name,
                    label="To",
                    default_value="Versailles, France",
                    width=small_window_w - 50,
                    hint="Arrival address",
                )
            with dpg.node_attribute(
                tag=node.tag_node_route_speed_name,
                attribute_type=dpg.mvNode_Attr_Static,
                show=_route_visible,
            ):
                dpg.add_input_float(
                    tag=node.tag_node_route_speed_value_name,
                    label="km/h",
                    default_value=50.0,
                    min_value=0.1,
                    min_clamped=True,
                    width=small_window_w - 50,
                    step=5.0,
                )

            # Status text showing number of points
            with dpg.node_attribute(
                tag=node.tag_node_status_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_status_value_name,
                    default_value='5 points (AISTRACKER)',
                )

            # Start/Stop button to begin the trip (used by GPS Movement Simulation)
            with dpg.node_attribute(
                tag=node.tag_node_start_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label="Start",
                    tag=node.tag_node_start_button_name,
                    width=small_window_w,
                    callback=lambda s, a, u: Node.on_start_toggle(s, a, u),
                    user_data=(node, node_id),
                )
            
            # JSON output
            with dpg.node_attribute(
                tag=node.tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                btn = dpg.add_button(
                    label="JSON (Coordinates)",
                    tag=node.tag_node_output01_value_name,
                    width=small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)
                    
        return node


class Node(BaseNode):
    _ver = '1.0.2'

    node_label = 'CoordinateExamples'
    node_tag = 'CoordinateExamples'

    _opencv_setting_dict = None

    def __init__(self):
        self.gps_simulator = None  # Will be initialized when GPS simulation is selected
        self.roissy_tracker = None  # Will be initialized when Roissy planes is selected
        self.route_player = None  # Will be initialized when Road Route is selected
        self.last_update_time = None  # Track last GPS update time
        self.update_interval = 1.0  # Update GPS positions every 1 second
        self.last_coordinates = []  # Cache last generated coordinates
        # Whether the user has pressed Start to begin the GPS trip.
        # The GPS Movement Simulation stays idle (no coordinates emitted)
        # until the trip has been explicitly started from the node UI.
        self.is_started = False

    @staticmethod
    def _set_route_inputs_visible(node_id, visible):
        """Show/hide the Road Route input fields (From/To/km/h).

        The Road Route inputs are reserved for the Road Route option. They
        are hidden for every other dropdown choice so neither the UI nor
        any persistence path accidentally feeds them to a non-route mode.
        """
        tag_node_name = str(node_id) + ':' + Node.node_tag
        for suffix in (':RouteStart', ':RouteEnd', ':RouteSpeed'):
            try:
                dpg.configure_item(tag_node_name + suffix, show=bool(visible))
            except Exception:
                pass

    @staticmethod
    def on_start_toggle(sender, app_data, user_data):
        """Callback for the Start/Stop button: begins or stops the GPS trip."""
        node, node_id = user_data
        tag_node_name = str(node_id) + ':' + node.node_tag
        button_tag = tag_node_name + ':StartButton'
        status_tag = tag_node_name + ':StatusValue'
        dropdown_tag = tag_node_name + ':DropdownValue'

        if not node.is_started:
            # Begin the trip: reset any previous simulator so the trip
            # starts fresh from T0 at the current time.
            node.is_started = True
            node.gps_simulator = None
            node.route_player = None
            node.last_update_time = None
            node.last_coordinates = []
            try:
                dpg.configure_item(button_tag, label="Stop")
            except Exception:
                pass
            selected_example = dpg_get_value(dropdown_tag)
            if selected_example == GPS_SIMULATION_NAME:
                dpg_set_value(status_tag, 'Trip started (updates every 1s)')
            elif selected_example == ROAD_ROUTE_NAME:
                dpg_set_value(status_tag, 'Loading route...')
        else:
            # Stop the trip and reset state.
            node.is_started = False
            node.gps_simulator = None
            node.route_player = None
            node.last_update_time = None
            node.last_coordinates = []
            try:
                dpg.configure_item(button_tag, label="Start")
            except Exception:
                pass
            selected_example = dpg_get_value(dropdown_tag)
            if selected_example in (GPS_SIMULATION_NAME, ROAD_ROUTE_NAME):
                dpg_set_value(status_tag, 'Trip stopped (press Start to begin)')
    
    @staticmethod
    def on_selection_change(sender, app_data, user_data):
        """Callback when dropdown selection changes."""
        node, node_id = user_data
        selected_example = app_data
        
        # Reset GPS simulator when switching away from GPS simulation
        if selected_example != GPS_SIMULATION_NAME and hasattr(node, 'gps_simulator'):
            node.gps_simulator = None
            node.last_update_time = None
            node.last_coordinates = []
            node.is_started = False
            # Reset the Start button label back to "Start" so the user can
            # start a fresh trip the next time GPS Movement Simulation is picked.
            try:
                button_tag = str(node_id) + ':' + node.node_tag + ':StartButton'
                dpg.configure_item(button_tag, label="Start")
            except Exception:
                pass
        
        # Reset Roissy tracker when switching away from Roissy planes
        if selected_example != ROISSY_PLANES_NAME and hasattr(node, 'roissy_tracker'):
            node.roissy_tracker = None

        # Reset Road Route player when switching away from Road Route.
        # Also reset the Start button so the user can launch a fresh trip
        # next time the mode is selected.
        if selected_example != ROAD_ROUTE_NAME and hasattr(node, 'route_player'):
            if node.route_player is not None or getattr(node, 'is_started', False):
                node.route_player = None
                node.is_started = False
                node.last_coordinates = []
                try:
                    button_tag = str(node_id) + ':' + node.node_tag + ':StartButton'
                    dpg.configure_item(button_tag, label="Start")
                except Exception:
                    pass

        # Toggle visibility of the Road Route input fields: they are
        # reserved for the Road Route option and must stay hidden (and
        # ignored) for every other dropdown choice.
        Node._set_route_inputs_visible(
            node_id, selected_example == ROAD_ROUTE_NAME
        )

        # Get the coordinates for the selected example
        if selected_example == GPS_SIMULATION_NAME:
            # For GPS simulation, show dynamic message
            if getattr(node, 'is_started', False):
                status_text = 'Trip started (updates every 1s)'
            else:
                status_text = 'Press Start to begin the trip'
        elif selected_example == ROISSY_PLANES_NAME:
            # For Roissy planes, show dynamic message
            status_text = 'Tracking planes near Roissy Airport (updates every 20s)'
        elif selected_example == ROAD_ROUTE_NAME:
            if getattr(node, 'is_started', False):
                status_text = 'Trip in progress'
            else:
                status_text = 'Set From/To/km/h and press Start'
        else:
            coordinates = COORDINATE_EXAMPLES.get(selected_example, [])
            num_points = len(coordinates)
            
            if num_points > 0:
                status_text = f'{num_points} points ({selected_example})'
            else:
                status_text = 'No data (None selected)'
        
        # Update status text
        tag_node_name = str(node_id) + ':' + node.node_tag
        status_tag = tag_node_name + ':StatusValue'
        dpg_set_value(status_tag, status_text)

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        """Coordinate Examples node outputs the selected example coordinates as JSON."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        dropdown_tag = tag_node_name + ':DropdownValue'
        
        # Get selected example name
        selected_example = dpg_get_value(dropdown_tag)
        if selected_example is None:
            selected_example = "None"
        
        # Handle GPS Movement Simulation
        if selected_example == GPS_SIMULATION_NAME:
            # The trip must be explicitly started via the Start button.
            # While idle, emit no coordinates so the Map stays empty until
            # the user kicks off the trajectory.
            if not self.is_started:
                json_output = []
            else:
                # Initialize simulator if not already done
                if self.gps_simulator is None:
                    # Default: Paris, France as center
                    self.gps_simulator = GPSMovementSimulator(
                        num_objects=1,
                        center_lat=48.8566,
                        center_lon=2.3522
                    )
                    self.last_update_time = time.time()
                    # Get initial coordinates immediately so first call has data
                    self.last_coordinates = self.gps_simulator.get_coordinates()

                # Check if enough time has elapsed for an update (1 second interval)
                current_time = time.time()
                time_elapsed = current_time - self.last_update_time

                if time_elapsed >= self.update_interval:
                    # Update positions for current time
                    self.gps_simulator.update_positions()

                    # Get current coordinates
                    self.last_coordinates = self.gps_simulator.get_coordinates()

                    # Update the last update time
                    self.last_update_time = current_time

                # Return the last generated coordinates (updated every second)
                json_output = self.last_coordinates
        
        # Handle Roissy Airport Planes
        elif selected_example == ROISSY_PLANES_NAME:
            # Initialize tracker if not already done
            if self.roissy_tracker is None:
                self.roissy_tracker = RoissyPlanesTracker()
            
            # Get current approaching planes (tracker manages its own refresh interval)
            json_output = self.roissy_tracker.get_coordinates()

        # Handle Road Route mode: drive a single moving point along an
        # OSRM-computed driving route between the From/To addresses, at
        # the configured km/h tempo. Coordinates are emitted only after
        # the user has pressed Start (and the route is loaded).
        elif selected_example == ROAD_ROUTE_NAME:
            if not self.is_started:
                json_output = []
            else:
                start_addr_tag = tag_node_name + ':RouteStartValue'
                end_addr_tag = tag_node_name + ':RouteEndValue'
                speed_tag = tag_node_name + ':RouteSpeedValue'
                status_tag = tag_node_name + ':StatusValue'

                start_addr = dpg_get_value(start_addr_tag) or ""
                end_addr = dpg_get_value(end_addr_tag) or ""
                speed_kmh = dpg_get_value(speed_tag)
                if speed_kmh is None:
                    speed_kmh = 50.0

                # Lazily create / refresh the player when the inputs
                # change so the user can edit From/To and press Start
                # again to recompute the route.
                needs_new = (
                    self.route_player is None
                    or self.route_player.start_address != start_addr
                    or self.route_player.end_address != end_addr
                )
                if needs_new:
                    self.route_player = RouteTripPlayer(
                        start_addr, end_addr, speed_kmh,
                    )
                    if not self.route_player.start():
                        # Show the error in the node status but keep the
                        # player around so we don't hammer the API every
                        # frame; the user can edit and press Start again.
                        try:
                            dpg_set_value(
                                status_tag,
                                self.route_player.error or 'Route error',
                            )
                        except Exception:
                            pass
                        json_output = []
                    else:
                        try:
                            dpg_set_value(
                                status_tag,
                                f'Trip in progress: '
                                f'{self.route_player.total_km:.1f} km '
                                f'@ {self.route_player.speed_kmh:.1f} km/h',
                            )
                        except Exception:
                            pass
                        json_output = self.route_player.get_coordinates()
                else:
                    # Live speed tweaks are honoured without resetting the trip.
                    self.route_player.set_speed(speed_kmh)
                    json_output = self.route_player.get_coordinates()

        else:
            # Get static coordinates for the selected example
            coordinates = COORDINATE_EXAMPLES.get(selected_example, [])
            
            # Return coordinates in format compatible with Map node
            # Map node expects [{"latitude": x, "longitude": y, ...}]
            # or {"boats": [...]} format
            if coordinates:
                # Output as a list of coordinate objects (compatible with Map node)
                json_output = coordinates
            else:
                # Return empty list when None selected
                json_output = []

        return {"image": None, "json": json_output, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        """Save the current dropdown selection."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        dropdown_tag = tag_node_name + ':DropdownValue'
        route_start_tag = tag_node_name + ':RouteStartValue'
        route_end_tag = tag_node_name + ':RouteEndValue'
        route_speed_tag = tag_node_name + ':RouteSpeedValue'

        selected_example = dpg_get_value(dropdown_tag)
        if selected_example is None:
            selected_example = "AISTRACKER"

        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[dropdown_tag] = selected_example
        # Persist Road Route inputs (only when that mode is active) so the
        # trip can be resumed after reload. For every other mode the route
        # fields are out of scope and must not leak into the settings file.
        if selected_example == ROAD_ROUTE_NAME:
            try:
                setting_dict[route_start_tag] = dpg_get_value(route_start_tag)
                setting_dict[route_end_tag] = dpg_get_value(route_end_tag)
                setting_dict[route_speed_tag] = dpg_get_value(route_speed_tag)
            except Exception:
                pass

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        """Restore the dropdown selection."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        dropdown_tag = tag_node_name + ':DropdownValue'
        status_tag = tag_node_name + ':StatusValue'
        route_start_tag = tag_node_name + ':RouteStartValue'
        route_end_tag = tag_node_name + ':RouteEndValue'
        route_speed_tag = tag_node_name + ':RouteSpeedValue'

        selected_example = setting_dict.get(dropdown_tag, "AISTRACKER")
        dpg_set_value(dropdown_tag, selected_example)

        # Restore Road Route inputs when present.
        for tag in (route_start_tag, route_end_tag, route_speed_tag):
            if tag in setting_dict:
                try:
                    dpg_set_value(tag, setting_dict[tag])
                except Exception:
                    pass

        # Apply field visibility according to the restored mode: the
        # Road Route inputs must only appear when Road Route is active.
        Node._set_route_inputs_visible(
            node_id, selected_example == ROAD_ROUTE_NAME
        )

        # Update status text
        if selected_example == GPS_SIMULATION_NAME:
            status_text = 'Press Start to begin the trip'
        elif selected_example == ROAD_ROUTE_NAME:
            status_text = 'Set From/To/km/h and press Start'
        else:
            coordinates = COORDINATE_EXAMPLES.get(selected_example, [])
            num_points = len(coordinates)
            if num_points > 0:
                status_text = f'{num_points} points ({selected_example})'
            else:
                status_text = 'No data (None selected)'
        dpg_set_value(status_tag, status_text)
