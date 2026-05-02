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

    def _feed_notify_settings(self) -> Tuple[Optional[str], Optional[str]]:
        """
        GUI löst grundsätzlich keine externen Benachrichtigungen aus.
        CLI bleibt der einzige Kanal für Ntfy/Apprise.
        """
        return (None, None)

    def cancel(self):
        """Bricht den Download ab."""
        self.is_cancelled = True
    
    def run(self):
        """Führt den Download aus."""
        try:
            entry_id = self.entry_data['entry_id']
            entry = self.entry_data['entry']
            entry_link = self.entry_data.get('entry_link', '')
            sender_mediathek_url = self.entry_data.get('sender_mediathek_url')
            movie_title = self.entry_data['movie_title']
            year = self.entry_data.get('year')
            metadata = self.entry_data.get('metadata', {})
            notify_url, notify_src = self._feed_notify_settings()

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
                        notify_url=notify_url,
                        notify_source=notify_src,
                        entry_link=entry_link,
                        year=year,
                        metadata=metadata,
                        debug=self.debug_no_download,
                        sender_reference_url=sender_mediathek_url,
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
                    self._download_series_season(movie_title, entry_link, year, metadata, sender_mediathek_url)
            else:
                # Normale Film-Verarbeitung
                result = core.search_mediathek(
                    movie_title,
                    prefer_language=self.config.get('sprache', 'deutsch'),
                    prefer_audio_desc=self.config.get('audiodeskription', 'egal'),
                    notify_url=notify_url,
                    notify_source=notify_src,
                    entry_link=entry_link,
                    year=year,
                    metadata=metadata,
                    debug=self.debug_no_download,
                    sender_reference_url=sender_mediathek_url,
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
        Lädt einen Film/Episode herunter mit Progress-Updates (einheitlich über core.download_content).

        Returns:
            Tuple (success: bool, title: str, filepath: str)
        """
        blog_link = (self.entry_data.get("entry_link") or "").strip() or None
        cfg_ff = (self.config.get("ffmpeg_path") or "").strip()
        ffmpeg_path_kw = cfg_ff if cfg_ff else None

        def progress_cb(pct: int, msg: str) -> None:
            if not self.is_cancelled:
                self.progress_updated.emit(pct, msg)

        def cancel_cb() -> bool:
            return self.is_cancelled

        try:
            success, title, filepath, skipped = core.download_content(
                movie_data,
                self.config.get("download_dir"),
                content_title=content_title,
                metadata=metadata,
                is_series=is_series,
                series_base_dir=series_base_dir,
                season=season,
                episode=episode,
                notify_url=None,
                notify_source=None,
                entry_link=blog_link,
                ffmpeg_path=ffmpeg_path_kw,
                progress_callback=progress_cb,
                cancel_check=cancel_cb,
            )
            disp = title or movie_data.get("title", "Unbekannt")
            if success and filepath:
                if skipped:
                    self.progress_updated.emit(100, "Datei bereits vorhanden")
                else:
                    self.progress_updated.emit(100, "Download abgeschlossen")
            return (success, disp, filepath or "")
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Download-Fehler: {error_msg}")
            nu, ns = self._feed_notify_settings()
            core.notify_non_wishlist_download_outcome(
                nu,
                ns,
                "error",
                title=movie_data.get("title"),
                filepath=None,
                content_title=content_title,
                is_series=is_series,
                season=season,
                episode=episode,
                error_text=error_msg,
                entry_link=blog_link,
            )
            return (False, movie_data.get("title", "Unbekannt"), "")
    
    def _download_series_season(
        self,
        series_title: str,
        entry_link: str,
        year: Optional[int],
        metadata: Dict,
        sender_mediathek_url: Optional[str] = None,
    ):
        """
        Lädt alle Episoden einer Serie herunter.
        
        Args:
            series_title: Der Serientitel
            entry_link: Link zum Blog-Eintrag
            year: Optional - Das Jahr der Serie
            metadata: Dictionary mit Metadaten
            sender_mediathek_url: Optional - Direkter Sender-Mediathek-Link aus dem Blogpost
        """
        try:
            notify_url, notify_src = self._feed_notify_settings()
            # Suche nach allen Episoden
            episodes = core.search_mediathek_series(
                series_title,
                prefer_language=self.config.get('sprache', 'deutsch'),
                prefer_audio_desc=self.config.get('audiodeskription', 'egal'),
                notify_url=notify_url,
                notify_source=notify_src,
                entry_link=entry_link,
                year=year,
                metadata=metadata,
                debug=self.debug_no_download,
                sender_reference_url=sender_mediathek_url,
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
                        metadata=metadata,
                        use_series_listing_similarity=True,
                    )
                except Exception as e:
                    logging.debug(f"Fehler beim Bewerten einer Episode: {e}")
                    score = 0
                
                episode_key = (season, episode_num)
                # Behalte nur die Episode mit dem höchsten Score
                if episode_key not in episodes_dict or score > episodes_dict[episode_key][0]:
                    episodes_dict[episode_key] = (score, episode_data)
            
            # Fallback: Episoden ohne S/E nicht verwerfen – als Staffel 1 fortlaufend nummerieren (wie CLI)
            if episodes_without_info and core.should_use_unknown_episode_fallback(episodes_dict):
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
                            metadata=metadata,
                            use_series_listing_similarity=True,
                        )
                    except Exception as e:
                        logging.debug(f"Fehler beim Bewerten einer Episode: {e}")
                        score = 0
                    key = (1, fallback_ep)
                    if key not in episodes_dict or score > episodes_dict[key][0]:
                        episodes_dict[key] = (score, episode_data)
                logging.info(f"{len(episodes_without_info)} Episoden ohne Staffel/Episode-Info als S01E{max_ep_s1 + 1}+ nummeriert")
            elif episodes_without_info:
                logging.info(
                    f"{len(episodes_without_info)} Episoden ohne Staffel/Episode-Info verworfen "
                    "(genug valide Episoden vorhanden)"
                )
            
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
