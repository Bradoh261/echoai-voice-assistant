import os
import sys
import ctypes
import time
import tempfile
import pyttsx3
from gtts import gTTS

class TTSService:
    def __init__(self):
        """Initializes the Text-to-Speech service using pyttsx3 (SAPI5 on Windows)."""
        self.engine = None
        self.voices = []
        self.current_voice_id = None
        self.rate = 180  # Default speech rate
        self.volume = 1.0  # Default volume (0.0 to 1.0)
        self.is_playing = False
        
        try:
            self.engine = pyttsx3.init()
            self.voices = self.engine.getProperty('voices')
            if self.voices:
                # Default to a gentle female voice (Zira) if available, otherwise first voice
                female_voice = next((v for v in self.voices if "female" in getattr(v, 'gender', '').lower() or "zira" in v.name.lower()), None)
                if female_voice:
                    self.current_voice_id = female_voice.id
                else:
                    self.current_voice_id = self.voices[0].id
        except Exception as e:
            print(f"Failed to initialize pyttsx3 engine: {e}")

    def get_available_voices(self) -> list:
        """Returns list of dicts with voice metadata: [{'id': id, 'name': name}]"""
        return [{"id": v.id, "name": v.name} for v in self.voices]

    def set_voice(self, voice_id: str):
        """Sets the active voice for the offline engine."""
        self.current_voice_id = voice_id

    def set_rate(self, rate: int):
        """Sets speech rate (words per minute)."""
        self.rate = rate

    def set_volume(self, volume: float):
        """Sets volume level (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))

    def _play_mp3_windows(self, filepath: str):
        """Plays an MP3 file using Windows MCI (Media Control Interface) natively."""
        self.is_playing = True
        alias = f"speech_{int(time.time())}"
        
        # Quote filepath for MCI
        filepath_clean = os.path.abspath(filepath).replace("\\", "/")
        
        # Open the audio file
        ctypes.windll.winmm.mciSendStringW(f'open "{filepath_clean}" type mpegvideo alias {alias}', None, 0, 0)
        # Play the audio file
        ctypes.windll.winmm.mciSendStringW(f'play {alias}', None, 0, 0)
        
        # Poll status so we can check if it is still playing or if we should stop
        status_buf = ctypes.create_unicode_buffer(128)
        while self.is_playing:
            ctypes.windll.winmm.mciSendStringW(f'status {alias} mode', status_buf, 128, 0)
            mode = status_buf.value.strip()
            if mode != "playing":
                break
            time.sleep(0.1)
            
        # Close and clean up
        ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, 0)
        self.is_playing = False

    def speak(self, text: str, mode: str = "offline"):
        """
        Speaks the given text using either 'offline' (pyttsx3) or 'online' (gTTS) mode.
        
        Args:
            text: The text string to speak.
            mode: 'offline' or 'online'
        """
        if not text:
            return
            
        self.is_playing = True
        
        if mode == "offline" and self.engine:
            try:
                # Update properties before speaking
                self.engine.setProperty('rate', self.rate)
                self.engine.setProperty('volume', self.volume)
                if self.current_voice_id:
                    self.engine.setProperty('voice', self.current_voice_id)
                
                # Speak
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"pyttsx3 speaking error: {e}. Falling back to online TTS.")
                mode = "online"  # fallback
            finally:
                self.is_playing = False
                
        if mode == "online" or not self.engine:
            # Online gTTS implementation
            temp_file = None
            try:
                tts = gTTS(text=text, lang='en', slow=False)
                # Create a temp file in a safe location
                fd, temp_path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                tts.save(temp_path)
                
                # Play audio
                self._play_mp3_windows(temp_path)
                
                # Delete temp file
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            except Exception as e:
                print(f"gTTS error: {e}")
            finally:
                self.is_playing = False

    def stop(self):
        """Stops the active speech playback immediately."""
        self.is_playing = False
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass
        # MCI close command
        # This closes any open MCI mpegvideo devices to stop playing sound
        ctypes.windll.winmm.mciSendStringW('close all', None, 0, 0)
