"""Please install dependencies using:
pip install agno gitpython pyyaml
"""

import os
import re
import glob
from typing import Iterator, AsyncIterator, Optional, List, Dict, Any

import git
import yaml
from agno.agent import RunResponse
from agno.utils.log import logger
from agno.workflow import Workflow


class GitHubReleaseWorkflow(Workflow):
    description: str = (
        "Clone a GitHub repository to a local directory and search for YAML files with specific service configurations."
    )

    def clone_repository(self, github_url: str, target_dir: Optional[str] = None, 
                       username: Optional[str] = None, token: Optional[str] = None) -> str:
        """Clone a GitHub repository to a local directory.

        Args:
            github_url (str): URL of the GitHub repository to clone
            target_dir (Optional[str]): Target directory for cloning. If None, a temp directory is used.
            username (Optional[str]): GitHub username for private repository authentication
            token (Optional[str]): GitHub personal access token for private repository authentication

        Returns:
            str: Path to the cloned repository directory
        """
        # Check environment variables for credentials if not provided directly
        username = username or os.environ.get('GITHUB_USERNAME')
        token = token or os.environ.get('GITHUB_TOKEN')
        
        # Prepare authenticated URL if credentials are provided
        clone_url = github_url
        if username and token and clone_url.startswith("https://"):
            # Parse GitHub URL to insert auth credentials
            parts = clone_url.split("//")
            if len(parts) == 2:
                clone_url = f"{parts[0]}//{username}:{token}@{parts[1]}"
                # Don't log the URL with credentials for security
                logger.info(f"Using authenticated URL for cloning")
            else:
                logger.warning(f"Could not parse URL for authentication: {github_url}")
        
        # Extract repo name from URL for creating a default target directory
        repo_name = github_url.split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        # Use provided target_dir or create one based on repo name
        if target_dir is None:
            current_dir = os.getcwd()
            target_dir = os.path.join(current_dir, "cloned_repos", repo_name)

        # Create target directory if it doesn't exist
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)

        # Clone the repository
        logger.info(f"Cloning repository to {target_dir}...")
        try:
            if os.path.exists(target_dir):
                # If directory exists, try to update it
                try:
                    repo = git.Repo(target_dir)
                    origin = repo.remotes.origin
                    
                    # Set credentials for pull if needed
                    if username and token:
                        with repo.git.custom_environment(GIT_USERNAME=username, GIT_PASSWORD=token):
                            origin.pull()
                    else:
                        origin.pull()
                    
                    return target_dir
                except Exception as e:
                    logger.warning(f"Failed to update existing repository: {e}")
                    # If updating fails, remove and clone fresh
                    import shutil
                    shutil.rmtree(target_dir, ignore_errors=True)
                    
            # Clone fresh repository
            git.Repo.clone_from(clone_url, target_dir)
            return target_dir
        except Exception as e:
            error_msg = f"Failed to clone repository: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)



    def run(self, github_url: str, services_info: List[Dict[str, Any]], target_dir: Optional[str] = None,
            username: Optional[str] = None, token: Optional[str] = None) -> Iterator[RunResponse]:
        """Clone a GitHub repository to a local directory and search for service configurations.

        Args:
            github_url (str): URL of the GitHub repository to clone
            services_info (List[Dict[str, Any]]): List of dictionaries with service_name and product_names
                Example 1: [{"service_name": "user-api", "product_name": "corp"}]
                Example 2: [{"service_name": "user-api", "product_names": ["corp", "sophia-vpbank"]}]
            target_dir (Optional[str]): Target directory for cloning. If None, a temp directory is used.
            username (Optional[str]): GitHub username for private repository authentication
            token (Optional[str]): GitHub personal access token for private repository authentication

        Yields:
            Iterator[RunResponse]: Iterator of run responses
        """
        # Clone the repository
        logger.info(f"Cloning GitHub repository: {github_url}")
        yield RunResponse(
            run_id=self.run_id,
            content=f"Starting repository clone for {github_url}..."
        )
        
        try:
            # Clone the repository
            repo_dir = self.clone_repository(github_url, target_dir, username, token)
            yield RunResponse(
                run_id=self.run_id,
                content=f"Repository cloned successfully to {repo_dir}."
            )
            
            # Search for YAML files for each service
            for service_info in services_info:
                service_name = service_info.get("service_name")
                
                # Support both single product_name and list of product_names
                product_names = service_info.get("product_names") or [service_info.get("product_name")]
                
                # Ensure product_names is a list
                if isinstance(product_names, str):
                    product_names = [product_names]
                    
                if not service_name or not product_names or None in product_names:
                    yield RunResponse(
                        run_id=self.run_id,
                        content=f"Error: Missing service_name or valid product_names in service info: {service_info}"
                    )
                    continue
                
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"Searching for YAML files for service '{service_name}' across products: {', '.join(product_names)}"
                )
                
                all_matching_files = []
                
                # Process each product name and collect all matching files
                for product_name in product_names:
                    # Search for YAML files matching the path pattern
                    logger.info(f"Searching for YAML files in product '{product_name}'...")
                    
                    yaml_files = self.search_yaml_files(repo_dir, product_name)
                    
                    if not yaml_files:
                        logger.info(f"No YAML files found for product '{product_name}'")
                        continue
                    
                    # Filter YAML files by service name
                    matching_files = self.filter_yaml_by_service(yaml_files, service_name)
                    
                    if not matching_files:
                        logger.info(f"No matches found for service '{service_name}' in product '{product_name}'")
                        continue
                        
                    # Add product name to each file info
                    for file_info in matching_files:
                        file_info['product_name'] = product_name
                    
                    all_matching_files.extend(matching_files)
                
                # Report consolidated results
                if not all_matching_files:
                    yield RunResponse(
                        run_id=self.run_id,
                        content=f"No YAML files found with image repository ending with '{service_name}' across the specified products"
                    )
                    continue
                
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"Found {len(all_matching_files)} YAML files for service '{service_name}' across all specified products:"
                )
                
                for file_info in all_matching_files:
                    file_path = file_info['file_path']
                    product_name = file_info['product_name']
                    matches = file_info['matches']
                    relative_path = os.path.relpath(file_path, repo_dir)
                    
                    match_details = "\n".join([f"  - {match['key']}: {match['value']}" for match in matches])
                    yield RunResponse(
                        run_id=self.run_id,
                        content=f"Product: {product_name}\nFile: {relative_path}\nMatching keys:\n{match_details}"
                    )
                
        except Exception as e:
            yield RunResponse(
                run_id=self.run_id,
                content=f"Error during processing: {str(e)}"
            )

    async def arun(self, github_url: str, services_info: List[Dict[str, Any]], target_dir: Optional[str] = None,
               username: Optional[str] = None, token: Optional[str] = None) -> AsyncIterator[RunResponse]:
        """Asynchronous version of the run method.

        Args:
            github_url (str): URL of the GitHub repository to clone
            services_info (List[Dict[str, Any]]): List of dictionaries with service_name and product_names
                Example 1: [{"service_name": "user-api", "product_name": "corp"}]
                Example 2: [{"service_name": "user-api", "product_names": ["corp", "sophia-vpbank"]}]
            target_dir (Optional[str]): Target directory for cloning. If None, a temp directory is used.
            username (Optional[str]): GitHub username for private repository authentication
            token (Optional[str]): GitHub personal access token for private repository authentication

        Returns:
            AsyncIterator[RunResponse]: Async iterator of run responses.
        """
        # Clone the repository
        logger.info(f"Cloning GitHub repository: {github_url}")
        yield RunResponse(
            run_id=self.run_id,
            content=f"Starting repository clone for {github_url}..."
        )
        
        try:
            # Clone the repository
            repo_dir = self.clone_repository(github_url, target_dir, username, token)
            yield RunResponse(
                run_id=self.run_id,
                content=f"Repository cloned successfully to {repo_dir}."
            )
            
            # Search for YAML files for each service
            for service_info in services_info:
                service_name = service_info.get("service_name")
                
                # Support both single product_name and list of product_names
                product_names = service_info.get("product_names") or [service_info.get("product_name")]
                
                # Ensure product_names is a list
                if isinstance(product_names, str):
                    product_names = [product_names]
                    
                if not service_name or not product_names or None in product_names:
                    yield RunResponse(
                        run_id=self.run_id,
                        content=f"Error: Missing service_name or valid product_names in service info: {service_info}"
                    )
                    continue
                
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"Searching for YAML files for service '{service_name}' across products: {', '.join(product_names)}"
                )
                
                all_matching_files = []
                
                # Process each product name and collect all matching files
                for product_name in product_names:
                    # Search for YAML files matching the path pattern
                    logger.info(f"Searching for YAML files in product '{product_name}'...")
                    
                    yaml_files = self.search_yaml_files(repo_dir, product_name)
                    
                    if not yaml_files:
                        logger.info(f"No YAML files found for product '{product_name}'")
                        continue
                
                    # Filter YAML files by service name
                    matching_files = self.filter_yaml_by_service(yaml_files, service_name)
                    
                    if not matching_files:
                        logger.info(f"No matches found for service '{service_name}' in product '{product_name}'")
                        continue
                        
                    # Add product name to each file info
                    for file_info in matching_files:
                        file_info['product_name'] = product_name
                    
                    all_matching_files.extend(matching_files)
                
                # Report consolidated results
                if not all_matching_files:
                    yield RunResponse(
                        run_id=self.run_id,
                        content=f"No YAML files found with image repository ending with '{service_name}' across the specified products"
                    )
                    continue
                
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"Found {len(all_matching_files)} YAML files for service '{service_name}' across all specified products:"
                )
                
                for file_info in all_matching_files:
                    file_path = file_info['file_path']
                    product_name = file_info['product_name']
                    matches = file_info['matches']
                    relative_path = os.path.relpath(file_path, repo_dir)
                    
                    match_details = "\n".join([f"  - {match['key']}: {match['value']}" for match in matches])
                    yield RunResponse(
                        run_id=self.run_id,
                        content=f"Product: {product_name}\nFile: {relative_path}\nMatching keys:\n{match_details}"
                    )
                
        except Exception as e:
            yield RunResponse(
                run_id=self.run_id,
                content=f"Error during processing: {str(e)}"
            )

    def search_yaml_files(self, repo_dir: str, product_name: str) -> List[str]:
        """Search for YAML files in the specified path pattern.
        
        Args:
            repo_dir (str): Path to the cloned repository
            product_name (str): Name of the product to search in values directory
            
        Returns:
            List[str]: List of YAML file paths matching the pattern
        """
        # Based on the observed repository structure, we need to search all cluster directories
        # and look for the product_name in the production directory
        values_dir = os.path.join(repo_dir, "values")
        all_yaml_files = []
        
        # Get all cluster directories
        if os.path.exists(values_dir):
            cluster_dirs = [d for d in os.listdir(values_dir) 
                          if os.path.isdir(os.path.join(values_dir, d))]
            
            for cluster in cluster_dirs:
                # Check if this cluster has a production directory
                prod_dir = os.path.join(values_dir, cluster, "production")
                if os.path.exists(prod_dir):
                    # If product_name is "production", search all directories under production
                    if product_name == "production":
                        search_pattern = os.path.join(prod_dir, "**", "*.yaml")
                        logger.info(f"Searching for YAML files with pattern: {search_pattern}")
                        yaml_files = glob.glob(search_pattern, recursive=True)
                    else:
                        # Otherwise, look for the specific product directory
                        prod_subdir = os.path.join(prod_dir, product_name)
                        if os.path.exists(prod_subdir):
                            search_pattern = os.path.join(prod_subdir, "**", "*.yaml")
                            logger.info(f"Searching for YAML files with pattern: {search_pattern}")
                            yaml_files = glob.glob(search_pattern, recursive=True)
                        else:
                            yaml_files = []
                    
                    # Filter out files in templates directories
                    filtered_files = [f for f in yaml_files if "templates" not in f.split(os.sep)]
                    
                    if len(yaml_files) != len(filtered_files):
                        logger.info(f"Excluded {len(yaml_files) - len(filtered_files)} files from templates directories")
                    
                    all_yaml_files.extend(filtered_files)
        
        logger.info(f"Found {len(all_yaml_files)} YAML files matching the pattern (excluding templates)")
        return all_yaml_files
    
    def filter_yaml_by_service(self, yaml_files: List[str], service_name: str) -> List[Dict[str, Any]]:
        """Filter YAML files to find those with keys ending with service_name in the image repository.
        
        Args:
            yaml_files (List[str]): List of YAML file paths
            service_name (str): Service name to match in image repository keys
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries with file path, matching key, and value
        """
        matching_files = []
        
        for file_path in yaml_files:
            try:
                with open(file_path, 'r') as f:
                    yaml_content = yaml.safe_load(f)
                
                # Search for keys ending with 'image.repository'
                matches = self._find_image_repository_keys(yaml_content, service_name)
                if matches:
                    file_info = {
                        'file_path': file_path,
                        'matches': matches
                    }
                    matching_files.append(file_info)
                    logger.info(f"Found matching YAML file: {file_path}")
            except Exception as e:
                logger.warning(f"Error processing YAML file {file_path}: {str(e)}")
                
        return matching_files
    
    def _find_image_repository_keys(self, yaml_data: Dict, service_name: str, 
                                   parent_key: str = '', matches: List[Dict] = None) -> List[Dict]:
        """Recursively search for keys ending with 'image.repository' that contain the service name.
        
        Args:
            yaml_data (Dict): YAML data to search through
            service_name (str): Service name to match
            parent_key (str): Parent key for tracking the full path
            matches (List[Dict]): List of matches found so far
            
        Returns:
            List[Dict]: List of matches with key paths and values
        """
        if matches is None:
            matches = []
            
        if not isinstance(yaml_data, dict):
            return matches
            
        for key, value in yaml_data.items():
            current_key = f"{parent_key}.{key}" if parent_key else key
            
            # Debug logging to see all repository values
            if key == "repository" and isinstance(value, str):
                logger.info(f"Found repository key: {current_key} with value: {value}")
                
                # Check if this is an image.repository key
                if parent_key.endswith("image"):
                    logger.info(f"Checking if '{value}' contains '{service_name}'")
                    
                    # Only check if the value ends exactly with the service_name
                    last_part = value.lower().split('/')[-1]
                    if last_part == service_name.lower():
                        logger.info(f"Match found! Value ends exactly with service name.")
                        matches.append({
                            'key': current_key,
                            'value': value
                        })
                    
            # Recursively search nested dictionaries
            if isinstance(value, dict):
                self._find_image_repository_keys(value, service_name, current_key, matches)
        
        return matches