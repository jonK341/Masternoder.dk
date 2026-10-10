"""
SeaGOAT - Semantic Code Search Integration
Open source semantic code search tool
"""

import os
import subprocess
from typing import List, Dict, Optional

class SeaGOATService:
    """Service for semantic code search using SeaGOAT"""
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize SeaGOAT service
        
        Args:
            repo_path: Path to code repository to search
        """
        self.repo_path = repo_path or os.getcwd()
        self.seagoat_installed = self._check_installation()
    
    def _check_installation(self) -> bool:
        """Check if SeaGOAT is installed"""
        try:
            result = subprocess.run(
                ['seagoat', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search code using semantic search
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of search results with file paths and code snippets
        """
        if not self.seagoat_installed:
            return []
        
        try:
            result = subprocess.run(
                ['seagoat', 'search', query, '--limit', str(limit)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse SeaGOAT output
                return self._parse_results(result.stdout)
            else:
                return []
        except Exception as e:
            print(f"SeaGOAT search error: {e}")
            return []
    
    def _parse_results(self, output: str) -> List[Dict]:
        """Parse SeaGOAT search results"""
        results = []
        # SeaGOAT output format may vary - adjust parsing as needed
        lines = output.strip().split('\n')
        for line in lines:
            if line.strip():
                results.append({
                    'file': line,
                    'snippet': '',
                    'relevance': 0.0
                })
        return results
    
    def install(self) -> bool:
        """Install SeaGOAT if not already installed"""
        if self.seagoat_installed:
            return True
        
        try:
            subprocess.run(
                ['pip', 'install', 'seagoat-code-search'],
                check=True,
                timeout=120
            )
            self.seagoat_installed = True
            return True
        except Exception as e:
            print(f"Failed to install SeaGOAT: {e}")
            return False

