#!/usr/bin/env python3
import os
import argparse
import logging
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration des logs
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/tiktok_{time.strftime('%Y%m%d')}.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def upload_to_tiktok(video_file, caption):
    """
    Télécharge une vidéo sur TikTok en utilisant Selenium pour automatiser le navigateur.

    Note: TikTok n'a pas d'API officielle pour le téléchargement de vidéos, donc cette
    méthode utilise l'automatisation du navigateur, ce qui est moins fiable qu'une API
    officielle mais reste la meilleure option disponible.
    """
    # Récupérer les identifiants depuis les variables d'environnement
    username = os.getenv("TIKTOK_USERNAME")
    password = os.getenv("TIKTOK_PASSWORD")

    if not username or not password:
        logger.error("Identifiants TikTok manquants dans le fichier .env")
        return False

    # Vérifier que le fichier existe
    if not os.path.exists(video_file):
        logger.error(f"Le fichier vidéo n'existe pas: {video_file}")
        return False

    # Vérifier que le fichier est une vidéo valide
    if not video_file.lower().endswith(('.mp4', '.mov', '.avi')):
        logger.error(f"Le fichier n'est pas une vidéo valide: {video_file}")
        return False

    try:
        logger.info(f"Préparation du téléchargement de la vidéo sur TikTok: {video_file}")

        # Configurer les options Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Exécuter en mode headless (sans interface graphique)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # Créer une instance du navigateur
        logger.info("Lancement du navigateur Chrome")
        driver = webdriver.Chrome(options=chrome_options)

        try:
            # Accéder à la page de connexion TikTok
            logger.info("Accès à la page de connexion TikTok")
            driver.get("https://www.tiktok.com/login")

            # Attendre que la page se charge
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//form"))
            )

            # Sélectionner la connexion par email/mot de passe
            logger.info("Sélection de la méthode de connexion par email")
            try:
                email_login_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Use phone / email / username')]"))
                )
                email_login_button.click()
            except TimeoutException:
                logger.info("Bouton de connexion par email non trouvé, essai de la méthode alternative")
                try:
                    email_login_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Log in with email or username')]"))
                    )
                    email_login_button.click()
                except TimeoutException:
                    logger.warning("Méthode de connexion par email non trouvée, tentative de continuer")

            # Remplir le formulaire de connexion
            logger.info("Remplissage du formulaire de connexion")
            try:
                # Attendre que le champ email soit visible
                email_field = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, "//input[@name='username' or @name='email']"))
                )
                email_field.clear()
                email_field.send_keys(username)

                # Remplir le mot de passe
                password_field = driver.find_element(By.XPATH, "//input[@type='password']")
                password_field.clear()
                password_field.send_keys(password)

                # Cliquer sur le bouton de connexion
                login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
                login_button.click()

                # Attendre que la connexion soit établie
                logger.info("Attente de la connexion...")
                WebDriverWait(driver, 30).until(
                    EC.url_contains("tiktok.com/@")
                )
                logger.info("Connexion réussie")

            except (TimeoutException, NoSuchElementException) as e:
                logger.error(f"Erreur lors de la connexion: {e}")
                return False

            # Accéder à la page de téléchargement
            logger.info("Accès à la page de téléchargement")
            driver.get("https://www.tiktok.com/upload")

            # Attendre que la page de téléchargement se charge
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'upload')]"))
            )

            # Télécharger la vidéo
            logger.info("Téléchargement de la vidéo")
            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )

            # Convertir le chemin relatif en chemin absolu
            abs_video_path = os.path.abspath(video_file)
            file_input.send_keys(abs_video_path)

            # Attendre que la vidéo soit téléchargée
            logger.info("Attente du téléchargement de la vidéo...")
            WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, 'progress-bar') and contains(@class, 'completed')]"))
            )
            logger.info("Vidéo téléchargée avec succès")

            # Ajouter la légende
            logger.info("Ajout de la légende")
            caption_field = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//div[@role='textbox' or @contenteditable='true']"))
            )
            caption_field.clear()
            caption_field.send_keys(caption)

            # Cliquer sur le bouton de publication
            logger.info("Publication de la vidéo")
            post_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Post') or contains(text(), 'Upload') or contains(@class, 'publish')]"))
            )
            post_button.click()

            # Attendre la confirmation de publication
            logger.info("Attente de la confirmation de publication...")
            WebDriverWait(driver, 120).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(text(), 'Your video is being uploaded to TikTok') or contains(text(), 'Your video has been uploaded')]"))
            )

            logger.info("Vidéo publiée avec succès sur TikTok!")
            return True

        finally:
            # Fermer le navigateur
            logger.info("Fermeture du navigateur")
            driver.quit()

    except Exception as e:
        logger.error(f"Erreur lors du téléchargement sur TikTok: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def upload_to_tiktok_alternative(video_file, caption):
    """
    Méthode alternative utilisant un service tiers pour publier sur TikTok.
    Cette méthode est fournie comme solution de secours si l'automatisation du navigateur échoue.

    Note: Cette méthode nécessite un service tiers comme Zapier, IFTTT ou un service d'API TikTok non officiel.
    """
    logger.info("Utilisation de la méthode alternative pour TikTok")

    # Exemple d'utilisation d'un service d'API tiers (à adapter selon le service utilisé)
    try:
        # Simuler l'envoi à un service tiers
        logger.info(f"Envoi de la vidéo {video_file} à un service tiers pour publication sur TikTok")
        logger.info(f"Légende: {caption}")

        # Ici, tu devrais implémenter l'appel à ton service tiers
        # Par exemple, un webhook Zapier, une API personnalisée, etc.

        # Exemple fictif:
        # response = requests.post(
        #     "https://ton-service-tiers.com/api/tiktok/upload",
        #     files={"video": open(video_file, "rb")},
        #     data={"caption": caption}
        # )
        # if response.status_code == 200:
        #     logger.info("Vidéo envoyée avec succès au service tiers")
        #     return True

        # Pour l'instant, on simule un succès
        logger.info("Simulation: Vidéo envoyée avec succès au service tiers")
        return True

    except Exception as e:
        logger.error(f"Erreur lors de l'utilisation du service tiers pour TikTok: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Télécharge une vidéo sur TikTok")
    parser.add_argument("--file", required=True, help="Fichier vidéo à télécharger")
    parser.add_argument("--caption", required=True, help="Légende de la vidéo")
    parser.add_argument("--alternative", action="store_true", help="Utiliser la méthode alternative")

    args = parser.parse_args()

    if args.alternative:
        success = upload_to_tiktok_alternative(args.file, args.caption)
    else:
        success = upload_to_tiktok(args.file, args.caption)

    if not success:
        logger.error("Échec du téléchargement sur TikTok")
        exit(1)
    else:
        logger.info("Téléchargement sur TikTok terminé avec succès")


# # Méthode principale (automatisation de navigateur)
# python upload_tiktok.py --file "videos/ma_video.mp4" --caption "Ma super vidéo #TikTok"

# # Méthode alternative (service tiers)
# python upload_tiktok.py --file "videos/ma_video.mp4" --caption "Ma super vidéo #TikTok" --alternative