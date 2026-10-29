# 🎙️ EchoAI — Voice AI Conversational Assistant

A modular, multimodal **desktop voice assistant** built in Python, featuring conversational memory, dual TTS engines, configurable AI personalities, and support for both **Google Gemini** (cloud) and **Ollama** (local/offline) LLM backends.

---

## ✨ Features

- 🎙️ **Speech Recognition** — Hands-free voice input via Google Speech Recognition
- 🔊 **Dual TTS Engines** — Offline (Windows SAPI5 / Microsoft Zira) or Online (Google gTTS)
- 🧠 **Multiple LLM Backends** — Google Gemini (cloud) or Ollama (fully offline, no API key needed)
- 💬 **Conversational Memory** — Retains context across the full session
- 🎭 **Configurable Personalities** — Choose from Helpful Assistant, Sarcastic Robot, Coding Mentor, Academic Tutor, Mindful Guide, or Tech Support Specialist
- 📤 **Export Chat** — Save conversation history as PDF or Word (DOCX)
- 🔁 **Continuous Listening Mode** — Hands-free loop for uninterrupted conversation
- 🎨 **Modern Dark UI** — Built with CustomTkinter

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Windows (for SAPI5 offline TTS)

### Installation

```bash
git clone https://github.com/Bradoh261/echoai-voice-assistant.git
cd echoai-voice-assistant
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the root directory:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

> Get a free Gemini API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
> 
> Or run fully offline with [Ollama](https://ollama.com) — no key needed.

### Run

```bash
python main.py
```

---

## 🧩 Project Structure

```
echoai-voice-assistant/
├── main.py                  # Main GUI application (CustomTkinter)
├── text_to_speech.py        # TTSService — SAPI5 (offline) & gTTS (online)
├── tts_handler.py           # Low-level TTSHandler for thread-safe playback
├── speech_recognition.py    # Microphone input & transcription
├── llm.py                   # LLM personalities & Gemini/Ollama integration
├── llm_handler.py           # Dual-backend LLM handler (auto-selects Ollama → Gemini)
├── conversation.py          # Conversation history & PDF/DOCX export
├── utils.py                 # Environment variable helpers
├── requirements.txt         # Python dependencies
└── assets/                  # Screenshots and resources
```

---

## 🎭 Personalities

| Name | Description |
|---|---|
| Helpful Assistant | Friendly, clear, and concise |
| Sarcastic Robot | Witty and slightly sassy |
| Coding Mentor | Encouraging software engineering guide |
| Academic Tutor | Step-by-step explanations with analogies |
| Mindful Guide | Calm, gentle, and reassuring |
| Tech Support Specialist | Logical, systematic troubleshooter |

---

## 📦 Dependencies

See [`requirements.txt`](requirements.txt) for the full list. Key packages:

- `customtkinter` — Modern Tkinter UI
- `pyttsx3` — Offline TTS (SAPI5)
- `gTTS` — Online TTS (Google)
- `SpeechRecognition` — Microphone input
- `google-generativeai` — Gemini API
- `ollama` — Local LLM support
- `fpdf2` — PDF export
- `python-docx` — DOCX export

---

## 📄 License

MIT License — free to use, modify, and distribute.
