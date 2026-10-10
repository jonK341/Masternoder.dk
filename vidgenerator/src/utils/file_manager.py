"""
File Manager - Handles output file management for the video generation pipeline
"""
import os
from pathlib import Path
from typing import Optional


class FileManager:
    """Manages file paths for pipeline output"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize file manager
        
        Args:
            output_dir: Custom output directory (optional)
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Default to output directory in project root or environment variable
            base_output = os.getenv('OUTPUT_DIR', 'output')
            
            # Try to find project root
            current_path = Path(__file__).resolve()
            # Go up from src/utils/file_manager.py to project root
            project_root = current_path.parent.parent.parent
            
            self.output_dir = project_root / base_output / "videos"
        
        # Also check for production path
        if os.path.exists('/var/www/html/vidgenerator/output'):
            self.output_dir = Path('/var/www/html/vidgenerator/output/videos')
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage manager (for external storage like S3) - optional
        self.storage_manager = None
        try:
            # Try to initialize external storage if configured
            if os.getenv('USE_EXTERNAL_STORAGE', '').lower() == 'true':
                # External storage integration can be added here
                pass
        except Exception:
            pass  # External storage is optional
    
    def get_output_path(self, filename: str) -> Path:
        """
        Get output path for a file
        
        Args:
            filename: Name of the file
        
        Returns:
            Path object for the output file
        """
        return self.output_dir / filename
    
    def get_clips_dir(self) -> Path:
        """Get directory for video clips"""
        clips_dir = self.output_dir / "clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        return clips_dir
    
    def get_thumbnails_dir(self) -> Path:
        """Get directory for thumbnails"""
        thumbnails_dir = self.output_dir / "thumbnails"
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        return thumbnails_dir
    
    def ensure_dir_exists(self, file_path: Path) -> Path:
        """Ensure directory for file exists"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

