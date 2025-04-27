#!/usr/bin/env python3
"""
Script Python pour télécharger et synchroniser des playlists Spotify
en utilisant Docker et spotdl.

Fonctionnalités :
- Création du répertoire cible s'il n'existe pas
- Sauvegarde de l'état sync dans un fichier save.spotdl
- Gestion du téléchargement initial et de la synchronisation ultérieure
"""
import os
import subprocess
from pathlib import Path

def download_playlist(playlist_url: str, target_dir: str):
    """
    Télécharge ou synchronise une playlist Spotify.

    Args:
        playlist_url (str): URL de la playlist Spotify.
        target_dir (str): Chemin du répertoire local de destination.
    """
    save_file = Path(target_dir) / 'save.spotdl'

    # Créer le répertoire cible s'il n'existe pas
    os.makedirs(target_dir, exist_ok=True)

    # Définir la commande Docker
    base_cmd = [
        'docker', 'run', '--rm',
        '-v', f'{os.path.abspath(target_dir)}:/music',
        'spotdl/spotify-downloader',
    ]

    if not save_file.exists():
        print(f"Génération du fichier de sauvegarde pour {target_dir}...")
        cmd = base_cmd + [
            'sync', playlist_url,
            '--save-file', '/music/save.spotdl'
        ]
    else:
        print(f"Synchronisation avec le fichier existant save.spotdl pour {target_dir}...")
        cmd = base_cmd + [
            'sync', '/music/save.spotdl'
        ]

    # Exécuter la commande
    try:
        subprocess.run(cmd, check=True)
        print(f"Opération terminée pour {target_dir}\n")
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'exécution de Docker pour {target_dir}: {e}")

if __name__ == '__main__':
    # Liste des playlists à traiter
    playlists = [
        ('https://open.spotify.com/playlist/37i9dQZEVXbIPWwFssbupI', './top-50-france'),
        ('https://open.spotify.com/playlist/7ix6X61JdZZXhlRge6N65z', './mes_titre_likes'),
    ]

    for url, directory in playlists:
        download_playlist(url, directory)