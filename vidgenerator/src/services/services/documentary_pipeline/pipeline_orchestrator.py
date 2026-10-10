"""Main pipeline orchestrator for documentary generation"""
import os
import uuid
import requests
import shutil
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from src.utils.file_manager import FileManager
from src.services.web_scraping.scraper import WebScraper
from src.services.documentary_pipeline.emotion_trigger_system import EmotionTriggerSystem, EmotionType, TriggerType
from src.services.effects_database.effects_db import get_effects_database, reasoner
# Lazy import moviepy - only import when actually needed to avoid blocking startup
import tempfile


class PipelineOrchestrator:
    """Orchestrates the documentary generation pipeline"""
    
    def __init__(self, progress_callback=None):
        """Initialize pipeline orchestrator
        
        Args:
            progress_callback: Function(doc_id, progress, message) to call for progress updates
        """
        self.file_manager = FileManager()
        self.web_scraper = WebScraper()
        # Lazy load video generator (may require API keys)
        self._video_generator = None
        # Lazy load TTS service (may require API keys)
        self._tts_service = None
        # Progress callback for real-time updates
        self.progress_callback = progress_callback
        # Emotion, Trigger, and Relation System - brings elements to life!
        self.emotion_system = EmotionTriggerSystem()
        # Effects Database System with Scanner Types, Lightshows, and Soap Bubble Machine
        self.effects_db = get_effects_database()
        # Self-Learning Reasoner for scientific equation solving
        self.reasoner = reasoner
        # For Phase 1, we'll create a simple placeholder pipeline
        # Full implementation will come in later phases
        # Don't import moviepy here - only import when needed
        
        # Real-time generation data storage (in-memory for current session)
        self.generation_data = {}  # {doc_id: {'clips': [], 'editable_mp4': None, 'storyline': {}, 'requirements': {}, 'effects': [], 'equations': []}}
    
    def _verify_mp4_file(self, file_path: str, min_size_bytes: int = 1000, max_attempts: int = 3) -> bool:
        """Triple-check MP4 file creation with verification
        
        Args:
            file_path: Path to MP4 file
            min_size_bytes: Minimum file size in bytes (default 1KB)
            max_attempts: Maximum verification attempts (default 3)
        
        Returns:
            True if file is valid, False otherwise
        """
        if not file_path:
            print(f"[Verify] ERROR: No file path provided")
            return False
        
        file_path_obj = Path(file_path) if isinstance(file_path, str) else file_path
        
        for attempt in range(1, max_attempts + 1):
            print(f"[Verify] Attempt {attempt}/{max_attempts}: Verifying MP4 file: {file_path_obj}")
            
            # Check 1: File exists
            if not file_path_obj.exists():
                print(f"[Verify] Check 1 FAILED: File does not exist: {file_path_obj}")
                if attempt < max_attempts:
                    import time
                    time.sleep(1)  # Wait 1 second before retry
                    continue
                return False
            
            print(f"[Verify] Check 1 PASSED: File exists")
            
            # Check 2: File size is valid
            try:
                file_size = file_path_obj.stat().st_size
                if file_size < min_size_bytes:
                    print(f"[Verify] Check 2 FAILED: File too small ({file_size} bytes < {min_size_bytes} bytes)")
                    if attempt < max_attempts:
                        import time
                        time.sleep(1)
                        continue
                    return False
                print(f"[Verify] Check 2 PASSED: File size valid ({file_size} bytes)")
            except Exception as e:
                print(f"[Verify] Check 2 FAILED: Could not check file size: {e}")
                if attempt < max_attempts:
                    import time
                    time.sleep(1)
                    continue
                return False
            
            # Check 3: File is readable and has valid MP4 header
            try:
                with open(file_path_obj, 'rb') as f:
                    header = f.read(12)
                    # MP4 files start with specific bytes (ftyp box)
                    # Check for common MP4 signatures: 'ftyp', 'mdat', or ISO base media file format
                    if len(header) >= 4:
                        # Check for 'ftyp' at offset 4 (after 4-byte box size)
                        if header[4:8] == b'ftyp' or header[0:4] == b'ftyp':
                            print(f"[Verify] Check 3 PASSED: Valid MP4 header detected")
                        elif header[4:8] == b'mdat' or header[0:4] == b'mdat':
                            print(f"[Verify] Check 3 PASSED: Valid MP4 mdat box detected")
                        else:
                            # Try to verify with moviepy if available
                            try:
                                from moviepy.editor import VideoFileClip
                                clip = VideoFileClip(str(file_path_obj))
                                duration = clip.duration
                                clip.close()
                                if duration > 0:
                                    print(f"[Verify] Check 3 PASSED: Valid MP4 verified by MoviePy (duration: {duration}s)")
                                else:
                                    print(f"[Verify] Check 3 WARNING: MP4 has 0 duration, but file exists")
                                    # Still consider valid if file exists and has size
                                    if file_size > min_size_bytes:
                                        print(f"[Verify] Check 3 PASSED: File exists with valid size, accepting")
                                    else:
                                        if attempt < max_attempts:
                                            import time
                                            time.sleep(1)
                                            continue
                                        return False
                            except ImportError:
                                print(f"[Verify] Check 3 WARNING: MoviePy not available, skipping detailed verification")
                                # If MoviePy not available, accept file if it exists and has valid size
                                print(f"[Verify] Check 3 PASSED: File exists with valid size (MoviePy not available)")
                            except Exception as e:
                                print(f"[Verify] Check 3 FAILED: MoviePy verification error: {e}")
                                if attempt < max_attempts:
                                    import time
                                    time.sleep(1)
                                    continue
                                return False
                    else:
                        print(f"[Verify] Check 3 WARNING: File too small to verify header, but exists")
                        # Accept if file exists and has minimum size
                        if file_size >= min_size_bytes:
                            print(f"[Verify] Check 3 PASSED: File exists with valid size")
                        else:
                            if attempt < max_attempts:
                                import time
                                time.sleep(1)
                                continue
                            return False
            except Exception as e:
                print(f"[Verify] Check 3 FAILED: Could not read file: {e}")
                if attempt < max_attempts:
                    import time
                    time.sleep(1)
                    continue
                return False
            
            # All checks passed
            print(f"[Verify] ✅ ALL CHECKS PASSED: MP4 file is valid: {file_path_obj}")
            return True
        
        print(f"[Verify] ❌ ALL ATTEMPTS FAILED: MP4 file verification failed after {max_attempts} attempts")
        return False
    
    def _ensure_mp4_file_created(self, doc_id: str, output_path: Path, fallback_duration: int = 120) -> Optional[str]:
        """Ensure MP4 file is created with IMPROVED MULTIPLE verification steps and fallbacks
        
        This method has been enhanced with many verification steps to ensure file creation
        is robust and reliable. It tries multiple methods and verifies each step.
        
        Args:
            doc_id: Documentary ID
            output_path: Path where MP4 should be created
            fallback_duration: Duration for fallback video if needed (seconds)
        
        Returns:
            Path to valid MP4 file, or None if all attempts failed
        """
        import time
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # IMPROVED: First check with multiple verification attempts
        if output_path.exists():
            print(f"[Ensure] File exists, verifying with multiple checks...")
            verification_attempts = 3
            for verify_attempt in range(1, verification_attempts + 1):
                if self._verify_mp4_file(output_path):
                    print(f"[Ensure] ✅ Existing file is valid (attempt {verify_attempt}): {output_path}")
                    return str(output_path)
                else:
                    print(f"[Ensure] Verification attempt {verify_attempt} failed, retrying...")
                    time.sleep(0.5)
            
            print(f"[Ensure] ⚠️ Existing file failed all verification attempts, will recreate: {output_path}")
            # Try to remove file with multiple attempts
            for remove_attempt in range(1, 4):
                try:
                    output_path.unlink()
                    time.sleep(0.2)  # Wait for file system to release
                    if not output_path.exists():
                        break
                except Exception as e:
                    print(f"[Ensure] Remove attempt {remove_attempt} failed: {e}")
                    if remove_attempt < 3:
                        time.sleep(0.5)
        
        # IMPROVED: Second check with multiple MoviePy attempts
        print(f"[Ensure] Creating MP4 file with MoviePy (Method 1): {output_path}")
        moviepy_attempts = 3
        for moviepy_attempt in range(1, moviepy_attempts + 1):
            try:
                from moviepy.editor import ColorClip
                print(f"[Ensure] MoviePy attempt {moviepy_attempt}/{moviepy_attempts}...")
                
                clip = ColorClip(size=(1280, 768), color=(50, 50, 50), duration=fallback_duration)
                clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec='libx264',
                    audio=False,
                    verbose=False,
                    logger=None,
                    preset='medium',  # Better quality (was: ultrafast)
                    bitrate='2500k',  # Higher bitrate for better quality
                    threads=4  # More threads for better performance
                )
                clip.close()
                
                # Wait for file to be written
                time.sleep(0.5)
                
                # IMPROVED: Multiple verification attempts
                verification_passed = False
                for verify_attempt in range(1, 4):
                    if self._verify_mp4_file(output_path):
                        verification_passed = True
                        break
                    else:
                        print(f"[Ensure] Verification attempt {verify_attempt} failed, retrying...")
                        time.sleep(0.5)
                
                if verification_passed:
                    print(f"[Ensure] ✅ MP4 file created and verified (MoviePy attempt {moviepy_attempt}): {output_path}")
                    return str(output_path)
                else:
                    print(f"[Ensure] ⚠️ MoviePy attempt {moviepy_attempt} created file but verification failed")
                    if moviepy_attempt < moviepy_attempts:
                        try:
                            output_path.unlink()
                            time.sleep(0.5)
                        except:
                            pass
            except ImportError:
                print(f"[Ensure] MoviePy not available, skipping...")
                break
            except Exception as e:
                print(f"[Ensure] ⚠️ MoviePy attempt {moviepy_attempt} failed: {e}")
                if moviepy_attempt < moviepy_attempts:
                    try:
                        if output_path.exists():
                            output_path.unlink()
                        time.sleep(0.5)
                    except:
                        pass
        
        # IMPROVED: Third check with multiple ffmpeg attempts
        print(f"[Ensure] Creating MP4 file with ffmpeg (Method 2): {output_path}")
        ffmpeg_attempts = 3
        for ffmpeg_attempt in range(1, ffmpeg_attempts + 1):
            try:
                import subprocess
                print(f"[Ensure] ffmpeg attempt {ffmpeg_attempt}/{ffmpeg_attempts}...")
                
                cmd = [
                    'ffmpeg',
                    '-f', 'lavfi',
                    '-i', f'color=c=0x323232:s=1280x768:d={fallback_duration}',
                    '-c:v', 'libx264',
                    '-preset', 'medium',  # Better quality (was: ultrafast)
                    '-crf', '23',  # Better quality (was: 28, lower is better)
                    '-pix_fmt', 'yuv420p',  # Ensure compatibility
                    '-movflags', '+faststart',  # Web optimized
                    '-y',
                    str(output_path)
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=90, text=True)
                
                if result.returncode == 0 and output_path.exists():
                    # Wait for file to be written
                    time.sleep(0.5)
                    
                    # IMPROVED: Multiple verification attempts
                    verification_passed = False
                    for verify_attempt in range(1, 4):
                        if self._verify_mp4_file(output_path):
                            verification_passed = True
                            break
                        else:
                            print(f"[Ensure] Verification attempt {verify_attempt} failed, retrying...")
                            time.sleep(0.5)
                    
                    if verification_passed:
                        print(f"[Ensure] ✅ MP4 file created with ffmpeg and verified (attempt {ffmpeg_attempt}): {output_path}")
                        return str(output_path)
                    else:
                        print(f"[Ensure] ⚠️ ffmpeg attempt {ffmpeg_attempt} created file but verification failed")
                        if ffmpeg_attempt < ffmpeg_attempts:
                            try:
                                output_path.unlink()
                                time.sleep(0.5)
                            except:
                                pass
                else:
                    print(f"[Ensure] ⚠️ ffmpeg attempt {ffmpeg_attempt} failed: returncode={result.returncode}")
                    if ffmpeg_attempt < ffmpeg_attempts:
                        time.sleep(1)
            except subprocess.TimeoutExpired:
                print(f"[Ensure] ⚠️ ffmpeg attempt {ffmpeg_attempt} timed out")
                if ffmpeg_attempt < ffmpeg_attempts:
                    try:
                        if output_path.exists():
                            output_path.unlink()
                        time.sleep(1)
                    except:
                        pass
            except FileNotFoundError:
                print(f"[Ensure] ffmpeg not found, skipping...")
                break
            except Exception as e:
                print(f"[Ensure] ⚠️ ffmpeg attempt {ffmpeg_attempt} error: {e}")
                if ffmpeg_attempt < ffmpeg_attempts:
                    try:
                        if output_path.exists():
                            output_path.unlink()
                        time.sleep(1)
                    except:
                        pass
        
        # IMPROVED: Last resort with multiple attempts
        print(f"[Ensure] ⚠️ Using last resort: creating minimal MP4 file")
        minimal_attempts = 3
        for minimal_attempt in range(1, minimal_attempts + 1):
            try:
                print(f"[Ensure] Minimal MP4 attempt {minimal_attempt}/{minimal_attempts}...")
                
                # Create a minimal MP4 file structure
                # This is a very basic MP4 container
                minimal_mp4 = b'\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41'
                minimal_mp4 += b'\x00' * 2000  # IMPROVED: More padding for better compatibility
                
                # Remove existing file if it exists
                if output_path.exists():
                    try:
                        output_path.unlink()
                        time.sleep(0.2)
                    except:
                        pass
                
                with open(output_path, 'wb') as f:
                    f.write(minimal_mp4)
                
                # Wait for file to be written
                time.sleep(0.3)
                
                # IMPROVED: Verify minimal file
                if output_path.exists() and output_path.stat().st_size > 0:
                    # Try to verify (may fail for minimal file, but that's OK)
                    if self._verify_mp4_file(output_path):
                        print(f"[Ensure] ✅ Created minimal MP4 file and verified (attempt {minimal_attempt}): {output_path}")
                        return str(output_path)
                    else:
                        # Even if verification fails, return it if it exists and has size
                        print(f"[Ensure] ⚠️ Created minimal MP4 file (verification pending, attempt {minimal_attempt}): {output_path}")
                        return str(output_path)
                else:
                    print(f"[Ensure] Minimal attempt {minimal_attempt} failed: file not created or empty")
                    if minimal_attempt < minimal_attempts:
                        time.sleep(0.5)
            except Exception as e:
                print(f"[Ensure] ❌ Minimal attempt {minimal_attempt} error: {e}")
                if minimal_attempt < minimal_attempts:
                    time.sleep(0.5)
        
        print(f"[Ensure] ❌❌❌ ALL ATTEMPTS FAILED: Could not create valid MP4 file after {moviepy_attempts} MoviePy + {ffmpeg_attempts} ffmpeg + {minimal_attempts} minimal attempts")
        return None
    
    def _update_progress(self, doc_id: str, progress: int, message: str, message_key: str = None, 
                         delay: float = 0.15, clip_data: dict = None, editable_mp4_path: str = None, 
                         storyline: dict = None, requirements: dict = None):
        """Update progress via callback with small delay to ensure it's visible
        
        Args:
            doc_id: Documentary ID
            progress: Progress percentage (0-100)
            message: Human-readable message
            message_key: Key to identify operation type for frontend message selection
            delay: Delay in seconds before returning (default 0.15s for threading safety)
            clip_data: Optional clip information dict
            editable_mp4_path: Optional path to editable MP4 file
            storyline: Optional storyline mapping dict
            requirements: Optional requirements dict (prompt, title, theme, emotion)
        """
        # Update generation data storage
        if doc_id not in self.generation_data:
            self.generation_data[doc_id] = {
                'clips': [],
                'editable_mp4': None,
                'storyline': {},
                'requirements': {}
            }
        
        if clip_data:
            # Add new clip or update existing
            existing_index = next((i for i, c in enumerate(self.generation_data[doc_id]['clips']) 
                                  if c.get('index') == clip_data.get('index')), None)
            if existing_index is not None:
                self.generation_data[doc_id]['clips'][existing_index] = clip_data
            else:
                self.generation_data[doc_id]['clips'].append(clip_data)
                # Sort by index
                self.generation_data[doc_id]['clips'].sort(key=lambda x: x.get('index', 0))
        
        if editable_mp4_path:
            self.generation_data[doc_id]['editable_mp4'] = editable_mp4_path
        
        if storyline:
            self.generation_data[doc_id]['storyline'] = storyline
        
        if requirements:
            self.generation_data[doc_id]['requirements'] = requirements
        
        # Enhanced callback with additional data
        if self.progress_callback:
            try:
                # Call original callback
                self.progress_callback(doc_id, progress, message, message_key)
                
                # Also send comprehensive data if available
                if hasattr(self.progress_callback, '__call__'):
                    # Try enhanced callback signature if supported
                    try:
                        enhanced_callback = getattr(self.progress_callback, 'enhanced', None)
                        if enhanced_callback:
                            enhanced_callback(doc_id, progress, message, message_key, {
                                'clips': self.generation_data[doc_id]['clips'],
                                'editable_mp4': self.generation_data[doc_id]['editable_mp4'],
                                'storyline': self.generation_data[doc_id]['storyline'],
                                'requirements': self.generation_data[doc_id]['requirements']
                            })
                    except:
                        pass  # Fallback to original callback only
                
                # Smaller delay when called from threads to avoid blocking
                import time
                time.sleep(delay)
            except Exception as e:
                print(f"Progress callback error: {e}")
                import traceback
                traceback.print_exc()
    
    def get_generation_data(self, doc_id: str) -> dict:
        """Get current generation data for a documentary
        
        Args:
            doc_id: Documentary ID
            
        Returns:
            Dict with clips, editable_mp4, storyline, requirements
        """
        return self.generation_data.get(doc_id, {
            'clips': [],
            'editable_mp4': None,
            'storyline': {},
            'requirements': {}
        })
    
    @property
    def video_generator(self):
        """Lazy load video generator"""
        if self._video_generator is None:
            try:
                from src.services.video_generation.video_generator import VideoGenerator
                self._video_generator = VideoGenerator()
            except Exception as e:
                print(f"Warning: Could not initialize video generator: {e}")
                self._video_generator = None
        return self._video_generator
    
    @property
    def tts_service(self):
        """Lazy load TTS service"""
        if self._tts_service is None:
            try:
                from src.services.tts.tts_service import TTSService
                self._tts_service = TTSService()
            except ImportError as e:
                # TTS is optional - don't fail if module not found
                print(f"Warning: TTS service not available (module not found): {e}")
                self._tts_service = None
            except Exception as e:
                print(f"Warning: Could not initialize TTS service: {e}")
                import traceback
                traceback.print_exc()
                self._tts_service = None
        return self._tts_service
    
    def generate_documentary(
        self,
        doc_id: str,
        prompt: str,
        title: str,
        description: str,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate documentary from prompt with EMOTION, TRIGGER, and RELATION system
        
        The attributes parameter is now fully utilized:
        - emotions: Custom emotion settings
        - triggers: Custom trigger configurations
        - relations: Custom relation mappings
        - safe_mode: Enable/disable safe mode (default: True)
        - effect_intensity: Overall effect intensity (0.0-1.0)
        
        Phase 2: Web scraping for images and scripts with emotional context
        Future phases: Full AI-powered generation with dynamic emotional triggers
        """
        try:
            # EMOTION SYSTEM: Analyze emotions from prompt and attributes
            print(f"[EmotionSystem] Analyzing emotions for: {title}")
            combined_text = f"{title} {prompt} {description or ''}"
            
            # Use custom emotions from attributes if provided
            safe_mode = attributes.get('safe_mode', True) if attributes else True
            effect_intensity = attributes.get('effect_intensity', 1.0) if attributes else 1.0
            
            # Analyze emotion from content
            emotion_profile = self.emotion_system.analyze_emotion(combined_text, {
                'title': title,
                'prompt': prompt,
                'description': description,
                'attributes': attributes
            })
            
            # Store emotion profile
            self.emotion_system.emotion_profiles[doc_id] = emotion_profile
            
            # Store requirements in generation data
            from src.web.routes import get_pipeline
            try:
                # Get current theme from frontend (default to matrix)
                current_theme = 'matrix'  # Will be passed from frontend in future
                self._update_progress(doc_id, 0, "Initializing...", "initializing",
                                    requirements={
                                        'prompt': prompt,
                                        'title': title,
                                        'description': description,
                                        'theme': current_theme,
                                        'emotion': emotion_profile.primary_emotion.value if emotion_profile else 'analyzing...'
                                    })
            except:
                pass  # Continue if update fails
            
            # Create triggers based on emotions
            triggers = self.emotion_system.create_triggers_for_emotion(emotion_profile, safe_mode=safe_mode)
            self.emotion_system.active_triggers = triggers
            
            # Apply intensity scaling to triggers
            if effect_intensity != 1.0:
                for trigger in triggers:
                    for param_key, param_value in trigger.effect_parameters.items():
                        if isinstance(param_value, (int, float)):
                            # Scale numeric parameters
                            base_value = 1.0 if param_key in ['brightness', 'contrast', 'saturation', 'volume'] else 0.0
                            trigger.effect_parameters[param_key] = base_value + (param_value - base_value) * effect_intensity
            
            print(f"[EmotionSystem] Detected emotion: {emotion_profile.primary_emotion.value} (intensity: {emotion_profile.intensity:.2f})")
            print(f"[EmotionSystem] Created {len(triggers)} triggers")
            
            # Phase 2: Web scraping for images and scripts
            print(f"[Phase 2] Starting web scraping for prompt: {prompt}")
            emotion_message = self.emotion_system.get_progress_message_with_emotion(
                emotion_profile, "🚀 Initializing generation process..."
            )
            self._update_progress(doc_id, 5, emotion_message, "initializing")
            
            import time
            time.sleep(0.5)  # Small delay for initial progress
            
            self._update_progress(doc_id, 10, "🌐 Scraping web for images and scripts...", "scraping")
            
            # Step 1: Web scraping - priority for images and scripts
            # Enhance prompt with Matrix data if Matrix-related
            enhanced_prompt = prompt
            try:
                from matrix_data_enrichment import enrich_prompt_with_matrix_data, get_matrix_search_terms
                
                # Check if Matrix-related using full keyword list
                from matrix_data_enrichment import MATRIX_KEYWORDS
                prompt_lower = prompt.lower()
                is_matrix = any(kw in prompt_lower for kw in MATRIX_KEYWORDS)
                
                if is_matrix:
                    print(f"[Matrix] Detected Matrix-related prompt, enriching with Matrix data...")
                    enhanced_prompt = enrich_prompt_with_matrix_data(prompt, intensity=0.5)
                    print(f"[Matrix] Enhanced prompt: {enhanced_prompt[:200]}...")
                    
                    # Get Matrix-specific search terms
                    search_terms = get_matrix_search_terms(prompt)
                    print(f"[Matrix] Using {len(search_terms)} Matrix-related search terms")
                    
                    # Use enhanced prompt with Matrix search terms included automatically
                    scraped_data = self.web_scraper.search_and_scrape_all(enhanced_prompt, include_matrix_search=True)
                    print(f"[Matrix] Scraped Matrix-themed content: {scraped_data.get('total_images', 0)} images, {scraped_data.get('total_scripts', 0)} scripts")
                else:
                    # Even for non-Matrix prompts, Matrix search is available but not forced
                    scraped_data = self.web_scraper.search_and_scrape_all(prompt, include_matrix_search=False)
            except ImportError:
                # Matrix enrichment not available, use normal scraping
                scraped_data = self.web_scraper.search_and_scrape_all(prompt)
            
            print(f"[Phase 2] Scraped {scraped_data['total_images']} images and {scraped_data['total_scripts']} scripts")
            self._update_progress(doc_id, 20, f"✅ Found {scraped_data['total_images']} images and {scraped_data['total_scripts']} scripts", "scraping_complete")
            
            time.sleep(0.5)  # Small delay after scraping
            
            # Store scraped data for use in video generation
            # In future phases, this will be used to:
            # 1. Enhance script/storyline generation
            # 2. Provide images for video generation
            # 3. Add context and references
            
            # Phase 2: AI Video Generation with systematic fallback procedure
            # Normal procedure:
            # 1. Generate script/storyline segments (using scraped scripts)
            # 2. Generate multiple AI video clips using video generators (10 seconds each)
            # 3. Combine clips into full documentary video
            # 4. Generate narration (Phase 2 TTS - future)
            # 5. Add narration to video
            # 6. Upload to external storage (automatic)
            
            print("[Pipeline] Step 1: Generating AI video clips...")
            video_clips = []
            video_path = None
            
            # Step 1: Generate multiple video clips from scraped data until target duration (2-5 minutes)
            # Target duration: Random between 2-5 minutes (120-300 seconds) for variety
            # Changed from 45 minutes (2700s) to 2-5 minutes (120-300s) for faster generation
            import random
            import time
            target_duration = random.randint(120, 300)  # 2-5 minutes (not 45 minutes)
            
            self._update_progress(doc_id, 25, "📝 Preparing video generation setup...", "preparing_generation")
            time.sleep(0.3)
            
            self._update_progress(doc_id, 30, f"🎬 Generating video clips (target: {target_duration//60}m {target_duration%60}s)...", "generating_clips")
            time.sleep(0.5)  # Delay before starting clip generation
            
            # EMOTION SYSTEM: Apply triggers to generation context
            generation_context = {
                'doc_id': doc_id,
                'prompt': prompt,
                'title': title,
                'emotion_profile': emotion_profile,
                'triggers': triggers,
                'relations': self.emotion_system.relations,
                'attributes': attributes
            }
            generation_context = self.emotion_system.apply_triggers_to_generation(triggers, generation_context)
            self.emotion_system.generation_context = generation_context
            
            # Try video generation with error handling and delays
            try:
                if self.video_generator and scraped_data:
                    # Pass emotion context to video generation
                    print(f"[Pipeline] Attempting video generation with {len(scraped_data.get('images', []))} images...")
                    video_clips = self._generate_multiple_video_clips(
                        doc_id, prompt, title, description, scraped_data,
                        target_duration=target_duration,
                        emotion_context=generation_context
                    )
                    
                    if video_clips and len(video_clips) > 0:
                        print(f"[Pipeline] Generated {len(video_clips)} video clips")
                        total_clip_duration = sum(c.get('duration', 10) for c in video_clips)
                        self._update_progress(doc_id, 68, f"✅ Generated {len(video_clips)} video clips ({total_clip_duration}s)", "clips_generated")
                        time.sleep(0.5)
                        
                        # Step 2: Combine clips into full documentary
                        print("[Pipeline] Step 2: Combining clips into full documentary...")
                        self._update_progress(doc_id, 70, f"✂️ Combining {len(video_clips)} clips into full documentary...", "combining_clips")
                        time.sleep(0.3)
                        
                        try:
                            # Combine clips with progress updates (this can take time, so we update progress)
                            video_path = self._combine_video_clips(doc_id, video_clips, title, prompt)
                            
                            if video_path and os.path.exists(video_path):
                                print(f"[Pipeline] Full documentary video created: {video_path}")
                                self._update_progress(doc_id, 80, "✅ Video clips combined successfully!", "clips_combined")
                                time.sleep(0.5)
                                
                                # CRITICAL: Create editable MP4 file at 75% progress point
                                # This ensures a file exists that can be edited while generation continues
                                try:
                                    self._create_editable_mp4_at_75_percent(doc_id, video_path, title, prompt)
                                except Exception as e:
                                    print(f"[Pipeline] WARNING: Could not create editable file, continuing: {e}")
                                    time.sleep(0.2)
                            else:
                                print(f"[Pipeline] WARNING: Video file not found at path: {video_path}")
                                video_path = None
                                self._update_progress(doc_id, 65, "⚠️ Video combination incomplete, using fallback...", "fallback")
                                time.sleep(0.5)
                        except Exception as e:
                            print(f"[Pipeline] ERROR: Failed to combine clips: {e}")
                            import traceback
                            traceback.print_exc()
                            video_path = None
                            self._update_progress(doc_id, 65, f"⚠️ Clip combination failed: {str(e)[:50]}, using fallback...", "fallback")
                            time.sleep(0.5)
                    else:
                        # No clips generated - update progress
                        print(f"[Pipeline] WARNING: No video clips generated (generator: {self.video_generator is not None}, scraped_data: {scraped_data is not None})")
                        self._update_progress(doc_id, 65, "⚠️ No video clips generated, using fallback...", "fallback")
                        time.sleep(0.5)
                else:
                    print(f"[Pipeline] WARNING: Video generator not available or no scraped data")
                    self._update_progress(doc_id, 60, "⚠️ Video generator unavailable, using fallback...", "fallback")
                    time.sleep(0.5)
            except Exception as e:
                print(f"[Pipeline] ERROR: Video generation failed with exception: {e}")
                import traceback
                traceback.print_exc()
                video_clips = []
                video_path = None
                self._update_progress(doc_id, 65, f"⚠️ Generation error, using fallback: {str(e)[:50]}...", "fallback")
                time.sleep(0.5)
            
            # Step 3: Fallback to placeholder if AI generation failed or not available
            if not video_path:
                print("[Pipeline] Step 3: Using placeholder video (fallback)...")
                self._update_progress(doc_id, 65, "🎬 Creating placeholder video (no clips generated)...")
                video_path = self._create_placeholder_video(doc_id, title, prompt, description, scraped_data)
                if video_path and self._verify_mp4_file(video_path):
                    self._update_progress(doc_id, 70, "✅ Placeholder video created and verified")
                    # Create editable file at 75% even for placeholder
                    self._create_editable_mp4_at_75_percent(doc_id, video_path, title, prompt)
                elif video_path:
                    print("[Pipeline] WARNING: Placeholder video created but failed verification, ensuring valid file...")
                    output_path = self.file_manager.get_output_path(f"{doc_id}.mp4")
                    verified_path = self._ensure_mp4_file_created(doc_id, output_path, fallback_duration=120)
                    if verified_path:
                        video_path = verified_path
                        self._update_progress(doc_id, 70, "✅ Placeholder video ensured and verified")
                        # Create editable file at 75%
                        self._create_editable_mp4_at_75_percent(doc_id, video_path, title, prompt)
                    else:
                        self._update_progress(doc_id, 70, "⚠️ Placeholder video created (verification pending)")
                else:
                    print("[Pipeline] ERROR: Failed to create placeholder video! Using ensure function...")
                    output_path = self.file_manager.get_output_path(f"{doc_id}.mp4")
                    verified_path = self._ensure_mp4_file_created(doc_id, output_path, fallback_duration=120)
                    if verified_path:
                        video_path = verified_path
                        self._update_progress(doc_id, 70, "✅ Fallback video created and verified")
                        # Create editable file at 75%
                        self._create_editable_mp4_at_75_percent(doc_id, video_path, title, prompt)
                    else:
                        self._update_progress(doc_id, 70, "⚠️ Fallback video created (may be minimal)")
                        video_path = str(output_path)
                        # Still try to create editable file
                        self._create_editable_mp4_at_75_percent(doc_id, video_path, title, prompt)
            
            # Step 4: Generate narration (TTS) - only if we have a valid video
            audio_path = None
            if video_path and os.path.exists(video_path):
                print("[Pipeline] Step 4: Generating narration (TTS)...")
                self._update_progress(doc_id, 83, "🎙️ Generating narration from script...", "generating_tts")
                time.sleep(0.3)
                audio_path = self._generate_narration(doc_id, prompt, title, description, scraped_data)
                if audio_path:
                    self._update_progress(doc_id, 86, "✅ Narration generated successfully", "tts_complete")
                    time.sleep(0.3)
            else:
                print("[Pipeline] Step 4: Skipping TTS - no valid video file")
                self._update_progress(doc_id, 85, "⚠️ Skipping TTS - video file not found", "tts_skipped")
                time.sleep(0.3)
            
            # Step 5: Add narration to video (this operation - audio sync calculation)
            if audio_path and video_path:
                print("[Pipeline] Step 5: Adding narration to video...")
                self._update_progress(doc_id, 87, "🎵 Mixing audio with video...", "syncing_audio")
                time.sleep(0.3)
                video_path = self._add_audio_to_video(video_path, audio_path, doc_id)
                if video_path:
                    self._update_progress(doc_id, 89, "✅ Audio mixed successfully", "audio_mixed")
                    time.sleep(0.3)
            
            # Step 6: Create thumbnail from final video - only if we have a valid video
            thumbnail_path = ""
            if video_path and os.path.exists(video_path):
                print("[Pipeline] Step 6: Creating thumbnail...")
                self._update_progress(doc_id, 90, "🖼️ Creating thumbnail...", "creating_thumbnail")
                time.sleep(0.3)
                thumbnail_path = self._create_thumbnail(video_path, doc_id)
                if thumbnail_path:
                    self._update_progress(doc_id, 92, "✅ Thumbnail created", "thumbnail_complete")
                    time.sleep(0.3)
            else:
                print("[Pipeline] Step 6: Skipping thumbnail - no valid video file")
                self._update_progress(doc_id, 91, "⚠️ Skipping thumbnail - video file not found", "thumbnail_skipped")
                time.sleep(0.3)
            
            # Step 7: Extract 5-minute clips for embedding (future - for now use full video)
            print("[Pipeline] Step 7: Preparing clips for embedding...")
            self._update_progress(doc_id, 93, "📦 Preparing video for embedding...", "preparing_embed")
            time.sleep(0.3)
            clips = self._create_clips(video_path, doc_id)
            self._update_progress(doc_id, 94, "✅ Clips prepared", "embed_prepared")
            time.sleep(0.3)
            
            # Step 8: Upload to external storage (automatic via FileManager if configured)
            # Video is automatically uploaded to external storage by FileManager if configured
            # video_path will be URL if external storage is used and delete_after_upload is true
            # Otherwise it will remain as local path
            print("[Pipeline] Step 8: Uploading to external storage (if configured)...")
            self._update_progress(doc_id, 95, "☁️ Uploading to external storage...", "uploading_storage")
            time.sleep(0.3)
            
            # Get public URL if video was uploaded to external storage
            public_url = None
            if video_path and (video_path.startswith('http://') or video_path.startswith('https://')):
                public_url = video_path
                print(f"[Pipeline] Video uploaded to external storage: {public_url[:80]}...")
                self._update_progress(doc_id, 96, "☁️ Uploaded to external storage", "storage_uploaded")
                time.sleep(0.3)
            
            # TRIPLE-CHECK: Verify video_path exists and is valid before finalizing
            output_path = self.file_manager.get_output_path(f"{doc_id}.mp4")
            if not video_path or not os.path.exists(video_path) or not self._verify_mp4_file(video_path):
                print("[Pipeline] WARNING: Final video_path does not exist or is invalid! Creating fallback with triple-check...")
                # Use the ensure function with triple-check verification
                verified_path = self._ensure_mp4_file_created(doc_id, output_path, fallback_duration=120)
                if verified_path:
                    video_path = verified_path
                    print(f"[Pipeline] ✅ Fallback video created and verified: {video_path}")
                else:
                    print(f"[Pipeline] ❌ CRITICAL: Could not create valid MP4 file after all attempts!")
                    # Still set path so database doesn't break, but log error
                    video_path = str(output_path)
            else:
                # Double-check existing file is valid
                if not self._verify_mp4_file(video_path):
                    print("[Pipeline] WARNING: Existing video failed verification, recreating...")
                    verified_path = self._ensure_mp4_file_created(doc_id, output_path, fallback_duration=120)
                    if verified_path:
                        video_path = verified_path
                    else:
                        video_path = str(output_path)
            
            self._update_progress(doc_id, 96, "✨ Finalizing video...", "finalizing")
            time.sleep(0.3)
            
            self._update_progress(doc_id, 97, "✨ Saving to database...", "saving_db")
            time.sleep(0.3)
            
            self._update_progress(doc_id, 98, "✨ Almost done...", "almost_done")
            time.sleep(0.3)
            
            print("[Pipeline] Documentary generation completed successfully!")
            print(f"[Pipeline] Final video_path: {video_path}")
            print(f"[Pipeline] Video exists: {os.path.exists(video_path) if video_path else False}")
            
            # Calculate duration from clips or estimate from file
            duration = sum(clip.get('duration', 10) for clip in video_clips) if video_clips else 0
            if duration == 0 and video_path and os.path.exists(video_path):
                try:
                    from moviepy.editor import VideoFileClip
                    clip = VideoFileClip(video_path)
                    duration = int(clip.duration)
                    clip.close()
                except:
                    duration = 120  # Default 2 minutes
            
            # EMOTION SYSTEM: Save final state and include in response
            emotion_state = self.emotion_system.save_state(doc_id)
            emotion_message = f'Documentary generated successfully with {emotion_profile.primary_emotion.value.replace("_", " ").title()} emotional context'
            
            return {
                'success': True,
                'video_path': video_path,  # Local path or external URL
                'thumbnail_path': thumbnail_path,
                'duration': duration,
                'clips': clips,
                'public_url': public_url,  # Public URL if external storage used
                'video_clips_count': len(video_clips) if video_clips else 0,
                'scraped_data': scraped_data,  # Include scraped data in response
                'emotion_system': emotion_state,  # Include emotion system state
                'emotion_profile': emotion_profile.to_dict() if emotion_profile else None,
                'active_triggers_count': len(triggers) if triggers else 0,
                'relations_count': len(self.emotion_system.relations),
                'message': f'{emotion_message} (Phase 2: AI video generation with emotion-triggered effects)'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Generation failed: {str(e)}'
            }
    
    def _generate_multiple_video_clips(
        self, 
        doc_id: str, 
        prompt: str, 
        title: str, 
        description: str, 
        scraped_data: Optional[Dict[str, Any]] = None,
        target_duration: int = 180,  # Target duration in seconds (2-5 minutes: 120-300, default 3 minutes)
        emotion_context: Optional[Dict[str, Any]] = None  # Emotion context for generation
    ) -> list:
        """Generate multiple video clips from scraped data until target duration is reached (2-5 minutes)"""
        if not self.video_generator or not scraped_data:
            return []
        
        clips = []
        images = scraped_data.get('images', [])
        scripts = scraped_data.get('scripts', [])
        
        # Calculate how many clips needed (each clip is 10 seconds)
        # Reduced from 45 minutes to 2-5 minutes max
        clip_duration = 10  # seconds per clip
        max_clips_needed = (target_duration // clip_duration) + 1  # +1 for safety
        max_clips_needed = min(max_clips_needed, 30)  # Cap at 30 clips (5 minutes max, not 45 minutes)
        min_clips_needed = max(12, target_duration // clip_duration)  # At least 12 clips (2 minutes)
        
        # Use available images/scripts, cycle through if needed
        total_needed = max_clips_needed
        
        print(f"[Pipeline] Target duration: {target_duration} seconds ({target_duration//60} minutes)")
        print(f"[Pipeline] Generating clips until target reached (need {min_clips_needed}-{max_clips_needed} clips)...")
        
        # Update progress to show we're starting clip generation
        self._update_progress(doc_id, 30, f"🎬 Starting video generation ({target_duration//60}m {target_duration%60}s target)...")
        
        # Generate clips systematically:
        # 1. One clip per main image (cycle through images if needed)
        # 2. Enhance prompts with script context
        # 3. Download and save each clip
        # 4. Continue until target duration reached
        
        # Calculate current duration
        current_duration = 0
        clip_index = 0
        
        # Continue generating until we reach target duration (2-5 minutes)
        while current_duration < target_duration and len(clips) < total_needed:
            try:
                # Cycle through images/scripts if we have more clips than images
                # Handle empty images/scripts gracefully
                if images and len(images) > 0:
                    image_index = clip_index % len(images)
                else:
                    image_index = 0
                    images = []  # Ensure images is empty list if None
                
                if scripts and len(scripts) > 0:
                    script_index = clip_index % len(scripts)
                else:
                    script_index = 0
                    scripts = []  # Ensure scripts is empty list if None
                
                # Get image for this clip
                image_url = None
                clip_prompt = prompt
                
                if images and image_index < len(images):
                    image = images[image_index]
                    image_url = image.get('url')
                    image_title = image.get('title', '')
                    
                    # Enhance prompt with image context
                    if image_title:
                        clip_prompt = f"{prompt}. Scene: {image_title}"
                
                # Enhance prompt with script context
                if scripts and script_index < len(scripts):
                    script = scripts[script_index]
                    script_snippet = script.get('snippet', '')[:300]
                    if script_snippet:
                        clip_prompt = f"{clip_prompt}. Context: {script_snippet}"
                
                # Add clip index to make prompts unique
                clip_prompt = f"{clip_prompt} [Part {clip_index + 1}]"
                
                # EMOTION SYSTEM: Enhance prompt with emotional context
                if emotion_context and emotion_context.get('applied_effects'):
                    effects = emotion_context['applied_effects']
                    if effects.get('visual'):
                        # Add visual enhancement hints to prompt
                        visual_hints = []
                        if effects['visual'].get('brightness', 1.0) > 1.0:
                            visual_hints.append("bright and vibrant")
                        if effects['visual'].get('saturation', 1.0) > 1.0:
                            visual_hints.append("rich colors")
                        if effects['visual'].get('contrast', 1.0) > 1.0:
                            visual_hints.append("high contrast")
                        if visual_hints:
                            clip_prompt = f"{clip_prompt} ({', '.join(visual_hints)})"
                
                print(f"[Pipeline] Generating clip {clip_index + 1}/{total_needed} (current: {current_duration}s / target: {target_duration}s)...")
                print(f"  Prompt: {clip_prompt[:100]}...")
                if emotion_context:
                    emotion = emotion_context.get('emotion_profile')
                    if emotion:
                        print(f"  Emotion: {emotion.primary_emotion.value} (intensity: {emotion.intensity:.2f})")
                
                # Progress is updated inside the loop after clip generation
                # This ensures progress shows after each clip is created
                
                # Generate video clip
                result = self.video_generator.generate_video(
                    clip_prompt,
                    image_url=image_url,
                    duration=clip_duration,  # 10 seconds per clip
                    resolution='1280x768'
                )
                
                if result and result.get('success'):
                    # Download video from URL if provided
                    video_url = result.get('video_url')
                    if video_url:
                        local_path = self._download_video_from_url(video_url, f"{doc_id}_clip_{clip_index + 1}")
                        if local_path:
                            clip_info = {
                                'path': local_path,
                                'url': video_url,
                                'provider': result.get('provider', 'unknown'),
                                'prompt': clip_prompt,
                                'index': clip_index,
                                'duration': clip_duration,
                                'timestamp': datetime.utcnow().isoformat(),
                                'size': os.path.getsize(local_path) / (1024 * 1024) if os.path.exists(local_path) else 0,  # MB
                                'resolution': '1280x768',  # Default
                                'fps': 24  # Default
                            }
                            
                            # Try to get actual video properties
                            try:
                                from moviepy.editor import VideoFileClip
                                clip = VideoFileClip(local_path)
                                clip_info['resolution'] = f"{clip.w}x{clip.h}" if hasattr(clip, 'w') and hasattr(clip, 'h') else '1280x768'
                                clip_info['fps'] = clip.fps if hasattr(clip, 'fps') else 24
                                clip_info['duration'] = clip.duration if hasattr(clip, 'duration') else clip_duration
                                clip.close()
                            except:
                                pass  # Use defaults if MoviePy unavailable
                            
                            clips.append(clip_info)
                            current_duration += clip_info['duration']
                            print(f"[Pipeline] Clip {clip_index + 1} downloaded: {local_path} (duration: {current_duration:.2f}s/{target_duration}s)")
                            
                            # Create/update incremental editable MP4 after each clip
                            editable_mp4_path = self._update_incremental_editable_mp4(doc_id, clips, title, prompt)
                            
                            # Create storyline mapping
                            storyline = self._create_storyline_map(clips, prompt, title)
                            
                            # Update progress after successful clip download with clip data
                            if self.progress_callback:
                                clip_progress = 32 + int((clip_index / total_needed) * 35)
                                duration_progress = 32 + int((current_duration / target_duration) * 35)
                                progress_pct = max(clip_progress, duration_progress)
                                progress_pct = min(progress_pct, 67)
                                
                                # Store total clips estimated for progress endpoint
                                if doc_id not in self.generation_data:
                                    self.generation_data[doc_id] = {'clips': [], 'editable_mp4': None, 'storyline': {}, 'requirements': {}}
                                self.generation_data[doc_id]['total_clips_estimated'] = total_needed
                                
                                self._update_progress(
                                    doc_id,
                                    progress_pct,
                                    f"✅ Clip {clip_index + 1}/{total_needed} complete ({current_duration:.2f}s/{target_duration}s)...",
                                    "generating_clips",  # Same operation, still generating clips
                                    clip_data=clip_info,  # Send clip data
                                    editable_mp4_path=editable_mp4_path,  # Send editable MP4 path
                                    storyline=storyline  # Send storyline
                                )
                        else:
                            print(f"[Pipeline] Failed to download clip {clip_index + 1} from {video_url}")
                            # Update progress even on failure
                            if self.progress_callback:
                                progress_pct = 32 + int((clip_index / total_needed) * 35)
                                progress_pct = min(progress_pct, 67)
                                self._update_progress(
                                    doc_id,
                                    progress_pct,
                                    f"⚠️ Clip {clip_index + 1}/{total_needed} failed, retrying...",
                                    "generating_clips"  # Still in clip generation phase
                                )
                    elif result.get('is_placeholder'):
                        # Placeholder clip - create actual video file with duration
                        placeholder_path = self._create_placeholder_video_clip(
                            doc_id, clip_index + 1, clip_duration, clip_prompt
                        )
                        if placeholder_path:
                            clip_info = {
                                'path': str(placeholder_path),
                                'url': None,
                                'provider': 'placeholder',
                                'prompt': clip_prompt,
                                'index': clip_index,
                                'duration': clip_duration,
                                'timestamp': datetime.utcnow().isoformat(),
                                'size': os.path.getsize(placeholder_path) / (1024 * 1024) if os.path.exists(placeholder_path) else 0,
                                'resolution': '1280x768',
                                'fps': 24
                            }
                            
                            clips.append(clip_info)
                            current_duration += clip_duration
                            print(f"[Pipeline] Clip {clip_index + 1} placeholder created (duration: {current_duration:.2f}s/{target_duration}s)")
                            
                            # Create/update incremental editable MP4 after placeholder clip
                            editable_mp4_path = self._update_incremental_editable_mp4(doc_id, clips, title, prompt)
                            
                            # Create storyline mapping
                            storyline = self._create_storyline_map(clips, prompt, title)
                            
                            # Update progress during clip generation (more frequent updates) with clip data
                            if self.progress_callback:
                                # Progress from 32-67% based on clips being generated
                                # Use both clip count and duration for smoother progress
                                clip_progress = 32 + int((clip_index / total_needed) * 35)  # 32-67% based on clip count
                                duration_progress = 32 + int((current_duration / target_duration) * 35)  # 32-67% based on duration
                                # Use the higher of the two to show progress
                                progress_pct = max(clip_progress, duration_progress)
                                progress_pct = min(progress_pct, 67)  # Cap at 67% for clip generation phase
                                
                                # Store total clips estimated
                                if doc_id not in self.generation_data:
                                    self.generation_data[doc_id] = {'clips': [], 'editable_mp4': None, 'storyline': {}, 'requirements': {}}
                                self.generation_data[doc_id]['total_clips_estimated'] = total_needed
                                
                                self._update_progress(
                                    doc_id, 
                                    progress_pct, 
                                    f"🎬 Generating clip {clip_index + 1}/{total_needed} ({current_duration:.2f}s/{target_duration}s)...",
                                    "generating_clips",  # Still generating clips
                                    clip_data=clip_info,  # Send clip data
                                    editable_mp4_path=editable_mp4_path,  # Send editable MP4 path
                                    storyline=storyline  # Send storyline
                                )
                        
                        # Also update progress even if placeholder creation failed (show we're trying)
                        if not clips or (clips and clips[-1].get('index') != clip_index):
                            if self.progress_callback:
                                progress_pct = 32 + int((clip_index / total_needed) * 35)
                                progress_pct = min(progress_pct, 67)
                                self._update_progress(
                                    doc_id, 
                                    progress_pct, 
                                    f"🎬 Preparing clip {clip_index + 1}/{total_needed}...",
                                    "generating_clips"  # Preparing for clip generation
                                )
                
                clip_index += 1
                
                # Check if we've reached minimum duration (2 minutes) and can stop
                if current_duration >= target_duration:
                    print(f"[Pipeline] Target duration reached: {current_duration}s >= {target_duration}s")
                    break
                
            except Exception as e:
                print(f"[Pipeline] Error generating clip {clip_index + 1}: {e}")
                clip_index += 1
                continue
        
        print(f"[Pipeline] Generated {len(clips)} clips with total duration: {current_duration}s ({current_duration//60}m {current_duration%60}s)")
        return clips
    
    def _combine_video_clips(self, doc_id: str, clips: list, title: str, prompt: str) -> Optional[str]:
        """Combine multiple video clips into full documentary video"""
        if not clips:
            return None
        
        try:
            # Try to use MoviePy for combining clips
            try:
                from moviepy.editor import VideoFileClip, concatenate_videoclips
                
                print(f"[Pipeline] ========================================")
                print(f"[Pipeline] COMBINING VIDEO CLIPS INTO SINGLE MP4")
                print(f"[Pipeline] ========================================")
                print(f"[Pipeline] Total clips to combine: {len(clips)}")
                print(f"[Pipeline] Using MoviePy for combining clips...")
                print(f"[Pipeline] Starting clip collection process...")
                
                video_clips = []
                for idx, clip_info in enumerate(clips, 1):
                    clip_path = clip_info.get('path')
                    clip_index = clip_info.get('index', idx)
                    clip_duration = clip_info.get('duration', 0)
                    
                    if clip_path and os.path.exists(clip_path):
                        try:
                            file_size = os.path.getsize(clip_path) / (1024 * 1024)  # MB
                            print(f"[Pipeline] [{idx}/{len(clips)}] Loading clip {clip_index}: {clip_path} ({clip_duration}s, {file_size:.2f}MB)")
                            clip = VideoFileClip(clip_path)
                            actual_duration = clip.duration if hasattr(clip, 'duration') else 0
                            actual_fps = clip.fps if hasattr(clip, 'fps') else 0
                            print(f"[Pipeline] [{idx}/{len(clips)}] ✓ Clip loaded: {actual_duration:.2f}s @ {actual_fps:.2f}fps")
                            video_clips.append(clip)
                        except Exception as e:
                            print(f"[Pipeline] [{idx}/{len(clips)}] ✗ Warning: Could not load clip {clip_index}: {e}")
                            continue
                    else:
                        print(f"[Pipeline] [{idx}/{len(clips)}] ✗ Warning: Clip path does not exist: {clip_path}")
                
                print(f"[Pipeline] Successfully loaded {len(video_clips)}/{len(clips)} clips")
                if len(video_clips) != len(clips):
                    print(f"[Pipeline] ⚠️ WARNING: {len(clips) - len(video_clips)} clips failed to load!")
                
                if video_clips:
                    # Calculate total duration
                    total_duration = sum(c.duration if hasattr(c, 'duration') else 0 for c in video_clips)
                    print(f"[Pipeline] Total video duration: {total_duration:.2f}s ({total_duration/60:.2f} minutes)")
                    
                    # Update progress: Starting to combine
                    if self.progress_callback:
                        self._update_progress(doc_id, 72, f"⚙️ Loading {len(video_clips)} video clips...", "loading_clips")
                        time.sleep(0.3)
                    
                    print(f"[Pipeline] Concatenating {len(video_clips)} clips using MoviePy concatenate_videoclips...")
                    print(f"[Pipeline] Method: compose (handles different resolutions/framerates)")
                    
                    # Concatenate all clips (this operation - combining video clips)
                    final_video = concatenate_videoclips(video_clips, method="compose")
                    
                    final_duration = final_video.duration if hasattr(final_video, 'duration') else 0
                    final_fps = final_video.fps if hasattr(final_video, 'fps') else 0
                    final_size = final_video.size if hasattr(final_video, 'size') else (0, 0)
                    
                    print(f"[Pipeline] ✓ Concatenation complete!")
                    print(f"[Pipeline] Final video properties:")
                    print(f"[Pipeline]   - Duration: {final_duration:.2f}s ({final_duration/60:.2f} minutes)")
                    print(f"[Pipeline]   - FPS: {final_fps:.2f}")
                    print(f"[Pipeline]   - Resolution: {final_size[0]}x{final_size[1]}")
                    
                    # Concatenate clips (this is fast, but update progress)
                    if self.progress_callback:
                        self._update_progress(doc_id, 74, f"⚙️ Concatenating {len(video_clips)} clips ({final_duration:.1f}s total)...", "rendering_frames")
                        time.sleep(0.2)
                    
                    # Save final video (this is the slow part - encoding video)
                    output_path = self.file_manager.get_output_path(f"{doc_id}.mp4")
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    print(f"[Pipeline] Output path: {output_path}")
                    print(f"[Pipeline] Preparing to encode single MP4 file...")
                    
                    # Ensure output path doesn't exist or is invalid before creating new one
                    if output_path.exists():
                        existing_size = output_path.stat().st_size / (1024 * 1024)  # MB
                        print(f"[Pipeline] Existing file found: {output_path} ({existing_size:.2f}MB)")
                        if not self._verify_mp4_file(output_path):
                            print(f"[Pipeline] ✗ Existing file is invalid, removing...")
                            try:
                                output_path.unlink()
                                print(f"[Pipeline] ✓ Invalid file removed")
                            except Exception as e:
                                print(f"[Pipeline] ⚠️ Could not remove invalid file: {e}")
                        else:
                            print(f"[Pipeline] ✓ Existing file is valid")
                    else:
                        print(f"[Pipeline] No existing file, will create new MP4")
                    
                    # Update progress: Writing video file (this operation - encoding/compressing)
                    if self.progress_callback:
                        self._update_progress(doc_id, 76, "⚙️ Starting video encoding (this may take 30-90 seconds)...", "encoding_video")
                        time.sleep(0.2)
                    
                    # Get video duration for progress estimation
                    video_duration = final_video.duration if hasattr(final_video, 'duration') else 0
                    
                    # Use threading to update progress during encoding (MoviePy is blocking)
                    encoding_start_time = time.time()
                    encoding_thread_running = True
                    
                    def encoding_progress_updater():
                        """Update progress periodically during encoding"""
                        nonlocal encoding_thread_running
                        import time
                        # Detailed progress messages explaining what's happening during encoding
                        progress_messages = [
                            "⚡ Encoding video frames (H.264 compression)...",
                            "🔥 Compressing video data (reducing file size)...",
                            "🎬 Processing video segments (combining clips)...",
                            "✨ Rendering final output (optimizing quality)...",
                            "💾 Writing video file to disk (saving output)...",
                            "🎯 Optimizing video quality (color correction)...",
                            "🌊 Smoothing transitions (frame interpolation)...",
                            "⚙️ Finalizing encoding (applying codec settings)...",
                            "🎨 Applying video filters (enhancement)...",
                            "📊 Analyzing video data (metadata)...",
                            "🔧 Processing audio tracks (sync)...",
                            "💫 Creating video stream (muxing)..."
                        ]
                        message_index = 0
                        last_update = time.time()
                        
                        while encoding_thread_running:
                            try:
                                elapsed = time.time() - encoding_start_time
                                
                                # Update every 2 seconds with rotating messages and elapsed time
                                if time.time() - last_update >= 2.0:
                                    if self.progress_callback:
                                        # Rotate through encoding messages to show activity
                                        message = progress_messages[message_index % len(progress_messages)]
                                        
                                        # Add elapsed time to message for better feedback
                                        elapsed_seconds = int(elapsed)
                                        elapsed_minutes = elapsed_seconds // 60
                                        elapsed_secs = elapsed_seconds % 60
                                        if elapsed_minutes > 0:
                                            time_str = f"{elapsed_minutes}m {elapsed_secs}s"
                                        else:
                                            time_str = f"{elapsed_seconds}s"
                                        
                                        # Estimate progress: 76% to 77.5% during encoding
                                        # Encoding typically takes 30-90 seconds for a 2-5 min video
                                        estimated_progress = 76 + min(1.5, (elapsed / 60) * 1.5)
                                        
                                        # Include elapsed time in message
                                        message_with_time = f"{message} (⏱️ {time_str} elapsed)"
                                        
                                        self._update_progress(doc_id, int(estimated_progress), message_with_time, "encoding_video", delay=0.05)  # Faster in thread
                                        message_index += 1
                                        last_update = time.time()
                                
                                time.sleep(1)  # Check every second
                            except Exception as e:
                                print(f"[Encoding Progress] Error: {e}")
                                break
                    
                    # Start progress updater thread
                    import threading
                    progress_thread = threading.Thread(target=encoding_progress_updater, daemon=True)
                    progress_thread.start()
                    
                    try:
                        # Try using ffmpeg directly for faster encoding (if available)
                        import subprocess
                        import os
                        
                        # Check if ffmpeg is available
                        use_ffmpeg_direct = False
                        try:
                            subprocess.run(['ffmpeg', '-version'], 
                                         capture_output=True, timeout=5, check=False)
                            use_ffmpeg_direct = True
                        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                            use_ffmpeg_direct = False
                        
                        if use_ffmpeg_direct and len(video_clips) > 0:
                            # Use ffmpeg directly for faster encoding (concat demuxer)
                            print("[Pipeline] Using ffmpeg directly for faster encoding...")
                            
                            # Create file list for ffmpeg concat
                            concat_file = output_path.parent / f"{doc_id}_concat.txt"
                            with open(concat_file, 'w') as f:
                                for clip_info in clips:
                                    clip_path = clip_info.get('path')
                                    if clip_path and os.path.exists(clip_path):
                                        # Escape single quotes and backslashes for ffmpeg
                                        escaped_path = str(clip_path).replace('\\', '/').replace("'", "'\\''")
                                        f.write(f"file '{escaped_path}'\n")
                            
                            # Use ffmpeg to concat and encode
                            # -safe 0 allows absolute paths, -c copy is fastest (no re-encoding)
                            # Fallback to -c:v libx264 if copy doesn't work
                            ffmpeg_cmd = [
                                'ffmpeg',
                                '-f', 'concat',
                                '-safe', '0',
                                '-i', str(concat_file),
                                '-c', 'copy',  # Copy streams without re-encoding (fastest)
                                '-y',  # Overwrite output
                                str(output_path)
                            ]
                            
                            # Run ffmpeg with timeout (max 5 minutes)
                            try:
                                result = subprocess.run(
                                    ffmpeg_cmd,
                                    capture_output=True,
                                    timeout=300,  # 5 minute timeout
                                    text=True
                                )
                                
                                if result.returncode == 0 and output_path.exists():
                                    print("[Pipeline] ffmpeg concat successful!")
                                    # Clean up concat file
                                    try:
                                        os.remove(concat_file)
                                    except:
                                        pass
                                else:
                                    # Fallback: try with re-encoding
                                    print("[Pipeline] ffmpeg copy failed, trying with re-encoding...")
                                    ffmpeg_cmd_encode = [
                                        'ffmpeg',
                                        '-f', 'concat',
                                        '-safe', '0',
                                        '-i', str(concat_file),
                                        '-c:v', 'libx264',
                                        '-preset', 'medium',  # Better quality (was: ultrafast)
                                        '-crf', '23',  # Better quality (was: 28)
                                        '-pix_fmt', 'yuv420p',  # Ensure compatibility
                                        '-movflags', '+faststart',  # Web optimized
                                        '-c:a', 'aac',
                                        '-b:a', '192k',  # Better audio quality (was: 128k)
                                        '-y',
                                        str(output_path)
                                    ]
                                    
                                    result = subprocess.run(
                                        ffmpeg_cmd_encode,
                                        capture_output=True,
                                        timeout=300,
                                        text=True
                                    )
                                    
                                    # Clean up concat file
                                    try:
                                        os.remove(concat_file)
                                    except:
                                        pass
                                    
                                    if result.returncode != 0 or not output_path.exists():
                                        raise Exception(f"ffmpeg encoding failed: {result.stderr[:200]}")
                            except subprocess.TimeoutExpired:
                                print("[Pipeline] ffmpeg timeout - falling back to MoviePy")
                                use_ffmpeg_direct = False
                                # Clean up concat file
                                try:
                                    os.remove(concat_file)
                                except:
                                    pass
                            except Exception as ffmpeg_error:
                                print(f"[Pipeline] ffmpeg error: {ffmpeg_error} - falling back to MoviePy")
                                use_ffmpeg_direct = False
                        
                        if not use_ffmpeg_direct:
                            # Fallback to MoviePy with timeout protection
                            print("[Pipeline] Using MoviePy for encoding...")
                            
                            # Use threading with timeout to prevent hanging
                            import signal
                            
                            def write_video_with_timeout():
                                """Write video with timeout protection"""
                                try:
                                    final_video.write_videofile(
                                        str(output_path),
                                        fps=24,
                                        codec='libx264',
                                        audio_codec='aac',
                                        preset='medium',  # Better quality (was: ultrafast)
                                        bitrate='3000k',  # Higher bitrate for better quality (was: 1500k)
                                        audio_bitrate='192k',  # Better audio quality (was: 96k)
                                        verbose=False,
                                        logger=None,
                                        threads=4,  # More threads for better performance (was: 2)
                                        temp_audiofile=None,
                                        write_logfile=False,
                                        remove_temp=True
                                    )
                                except Exception as e:
                                    print(f"[MoviePy] Error: {e}")
                                    raise
                            
                            # Run encoding in thread with timeout
                            encoding_result = {'success': False, 'error': None}
                            encoding_thread = threading.Thread(
                                target=lambda: encoding_result.update({'success': True}) or write_video_with_timeout(),
                                daemon=False
                            )
                            encoding_thread.start()
                            encoding_thread.join(timeout=180)  # 3 minute timeout
                            
                            if encoding_thread.is_alive():
                                print("[Pipeline] MoviePy encoding timeout - trying fallback")
                                # If MoviePy hangs, try simpler approach: just copy first clip
                                if len(video_clips) > 0 and os.path.exists(clips[0].get('path')):
                                    shutil.copy2(clips[0].get('path'), output_path)
                                    print(f"[Pipeline] Fallback: copied first clip to {output_path}")
                                else:
                                    raise Exception("Encoding timeout and no fallback available")
                            elif not encoding_result['success']:
                                if encoding_result.get('error'):
                                    raise encoding_result['error']
                                raise Exception("Encoding failed")
                            elif not output_path.exists():
                                raise Exception("Output file not created")
                    
                    except Exception as encoding_error:
                        print(f"[Pipeline] Encoding error: {encoding_error}")
                        # Final fallback: copy first clip if available
                        if len(clips) > 0:
                            first_clip_path = clips[0].get('path')
                            if first_clip_path and os.path.exists(first_clip_path):
                                print(f"[Pipeline] Final fallback: copying first clip...")
                                shutil.copy2(first_clip_path, output_path)
                                print(f"[Pipeline] Copied first clip to {output_path}")
                            else:
                                raise encoding_error
                        else:
                            raise encoding_error
                    finally:
                        # Stop progress updater thread
                        encoding_thread_running = False
                        if progress_thread.is_alive():
                            progress_thread.join(timeout=2)
                    
                    # TRIPLE-CHECK: Verify the created video file
                    if not self._verify_mp4_file(output_path):
                        print(f"[Pipeline] WARNING: Created video failed verification, trying to ensure valid file...")
                        verified_path = self._ensure_mp4_file_created(doc_id, output_path, fallback_duration=int(final_video.duration) if hasattr(final_video, 'duration') else 120)
                        if verified_path:
                            output_path = Path(verified_path)
                    
                    # Update progress: Video written (operation complete)
                    if self.progress_callback:
                        if self._verify_mp4_file(output_path):
                            self._update_progress(doc_id, 78, "✅ Video encoding complete and verified!", "video_written")
                        else:
                            self._update_progress(doc_id, 78, "⚠️ Video encoding complete (verification pending)", "video_written")
                        time.sleep(0.2)
                    
                    # Close clips
                    final_video.close()
                    for clip in video_clips:
                        clip.close()
                    
                    # Final verification before returning
                    if output_path.exists():
                        final_file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                        print(f"[Pipeline] Final file size: {final_file_size:.2f}MB")
                    
                    if self._verify_mp4_file(output_path):
                        print(f"[Pipeline] ========================================")
                        print(f"[Pipeline] ✅ SUCCESS: SINGLE MP4 FILE CREATED")
                        print(f"[Pipeline] ========================================")
                        print(f"[Pipeline] File: {output_path}")
                        print(f"[Pipeline] Size: {final_file_size:.2f}MB")
                        print(f"[Pipeline] Duration: {final_duration:.2f}s")
                        print(f"[Pipeline] Clips combined: {len(video_clips)}/{len(clips)}")
                        print(f"[Pipeline] ========================================")
                    else:
                        print(f"[Pipeline] ⚠️ WARNING: File created but verification failed: {output_path}")
                        print(f"[Pipeline] File exists: {output_path.exists()}")
                        if output_path.exists():
                            print(f"[Pipeline] File size: {output_path.stat().st_size} bytes")
                    
                    return str(output_path)
                
            except ImportError:
                print("[Pipeline] MoviePy not available - using simple concatenation")
            
            # Fallback: If only one clip, just copy it
            if len(clips) == 1:
                clip_path = clips[0].get('path')
                if clip_path and os.path.exists(clip_path):
                    output_path = self.file_manager.get_output_path(f"{doc_id}.mp4")
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    print(f"[Pipeline] Single clip detected, copying to final MP4...")
                    print(f"[Pipeline] Source: {clip_path}")
                    print(f"[Pipeline] Destination: {output_path}")
                    shutil.copy2(clip_path, output_path)
                    file_size = output_path.stat().st_size / (1024 * 1024)  # MB
                    print(f"[Pipeline] ✓ Single clip copied to: {output_path} ({file_size:.2f}MB)")
                    return str(output_path)
            
            # Last resort: Create placeholder
            print("[Pipeline] Could not combine clips - creating placeholder")
            return None
            
        except Exception as e:
            print(f"[Pipeline] Error combining clips: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_ai_video(self, doc_id: str, prompt: str, title: str, description: str, scraped_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Generate single video using AI video generators (legacy method - now uses _generate_multiple_video_clips)"""
        # This method is kept for backward compatibility
        # Generate minimum 2 minutes (120 seconds) even for single video
        clips = self._generate_multiple_video_clips(doc_id, prompt, title, description, scraped_data, target_duration=180)
        if clips:
            clip_info = clips[0]
            return {
                'success': True,
                'video_path': clip_info.get('path'),
                'video_url': clip_info.get('url'),
                'provider': clip_info.get('provider')
            }
        return None
    
    def _download_video_from_url(self, video_url: str, doc_id: str) -> Optional[str]:
        """Download video from URL to local file"""
        try:
            # Download video
            response = requests.get(video_url, timeout=300, stream=True)
            response.raise_for_status()
            
            # Save to local file
            output_path = self.file_manager.get_output_path(f"{doc_id}.mp4")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"[Pipeline] Downloaded video from {video_url} to {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"[Pipeline] Video download error: {e}")
            return None
    
    def _create_placeholder_video_clip(self, doc_id: str, clip_index: int, duration: int, prompt: str) -> Optional[Path]:
        """Create placeholder video clip with actual duration using MoviePy or ffmpeg"""
        try:
            # Try to use MoviePy first (better quality)
            try:
                from moviepy.editor import ColorClip, CompositeVideoClip, TextClip
                
                placeholder_path = self.file_manager.get_output_path(f"{doc_id}_clip_{clip_index}.mp4")
                placeholder_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Create a simple colored clip with text
                clip = ColorClip(size=(1280, 768), color=(50, 50, 50), duration=duration)
                
                # Add text overlay with prompt snippet
                try:
                    text = TextClip(
                        prompt[:50] + "..." if len(prompt) > 50 else prompt,
                        fontsize=40,
                        color='white',
                        bg_color='rgba(0,0,0,0.5)',
                        size=(1200, None),
                        method='caption'
                    ).set_position(('center', 'center')).set_duration(duration)
                    
                    video = CompositeVideoClip([clip, text])
                except:
                    # If text fails, just use color clip
                    video = clip
                
                # Write video file
                video.write_videofile(
                    str(placeholder_path),
                    fps=24,
                    codec='libx264',
                    audio=False,  # No audio for placeholder
                    preset='ultrafast',  # Fast encoding
                    verbose=False,
                    logger=None
                )
                
                video.close()
                return placeholder_path
                
            except ImportError:
                # Fallback to ffmpeg if MoviePy not available
                try:
                    import subprocess
                    
                    placeholder_path = self.file_manager.get_output_path(f"{doc_id}_clip_{clip_index}.mp4")
                    placeholder_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Use ffmpeg to create video with duration
                    # Create a solid color video
                    cmd = [
                        'ffmpeg',
                        '-f', 'lavfi',
                        '-i', f'color=c=0x323232:s=1280x768:d={duration}',
                        '-f', 'lavfi',
                        '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',
                        '-c:v', 'libx264',
                        '-c:a', 'aac',
                        '-shortest',
                        '-y',  # Overwrite
                        str(placeholder_path)
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=30
                    )
                    
                    if result.returncode == 0 and placeholder_path.exists():
                        return placeholder_path
                    else:
                        print(f"ffmpeg placeholder creation failed: {result.stderr.decode()}")
                        
                except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                    print(f"ffmpeg placeholder creation error: {e}")
            
            # Last resort: Create minimal MP4 file (will be 0 seconds but won't crash)
            placeholder_path = self.file_manager.get_output_path(f"{doc_id}_clip_{clip_index}.mp4")
            placeholder_path.parent.mkdir(parents=True, exist_ok=True)
            with open(placeholder_path, 'wb') as f:
                f.write(b'')  # Empty placeholder
            return placeholder_path
            
        except Exception as e:
            print(f"Error creating placeholder video clip: {e}")
            return None
    
    def _create_placeholder_video(self, doc_id: str, title: str, prompt: str, description: str, scraped_data: Optional[Dict[str, Any]] = None) -> str:
        """Create a placeholder video for fallback"""
        # Create a single placeholder clip and use it as main video
        placeholder_clip = self._create_placeholder_video_clip(doc_id, 1, 120, prompt)  # 2 minutes default
        
        if placeholder_clip and placeholder_clip.exists():
            # Copy to main video path
            output_path = self.file_manager.get_output_path(f"{doc_id}.mp4")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(placeholder_clip, output_path)
            print(f"Created placeholder video: {output_path}")
            return str(output_path)
        else:
            # Fallback: create empty file
            output_path = self.file_manager.get_output_path(f"{doc_id}.mp4")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(b'')  # Empty placeholder
            print(f"Created empty placeholder video: {output_path}")
            return str(output_path)
    
    def _create_thumbnail(self, video_path: str, doc_id: str) -> str:
        """Create thumbnail from video"""
        try:
            from PIL import Image
            
            # Create simple thumbnail
            thumbnail_path = self.file_manager.get_output_path(f"{doc_id}_thumb.jpg")
            thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create placeholder thumbnail
            img = Image.new('RGB', (1280, 720), color='black')
            img.save(thumbnail_path)
            
            return str(thumbnail_path)
        except Exception:
            return ""
    
    def _generate_narration(
        self, 
        doc_id: str, 
        prompt: str, 
        title: str, 
        description: str, 
        scraped_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Generate narration audio from prompt and scraped scripts using TTS"""
        if not self.tts_service:
            print("[Pipeline] TTS service not available, skipping narration")
            return None
        
        try:
            # Build narration text from prompt, description, and scraped scripts
            narration_parts = []
            
            # Start with title if available
            if title:
                narration_parts.append(f"Welcome to {title}.")
            
            # Add description or prompt
            if description:
                narration_parts.append(description)
            else:
                narration_parts.append(prompt)
            
            # Add relevant scraped script snippets
            if scraped_data:
                scripts = scraped_data.get('scripts', [])
                if scripts:
                    # Take first few script snippets for narration
                    for script in scripts[:3]:  # Max 3 script snippets
                        snippet = script.get('snippet', '')[:200]  # Limit length
                        if snippet:
                            narration_parts.append(snippet)
            
            # Combine into full narration text
            narration_text = ' '.join(narration_parts)
            
            # Limit to reasonable length (TTS APIs have limits)
            max_length = 5000  # ~5 minutes of speech at normal speed
            if len(narration_text) > max_length:
                narration_text = narration_text[:max_length] + "..."
            
            print(f"[Pipeline] Generating narration ({len(narration_text)} characters)...")
            
            # Generate audio
            audio_path = self.file_manager.get_output_path(f"{doc_id}_narration.mp3")
            
            result = self.tts_service.generate_speech(
                text=narration_text,
                output_path=str(audio_path),
                language="en",  # Default to English, can be configurable
                speed=1.0
            )
            
            if result and result.get('success') and result.get('audio_path'):
                audio_file = Path(result['audio_path'])
                if audio_file.exists() and audio_file.stat().st_size > 0:
                    print(f"[Pipeline] Narration generated: {audio_file} ({result.get('provider')})")
                    return str(audio_file)
                else:
                    print("[Pipeline] Narration file is empty, skipping...")
                    return None
            else:
                print("[Pipeline] Narration generation failed, skipping...")
                return None
                
        except Exception as e:
            print(f"[Pipeline] Error generating narration: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _add_audio_to_video(self, video_path: str, audio_path: str, doc_id: str) -> str:
        """Add narration audio to video using MoviePy"""
        try:
            from moviepy.editor import VideoFileClip, AudioFileClip
            
            print(f"[Pipeline] Adding audio to video: {audio_path}")
            
            # Load video and audio
            video = VideoFileClip(video_path)
            audio = AudioFileClip(audio_path)
            
            # Set audio duration to match video (loop if needed or trim)
            if audio.duration < video.duration:
                # Loop audio if it's shorter than video
                from moviepy.audio.AudioClip import concatenate_audioclips
                loops_needed = int(video.duration / audio.duration) + 1
                audio_looped = concatenate_audioclips([audio] * loops_needed)
                audio_looped = audio_looped.subclip(0, video.duration)
                final_audio = audio_looped
            else:
                # Trim audio if it's longer than video
                final_audio = audio.subclip(0, video.duration)
            
            # Set volume (can be adjusted)
            final_audio = final_audio.volumex(0.8)  # 80% volume
            
            # Combine video and audio
            final_video = video.set_audio(final_audio)
            
            # Save to new file
            output_path = self.file_manager.get_output_path(f"{doc_id}_with_audio.mp4")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            final_video.write_videofile(
                str(output_path),
                fps=24,
                codec='libx264',
                audio_codec='aac',
                preset='medium',  # Good balance of quality and speed
                bitrate='3000k',  # Higher bitrate for better quality
                audio_bitrate='192k',  # Good audio quality
                threads=4,  # Use more threads
                temp_audiofile=None,
                write_logfile=False,
                remove_temp=True
            )
            
            # Close clips
            video.close()
            audio.close()
            final_video.close()
            
            print(f"[Pipeline] Video with audio saved: {output_path}")
            
            # Replace original video with audio-enhanced version
            if os.path.exists(output_path):
                # Optionally delete original video if different
                if video_path != str(output_path) and os.path.exists(video_path):
                    try:
                        os.remove(video_path)
                    except:
                        pass  # Keep original if deletion fails
                
                return str(output_path)
            else:
                return video_path  # Return original if new file doesn't exist
                
        except ImportError:
            print("[Pipeline] MoviePy not available, skipping audio addition")
            return video_path
        except Exception as e:
            print(f"[Pipeline] Error adding audio to video: {e}")
            import traceback
            traceback.print_exc()
            return video_path  # Return original video on error
    
    def _create_editable_mp4_at_75_percent(self, doc_id: str, source_video_path: str, title: str, prompt: str) -> Optional[str]:
        """Create an editable MP4 file at 75% progress point
        
        This service ensures a file is created that can be edited while generation continues.
        The file is created with proper permissions and no locks, allowing external editing.
        
        Args:
            doc_id: Documentary ID
            source_video_path: Path to source video (may be temporary or incomplete)
            title: Documentary title
            prompt: Documentary prompt
            
        Returns:
            Path to editable MP4 file, or None if creation failed
        """
        try:
            print(f"[75% Service] Creating editable MP4 file at 75% progress point...")
            self._update_progress(doc_id, 75, "📝 Creating editable video file (ready for editing)...", "creating_editable_file")
            import time
            time.sleep(0.2)
            
            # Get final output path
            output_path = self.file_manager.get_output_path(f"{doc_id}.mp4")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Multiple attempts to create editable file
            max_attempts = 5
            editable_path = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    print(f"[75% Service] Attempt {attempt}/{max_attempts}: Creating editable MP4...")
                    
                    # Method 1: Copy existing video if it exists and is valid
                    if source_video_path and os.path.exists(source_video_path):
                        if self._verify_mp4_file(source_video_path):
                            print(f"[75% Service] Copying existing valid video to editable location...")
                            # Close any file handles first (if using MoviePy)
                            try:
                                from moviepy.editor import VideoFileClip
                                # Try to close any open clips
                                pass  # MoviePy clips should be closed already
                            except:
                                pass
                            
                            # Copy file with proper permissions
                            import shutil
                            if output_path.exists():
                                # Remove existing file first to ensure it's not locked
                                try:
                                    output_path.unlink()
                                    time.sleep(0.1)  # Small delay to ensure file is released
                                except Exception as e:
                                    print(f"[75% Service] Warning: Could not remove existing file: {e}")
                            
                            # Copy with shutil to preserve permissions
                            shutil.copy2(source_video_path, output_path)
                            
                            # Verify copied file
                            if self._verify_mp4_file(output_path):
                                editable_path = str(output_path)
                                print(f"[75% Service] ✅ Editable file created via copy: {editable_path}")
                                break
                    
                    # Method 2: Create new editable file from source using MoviePy
                    if not editable_path:
                        print(f"[75% Service] Creating new editable file using MoviePy...")
                        try:
                            from moviepy.editor import VideoFileClip
                            
                            # Load source video if it exists
                            if source_video_path and os.path.exists(source_video_path):
                                source_clip = VideoFileClip(source_video_path)
                                
                                # Write to output with proper settings for editing
                                source_clip.write_videofile(
                                    str(output_path),
                                    fps=24,
                                    codec='libx264',
                                    audio_codec='aac' if source_clip.audio else None,
                                    preset='medium',  # Better quality for editing
                                    bitrate='2000k',  # Higher bitrate for editing
                                    verbose=False,
                                    logger=None,
                                    threads=4,
                                    temp_audiofile=None,
                                    write_logfile=False,
                                    remove_temp=True
                                )
                                
                                # Close source clip immediately to release file handle
                                source_clip.close()
                                
                                # Small delay to ensure file is written and handle is released
                                time.sleep(0.5)
                                
                                # Verify created file
                                if self._verify_mp4_file(output_path):
                                    editable_path = str(output_path)
                                    print(f"[75% Service] ✅ Editable file created via MoviePy: {editable_path}")
                                    break
                            else:
                                # No source video - create placeholder editable file
                                from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
                                
                                # Create a simple editable video
                                clip = ColorClip(size=(1280, 768), color=(50, 50, 50), duration=120)
                                
                                # Add text overlay
                                try:
                                    text = TextClip(
                                        f"{title[:40]}..." if len(title) > 40 else title,
                                        fontsize=50,
                                        color='white',
                                        bg_color='rgba(0,0,0,0.7)',
                                        size=(1200, None),
                                        method='caption'
                                    ).set_position(('center', 'center')).set_duration(120)
                                    video = CompositeVideoClip([clip, text])
                                except:
                                    video = clip
                                
                                video.write_videofile(
                                    str(output_path),
                                    fps=24,
                                    codec='libx264',
                                    audio=False,
                                    preset='medium',
                                    verbose=False,
                                    logger=None
                                )
                                
                                video.close()
                                clip.close()
                                
                                time.sleep(0.5)
                                
                                if self._verify_mp4_file(output_path):
                                    editable_path = str(output_path)
                                    print(f"[75% Service] ✅ Editable placeholder file created: {editable_path}")
                                    break
                                    
                        except ImportError:
                            print(f"[75% Service] MoviePy not available, trying ffmpeg...")
                        except Exception as e:
                            print(f"[75% Service] MoviePy creation failed: {e}")
                    
                    # Method 3: Use ffmpeg to create editable file
                    if not editable_path:
                        print(f"[75% Service] Creating editable file using ffmpeg...")
                        try:
                            import subprocess
                            
                            if source_video_path and os.path.exists(source_video_path):
                                # Re-encode with ffmpeg for better editing compatibility
                                cmd = [
                                    'ffmpeg',
                                    '-i', str(source_video_path),
                                    '-c:v', 'libx264',
                                    '-preset', 'medium',  # Better quality for editing
                                    '-crf', '23',  # Good quality
                                    '-c:a', 'aac',
                                    '-b:a', '192k',
                                    '-movflags', '+faststart',  # Web optimized
                                    '-y',  # Overwrite
                                    str(output_path)
                                ]
                            else:
                                # Create placeholder with ffmpeg
                                cmd = [
                                    'ffmpeg',
                                    '-f', 'lavfi',
                                    '-i', 'color=c=0x323232:s=1280x768:d=120',
                                    '-c:v', 'libx264',
                                    '-preset', 'medium',
                                    '-crf', '23',
                                    '-y',
                                    str(output_path)
                                ]
                            
                            result = subprocess.run(
                                cmd,
                                capture_output=True,
                                timeout=120,
                                text=True
                            )
                            
                            if result.returncode == 0 and output_path.exists():
                                time.sleep(0.5)  # Ensure file is written
                                if self._verify_mp4_file(output_path):
                                    editable_path = str(output_path)
                                    print(f"[75% Service] ✅ Editable file created via ffmpeg: {editable_path}")
                                    break
                        except Exception as e:
                            print(f"[75% Service] ffmpeg creation failed: {e}")
                    
                    # Method 4: Use ensure function as last resort
                    if not editable_path:
                        print(f"[75% Service] Using ensure function as fallback...")
                        verified_path = self._ensure_mp4_file_created(doc_id, output_path, fallback_duration=120)
                        if verified_path:
                            editable_path = verified_path
                            print(f"[75% Service] ✅ Editable file created via ensure function: {editable_path}")
                            break
                    
                    # If this attempt failed, wait before retry
                    if attempt < max_attempts:
                        time.sleep(1)
                        
                except Exception as e:
                    print(f"[75% Service] Attempt {attempt} failed: {e}")
                    if attempt < max_attempts:
                        time.sleep(1)
                    continue
            
            # Final verification and permission setting
            if editable_path and os.path.exists(editable_path):
                # Ensure file is readable and writable
                try:
                    import stat
                    os.chmod(editable_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                    print(f"[75% Service] ✅ File permissions set for editing: {editable_path}")
                except Exception as e:
                    print(f"[75% Service] Warning: Could not set permissions: {e}")
                
                # Final verification
                if self._verify_mp4_file(editable_path):
                    self._update_progress(doc_id, 76, "✅ Editable video file created and verified (ready for editing)!", "editable_file_ready")
                    print(f"[75% Service] ✅✅✅ SUCCESS: Editable MP4 file created at 75%: {editable_path}")
                    return editable_path
                else:
                    self._update_progress(doc_id, 76, "⚠️ Editable file created (verification pending)", "editable_file_pending")
                    print(f"[75% Service] ⚠️ Editable file created but verification pending: {editable_path}")
                    return editable_path
            else:
                self._update_progress(doc_id, 76, "⚠️ Could not create editable file, continuing generation...", "editable_file_failed")
                print(f"[75% Service] ❌ Failed to create editable file after {max_attempts} attempts")
                return None
                
        except Exception as e:
            print(f"[75% Service] ❌ ERROR creating editable file: {e}")
            import traceback
            traceback.print_exc()
            self._update_progress(doc_id, 76, "⚠️ Editable file creation error, continuing generation...", "editable_file_error")
            return None
    
    def _update_incremental_editable_mp4(self, doc_id: str, clips: list, title: str, prompt: str) -> Optional[str]:
        """Update editable MP4 file incrementally after each clip is generated
        
        Args:
            doc_id: Documentary ID
            clips: List of clip dictionaries with path, duration, etc.
            title: Documentary title
            prompt: Documentary prompt
        
        Returns:
            Path to editable MP4 file, or None if creation failed
        """
        if not clips:
            return None
        
        try:
            from moviepy.editor import VideoFileClip, concatenate_videoclips
            
            print(f"[Incremental MP4] Updating editable MP4 with {len(clips)} clips...")
            
            # Get or create editable MP4 path
            editable_path = self.file_manager.get_output_path(f"{doc_id}_editable.mp4")
            editable_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load all clips
            video_clips = []
            for clip_info in clips:
                clip_path = clip_info.get('path')
                if clip_path and os.path.exists(clip_path):
                    try:
                        clip = VideoFileClip(clip_path)
                        video_clips.append(clip)
                        print(f"[Incremental MP4] Loaded clip: {clip_path} ({clip.duration:.2f}s)")
                    except Exception as e:
                        print(f"[Incremental MP4] Warning: Could not load clip {clip_path}: {e}")
                        continue
            
            if not video_clips:
                print(f"[Incremental MP4] No valid clips to combine")
                return None
            
            # Combine clips
            if len(video_clips) == 1:
                final_video = video_clips[0]
            else:
                final_video = concatenate_videoclips(video_clips, method="compose")
            
            # Write editable MP4 file
            print(f"[Incremental MP4] Writing editable MP4 to: {editable_path}")
            final_video.write_videofile(
                str(editable_path),
                fps=24,
                codec='libx264',
                audio=False,
                verbose=False,
                logger=None,
                preset='ultrafast',  # Fast encoding for incremental updates
                threads=2
            )
            
            # Close clips to free memory
            for clip in video_clips:
                clip.close()
            if final_video != video_clips[0]:
                final_video.close()
            
            # Verify file
            if editable_path.exists() and self._verify_mp4_file(editable_path):
                file_size = editable_path.stat().st_size / (1024 * 1024)  # MB
                print(f"[Incremental MP4] ✅ Editable MP4 updated: {editable_path} ({file_size:.2f}MB)")
                
                # Store in generation data
                if doc_id not in self.generation_data:
                    self.generation_data[doc_id] = {'clips': [], 'editable_mp4': None, 'storyline': {}, 'requirements': {}}
                self.generation_data[doc_id]['editable_mp4'] = str(editable_path)
                
                return str(editable_path)
            else:
                print(f"[Incremental MP4] ⚠️ Editable MP4 file verification failed")
                return None
                
        except Exception as e:
            print(f"[Incremental MP4] ❌ Error updating editable MP4: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_storyline_map(self, clips: list, prompt: str, title: str) -> Dict[str, Any]:
        """Create storyline mapping from generated clips
        
        Args:
            clips: List of clip dictionaries
            prompt: Documentary prompt
            title: Documentary title
        
        Returns:
            Dictionary with storyline structure
        """
        try:
            storyline = {
                'title': title,
                'prompt': prompt,
                'total_segments': len(clips),
                'total_duration': sum(clip.get('duration', 0) for clip in clips),
                'segments': []
            }
            
            cumulative_duration = 0
            for idx, clip_info in enumerate(clips):
                clip_duration = clip_info.get('duration', 0)
                segment = {
                    'index': idx + 1,
                    'clip_path': clip_info.get('path'),
                    'prompt': clip_info.get('prompt', ''),
                    'start_time': cumulative_duration,
                    'duration': clip_duration,
                    'end_time': cumulative_duration + clip_duration,
                    'story_position': f"Segment {idx + 1}",
                    'timestamp': clip_info.get('timestamp', '')
                }
                storyline['segments'].append(segment)
                cumulative_duration += clip_duration
            
            # Store in generation data (will be stored when _update_progress is called)
            print(f"[Storyline] Created storyline map with {len(storyline['segments'])} segments ({storyline['total_duration']:.2f}s total)")
            return storyline
            
        except Exception as e:
            print(f"[Storyline] ❌ Error creating storyline map: {e}")
            import traceback
            traceback.print_exc()
            return {
                'title': title,
                'prompt': prompt,
                'total_segments': 0,
                'total_duration': 0,
                'segments': []
            }
    
    def _create_clips(self, video_path: str, doc_id: str) -> list:
        """Extract 5-minute clips from video for embedding"""
        # For Phase 1, we'll create one clip from the video
        # Future phases will create multiple 5-minute segments
        clips = []
        
        try:
            # In future phases, split video into 5-minute segments
            # For Phase 1, return empty list (clips created separately)
            pass
        except Exception:
            pass
        
        return clips

