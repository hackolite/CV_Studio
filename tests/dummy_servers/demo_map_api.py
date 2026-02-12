#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demo script showing how to use the Map API endpoint
This demonstrates fetching and displaying map data from the API server
"""

import requests
import json
import time
import sys


def fetch_map_data(url="http://localhost:8080/map"):
    """Fetch map data from the API server"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {url}")
        print("Make sure the API server is running:")
        print("  cd tests/dummy_servers && python api_server.py")
        return None
    except Exception as e:
        print(f"Error fetching map data: {e}")
        return None


def display_map_data(data):
    """Display map data in a user-friendly format"""
    if not data:
        return
    
    print("\n" + "=" * 70)
    print(f"Map Data - {data['count']} Points")
    print("=" * 70)
    print(f"Timestamp: {time.ctime(data['timestamp'])}")
    print()
    
    for i, point in enumerate(data['points'], 1):
        print(f"{i}. {point['name']}")
        print(f"   Latitude:  {point['latitude']:>11.6f}")
        print(f"   Longitude: {point['longitude']:>11.6f}")
        print(f"   Time:      {time.ctime(point['timestamp'])}")
        print()
    
    print("=" * 70)


def demonstrate_continuous_fetching(url="http://localhost:8080/map", count=3, interval=2):
    """Demonstrate continuous fetching of map data"""
    print("\n" + "=" * 70)
    print("Demonstrating Continuous Map Data Fetching")
    print("=" * 70)
    print(f"Fetching {count} samples with {interval}s interval")
    print()
    
    for i in range(count):
        print(f"\n--- Fetch #{i+1} ---")
        data = fetch_map_data(url)
        if data:
            display_map_data(data)
        
        if i < count - 1:
            print(f"Waiting {interval} seconds before next fetch...")
            time.sleep(interval)


def main():
    """Main demo function"""
    print("\n" + "=" * 70)
    print("Map API Endpoint Demo")
    print("=" * 70)
    print()
    print("This demo shows how to fetch and display map data from the API server.")
    print("The /map endpoint returns JSON data with latitude/longitude coordinates")
    print("suitable for visualization in the CV_Studio Map node.")
    print()
    
    # Check if requests is available
    try:
        import requests
    except ImportError:
        print("Error: 'requests' library not found")
        print("Install it with: pip install requests")
        sys.exit(1)
    
    # Default URL
    url = "http://localhost:8080/map"
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    print(f"API Endpoint: {url}")
    print()
    
    # Single fetch demo
    print("\n1. Single Fetch Demo")
    print("-" * 70)
    data = fetch_map_data(url)
    if data:
        display_map_data(data)
    
        # Show raw JSON
        print("\n2. Raw JSON Response")
        print("-" * 70)
        print(json.dumps(data, indent=2))
        
        # Continuous fetching demo
        print("\n3. Continuous Fetching Demo")
        print("-" * 70)
        print("Press Ctrl+C to stop")
        try:
            demonstrate_continuous_fetching(url, count=3, interval=2)
        except KeyboardInterrupt:
            print("\nDemo interrupted by user")
    
    print("\n" + "=" * 70)
    print("Demo Complete")
    print("=" * 70)
    print()
    print("To use this data in CV_Studio:")
    print("1. Start the API server: python tests/dummy_servers/api_server.py")
    print("2. Add an API node in CV_Studio (Input menu)")
    print("3. Configure it to fetch from: http://localhost:8080/map")
    print("4. Add a Map node (Visual menu)")
    print("5. Connect API JSON output → Map JSON input")
    print("6. Click 'Open Map in Browser' to see the visualization")
    print()


if __name__ == '__main__':
    main()
