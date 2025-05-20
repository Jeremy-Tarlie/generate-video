#!/usr/bin/env python3
import os
import json
import time
import logging
import subprocess
from datetime import datetime, timedelta
import schedule
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration des logs
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/scheduler_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_schedule():
    """Charge la programmation des vidéos"""
    schedule_file = "schedule.json"
    if os.path.exists(schedule_file):
        with open(schedule_file, 'r') as f:
            return json.load(f)
    else:
        return {"videos": []}

def save_schedule(schedule_data):
    """Enregistre la programmation des vidéos"""
    with open("schedule.json", 'w') as f:
        json.dump(schedule_data, f, indent=2)

def publish_video(video_data):
    """Publie une vidéo sur toutes les plateformes"""
    video_file = video_data["video_file"]

    if not os.path.exists(video_file):
        logger.error(f"Fichier vidéo introuvable: {video_file}")
        return False

    success = True

    # Publication sur YouTube
    logger.info(f"Publication sur YouTube: {video_file}")
    try:
        subprocess.run([
            "python", "upload_youtube.py",
            "--file", video_file,
            "--title", video_data["title"],
            "--description", video_data["description"],
            "--keywords", video_data["keywords"],
            "--category", "22",
            "--privacyStatus", "public"
        ], check=True)
        logger.info("Publication sur YouTube réussie")
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de la publication sur YouTube: {e}")
        success = False

    # Publication sur Instagram
    logger.info(f"Publication sur Instagram: {video_file}")
    try:
        subprocess.run([
            "python", "upload_instagram.py",
            "--file", video_file,
            "--caption", f"{video_data['title']}\n\n{video_data['description']}"
        ], check=True)
        logger.info("Publication sur Instagram réussie")
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de la publication sur Instagram: {e}")
        success = False

    # Publication sur TikTok
    logger.info(f"Publication sur TikTok: {video_file}")
    try:
        subprocess.run([
            "python", "upload_tiktok.py",
            "--file", video_file,
            "--caption", f"{video_data['title']}\n\n{video_data['description']}"
        ], check=True)
        logger.info("Publication sur TikTok réussie")
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de la publication sur TikTok: {e}")
        success = False

    return success

def check_and_publish():
    """Vérifie s'il y a des vidéos à publier aujourd'hui"""
    logger.info("Vérification des vidéos à publier...")

    # Charger la programmation
    schedule_data = load_schedule()

    # Date d'aujourd'hui
    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M")

    # Vérifier s'il y a des vidéos à publier
    videos_to_publish = []
    for i, video in enumerate(schedule_data["videos"]):
        if not video["published"] and video["date"] == today and video["time"] <= current_time:
            videos_to_publish.append((i, video))

    # Publier les vidéos
    for i, video in videos_to_publish:
        logger.info(f"Publication de la vidéo programmée: {video['video_file']}")
        success = publish_video(video)

        if success:
            # Marquer la vidéo comme publiée
            schedule_data["videos"][i]["published"] = True
            save_schedule(schedule_data)
            logger.info(f"Vidéo {video['video_file']} publiée avec succès")
        else:
            logger.error(f"Échec de la publication de la vidéo {video['video_file']}")

def check_and_generate_batch():
    """Vérifie s'il faut générer un nouveau lot de vidéos"""
    logger.info("Vérification du besoin de générer un nouveau lot...")

    # Charger la programmation
    schedule_data = load_schedule()

    # Compter les vidéos non publiées
    unpublished_videos = [v for v in schedule_data["videos"] if not v["published"]]

    # Si moins de 3 vidéos non publiées, générer un nouveau lot
    if len(unpublished_videos) < 3:
        logger.info(f"Seulement {len(unpublished_videos)} vidéos non publiées. Génération d'un nouveau lot.")
        try:
            subprocess.run(["python", "batch_generator.py", "--count", "10"], check=True)
            logger.info("Nouveau lot généré avec succès")
        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors de la génération du nouveau lot: {e}")
    else:
        logger.info(f"Encore {len(unpublished_videos)} vidéos non publiées. Pas besoin de générer un nouveau lot.")

def main():
    """Fonction principale"""
    logger.info("Démarrage du planificateur")

    # Vérifier toutes les heures s'il y a des vidéos à publier
    schedule.every().hour.do(check_and_publish)

    # Vérifier tous les jours à minuit s'il faut générer un nouveau lot
    schedule.every().day.at("00:00").do(check_and_generate_batch)

    # Vérifier immédiatement au démarrage
    check_and_publish()
    check_and_generate_batch()

    logger.info("Planificateur démarré. Appuyez sur Ctrl+C pour arrêter.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Arrêt du planificateur.")

if __name__ == "__main__":
    main()