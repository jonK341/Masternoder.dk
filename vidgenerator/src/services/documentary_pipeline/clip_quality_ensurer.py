"""
Clip Quality Ensurer
Ensures all generated clips are properly saved and available for gallery editing
Handles separated video and audio files
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from pathlib import Path


class ClipQualityEnsurer:
    """Ensures clip quality and proper storage for gallery editing"""
    
    def __init__(self):
        self.min_clip_duration = 5  # Minimum 5 seconds
        self.max_clip_duration = 15  # Maximum 15 seconds
        self.required_clips = 20  # Minimum clips for a complete documentary
        self.quality_threshold = 0.7  # Minimum quality score
    
    def ensure_clip_quality(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure clip meets quality standards
        
        Args:
            clip_data: Clip data dictionary
        
        Returns:
            Quality assessment and recommendations
        """
        assessment = {
            'meets_standards': True,
            'issues': [],
            'recommendations': [],
            'quality_score': 0.0
        }
        
        # Check duration
        duration = clip_data.get('duration', 0)
        if duration < self.min_clip_duration:
            assessment['meets_standards'] = False
            assessment['issues'].append(f'Duration too short: {duration}s (min: {self.min_clip_duration}s)')
        elif duration > self.max_clip_duration:
            assessment['issues'].append(f'Duration long: {duration}s (max: {self.max_clip_duration}s)')
        
        # Check file existence
        video_path = clip_data.get('video_path')
        if video_path and not os.path.exists(video_path):
            assessment['meets_standards'] = False
            assessment['issues'].append(f'Video file not found: {video_path}')
        
        # Check file size
        if video_path and os.path.exists(video_path):
            file_size = os.path.getsize(video_path)
            if file_size < 1000:  # Less than 1KB is suspicious
                assessment['meets_standards'] = False
                assessment['issues'].append(f'Video file too small: {file_size} bytes')
        
        # Check quality score
        quality_score = clip_data.get('quality_score', 0)
        if quality_score < self.quality_threshold:
            assessment['meets_standards'] = False
            assessment['issues'].append(f'Quality score too low: {quality_score} (min: {self.quality_threshold})')
        
        assessment['quality_score'] = quality_score
        
        # Generate recommendations
        if not assessment['meets_standards']:
            assessment['recommendations'].append('Regenerate clip with improved settings')
            if duration < self.min_clip_duration:
                assessment['recommendations'].append('Increase clip duration')
            if quality_score < self.quality_threshold:
                assessment['recommendations'].append('Use Quality AI for better results')
        
        return assessment
    
    def separate_video_audio(self, clip_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Separate video and audio files
        
        Args:
            clip_path: Path to video file
            output_dir: Output directory for separated files
        
        Returns:
            Paths to separated video and audio files
        """
        try:
            import subprocess
            from pathlib import Path
            
            clip_file = Path(clip_path)
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Extract audio
            audio_path = output_path / f"{clip_file.stem}_audio.wav"
            subprocess.run([
                'ffmpeg', '-i', str(clip_path),
                '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
                '-y', str(audio_path)
            ], check=True, capture_output=True)
            
            # Extract video (video only, no audio)
            video_only_path = output_path / f"{clip_file.stem}_video.mp4"
            subprocess.run([
                'ffmpeg', '-i', str(clip_path),
                '-vn', '-c:v', 'copy',
                '-y', str(video_only_path)
            ], check=True, capture_output=True)
            
            return {
                'success': True,
                'video_path': str(video_only_path),
                'audio_path': str(audio_path),
                'original_path': clip_path
            }
        except Exception as e:
            print(f"[ClipQuality] Separation error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def ensure_clips_for_gallery(self, clips: List[Dict[str, Any]], doc_id: str) -> Dict[str, Any]:
        """
        Ensure all clips are properly saved and ready for gallery editing
        
        Args:
            clips: List of clip data
            doc_id: Documentary ID
        
        Returns:
            Status of clip preparation
        """
        from src.db.models import db, MovieClip, Documentary
        
        status = {
            'total_clips': len(clips),
            'saved_clips': 0,
            'failed_clips': 0,
            'separated_clips': 0,
            'ready_for_editing': False
        }
        
        try:
            # Get documentary
            documentary = Documentary.query.get(doc_id)
            if not documentary:
                status['error'] = 'Documentary not found'
                return status
            
            # Process each clip
            for clip_data in clips:
                try:
                    # Ensure quality
                    quality_check = self.ensure_clip_quality(clip_data)
                    
                    if not quality_check['meets_standards']:
                        print(f"[ClipQuality] Clip {clip_data.get('id')} does not meet standards")
                        status['failed_clips'] += 1
                        continue
                    
                    # Save clip to database
                    clip_id = clip_data.get('id') or f"{doc_id}_clip_{status['saved_clips']}"
                    
                    # Check if clip already exists
                    existing_clip = MovieClip.query.filter_by(id=clip_id).first()
                    
                    if existing_clip:
                        # Update existing clip
                        existing_clip.video_path = clip_data.get('video_path', '')
                        existing_clip.audio_path = clip_data.get('audio_path', '')
                        existing_clip.duration = clip_data.get('duration', 0)
                        existing_clip.quality_score = quality_check['quality_score']
                        existing_clip.updated_at = datetime.utcnow()
                    else:
                        # Create new clip
                        new_clip = MovieClip(
                            id=clip_id,
                            documentary_id=doc_id,
                            video_path=clip_data.get('video_path', ''),
                            audio_path=clip_data.get('audio_path', ''),
                            duration=clip_data.get('duration', 0),
                            quality_score=quality_check['quality_score'],
                            order_index=status['saved_clips'],
                            metadata=clip_data.get('metadata', {})
                        )
                        db.session.add(new_clip)
                    
                    # Separate video and audio if not already separated
                    video_path = clip_data.get('video_path', '')
                    if video_path and not clip_data.get('audio_path'):
                        output_dir = os.path.join(
                            os.path.dirname(video_path),
                            'separated',
                            clip_id
                        )
                        separation_result = self.separate_video_audio(video_path, output_dir)
                        
                        if separation_result.get('success'):
                            # Update clip with separated paths
                            if existing_clip:
                                existing_clip.video_path = separation_result['video_path']
                                existing_clip.audio_path = separation_result['audio_path']
                            status['separated_clips'] += 1
                    
                    status['saved_clips'] += 1
                    
                except Exception as e:
                    print(f"[ClipQuality] Error processing clip: {e}")
                    status['failed_clips'] += 1
                    continue
            
            # Commit all changes
            db.session.commit()
            
            # Check if we have enough clips for editing
            if status['saved_clips'] >= self.required_clips:
                status['ready_for_editing'] = True
                documentary.status = 'ready_for_editing'
                db.session.commit()
            
            print(f"[ClipQuality] Saved {status['saved_clips']} clips for documentary {doc_id}")
            
        except Exception as e:
            print(f"[ClipQuality] Error ensuring clips: {e}")
            import traceback
            traceback.print_exc()
            status['error'] = str(e)
            db.session.rollback()
        
        return status


# Global instance
clip_quality_ensurer = ClipQualityEnsurer()

