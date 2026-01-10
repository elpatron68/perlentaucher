"""
Thread-Manager für asynchrone Downloads.
Nutzt QThread für nicht-blockierende Downloads.
"""
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Dict, Optional, Callable
import logging
import sys
import os

# Importiere die Core-Funktionalität von perlentaucher.py
# Füge das Root-Verzeichnis zum Python-Pfad hinzu
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
import perlentaucher as core


class DownloadThread(QThread):
    """Thread für einzelne Downloads mit Progress-Tracking."""
    
    progress_updated = pyqtSignal(int, str)  # Prozent, Status-Text
    download_started = pyqtSignal(str)  # Titel
    download_finished = pyqtSignal(bool, str, str, str)  # Erfolg, Titel, Dateipfad, Fehlermeldung
    
    def __init__(self, entry_data: Dict, config: Dict):
        """
        Initialisiert den Download-Thread.
        
        Args:
            entry_data: Dictionary mit Entry-Daten (entry_id, entry, entry_link, movie_title, year, metadata)
            config: Konfigurations-Dictionary mit allen Einstellungen
        """
        super().__init__()
        self.entry_data = entry_data
        self.config = config
        self.is_cancelled = False
    
    def cancel(self):
        """Bricht den Download ab."""
        self.is_cancelled = True
    
    def run(self):
        """Führt den Download aus."""
        try:
            entry_id = self.entry_data['entry_id']
            entry = self.entry_data['entry']
            entry_link = self.entry_data.get('entry_link', '')
            movie_title = self.entry_data['movie_title']
            year = self.entry_data.get('year')
            metadata = self.entry_data.get('metadata', {})
            
            # Prüfe ob es sich um eine Serie handelt
            is_series_entry = core.is_series(entry, metadata)
            
            self.download_started.emit(movie_title)
            
            if is_series_entry:
                if self.config.get('serien_download') == 'keine':
                    self.download_finished.emit(
                        False, 
                        movie_title, 
                        "", 
                        "Serie übersprungen (serien_download=keine)"
                    )
                    return
                
                # Serie-Verarbeitung
                if self.config.get('serien_download') == 'erste':
                    # Nur erste Episode
                    result = core.search_mediathek(
                        movie_title,
                        prefer_language=self.config.get('sprache', 'deutsch'),
                        prefer_audio_desc=self.config.get('audiodeskription', 'egal'),
                        notify_url=None,  # Keine Benachrichtigungen im Thread
                        entry_link=entry_link,
                        year=year,
                        metadata=metadata
                    )
                    
                    if result and not self.is_cancelled:
                        season, episode = core.extract_episode_info(result, movie_title)
                        series_base_dir = self.config.get('serien_dir') or self.config.get('download_dir')
                        
                        success, title, filepath = self._download_with_progress(
                            result, 
                            movie_title, 
                            metadata,
                            is_series=True,
                            series_base_dir=series_base_dir,
                            season=season,
                            episode=episode
                        )
                        
                        self.download_finished.emit(success, title, filepath, "" if success else "Download fehlgeschlagen")
                    else:
                        self.download_finished.emit(False, movie_title, "", "Film/Serie nicht in Mediathek gefunden")
                elif self.config.get('serien_download') == 'staffel':
                    # Ganze Staffel - TODO: Implementierung für mehrere Episoden
                    self.download_finished.emit(False, movie_title, "", "Staffel-Download noch nicht implementiert")
            else:
                # Normale Film-Verarbeitung
                result = core.search_mediathek(
                    movie_title,
                    prefer_language=self.config.get('sprache', 'deutsch'),
                    prefer_audio_desc=self.config.get('audiodeskription', 'egal'),
                    notify_url=None,
                    entry_link=entry_link,
                    year=year,
                    metadata=metadata
                )
                
                if result and not self.is_cancelled:
                    success, title, filepath = self._download_with_progress(
                        result,
                        movie_title,
                        metadata,
                        is_series=False
                    )
                    self.download_finished.emit(success, title, filepath, "" if success else "Download fehlgeschlagen")
                else:
                    self.download_finished.emit(False, movie_title, "", "Film nicht in Mediathek gefunden")
                    
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Fehler im Download-Thread: {error_msg}")
            self.download_finished.emit(False, self.entry_data.get('movie_title', 'Unbekannt'), "", error_msg)
    
    def _download_with_progress(self, movie_data, content_title: str, metadata: Dict, 
                               is_series: bool = False, series_base_dir: Optional[str] = None,
                               season: Optional[int] = None, episode: Optional[int] = None) -> tuple:
        """
        Lädt einen Film/Episode herunter mit Progress-Updates.
        
        Returns:
            Tuple (success: bool, title: str, filepath: str)
        """
        filepath = ""  # Initialisiere für Exception-Handler
        try:
            # Bestimme Ziel-Verzeichnis und Dateinamen
            if is_series and series_base_dir:
                target_dir = core.get_series_directory(series_base_dir, content_title, metadata.get("year"))
                base_filename = core.format_episode_filename(content_title, season, episode, metadata)
            else:
                target_dir = self.config.get('download_dir')
                base_title = content_title
                import re
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', base_title)
                filename_parts = [safe_title]
                year = metadata.get("year")
                if year:
                    filename_parts.append(f"({year})")
                provider_id = metadata.get("provider_id")
                if provider_id:
                    filename_parts.append(provider_id)
                base_filename = " ".join(filename_parts)
            
            # Bestimme Extension
            url = movie_data.get("url_video")
            if not url:
                return (False, movie_data.get("title", "Unbekannt"), "")
            
            ext = "mp4"
            if url.endswith(".mkv"):
                ext = "mkv"
            
            filename = f"{base_filename}.{ext}"
            filepath = os.path.join(target_dir, filename)
            
            # Prüfe ob Datei bereits existiert
            if os.path.exists(filepath):
                self.progress_updated.emit(100, "Datei bereits vorhanden")
                return (True, movie_data.get("title"), filepath)
            
            # Download mit Progress
            import requests
            
            self.progress_updated.emit(0, "Starte Download...")
            
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                
                downloaded = 0
                chunk_size = 8192
                
                os.makedirs(target_dir, exist_ok=True)
                
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if self.is_cancelled:
                            f.close()
                            if os.path.exists(filepath):
                                os.remove(filepath)
                            return (False, movie_data.get("title"), filepath)
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            mb_downloaded = downloaded / (1024 * 1024)
                            self.progress_updated.emit(
                                progress,
                                f"{mb_downloaded:.1f} MB / {total_size / (1024 * 1024):.1f} MB"
                            )
                        else:
                            mb_downloaded = downloaded / (1024 * 1024)
                            self.progress_updated.emit(
                                50,  # Unbekannte Größe, zeige 50%
                                f"{mb_downloaded:.1f} MB heruntergeladen"
                            )
            
            self.progress_updated.emit(100, "Download abgeschlossen")
            return (True, movie_data.get("title"), filepath)
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Download-Fehler: {error_msg}")
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            return (False, movie_data.get("title", "Unbekannt"), filepath if filepath else "")
