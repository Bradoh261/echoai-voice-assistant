import os
import queue
import threading
import time
from tkinter import messagebox, filedialog
import customtkinter as ctk

# Import local modules
import utils
from speech_recognition import SpeechRecognizer, sr
from llm import LLMService, PERSONALITIES
from text_to_speech import TTSService
from conversation import ConversationManager

class VoiceAssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Load environment variables
        utils.load_env_vars()
        
        # Initialize Services
        self.speech_recognizer = SpeechRecognizer()
        self.llm_service = LLMService()
        self.tts_service = TTSService()
        self.conversation_manager = ConversationManager()
        
        # Configure Main Window
        self.title("EchoAI - Voice AI Conversational Assistant")
        self.geometry("1050x720")
        self.minsize(950, 650)
        self.lift()
        self.attributes("-topmost", True)
        self.after(1000, lambda: self.attributes("-topmost", False))
        self.focus_force()
        
        # Set theme and appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Threading state variables
        self.gui_queue = queue.Queue()
        self.is_listening = False
        self.continuous_listening = False
        self.worker_thread = None
        self.speech_interrupted = False
        
        # Animation state
        self.status = "Idle"
        self.pulse_radius = 25
        self.pulse_dir = 1
        
        # Create Layout
        self._create_sidebar()
        self._create_main_panel()
        
        # Start GUI polling loop
        self.after(100, self.poll_queue)
        
        # Start mic animation
        self.animate_microphone()
        
        # Initialize background worker thread
        self.worker_active = True
        self.listen_event = threading.Event()
        self.start_worker_thread()
        
        # Welcome message
        self.gui_queue.put(("assistant_msg", "Hello! I am your EchoAI voice assistant. Select your settings on the left sidebar, then click '🎙️ Start Listening' or type a message below to begin!"))

    def _create_sidebar(self):
        # Sidebar Frame
        self.sidebar = ctk.CTkScrollableFrame(self, width=280, corner_radius=0)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        
        # Title Label
        self.title_lbl = ctk.CTkLabel(
            self.sidebar, 
            text="🎙️ ECHO AI", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_lbl.pack(padx=20, pady=25)
        
        # --- Section: AI SETTINGS ---
        self.ai_section_lbl = ctk.CTkLabel(
            self.sidebar, 
            text="AI SETTINGS", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray"
        )
        self.ai_section_lbl.pack(anchor="w", padx=20, pady=(10, 5))
        
        # LLM Provider Select
        self.provider_lbl = ctk.CTkLabel(self.sidebar, text="LLM Provider:", font=ctk.CTkFont(size=11))
        self.provider_lbl.pack(anchor="w", padx=20, pady=0)
        self.provider_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Gemini (Cloud)", "Ollama (Local)"],
            command=self._on_provider_change
        )
        self.provider_menu.pack(fill="x", padx=20, pady=(0, 10))
        
        # LLM Model Name Select
        self.model_lbl = ctk.CTkLabel(self.sidebar, text="Model:", font=ctk.CTkFont(size=11))
        self.model_lbl.pack(anchor="w", padx=20, pady=0)
        self.model_menu = ctk.CTkOptionMenu(self.sidebar, values=["gemini-2.5-flash"])
        self.model_menu.pack(fill="x", padx=20, pady=(0, 10))
        
        # Personality Select
        self.personality_lbl = ctk.CTkLabel(self.sidebar, text="Personality:", font=ctk.CTkFont(size=11))
        self.personality_lbl.pack(anchor="w", padx=20, pady=0)
        self.personality_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=list(PERSONALITIES.keys()),
            command=self._on_personality_change
        )
        self.personality_menu.pack(fill="x", padx=20, pady=(0, 15))
        
        # --- Section: VOICE SETTINGS ---
        self.voice_section_lbl = ctk.CTkLabel(
            self.sidebar, 
            text="VOICE SETTINGS", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray"
        )
        self.voice_section_lbl.pack(anchor="w", padx=20, pady=(10, 5))
        
        # Voice Engine Select (Offline pyttsx3 vs Online gTTS)
        self.engine_lbl = ctk.CTkLabel(self.sidebar, text="Speech Engine:", font=ctk.CTkFont(size=11))
        self.engine_lbl.pack(anchor="w", padx=20, pady=0)
        self.engine_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Offline (SAPI5)", "Online (gTTS)"],
            command=self._on_engine_change
        )
        self.engine_menu.pack(fill="x", padx=20, pady=(0, 10))
        
        # Offline Voice Selector
        self.voice_lbl = ctk.CTkLabel(self.sidebar, text="Select Voice:", font=ctk.CTkFont(size=11))
        self.voice_lbl.pack(anchor="w", padx=20, pady=0)
        
        # Query pyttsx3 voices
        voices_list = self.tts_service.get_available_voices()
        self.voices_map = {v["name"]: v["id"] for v in voices_list}
        voice_names = list(self.voices_map.keys()) if voices_list else ["Default Voice"]
        self.voice_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=voice_names,
            command=self._on_voice_change
        )
        self.voice_menu.pack(fill="x", padx=20, pady=(0, 10))
        
        # Set default selection in option menu to active voice
        active_voice_name = next((v["name"] for v in voices_list if v["id"] == self.tts_service.current_voice_id), None)
        if active_voice_name:
            self.voice_menu.set(active_voice_name)
        
        # Voice Speed Slider
        self.speed_lbl = ctk.CTkLabel(self.sidebar, text="Speed: 180 wpm", font=ctk.CTkFont(size=11))
        self.speed_lbl.pack(anchor="w", padx=20, pady=0)
        self.speed_slider = ctk.CTkSlider(
            self.sidebar,
            from_=100,
            to=300,
            number_of_steps=20,
            command=self._on_speed_change
        )
        self.speed_slider.set(180)
        self.speed_slider.pack(fill="x", padx=20, pady=(0, 15))
        
        # --- Section: API SECURITY ---
        self.api_section_lbl = ctk.CTkLabel(
            self.sidebar, 
            text="API SECURITY", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray"
        )
        self.api_section_lbl.pack(anchor="w", padx=20, pady=(10, 5))
        
        # API Key Field with visibility toggle
        self.key_lbl = ctk.CTkLabel(self.sidebar, text="Gemini API Key:", font=ctk.CTkFont(size=11))
        self.key_lbl.pack(anchor="w", padx=20, pady=0)
        
        self.key_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.key_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.key_entry = ctk.CTkEntry(
            self.key_frame,
            placeholder_text="Enter API Key...",
            show="*"
        )
        # Prefill if it exists in environment
        existing_key = os.environ.get("GEMINI_API_KEY", "")
        if existing_key:
            self.key_entry.insert(0, existing_key)
            
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.key_toggle_btn = ctk.CTkButton(
            self.key_frame,
            text="👁️",
            width=30,
            command=self._toggle_key_visibility
        )
        self.key_toggle_btn.pack(side="right")
        
        self.save_key_btn = ctk.CTkButton(
            self.sidebar,
            text="💾 Save API Key",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._save_api_key
        )
        self.save_key_btn.pack(fill="x", padx=20, pady=(0, 15))

    def _create_main_panel(self):
        # Main Frame
        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        # Header Frame
        self.header_frame = ctk.CTkFrame(self.main_panel, height=60, corner_radius=10)
        self.header_frame.pack(fill="x", padx=0, pady=(0, 15))
        
        self.header_title = ctk.CTkLabel(
            self.header_frame,
            text="EchoAI Chat Session",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.header_title.pack(side="left", padx=20, pady=15)
        
        # Status indicator badge
        self.status_badge = ctk.CTkLabel(
            self.header_frame,
            text="Status: Idle",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#333333",
            corner_radius=15,
            height=28,
            width=120
        )
        self.status_badge.pack(side="right", padx=20, pady=15)
        
        # Scrollable Chat History Frame
        self.chat_frame = ctk.CTkScrollableFrame(self.main_panel, corner_radius=10)
        self.chat_frame.pack(fill="both", expand=True, padx=0, pady=(0, 15))
        
        # Bot Control and Visualizer Container
        self.control_container = ctk.CTkFrame(self.main_panel, height=80, corner_radius=10)
        self.control_container.pack(fill="x", padx=0, pady=(0, 15))
        
        # Canvas for the mic pulsing visualizer
        self.visualizer_canvas = ctk.CTkCanvas(
            self.control_container,
            width=70,
            height=70,
            bg="#2b2b2b",  # matches frame bg
            highlightthickness=0
        )
        self.visualizer_canvas.pack(side="left", padx=15, pady=5)
        
        # Control Buttons inside container
        self.btns_frame = ctk.CTkFrame(self.control_container, fg_color="transparent")
        self.btns_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        self.listen_btn = ctk.CTkButton(
            self.btns_frame,
            text="🎙️ Start Listening",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144d75",
            command=self._toggle_listening
        )
        self.listen_btn.pack(side="left", padx=5)
        
        self.stop_tts_btn = ctk.CTkButton(
            self.btns_frame,
            text="⏹️ Stop TTS",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#a51f1f",
            hover_color="#751414",
            command=self._stop_tts
        )
        self.stop_tts_btn.pack(side="left", padx=5)
        
        # Continuous listening switch
        self.cont_switch = ctk.CTkSwitch(
            self.btns_frame,
            text="Continuous Loop",
            command=self._on_continuous_toggle
        )
        self.cont_switch.pack(side="left", padx=15)
        
        # Save / Export Options
        self.export_menu = ctk.CTkOptionMenu(
            self.btns_frame,
            values=["Export Chat", "Save as PDF", "Save as Word (DOCX)", "Clear Chat"],
            command=self._handle_export_menu
        )
        self.export_menu.pack(side="right", padx=10)
        
        # Keyboard entry area (fallback / multi-modal entry)
        self.entry_frame = ctk.CTkFrame(self.main_panel, height=50, fg_color="transparent")
        self.entry_frame.pack(fill="x", padx=0, pady=0)
        
        self.msg_entry = ctk.CTkEntry(
            self.entry_frame,
            placeholder_text="Or type your query here and press Enter...",
            height=40
        )
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda event: self._send_manual_message())
        
        self.send_btn = ctk.CTkButton(
            self.entry_frame,
            text="Send",
            width=100,
            height=40,
            command=self._send_manual_message
        )
        self.send_btn.pack(side="right")

    # --- Configuration Event Handlers ---
    def _on_provider_change(self, value):
        if "Gemini" in value:
            self.llm_service.set_provider("gemini")
            self.model_menu.configure(values=["gemini-2.5-flash"])
            self.model_menu.set("gemini-2.5-flash")
            self.key_entry.configure(state="normal")
            self.save_key_btn.configure(state="normal")
        else:
            self.llm_service.set_provider("ollama")
            self.model_menu.configure(values=["llama3", "mistral", "gemma"])
            self.model_menu.set("llama3")
            # Disable API key settings as Ollama is local
            self.key_entry.configure(state="disabled")
            self.save_key_btn.configure(state="disabled")

    def _on_personality_change(self, value):
        self.llm_service.set_personality(value)

    def _on_engine_change(self, value):
        if "Offline" in value:
            self.voice_menu.configure(state="normal")
        else:
            self.voice_menu.configure(state="disabled")

    def _on_voice_change(self, value):
        voice_id = self.voices_map.get(value)
        if voice_id:
            self.tts_service.set_voice(voice_id)

    def _on_speed_change(self, value):
        rate = int(value)
        self.speed_lbl.configure(text=f"Speed: {rate} wpm")
        self.tts_service.set_rate(rate)

    def _toggle_key_visibility(self):
        if self.key_entry.cget("show") == "*":
            self.key_entry.configure(show="")
            self.key_toggle_btn.configure(text="🔒")
        else:
            self.key_entry.configure(show="*")
            self.key_toggle_btn.configure(text="👁️")

    def _save_api_key(self):
        key = self.key_entry.get().strip()
        utils.save_gemini_api_key(key)
        messagebox.showinfo("Success", "Gemini API Key saved to local configuration (.env).")

    def _on_continuous_toggle(self):
        self.continuous_listening = self.cont_switch.get() == 1
        if self.continuous_listening:
            # Trigger listening loop
            self.is_listening = True
            self.listen_btn.configure(text="🎙️ Listening...", fg_color="#27ae60", hover_color="#219653")
            self.listen_event.set()
        else:
            if not self.is_listening:
                self.listen_event.clear()

    # --- Chat Display Helpers ---
    def append_message_bubble(self, sender: str, text: str):
        """Adds a neat message bubble into the scrollable chat frame."""
        # Main bubble frame container
        bubble_container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        bubble_container.pack(fill="x", padx=10, pady=5)
        
        # Decide colors and placement
        if sender == "user":
            anchor = "e"
            bg_color = "#1f6aa5"  # Theme Blue
            text_color = "#ffffff"
            title_text = f"You ({time.strftime('%H:%M:%S')})"
        else:
            anchor = "w"
            bg_color = "#3d3d3d"  # Dark gray
            text_color = "#eeeeee"
            title_text = f"Assistant ({time.strftime('%H:%M:%S')})"
            
        # Sender title
        title_lbl = ctk.CTkLabel(
            bubble_container,
            text=title_text,
            font=ctk.CTkFont(size=10, weight="bold", slant="italic"),
            text_color="gray"
        )
        title_lbl.pack(anchor=anchor, padx=5, pady=0)
        
        # Bubble body
        # Calculate appropriate width wrapping
        bubble = ctk.CTkFrame(bubble_container, fg_color=bg_color, corner_radius=12)
        bubble.pack(anchor=anchor, padx=5, pady=(2, 0))
        
        msg_lbl = ctk.CTkLabel(
            bubble,
            text=text,
            font=ctk.CTkFont(size=13),
            text_color=text_color,
            wraplength=600,
            justify="left"
        )
        msg_lbl.pack(padx=15, pady=10)
        
        # Update idle tasks to compute geometry and scroll down
        self.chat_frame.update_idletasks()
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    # --- Action Handlers ---
    def _toggle_listening(self):
        if self.is_listening:
            # Stop listening
            self.is_listening = False
            self.listen_btn.configure(text="🎙️ Start Listening", fg_color="#1f6aa5", hover_color="#144d75")
            self.listen_event.clear()
            self.update_status("Idle")
        else:
            # Start listening
            self.is_listening = True
            self.listen_btn.configure(text="🎙️ Listening...", fg_color="#27ae60", hover_color="#219653")
            self.listen_event.set()

    def _stop_tts(self):
        self.speech_interrupted = True
        self.tts_service.stop()
        self.update_status("Idle")

    def _send_manual_message(self):
        text = self.msg_entry.get().strip()
        if not text:
            return
        
        # Stop speech playback if typing
        self._stop_tts()
        
        # Clear field
        self.msg_entry.delete(0, "end")
        
        # Put user message into GUI queue
        self.gui_queue.put(("user_msg", text))
        
        # Process message in a non-blocking thread to allow UI responsiveness
        threading.Thread(
            target=self._process_text_query, 
            args=(text,), 
            daemon=True
        ).start()

    def _process_text_query(self, text: str):
        self.gui_queue.put(("status", "Processing..."))
        
        # Check exit command
        if text.lower().strip() in ["exit", "quit", "goodbye"]:
            farewell = "Goodbye. Have a nice day!"
            self.gui_queue.put(("assistant_msg", farewell))
            self.gui_queue.put(("status", "Speaking..."))
            self.tts_service.speak(farewell, mode="offline" if self.engine_menu.get().startswith("Offline") else "online")
            self.gui_queue.put(("status", "Idle"))
            self.after(1000, self.quit)
            return

        try:
            # Fetch response
            api_key = self.key_entry.get().strip()
            history = self.conversation_manager.get_formatted_history()
            
            response = self.llm_service.generate_response(history, text, api_key)
            
            # Post response
            self.gui_queue.put(("assistant_msg", response))
            
            # Speak response
            self.gui_queue.put(("status", "Speaking..."))
            self.speech_interrupted = False
            self.tts_service.speak(response, mode="offline" if self.engine_menu.get().startswith("Offline") else "online")
            
        except Exception as e:
            self.gui_queue.put(("error", f"AI Error: {str(e)}"))
        finally:
            self.gui_queue.put(("status", "Idle"))

    def _handle_export_menu(self, value):
        # Reset menu choice display back to "Export Chat"
        self.export_menu.set("Export Chat")
        
        if value == "Save as PDF":
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf")],
                title="Export History to PDF"
            )
            if filepath:
                try:
                    self.conversation_manager.export_to_pdf(filepath)
                    messagebox.showinfo("Success", f"History saved to PDF successfully at:\n{filepath}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save PDF: {e}")
                    
        elif value == "Save as Word (DOCX)":
            filepath = filedialog.asksaveasfilename(
                defaultextension=".docx",
                filetypes=[("Word Documents", "*.docx")],
                title="Export History to DOCX"
            )
            if filepath:
                try:
                    self.conversation_manager.export_to_docx(filepath)
                    messagebox.showinfo("Success", f"History saved to Word successfully at:\n{filepath}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save DOCX: {e}")
                    
        elif value == "Clear Chat":
            if messagebox.askyesno("Clear Chat", "Are you sure you want to clear the entire chat history?"):
                self.conversation_manager.clear()
                # Clear GUI elements
                for widget in self.chat_frame.winfo_children():
                    widget.destroy()
                self.append_message_bubble("assistant", "Chat history has been cleared.")

    # --- Background Worker Thread ---
    def start_worker_thread(self):
        self.worker_thread = threading.Thread(target=self.listening_worker_loop, daemon=True)
        self.worker_thread.start()

    def listening_worker_loop(self):
        """Continuous background loop for mic capturing, transcribing, LLM, and TTS."""
        microphone = None
        
        # Check and initialize default microphone
        try:
            microphone = sr.Microphone()
            # Perform initial noise calibration
            self.gui_queue.put(("status", "Calibrating mic..."))
            with microphone as source:
                self.speech_recognizer.calibrate(source, duration=1.0)
            self.gui_queue.put(("status", "Idle"))
        except Exception as e:
            self.gui_queue.put(("error", f"Microphone Initialization Error: {e}\nYou can still interact by typing messages below."))
        
        while self.worker_active:
            # Wait until listening event is set (triggered by 'Start Listening' or continuous loop)
            self.listen_event.wait()
            
            if not self.worker_active:
                break
                
            if microphone is None:
                # No microphone, sleep and try again
                self.listen_event.clear()
                self.gui_queue.put(("status", "Idle"))
                continue
                
            self.gui_queue.put(("status", "Listening..."))
            
            try:
                with microphone as source:
                    # Captures audio
                    text = self.speech_recognizer.listen_and_recognize(source, timeout=4, phrase_time_limit=10)
                
                # Check interruption or exit of listening
                if not self.is_listening:
                    continue
                    
                # User transcribing complete
                self.gui_queue.put(("user_msg", text))
                self.gui_queue.put(("status", "Processing..."))
                
                # Handle Exit commands
                if text.lower().strip() in ["exit", "quit", "goodbye"]:
                    farewell = "Goodbye. Have a nice day!"
                    self.gui_queue.put(("assistant_msg", farewell))
                    self.gui_queue.put(("status", "Speaking..."))
                    self.tts_service.speak(farewell, mode="offline" if self.engine_menu.get().startswith("Offline") else "online")
                    self.gui_queue.put(("status", "Idle"))
                    
                    # Stop listening
                    self.is_listening = False
                    self.listen_event.clear()
                    # Trigger application exit
                    self.after(1000, self.quit)
                    continue
                
                # AI generation
                api_key = self.key_entry.get().strip()
                history = self.conversation_manager.get_formatted_history()
                
                response = self.llm_service.generate_response(history, text, api_key)
                
                # AI display response
                self.gui_queue.put(("assistant_msg", response))
                self.gui_queue.put(("status", "Speaking..."))
                
                # TTS Speech Playback
                self.speech_interrupted = False
                self.tts_service.speak(response, mode="offline" if self.engine_menu.get().startswith("Offline") else "online")
                
            except sr.WaitTimeoutError:
                # Quiet room, just loop again if continuous
                pass
            except sr.UnknownValueError:
                # Noise heard but not recognized
                pass
            except sr.RequestError as e:
                self.gui_queue.put(("error", f"Speech Recognition API Error: {e}"))
                self.is_listening = False
                self.listen_event.clear()
            except Exception as e:
                self.gui_queue.put(("error", f"Processing Error: {e}"))
                self.is_listening = False
                self.listen_event.clear()
            finally:
                # If continuous loop is off, stop listening
                if not self.continuous_listening:
                    self.is_listening = False
                    self.listen_event.clear()
                    self.gui_queue.put(("status", "Idle"))
                    # Update button text back to original
                    self.after(0, lambda: self.listen_btn.configure(text="🎙️ Start Listening", fg_color="#1f6aa5", hover_color="#144d75"))
                else:
                    self.gui_queue.put(("status", "Listening..."))

    # --- Thread Safe GUI Updating ---
    def poll_queue(self):
        """Reads status/chat messages from background worker and updates UI."""
        try:
            while True:
                msg_type, data = self.gui_queue.get_nowait()
                if msg_type == "status":
                    self.update_status(data)
                elif msg_type == "user_msg":
                    self.append_message_bubble("user", data)
                    self.conversation_manager.add_message("user", data)
                elif msg_type == "assistant_msg":
                    self.append_message_bubble("assistant", data)
                    self.conversation_manager.add_message("assistant", data)
                elif msg_type == "error":
                    self.update_status("Error")
                    messagebox.showerror("System Error", data)
                self.gui_queue.task_done()
        except queue.Empty:
            pass
        self.after(100, self.poll_queue)

    def update_status(self, status: str):
        self.status = status
        self.status_badge.configure(text=f"Status: {status}")
        
        # Color badge depending on status
        if status == "Listening...":
            self.status_badge.configure(fg_color="#27ae60")  # Green
        elif status == "Processing...":
            self.status_badge.configure(fg_color="#d35400")  # Orange
        elif status == "Speaking...":
            self.status_badge.configure(fg_color="#2980b9")  # Blue
        elif status == "Calibrating mic...":
            self.status_badge.configure(fg_color="#8e44ad")  # Purple
        elif status == "Error":
            self.status_badge.configure(fg_color="#c0392b")  # Red
        else:
            self.status_badge.configure(fg_color="#333333")  # Gray (Idle)

    # --- Pulsing Microphone Animation ---
    def draw_mic_circle(self, radius, color):
        self.visualizer_canvas.delete("all")
        
        # Coordinates (canvas is 70x70)
        cx, cy = 35, 35
        
        # Draw soft outer shadow/glow if active
        if self.status in ["Listening...", "Speaking...", "Processing..."]:
            self.visualizer_canvas.create_oval(
                cx - radius - 5, cy - radius - 5,
                cx + radius + 5, cy + radius + 5,
                fill="", outline=color, width=2, state="normal"
            )
            
        # Draw main circle
        self.visualizer_canvas.create_oval(
            cx - radius, cy - radius,
            cx + radius, cy + radius,
            fill=color, outline=""
        )
        
        # Draw mic symbol icon text inside circle
        mic_symbol = "🎙️"
        if self.status == "Speaking...":
            mic_symbol = "🔊"
        elif self.status == "Processing...":
            mic_symbol = "🧠"
        elif self.status == "Error":
            mic_symbol = "⚠️"
            
        self.visualizer_canvas.create_text(
            cx, cy,
            text=mic_symbol,
            font=("Arial", 16)
        )

    def animate_microphone(self):
        """Microphone animations based on program status."""
        if self.status == "Listening...":
            # Pulse logic
            self.pulse_radius += self.pulse_dir * 1.5
            if self.pulse_radius > 32:
                self.pulse_radius = 32
                self.pulse_dir = -1
            elif self.pulse_radius < 20:
                self.pulse_radius = 20
                self.pulse_dir = 1
            self.draw_mic_circle(self.pulse_radius, "#27ae60")  # Pulsing Green
            
        elif self.status == "Calibrating mic...":
            # Purple rotation/pulse
            self.pulse_radius += self.pulse_dir * 1
            if self.pulse_radius > 28 or self.pulse_radius < 22:
                self.pulse_dir *= -1
            self.draw_mic_circle(self.pulse_radius, "#8e44ad")
            
        elif self.status == "Processing...":
            # Solid glowing orange
            self.draw_mic_circle(25, "#d35400")
            
        elif self.status == "Speaking...":
            # Pulse logic for speech
            self.pulse_radius += self.pulse_dir * 1
            if self.pulse_radius > 28 or self.pulse_radius < 22:
                self.pulse_dir *= -1
            self.draw_mic_circle(self.pulse_radius, "#2980b9")  # Blue
            
        else: # Idle
            self.draw_mic_circle(24, "#1f6aa5")  # Default Theme Blue
            
        self.after(80, self.animate_microphone)

    def destroy(self):
        """Ensures that background thread is closed when app exits."""
        self.worker_active = False
        self.listen_event.set()  # unlock thread
        self.tts_service.stop()
        super().destroy()

if __name__ == "__main__":
    print("Launching EchoAI GUI...")
    app = VoiceAssistantApp()
    print("EchoAI GUI initialized")
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.destroy()
