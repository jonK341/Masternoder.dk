"""
Subtitle Generator from External Sources
Generates subtitles for documentaries from various external sources
"""
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import re


class SubtitleGenerator:
    """Generate subtitles from external sources"""
    
    def __init__(self):
        self.sources = {
            'whisper': {
                'name': 'OpenAI Whisper',
                'type': 'speech_to_text',
                'requires_api': True
            },
            'youtube': {
                'name': 'YouTube Auto-captions',
                'type': 'captions',
                'requires_api': True
            },
            'assemblyai': {
                'name': 'AssemblyAI',
                'type': 'speech_to_text',
                'requires_api': True
            },
            'rev': {
                'name': 'Rev.com',
                'type': 'human_transcription',
                'requires_api': True
            },
            'wikipedia': {
                'name': 'Wikipedia',
                'type': 'text_extraction',
                'requires_api': False
            }
        }
    
    def generate_subtitles_from_audio(self, audio_path: str, language: str = 'en') -> Dict[str, Any]:
        """
        Generate subtitles from audio file using speech-to-text
        
        Args:
            audio_path: Path to audio file
            language: Language code (default: 'en')
        
        Returns:
            Subtitle data in SRT format
        """
        # Placeholder for actual implementation
        # In production, this would call Whisper API or similar
        subtitles = {
            'format': 'srt',
            'language': language,
            'subtitles': [],
            'source': 'whisper',
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Simulated subtitle generation
        # In production: Call Whisper API or AssemblyAI
        return subtitles
    
    def generate_subtitles_from_text(self, text: str, timing_data: List[Dict] = None) -> Dict[str, Any]:
        """
        Generate subtitles from text content
        
        Args:
            text: Text content to convert to subtitles
            timing_data: Optional timing information
        
        Returns:
            Subtitle data in SRT format
        """
        subtitles = {
            'format': 'srt',
            'language': 'en',
            'subtitles': [],
            'source': 'text',
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Split text into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Generate timing (5 seconds per sentence, or use provided timing)
        current_time = 0
        for i, sentence in enumerate(sentences[:50]):  # Limit to 50 sentences
            duration = 5.0  # Default 5 seconds per sentence
            if timing_data and i < len(timing_data):
                duration = timing_data[i].get('duration', 5.0)
            
            subtitle_entry = {
                'index': i + 1,
                'start_time': current_time,
                'end_time': current_time + duration,
                'text': sentence
            }
            
            subtitles['subtitles'].append(subtitle_entry)
            current_time += duration
        
        return subtitles
    
    def generate_subtitles_from_wikipedia(self, topic: str, video_duration: float) -> Dict[str, Any]:
        """
        Generate subtitles from Wikipedia content
        
        Args:
            topic: Topic to search on Wikipedia
            video_duration: Duration of video in seconds
        
        Returns:
            Subtitle data
        """
        try:
            # Fetch Wikipedia summary
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
            response = requests.get(url, timeout=10)
            
            if response.ok:
                data = response.json()
                extract = data.get('extract', '')
                
                # Generate subtitles from extract
                return self.generate_subtitles_from_text(extract, None)
        except Exception as e:
            print(f"[Subtitle] Wikipedia fetch error: {e}")
        
        return {
            'format': 'srt',
            'language': 'en',
            'subtitles': [],
            'source': 'wikipedia',
            'error': 'Failed to fetch Wikipedia content'
        }
    
    def format_as_srt(self, subtitle_data: Dict[str, Any]) -> str:
        """
        Format subtitle data as SRT (SubRip) format
        
        Args:
            subtitle_data: Subtitle data dictionary
        
        Returns:
            SRT formatted string
        """
        srt_lines = []
        
        for entry in subtitle_data.get('subtitles', []):
            index = entry.get('index', 0)
            start = self._format_timestamp(entry.get('start_time', 0))
            end = self._format_timestamp(entry.get('end_time', 0))
            text = entry.get('text', '')
            
            srt_lines.append(f"{index}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")  # Empty line between entries
        
        return "\n".join(srt_lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as SRT timestamp (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def save_subtitles(self, subtitle_data: Dict[str, Any], output_path: str) -> bool:
        """
        Save subtitles to file
        
        Args:
            subtitle_data: Subtitle data
            output_path: Path to save subtitle file
        
        Returns:
            True if successful
        """
        try:
            srt_content = self.format_as_srt(subtitle_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            print(f"[Subtitle] Saved subtitles to {output_path}")
            return True
        except Exception as e:
            print(f"[Subtitle] Save error: {e}")
            return False


# Global instance
subtitle_generator = SubtitleGenerator()

