import argparse
import logging
import os
import re
import sys
import requests
import feedparser
import json

# Configuration
RSS_FEED_URL = "https://nexxtpress.de/author/mediathekperlen/feed/"
MVW_API_URL = "https://mediathekviewweb.de/api/query"

# Logging setup
def setup_logging(level_name):
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=level,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def parse_rss_feed(limit):
    logging.info(f"Parsing RSS feed: {RSS_FEED_URL}")
    feed = feedparser.parse(RSS_FEED_URL)
    
    if feed.bozo:
        logging.warning("Feed parsing encountered an error, but continuing...")
    
    entries = feed.entries[:limit]
    logging.info(f"Found {len(entries)} entries (limit: {limit})")
    
    movies = []
    for entry in entries:
        title = entry.title
        # Regex to extract title from 'Director - „Movie“ (Year)' or similar
        # Looking for content inside „...“
        match = re.search(r'„(.*?)“', title)
        if match:
            movie_title = match.group(1)
            logging.debug(f"Extracted movie title: '{movie_title}' from '{title}'")
            movies.append(movie_title)
        else:
            logging.warning(f"Could not extract movie title from RSS entry: '{title}'")
    
    return movies

def search_mediathek(movie_title):
    logging.info(f"Searching MediathekViewWeb for: '{movie_title}'")
    payload = {
        "queries": [
            {
                "fields": ["title", "topic"],
                "query": movie_title
            }
        ],
        "sortBy": "size",  # Sort by size to get best quality easily
        "sortOrder": "desc",
        "future": False,
        "offset": 0,
        "size": 5  # Get top 5 to filter if needed
    }
    
    try:
        response = requests.post(MVW_API_URL, json=payload, headers={"Content-Type": "text/plain"}, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("result", {}).get("results", [])
        if not results:
            logging.info(f"No results found for '{movie_title}'")
            return None
        
        # Helper to get the best result.
        # Since we sorted by size desc, the first one should be the largest file (best quality usually)
        # But we can also check for resolution if available
        # But simply picking the largest file is a good heuristic for "best quality" in this context
        best_match = results[0]
        logging.info(f"Found match: {best_match.get('title')} ({best_match.get('size')} bytes)")
        return best_match

    except Exception as e:
        logging.error(f"Error searching for '{movie_title}': {e}")
        return None

def download_movie(movie_data, download_dir):
    url = movie_data.get("url_video")
    title = movie_data.get("title")
    # Clean filename
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
    # Try to guess extension
    ext = "mp4"
    if url.endswith(".mkv"): ext = "mkv"
    if url.endswith(".mp4"): ext = "mp4"
    
    filename = f"{safe_title}.{ext}"
    filepath = os.path.join(download_dir, filename)

    if os.path.exists(filepath):
        logging.info(f"File already exists, skipping: {filepath}")
        return

    logging.info(f"Starting download: {title} -> {filepath}")
    
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size_in_bytes = int(r.headers.get('content-length', 0))
            if total_size_in_bytes == 0:
                logging.warning("Content-Length header is missing. Cannot show progress.")

            with open(filepath, 'wb') as f:
                downloaded = 0
                chunk_size = 8192
                for chunk in r.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    downloaded += len(chunk)
                    # Log progress every 10% or so could be spammy in logs, 
                    # but good for console if we were using print. 
                    # For logging module, maybe just every 50MB?
                    if downloaded % (50 * 1024 * 1024) < chunk_size: # approx every 50MB
                         logging.info(f"Downloaded {downloaded / (1024*1024):.1f} MB ...")
        
        logging.info(f"Download completed: {filepath}")

    except Exception as e:
        logging.error(f"Failed to download {title}: {e}")
        # Clean up partial file
        if os.path.exists(filepath):
            os.remove(filepath)

def main():
    parser = argparse.ArgumentParser(description="Perlenlader - RSS Feed Downloader for MediathekViewWeb")
    parser.add_argument("--download-dir", default=os.getcwd(), help="Directory to save downloads")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent RSS posts to modify")
    parser.add_argument("--loglevel", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Log level")
    
    args = parser.parse_args()
    
    setup_logging(args.loglevel)
    
    if not os.path.exists(args.download_dir):
        try:
            os.makedirs(args.download_dir)
            logging.info(f"Created download directory: {args.download_dir}")
        except OSError as e:
            logging.critical(f"Could not create download directory {args.download_dir}: {e}")
            sys.exit(1)

    movies = parse_rss_feed(args.limit)
    
    for movie in movies:
        result = search_mediathek(movie)
        if result:
            download_movie(result, args.download_dir)
        else:
            logging.warning(f"Skipping '{movie}' - not found in Mediathek.")

if __name__ == "__main__":
    main()
