"""
Gallery Enhancements Service
Provides enhanced features for video gallery including advanced filtering, 
sorting, analytics, and future tech integration
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

try:
    from backend.services.future_tech_integration_service import future_tech_integration_service
    FUTURE_TECH_AVAILABLE = True
except ImportError:
    future_tech_integration_service = None
    FUTURE_TECH_AVAILABLE = False


class GalleryEnhancements:
    """
    Enhanced gallery features:
    - Advanced filtering and sorting
    - Analytics and insights
    - Future tech integration
    - Smart recommendations
    - Performance metrics
    """
    
    def __init__(self):
        self.filter_options = {
            'status': ['completed', 'processing', 'failed', 'pending'],
            'quality_level': ['low', 'medium', 'high', 'a_plus'],
            'categories': [],
            'date_ranges': ['today', 'week', 'month', 'year', 'all']
        }
        self.sort_options = [
            'newest', 'oldest', 'title', 'duration', 'quality_score',
            'created_at', 'completed_at', 'views', 'popularity'
        ]
        self.analytics_cache = {}
    
    def enhance_gallery_list(self, videos: List[Dict[str, Any]], 
                           filters: Dict[str, Any] = None,
                           sort_by: str = 'newest') -> Dict[str, Any]:
        """
        Enhance gallery video list with additional data and features
        
        Args:
            videos: List of video dictionaries
            filters: Filter parameters
            sort_by: Sort option
        """
        enhanced_videos = []
        
        for video in videos:
            enhanced_video = video.copy()
            
            # Add calculated fields
            enhanced_video['duration_formatted'] = self._format_duration(video.get('duration', 0))
            enhanced_video['age'] = self._calculate_age(video.get('created_at'))
            enhanced_video['quality_score_percent'] = (video.get('quality_score', 0) * 100) if video.get('quality_score') else 0
            
            # Add future tech data if available
            if FUTURE_TECH_AVAILABLE:
                try:
                    # Check if video has future projection link
                    enhanced_video['future_tech_available'] = True
                except Exception as e:
                    enhanced_video['future_tech_available'] = False
            
            enhanced_videos.append(enhanced_video)
        
        # Apply advanced sorting
        sorted_videos = self._apply_sorting(enhanced_videos, sort_by)
        
        # Apply advanced filtering
        filtered_videos = self._apply_filtering(sorted_videos, filters or {})
        
        return {
            'videos': filtered_videos,
            'total': len(filtered_videos),
            'original_count': len(videos),
            'filters_applied': filters or {},
            'sort_by': sort_by,
            'enhancements': {
                'future_tech': FUTURE_TECH_AVAILABLE,
                'analytics': True,
                'smart_sorting': True
            }
        }
    
    def _apply_sorting(self, videos: List[Dict], sort_by: str) -> List[Dict]:
        """Apply sorting to video list"""
        if sort_by == 'newest':
            return sorted(videos, key=lambda v: v.get('created_at', ''), reverse=True)
        elif sort_by == 'oldest':
            return sorted(videos, key=lambda v: v.get('created_at', ''))
        elif sort_by == 'title':
            return sorted(videos, key=lambda v: v.get('title', '').lower())
        elif sort_by == 'duration':
            return sorted(videos, key=lambda v: v.get('duration', 0), reverse=True)
        elif sort_by == 'quality_score':
            return sorted(videos, key=lambda v: v.get('quality_score', 0), reverse=True)
        elif sort_by == 'popularity':
            # Combine views, likes, etc. if available
            return sorted(videos, key=lambda v: (
                v.get('views', 0) + v.get('likes', 0) * 2
            ), reverse=True)
        else:
            return videos
    
    def _apply_filtering(self, videos: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
        """Apply advanced filtering"""
        filtered = videos
        
        # Filter by status
        if 'status' in filters and filters['status']:
            status_filter = filters['status']
            if status_filter != 'all':
                filtered = [v for v in filtered if v.get('status') == status_filter]
        
        # Filter by quality
        if 'quality' in filters and filters['quality']:
            quality_filter = filters['quality'].lower()
            if quality_filter != 'all':
                filtered = [v for v in filtered if v.get('quality_level', '').lower() == quality_filter]
        
        # Filter by category
        if 'category' in filters and filters['category']:
            category_filter = filters['category']
            if category_filter:
                filtered = [v for v in filtered if v.get('category_name') == category_filter]
        
        # Filter by date range
        if 'date_range' in filters and filters['date_range']:
            date_range = filters['date_range']
            if date_range != 'all':
                filtered = self._filter_by_date_range(filtered, date_range)
        
        # Filter by search query
        if 'search' in filters and filters['search']:
            search_query = filters['search'].lower()
            filtered = [
                v for v in filtered
                if search_query in (v.get('title', '') or '').lower()
                or search_query in (v.get('description', '') or '').lower()
                or search_query in (v.get('prompt', '') or '').lower()
            ]
        
        return filtered
    
    def _filter_by_date_range(self, videos: List[Dict], date_range: str) -> List[Dict]:
        """Filter videos by date range"""
        now = datetime.utcnow()
        
        if date_range == 'today':
            cutoff = now - timedelta(days=1)
        elif date_range == 'week':
            cutoff = now - timedelta(weeks=1)
        elif date_range == 'month':
            cutoff = now - timedelta(days=30)
        elif date_range == 'year':
            cutoff = now - timedelta(days=365)
        else:
            return videos
        
        filtered = []
        for video in videos:
            created_at = video.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        video_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        video_date = created_at
                    
                    if video_date >= cutoff:
                        filtered.append(video)
                except Exception:
                    pass  # Skip videos with invalid dates
        
        return filtered
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to readable string"""
        if not seconds:
            return "N/A"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def _calculate_age(self, created_at: str) -> str:
        """Calculate age of video (e.g., '2 days ago')"""
        if not created_at:
            return "Unknown"
        
        try:
            if isinstance(created_at, str):
                video_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                video_date = created_at
            
            now = datetime.utcnow()
            delta = now - video_date
            
            if delta.days > 365:
                years = delta.days // 365
                return f"{years} year{'s' if years > 1 else ''} ago"
            elif delta.days > 30:
                months = delta.days // 30
                return f"{months} month{'s' if months > 1 else ''} ago"
            elif delta.days > 0:
                return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
            elif delta.seconds > 3600:
                hours = delta.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif delta.seconds > 60:
                minutes = delta.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "Just now"
        except Exception:
            return "Unknown"
    
    def get_gallery_analytics(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get analytics for gallery videos"""
        if not videos:
            return {
                'total_videos': 0,
                'analytics': {}
            }
        
        total = len(videos)
        completed = sum(1 for v in videos if v.get('status') == 'completed')
        processing = sum(1 for v in videos if v.get('status') == 'processing')
        failed = sum(1 for v in videos if v.get('status') == 'failed')
        
        # Quality distribution
        quality_dist = defaultdict(int)
        for video in videos:
            quality = video.get('quality_level', 'unknown')
            quality_dist[quality] += 1
        
        # Average quality score
        quality_scores = [v.get('quality_score', 0) for v in videos if v.get('quality_score')]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Total duration
        total_duration = sum(v.get('duration', 0) for v in videos)
        
        return {
            'total_videos': total,
            'completed': completed,
            'processing': processing,
            'failed': failed,
            'quality_distribution': dict(quality_dist),
            'average_quality_score': avg_quality,
            'total_duration_seconds': total_duration,
            'total_duration_formatted': self._format_duration(total_duration),
            'completion_rate': (completed / total * 100) if total > 0 else 0
        }
    
    def get_smart_recommendations(self, user_id: str, 
                                 videos: List[Dict[str, Any]],
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """Get smart video recommendations for user"""
        # Simple recommendation based on quality and recency
        # Could be enhanced with ML/AI in the future
        
        scored_videos = []
        for video in videos:
            if video.get('status') != 'completed':
                continue
            
            score = 0
            # Recency score (newer is better)
            age = self._calculate_age(video.get('created_at', ''))
            if 'day' in age or 'hour' in age or 'minute' in age:
                score += 10
            
            # Quality score
            quality_score = video.get('quality_score', 0)
            score += quality_score * 5
            
            # Quality level bonus
            quality_level = video.get('quality_level', '').lower()
            if quality_level == 'a_plus':
                score += 20
            elif quality_level == 'high':
                score += 10
            
            scored_videos.append((score, video))
        
        # Sort by score and return top N
        scored_videos.sort(key=lambda x: x[0], reverse=True)
        return [video for score, video in scored_videos[:limit]]


# Global instance
gallery_enhancements = GalleryEnhancements()

