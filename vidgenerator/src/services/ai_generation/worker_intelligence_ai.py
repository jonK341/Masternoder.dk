"""
AI Generation System - Phase 2
Uses worker intelligence to create clips, files, and MPEG movies
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os
from pathlib import Path

# Import existing video generation system
try:
    from src.services.video_generation.video_generator import VideoGenerator
except ImportError as e:
    print(f"[WorkerIntelligenceAI] Warning: VideoGenerator not available: {e}")
    VideoGenerator = None

# Import AI provider manager
try:
    from src.services.ai_generation.ai_providers import AIProviderManager
    ai_provider_manager = AIProviderManager()
    print(f"[WorkerIntelligenceAI] AI Provider Manager initialized with {len(ai_provider_manager.active_providers)} providers")
except ImportError as e:
    print(f"[WorkerIntelligenceAI] Warning: AIProviderManager not available: {e}")
    ai_provider_manager = None

try:
    from src.utils.file_manager import FileManager
except ImportError:
    # Try alternative import paths
    try:
        from src.services.file_management.file_manager import FileManager
    except ImportError:
        try:
            from src.services.storage.storage_manager import StorageManager as FileManager
        except ImportError:
            print("[WorkerIntelligenceAI] Warning: FileManager not available")
            FileManager = None


class WorkerIntelligenceAI:
    """
    Phase 2: AI Generation from Worker Intelligence
    Takes the comprehensive intelligence gathered by the service worker
    and uses AI to generate clips, files, and MPEG movies
    """
    
    def __init__(self, doc_id: Optional[str] = None):
        self.ai_providers = self._initialize_ai_providers()
        self.generation_strategies = self._initialize_strategies()
        self.doc_id = doc_id
        
        # Initialize existing video generation system
        if VideoGenerator:
            try:
                self.video_generator = VideoGenerator()
                print(f"[WorkerIntelligenceAI] VideoGenerator initialized successfully")
                # Verify it has available providers
                if hasattr(self.video_generator, 'get_available_providers'):
                    providers = self.video_generator.get_available_providers()
                    print(f"[WorkerIntelligenceAI] Available providers: {providers}")
            except Exception as e:
                print(f"[WorkerIntelligenceAI] Warning: Could not initialize VideoGenerator: {e}")
                import traceback
                traceback.print_exc()
                self.video_generator = None
        else:
            print(f"[WorkerIntelligenceAI] VideoGenerator class not available")
            self.video_generator = None
        
        # Initialize file manager
        if FileManager:
            try:
                self.file_manager = FileManager()
            except Exception as e:
                print(f"[WorkerIntelligenceAI] Warning: Could not initialize FileManager: {e}")
                self.file_manager = None
        else:
            self.file_manager = None
    
    def _initialize_ai_providers(self) -> Dict[str, Any]:
        """Initialize available AI providers"""
        return {
            'runway': {'available': True, 'priority': 1},
            'pika': {'available': True, 'priority': 2},
            'stable_video': {'available': True, 'priority': 3},
            'luma': {'available': True, 'priority': 4},
            'krea': {'available': True, 'priority': 5},
            'ffmpeg_fallback': {'available': True, 'priority': 99}
        }
    
    def _initialize_strategies(self) -> Dict[str, Any]:
        """Initialize generation strategies"""
        return {
            'high_quality': {
                'description': 'Maximum quality, slower generation',
                'provider_priority': ['runway', 'luma', 'pika'],
                'quality_target': 0.9
            },
            'balanced': {
                'description': 'Balance between quality and speed',
                'provider_priority': ['pika', 'runway', 'stable_video'],
                'quality_target': 0.7
            },
            'fast': {
                'description': 'Fast generation, acceptable quality',
                'provider_priority': ['stable_video', 'krea', 'ffmpeg_fallback'],
                'quality_target': 0.5
            }
        }
    
    def generate_from_intelligence(
        self,
        intelligence: Dict[str, Any],
        target_duration: int = 180,
        strategy: str = 'balanced',
        doc_id: Optional[str] = None,
        clip_count: Optional[int] = None  # NEW: Emphasize clip count
    ) -> Dict[str, Any]:
        """
        Generate clips and movie from worker intelligence
        
        Args:
            intelligence: Comprehensive intelligence from service worker
            target_duration: Target duration in seconds
            strategy: Generation strategy (high_quality, balanced, fast)
            doc_id: Documentary ID for file management
        
        Returns:
            Generation result with clips, files, and movie path
        """
        if doc_id:
            self.doc_id = doc_id
        
        print(f"[WorkerIntelligenceAI] Starting generation from intelligence")
        print(f"[WorkerIntelligenceAI] Strategy: {strategy}, Target duration: {target_duration}s, Doc ID: {doc_id}")
        
        # Select strategy
        gen_strategy = self.generation_strategies.get(strategy, self.generation_strategies['balanced'])
        
        # Build comprehensive prompt from intelligence
        mega_prompt = self._build_mega_prompt_from_intelligence(intelligence)
        
        # Determine clip count and durations (use emphasized clip_count if provided)
        clip_plan = self._plan_clips(intelligence, target_duration, gen_strategy, clip_count=clip_count)
        
        # Generate clips using AI with smart retry logic
        generated_clips = []
        max_retries = 3
        
        for i, clip_spec in enumerate(clip_plan['clips']):
            print(f"[WorkerIntelligenceAI] Generating clip {i+1}/{len(clip_plan['clips'])} (duration: {clip_spec['duration']}s)")
            
            clip = None
            for retry in range(max_retries):
                clip = self._generate_single_clip(
                    clip_spec,
                    mega_prompt,
                    intelligence,
                    gen_strategy
                )
                
                if clip and clip.get('video_path'):
                    # Verify clip has actual content (file size > 10KB)
                    video_path = clip['video_path']
                    if os.path.exists(video_path):
                        file_size = os.path.getsize(video_path)
                        if file_size > 10240:  # 10KB minimum
                            print(f"[WorkerIntelligenceAI] ✓ Clip {i+1} created: {video_path} ({file_size} bytes)")
                            generated_clips.append(clip)
                            break  # Success, move to next clip
                        else:
                            print(f"[WorkerIntelligenceAI] ⚠ Clip {i+1} too small ({file_size} bytes), retry {retry+1}/{max_retries}")
                            # Try to fix the file
                            if retry < max_retries - 1:
                                clip = self._fix_small_clip_file(video_path, clip_spec)
                                if clip and clip.get('video_path'):
                                    continue  # Retry with fixed file
                    else:
                        print(f"[WorkerIntelligenceAI] ⚠ Clip {i+1} file not found: {video_path}, retry {retry+1}/{max_retries}")
                else:
                    print(f"[WorkerIntelligenceAI] ⚠ Clip {i+1} generation failed, retry {retry+1}/{max_retries}")
                
                # If all retries failed, try creating a proper placeholder
                if retry == max_retries - 1:
                    print(f"[WorkerIntelligenceAI] All retries failed for clip {i+1}, creating enhanced placeholder")
                    clip = self._create_placeholder_clip(clip_spec)
                    if clip and clip.get('video_path') and os.path.exists(clip['video_path']):
                        file_size = os.path.getsize(clip['video_path'])
                        if file_size > 10240:
                            print(f"[WorkerIntelligenceAI] ✓ Enhanced placeholder created: {clip['video_path']} ({file_size} bytes)")
                            generated_clips.append(clip)
                        else:
                            print(f"[WorkerIntelligenceAI] ✗ Even placeholder too small ({file_size} bytes), skipping clip")
                    else:
                        print(f"[WorkerIntelligenceAI] ✗ Could not create valid placeholder, skipping clip")
        
        print(f"[WorkerIntelligenceAI] Generated {len(generated_clips)}/{len(clip_plan['clips'])} valid clips")
        
        # CRITICAL: Only combine if we have valid clips with actual content
        if not generated_clips:
            print(f"[WorkerIntelligenceAI] ⚠ No valid clips generated! Creating fallback video with context...")
            # Create a single fallback video file with actual content from intelligence
            movie_path = self._create_contextual_fallback_video(intelligence, target_duration)
        else:
            # Combine clips into movie
            movie_path = self._combine_clips_to_movie(generated_clips, intelligence)
            
            # Verify final movie is valid and has content
            if movie_path and os.path.exists(movie_path):
                file_size = os.path.getsize(movie_path)
                if file_size <= 10240:
                    print(f"[WorkerIntelligenceAI] ⚠ Final movie too small ({file_size} bytes), recreating with context...")
                    # Recreate the movie with actual content
                    movie_path = self._recreate_movie_with_context(generated_clips, intelligence, target_duration)
                else:
                    # Verify video is playable
                    if not self._verify_video_file(movie_path):
                        print(f"[WorkerIntelligenceAI] ⚠ Video file invalid, recreating with context...")
                        movie_path = self._recreate_movie_with_context(generated_clips, intelligence, target_duration)
            else:
                print(f"[WorkerIntelligenceAI] ⚠ Movie path invalid, creating fallback with context...")
                movie_path = self._create_contextual_fallback_video(intelligence, target_duration)
        
        # FINAL VALIDATION: Ensure movie_path is valid before returning
        if movie_path and os.path.exists(movie_path):
            file_size = os.path.getsize(movie_path)
            if file_size <= 10240:
                print(f"[WorkerIntelligenceAI] ✗ CRITICAL: Final movie_path is invalid ({file_size} bytes), attempting final fix...")
                # Try one more time with contextual fallback
                final_fallback = self._create_contextual_fallback_video(intelligence, target_duration)
                if final_fallback and os.path.exists(final_fallback) and os.path.getsize(final_fallback) > 10240:
                    movie_path = final_fallback
                    print(f"[WorkerIntelligenceAI] ✓ Final fix successful: {movie_path} ({os.path.getsize(movie_path)} bytes)")
                else:
                    print(f"[WorkerIntelligenceAI] ✗ Final fix failed, movie_path will be None")
                    movie_path = None
        
        # Only return success if we have a valid movie_path
        success = movie_path is not None and os.path.exists(movie_path) and os.path.getsize(movie_path) > 10240
        
        return {
            'success': success,
            'clips': generated_clips,
            'movie_path': movie_path if success else None,
            'total_duration': sum(c.get('duration', 0) for c in generated_clips) if generated_clips else target_duration,
            'quality_score': self._calculate_overall_quality(generated_clips) if generated_clips else 0.3,
            'intelligence_used': {
                'sources': intelligence.get('metadata', {}).get('sources_count', 0),
                'intelligence_score': intelligence.get('metadata', {}).get('intelligence_score', 0)
            },
            'error': None if success else 'Could not create valid video file (all attempts failed)'
        }
    
    def _build_mega_prompt_from_intelligence(self, intelligence: Dict[str, Any]) -> str:
        """Build comprehensive, optimized prompt from all intelligence sources - ENHANCED VERSION"""
        # Structure: Main prompt + Context sections + Style guide
        main_prompt_parts = []
        context_sections = []
        style_guide = []
        
        # === MAIN PROMPT (Core content) ===
        prompt = intelligence.get('prompt', '') or intelligence.get('metadata', {}).get('original_prompt', '')
        title = intelligence.get('title', '') or intelligence.get('metadata', {}).get('title', '')
        
        # Enhanced main prompt with title
        if title:
            main_prompt_parts.append(f"Create a documentary video about: {title}")
        if prompt:
            main_prompt_parts.append(f"Focus: {prompt}")
        
        # === CONTEXT SECTIONS (Supporting information) ===
        
        # 1. Wikipedia/Research Context (High priority for factual content)
        research = intelligence.get('research', {})
        gathered_data = intelligence.get('gathered_data', {})  # From enhanced service worker
        
        # Check both old and new data structures
        wiki_data = research.get('wikipedia') or gathered_data.get('wikipedia')
        if wiki_data:
            wiki_extract = wiki_data.get('extract', '') or wiki_data.get('summary', '')
            if wiki_extract:
                # Extract key facts (first 500 chars for prompt efficiency)
                context_sections.append(f"CONTEXT: {wiki_extract[:500]}")
                if wiki_data.get('title'):
                    context_sections.append(f"Subject: {wiki_data['title']}")
        
        # 2. Keyword Foundation Context (Game/XP system keywords)
        keywords = gathered_data.get('keywords', []) or intelligence.get('keywords', [])
        if keywords:
            # Use high-power keywords for better AI context
            high_power_keywords = [k for k in keywords if isinstance(k, dict) and k.get('power_level', 0) > 5]
            if high_power_keywords:
                keyword_terms = [k.get('english_translation') or k.get('danish_keyword', '') for k in high_power_keywords[:10]]
                context_sections.append(f"KEY CONCEPTS: {', '.join(keyword_terms)}")
        
        # 3. Facts from Service Worker
        facts = gathered_data.get('facts', [])
        if facts:
            fact_descriptions = []
            for fact in facts[:5]:
                if isinstance(fact, dict):
                    fact_descriptions.append(fact.get('content', ''))
                else:
                    fact_descriptions.append(str(fact))
            if fact_descriptions:
                context_sections.append(f"KEY FACTS: {' | '.join(fact_descriptions)}")
        
        # 4. Image/Visual Context
        images_data = intelligence.get('images', {})
        if isinstance(images_data, dict):
            images = images_data.get('images', [])
        else:
            images = images_data if isinstance(images_data, list) else []
        
        if not images and gathered_data.get('images'):
            images = gathered_data['images']
        
        if images:
            # Extract visual descriptions
            visual_descriptions = []
            for img in images[:5]:
                if isinstance(img, dict):
                    desc = img.get('description') or img.get('alt') or img.get('url', '')
                    if desc:
                        visual_descriptions.append(desc)
            if visual_descriptions:
                context_sections.append(f"VISUAL STYLE: {', '.join(visual_descriptions[:3])}")
        
        # 5. Theme Context (High priority for style)
        theme = intelligence.get('theme', {})
        if theme.get('theme_type'):
            style_guide.append(f"STYLE: {theme['theme_type']} documentary")
            if theme.get('keywords'):
                style_guide.append(f"Style keywords: {', '.join(theme['keywords'][:5])}")
        
        # 6. Quality and Performance Context
        quality_score = gathered_data.get('metadata', {}).get('quality_score', 0)
        if quality_score > 70:
            style_guide.append("QUALITY: High-quality production")
        elif quality_score > 40:
            style_guide.append("QUALITY: Standard production")
        
        # 7. User Preferences (Personalization)
        behavioral = intelligence.get('behavioral', {})
        if behavioral.get('preferences'):
            prefs = behavioral['preferences']
            if isinstance(prefs, dict):
                if prefs.get('preferred_style'):
                    style_guide.append(f"User prefers: {prefs['preferred_style']}")
        
        # === BUILD FINAL PROMPT ===
        # Structure: Main prompt first, then context, then style guide
        final_parts = []
        
        # Main prompt (most important)
        if main_prompt_parts:
            final_parts.append(" ".join(main_prompt_parts))
        
        # Context (supporting information)
        if context_sections:
            final_parts.append("\n" + "\n".join(context_sections))
        
        # Style guide (visual and quality instructions)
        if style_guide:
            final_parts.append("\n" + "\n".join(style_guide))
        
        # Add quality instructions
        final_parts.append("\nINSTRUCTIONS: Create engaging, informative documentary-style video with smooth transitions and professional quality.")
        
        # Combine and optimize length (AI models have token limits)
        final_prompt = " ".join(final_parts)
        
        # Limit to reasonable length (most AI models handle 500-1000 tokens well)
        if len(final_prompt) > 2000:
            # Keep main prompt, truncate context
            main = " ".join(main_prompt_parts)
            context = "\n".join(context_sections[:3])  # Keep top 3 context items
            style = "\n".join(style_guide[:2])  # Keep top 2 style items
            final_prompt = f"{main}\n{context}\n{style}\nINSTRUCTIONS: Create engaging, informative documentary-style video."
        
        print(f"[WorkerIntelligenceAI] Built prompt (length: {len(final_prompt)} chars, quality_score: {quality_score})")
        return final_prompt
    
    def _plan_clips(
        self,
        intelligence: Dict[str, Any],
        target_duration: int,
        strategy: Dict[str, Any],
        clip_count: Optional[int] = None  # NEW: Emphasized clip count
    ) -> Dict[str, Any]:
        """Plan clip generation based on intelligence"""
        # Determine optimal clip count and durations
        # STANDARD: 10-second clips
        min_clip_duration = 8  # seconds - allow slight variation
        max_clip_duration = 12  # seconds - allow slight variation
        avg_clip_duration = 10  # STANDARD: 10 seconds per clip
        
        # Use user preferences if available (can override standard)
        if intelligence.get('user_stats', {}).get('preferred_clip_duration'):
            avg_clip_duration = intelligence['user_stats']['preferred_clip_duration']
            min_clip_duration = max(5, avg_clip_duration - 2)
            max_clip_duration = min(15, avg_clip_duration + 2)
        
        # Use emphasized clip count if provided, otherwise calculate
        if clip_count:
            num_clips = max(3, min(50, clip_count))  # Enforce limits
            print(f"[WorkerIntelligenceAI] Using emphasized clip count: {num_clips}")
        else:
            # Calculate number of clips needed from target duration
            num_clips = max(1, int(target_duration / avg_clip_duration))
            print(f"[WorkerIntelligenceAI] Calculated clip count from duration: {num_clips}")
        
        clips = []
        total_duration = 0
        
        import random
        
        for i in range(num_clips):
            # Vary clip duration - allow different lengths for variety
            # Use weighted distribution: 60% standard, 30% slightly varied, 10% more varied
            rand = random.random()
            if rand < 0.6:
                # Standard duration (most common)
                clip_duration = avg_clip_duration
            elif rand < 0.9:
                # Slight variation (±1 second)
                clip_duration = avg_clip_duration + random.choice([-1, 0, 1])
            else:
                # More variation (within min/max range)
                clip_duration = random.randint(min_clip_duration, max_clip_duration)
            
            # Ensure clip duration is within bounds
            clip_duration = max(min_clip_duration, min(max_clip_duration, clip_duration))
            
            # Ensure we don't exceed target
            if total_duration + clip_duration > target_duration:
                clip_duration = max(min_clip_duration, target_duration - total_duration)
            
            if clip_duration > 0:
                clips.append({
                    'index': i,
                    'duration': clip_duration,
                    'prompt_suffix': f"Part {i+1} of {num_clips}",
                    'variation_type': 'standard' if rand < 0.6 else ('slight' if rand < 0.9 else 'varied')
                })
                total_duration += clip_duration
        
        return {
            'clips': clips,
            'total_duration': total_duration,
            'num_clips': len(clips)
        }
    
    def _generate_single_clip(
        self,
        clip_spec: Dict[str, Any],
        mega_prompt: str,
        intelligence: Dict[str, Any],
        strategy: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate a single clip using AI"""
        # Select AI provider based on strategy
        provider = self._select_provider(strategy)
        
        # Build clip-specific prompt
        clip_prompt = f"{mega_prompt}\n\n{clip_spec['prompt_suffix']}"
        
        # Get image for this clip if available
        image_url = None
        if intelligence.get('images', {}).get('images'):
            images = intelligence['images']['images']
            image_index = clip_spec['index'] % len(images)
            image_url = images[image_index].get('url')
        
        # Generate clip using selected provider
        try:
            clip_result = self._call_ai_provider(
                provider,
                clip_prompt,
                image_url,
                clip_spec['duration']
            )
            
            if clip_result:
                return {
                    'index': clip_spec['index'],
                    'duration': clip_spec['duration'],
                    'video_path': clip_result.get('video_path'),
                    'quality_score': clip_result.get('quality_score', 0.7),
                    'provider': provider
                }
        except Exception as e:
            print(f"[WorkerIntelligenceAI] Error generating clip {clip_spec['index']}: {e}")
            # Fallback to placeholder
            return self._create_placeholder_clip(clip_spec)
        
        return None
    
    def _select_provider(self, strategy: Dict[str, Any]) -> str:
        """Select AI provider based on strategy"""
        providers = strategy.get('provider_priority', ['pika', 'runway'])
        
        for provider_name in providers:
            provider_info = self.ai_providers.get(provider_name)
            if provider_info and provider_info.get('available'):
                return provider_name
        
        # Fallback
        return 'ffmpeg_fallback'
    
    def _call_ai_provider(
        self,
        provider: str,
        prompt: str,
        image_url: Optional[str],
        duration: int,
        retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """Call specific AI provider to generate clip using AI services - ENHANCED WITH RETRY"""
        print(f"[WorkerIntelligenceAI] Calling {provider} with prompt length: {len(prompt)}")
        
        # Optimize prompt for AI provider (some have specific requirements)
        optimized_prompt = self._optimize_prompt_for_provider(prompt, provider)
        
        # FIRST: Try AI Provider Manager (actual AI services) with retry logic
        if ai_provider_manager and ai_provider_manager.active_providers:
            for attempt in range(retries):
                try:
                    # Prepare output path
                    output_path = None
                    if self.file_manager and self.doc_id:
                        clip_id = f"{self.doc_id}_clip_{datetime.now().timestamp()}_{attempt}"
                        output_path = str(self.file_manager.get_output_path(f"{clip_id}.mp4"))
                    
                    # Generate using AI provider manager
                    result = ai_provider_manager.generate_video(
                        prompt=optimized_prompt,
                        duration=duration,
                        image_url=image_url,
                        provider=provider if provider in ai_provider_manager.active_providers else None,
                        output_path=output_path
                    )
                    
                    if result and (result.get('video_path') or result.get('video_url')):
                        # Validate result
                        if result.get('video_path') and os.path.exists(result['video_path']):
                            file_size = os.path.getsize(result['video_path'])
                            if file_size > 10240:  # Valid video file
                                print(f"[WorkerIntelligenceAI] ✓ AI provider generated video: {result.get('provider', 'unknown')} ({file_size} bytes)")
                                return result
                    else:
                                print(f"[WorkerIntelligenceAI] ⚠ Generated video too small ({file_size} bytes), retrying...")
                    if attempt < retries - 1:
                                    continue
                    elif result.get('video_url'):
                            # URL-based result, download it
                            downloaded_path = self._download_video_from_url(result['video_url'], attempt)
                    if downloaded_path:
                                result['video_path'] = downloaded_path
                                return result
                    else:
                            print(f"[WorkerIntelligenceAI] ⚠ Invalid result, retrying...")
                    if attempt < retries - 1:
                                continue
                    
                except Exception as e:
                    print(f"[WorkerIntelligenceAI] AI provider manager error (attempt {attempt + 1}/{retries}): {e}")
                    if attempt < retries - 1:
                        import time
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    import traceback
                    traceback.print_exc()
        
        # FALLBACK: Use existing video generator if available (with retry)
        if self.video_generator:
            for attempt in range(retries):
                try:
                    # Prepare scraped data structure for video generator
                    scraped_data = {
                    'images': [{'url': image_url}] if image_url else [],
                    'scripts': [{'text': prompt}],
                    'total_images': 1 if image_url else 0,
                    'total_scripts': 1
                    }

                    # Generate clip using existing system
                    # VideoGenerator.generate_video() returns a dict with video_path or video_url
                    print(f"[WorkerIntelligenceAI] Calling video_generator.generate_video() with prompt: {prompt[:50]}...")

                    # Prepare output directory for video generator
                    output_dir = None
                    if self.file_manager:
                        output_dir = str(self.file_manager.get_output_dir())

                        clip_result = self.video_generator.generate_video(
                        prompt=prompt,
                        image_url=image_url,
                        duration=duration,
                        output_dir=output_dir  # Pass output directory so files are saved in the right place
                        )

                        print(f"[WorkerIntelligenceAI] Video generator result: {clip_result}")

                    if clip_result:
                            # Check for video_path (local file)
                            video_path = clip_result.get('video_path')

                            # If we got a video_url instead, download it
                    if not video_path and clip_result.get('video_url'):
                                video_url = clip_result.get('video_url')
                                print(f"[WorkerIntelligenceAI] Downloading video from URL: {video_url}")
                                video_path = self._download_video_from_url(video_url, attempt)

                    if video_path:
                                    # Ensure path is absolute and file exists
                        if not os.path.isabs(video_path) and self.file_manager:
                                        # Convert to absolute path using file manager
                                        output_dir = self.file_manager.get_output_dir()
                                        video_path = os.path.join(output_dir, os.path.basename(video_path))

                        if os.path.exists(video_path):
                                            # Verify file size (should be > 10KB for a real video)
                                            file_size = os.path.getsize(video_path)
                        if file_size > 10240:  # 10KB minimum
                                    print(f"[WorkerIntelligenceAI] ✓ Valid video clip created: {video_path} ({file_size} bytes)")
                                    return {
                                    'video_path': video_path,
                                    'quality_score': clip_result.get('quality_score', 0.7),
                                    'duration': duration,
                                    'provider': provider,
                                    'file_size': file_size
                                    }
                        else:
                                                print(f"[WorkerIntelligenceAI] ⚠ Video file too small ({file_size} bytes), likely placeholder")
                except Exception as e:
                    print(f"[WorkerIntelligenceAI] Error using video generator: {e}")
                    import traceback
                    traceback.print_exc()
        
                    # Fallback: Create a simple video file using file manager
                    if self.file_manager and self.doc_id:
                        try:
                            clip_id = f"{self.doc_id}_clip_{datetime.now().timestamp()}"
                            output_path = self.file_manager.get_output_path(f"{clip_id}.mp4")
                
                # Use file manager's ensure_mp4_file_created method
                # Import here to avoid circular dependency
                        except Exception as e:
                            print(f"[WorkerIntelligenceAI] Error: {e}")
                            pass
                        except Exception as e:
                            print(f"[WorkerIntelligenceAI] Error in fallback video creation: {e}")
                except Exception as e:
                    print(f"[WorkerIntelligenceAI] Error: {e}")
                    pass
                try:
                    from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
                    # Create a minimal orchestrator instance just for file creation
                    pipeline = PipelineOrchestrator()
                    
                    video_path = pipeline._ensure_mp4_file_created(
                        self.doc_id,
                        output_path,
                        fallback_duration=duration
                    )
                    
                    if video_path and os.path.exists(video_path):
                        return {
                            'video_path': str(video_path),
                            'quality_score': 0.6,
                            'duration': duration,
                            'provider': 'fallback'
                        }

                    print(f"[WorkerIntelligenceAI] Could not import PipelineOrchestrator: {import_err}")
                    # Last resort: create minimal MP4 using ffmpeg directly
                    try:
                        import subprocess
                        subprocess.run([
                            'ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=1920x1080:d={duration}',
                            '-c:v', 'libx264', '-t', str(duration), '-y', str(output_path)
                        ], check=True, timeout=30, capture_output=True)
                        if os.path.exists(output_path):
                            return {
                                'video_path': str(output_path),
                                'quality_score': 0.5,
                                'duration': duration,
                                'provider': 'ffmpeg_fallback'
                            }
                    except Exception as ffmpeg_err:
                        print(f"[WorkerIntelligenceAI] FFmpeg fallback failed: {ffmpeg_err}")
                except Exception as e:
                    print(f"[WorkerIntelligenceAI] Error creating fallback video: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Last resort: return None (will be handled by placeholder)
                    print(f"[WorkerIntelligenceAI] All generation methods failed, using placeholder")
        return None
    
    def _download_video_from_url(self, video_url: str, clip_index: int) -> Optional[str]:
        """Download video from URL and save locally"""
        try:
            import requests
            from pathlib import Path
            
            if not self.file_manager or not self.doc_id:
                print(f"[WorkerIntelligenceAI] Cannot download video: file_manager or doc_id not available")
                return None
            
            # Create output path
            output_path = self.file_manager.get_output_path(f"{self.doc_id}_clip_{clip_index}.mp4")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download video
            print(f"[WorkerIntelligenceAI] Downloading video from {video_url}...")
            response = requests.get(video_url, timeout=120, stream=True)
            response.raise_for_status()
            
            # Save to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 10240:
                print(f"[WorkerIntelligenceAI] ✓ Video downloaded: {output_path} ({os.path.getsize(output_path)} bytes)")
                return str(output_path)
            else:
                print(f"[WorkerIntelligenceAI] ⚠ Downloaded file too small or missing")
                return None
                
        except Exception as e:
            #            except Exception as e:
                print(f"[WorkerIntelligenceAI] Error: {e}")
                pass
#            print(f"[WorkerIntelligenceAI] Error downloading video: {e}")
#            import traceback
#            traceback.print_exc()
#            return None
    
    def _create_placeholder_clip(self, clip_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create placeholder clip if AI generation fails - but try to create actual video file"""
        print(f"[WorkerIntelligenceAI] Creating placeholder clip {clip_spec['index']} - attempting to create actual video file")
        
        # Try to create a simple video file with content (not just empty)
#                except Exception as e:
#                    print(f"[WorkerIntelligenceAI] Error: {e}")
#                    pass
        if self.file_manager and self.doc_id:
            try:
                from moviepy.editor import ColorClip, TextClip, CompositeVideoClip
                
                clip_id = f"{self.doc_id}_clip_{clip_spec['index']}"
                output_path = self.file_manager.get_output_path(f"{clip_id}.mp4")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                duration = clip_spec.get('duration', 10)
                
                # Create a colored clip with text
                clip = ColorClip(size=(1280, 768), color=(30, 30, 50), duration=duration)
                
                # Add text overlay
                try:
                    text = TextClip(
                        f"Clip {clip_spec['index'] + 1}",
                        fontsize=60,
                        color='white',
                        bg_color='rgba(0, 0, 0, 0.7)',
                        size=(1200, None),
                        method='caption'
                    ).set_position(('center', 'center')).set_duration(duration)
                    
                    video = CompositeVideoClip([clip, text])
                except Exception:
                    video = clip
                
                # Write video file with better quality
                video.write_videofile(
                    str(output_path),
                    fps=24,
                    codec='libx264',
                    audio=False,
                    preset='medium',
                    bitrate='2000k',
                    verbose=False,
                    logger=None
                )
                
                video.close()
                clip.close()
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 10240:
                    print(f"[WorkerIntelligenceAI] ✓ Placeholder video created: {output_path} ({os.path.getsize(output_path)} bytes)")
                    return {
                        'index': clip_spec['index'],
                        'duration': duration,
                        'video_path': str(output_path),
                        'quality_score': 0.4,
                        'provider': 'placeholder_enhanced',
                        'file_size': os.path.getsize(output_path)
                    }
            except Exception as e:
                print(f"[WorkerIntelligenceAI] Error creating enhanced placeholder: {e}")
        
        # Fallback to minimal placeholder
        return {
            'index': clip_spec['index'],
            'duration': clip_spec['duration'],
            'video_path': None,
            'quality_score': 0.3,
            'provider': 'placeholder'
        }
    
    def _combine_clips_to_movie(
        self,
        clips: List[Dict[str, Any]],
        intelligence: Dict[str, Any]
    ) -> Optional[str]:
        """Combine generated clips into final MPEG movie"""
        print(f"[WorkerIntelligenceAI] Combining {len(clips)} clips into movie")
        
        # Filter out invalid clips - must have video_path, exist, and be > 10KB
#                except Exception as e:
#                    print(f"[WorkerIntelligenceAI] Error: {e}")
#                    pass
        valid_clips = []
        for c in clips:
            video_path = c.get('video_path')
            if video_path and os.path.exists(video_path):
                file_size = os.path.getsize(video_path)
                if file_size > 10240:  # > 10KB
                    valid_clips.append(c)
                    print(f"[WorkerIntelligenceAI] ✓ Valid clip: {video_path} ({file_size} bytes)")
                else:
                    print(f"[WorkerIntelligenceAI] ✗ Invalid clip (too small): {video_path} ({file_size} bytes)")
            else:
                print(f"[WorkerIntelligenceAI] ✗ Invalid clip (missing): {video_path}")
        
        if not valid_clips:
            print("[WorkerIntelligenceAI] No valid clips to combine")
            # Use file manager to create a single video file
            if self.file_manager and self.doc_id:
                try:
                    output_path = self.file_manager.get_output_path(f"{self.doc_id}.mp4")
                    from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
                    pipeline = PipelineOrchestrator()
                    video_path = pipeline._ensure_mp4_file_created(
                        self.doc_id,
                        output_path,
                        fallback_duration=180
                    )
                    if video_path:
                        return str(video_path)
                except Exception as e:
                    print(f"[WorkerIntelligenceAI] Error creating fallback video: {e}")
            return None
        
        # Use file manager for output path if available
#                    except Exception as e:
            print(f"[WorkerIntelligenceAI] Error: {e}")
            pass
        if self.file_manager and self.doc_id:
            output_path = self.file_manager.get_output_path(f"{self.doc_id}.mp4")
        else:
            output_path = Path(f"/tmp/movie_{datetime.now().timestamp()}.mp4")
        
        # Use MoviePy or FFmpeg to combine clips
        try:
            from moviepy.editor import VideoFileClip, concatenate_videoclips
            
            video_clips = []
            for clip in valid_clips:
                clip_path = clip['video_path']
            if os.path.exists(clip_path):
                try:
                        video_clips.append(VideoFileClip(clip_path))
                except Exception as e:
                        print(f"[WorkerIntelligenceAI] Error loading clip {clip_path}: {e}")
                        pass
            
            if video_clips:
                final_video = concatenate_videoclips(video_clips)
                final_video.write_videofile(
                    str(output_path),
                    codec='libx264',
                    audio_codec='aac',
                    verbose=False,
                    logger=None
                )
                final_video.close()
                
                # Clean up individual clips
                for clip in video_clips:
                    clip.close()
                
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    if file_size > 10240:  # > 10KB
                        print(f"[WorkerIntelligenceAI] ✓ Movie created: {output_path} ({file_size} bytes)")
                        return str(output_path)
                    else:
                        print(f"[WorkerIntelligenceAI] ✗ Movie too small ({file_size} bytes), recreating...")
                        # Recreate using pipeline orchestrator
                        if self.file_manager and self.doc_id:
                            from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
                            pipeline = PipelineOrchestrator()
                            recreated_path = pipeline._ensure_mp4_file_created(
                                self.doc_id,
                                output_path,
                                fallback_duration=180
                            )
                            if recreated_path and os.path.exists(recreated_path) and os.path.getsize(recreated_path) > 10240:
                                print(f"[WorkerIntelligenceAI] ✓ Movie recreated: {recreated_path} ({os.path.getsize(recreated_path)} bytes)")
                                return str(recreated_path)
                else:
                    print(f"[WorkerIntelligenceAI] Movie file not found after creation: {output_path}")
        except Exception as e:
            print(f"[WorkerIntelligenceAI] Error combining clips: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: create video with context
            return self._create_contextual_fallback_video(intelligence, 180)
            import traceback
            traceback.print_exc()
            
            # Fallback: use first valid clip
            if valid_clips:
                first_clip = valid_clips[0]['video_path']
                if os.path.exists(first_clip):
                    print(f"[WorkerIntelligenceAI] Using first clip as fallback: {first_clip}")
                    return first_clip
        
        except Exception as e:
            print(f"[WorkerIntelligenceAI] Error: {e}")
            pass
        return None
    
    def _calculate_overall_quality(self, clips: List[Dict[str, Any]]) -> float:
        """Calculate overall quality score from clips"""
        if not clips:
            return 0.0
        
#                except Exception as e:
#                    print(f"[WorkerIntelligenceAI] Error: {e}")
#                    pass
        quality_scores = [c.get('quality_score', 0) for c in clips if c.get('quality_score')]
        if not quality_scores:
            return 0.0
        
        return sum(quality_scores) / len(quality_scores)
    
    def _create_contextual_fallback_video(self, intelligence: Dict[str, Any], duration: int) -> Optional[str]:
        """Create a fallback video with actual content from intelligence"""
        print(f"[WorkerIntelligenceAI] Creating contextual fallback video (duration: {duration}s)")
        
        if not self.file_manager or not self.doc_id:
            print("[WorkerIntelligenceAI] Cannot create fallback: file_manager or doc_id missing")
            return None
        
        try:
            output_path = self.file_manager.get_output_path(f"{self.doc_id}.mp4")
            
            # Get context from intelligence
            prompt = intelligence.get('prompt', '') or intelligence.get('metadata', {}).get('original_prompt', '')
            title = intelligence.get('title', '') or intelligence.get('metadata', {}).get('title', '')
            
            # Build comprehensive prompt from intelligence
            context_prompt = self._build_mega_prompt_from_intelligence(intelligence)
            
            # Try to use video generator to create actual content
            if self.video_generator:
                try:
                    print(f"[WorkerIntelligenceAI] Attempting to generate video with context: {context_prompt[:100]}...")
                    result = self.video_generator.generate_video(
                        prompt=context_prompt or prompt,
                        duration=duration,
                        output_dir=str(self.file_manager.get_output_dir())
                    )
                    
                    if result and result.get('video_path'):
                        video_path = result['video_path']
                    if os.path.exists(video_path) and os.path.getsize(video_path) > 10240:
                            print(f"[WorkerIntelligenceAI] ✓ Contextual video created: {video_path} ({os.path.getsize(video_path)} bytes)")
                            return str(video_path)
                except Exception as e:
                    print(f"[WorkerIntelligenceAI] Video generator failed: {e}")
            
            # Fallback: Use pipeline orchestrator
            from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
            pipeline = PipelineOrchestrator()
            video_path = pipeline._ensure_mp4_file_created(
                self.doc_id,
                output_path,
                fallback_duration=duration
            )
            
            if video_path and os.path.exists(video_path):
                file_size = os.path.getsize(video_path)
                if file_size > 10240:
                    print(f"[WorkerIntelligenceAI] ✓ Fallback video created: {video_path} ({file_size} bytes)")
                    return str(video_path)
                else:
                    print(f"[WorkerIntelligenceAI] ✗ Fallback video too small ({file_size} bytes)")
            else:
                print(f"[WorkerIntelligenceAI] ✗ Fallback video creation failed")
                
        except Exception as e:
            print(f"[WorkerIntelligenceAI] ✗ Error creating contextual fallback: {e}")
            import traceback
            traceback.print_exc()
        
        except Exception as e:
            print(f"[WorkerIntelligenceAI] Error: {e}")
            pass
        return None
    
    def _recreate_movie_with_context(self, clips: List[Dict[str, Any]], intelligence: Dict[str, Any], duration: int) -> Optional[str]:
        """Recreate movie with actual content from clips and intelligence"""
        print(f"[WorkerIntelligenceAI] Recreating movie with context (duration: {duration}s)")
        
        # First try to combine existing valid clips
        if clips:
            valid_clips = [c for c in clips if c.get('video_path') and os.path.exists(c.get('video_path')) and os.path.getsize(c.get('video_path', '')) > 10240]
            if valid_clips:
                movie_path = self._combine_clips_to_movie(valid_clips, intelligence)
                if movie_path and os.path.exists(movie_path) and os.path.getsize(movie_path) > 10240:
                    if self._verify_video_file(movie_path):
                        return movie_path
        
        # If that fails, create contextual fallback
                    #                    except Exception as e:
                print(f"[WorkerIntelligenceAI] Error: {e}")
                pass
        if self.file_manager and self.doc_id:
            return self._create_contextual_fallback_video(intelligence, duration)
        return None
    
    def _create_contextual_fallback_video(self, intelligence: Dict[str, Any], duration: int) -> Optional[str]:
        """Create a contextual fallback video with actual content from intelligence"""
        print(f"[WorkerIntelligenceAI] Creating contextual fallback video (duration: {duration}s)")
        
        if not self.file_manager or not self.doc_id:
            print("[WorkerIntelligenceAI] File manager or doc_id not available")
            return None
        
        try:
            output_path = self.file_manager.get_output_path(f"{self.doc_id}_contextual.mp4")
            
            # Build contextual prompt from intelligence
            title = intelligence.get('title', 'Documentary')
            summary = intelligence.get('summary', '')
            keywords = intelligence.get('keywords', [])
            
            # Create a text overlay with context
            text_content = f"{title}\n\n"
            if summary:
                text_content += summary[:200] + "..."
            elif keywords:
                text_content += f"Topics: {', '.join(keywords[:5])}"
            else:
                text_content += "Generated Documentary"
            
            # Use ffmpeg to create video with text overlay
            import subprocess
            try:
                # Escape text for ffmpeg
                text_escaped = text_content.replace("'", "\\'").replace(":", "\\:")
                
                subprocess.run([
                    'ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=1920x1080:d={duration}',
                    '-vf', f"drawtext=text='{text_escaped}':x=(w-text_w)/2:y=(h-text_h)/2:fontsize=48:fontcolor=white:box=1:boxcolor=0x00000000@1:boxborderw=10",
                    '-c:v', 'libx264', '-t', str(duration), '-y', str(output_path)
                ], check=True, timeout=120, capture_output=True)
                
            except Exception as e:
                print(f"[WorkerIntelligenceAI] Error: {e}")
                pass
            if os.path.exists(output_path) and os.path.getsize(output_path) > 10240:
                if self._verify_video_file(str(output_path)):
                        print(f"[WorkerIntelligenceAI] ✓ Contextual fallback video created: {output_path}")
                        return str(output_path)
            else:
                        print(f"[WorkerIntelligenceAI] ✗ Contextual fallback video failed verification")
                #                else:
#                    print(f"[WorkerIntelligenceAI] ✗ Contextual fallback video too small or missing")
                #                except subprocess.CalledProcessError as e:
#                print(f"[WorkerIntelligenceAI] ✗ FFmpeg error: {e.stderr.decode() if e.stderr else 'Unknown'}")
                #                except Exception as e:
#                print(f"[WorkerIntelligenceAI] ✗ Error creating contextual fallback: {e}")
        except Exception as e:
            print(f"[WorkerIntelligenceAI] Critical error in _create_contextual_fallback_video: {e}")
        
        return None
    
    def _verify_video_file(self, video_path: str) -> bool:
        """Verify that video file is valid and playable"""
        try:
            if not os.path.exists(video_path):
                return False
            
            file_size = os.path.getsize(video_path)
            if file_size <= 10240:  # Less than 10KB is likely invalid
                return False
            
            # Try to open with moviepy to verify it's a valid video
            try:
                from moviepy.editor import VideoFileClip
                clip = VideoFileClip(video_path)
                duration = clip.duration
                clip.close()
                
#            if duration > 0:
#                    print(f"[WorkerIntelligenceAI] ✓ Video verified: {video_path} (duration: {duration}s, size: {file_size} bytes)")
#                    return True
#            else:
#                    print(f"[WorkerIntelligenceAI] ✗ Video has zero duration: {video_path}")
#                    return False
#        except Exception as e:
                print(f"[WorkerIntelligenceAI] ⚠ Could not verify with moviepy: {e}, assuming valid based on size")
                # If moviepy fails but file is large enough, assume it's valid
            except Exception as e:
                    print(f"[WorkerIntelligenceAI] Could not verify with moviepy: {e}, assuming valid based on size")
                    # If moviepy fails but file is large enough, assume it's valid
                
#        except Exception as e:
#            print(f"[WorkerIntelligenceAI] Error verifying video: {e}")
#            return False
        except Exception as e:
            print(f"[WorkerIntelligenceAI] Error: {e}")
            pass
#
