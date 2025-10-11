# New Architecture Documentation

## Overview

The CV Studio codebase has been restructured to be more professional and scalable while maintaining 100% backward compatibility with existing code.

## Directory Structure

```
src/
├── core/           # Core business logic
│   ├── nodes/      # Base node classes and factory
│   │   ├── base.py           # BaseNode abstract class
│   │   ├── factory.py        # NodeFactory for node creation
│   │   ├── enhanced.py       # EnhancedNode with utilities
│   │   └── node_abc_enhanced.py  # Enhanced DpgNodeABC
│   ├── pipeline/   # Processing pipeline logic (future)
│   └── config/     # Centralized configuration
│       └── settings.py       # Settings management
├── nodes/          # Node implementations
│   ├── input/      # Input nodes (with adapters to old code)
│   ├── process/    # Processing nodes (with adapters)
│   ├── ml/         # ML nodes (renamed from DLNode, with adapters)
│   └── output/     # Output nodes (future)
├── utils/          # Reusable utilities
│   ├── exceptions.py         # Custom exception hierarchy
│   ├── logging.py            # Logging configuration
│   └── resource_manager.py  # Resource lifecycle management
└── gui/            # User interface components (future)
```

## Core Components

### BaseNode (src/core/nodes/base.py)

Abstract base class that defines the interface all nodes must implement:

```python
from src.core.nodes import BaseNode

class MyNode(BaseNode):
    def add_node(self, parent, node_id, pos, opencv_setting_dict=None):
        # Implementation
        pass
    
    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        # Implementation
        return {"image": result_image, "json": result_data}
    
    def get_setting_dict(self, node_id):
        # Implementation
        return {}
    
    def set_setting_dict(self, node_id, setting_dict):
        # Implementation
        pass
    
    def close(self, node_id):
        # Implementation
        pass
```

### EnhancedNode (src/core/nodes/enhanced.py)

Enhanced base class with additional utilities:

```python
from src.core.nodes import EnhancedNode

class MyNode(EnhancedNode):
    # Inherits convert_cv_to_dpg, safe_execute, and other utilities
    # Maintains compatibility with old node system
    pass
```

### NodeFactory (src/core/nodes/factory.py)

Centralized node creation and registration:

```python
from src.core.nodes import NodeFactory

# Register a node type
NodeFactory.register('MyNode', MyNodeClass)

# Create instances
node = NodeFactory.create('MyNode')

# Check registration
if NodeFactory.is_registered('MyNode'):
    # ...
```

### Settings (src/core/config/settings.py)

Centralized configuration management:

```python
from src.core.config import Settings

# Load settings from file
settings = Settings('path/to/config.json')

# Access settings
width = settings.get('webcam_width', 640)

# Update settings
settings.set('use_gpu', True)
settings.save_to_file('path/to/config.json')
```

### Exception Hierarchy (src/utils/exceptions.py)

Custom exceptions for better error handling:

```python
from src.utils.exceptions import NodeError, NodeExecutionError, NodeConfigurationError

try:
    # Node operation
    pass
except NodeExecutionError as e:
    print(f"Node {e.node_id} failed: {e}")
```

### Logging (src/utils/logging.py)

Centralized logging configuration:

```python
from src.utils.logging import setup_logging, get_logger

# Setup logging at application start
setup_logging(level=logging.INFO, log_file='app.log')

# Get logger in modules
logger = get_logger(__name__)
logger.info("Processing started")
```

### ResourceManager (src/utils/resource_manager.py)

Manage lifecycle of resources (video captures, models, etc.):

```python
from src.utils.resource_manager import get_resource_manager

manager = get_resource_manager()

# Register a resource
manager.register('video_capture', video_cap, cleanup_func=lambda v: v.release())

# Get resource
cap = manager.get('video_capture')

# Release when done
manager.release('video_capture')
```

## Backward Compatibility

The new architecture is designed to work alongside the existing code:

1. **Adapters**: The `src/nodes/*/adapters.py` files import existing node implementations
2. **Old code continues to work**: All existing nodes in `node/` directory remain untouched
3. **Gradual migration**: New nodes can use the new architecture, old nodes continue working
4. **No breaking changes**: External APIs remain the same

## Migration Guide

### For New Nodes

Use the new architecture:

```python
from src.core.nodes import EnhancedNode

class NewNode(EnhancedNode):
    node_label = 'New Node'
    node_tag = 'NewNode'
    
    def __init__(self):
        super().__init__()
        # Initialize
    
    # Implement required methods
```

### For Existing Nodes

Existing nodes continue to work without changes. To gradually enhance them:

1. Import utilities: `from src.utils.logging import get_logger`
2. Add logging: `logger = get_logger(__name__)`
3. Use resource manager for cleanup
4. Add proper exception handling

## Testing

The new components can be tested independently:

```python
# Test Settings
from src.core.config import Settings
settings = Settings()
assert settings.get('webcam_width') == 640

# Test NodeFactory
from src.core.nodes import NodeFactory
NodeFactory.register('TestNode', TestNodeClass)
node = NodeFactory.create('TestNode')

# Test ResourceManager
from src.utils.resource_manager import ResourceManager
manager = ResourceManager()
manager.register('test', resource, cleanup_func)
```

## Future Enhancements

1. **Pipeline processing**: Implement graph-based execution in `src/core/pipeline/`
2. **GUI refactoring**: Move GUI components to `src/gui/`
3. **Output nodes**: Implement output node abstractions in `src/nodes/output/`
4. **Plugin system**: Dynamic node loading from external packages
5. **Type hints**: Add comprehensive type annotations
6. **Unit tests**: Comprehensive test coverage
7. **Documentation**: Auto-generated API docs

## Benefits

1. **Separation of concerns**: Core logic, nodes, utils, and GUI are separated
2. **Testability**: Components can be tested independently
3. **Maintainability**: Clear structure makes code easier to understand and modify
4. **Scalability**: Easy to add new node types and features
5. **Professional**: Follows industry best practices
6. **Backward compatible**: No breaking changes to existing functionality
