# Coordinate Examples Node

## Overview
The Coordinate Examples node provides predefined and simulated GPS coordinate datasets for testing and demonstration with the Map visualization node. It includes static examples and a dynamic GPS movement simulator.

## Features
- **Predefined Static Examples**: Multiple coordinate sets for different regions
- **GPS Movement Simulation**: Real-time simulation of moving objects with various patterns
- **No External Dependencies**: All data is generated locally
- **Map Node Compatible**: Output format works directly with Map visualization node

## Outputs
- **JSON (Coordinates)**: List of coordinate objects with latitude/longitude

## Controls
- **Example Dropdown**: Select from available coordinate datasets
- **Status Display**: Shows the number of points or simulation status

## Available Examples

### Static Examples

#### AISTRACKER
Sample vessel positions simulating maritime AIS data:
- 5 vessels in Port of Marseille area (within 1 km)
- Includes vessel names (Vessel Alpha, Beta, Gamma, Delta, Epsilon) and MMSI identifiers
- All vessels within 567m of each other for detailed visualization

#### World Cities
Clustered points for testing:
- 6 test points (Point A through F) in Paris area (within 1 km)
- All points within 496m of each other for detailed visualization

#### European Ports
Port zone markers for testing:
- 6 port zones (Port Zone A through F) in Amsterdam area (within 1 km)
- All points within 698m of each other for detailed visualization

#### Mediterranean Sea
Directional markers for testing:
- 6 directional points in Nice area (within 1 km)
- All points within 709m of each other for detailed visualization

### Dynamic Simulation

#### GPS Movement Simulation
Real-time simulation of a single moving object with realistic movement patterns:

**Movement Patterns**:
- **Linear**: Object moves in straight line at constant speed
- **Circular**: Object follows circular path
- **Random Walk**: Object moves with changing directions, staying within bounds

**Parameters**:
- Center: Paris, France (48.8566°N, 2.3522°E)
- Number of objects: 1 vehicle
- Speed: 4 km/h (walking speed)
- Update frequency: Real-time with each node update

**Features**:
- Reproducible movements (uses seeded random generator)
- Object stays within ~15km of center point
- Movement follows a randomly selected pattern (linear, circular, or random walk)
- Continuous position updates

#### Roissy Airport Planes
Real-time tracking of planes approaching Roissy-Charles de Gaulle Airport (CDG) using OpenSky Network API:

**Coverage Area**:
- Latitude: 48.90°N to 49.10°N
- Longitude: 2.35°E to 2.75°E
- Area: ~20km x 20km around CDG airport

**Approach Detection Criteria**:
- Altitude: < 1,500 meters (4,920 feet)
- Speed: < 300 km/h (162 knots)
- Vertical rate: < -1 m/s (descending)

**Parameters**:
- Update frequency: Every 20 seconds (to respect API rate limits)
- Data source: OpenSky Network public API
- Real-time flight data

**Output Information**:
- Callsign: Aircraft identification
- Position: Latitude and longitude
- Altitude: Height in meters
- Speed: Ground speed in km/h
- Vertical rate: Climb/descent rate in m/s

**Features**:
- Live aircraft tracking
- Automatic approach detection
- No API key required (public endpoint)
- Cached data between updates
- Network error handling

## Usage Examples

### Basic Visualization
1. Add **CoordinateExamples** node
2. Select an example from dropdown
3. Add **Map** node
4. Connect JSON output to Map input
5. Open map in browser

### GPS Movement Simulation
```
[CoordinateExamples: "GPS Movement Simulation"] 
    → [Map: Zoom=12, Cache=On] 
    → Browser
```

### Roissy Airport Planes
```
[CoordinateExamples: "Roissy Airport Planes"]
    → [Map: Zoom=11, Cache=Off]
    → Browser
```
Note: Requires internet connection to OpenSky Network API.

### Comparing Different Regions
```
[CoordinateExamples: "European Ports"] → [Map A]
[CoordinateExamples: "World Cities"] → [Map B]
```

## Output Format

All examples output JSON in this format:
```json
[
  {
    "latitude": 48.8566,
    "longitude": 2.3522,
    "name": "Vehicle-001",
    "info": "linear - 4.0 km/h"
  }
]
```

### Field Descriptions
- **latitude**: Decimal degrees, range -90 to 90
- **longitude**: Decimal degrees, range -180 to 180
- **name**: Human-readable identifier
- **info**: Additional information (MMSI for ships, movement pattern for simulation)

## GPS Movement Simulation Details

### Movement Patterns

#### Linear Movement
- Objects move in straight lines
- Direction set randomly at initialization
- Constant speed throughout
- Wraps around to stay in area

#### Circular Movement
- Objects follow circular paths around center point
- Radius approximately 11km
- Angular velocity based on speed
- Smooth continuous motion

#### Random Walk
- Direction changes randomly at each update
- Small step size (~111 meters per update)
- Automatically turns back toward center if too far
- Simulates unpredictable movement

### Technical Details

**Coordinate System**:
- Uses standard WGS84 decimal degrees
- Approximate conversions: 1 degree ≈ 111km at equator

**Time Simulation**:
- Position updates based on elapsed time since start
- Linear and circular patterns use absolute time
- Random walk uses incremental steps

**Reproducibility**:
- Uses seed value (42) for consistent "random" results
- Same seed produces same movement patterns
- Useful for testing and demonstrations

## Use Cases

### Testing and Development
- Test Map node without external data sources
- Verify coordinate visualization pipelines
- Debug GPS tracking workflows

### Demonstrations
- Show real-time tracking capabilities
- Demonstrate different movement patterns
- Illustrate map clustering with many points

### Education
- Learn about GPS coordinate systems
- Understand different movement patterns
- Explore map visualization concepts

### Prototyping
- Mock up maritime tracking systems
- Simulate vehicle tracking applications
- Test geographic analytics pipelines

## Tips

### For Static Examples
- Use "World Cities" to test global scale maps
- Use "European Ports" for regional testing
- Use "AISTRACKER" to simulate maritime data

### For GPS Simulation
- **Zoom Level**: Use 12-14 for best city-level view
- **View Size**: Set to 1.5-2.0 to see movement area
- **Caching**: Disable cache for simulation (coordinates change continuously)
- **Update Rate**: The simulation updates every time the node processes

### For Roissy Airport Planes
- **Zoom Level**: Use 10-12 for airport area view
- **View Size**: Set to 1.5-2.0 to see approach paths
- **Caching**: Keep cache disabled for real-time updates
- **Update Frequency**: Data refreshes every 20 seconds
- **Internet Required**: Needs active connection to OpenSky Network API
- **Rate Limiting**: API respects 20-second intervals to avoid rate limits

### Performance
- Static examples are instant (no computation)
- GPS simulation is very lightweight (< 1ms per update)
- All data generated locally (no network required)

## Coordinate Accuracy

All static examples use coordinates clustered within 1 km for detailed visualization:
- AISTRACKER: Port of Marseille area (max distance: 567m)
- World Cities: Paris area (max distance: 496m)
- European Ports: Amsterdam area (max distance: 698m)
- Mediterranean Sea: Nice area (max distance: 709m)

This close proximity allows for:
- Detailed street-level map visualization
- Better testing of zoom and pan features
- Clear visibility of individual markers
- Realistic urban-scale scenarios

GPS simulation provides realistic but not exact coordinates for:
- Testing purposes
- Demonstration scenarios
- Development workflows

## Future Enhancements

Potential features for future versions:
- Configurable number of simulated objects
- Custom center point selection
- Speed and pattern controls
- Historical track visualization
- Import custom coordinate sets
- Export simulation data
