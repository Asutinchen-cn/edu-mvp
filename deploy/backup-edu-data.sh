#!/bin/sh
set -eu

umask 077

PROJECT_DIR="${PROJECT_DIR:-/opt/edu-mvp}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
BACKUP_DIR="$PROJECT_DIR/data/backups"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
STAGING_DIR="$BACKUP_DIR/.tmp-$TIMESTAMP"
FINAL_DIR="$BACKUP_DIR/$TIMESTAMP"

cleanup() {
    /bin/rm -rf -- "$STAGING_DIR"
}

trap cleanup 0 1 2 15

/bin/mkdir -p "$BACKUP_DIR"
/bin/rm -rf -- "$STAGING_DIR"
/bin/mkdir -p "$STAGING_DIR"

/usr/bin/docker exec -i edu-api python - "$TIMESTAMP" <<'PY'
from pathlib import Path
import sqlite3
import sys


timestamp = sys.argv[1]
source_path = Path("/data/exam.db")
target_path = Path("/data/backups") / f".tmp-{timestamp}" / "exam.db"
target_path.parent.mkdir(parents=True, exist_ok=True)

source_db = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True, timeout=30)
target_db = sqlite3.connect(target_path)
try:
    source_db.backup(target_db)
    check_rows = target_db.execute("PRAGMA quick_check").fetchall()
finally:
    target_db.close()
    source_db.close()

if check_rows != [("ok",)]:
    raise RuntimeError(f"SQLite backup failed quick_check: {check_rows}")
PY

/usr/bin/tar -cf "$STAGING_DIR/uploads.tar" -C "$PROJECT_DIR" uploads

(
    cd "$STAGING_DIR"
    /usr/bin/sha256sum exam.db uploads.tar > SHA256SUMS
)

/bin/chmod -R go-rwx "$STAGING_DIR"
/bin/mv "$STAGING_DIR" "$FINAL_DIR"
/bin/ln -sfn "$TIMESTAMP" "$BACKUP_DIR/latest"

/usr/bin/find "$BACKUP_DIR" \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    -name "20??????T??????Z" \
    -mtime +"$RETENTION_DAYS" \
    -exec /bin/rm -rf -- {} +

/bin/echo "edu-mvp backup ready: $FINAL_DIR"
