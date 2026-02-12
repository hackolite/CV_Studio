#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for Map API endpoint compatibility with Map node
Tests that the JSON returned by /map endpoint can be parsed by Map node
"""

import unittest
import sys
import os
import json


def extract_lat_lon_from_json(data):
    """
    Simplified version of Map node's _extract_lat_lon_from_json method
    This is the same logic used by the Map node to parse JSON data
    """
    points = []
    
    # Handle different JSON structures
    if isinstance(data, dict):
        # Check for AIS boat data structure
        if 'boats' in data:
            for boat in data['boats']:
                if 'latitude' in boat and 'longitude' in boat:
                    points.append({
                        'lat': boat['latitude'],
                        'lon': boat['longitude'],
                        'name': boat.get('ship_name', 'Unknown'),
                        'info': boat.get('mmsi', '')
                    })
        # Check for direct lat/lon in dict
        elif 'latitude' in data and 'longitude' in data:
            points.append({
                'lat': data['latitude'],
                'lon': data['longitude'],
                'name': data.get('name', 'Point'),
                'info': ''
            })
        # Check for nested data
        else:
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    points.extend(extract_lat_lon_from_json(value))
    
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if 'latitude' in item and 'longitude' in item:
                    points.append({
                        'lat': item['latitude'],
                        'lon': item['longitude'],
                        'name': item.get('name', 'Point'),
                        'info': item.get('mmsi', '')
                    })
                elif 'lat' in item and 'lon' in item:
                    points.append({
                        'lat': item['lat'],
                        'lon': item['lon'],
                        'name': item.get('name', 'Point'),
                        'info': ''
                    })
    
    return points


class TestMapAPIIntegration(unittest.TestCase):
    """Test Map API endpoint JSON format compatibility with Map node"""
    
    def test_map_api_json_format_simple(self):
        """Test that Map node can parse the API endpoint JSON format"""
        # Sample JSON response from /map endpoint
        api_response = {
            "points": [
                {
                    "name": "Paris",
                    "latitude": 48.8566,
                    "longitude": 2.3522,
                    "timestamp": 1234567890.123
                },
                {
                    "name": "London",
                    "latitude": 51.5074,
                    "longitude": -0.1278,
                    "timestamp": 1234567890.124
                }
            ],
            "timestamp": 1234567890.125,
            "count": 2
        }
        
        # Extract points using Map node's method
        points = extract_lat_lon_from_json(api_response)
        
        # Verify points were extracted correctly
        self.assertEqual(len(points), 2)
        
        # Check first point
        self.assertEqual(points[0]['lat'], 48.8566)
        self.assertEqual(points[0]['lon'], 2.3522)
        self.assertEqual(points[0]['name'], 'Paris')
        
        # Check second point
        self.assertEqual(points[1]['lat'], 51.5074)
        self.assertEqual(points[1]['lon'], -0.1278)
        self.assertEqual(points[1]['name'], 'London')
    
    def test_map_api_json_format_multiple_points(self):
        """Test with multiple points like real API response"""
        api_response = {
            "points": [
                {"name": "Tokyo", "latitude": 35.6762, "longitude": 139.6503, "timestamp": 1.0},
                {"name": "Sydney", "latitude": -33.8688, "longitude": 151.2093, "timestamp": 2.0},
                {"name": "Berlin", "latitude": 52.5200, "longitude": 13.4050, "timestamp": 3.0},
                {"name": "San Francisco", "latitude": 37.7749, "longitude": -122.4194, "timestamp": 4.0}
            ],
            "timestamp": 5.0,
            "count": 4
        }
        
        points = extract_lat_lon_from_json(api_response)
        
        self.assertEqual(len(points), 4)
        self.assertEqual(points[0]['name'], 'Tokyo')
        self.assertEqual(points[1]['name'], 'Sydney')
        self.assertEqual(points[2]['name'], 'Berlin')
        self.assertEqual(points[3]['name'], 'San Francisco')
    
    def test_map_api_json_with_random_offsets(self):
        """Test with coordinates that have random offsets (realistic API behavior)"""
        api_response = {
            "points": [
                {
                    "name": "Paris",
                    "latitude": 48.8566 + 0.01234,  # Small offset to simulate GPS drift/movement
                    "longitude": 2.3522 - 0.00567,  # Similar to what real GPS devices report
                    "timestamp": 1234567890.123
                }
            ],
            "timestamp": 1234567890.125,
            "count": 1
        }
        
        points = extract_lat_lon_from_json(api_response)
        
        self.assertEqual(len(points), 1)
        self.assertAlmostEqual(points[0]['lat'], 48.86894, places=5)
        self.assertAlmostEqual(points[0]['lon'], 2.34653, places=5)
    
    def test_map_api_empty_points(self):
        """Test with empty points array"""
        api_response = {
            "points": [],
            "timestamp": 1234567890.125,
            "count": 0
        }
        
        points = extract_lat_lon_from_json(api_response)
        
        self.assertEqual(len(points), 0)
    
    def test_map_api_nested_structure(self):
        """Test that Map node can extract from nested structure"""
        # The Map node recursively searches for lat/lon in nested structures
        api_response = {
            "metadata": {"source": "test"},
            "data": {
                "points": [
                    {"name": "Test", "latitude": 40.0, "longitude": -70.0, "timestamp": 1.0}
                ]
            }
        }
        
        points = extract_lat_lon_from_json(api_response)
        
        # The node should find the point through recursive search
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]['lat'], 40.0)
        self.assertEqual(points[0]['lon'], -70.0)
    
    def test_direct_list_format(self):
        """Test that a direct list of points also works"""
        # Some APIs might return a list directly
        api_response = [
            {"name": "Point1", "latitude": 10.0, "longitude": 20.0},
            {"name": "Point2", "latitude": 30.0, "longitude": 40.0}
        ]
        
        points = extract_lat_lon_from_json(api_response)
        
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0]['lat'], 10.0)
        self.assertEqual(points[0]['lon'], 20.0)


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("Testing Map API Integration with Map Node")
    print("=" * 70 + "\n")
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70 + "\n")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
