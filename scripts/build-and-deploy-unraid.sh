#!/usr/bin/env bash
#
# Baut das Perlentaucher-Docker-Image, speichert es als Tar, kopiert es per scp
# auf einen Unraid-Host und führt dort „docker load“ aus.
#
# Voraussetzung: docker, ssh, scp; passwortloser SSH-Zugang zum Ziel-Host empfohlen.
#
# Nutzung (aus dem Repo-Root oder beliebig):
#   ./scripts/build-and-deploy-unraid.sh
#
# Anpassung per Umgebungsvariablen:
#   REMOTE_HOST=root@192.168.1.10 REMOTE_DIR=/mnt/user/appdata/foo IMAGE_TAG=perlentaucher:dev ./scripts/build-and-deploy-unraid.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REMOTE_HOST="${REMOTE_HOST:-root@192.168.177.5}"
REMOTE_DIR="${REMOTE_DIR:-/mnt/user/appdata/perlentaucher-branch-test}"
IMAGE_TAG="${IMAGE_TAG:-perlentaucher:branch-test}"
TAR_NAME="${TAR_NAME:-perlentaucher-branch.tar}"
TAR_PATH="${TAR_PATH:-$ROOT/$TAR_NAME}"

echo "==> Build-Kontext: $ROOT"
echo "==> Image:        $IMAGE_TAG"
echo "==> Ziel:         $REMOTE_HOST:$REMOTE_DIR/$TAR_NAME"

docker build -t "$IMAGE_TAG" -f docker/Dockerfile .

echo "==> docker save → $TAR_PATH"
docker save "$IMAGE_TAG" -o "$TAR_PATH"

cleanup() { rm -f "$TAR_PATH"; }
trap cleanup EXIT

echo "==> ssh: Verzeichnis anlegen"
ssh "$REMOTE_HOST" "mkdir -p '$REMOTE_DIR'"

echo "==> scp: Tar kopieren"
scp "$TAR_PATH" "$REMOTE_HOST:$REMOTE_DIR/$TAR_NAME"

echo "==> ssh: docker load"
ssh "$REMOTE_HOST" "docker load -i '$REMOTE_DIR/$TAR_NAME'"

trap - EXIT
rm -f "$TAR_PATH"
echo "==> Fertig. Image auf $REMOTE_HOST geladen ($IMAGE_TAG)."
