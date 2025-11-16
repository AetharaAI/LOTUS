"""
Voice Interface Module - STT, TTS, Wake Word Detection

Provides voice interaction capabilities for LOTUS.
"""

import asyncio
import json
from typing import Dict, Any, Optional
import threading

try:
    import whisper
    import pyttsx3
    import pyaudio
    import numpy as np
except ImportError as e:
    print(f"Warning: Voice interface dependencies not available: {e}")

from lotus.lib.module import BaseModule
from lotus.lib.decorators import on_event, tool
from lotus.lib.logging import get_logger

logger = get_logger("voice_interface")


class VoiceInterface(BaseModule):
    """Voice interaction module"""
    
    async def initialize(self) -> None:
        """Initialize voice interface"""
        self.logger.info("🎤 Initializing Voice Interface Module")
        
        self.listening = False
        self.wake_word = self.config.get("voice.wake_word", "lotus")
        
        try:
            self.whisper_model = whisper.load_model("base")
            self.logger.info("✅ Whisper STT model loaded")
        except Exception as e:
            self.logger.error(f"❌ Failed to load Whisper: {e}")
            self.whisper_model = None
        
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)
            self.logger.info("✅ TTS engine initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize TTS: {e}")
            self.tts_engine = None
    
    @on_event("voice.start_listening")
    async def start_listening(self, event: Dict[str, Any]) -> None:
        """Start listening for voice input"""
        self.listening = True
        self.logger.info("🎧 Started listening for voice input")
        await self.publish("voice.listening_started", {})
    
    @on_event("voice.stop_listening")
    async def stop_listening(self, event: Dict[str, Any]) -> None:
        """Stop listening"""
        self.listening = False
        self.logger.info("⏹️  Stopped listening")
        await self.publish("voice.listening_stopped", {})
    
    @on_event("action.speak")
    async def speak(self, event: Dict[str, Any]) -> None:
        """Convert text to speech"""
        text = event.get("text", "")
        if not text or not self.tts_engine:
            return
        
        try:
            self.logger.debug(f"🔊 Speaking: {text[:50]}...")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            await self.publish("voice.spoke", {"text": text})
        except Exception as e:
            self.logger.error(f"❌ TTS failed: {e}")
    
    @tool("transcribe_audio")
    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file to text"""
        if not self.whisper_model:
            return {"success": False, "error": "Whisper model not loaded"}
        
        try:
            result = self.whisper_model.transcribe(audio_path)
            return {
                "success": True,
                "text": result["text"],
                "language": result.get("language", "unknown")
            }
        except Exception as e:
            self.logger.error(f"❌ Transcription failed: {e}")
            return {"success": False, "error": str(e)}
    
    @tool("speak_text")
    async def speak_text(self, text: str) -> Dict[str, Any]:
        """Speak text synchronously"""
        if not self.tts_engine:
            return {"success": False, "error": "TTS engine not available"}
        
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}