# CV Studio - Architecture Restructuring

## 🎯 Overview

This repository has been restructured to provide a more professional and scalable codebase while maintaining **100% backward compatibility** with existing code.

## ✅ What's New

### New Directory Structure

```
src/
├── core/               # Core business logic
│   ├── nodes/          # Node abstractions (BaseNode, NodeFactory, EnhancedNode)
│   ├── config/         # Settings management
│   └── pipeline/       # Future: Processing pipeline
├── nodes/              # Node implementations
│   ├── input/          # Input node adapters
│   ├── process/        # Process node adapters
│   ├── ml/             # ML node adapters
│   ├── output/         # Output nodes (future)
│   └── examples/       # Example implementations
├── utils/              # Reusable utilities
│   ├── exceptions.py   # Custom exception hierarchy
│   ├── logging.py      # Centralized logging
│   └── resource_manager.py  # Resource lifecycle management
└── gui/                # GUI components (future)
```

### New Features

#### 1. **Professional Exception Handling**
```python
from src.utils.exceptions import NodeExecutionError, NodeConfigurationError

# Clear, structured error handling
raise NodeExecutionError(node_id, "Processing failed", original_exception)
```

#### 2. **Centralized Logging**
```python
from src.utils.logging import get_logger

logger = get_logger(__name__)
logger.info("Processing node...")
logger.error("Node failed", exc_info=True)
```

#### 3. **Resource Management**
```python
from src.utils.resource_manager import get_resource_manager

manager = get_resource_manager()
manager.register('video_capture', video_cap, cleanup_func=lambda v: v.release())
```

#### 4. **Settings Management**
```python
from src.core.config import Settings

settings = Settings('config.json')
width = settings.get('webcam_width', 640)
settings.set('use_gpu', True)
settings.save_to_file('config.json')
```

#### 5. **Node Factory Pattern**
```python
from src.core.nodes import NodeFactory

NodeFactory.register('MyNode', MyNodeClass)
node = NodeFactory.create('MyNode')
```

#### 6. **Enhanced Base Nodes**
```python
from src.core.nodes import EnhancedNode

class MyNode(EnhancedNode):
    # Inherits logging, error handling, resource management
    # Maintains compatibility with old system
    pass
```

## 📊 Test Coverage

**38 tests** covering all new components:
- ✅ Exception hierarchy (7 tests)
- ✅ Logging utilities (6 tests)
- ✅ Resource management (8 tests)
- ✅ Node factory (7 tests)
- ✅ Settings management (10 tests)

Run tests:
```bash
python3 -m pytest tests/ -v
```

## 🔄 Backward Compatibility

### All Existing Code Works Unchanged

```python
# Old code still works perfectly
from node.node_abc import DpgNodeABC
from node.basenode import Node
from node.InputNode.node_webcam import Node as WebcamNode
# ... etc
```

### Adapters Provide Access to Old Nodes

```python
# Access old nodes through new structure (optional)
from src.nodes.input import WebcamInputNode
from src.nodes.process import CannyNode
from src.nodes.ml import ClassificationNode
```

## 📚 Documentation

- **[Architecture Documentation](src/README.md)** - Detailed architecture overview
- **[Migration Guide](MIGRATION_GUIDE.md)** - How to use new features
- **[Example Node](src/nodes/examples/example_enhanced_node.py)** - Reference implementation

## 🚀 Quick Start

### Using the New Architecture

```python
# 1. Setup logging
from src.utils.logging import setup_logging
import logging

setup_logging(level=logging.INFO)

# 2. Create settings
from src.core.config import Settings
settings = Settings('config.json')

# 3. Create a node using the enhanced base
from src.core.nodes import EnhancedNode

class MyNode(EnhancedNode):
    node_label = 'My Node'
    node_tag = 'MyNode'
    
    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        # Your processing logic with built-in logging and error handling
        result = self.safe_execute(self.process_image, node_image_dict)
        return {"image": result, "json": None}
```

### Continuing with Old Code

```python
# Everything works as before
from node.ProcessNode.node_canny import Node as CannyNode

node = CannyNode()
# Use as normal
```

## 🎨 Benefits

### For Developers
- ✅ Clear code organization
- ✅ Reusable utilities
- ✅ Consistent error handling
- ✅ Professional logging
- ✅ Better testability

### For Maintainers
- ✅ Easier to add new features
- ✅ Separation of concerns
- ✅ Comprehensive tests
- ✅ No breaking changes
- ✅ Gradual migration path

### For Users
- ✅ Same functionality
- ✅ Better error messages
- ✅ More reliable resource cleanup
- ✅ Future-proof architecture

## 🔧 Development

### Running Tests

```bash
# All tests
python3 -m pytest tests/ -v

# Specific test suite
python3 -m pytest tests/test_utils/ -v
python3 -m pytest tests/test_core/ -v

# With coverage
python3 -m pytest tests/ --cov=src --cov-report=html
```

### Creating New Nodes

See [examples/example_enhanced_node.py](src/nodes/examples/example_enhanced_node.py) for a complete example.

```python
from src.core.nodes import EnhancedNode
from src.utils.logging import get_logger

logger = get_logger(__name__)

class MyNewNode(EnhancedNode):
    node_label = 'My New Node'
    node_tag = 'MyNewNode'
    
    # Implement required methods
    # Enjoy built-in logging, error handling, resource management
```

## 📈 Migration Strategy

### Phase 1: Infrastructure ✅ (Complete)
- ✅ New directory structure
- ✅ Core components
- ✅ Utilities
- ✅ Adapters
- ✅ Tests
- ✅ Documentation

### Phase 2: Enhancement (Optional)
- Add logging to existing nodes
- Use resource manager for cleanup
- Migrate to centralized settings

### Phase 3: Future Features
- Pipeline processing
- GUI refactoring
- Plugin system
- Auto-generated documentation

## 🤝 Contributing

When adding new features:

1. **Use the new architecture** for new code
2. **Add tests** for new functionality
3. **Update documentation** as needed
4. **Maintain backward compatibility**

## 📝 License

Same as the original project.

## 🙏 Acknowledgments

This restructuring maintains all original functionality while providing a foundation for future growth and maintainability.
