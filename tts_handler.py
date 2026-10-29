import threading
import queue
import pyttsx3

class TTSHandler:
    """
    Handles Text-to-Speech playback using pyttsx3 SAPI5 (offline Windows engine).
    Uses a worker thread to run the speech engine to prevent GUI lockups.
    """
    
    def __init__(self, voice_index: int = None, rate: int = 175):
        self.rate = rate
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.stop_requested = False
        self.worker_thread = None
        
        # Test engine initialization and list available voices
        try:
            engine = pyttsx3.init()
            self.voices = engine.getProperty('voices')
            self.has_voices = len(self.voices) > 0
            
            # Find default female voice index if voice_index is None
            if voice_index is None:
                default_index = 0
                for idx, v in enumerate(self.voices):
                    if "female" in getattr(v, "gender", "").lower() or "zira" in v.name.lower():
                        default_index = idx
                        break
                self.voice_index = default_index
            else:
                self.voice_index = voice_index
                
            del engine
        except Exception as e:
            print(f"Failed to initialize pyttsx3 SAPI5: {e}")
            self.voices = []
            self.has_voices = False
            self.voice_index = 0

    def get_available_voices(self) -> list:
        """Returns list of voice objects with metadata (id, name, languages)."""
        return [{"id": v.id, "name": v.name} for v in self.voices]

    def speak(self, text: str, on_start_callback=None, on_end_callback=None) -> None:
        """
        Asynchronously speaks the given text on a background worker thread.
        
        Args:
            text: String content to speak.
            on_start_callback: Function called when speech starts.
            on_end_callback: Function called when speech ends.
        """
        if not self.has_voices:
            if on_end_callback:
                on_end_callback()
            return
            
        # Clean up text to speak: strip markdown symbols to sound natural
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").replace("Assistant:", "").strip()
        if not clean_text:
            if on_end_callback:
                on_end_callback()
            return

        self.stop_requested = False
        
        # Spawn a thread to speak the text
        # Because SAPI5 is a Windows COM object, it is highly sensitive to the thread it runs on.
        # Initializing, running, and destroying the pyttsx3 engine entirely within the worker thread
        # is the most stable approach to avoid COM CoInitialize/threading errors.
        def speak_task():
            self.is_speaking = True
            if on_start_callback:
                on_start_callback()
                
            try:
                # Local initialization inside the thread
                engine = pyttsx3.init()
                
                # Apply current configurations
                voices = engine.getProperty('voices')
                if 0 <= self.voice_index < len(voices):
                    engine.setProperty('voice', voices[self.voice_index].id)
                engine.setProperty('rate', self.rate)
                
                # Speak
                engine.say(clean_text)
                engine.runAndWait()
                
                # Clean up
                del engine
            except Exception as e:
                print(f"Error in speech playback thread: {e}")
            finally:
                self.is_speaking = False
                if on_end_callback:
                    on_end_callback()

        self.worker_thread = threading.Thread(target=speak_task, daemon=True)
        self.worker_thread.start()

    def set_voice(self, index: int) -> None:
        """Sets the active voice index."""
        if 0 <= index < len(self.voices):
            self.voice_index = index

    def set_rate(self, rate: int) -> None:
        """Sets the speaking rate (words per minute)."""
        self.rate = rate
