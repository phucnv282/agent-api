#!/usr/bin/env python3

"""
Test runner for all tests in the agent-api project

This script discovers and runs all tests in the tests directory:
1. Function-based tests that start with 'test_'
2. Unittest-based tests that inherit from unittest.TestCase

Usage:
    python -m tests.run_tests           # Run all tests
    python -m tests.run_tests -v        # Run with verbose output
    python -m tests.test_github_release # Run a specific test module
"""

import os
import sys
import unittest
import importlib
import inspect
import asyncio

def run_function_tests():
    """
    Run all standalone test functions that start with 'test_' in test modules
    """
    test_dir = os.path.dirname(os.path.abspath(__file__))
    test_count = 0
    success_count = 0
    
    print("\n=== Running Function Tests ===")
    
    # Load all test modules in the tests directory
    for file in os.listdir(test_dir):
        if file.startswith('test_') and file.endswith('.py') and file != '__init__.py':
            module_name = file[:-3]  # Remove .py extension
            print(f"\nRunning functions from {module_name}...")
            
            # Import the module
            try:
                module = importlib.import_module(f"tests.{module_name}")
                
                # Run any test_ functions defined in the module
                for name, obj in inspect.getmembers(module):
                    if name.startswith('test_') and inspect.isfunction(obj):
                        test_count += 1
                        print(f"  Running {name}...")
                        try:
                            # Handle both regular and async functions
                            if inspect.iscoroutinefunction(obj):
                                asyncio.run(obj())
                            else:
                                obj()
                            print(f"  ✓ {name} passed")
                            success_count += 1
                        except Exception as e:
                            print(f"  ✗ {name} failed: {str(e)}")
            except ImportError as e:
                print(f"  Error importing {module_name}: {str(e)}")
    
    print(f"\nFunction tests: {success_count}/{test_count} passed")
    return success_count == test_count

def run_unittest_tests():
    """
    Run all unittest-based tests using the unittest discovery mechanism
    """
    print("\n=== Running Unittest Tests ===")
    
    # Create a test loader
    loader = unittest.TestLoader()
    
    # Discover all test cases in the tests directory
    test_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(test_dir, pattern="test_*.py")
    
    # Create a test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run the test suite
    result = runner.run(suite)
    
    # Return True if all tests passed
    return result.wasSuccessful()

if __name__ == "__main__":
    # Add the parent directory to the path so we can import the tests module
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    
    # Run both types of tests
    function_success = run_function_tests()
    unittest_success = run_unittest_tests()
    
    # Exit with appropriate code
    sys.exit(0 if function_success and unittest_success else 1)
