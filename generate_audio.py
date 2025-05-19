import json
import os
import asyncio
from edge_tts import Communicate
from moviepy.audio.io.AudioFileClip import AudioFileClip
import re
import unicodedata

def remove_emojis(text):
    """Supprime les emojis et caractères spéciaux du texte"""
    return ''.join(
        c for c in text
        if not unicodedata.category(c).startswith('So')
        and not unicodedata.category(c).startswith('Cs')
    )

async def generate_audio_and_json(messages_file, output_json_dir):
    global DURATION_TOTAL
    DURATION_TOTAL = 0
    with open(messages_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        messages = data["messages"]
        voice_mapping = data["voice_mapping"]

    os.makedirs(output_json_dir, exist_ok=True)
    result = []
    for idx, msg in enumerate(messages):
        sender = msg["sender"]
        if "image" in msg:
            audio_path = "iphone.mp3"  # doit être présent dans le dossier de travail
            # Récupérer la durée du son iPhone
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            DURATION_TOTAL += duration
            audio_clip.close()
            result.append({
                "sender": sender,
                "image": msg["image"],
                "audio": audio_path,
                "duration": duration
            })
        else:
            text = remove_emojis(msg["text"])
            voice = voice_mapping.get(sender, "fr-FR-DeniseNeural")
            audio_path = os.path.join(output_json_dir, f"audio_{idx}.mp3")
            communicate = Communicate(text, voice)
            await communicate.save(audio_path)
            # Get duration
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            DURATION_TOTAL += duration
            audio_clip.close()
            result.append({
                "sender": sender,
                "text": text,
                "audio": audio_path,
                "duration": duration
            })

    with open(os.path.join(output_json_dir, "messages_with_audio.json"), "w", encoding="utf-8") as f:
        json.dump({
            "duration_total": DURATION_TOTAL+3,
            "messages": result
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(generate_audio_and_json("messages.json", "audios"))

