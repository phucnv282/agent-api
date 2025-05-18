# Tests for Agent API

This directory contains tests for the Agent API project. The tests are organized as follows:

## Test Structure

- `__init__.py` - Makes the tests directory a proper Python package
- `run_tests.py` - Main test runner that can run all tests
- `test_github_release.py` - Basic test script for the GitHub Release workflow
- `test_github_release_unittest.py` - Unit tests for the GitHub Release workflow using unittest framework

## GitHub Release Workflow Tests

The GitHub Release Workflow is tested in two ways:

1. **Basic test script (`test_github_release.py`)**:
   - Directly executes the workflow against a local repository
   - Tests multiple product names per service functionality
   - Prints output to the console for manual verification

2. **Unit tests (`test_github_release_unittest.py`)**:
   - Uses the unittest framework for structured testing
   - Tests individual components like repository cloning, YAML file searching, and service filtering
   - Tests the full workflow execution with assertions

## Running Tests

You can run tests in several ways:

### Run all tests

```bash
python -m tests.run_tests
```

### Run a specific test file

```bash
python -m tests.test_github_release
python -m tests.test_github_release_unittest
```

### Run a specific test directly

```bash
./tests/test_github_release.py
./tests/test_github_release_unittest.py
```

### Configuring Tests with Environment Variables

The tests are designed to use environment variables for configuration, making them suitable for CI/CD pipelines and avoiding hardcoded values in the codebase.

#### Available Environment Variables:

- `TEST_GITHUB_URL`: URL of the repository to test with (default: example URL)
- `TEST_REPO_NAME`: Name of the repository for local directory (default: test-repo)
- `TEST_PRODUCT_NAME`: Product name to search for (default: test-product)
- `TEST_SERVICE_NAME`: Service name to search for (default: test-service)
- `TEST_PRODUCT_NAMES`: Comma-separated list of product names (optional)
- `TEST_SERVICE_NAMES`: Comma-separated list of service names (optional)
- `TEST_EXPECT_MATCHES`: Set to 'true' if you expect to find matches (optional)

#### Example Usage:

```bash
# Basic configuration for functional test script
TEST_GITHUB_URL=https://github.com/org/repo \
TEST_REPO_NAME=repo \
TEST_SERVICE_NAMES=service1,service2 \
TEST_PRODUCT_NAMES=product1,product2 \
python -m tests.test_github_release

# Configuration for unittest-based tests
TEST_GITHUB_URL=https://github.com/org/repo \
TEST_REPO_NAME=repo \
TEST_PRODUCT_NAME=product \
TEST_SERVICE_NAME=service \
TEST_EXPECT_MATCHES=true \
python -m tests.test_github_release_unittest
```

## Test Features

- Support for multiple product names per service in the workflow
- Path-agnostic test files that work regardless of where they're run from
- Both function-based tests and unittest-based tests
- Comprehensive testing of workflow functionality

## Test Runner Features

The `run_tests.py` script:

1. Discovers and runs all standalone test functions that start with `test_`
2. Runs all unittest-based tests using the unittest discovery mechanism
3. Supports both synchronous and asynchronous test functions
4. Provides clear output showing which tests pass and fail
