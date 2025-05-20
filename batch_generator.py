#!/usr/bin/env python3
import os
import json
import time
import logging
import subprocess
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration des logs
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/batch_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Chargement de la configuration
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

def generate_story():
    """Génère une nouvelle histoire JSON et retourne le chemin du fichier"""
    logger.info("Génération d'une nouvelle histoire...")
    try:
        result = subprocess.run(
            ["python", "generate_stories.py"],
            check=True,
            capture_output=True,
            text=True
        )
        json_file = result.stdout.strip()
        logger.info(f"Histoire générée: {json_file}")
        return json_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de la génération de l'histoire: {e}")
        logger.error(f"Sortie d'erreur: {e.stderr}")
        return None

def create_video(json_file):
    """Crée une vidéo à partir d'un fichier JSON et retourne le chemin de la vidéo"""
    if not json_file or not os.path.exists(json_file):
        logger.error(f"Fichier JSON introuvable: {json_file}")
        return None

    logger.info(f"Création de la vidéo pour {json_file}...")
    try:
        subprocess.run(
            ["node", "capture.js", json_file],
            check=True
        )

        # Déterminer le nom de la vidéo générée
        with open(json_file, 'r') as f:
            story_data = json.load(f)

        story_name = story_data["metadata"]["name"]
        video_file = os.path.join("videos", f"{story_name}.mp4")

        if os.path.exists(video_file):
            logger.info(f"Vidéo créée: {video_file}")
            return video_file
        else:
            # Vérifier si la vidéo a été créée au format webm
            webm_file = os.path.join("videos", f"{story_name}.webm")
            if os.path.exists(webm_file):
                logger.info(f"Vidéo créée au format webm: {webm_file}")

                # Convertir webm en mp4 si nécessaire
                try:
                    mp4_file = os.path.join("videos", f"{story_name}.mp4")
                    logger.info(f"Conversion de webm en mp4: {webm_file} -> {mp4_file}")

                    # Utiliser ffmpeg pour la conversion
                    subprocess.run([
                        "ffmpeg", "-i", webm_file, "-c:v", "libx264", "-c:a", "aac",
                        "-strict", "experimental", mp4_file
                    ], check=True)

                    logger.info(f"Conversion réussie: {mp4_file}")
                    return mp4_file
                except subprocess.CalledProcessError as e:
                    logger.error(f"Erreur lors de la conversion webm en mp4: {e}")
                    return webm_file  # Retourner le fichier webm si la conversion échoue
            else:
                logger.error(f"Vidéo non trouvée: {video_file} ou {webm_file}")
                return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de la création de la vidéo: {e}")
        return None

def schedule_videos(video_files):
    """Programme la publication des vidéos, une par jour à 18h00"""
    if not video_files:
        logger.error("Aucune vidéo à programmer")
        return False

    # Charger la programmation existante ou créer une nouvelle
    schedule_file = "schedule.json"
    if os.path.exists(schedule_file):
        with open(schedule_file, 'r') as f:
            schedule_data = json.load(f)
    else:
        schedule_data = {"videos": []}

    # Déterminer la date de début (soit aujourd'hui, soit le lendemain de la dernière vidéo programmée)
    if schedule_data["videos"]:
        last_date = datetime.strptime(schedule_data["videos"][-1]["date"], "%Y-%m-%d")
        start_date = last_date + timedelta(days=1)
    else:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Ajouter les nouvelles vidéos à la programmation
    for i, video_file in enumerate(video_files):
        publish_date = start_date + timedelta(days=i)

        # Extraire le nom de l'histoire à partir du chemin de la vidéo
        story_name = os.path.basename(video_file).split('.')[0]

        # Charger les métadonnées de l'histoire
        json_file = os.path.join("stories", f"{story_name}.json")
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                story_data = json.load(f)

            # Extraire la description et les tags
            description = story_data["metadata"].get("description", "Histoire mystérieuse générée automatiquement")
            tags = story_data["metadata"].get("tags", ["#shorts", "#mystère", "#histoire"])

            # Construire la description complète avec les tags
            full_description = f"{description}\n\n{' '.join(tags)}"

            # Construire le titre
            title = f"{story_name.replace('_', ' ')} #Shorts"
        else:
            # Valeurs par défaut si le fichier JSON n'est pas trouvé
            title = f"{story_name.replace('_', ' ')} #Shorts"
            full_description = "Histoire mystérieuse générée automatiquement #Shorts"
            tags = "histoire,mystère,shorts"

        schedule_data["videos"].append({
            "video_file": video_file,
            "date": publish_date.strftime("%Y-%m-%d"),
            "time": "18:00",
            "title": title,
            "description": full_description,
            "keywords": ",".join(tags) if isinstance(tags, list) else tags,
            "published": False
        })

    # Enregistrer la programmation mise à jour
    with open(schedule_file, 'w') as f:
        json.dump(schedule_data, f, indent=2)

    logger.info(f"{len(video_files)} vidéos programmées avec succès")
    return True

def generate_batch(count=10):
    """Génère un lot de vidéos"""
    logger.info(f"Démarrage de la génération de {count} vidéos")

    video_files = []

    for i in range(count):
        logger.info(f"Génération de la vidéo {i+1}/{count}")

        # Générer une histoire
        json_file = generate_story()
        if not json_file:
            logger.error(f"Échec de la génération d'histoire {i+1}/{count}")
            continue

        # Créer une vidéo
        video_file = create_video(json_file)
        if not video_file:
            logger.error(f"Échec de la création de vidéo {i+1}/{count}")
            continue

        video_files.append(video_file)

        # Petite pause pour éviter de surcharger le système
        time.sleep(2)

    # Programmer les vidéos
    if video_files:
        schedule_videos(video_files)
        logger.info(f"Lot de {len(video_files)} vidéos généré et programmé avec succès")
    else:
        logger.error("Aucune vidéo n'a pu être générée")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Génère un lot de vidéos et les programme")
    parser.add_argument("--count", type=int, default=1, help="Nombre de vidéos à générer")

    args = parser.parse_args()

    generate_batch(args.count)