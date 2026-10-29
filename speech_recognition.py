import sys
import os

# Save original sys.path and sys.modules['speech_recognition']
orig_path = list(sys.path)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Remove current directory from sys.path
while current_dir in sys.path:
    sys.path.remove(current_dir)
while "" in sys.path:
    sys.path.remove("")

# Remove local 'speech_recognition' from sys.modules temporarily to import the real package
local_module = sys.modules.get('speech_recognition')
if 'speech_recognition' in sys.modules:
    del sys.modules['speech_recognition']

try:
    import speech_recognition as sr
finally:
    # Restore the local module in sys.modules and sys.path
    if local_module is not None:
        sys.modules['speech_recognition'] = local_module
    sys.path = orig_path

class SpeechRecognizer:
    def __init__(self):
        """Initializes the SpeechRecognizer with a recognizer instance."""
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 300
        self.recognizer.pause_threshold = 1.0  # seconds of silence before a phrase is considered complete
        
    def calibrate(self, source, duration=1.0):
        """Calibrates the microphone for ambient noise."""
        try:
            self.recognizer.adjust_for_ambient_noise(source, duration=duration)
        except Exception as e:
            print(f"Calibration error: {e}")

    def listen_and_recognize(self, source, timeout=5, phrase_time_limit=10) -> str:
        """
        Listens to the microphone source and converts it to text using Google Speech API.
        
        Returns:
            str: The recognized text.
        """
        # Listen for audio
        audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        
        # Perform speech recognition
        text = self.recognizer.recognize_google(audio)
        return text
