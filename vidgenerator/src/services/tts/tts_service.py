"""Text-to-Speech service with multiple providers and fallback"""
import os
import requests
from typing import Optional, Dict, Any
from pathlib import Path
from abc import ABC, abstractmethod


class TTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available (API keys configured)"""
        pass
    
    @abstractmethod
    def generate_speech(
        self, 
        text: str, 
        output_path: str,
        voice: Optional[str] = None,
        language: str = "en",
        speed: float = 1.0
    ) -> Optional[str]:
        """Generate speech from text
        
        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            voice: Voice ID or name (provider-specific)
            language: Language code (e.g., 'en', 'da')
            speed: Speech speed (1.0 = normal)
            
        Returns:
            Path to generated audio file or None if failed
        """
        pass


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs TTS provider"""
    
    def __init__(self):
        self.api_key = os.getenv('ELEVENLABS_API_KEY')
        self.api_url = "https://api.elevenlabs.io/v1/text-to-speech"
        self.default_voice = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')  # Default voice
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate_speech(
        self, 
        text: str, 
        output_path: str,
        voice: Optional[str] = None,
        language: str = "en",
        speed: float = 1.0
    ) -> Optional[str]:
        if not self.is_available():
            return None
        
        try:
            voice_id = voice or self.default_voice
            
            # Prepare request
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",  # Supports multiple languages
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "speed": speed
                }
            }
            
            # Make request
            response = requests.post(
                f"{self.api_url}/{voice_id}",
                json=data,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            
            # Save audio file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            return str(output_file)
            
        except Exception as e:
            print(f"ElevenLabs TTS error: {e}")
            return None


class AzureTTSProvider(TTSProvider):
    """Azure Cognitive Services TTS provider"""
    
    def __init__(self):
        self.api_key = os.getenv('AZURE_TTS_KEY')
        self.region = os.getenv('AZURE_TTS_REGION', 'westeurope')
        self.api_url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"
    
    def is_available(self) -> bool:
        return bool(self.api_key and self.region)
    
    def generate_speech(
        self, 
        text: str, 
        output_path: str,
        voice: Optional[str] = None,
        language: str = "en",
        speed: float = 1.0
    ) -> Optional[str]:
        if not self.is_available():
            return None
        
        try:
            # Map language to Azure voice
            voice_map = {
                "en": "en-US-AriaNeural",
                "da": "da-DK-ChristelNeural",
                "de": "de-DE-KatjaNeural",
                "fr": "fr-FR-DeniseNeural",
                "es": "es-ES-ElviraNeural"
            }
            
            voice_name = voice or voice_map.get(language, "en-US-AriaNeural")
            
            # SSML for Azure TTS
            ssml = f'''<speak version='1.0' xml:lang='{language}'>
                <voice xml:lang='{language}' xml:gender='Female' name='{voice_name}'>
                    <prosody rate='{speed:.2f}'>
                        {text}
                    </prosody>
                </voice>
            </speak>'''
            
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3"
            }
            
            response = requests.post(
                self.api_url,
                data=ssml.encode('utf-8'),
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            
            # Save audio file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            return str(output_file)
            
        except Exception as e:
            print(f"Azure TTS error: {e}")
            return None


class GoogleTTSProvider(TTSProvider):
    """Google Cloud Text-to-Speech provider"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_CLOUD_TTS_KEY')
        self.api_url = "https://texttospeech.googleapis.com/v1/text:synthesize"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate_speech(
        self, 
        text: str, 
        output_path: str,
        voice: Optional[str] = None,
        language: str = "en",
        speed: float = 1.0
    ) -> Optional[str]:
        if not self.is_available():
            return None
        
        try:
            import base64
            
            # Map language to Google voice
            voice_map = {
                "en": "en-US-Wavenet-F",
                "da": "da-DK-Wavenet-D",
                "de": "de-DE-Wavenet-F",
                "fr": "fr-FR-Wavenet-C",
                "es": "es-ES-Wavenet-C"
            }
            
            voice_name = voice or voice_map.get(language, "en-US-Wavenet-F")
            
            data = {
                "input": {"text": text},
                "voice": {
                    "languageCode": language,
                    "name": voice_name,
                    "ssmlGender": "FEMALE"
                },
                "audioConfig": {
                    "audioEncoding": "MP3",
                    "speakingRate": speed
                }
            }
            
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                json=data,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            audio_content = base64.b64decode(result['audioContent'])
            
            # Save audio file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'wb') as f:
                f.write(audio_content)
            
            return str(output_file)
            
        except Exception as e:
            print(f"Google TTS error: {e}")
            return None


class PlaceholderTTSProvider(TTSProvider):
    """Placeholder TTS provider (always available, creates empty audio)"""
    
    def is_available(self) -> bool:
        return True  # Always available as fallback
    
    def generate_speech(
        self, 
        text: str, 
        output_path: str,
        voice: Optional[str] = None,
        language: str = "en",
        speed: float = 1.0
    ) -> Optional[str]:
        # Create placeholder audio file (empty MP3)
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create minimal valid MP3 file (empty)
            with open(output_file, 'wb') as f:
                f.write(b'')  # Placeholder empty file
            
            print(f"Placeholder TTS: Created empty audio file for '{text[:50]}...'")
            return str(output_file)
            
        except Exception as e:
            print(f"Placeholder TTS error: {e}")
            return None


class TTSService:
    """Text-to-Speech service with multiple providers and systematic fallback"""
    
    def __init__(self):
        """Initialize TTS service with available providers"""
        self.providers = []
        
        # Try to initialize providers in order of preference
        providers_to_try = [
            ElevenLabsProvider,
            AzureTTSProvider,
            GoogleTTSProvider
        ]
        
        for ProviderClass in providers_to_try:
            try:
                provider = ProviderClass()
                if provider.is_available():
                    self.providers.append(provider)
                    print(f"[TTS] Enabled: {ProviderClass.__name__}")
            except Exception as e:
                print(f"[TTS] Could not initialize {ProviderClass.__name__}: {e}")
        
        # Always add placeholder as last resort
        if not self.providers:
            self.providers.append(PlaceholderTTSProvider())
            print("[TTS] Enabled: Placeholder (fallback)")
        else:
            # Add placeholder as fallback
            self.providers.append(PlaceholderTTSProvider())
    
    def generate_speech(
        self, 
        text: str, 
        output_path: str,
        voice: Optional[str] = None,
        language: str = "en",
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """Generate speech from text using available providers with fallback
        
        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            voice: Voice ID or name (provider-specific)
            language: Language code (e.g., 'en', 'da')
            speed: Speech speed (1.0 = normal)
            
        Returns:
            Dict with:
                - success: bool
                - audio_path: str or None
                - provider: str
                - is_placeholder: bool
        """
        # Try each provider until one succeeds
        for provider in self.providers:
            provider_name = provider.__class__.__name__
            print(f"[TTS] Attempting generation with {provider_name}...")
            
            audio_path = provider.generate_speech(
                text=text,
                output_path=output_path,
                voice=voice,
                language=language,
                speed=speed
            )
            
            if audio_path:
                is_placeholder = isinstance(provider, PlaceholderTTSProvider)
                print(f"[TTS] Success with {provider_name}")
                return {
                    'success': True,
                    'audio_path': audio_path,
                    'provider': provider_name.replace('Provider', ''),
                    'is_placeholder': is_placeholder
                }
            else:
                print(f"[TTS] Failed with {provider_name}, trying next...")
        
        # Should never reach here (placeholder always succeeds)
        return {
            'success': False,
            'audio_path': None,
            'provider': 'none',
            'is_placeholder': True
        }
    
    def get_available_providers(self) -> list:
        """Get list of available provider names"""
        return [p.__class__.__name__.replace('Provider', '') for p in self.providers]
