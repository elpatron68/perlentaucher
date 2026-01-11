FROM python:3.11-slim

WORKDIR /app

# Installiere Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere das src-Verzeichnis
COPY src/ ./src/

# Kopiere das Entrypoint-Script
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Erstelle Download-Verzeichnis
RUN mkdir -p /downloads

# Setze Standardwerte
ENV INTERVAL_HOURS=12
ENV DOWNLOAD_DIR=/downloads
ENV LIMIT=10
ENV LOGLEVEL=INFO
ENV SPRACHE=deutsch
ENV AUDIODESKRIPTION=egal
ENV NOTIFY=

# Entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]

