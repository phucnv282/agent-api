#!/usr/bin/env python3

"""
Test script for GitHub Release Workflow

Environment Variables:
    TEST_GITHUB_URL: URL of the repository to test with (default: https://github.com/example/test-repo)
    TEST_REPO_NAME: Name of the repository for local directory (default: test-repo)
    TEST_SERVICE_NAMES: Comma-separated list of service names to test (default: test-service)
    TEST_PRODUCT_NAMES: Comma-separated list of product names to test (default: test-product)
"""

import asyncio
import os
import sys

# Add the parent directory to the path so we can import the workflows module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from workflows.github_release import GitHubReleaseWorkflow

async def test_workflow():
    workflow = GitHubReleaseWorkflow()
    
    # Define the GitHub repo URL from environment or use default
    github_url = os.environ.get("TEST_GITHUB_URL", "https://github.com/example/test-repo")
    
    # Get repo name from environment or use default
    repo_name = os.environ.get("TEST_REPO_NAME", "test-repo")
    
    # Use the existing cloned repo for testing instead of cloning a new one
    target_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             "cloned_repos", repo_name)
    
    # Get service names from environment or use default
    service_names = os.environ.get("TEST_SERVICE_NAMES", "test-service").split(",")
    
    # Get product names from environment or use default
    product_names = os.environ.get("TEST_PRODUCT_NAMES", "test-product").split(",")
    
    # Define test service info from environment variables
    services_info = []
    for service_name in service_names:
        if service_name:  # Skip empty service names
            services_info.append({
                "service_name": service_name,
                "product_names": product_names
            })
    
    # Use default test data if no valid services were defined
    if not services_info:
        print("No valid services defined. Using example services.")
        services_info = [
            {"service_name": "example-service", "product_names": ["example-product"]}
        ]
    
    # Display what we're testing
    print(f"\nTesting GitHub Release Workflow:")
    print(f"- Repository URL: {github_url}")
    print(f"- Target Directory: {target_dir}")
    print(f"- Services Information:")
    for info in services_info:
        print(f"  - Service: {info['service_name']}")
        print(f"    Products: {', '.join(info['product_names'])}")
    print()
    
    # Test the workflow
    try:
        async for response in workflow.arun(
            github_url=github_url,
            services_info=services_info,
            target_dir=target_dir,
        ):
            print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error running workflow: {str(e)}")

if __name__ == "__main__":
    # Show usage instructions when running with default values
    if os.environ.get("TEST_GITHUB_URL", "") == "https://github.com/example/test-repo":
        print("\nRunning with default example values.")
        print("To run tests with real values, set the following environment variables:")
        print("  TEST_GITHUB_URL     - GitHub URL to clone and test with")
        print("  TEST_REPO_NAME      - Name of the repository for local directory")
        print("  TEST_SERVICE_NAMES  - Comma-separated list of service names to test")
        print("  TEST_PRODUCT_NAMES  - Comma-separated list of product names to test")
        print("\nExample:")
        print("  TEST_GITHUB_URL=https://github.com/org/repo \\")
        print("  TEST_REPO_NAME=repo \\")
        print("  TEST_SERVICE_NAMES=service1,service2 \\")
        print("  TEST_PRODUCT_NAMES=product1,product2 \\")
        print("  python -m tests.test_github_release\n")
    
    asyncio.run(test_workflow())
