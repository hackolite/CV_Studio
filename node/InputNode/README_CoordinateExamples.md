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
- 5 vessels in European waters
- Includes vessel names and MMSI identifiers
- Locations: Le Havre, Thames, Marseille, Barcelona, Valencia

#### World Cities
Major cities around the world:
- 6 global metropolises
- Locations: New York, Tokyo, Sydney, San Francisco, Berlin, Singapore

#### European Ports
Major European maritime ports:
- 6 port locations
- Locations: Rotterdam, Hamburg, Antwerp, Le Havre, Gibraltar, Gijón

#### Mediterranean Sea
Cities and ports along the Mediterranean:
- 6 locations
- Locations: Malaga, Marseille, Nice, Bari, Malta, Athens

### Dynamic Simulation

#### GPS Movement Simulation
Real-time simulation of 5 moving objects with realistic movement patterns:

**Movement Patterns**:
- **Linear**: Objects move in straight lines at constant speed
- **Circular**: Objects follow circular paths
- **Random Walk**: Objects move with changing directions, staying within bounds

**Parameters**:
- Center: Paris, France (48.8566°N, 2.3522°E)
- Number of objects: 5 vehicles
- Speed range: 20-80 km/h
- Update frequency: Real-time with each node update

**Features**:
- Reproducible movements (uses seeded random generator)
- Objects stay within ~15km of center point
- Each object has unique name and pattern
- Continuous position updates

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
    "info": "linear - 45.5 km/h"
  },
  {
    "latitude": 48.8570,
    "longitude": 2.3530,
    "name": "Vehicle-002",
    "info": "circular - 60.2 km/h"
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

### Performance
- Static examples are instant (no computation)
- GPS simulation is very lightweight (< 1ms per update)
- All data generated locally (no network required)

## Coordinate Accuracy

Static examples use real-world coordinates from:
- Official port locations
- City center coordinates
- Maritime navigation data

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
