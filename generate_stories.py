#!/usr/bin/env python3
import os
import json
import random
import time
import logging
import requests
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/stories_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ollama API configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# Directory to store generated stories
STORIES_DIR = "./stories"
os.makedirs(STORIES_DIR, exist_ok=True)

# Load configuration
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# List of themes and names from configuration
THEMES = config["story_settings"]["themes"]
VOICES = config["story_settings"]["voice_mapping"]
ALL_VOICES = list({voice for voices in VOICES.values() for voice in voices})

def generate_story_with_ollama():
    """Generates a complete story using Ollama API"""
    theme = random.choice(THEMES)
    character1 = random.choice(list(VOICES.keys()))
    character2 = "Moi"
    voice1 = random.choice(VOICES[character1])
    voice2 = random.choice(ALL_VOICES)  # Random voice for "Moi"

    logger.info(f"Generating story with theme: {theme}")
    logger.info(f"Characters: {character1} and {character2}")

    try:
        system_prompt = (
            "Tu es un générateur d'histoires pour des vidéos courtes.\n"
            "Génère une conversation entre deux personnes qui raconte une histoire.\n"
            "L'histoire doit être courte (20 à 25 messages), captivante et formatée pour les réseaux sociaux.\n"
            "Réponds UNIQUEMENT avec le JSON demandé, sans aucun texte avant ou après."
        )

        user_prompt = f"""
Crée une histoire sur le thème "{theme}"
entre {character1} et {character2}.

Format de sortie :
{{
  "metadata": {{
    "name": "Nom_de_l_histoire",
    "description": "Description accrocheuse de l'histoire",
    "tags": ["#sms", "#histoire", "#{theme}"]
  }},
  "destination": {{
    "name": "{character1}",
    "avatar": "avatar.png"
  }},
  "voice_mapping": {{
    "{character1}": "{voice1}",
    "{character2}": "{voice2}"
  }},
  "audio": "background.mp3",
  "messages": [
    {{
      "sender": "character1 ou character2 qui envoie le message",
      "text": "Premier message de character1 ou character2"
    }},
    {{
      "sender": "character2 ou character1 qui répond ou qui envoie le message",
      "text": "Réponse du premier message de character1 ou character2 ou message de character2 ou character1"
    }}
    // ... (20-25 messages en tout)
  ]
}}

Contraintes :
- L'histoire doit être racontée uniquement par SMS soit un minimum logique.
- Les noms des personnages doivent être utilisés dans chaque message, pas "Moi".
- Le JSON doit être bien formaté et sans explications.
- L'histoire doit avoir une fin forte et mémorable.
- Remplace character1 et character2 par les noms des personnages sans dire "character1" ou "character2".
- Je veux toujours que le character 2 soit "Moi".
- Je ne veux pas que le character 1 appelle le character 2 "Moi".
- Je ne veux pas que les phrases soient trop longues.
- Je veux que les messages soient les personnages qui envoient le message.
- Pas d'espace pour le titre.
"""

        response = requests.post(
            f"{OLLAMA_API_URL}/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": user_prompt,
                "system": system_prompt,
                "stream": False,
                "temperature": 0.8,
                "options": {"num_predict": 2000}
            }
        )

        response.raise_for_status()
        story_json_str = response.json().get("response", "").strip()

        if not story_json_str:
            logger.error("Ollama response is empty")
            return None

        story_json_str = story_json_str.replace("```json", "").replace("```", "").strip()

        match = re.search(r'\{.*\}', story_json_str, re.DOTALL)
        if match:
            story_json_str = match.group(0)
        else:
            logger.error("No JSON block found in Ollama response")
            logger.error(f"Full response: {story_json_str}")
            return None

        try:
            story_data = json.loads(story_json_str)
        except json.JSONDecodeError:
            try:
                fixed_json = re.sub(r',\s*([}\]])', r'\1', story_json_str)
                story_data = json.loads(fixed_json)
                logger.info("JSON fixed and parsed successfully")
            except json.JSONDecodeError as e:
                logger.error(f"Final JSON parse failed: {e}")
                logger.error(story_json_str)
                return None

        required_fields = ["metadata", "messages"]
        for field in required_fields:
            if field not in story_data:
                logger.error(f"Missing required field: {field}")
                return None

        timestamp = int(time.time())
        name = story_data["metadata"].get("name", f"story_{timestamp}")
        story_data["metadata"]["name"] = f"{name}_{timestamp}"

        return story_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

def save_story_to_json(story_data):
    """Save story to file"""
    if not story_data:
        return None
    file_path = os.path.join(STORIES_DIR, f"{story_data['metadata']['name']}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(story_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Story saved: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return None

def generate_story():
    logger.info("Starting new story generation")
    story_data = generate_story_with_ollama()
    if story_data:
        return save_story_to_json(story_data)
    return None

def retry_generate_story(max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Attempt {attempt}/{max_attempts}")
        path = generate_story()
        if path:
            return path
        time.sleep(2)
    logger.error("All attempts failed")
    return None

if __name__ == "__main__":
    try:
        path = retry_generate_story()
        if path:
            print(path)
            exit(0)
        exit(1)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        exit(1)
