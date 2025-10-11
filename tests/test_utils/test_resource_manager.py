#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for ResourceManager"""

import pytest
from src.utils.resource_manager import ResourceManager, get_resource_manager
from src.utils.exceptions import ResourceError


class MockResource:
    """Mock resource for testing"""
    def __init__(self):
        self.released = False
    
    def release(self):
        self.released = True


def test_resource_manager_register():
    """Test registering a resource"""
    manager = ResourceManager()
    resource = MockResource()
    manager.register('test_resource', resource)
    
    retrieved = manager.get('test_resource')
    assert retrieved is resource


def test_resource_manager_get_nonexistent():
    """Test getting a non-existent resource"""
    manager = ResourceManager()
    result = manager.get('nonexistent')
    assert result is None


def test_resource_manager_release():
    """Test releasing a resource"""
    manager = ResourceManager()
    resource = MockResource()
    
    cleanup_called = False
    def cleanup(r):
        nonlocal cleanup_called
        cleanup_called = True
        r.release()
    
    manager.register('test_resource', resource, cleanup)
    manager.release('test_resource')
    
    assert cleanup_called
    assert resource.released
    assert manager.get('test_resource') is None


def test_resource_manager_release_nonexistent():
    """Test releasing a non-existent resource (should not crash)"""
    manager = ResourceManager()
    # Should not raise an exception
    manager.release('nonexistent')


def test_resource_manager_release_all():
    """Test releasing all resources"""
    manager = ResourceManager()
    resources = [MockResource() for _ in range(3)]
    
    for i, resource in enumerate(resources):
        manager.register(f'resource_{i}', resource, lambda r: r.release())
    
    manager.release_all()
    
    # All resources should be released
    for i in range(3):
        assert manager.get(f'resource_{i}') is None


def test_resource_manager_replace():
    """Test replacing a resource"""
    manager = ResourceManager()
    resource1 = MockResource()
    resource2 = MockResource()
    
    manager.register('test', resource1, lambda r: r.release())
    manager.register('test', resource2, lambda r: r.release())
    
    # First resource should be released
    assert resource1.released
    # Second resource should be registered
    assert manager.get('test') is resource2


def test_get_global_resource_manager():
    """Test getting the global resource manager"""
    manager1 = get_resource_manager()
    manager2 = get_resource_manager()
    
    # Should return the same instance
    assert manager1 is manager2


def test_cleanup_error_handling():
    """Test that cleanup errors are handled properly"""
    manager = ResourceManager()
    
    def bad_cleanup(r):
        raise ValueError("Cleanup error")
    
    resource = MockResource()
    manager.register('test', resource, bad_cleanup)
    
    # Should raise ResourceError
    with pytest.raises(ResourceError):
        manager.release('test')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
