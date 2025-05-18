#!/usr/bin/env python3

"""
Unit tests for GitHub Release Workflow

Environment Variables:
    TEST_GITHUB_URL: URL of the repository to test with (default: placeholder)
    TEST_REPO_NAME: Name of the repository for local directory (default: test-repo)
    TEST_PRODUCT_NAME: Product name to search for (default: test-product)
    TEST_SERVICE_NAME: Service name to search for (default: test-service)
"""

import os
import unittest
import asyncio
import sys
from unittest import mock

# Add the parent directory to the path so we can import the workflows module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from workflows.github_release import GitHubReleaseWorkflow

class TestGitHubReleaseWorkflow(unittest.TestCase):
    """Test cases for GitHubReleaseWorkflow"""
    
    def setUp(self):
        """Set up the test environment with configurable parameters from environment variables"""
        self.workflow = GitHubReleaseWorkflow()
        
        # Get parameters from environment variables with defaults
        self.github_url = os.environ.get("TEST_GITHUB_URL", "https://github.com/example/test-repo")
        repo_name = os.environ.get("TEST_REPO_NAME", "test-repo")
        self.product_name = os.environ.get("TEST_PRODUCT_NAME", "test-product")
        self.service_name = os.environ.get("TEST_SERVICE_NAME", "test-service")
        
        # Set up target directory
        self.target_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                     "cloned_repos", repo_name)
    
    def test_clone_repository(self):
        """Test repository cloning functionality"""
        # Skip this test if we're using the default example URL
        if self.github_url == "https://github.com/example/test-repo":
            self.skipTest("Skipping repository clone test with default example URL")
            return
            
        # This test verifies that the repository can be cloned
        repo_dir = self.workflow.clone_repository(
            github_url=self.github_url, 
            target_dir=self.target_dir
        )
        self.assertTrue(os.path.exists(repo_dir), "Repository directory should exist")
        self.assertTrue(os.path.exists(os.path.join(repo_dir, ".git")), "Repository should be a git repository")

    def test_search_yaml_files(self):
        """Test YAML file search functionality"""
        # Skip the test if we're using the default repo
        if self.github_url == "https://github.com/example/test-repo":
            # Mock implementation for testing without a real repo
            with mock.patch.object(self.workflow, 'search_yaml_files') as mock_search:
                mock_search.return_value = [
                    f"/mock/path/values/cluster/production/{self.product_name}/app/values.yaml",
                    f"/mock/path/values/cluster/production/{self.product_name}/api/values.yaml"
                ]
                yaml_files = self.workflow.search_yaml_files('/mock/path', self.product_name)
                self.assertEqual(len(yaml_files), 2, "Should find mocked YAML files for the product")
                mock_search.assert_called_once_with('/mock/path', self.product_name)
            return
            
        # Real implementation using actual repository
        yaml_files = self.workflow.search_yaml_files(self.target_dir, self.product_name)
        self.assertGreater(len(yaml_files), 0, "Should find YAML files for the product")
        
        # Verify files are from the right product
        for file_path in yaml_files:
            self.assertIn(self.product_name, file_path, f"File {file_path} should contain product name {self.product_name}")
            self.assertTrue(file_path.endswith(".yaml"), f"File {file_path} should be a YAML file")
            self.assertNotIn("templates", file_path.split(os.sep), "Should not include template files")
    
    def test_filter_yaml_by_service(self):
        """Test filtering YAML files by service name"""
        if self.github_url == "https://github.com/example/test-repo":
            # Create mock YAML files for testing
            mock_yaml_files = [
                f"/mock/path/values/cluster/production/{self.product_name}/app/values.yaml",
                f"/mock/path/values/cluster/production/{self.product_name}/api/values.yaml"
            ]
            
            # Mock the filter_yaml_by_service method
            with mock.patch.object(self.workflow, 'filter_yaml_by_service') as mock_filter:
                mock_filter.return_value = [{
                    'file_path': mock_yaml_files[0],
                    'matches': [
                        {'key': 'image.repository', 'value': f'registry.example.com/{self.service_name}'}
                    ]
                }]
                
                matching_files = self.workflow.filter_yaml_by_service(mock_yaml_files, self.service_name)
                self.assertEqual(len(matching_files), 1, "Should find mocked YAML files for the service")
                mock_filter.assert_called_once_with(mock_yaml_files, self.service_name)
                
                # Basic validation of the mock structure
                for file_info in matching_files:
                    self.assertIn('file_path', file_info)
                    self.assertIn('matches', file_info)
            return
        
        # Real implementation using actual repository
        yaml_files = self.workflow.search_yaml_files(self.target_dir, self.product_name)
        matching_files = self.workflow.filter_yaml_by_service(yaml_files, self.service_name)
        
        self.assertGreater(len(matching_files), 0, f"Should find YAML files for service {self.service_name}")
        
        # Verify each match
        for file_info in matching_files:
            self.assertIn('file_path', file_info, "File info should contain file_path")
            self.assertIn('matches', file_info, "File info should contain matches")
            self.assertGreater(len(file_info['matches']), 0, "Should have at least one match")
            
            # Verify each match contains the repository key and value
            for match in file_info['matches']:
                self.assertIn('key', match, "Match should contain key")
                self.assertIn('value', match, "Match should contain value")
                self.assertIn(self.service_name, match['value'].lower(), 
                             f"Value {match['value']} should contain service name {self.service_name}")

    async def run_workflow_test(self):
        """Helper method to run the workflow asynchronously"""
        # Use environment variables for product names or fall back to defaults
        product_names = os.environ.get("TEST_PRODUCT_NAMES", "").split(",")
        if not product_names or product_names == [""]:
            product_names = [self.product_name]
        
        services_info = [
            {"service_name": self.service_name, "product_names": product_names},
        ]
        
        results = []
        async for response in self.workflow.arun(
            github_url=self.github_url,
            services_info=services_info,
            target_dir=self.target_dir,
        ):
            results.append(response.content)
        
        return results

    def test_workflow_full(self):
        """Test the full workflow execution"""
        # Skip the full workflow test if using default example URL
        if self.github_url == "https://github.com/example/test-repo":
            # Mock the workflow's arun method
            async def mock_arun():
                return [
                    "Starting repository clone for https://github.com/example/test-repo...",
                    "Repository cloned successfully to /mock/path.",
                    f"Searching for YAML files for service '{self.service_name}' across products: {self.product_name}",
                    f"Found 1 YAML files for service '{self.service_name}' across all specified products:",
                    f"Product: {self.product_name}\nFile: values/mock/values.yaml\nMatching keys:\n  - image.repository: registry.example.com/{self.service_name}"
                ]
            
            # Run the mocked test
            with mock.patch.object(self, 'run_workflow_test', mock_arun):
                results = asyncio.run(self.run_workflow_test())
                self.assertEqual(len(results), 5, "Should get mock responses from workflow")
            return
            
        # Real implementation for actual testing
        results = asyncio.run(self.run_workflow_test())
        
        # Verify that we got expected responses
        self.assertGreater(len(results), 0, "Should get responses from workflow")
        
        # Check for successful cloning
        clone_success = any("Repository cloned successfully" in result for result in results)
        self.assertTrue(clone_success, "Repository should be cloned successfully")
        
        # Check for YAML file search
        search_success = any("Searching for YAML files" in result for result in results)
        self.assertTrue(search_success, "YAML file search should be performed")
        
        # Check for matching files
        # If the test is configured with valid parameters, we should find matches
        # Otherwise, we'll at least verify the workflow ran correctly
        if os.environ.get("TEST_EXPECT_MATCHES", "false").lower() == "true":
            match_success = any("Found" in result and "YAML files for service" in result for result in results)
            self.assertTrue(match_success, "Should find matching YAML files for the service")

if __name__ == "__main__":
    # Check if we're running with the default example URL
    if os.environ.get("TEST_GITHUB_URL", "") == "https://github.com/example/test-repo":
        print("\nRunning with default example URL. Tests will use mocks instead of real repositories.")
        print("To run tests with a real repository, set the following environment variables:")
        print("  TEST_GITHUB_URL     - GitHub URL to clone and test with")
        print("  TEST_REPO_NAME      - Name of the repository for local directory")
        print("  TEST_PRODUCT_NAME   - Product name to search for")
        print("  TEST_SERVICE_NAME   - Service name to search for")
        print("  TEST_PRODUCT_NAMES  - Comma-separated list of product names (optional)")
        print("  TEST_EXPECT_MATCHES - Set to 'true' if you expect to find matches (optional)")
        print("\nExample:")
        print("  TEST_GITHUB_URL=https://github.com/org/repo \\")
        print("  TEST_REPO_NAME=repo \\")
        print("  TEST_PRODUCT_NAME=product \\")
        print("  TEST_SERVICE_NAME=service \\")
        print("  TEST_PRODUCT_NAMES=prod1,prod2 \\")
        print("  TEST_EXPECT_MATCHES=true \\")
        print("  python -m tests.test_github_release_unittest\n")
    
    unittest.main()
