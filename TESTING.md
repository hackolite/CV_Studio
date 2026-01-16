# Testing Guide for CV Studio

This document provides comprehensive information about testing in CV Studio.

## Overview

CV Studio includes an extensive test suite with 150+ test files covering:
- Core node architecture
- Utility functions and helpers
- Node implementations
- Integration tests
- Queue system tests

## Test Framework

CV Studio uses **pytest** as the testing framework, which provides:
- Simple and readable test syntax
- Powerful fixtures and parametrization
- Excellent plugin ecosystem
- Detailed test reports

## Configuration

The project includes a `pytest.ini` configuration file that:
- Sets up test discovery patterns
- Configures output options
- Defines custom markers for test categorization
- Sets up code coverage reporting

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-cov
```

### Run All Tests

```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run tests with short traceback
python -m pytest tests/ -v --tb=short

# Run tests and show print statements
python -m pytest tests/ -v -s
```

### Run Specific Test Suites

```bash
# Core architecture tests
python -m pytest tests/test_core/ -v

# Utility tests
python -m pytest tests/test_utils/ -v

# Queue system tests
python -m pytest tests/test_timestamped_queue.py -v
python -m pytest tests/test_queue_adapter.py -v
python -m pytest tests/test_queue_integration.py -v

# Node-specific tests
python -m pytest tests/test_homography_node.py -v
python -m pytest tests/test_video_node_onthefly.py -v
```

### Run Tests by Marker

```bash
# Run only unit tests
python -m pytest tests/ -v -m unit

# Run only integration tests
python -m pytest tests/ -v -m integration

# Run tests excluding slow tests
python -m pytest tests/ -v -m "not slow"
```

### Run Tests with Coverage

```bash
# Generate coverage report
python -m pytest tests/ --cov=src --cov=node --cov-report=html

# Open coverage report
# The report will be in htmlcov/index.html
```

## Test Structure

### Core Tests (`tests/test_core/`)

Tests for the core node architecture:

- **`test_base_node.py`** (14 tests)
  - Tests for the `BaseNode` abstract class
  - Validates node lifecycle methods
  - Tests error handling

- **`test_enhanced_node.py`** (22 tests)
  - Tests for the `EnhancedNode` class
  - Validates image conversion utilities
  - Tests safe execution wrapper

- **`test_dpg_node_abc.py`** (16 tests)
  - Tests for the `DpgNodeABC` class
  - Validates DearPyGUI integration
  - Tests backward compatibility

- **`test_factory.py`** (7 tests)
  - Tests for node factory pattern
  - Validates node registration

- **`test_settings.py`** (10 tests)
  - Tests for settings management
  - Validates configuration loading/saving

### Utility Tests (`tests/test_utils/`)

Tests for utility modules:

- **`test_exceptions.py`** (7 tests)
  - Tests for custom exception hierarchy
  - Validates error handling

- **`test_logging.py`** (6 tests)
  - Tests for logging configuration
  - Validates log output

- **`test_resource_manager.py`** (8 tests)
  - Tests for resource lifecycle management
  - Validates cleanup operations

- **`test_gpu_utils.py`** (7 tests)
  - Tests for GPU detection
  - Validates execution provider selection

### Node Integration Tests

150+ tests covering various node implementations:

- Video processing nodes
- Audio processing nodes
- Object detection nodes
- Tracking nodes
- Overlay nodes
- And many more...

## Writing Tests

### Test File Naming

Test files should follow the pattern `test_*.py`:

```
tests/
  test_core/
    test_base_node.py
    test_enhanced_node.py
  test_utils/
    test_logging.py
```

### Test Function Naming

Test functions should start with `test_`:

```python
def test_node_creation():
    """Test that a node can be created"""
    node = MyNode()
    assert node is not None
```

### Test Class Organization

Group related tests in classes:

```python
class TestMyNode:
    """Test suite for MyNode"""
    
    def test_initialization(self):
        """Test node initialization"""
        pass
    
    def test_update(self):
        """Test node update method"""
        pass
```

### Using Fixtures

Create reusable test fixtures:

```python
import pytest

@pytest.fixture
def sample_node():
    """Create a sample node for testing"""
    return MyNode()

def test_with_fixture(sample_node):
    """Test using fixture"""
    assert sample_node.node_tag == "MyNode"
```

### Testing Exceptions

Test that exceptions are raised correctly:

```python
import pytest

def test_invalid_input():
    """Test that invalid input raises error"""
    node = MyNode()
    with pytest.raises(ValueError, match="Invalid input"):
        node.process(None)
```

### Mocking Dependencies

Use unittest.mock to mock dependencies:

```python
from unittest.mock import Mock, patch

def test_with_mock():
    """Test with mocked dependency"""
    with patch('cv2.imread') as mock_imread:
        mock_imread.return_value = np.zeros((100, 100, 3))
        # Test code here
```

## Best Practices

### 1. Test Independence

Each test should be independent and not rely on other tests:

```python
# Good
def test_feature_a():
    node = MyNode()
    result = node.feature_a()
    assert result == expected

# Bad - depends on test execution order
def test_feature_b():
    # Assumes test_feature_a() ran first
    result = node.feature_b()  # 'node' not defined
    assert result == expected
```

### 2. Clear Test Names

Use descriptive test names that explain what is being tested:

```python
# Good
def test_node_raises_error_when_input_is_none():
    pass

# Bad
def test_1():
    pass
```

### 3. Arrange-Act-Assert Pattern

Structure tests clearly:

```python
def test_node_processing():
    # Arrange
    node = MyNode()
    input_data = create_test_data()
    
    # Act
    result = node.process(input_data)
    
    # Assert
    assert result is not None
    assert result.shape == expected_shape
```

### 4. Test Edge Cases

Don't just test the happy path:

```python
def test_empty_input():
    """Test with empty input"""
    pass

def test_invalid_input():
    """Test with invalid input"""
    pass

def test_boundary_values():
    """Test with boundary values"""
    pass
```

### 5. Use Markers

Mark tests appropriately:

```python
import pytest

@pytest.mark.unit
def test_simple_function():
    pass

@pytest.mark.integration
def test_full_pipeline():
    pass

@pytest.mark.slow
def test_expensive_operation():
    pass

@pytest.mark.gpu
def test_gpu_acceleration():
    pass
```

## Continuous Integration

Tests are automatically run in CI/CD pipelines to ensure code quality.

### Running Tests Locally Before Commit

```bash
# Run quick tests
python -m pytest tests/ -v -m "not slow"

# Run all tests
python -m pytest tests/ -v

# Check coverage
python -m pytest tests/ --cov=src --cov=node
```

## Troubleshooting

### Common Issues

**Issue: Import errors**
```bash
# Solution: Make sure project root is in PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)
python -m pytest tests/
```

**Issue: Module not found**
```bash
# Solution: Install missing dependencies
pip install -r requirements.txt
```

**Issue: Tests fail due to missing dependencies**
```bash
# Solution: Install test dependencies
pip install pytest pytest-cov numpy opencv-python
```

### Debugging Tests

Run tests with more verbose output:

```bash
# Show print statements
python -m pytest tests/ -v -s

# Show full traceback
python -m pytest tests/ -v --tb=long

# Stop on first failure
python -m pytest tests/ -v -x

# Drop into debugger on failure
python -m pytest tests/ -v --pdb
```

## Contributing Tests

When contributing to CV Studio:

1. **Write tests for new features**
   - Add unit tests for new functions/classes
   - Add integration tests for new nodes

2. **Update existing tests**
   - Modify tests when changing functionality
   - Keep tests up to date with code changes

3. **Maintain test coverage**
   - Aim for high test coverage
   - Test edge cases and error conditions

4. **Follow naming conventions**
   - Use descriptive test names
   - Group related tests in classes

5. **Run tests before committing**
   - Ensure all tests pass
   - Check for any deprecation warnings

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Writing Good Tests](https://docs.pytest.org/en/stable/goodpractices.html)

## Summary

CV Studio has a comprehensive test suite that ensures code quality and prevents regressions. By following the guidelines in this document, you can contribute high-quality tests that help maintain the reliability of the project.

For questions or issues related to testing, please open an issue on GitHub.
