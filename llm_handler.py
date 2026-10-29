"""
llm_handler.py
--------------
Dual-backend LLM handler supporting:
  1. Ollama (offline, no API key) — tried first
  2. Google Gemini (online, requires API key) — used as fallback or if selected

Ollama communicates over a local HTTP server (http://localhost:11434).
If Ollama is not running or no model is pulled, the handler transparently
falls back to Gemini if a key is available.
"""

import requests
from utils import get_api_key

# ---------------------------------------------------------------------------
# Ollama support
# ---------------------------------------------------------------------------
try:
    import ollama as _ollama_lib
    HAS_OLLAMA_LIB = True
except ImportError:
    HAS_OLLAMA_LIB = False

OLLAMA_BASE_URL = "http://localhost:11434"

# ---------------------------------------------------------------------------
# Gemini support (new google.genai SDK)
# ---------------------------------------------------------------------------
try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# ---------------------------------------------------------------------------
# Personality system prompts
# ---------------------------------------------------------------------------
PERSONALITIES = {
    "Friendly": (
        "You are a warm, kind, and helpful AI voice assistant. "
        "Keep your responses concise, friendly, and conversational since they will be read aloud. "
        "Speak directly and avoid excessive formatting like bullet points or markdown tables unless necessary."
    ),
    "Professional": (
        "You are a highly professional, polite, and expert academic voice assistant. "
        "Provide structured, clear, and informative explanations. Keep explanations clear but concise, "
        "and avoid long-winded formatting. Speak with poise and authority."
    ),
    "Sarcastic": (
        "You are a highly sarcastic, witty, and slightly cheeky voice assistant. "
        "You always answer questions accurately, but you frame your responses with dry humor, "
        "playful sarcasm, or mild exasperation. Keep responses punchy and short."
    ),
    "Academic Tutor": (
        "You are a warm, knowledgeable, and helpful academic tutor. "
        "Explain complex concepts step-by-step using simple analogies, keeping your responses conversational and concise."
    ),
    "Mindful Guide": (
        "You are a calm, gentle, and mindful guide. "
        "Speak slowly, use reassuring and supportive language, and keep responses brief and calming."
    ),
    "Tech Support Specialist": (
        "You are a logical and systematic technical support specialist. "
        "Troubleshoot issues step-by-step, providing clear, concise, and direct instructions."
    )
}

# Ollama models commonly available (users can pull these with: ollama pull <name>)
OLLAMA_MODELS = [
    "llama3.2",
    "llama3.1",
    "llama3",
    "mistral",
    "phi3",
    "phi3:mini",
    "gemma2",
    "qwen2.5",
    "tinyllama",
]

# Gemini models
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.5-flash",
]


def is_ollama_running() -> bool:
    """Returns True if the local Ollama server is reachable."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def list_ollama_models() -> list:
    """Returns a list of model names that are locally pulled in Ollama."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if r.status_code == 200:
            data = r.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


class LLMHandler:
    """
    Manages LLM inference with automatic backend selection.

    Priority order:
      1. Ollama (if running + model available) — fully offline, no key needed
      2. Google Gemini (if GEMINI_API_KEY is set) — online fallback
    """

    def __init__(self):
        self.gemini_client = None
        self.gemini_key_loaded = False
        self._setup_gemini()

    def _setup_gemini(self) -> bool:
        """Attempts to initialise the Gemini client from the stored API key."""
        if not HAS_GENAI:
            return False
        api_key = get_api_key()
        if api_key:
            self.gemini_client = genai.Client(api_key=api_key)
            self.gemini_key_loaded = True
            return True
        self.gemini_client = None
        self.gemini_key_loaded = False
        return False

    def configure_api(self) -> bool:
        """Re-reads the .env file and refreshes the Gemini client. Called after key is saved via GUI."""
        return self._setup_gemini()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_active_backend(self) -> str:
        """Returns a human-readable string describing the currently active backend."""
        if is_ollama_running() and list_ollama_models():
            return "Ollama (offline)"
        if self.gemini_key_loaded:
            return "Google Gemini (online)"
        return "None"

    def generate_response(
        self,
        prompt: str,
        history: list,
        personality: str = "Friendly",
        model_name: str = "auto",
    ) -> str:
        """
        Generates a response to the user prompt.

        The `model_name` parameter is interpreted as follows:
          - "auto"  → try Ollama first, then Gemini
          - A name that appears in OLLAMA_MODELS → force Ollama
          - A name that appears in GEMINI_MODELS → force Gemini

        Args:
            prompt:      Current user message.
            history:     List of prior turns from ConversationManager.get_formatted_history().
            personality: One of the keys in PERSONALITIES.
            model_name:  "auto", an Ollama model name, or a Gemini model name.

        Returns:
            The assistant's reply text, or a descriptive error string.
        """
        system_prompt = PERSONALITIES.get(personality, PERSONALITIES["Friendly"])

        # Determine which backend to use
        force_ollama = model_name in OLLAMA_MODELS
        force_gemini = model_name in GEMINI_MODELS

        if force_ollama:
            return self._call_ollama(prompt, history, system_prompt, model_name)

        if force_gemini:
            return self._call_gemini(prompt, history, system_prompt, model_name)

        # "auto" mode: Ollama → Gemini → error
        if is_ollama_running():
            local_models = list_ollama_models()
            if local_models:
                chosen = local_models[0]  # use first available pulled model
                result = self._call_ollama(prompt, history, system_prompt, chosen)
                if not result.startswith("Error:"):
                    return result

        # Gemini fallback
        self.configure_api()
        if self.gemini_key_loaded:
            return self._call_gemini(prompt, history, system_prompt, "gemini-2.5-flash")

        return (
            "No LLM backend is available.\n\n"
            "Option 1 — Offline (no key needed):\n"
            "  1. Download Ollama from https://ollama.com\n"
            "  2. Run: ollama pull llama3.2\n\n"
            "Option 2 — Online (free):\n"
            "  Enter a Gemini API key in the settings sidebar.\n"
            "  Get one free at https://aistudio.google.com/apikey"
        )

    # ------------------------------------------------------------------
    # Private backend callers
    # ------------------------------------------------------------------

    def _call_ollama(self, prompt: str, history: list, system_prompt: str, model: str) -> str:
        """Sends a request to the local Ollama server using the chat API."""
        if not HAS_OLLAMA_LIB:
            return "Error: The 'ollama' Python package is not installed. Run: pip install ollama"

        if not is_ollama_running():
            return (
                "Error: Ollama is not running.\n"
                "Please download and start Ollama from https://ollama.com, "
                f"then pull a model with: ollama pull {model}"
            )

        # Build the message list in the format Ollama expects
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            role = "user" if turn["role"] == "user" else "assistant"
            messages.append({"role": role, "content": turn["content"]})
        messages.append({"role": "user", "content": prompt})

        try:
            response = _ollama_lib.chat(model=model, messages=messages)
            return response["message"]["content"]
        except Exception as e:
            err = str(e)
            if "model" in err.lower() and "not found" in err.lower():
                return (
                    f"Error: Model '{model}' is not pulled yet.\n"
                    f"Run this in a terminal:  ollama pull {model}"
                )
            return f"Ollama Error: {err}"

    def _call_gemini(self, prompt: str, history: list, system_prompt: str, model: str) -> str:
        """Sends a request to the Google Gemini API."""
        if not HAS_GENAI:
            return "Error: google-genai package not installed. Run: pip install google-genai"

        if not self.gemini_key_loaded or self.gemini_client is None:
            return (
                "Error: Gemini API Key is missing.\n"
                "Enter it in the settings sidebar, or use Ollama instead (no key needed)."
            )

        # Build Gemini content objects
        contents = []
        for h in history:
            role = "user" if h["role"] == "user" else "model"
            contents.append(
                genai_types.Content(role=role, parts=[genai_types.Part(text=h["content"])])
            )
        contents.append(
            genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
        )

        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.75,
            max_output_tokens=512,
        )

        try:
            response = self.gemini_client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response.text
        except Exception as e:
            err = str(e)
            if "API_KEY_INVALID" in err or "403" in err:
                return "Error: The Gemini API Key is invalid. Please verify it in the settings panel."
            return f"Gemini API Error: {err}"
