import json
import os
import asyncio
from edge_tts import Communicate
from moviepy.audio.io.AudioFileClip import AudioFileClip
import unicodedata

def remove_emojis(text):
    """Supprime les emojis et caractères spéciaux du texte"""
    return ''.join(
        c for c in text
        if not unicodedata.category(c).startswith('So')  # Symbol, Other
        and not unicodedata.category(c).startswith('Cs')  # Other, Surrogate
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

        # Image = son fixe
        if "image" in msg:
            audio_path = "iphone.mp3"  # doit exister et être un vrai .mp3 valide
            try:
                audio_clip = AudioFileClip(audio_path)
                duration = audio_clip.duration
                audio_clip.close()
                DURATION_TOTAL += duration

                result.append({
                    "sender": sender,
                    "image": msg["image"],
                    "audio": audio_path,
                    "duration": duration
                })
            except Exception as e:
                print(f"⚠️ Erreur lecture audio image ({audio_path}) : {e}")
                continue
        else:
            text = remove_emojis(msg["text"])
            voice = voice_mapping.get(sender, "fr-FR-DeniseNeural")
            audio_path = os.path.join(output_json_dir, f"audio_{idx}.mp3")

            try:
                communicate = Communicate(text, voice)
                await communicate.save(audio_path)
            except Exception as e:
                print(f"❌ Erreur génération audio pour {sender} : {e}")
                continue

            # Vérification du fichier généré
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                print(f"❌ Fichier audio non généré ou vide : {audio_path}")
                continue

            # Lire la durée de l'audio
            try:
                audio_clip = AudioFileClip(audio_path)
                duration = audio_clip.duration
                audio_clip.close()
            except Exception as e:
                print(f"⚠️ Erreur lecture audio {audio_path} : {e}")
                continue

            DURATION_TOTAL += duration
            result.append({
                "sender": sender,
                "text": text,
                "audio": audio_path,
                "duration": duration
            })

    # Écriture du fichier final
    with open(os.path.join(output_json_dir, "messages_with_audio.json"), "w", encoding="utf-8") as f:
        json.dump({
            "duration_total": DURATION_TOTAL + 3,  # petite marge
            "messages": result
        }, f, ensure_ascii=False, indent=2)

    print("✅ Fichier messages_with_audio.json généré avec succès.")

if __name__ == "__main__":
    asyncio.run(generate_audio_and_json("messages.json", "audios"))
