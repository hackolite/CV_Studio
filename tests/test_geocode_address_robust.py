#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the hardened ``geocode_address`` helper.

The geocoder is the Achilles' heel of the Road Route mode because the
public OSM endpoints are flaky. These tests pin the new contract:

* a bare ``"lat, lon"`` string bypasses any HTTP call,
* Nominatim is retried on transient failures,
* Photon is used as a fallback when Nominatim cannot answer,
* ``None`` is returned only when every provider fails.
"""
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.InputNode import node_coordinate_examples as nce


def test_latlon_literal_bypasses_http(monkeypatch):
    def _explode(*a, **kw):
        raise AssertionError("HTTP must not be called for a lat,lon literal")

    monkeypatch.setattr(nce.requests, "get", _explode)
    assert nce.geocode_address("48.8566, 2.3522") == (48.8566, 2.3522)
    assert nce.geocode_address(" -33.8688 ; 151.2093 ") == (-33.8688, 151.2093)


def test_invalid_latlon_literal_falls_through_to_provider(monkeypatch):
    """Out-of-range numbers must not be treated as coordinates."""
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["url"] = url
        captured["q"] = (params or {}).get("q")

        class _Resp:
            status_code = 200

            def json(self):
                return [{"lat": "1.0", "lon": "2.0"}]

        return _Resp()

    monkeypatch.setattr(nce.requests, "get", fake_get)
    # 999 is not a valid latitude -> must hit the provider.
    assert nce.geocode_address("999, 0") == (1.0, 2.0)
    assert captured["url"] == nce._NOMINATIM_URL


def test_nominatim_first_provider_returns_coordinates(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(url)

        class _Resp:
            status_code = 200

            def json(self):
                return [{"lat": "48.8566", "lon": "2.3522"}]

        return _Resp()

    monkeypatch.setattr(nce.requests, "get", fake_get)
    monkeypatch.setattr(nce.time, "sleep", lambda *_: None)
    assert nce.geocode_address("Paris") == (48.8566, 2.3522)
    # Photon must not be queried when Nominatim already answered.
    assert calls == [nce._NOMINATIM_URL]


def test_nominatim_retries_then_photon_fallback(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(url)
        if url == nce._NOMINATIM_URL:
            raise requests.exceptions.ConnectionError("boom")

        class _Resp:
            status_code = 200

            def json(self):
                return {
                    "features": [
                        {"geometry": {"coordinates": [2.3522, 48.8566]}},
                    ]
                }

        return _Resp()

    monkeypatch.setattr(nce.requests, "get", fake_get)
    monkeypatch.setattr(nce.time, "sleep", lambda *_: None)
    result = nce.geocode_address("Paris", retries=2)
    assert result == (48.8566, 2.3522)
    # Nominatim attempted retries+1 times, then Photon answered.
    nominatim_calls = [u for u in calls if u == nce._NOMINATIM_URL]
    photon_calls = [u for u in calls if u == nce._PHOTON_URL]
    assert len(nominatim_calls) == 3
    assert len(photon_calls) == 1


def test_all_providers_failing_returns_none(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        raise requests.exceptions.Timeout("timeout")

    monkeypatch.setattr(nce.requests, "get", fake_get)
    monkeypatch.setattr(nce.time, "sleep", lambda *_: None)
    assert nce.geocode_address("Nowhere", retries=1) is None


def test_empty_address_returns_none(monkeypatch):
    def _explode(*a, **kw):
        raise AssertionError("HTTP must not be called for an empty address")

    monkeypatch.setattr(nce.requests, "get", _explode)
    assert nce.geocode_address("") is None
    assert nce.geocode_address("   ") is None
    assert nce.geocode_address(None) is None


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
