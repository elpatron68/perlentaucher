"""
Thread-Manager für asynchrone Downloads.
Nutzt QThread für nicht-blockierende Downloads.
"""
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Dict, Optional, Callable, List, Tuple
import logging
import sys
import os

# Importiere die Core-Funktionalität von perlentaucher.py
# Relativer Import da wir jetzt in src/gui/utils sind
import sys
import os
# Füge src-Verzeichnis zum Pfad hinzu für relativen Import
src_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
from src import perlentaucher as core


class DownloadThread(QThread):
    """Thread für einzelne Downloads mit Progress-Tracking."""
    
    progress_updated = pyqtSignal(int, str)  # Prozent, Status-Text
    download_started = pyqtSignal(str)  # Titel
    download_finished = pyqtSignal(bool, str, str, str)  # Erfolg, Titel, Dateipfad, Fehlermeldung
    
    def __init__(self, entry_data: Dict, config: Dict, series_download_mode: Optional[str] = None):
        """
        Initialisiert den Download-Thread.
        
        Args:
            entry_data: Dictionary mit Entry-Daten (entry_id, entry, entry_link, movie_title, year, metadata)
            config: Konfigurations-Dictionary mit allen Einstellungen
            series_download_mode: Optional - 'erste' oder 'staffel' für Serien (überschreibt Config)
        """
        super().__init__()
        self.entry_data = entry_data
        self.config = config
        self.series_download_mode = series_download_mode  # Überschreibt Config für diesen Eintrag
        self.is_cancelled = False
        self.debug_no_download = self.config.get('debug_no_download', False)
    
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
            # Erstelle kompatibles Entry-Objekt für is_series()
            from gui.utils.feedparser_helpers import make_entry_compatible
            entry_dict = make_entry_compatible(entry)
            is_series_entry = core.is_series(entry_dict, metadata)
            
            self.download_started.emit(movie_title)
            
            if is_series_entry:
                # Verwende series_download_mode wenn gesetzt, sonst Config
                serien_mode = self.series_download_mode if self.series_download_mode else self.config.get('serien_download', 'erste')
                
                if serien_mode == 'keine':
                    self.download_finished.emit(
                        False, 
                        movie_title, 
                        "", 
                        "Serie übersprungen (serien_download=keine)"
                    )
                    return
                
                # Serie-Verarbeitung
                if serien_mode == 'erste':
                    # Nur erste Episode
                    result = core.search_mediathek(
                        movie_title,
                        prefer_language=self.config.get('sprache', 'deutsch'),
                        prefer_audio_desc=self.config.get('audiodeskription', 'egal'),
                        notify_url=None,  # Keine Benachrichtigungen im Thread
                        entry_link=entry_link,
                        year=year,
                        metadata=metadata,
                        debug=self.debug_no_download
                    )
                    
                    if result and not self.is_cancelled:
                        season, episode = core.extract_episode_info(result, movie_title)
                        series_base_dir = self.config.get('serien_dir') or self.config.get('download_dir')

                        if self.debug_no_download:
                            filepath = core.build_download_filepath(
                                result,
                                self.config.get('download_dir'),
                                movie_title,
                                metadata,
                                is_series=True,
                                series_base_dir=series_base_dir,
                                season=season,
                                episode=episode,
                                create_dirs=False
                            )
                            logging.info(f"DEBUG-MODUS: Download übersprungen: '{result.get('title')}' -> {filepath}")
                            self.download_finished.emit(True, result.get("title", movie_title), filepath, "DEBUG_NO_DOWNLOAD")
                        else:
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
                elif serien_mode == 'staffel':
                    # Ganze Staffel - Lade alle Episoden
                    self._download_series_season(movie_title, entry_link, year, metadata)
            else:
                # Normale Film-Verarbeitung
                result = core.search_mediathek(
                    movie_title,
                    prefer_language=self.config.get('sprache', 'deutsch'),
                    prefer_audio_desc=self.config.get('audiodeskription', 'egal'),
                    notify_url=None,
                    entry_link=entry_link,
                    year=year,
                    metadata=metadata,
                    debug=self.debug_no_download
                )
                
                if result and not self.is_cancelled:
                    if self.debug_no_download:
                        filepath = core.build_download_filepath(
                            result,
                            self.config.get('download_dir'),
                            movie_title,
                            metadata,
                            is_series=False,
                            create_dirs=False
                        )
                        logging.info(f"DEBUG-MODUS: Download übersprungen: '{result.get('title')}' -> {filepath}")
                        self.download_finished.emit(True, result.get("title", movie_title), filepath, "DEBUG_NO_DOWNLOAD")
                    else:
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
    
    def _download_series_season(self, series_title: str, entry_link: str, year: Optional[int], metadata: Dict):
        """
        Lädt alle Episoden einer Serie herunter.
        
        Args:
            series_title: Der Serientitel
            entry_link: Link zum Blog-Eintrag
            year: Optional - Das Jahr der Serie
            metadata: Dictionary mit Metadaten
        """
        try:
            # Suche nach allen Episoden
            episodes = core.search_mediathek_series(
                series_title,
                prefer_language=self.config.get('sprache', 'deutsch'),
                prefer_audio_desc=self.config.get('audiodeskription', 'egal'),
                notify_url=None,  # Keine Benachrichtigungen im Thread
                entry_link=entry_link,
                year=year,
                metadata=metadata,
                debug=self.debug_no_download
            )
            
            if not episodes:
                self.download_finished.emit(False, series_title, "", "Keine Episoden für Serie gefunden")
                return
            
            # Sortiere Episoden nach Staffel/Episode und dedupliziere (wie in CLI)
            # Verwende Dictionary um nur die beste Version jeder Episode zu behalten
            episodes_dict = {}  # Key: (season, episode), Value: (score, episode_data)
            episodes_without_info = []  # Episoden ohne erkennbare S/E – Fallback-Nummer vergeben
            
            for episode_data in episodes:
                season, episode_num = core.extract_episode_info(episode_data, series_title)
                if season is None or episode_num is None:
                    episodes_without_info.append(episode_data)
                    continue
                
                # Bewerte Episode (score_movie gibt einen Score zurück)
                try:
                    score = core.score_movie(
                        episode_data,
                        self.config.get('sprache', 'deutsch'),
                        self.config.get('audiodeskription', 'egal'),
                        search_title=series_title,
                        search_year=year,
                        metadata=metadata
                    )
                except Exception as e:
                    logging.debug(f"Fehler beim Bewerten einer Episode: {e}")
                    score = 0
                
                episode_key = (season, episode_num)
                # Behalte nur die Episode mit dem höchsten Score
                if episode_key not in episodes_dict or score > episodes_dict[episode_key][0]:
                    episodes_dict[episode_key] = (score, episode_data)
            
            # Fallback: Episoden ohne S/E nicht verwerfen – als Staffel 1 fortlaufend nummerieren (wie CLI)
            if episodes_without_info:
                max_ep_s1 = max((e for (s, e) in episodes_dict if s == 1), default=0)
                for i, episode_data in enumerate(episodes_without_info):
                    fallback_ep = max_ep_s1 + 1 + i
                    try:
                        score = core.score_movie(
                            episode_data,
                            self.config.get('sprache', 'deutsch'),
                            self.config.get('audiodeskription', 'egal'),
                            search_title=series_title,
                            search_year=year,
                            metadata=metadata
                        )
                    except Exception as e:
                        logging.debug(f"Fehler beim Bewerten einer Episode: {e}")
                        score = 0
                    key = (1, fallback_ep)
                    if key not in episodes_dict or score > episodes_dict[key][0]:
                        episodes_dict[key] = (score, episode_data)
                logging.info(f"{len(episodes_without_info)} Episoden ohne Staffel/Episode-Info als S01E{max_ep_s1 + 1}+ nummeriert")
            
            # Konvertiere Dictionary zu Liste und sortiere
            episodes_with_info = [(s, e, data) for (s, e), (score, data) in episodes_dict.items()]
            episodes_with_info.sort(key=lambda x: (x[0] or 0, x[1] or 0))
            
            total_episodes = len(episodes_with_info)
            if total_episodes == 0:
                self.download_finished.emit(False, series_title, "", "Keine Episoden mit Staffel/Episode-Info gefunden")
                return
            
            # Sende Start-Signal mit Gesamtanzahl
            self.download_started.emit(f"{series_title} ({total_episodes} Episoden)")
            
            # Bestimme series_base_dir
            series_base_dir = self.config.get('serien_dir') or self.config.get('download_dir')
            if self.debug_no_download:
                logging.info(f"DEBUG-MODUS: Staffel-Download übersprungen ({total_episodes} Episoden)")
                for season, episode_num, episode_data in episodes_with_info:
                    if season is None or episode_num is None:
                        continue
                    filepath = core.build_download_filepath(
                        episode_data,
                        self.config.get('download_dir'),
                        series_title,
                        metadata,
                        is_series=True,
                        series_base_dir=series_base_dir,
                        season=season,
                        episode=episode_num,
                        create_dirs=False
                    )
                    logging.info(
                        f"  - S{season:02d}E{episode_num:02d}: "
                        f"{episode_data.get('title', 'Unbekannt')} -> {filepath}"
                    )
                self.download_finished.emit(True, f"{series_title} ({total_episodes} Episoden)", "", "DEBUG_NO_DOWNLOAD")
                return
            
            downloaded_count = 0
            failed_count = 0
            
            # Lade Episoden sequenziell
            for idx, (season, episode_num, episode_data) in enumerate(episodes_with_info, 1):
                if self.is_cancelled:
                    self.download_finished.emit(False, series_title, "", "Download abgebrochen")
                    return
                
                # Update Progress: Zeige aktuellen Fortschritt (Episode X von Y)
                episode_title = episode_data.get('title', f'S{season or 0:02d}E{episode_num or 0:02d}')
                progress_percent = int((idx - 1) / total_episodes * 100)
                self.progress_updated.emit(
                    progress_percent,
                    f"Episode {idx}/{total_episodes}: {episode_title}"
                )
                
                # Download Episode
                success, title, filepath = self._download_with_progress(
                    episode_data,
                    series_title,
                    metadata,
                    is_series=True,
                    series_base_dir=series_base_dir,
                    season=season,
                    episode=episode_num
                )
                
                if success:
                    downloaded_count += 1
                    logging.info(f"Episode S{season:02d}E{episode_num:02d} erfolgreich heruntergeladen: {filepath}")
                    
                    # State-Datei für diese Episode aktualisieren
                    self._update_episode_state(series_title, season, episode_num, 'download_success', filepath)
                else:
                    failed_count += 1
                    logging.error(f"Episode S{season:02d}E{episode_num:02d} fehlgeschlagen: {title}")
                    
                    # State-Datei für diese Episode aktualisieren
                    self._update_episode_state(series_title, season, episode_num, 'download_failed', None)
            
            # Finale Progress-Update
            final_progress = 100 if total_episodes > 0 else 0
            status_msg = f"Abgeschlossen: {downloaded_count}/{total_episodes} Episoden"
            if failed_count > 0:
                status_msg += f" ({failed_count} fehlgeschlagen)"
            self.progress_updated.emit(final_progress, status_msg)
            
            # Markiere Haupt-Eintrag als verarbeitet (mit Liste der Episoden)
            entry_id = self.entry_data['entry_id']
            config = self.config
            no_state = config.get('no_state', False)
            if not no_state:
                state_file = config.get('state_file', '.perlentaucher_state.json')
                if state_file:
                    try:
                        main_status = 'download_success' if downloaded_count > 0 else 'download_failed'
                        episodes_list = [f"S{s:02d}E{e:02d}" for s, e, _ in episodes_with_info if s is not None and e is not None]
                        core.save_processed_entry(
                            state_file,
                            entry_id,
                            status=main_status,
                            movie_title=series_title,
                            is_series=True,
                            episodes=episodes_list
                        )
                    except Exception as e:
                        logging.warning(f"Konnte Haupt-Eintrag State-Datei nicht aktualisieren: {e}")
            
            # Sende Finale-Signal
            if downloaded_count > 0:
                self.download_finished.emit(
                    True,
                    f"{series_title} ({downloaded_count}/{total_episodes} Episoden)",
                    "",  # Kein einzelner Dateipfad, da mehrere Dateien
                    status_msg
                )
            else:
                self.download_finished.emit(False, series_title, "", "Alle Episoden fehlgeschlagen")
                
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Fehler beim Staffel-Download für '{series_title}': {error_msg}")
            self.download_finished.emit(False, series_title, "", f"Fehler: {error_msg}")
    
    def _update_episode_state(self, series_title: str, season: Optional[int], episode: Optional[int], 
                             status: str, filepath: Optional[str]):
        """
        Aktualisiert die State-Datei für eine einzelne Episode.
        
        Args:
            series_title: Serientitel
            season: Staffel-Nummer
            episode: Episoden-Nummer
            status: Status ('download_success', 'download_failed', etc.)
            filepath: Optional - Pfad zur heruntergeladenen Datei
        """
        try:
            entry_id = self.entry_data['entry_id']
            config = self.config
            no_state = config.get('no_state', False)
            if no_state:
                return
            
            state_file = config.get('state_file', '.perlentaucher_state.json')
            if not state_file:
                return
            
            if season is not None and episode is not None:
                # Speichere individuelle Episode
                episode_id = f"{entry_id}_S{season:02d}E{episode:02d}"
                filename = os.path.basename(filepath) if filepath and os.path.exists(filepath) else None
                core.save_processed_entry(
                    state_file,
                    episode_id,
                    status=status,
                    movie_title=f"{series_title} S{season:02d}E{episode:02d}",
                    filename=filename
                )
        except Exception as e:
            logging.warning(f"Konnte State-Datei für Episode nicht aktualisieren: {e}")
