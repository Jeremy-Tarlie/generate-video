#!/usr/bin/env python3
import os
import argparse
import logging
import time
import random
import http.client
import httplib2
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration des logs
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/youtube_{time.strftime('%Y%m%d')}.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Si tu modifies ces scopes, supprime le fichier token.json
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

def get_authenticated_service():
    """Obtient un service YouTube authentifié."""
    client_secrets_file = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE")

    if not client_secrets_file or not os.path.exists(client_secrets_file):
        logger.error(f"Fichier de secrets client introuvable: {client_secrets_file}")
        logger.error("Assurez-vous que YOUTUBE_CLIENT_SECRETS_FILE est correctement défini dans le fichier .env")
        return None

    creds = None
    token_file = "token.json"

    # Charger les identifiants existants s'ils existent
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_info(
                json.load(open(token_file)), SCOPES)
        except Exception as e:
            logger.warning(f"Erreur lors du chargement du token: {e}")

    # Si les identifiants n'existent pas ou ne sont pas valides, en obtenir de nouveaux
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.warning(f"Impossible de rafraîchir le token: {e}")
                creds = None

        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"Erreur lors de l'authentification: {e}")
                return None

            # Sauvegarder les identifiants pour la prochaine exécution
            with open(token_file, 'w') as token:
                token.write(creds.to_json())

    try:
        # Construire le service YouTube
        return build("youtube", "v3", credentials=creds)
    except Exception as e:
        logger.error(f"Erreur lors de la construction du service YouTube: {e}")
        return None

def initialize_upload(youtube, file, title, description, category, keywords, privacy_status):
    """Initialise le téléchargement d'une vidéo sur YouTube."""
    if not os.path.exists(file):
        logger.error(f"Le fichier vidéo n'existe pas: {file}")
        return None

    # Vérifier que le fichier est une vidéo valide
    if not file.lower().endswith(('.mp4', '.mov', '.avi')):
        logger.error(f"Le fichier n'est pas une vidéo valide: {file}")
        return None

    tags = None
    if keywords:
        tags = keywords.split(",")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }

    # Appeler l'API pour télécharger la vidéo
    try:
        logger.info(f"Début du téléchargement de la vidéo: {file}")

        # Créer un objet MediaFileUpload pour le fichier vidéo
        media = MediaFileUpload(
            file,
            mimetype="video/*",
            resumable=True
        )

        # Appeler l'API pour initialiser le téléchargement
        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )

        video_id = resumable_upload(insert_request)
        return video_id

    except HttpError as e:
        logger.error(f"Une erreur HTTP s'est produite: {e.resp.status} {e.content}")
        return None
    except Exception as e:
        logger.error(f"Une erreur s'est produite: {e}")
        return None

def resumable_upload(request):
    """Télécharge la vidéo en morceaux et implémente une logique de reprise."""
    response = None
    error = None
    retry = 0
    retry_max = 10
    retry_status_codes = [500, 502, 503, 504]

    while response is None:
        try:
            logger.info("Téléchargement en cours...")
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Téléchargement: {progress}%")
        except HttpError as e:
            if e.resp.status in retry_status_codes:
                error = f"Une erreur récupérable HTTP s'est produite: {e.resp.status} {e.content}"
                retry += 1
                if retry > retry_max:
                    logger.error(f"Nombre maximum de tentatives atteint: {retry_max}")
                    raise

                max_sleep = 2 ** retry
                sleep_seconds = random.random() * max_sleep
                logger.info(f"Nouvelle tentative dans {sleep_seconds:.1f} secondes...")
                time.sleep(sleep_seconds)
            else:
                logger.error(f"Une erreur HTTP non récupérable s'est produite: {e.resp.status} {e.content}")
                raise
        except (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                http.client.IncompleteRead, http.client.ImproperConnectionState,
                http.client.CannotSendRequest, http.client.CannotSendHeader,
                http.client.ResponseNotReady, http.client.BadStatusLine) as e:
            error = f"Une erreur de transport s'est produite: {e}"
            retry += 1
            if retry > retry_max:
                logger.error(f"Nombre maximum de tentatives atteint: {retry_max}")
                raise

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            logger.info(f"Nouvelle tentative dans {sleep_seconds:.1f} secondes...")
            time.sleep(sleep_seconds)

    if response:
        if 'id' in response:
            video_id = response['id']
            logger.info(f"Vidéo téléchargée avec succès! ID: {video_id}")
            logger.info(f"URL de la vidéo: https://www.youtube.com/watch?v={video_id}")
            return video_id
        else:
            logger.error("La réponse ne contient pas d'ID vidéo")
            return None
    else:
        logger.error("Le téléchargement a échoué avec une réponse vide")
        return None

def set_thumbnail(youtube, video_id, thumbnail_path):
    """Définit une miniature personnalisée pour la vidéo."""
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        logger.info("Aucune miniature personnalisée spécifiée ou fichier introuvable")
        return False

    try:
        logger.info(f"Définition de la miniature pour la vidéo {video_id}")
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        ).execute()
        logger.info("Miniature définie avec succès")
        return True
    except HttpError as e:
        logger.error(f"Une erreur HTTP s'est produite lors de la définition de la miniature: {e.resp.status} {e.content}")
        return False
    except Exception as e:
        logger.error(f"Une erreur s'est produite lors de la définition de la miniature: {e}")
        return False

def add_to_playlist(youtube, video_id, playlist_id):
    """Ajoute la vidéo à une playlist spécifiée."""
    if not playlist_id:
        logger.info("Aucune playlist spécifiée")
        return False

    try:
        logger.info(f"Ajout de la vidéo {video_id} à la playlist {playlist_id}")
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        ).execute()
        logger.info("Vidéo ajoutée à la playlist avec succès")
        return True
    except HttpError as e:
        logger.error(f"Une erreur HTTP s'est produite lors de l'ajout à la playlist: {e.resp.status} {e.content}")
        return False
    except Exception as e:
        logger.error(f"Une erreur s'est produite lors de l'ajout à la playlist: {e}")
        return False

def upload_to_youtube(args):
    """Télécharge une vidéo sur YouTube avec les paramètres spécifiés."""
    # Obtenir le service YouTube authentifié
    youtube = get_authenticated_service()
    if not youtube:
        logger.error("Impossible d'obtenir le service YouTube authentifié")
        return False

    # Initialiser le téléchargement de la vidéo
    video_id = initialize_upload(
        youtube,
        args.file,
        args.title,
        args.description,
        args.category,
        args.keywords,
        args.privacyStatus
    )

    if not video_id:
        logger.error("Le téléchargement de la vidéo a échoué")
        return False

    # Définir une miniature personnalisée si spécifiée
    if args.thumbnail:
        set_thumbnail(youtube, video_id, args.thumbnail)

    # Ajouter la vidéo à une playlist si spécifiée
    if args.playlist:
        add_to_playlist(youtube, video_id, args.playlist)

    logger.info("Processus de téléchargement YouTube terminé avec succès")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Télécharge une vidéo sur YouTube")
    parser.add_argument("--file", required=True, help="Fichier vidéo à télécharger")
    parser.add_argument("--title", required=True, help="Titre de la vidéo")
    parser.add_argument("--description", default="", help="Description de la vidéo")
    parser.add_argument("--category", default="22", help="ID de catégorie YouTube (22 = People & Blogs)")
    parser.add_argument("--keywords", default="", help="Mots-clés séparés par des virgules")
    parser.add_argument("--privacyStatus", default="public", choices=["public", "private", "unlisted"], help="Statut de confidentialité")
    parser.add_argument("--thumbnail", help="Chemin vers l'image de miniature personnalisée")
    parser.add_argument("--playlist", help="ID de la playlist à laquelle ajouter la vidéo")

    args = parser.parse_args()

    success = upload_to_youtube(args)

    if not success:
        logger.error("Échec du téléchargement sur YouTube")
        exit(1)
    else:
        logger.info("Téléchargement sur YouTube terminé avec succès")


# python upload_youtube.py \
#   --file "videos/ma_video.mp4" \
#   --title "Ma super vidéo #Shorts" \
#   --description "Une histoire mystérieuse générée automatiquement #Shorts" \
#   --keywords "histoire,mystère,shorts" \
#   --privacyStatus "public" \
#   --thumbnail "thumbnails/ma_miniature.jpg" \
#   --playlist "PLxxxxxxxxxxxxxxxx"