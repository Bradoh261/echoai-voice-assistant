import os
import google.generativeai as genai
import ollama

# AI Personalities definitions
PERSONALITIES = {
    "Helpful Assistant": "You are a helpful, friendly, and intelligent voice assistant. Keep your responses concise, clear, and direct, as they will be read aloud to the user.",
    "Sarcastic Robot": "You are a highly intelligent but sarcastic and slightly cynical robot assistant. Keep your answers brief, witty, and a bit sassy, suitable for speech.",
    "Coding Mentor": "You are an experienced and encouraging software engineer mentor. Explain concepts simply, avoid long code dumps (unless specifically asked), and keep responses conversational.",
    "Academic Tutor": "You are a warm, knowledgeable, and helpful academic tutor. Explain complex concepts step-by-step using simple analogies, keeping your responses conversational and concise.",
    "Mindful Guide": "You are a calm, gentle, and mindful guide. Speak slowly, use reassuring and supportive language, and keep responses brief and calming.",
    "Tech Support Specialist": "You are a logical and systematic technical support specialist. Troubleshoot issues step-by-step, providing clear, concise, and direct instructions."
}

class LLMService:
    def __init__(self, provider="gemini", model_name="gemini-2.5-flash", personality="Helpful Assistant"):
        self.provider = provider
        self.model_name = model_name
        self.personality = personality
        
    def set_provider(self, provider: str):
        self.provider = provider
        if provider == "gemini":
            self.model_name = "gemini-2.5-flash"
        elif provider == "ollama":
            self.model_name = "llama3"  # default Ollama model

    def set_model_name(self, model_name: str):
        self.model_name = model_name

    def set_personality(self, personality: str):
        self.personality = personality

    def _get_system_instruction(self) -> str:
        return PERSONALITIES.get(self.personality, PERSONALITIES["Helpful Assistant"])

    def generate_response(self, history: list, user_message: str, api_key: str = None) -> str:
        """
        Sends the user message and conversation history to the selected LLM.
        
        Args:
            history: List of dicts like [{'role': 'user'|'assistant', 'content': str}]
            user_message: The latest text from the user.
            api_key: Optional API key for Gemini. If not provided, it will check the env.
            
        Returns:
            str: The model's response.
        """
        system_instruction = self._get_system_instruction()
        
        if self.provider == "gemini":
            # Configure Gemini key
            key = api_key or os.environ.get("GEMINI_API_KEY")
            if not key:
                raise ValueError("Gemini API Key is not set. Please set it in the sidebar or env file.")
            
            genai.configure(api_key=key)
            
            # Initialize model with system instruction
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
            
            # Format history for Gemini
            contents = []
            for msg in history:
                role = "model" if msg['role'] == "assistant" else "user"
                contents.append({"role": role, "parts": [msg['content']]})
            
            # Add latest user message
            contents.append({"role": "user", "parts": [user_message]})
            
            # Generate
            response = model.generate_content(contents)
            return response.text
            
        elif self.provider == "ollama":
            # Format messages for Ollama
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
                
            for msg in history:
                messages.append({"role": msg['role'], "content": msg['content']})
                
            messages.append({"role": "user", "content": user_message})
            
            # Generate using local Ollama
            response = ollama.chat(model=self.model_name, messages=messages)
            return response['message']['content']
            
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
