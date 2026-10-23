#!/usr/bin/env bash
# Backup Postgres production — giữ 14 bản
# Cách dùng:
#   export DATABASE_URL='postgres://...'
#   ./scripts/backup_postgres.sh
# Hoặc cron:
#   0 3 * * * cd /var/www/moora && ./scripts/backup_postgres.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/hoshi_${STAMP}.sql.gz"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "Cần DATABASE_URL" >&2
  exit 1
fi

echo "Backup → $OUT"
if command -v docker >/dev/null && docker ps --format '{{.Names}}' | grep -qx moora-postgres; then
  docker exec moora-postgres pg_dump -U hoshi -d hoshi | gzip > "$OUT"
else
  # cần pg_dump trên PATH
  pg_dump "$DATABASE_URL" | gzip > "$OUT"
fi

# Xóa bản cũ hơn 14
ls -1t "$BACKUP_DIR"/hoshi_*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
echo "OK $OUT"
echo "Restore ví dụ: gunzip -c $OUT | psql \"\$DATABASE_URL\""
