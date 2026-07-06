"""
Video Gallery - View and manage generated videos
"""
import requests
import json
from typing import List, Dict, Optional
from datetime import datetime

BASE_URL = "http://localhost:5000"

class VideoGallery:
    """Video gallery manager"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
    
    def list_videos(
        self,
        status: Optional[str] = None,
        quality: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """List all videos with optional filters"""
        # Note: This would need a new API endpoint
        # For now, we'll use the progress endpoint to check individual videos
        print("[INFO] Video listing requires a new API endpoint")
        print("[INFO] Use check_progress() for individual videos")
        return []
    
    def get_video_info(self, doc_id: str) -> Optional[Dict]:
        """Get detailed information about a video"""
        try:
            response = requests.get(
                f"{self.base_url}/api/documentary/progress/{doc_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'id': doc_id,
                    'status': data.get('status'),
                    'progress': data.get('progress', 0),
                    'video_path': data.get('video_path'),
                    'quality_score': data.get('quality_score', 0.0),
                    'quality_level': data.get('quality_level', 'unknown'),
                    'quality_valid': data.get('quality_valid', False),
                    'meets_a_plus': data.get('quality_meets_a_plus', False),
                    'duration': data.get('duration', 0),
                    'created_at': data.get('created_at'),
                    'completed_at': data.get('completed_at')
                }
            return None
        except Exception as e:
            print(f"[ERROR] Error getting video info: {e}")
            return None
    
    def get_video_url(self, doc_id: str) -> Optional[str]:
        """Get video URL for viewing"""
        return f"{self.base_url}/api/documentary/video/{doc_id}"
    
    def format_video_info(self, video_info: Dict) -> str:
        """Format video information for display"""
        if not video_info:
            return "[ERROR] No video information available"
        
        lines = [
            f"\n{'='*70}",
            f"Video Information: {video_info.get('id', 'Unknown')[:8]}...",
            f"{'='*70}",
            f"Status: {video_info.get('status', 'unknown').upper()}",
            f"Progress: {video_info.get('progress', 0)}%",
        ]
        
        if video_info.get('quality_score') is not None:
            score = video_info.get('quality_score', 0.0)
            lines.append(f"Quality Score: {score:.3f}")
            lines.append(f"Quality Level: {video_info.get('quality_level', 'unknown')}")
            lines.append(f"Meets A+ Standard: {'Yes' if video_info.get('meets_a_plus') else 'No'}")
        
        if video_info.get('video_path'):
            lines.append(f"Video Path: {video_info.get('video_path')}")
            lines.append(f"Video URL: {self.get_video_url(video_info.get('id'))}")
        
        if video_info.get('duration'):
            lines.append(f"Duration: {video_info.get('duration')} seconds")
        
        lines.append(f"{'='*70}")
        return "\n".join(lines)

def main():
    """Gallery demo"""
    print("\n" + "="*70)
    print("Video Gallery - View Generated Videos")
    print("="*70)
    
    gallery = VideoGallery()
    
    # Example: Check a video
    print("\n[EXAMPLE] Checking video information")
    print("Enter a documentary ID (or press Enter to skip):")
    doc_id = input("Doc ID: ").strip()
    
    if doc_id:
        video_info = gallery.get_video_info(doc_id)
        if video_info:
            print(gallery.format_video_info(video_info))
        else:
            print("[ERROR] Could not retrieve video information")
    else:
        print("[INFO] Skipped - no ID provided")
        print("\n[TIP] Use the video ID from create_video() response")
        print("Example: python start_using.py to create videos")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARN] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

