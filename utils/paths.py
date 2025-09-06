"""Centralized path management for the AI Agent Framework."""

import os
import asyncio
from pathlib import Path
from typing import Optional, List, Union


class ProjectPaths:
    """Singleton class for managing project paths with async support."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._setup_paths()
            ProjectPaths._initialized = True
    
    def _setup_paths(self):
        """Initialize all project paths."""
        # Get the project root (parent of utils directory)
        self.project_root = Path(__file__).parent.parent
        
        # Core directories
        self.agents_dir = self.project_root / "agents"
        self.configs_dir = self.project_root / "configs"
        self.data_dir = self.project_root / "data"
        self.examples_dir = self.project_root / "examples"
        self.graphs_dir = self.project_root / "graphs"
        self.memory_dir = self.project_root / "memory"
        self.models_dir = self.project_root / "models"
        self.prompts_dir = self.project_root / "prompts"
        self.scripts_dir = self.project_root / "scripts"
        self.services_dir = self.project_root / "services"
        self.tests_dir = self.project_root / "tests"
        self.tools_dir = self.project_root / "tools"
        self.utils_dir = self.project_root / "utils"
        
        # Configuration files
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / "env.example"
        self.requirements_file = self.project_root / "requirements.txt"
        self.pyproject_file = self.project_root / "pyproject.toml"
        self.langgraph_config = self.project_root / "langgraph.json"
        
        # Ensure critical directories exist - skip in ASGI context to avoid blocking
        self._ensure_directories_sync()
    
    def _ensure_directories_sync(self):
        """Synchronously ensure critical directories exist, but only if safe."""
        import os
        
        # Check if we're in an ASGI context - if so, skip directory creation to avoid blocking
        if os.getenv('ASGI_APPLICATION') or os.getenv('UVICORN_HOST') or os.getenv('LANGGRAPH_API'):
            return
        
        critical_dirs = [
            self.data_dir,
            self.configs_dir / "scenarios"
        ]
        
        for directory in critical_dirs:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception:
                # Silently ignore errors in directory creation
                pass
    
    async def _ensure_directories(self):
        """Asynchronously ensure critical directories exist."""
        critical_dirs = [
            self.data_dir,
            self.configs_dir / "scenarios"
        ]
        
        # Use asyncio.to_thread to run directory creation in a separate thread
        await asyncio.gather(
            *[asyncio.to_thread(dir.mkdir, parents=True, exist_ok=True) 
              for dir in critical_dirs]
        )
    
    def get_config_path(self, config_name: str) -> Path:
        """
        Get path to a configuration file.
        
        Args:
            config_name: Name of the config file (with or without .yaml extension)
            
        Returns:
            Path to the configuration file
        """
        if not config_name.endswith(('.yaml', '.yml', '.json')):
            config_name += '.yaml'
        
        return self.configs_dir / config_name
    
    def get_scenario_path(self, scenario_name: str) -> Path:
        """
        Get path to a scenario configuration file.
        
        Args:
            scenario_name: Name of the scenario file (with or without .yaml extension)
            
        Returns:
            Path to the scenario file
        """
        if not scenario_name.endswith(('.yaml', '.yml')):
            scenario_name += '.yaml'
        
        return self.configs_dir / "scenarios" / scenario_name
    
    def get_data_path(self, filename: str) -> Path:
        """
        Get path to a data file.
        
        Args:
            filename: Name of the data file
            
        Returns:
            Path to the data file
        """
        return self.data_dir / filename
    
    def get_log_path(self, log_name: str = "app.log") -> Path:
        """
        Get path to a log file.
        
        Args:
            log_name: Name of the log file
            
        Returns:
            Path to the log file
        """
        logs_dir = self.data_dir / "logs"
        try:
            logs_dir.mkdir(exist_ok=True)
        except Exception:
            pass  # Ignore errors in ASGI context
        return logs_dir / log_name
    
    def get_temp_path(self, filename: str) -> Path:
        """
        Get path to a temporary file.
        
        Args:
            filename: Name of the temporary file
            
        Returns:
            Path to the temporary file
        """
        temp_dir = self.data_dir / "temp"
        try:
            temp_dir.mkdir(exist_ok=True)
        except Exception:
            pass  # Ignore errors in ASGI context
        return temp_dir / filename
    
    def get_cache_path(self, cache_name: str) -> Path:
        """
        Get path to a cache file.
        
        Args:
            cache_name: Name of the cache file
            
        Returns:
            Path to the cache file
        """
        cache_dir = self.data_dir / "cache"
        try:
            cache_dir.mkdir(exist_ok=True)
        except Exception:
            pass  # Ignore errors in ASGI context
        return cache_dir / cache_name
    
    def get_backup_path(self, filename: str) -> Path:
        """
        Get path to a backup file.
        
        Args:
            filename: Name of the backup file
            
        Returns:
            Path to the backup file
        """
        backup_dir = self.data_dir / "backups"
        try:
            backup_dir.mkdir(exist_ok=True)
        except Exception:
            pass  # Ignore errors in ASGI context
        return backup_dir / filename
    
    def get_relative_path(self, path: Path) -> str:
        """
        Get relative path from project root.
        
        Args:
            path: Absolute path
            
        Returns:
            Relative path string
        """
        try:
            return str(path.relative_to(self.project_root))
        except ValueError:
            # Path is not relative to project root
            return str(path)
    
    def is_project_file(self, path: Path) -> bool:
        """
        Check if a path is within the project directory.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is within project, False otherwise
        """
        try:
            path.relative_to(self.project_root)
            return True
        except ValueError:
            return False
    
    def list_config_files(self) -> List[Path]:
        """
        List all configuration files.
        
        Returns:
            List of configuration file paths
        """
        config_files = []
        
        # Main config files
        for pattern in ["*.yaml", "*.yml", "*.json"]:
            config_files.extend(self.configs_dir.glob(pattern))
        
        # Scenario files
        scenarios_dir = self.configs_dir / "scenarios"
        if scenarios_dir.exists():
            for pattern in ["*.yaml", "*.yml"]:
                config_files.extend(scenarios_dir.glob(pattern))
        
        return sorted(config_files)
    
    def list_data_files(self, pattern: str = "*") -> List[Path]:
        """
        List data files matching a pattern.
        
        Args:
            pattern: File pattern to match
            
        Returns:
            List of data file paths
        """
        if self.data_dir.exists():
            return sorted(self.data_dir.glob(pattern))
        return []
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Clean up temporary files older than specified age.
        
        Args:
            max_age_hours: Maximum age of files to keep in hours
        """
        import time
        
        temp_dir = self.data_dir / "temp"
        if not temp_dir.exists():
            return
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                    except OSError:
                        pass  # Ignore errors when deleting files


# Global instance
paths = ProjectPaths()


def get_project_root() -> Path:
    """Get the project root directory."""
    return paths.project_root


def get_config_path(config_name: str) -> Path:
    """Get path to a configuration file."""
    return paths.get_config_path(config_name)


def get_data_path(filename: str) -> Path:
    """Get path to a data file."""
    return paths.get_data_path(filename)


def get_log_path(log_name: str = "app.log") -> Path:
    """Get path to a log file."""
    return paths.get_log_path(log_name)


def get_temp_path(filename: str) -> Path:
    """Get path to a temporary file."""
    return paths.get_temp_path(filename)


def get_cache_path(cache_name: str) -> Path:
    """Get path to a cache file."""
    return paths.get_cache_path(cache_name)


def ensure_data_dir() -> Path:
    """Ensure data directory exists and return its path."""
    try:
        paths.data_dir.mkdir(exist_ok=True)
    except Exception:
        pass  # Ignore errors in ASGI context
    return paths.data_dir


def cleanup_temp_files(max_age_hours: int = 24):
    """Clean up temporary files older than specified age."""
    paths.cleanup_temp_files(max_age_hours)
