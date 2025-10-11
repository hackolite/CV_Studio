# Migration Guide

## Overview

This guide helps you understand how to work with the new architecture while maintaining existing functionality.

## Current Status

✅ **All existing code continues to work unchanged**
✅ **New architecture is fully functional and tested (38 tests passing)**
✅ **Adapters provide seamless access to existing nodes**

## For Developers: Using the New Architecture

### 1. Creating a New Node with Enhanced Features

```python
from src.core.nodes import EnhancedNode
from src.utils.logging import get_logger

logger = get_logger(__name__)

class MyNewNode(EnhancedNode):
    """Example of a new node using the enhanced architecture"""
    
    node_label = 'My New Node'
    node_tag = 'MyNewNode'
    _ver = '1.0.0'
    
    def __init__(self):
        super().__init__()
        logger.info(f"Initialized {self.node_tag}")
    
    def add_node(self, parent, node_id, pos, opencv_setting_dict=None):
        """Add node to GUI"""
        # Your GUI code here
        pass
    
    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        """Process the node"""
        try:
            # Your processing logic here
            result = self.safe_execute(self._process_image, node_image_dict)
            return {"image": result, "json": None}
        except Exception as e:
            self.handle_error(node_id, e)
            return {"image": None, "json": None}
    
    def _process_image(self, image_dict):
        """Private processing method"""
        # Processing logic
        return processed_image
    
    def get_setting_dict(self, node_id):
        """Get settings"""
        return super().get_setting_dict(node_id)
    
    def set_setting_dict(self, node_id, setting_dict):
        """Apply settings"""
        super().set_setting_dict(node_id, setting_dict)
    
    def close(self, node_id):
        """Cleanup"""
        logger.info(f"Closing {self.node_tag}")
        super().close(node_id)
```

### 2. Using the Settings System

```python
from src.core.config import Settings

# In main.py or initialization code
settings = Settings('node_editor/setting/setting.json')

# Access settings
width = settings.get('webcam_width', 640)
height = settings.get('webcam_height', 480)
use_gpu = settings.get('use_gpu', False)

# Update settings
settings.set('use_gpu', True)
settings.save_to_file('node_editor/setting/setting.json')

# Pass to nodes
opencv_setting_dict = settings.get_all()
```

### 3. Using the Resource Manager

```python
from src.utils.resource_manager import get_resource_manager
import cv2

manager = get_resource_manager()

# Register a video capture with automatic cleanup
video_cap = cv2.VideoCapture(0)
manager.register(
    resource_id='webcam_0',
    resource=video_cap,
    cleanup_func=lambda cap: cap.release()
)

# Use the resource
cap = manager.get('webcam_0')
if cap:
    ret, frame = cap.read()

# Release when done (or it will be auto-released on shutdown)
manager.release('webcam_0')
```

### 4. Using the NodeFactory

```python
from src.core.nodes import NodeFactory

# Register your node class
NodeFactory.register('MyNewNode', MyNewNode)

# Create instances
node = NodeFactory.create('MyNewNode')

# Check if registered
if NodeFactory.is_registered('MyNewNode'):
    # Use the node
    pass
```

### 5. Using Custom Exceptions

```python
from src.utils.exceptions import NodeExecutionError, NodeConfigurationError

def process_node(node_id, config):
    # Validate configuration
    if 'required_param' not in config:
        raise NodeConfigurationError(
            node_id, 
            "Missing required parameter: required_param"
        )
    
    try:
        # Process
        result = do_processing()
    except Exception as e:
        raise NodeExecutionError(
            node_id,
            f"Processing failed: {str(e)}",
            original_exception=e
        )
    
    return result
```

### 6. Adding Logging to Existing Nodes

You can gradually enhance existing nodes with logging:

```python
# In any existing node file
from src.utils.logging import get_logger

logger = get_logger(__name__)

class ExistingNode(Node):
    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        logger.debug(f"Processing node {node_id}")
        
        try:
            # Existing processing code
            result = self.process()
            logger.info(f"Node {node_id} processed successfully")
            return result
        except Exception as e:
            logger.error(f"Node {node_id} failed: {e}")
            raise
```

## For Maintainers: Gradual Migration Strategy

### Phase 1: Infrastructure (Complete ✅)
- ✅ New directory structure
- ✅ Core components (BaseNode, NodeFactory, Settings)
- ✅ Utilities (exceptions, logging, resource manager)
- ✅ Adapters for backward compatibility
- ✅ Comprehensive tests

### Phase 2: Enhancement (Optional)
- Add logging to existing nodes
- Use resource manager for cleanup
- Replace manual exception handling with custom exceptions
- Migrate settings to centralized Settings class

### Phase 3: Refactoring (Future)
- Move commonly used code to utilities
- Create base classes for common node patterns
- Implement pipeline processing
- Separate GUI components

### Phase 4: Advanced Features (Future)
- Plugin system for dynamic node loading
- Type safety with comprehensive type hints
- Performance monitoring
- Auto-generated documentation

## File Organization

### Keep Old Structure Working
```
node/
├── InputNode/      # Existing input nodes (unchanged)
├── ProcessNode/    # Existing process nodes (unchanged)
├── DLNode/         # Existing ML nodes (unchanged)
├── basenode.py     # Original base node (unchanged)
└── node_abc.py     # Original abstract class (unchanged)
```

### New Architecture
```
src/
├── core/           # Core business logic
│   ├── nodes/      # Node abstractions
│   ├── config/     # Configuration
│   └── pipeline/   # Future: processing pipeline
├── nodes/          # Node adapters & new implementations
│   ├── input/      # Adapters to old InputNode + new nodes
│   ├── process/    # Adapters to old ProcessNode + new nodes
│   └── ml/         # Adapters to old DLNode + new nodes
└── utils/          # Shared utilities
```

## Testing

### Run All Tests
```bash
python3 -m pytest tests/ -v
```

### Run Specific Test Suite
```bash
python3 -m pytest tests/test_utils/test_logging.py -v
python3 -m pytest tests/test_core/test_factory.py -v
```

### Test Coverage
```bash
python3 -m pytest tests/ --cov=src --cov-report=html
```

## Best Practices

### 1. Use Logging Instead of Print
```python
# Old way
print("Processing node...")

# New way
from src.utils.logging import get_logger
logger = get_logger(__name__)
logger.info("Processing node...")
```

### 2. Use Resource Manager for Cleanup
```python
# Old way
def __del__(self):
    if hasattr(self, 'video_capture'):
        self.video_capture.release()

# New way
from src.utils.resource_manager import get_resource_manager
manager = get_resource_manager()
manager.register('video_capture', video_capture, lambda v: v.release())
```

### 3. Use Custom Exceptions
```python
# Old way
raise Exception(f"Node {node_id} failed")

# New way
from src.utils.exceptions import NodeExecutionError
raise NodeExecutionError(node_id, "Processing failed", original_exception)
```

### 4. Use Settings for Configuration
```python
# Old way
with open('config.json') as f:
    config = json.load(f)

# New way
from src.core.config import Settings
settings = Settings('config.json')
value = settings.get('key', default_value)
```

## Questions?

See the [README](../src/README.md) for detailed architecture documentation.
