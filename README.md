# Messenger Video Generator

Ce projet permet de générer une vidéo animée d'une conversation Messenger, avec synthèse vocale réaliste pour chaque message, synchronisation parfaite entre l'affichage des bulles et la voix, et capture vidéo+audio automatisée.

## Fonctionnalités
- Génération d'audios pour chaque message avec voix différentes (Edge TTS)
- Nettoyage automatique des emojis et caractères spéciaux
- Génération d'un JSON enrichi avec chemins et durées des audios
- Frontend animé qui affiche les bulles synchronisées à la voix
- Capture automatisée de la vidéo **et** de l'audio du front (via Puppeteer)
- Possibilité de capturer uniquement un élément spécifique (ex : `.chat-container`)

---

## Prérequis
- **Node.js** (>= 16)
- **Python** (>= 3.8)
- **pip**
- **Google Chrome** installé (pour la capture)
- **ffmpeg** (pour manipuler les vidéos/audios si besoin)

---

## Installation

### 1. Cloner le projet
```bash
# Clone le dépôt puis va dans le dossier
cd ton_projet
```

### 2. Installer les dépendances Python
```bash
python -m venv venv
venv\Scripts\activate  # (Windows)
pip install -r requirements.txt
```

**requirements.txt** doit contenir :
```
edge-tts
moviepy
```

### 3. Installer les dépendances Node.js
```bash
npm install puppeteer puppeteer-stream express
```

---

## Structure des fichiers

```
/ton_projet
│
├── audios/                       # Dossier généré contenant les fichiers audio et le JSON enrichi
│   ├── audio_0.mp3
│   ├── audio_1.mp3
│   └── messages_with_audio.json
│
├── messages.json                 # Messages à synthétiser (format Messenger)
├── generate_audio.py             # Script Python pour générer les audios et le JSON
├── index.html                    # Front animé (affichage des bulles + lecture audio)
├── capture.js                    # Script Node.js pour automatiser la capture vidéo+audio
├── video.webm                     # Vidéo capturée (sortie)
└── ...
```

---

## Utilisation

### 1. Générer les audios et le JSON enrichi

```bash
venv\Scripts\activate  # (Windows)
python generate_audio.py
```
- Les fichiers audio sont créés dans `audios/`
- Un fichier `audios/messages_with_audio.json` est généré avec la durée totale

### 2. Lancer la capture vidéo+audio automatisée

```bash
node capture.js
```
- Génère automatiquement les audios (appelle le script Python)
- Lance un serveur local et le front
- Capture la vidéo **et** l'audio synchronisé dans `video.webm`
- Coupe automatiquement à la bonne durée

### 3. (Optionnel) Convertir la vidéo en MP4

```bash
ffmpeg -i video.webm -c:v libx264 -c:a aac output_final.mp4
```

---

## Personnalisation

- **Changer les voix** : modifie le mapping dans `generate_audio.py` (`VOICE_MAPPING`)
- **Changer l'élément capturé** : dans `capture.js`, adapte la sélection de l'élément (ex : `.chat-container`)
- **Changer le fond vidéo** : modifie le `<video>` dans `index.html`

---

## Synchronisation parfaite front/audio
- Le front (`index.html`) lit le JSON enrichi et affiche chaque bulle exactement au moment où l'audio commence.
- L'audio est joué via `<audio>` et la bulle suivante s'affiche à la fin de la lecture.

---

## Conseils
- Pour une capture parfaite, ferme les autres fenêtres et désactive les notifications.
- Si tu veux capturer tout l'écran ou une zone différente, adapte le viewport et la sélection dans `capture.js`.
- Si tu veux utiliser d'autres voix (plus de diversité), regarde du côté d'Azure, ElevenLabs, etc.

---

## Exemple de workflow complet

```bash
# 1. Générer les audios
python generate_audio.py

# 2. Lancer la capture automatisée
node capture.js

# 3. (Optionnel) Convertir en MP4
ffmpeg -i test.webm -c:v libx264 -c:a aac output_final.mp4
```

---

## Auteur
- Projet documenté et automatisé par IA (ChatGPT/OpenAI) 