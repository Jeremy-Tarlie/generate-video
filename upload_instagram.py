#!/usr/bin/env python3
import os
import argparse
import logging
import time
from instagrapi import Client
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/instagram_{time.strftime('%Y%m%d')}.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def upload_to_instagram(video_file, caption):
    """Télécharge une vidéo sur Instagram Reels"""
    # Récupérer les identifiants depuis les variables d'environnement
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")

    if not username or not password:
        logger.error("Identifiants Instagram manquants dans le fichier .env")
        return False

    # Vérifier que le fichier existe
    if not os.path.exists(video_file):
        logger.error(f"Le fichier vidéo n'existe pas: {video_file}")
        return False

    try:
        logger.info(f"Tentative de connexion à Instagram avec le compte {username}")

        # Créer le dossier de session s'il n'existe pas
        os.makedirs("sessions", exist_ok=True)
        session_file = f"sessions/{username}.json"

        # Initialiser le client Instagram
        client = Client()

        # Essayer de charger une session existante
        if os.path.exists(session_file):
            logger.info("Chargement de la session existante")
            try:
                client.load_settings(session_file)
                client.get_timeline_feed()  # Vérifier si la session est valide
                logger.info("Session chargée avec succès")
            except Exception as e:
                logger.warning(f"Impossible d'utiliser la session existante: {e}")
                client = Client()  # Réinitialiser le client

        # Se connecter si nécessaire
        if not client.user_id:
            logger.info("Connexion avec identifiants")
            client.login(username, password)
            # Sauvegarder la session pour une utilisation future
            client.dump_settings(session_file)
            logger.info("Connexion réussie et session sauvegardée")

        # Préparer la vidéo pour le téléchargement
        logger.info(f"Préparation du téléchargement de la vidéo: {video_file}")

        # Télécharger la vidéo en tant que Reels
        logger.info("Téléchargement de la vidéo en tant que Reels")
        media = client.clip_upload(
            video_file,
            caption=caption,
            thumbnail=None,  # Utiliser une miniature générée automatiquement
            mentions=[],
            locations=[],
            configure_timeout=120  # Augmenter le timeout pour les vidéos plus longues
        )

        logger.info(f"Vidéo téléchargée sur Instagram Reels avec succès! ID: {media.id}")
        logger.info(f"URL de la publication: https://www.instagram.com/p/{media.code}/")
        return True

    except Exception as e:
        logger.error(f"Erreur lors du téléchargement sur Instagram: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Créer le dossier de logs s'il n'existe pas
    os.makedirs("logs", exist_ok=True)

    parser = argparse.ArgumentParser(description="Télécharge une vidéo sur Instagram Reels")
    parser.add_argument("--file", required=True, help="Fichier vidéo à télécharger")
    parser.add_argument("--caption", required=True, help="Légende de la vidéo")

    args = parser.parse_args()

    success = upload_to_instagram(args.file, args.caption)

    if not success:
        logger.error("Échec du téléchargement sur Instagram")
        exit(1)
    else:
        logger.info("Téléchargement sur Instagram terminé avec succès")


# python upload_instagram.py --file "videos/ma_video.mp4" --caption "Ma super vidéo #Reels"