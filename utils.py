import os
from dotenv import load_dotenv, find_dotenv

def get_env_path():
    """Returns the absolute path to the local .env file."""
    # Find local .env in the current file's directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, ".env")

def load_env_vars():
    """Loads environment variables from the local .env file."""
    env_path = get_env_path()
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
    else:
        # Create it if it doesn't exist
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("GEMINI_API_KEY=\n")
        load_dotenv(env_path)

def save_gemini_api_key(key: str):
    """Updates the GEMINI_API_KEY in the local .env file."""
    env_path = get_env_path()
    lines = []
    key_exists = False
    
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            if line.strip().startswith("GEMINI_API_KEY="):
                lines[i] = f"GEMINI_API_KEY={key}\n"
                key_exists = True
                break
                
    if not key_exists:
        lines.append(f"\nGEMINI_API_KEY={key}\n")
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    # Reload the environment variables
    load_dotenv(env_path, override=True)
