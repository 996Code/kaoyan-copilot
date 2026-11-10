#!/bin/bash
# kaoyan 库备份：pg_dump → gzip → backups/，保留最近 14 份
# 用法（服务器）：bash backup_db.sh
# 本地（postgres 超级用户叫 root）：PGUSER=root bash backup_db.sh
# 建议 crontab：0 4 * * * cd /data/kaoyan-copilot/src && bash backup_db.sh >> /data/kaoyan-copilot/backups/backup.log 2>&1

set -euo pipefail
cd "$(dirname "$0")"

PGUSER="${PGUSER:-postgres}"
PGCONTAINER="${PGCONTAINER:-postgres}"
DB="${DB:-kaoyan}"
KEEP="${KEEP:-14}"
OUT_DIR="${OUT_DIR:-../backups}"

mkdir -p "$OUT_DIR"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="$OUT_DIR/kaoyan-$STAMP.sql.gz"

docker exec "$PGCONTAINER" pg_dump -U "$PGUSER" "$DB" | gzip > "$OUT"
echo "[backup] $OUT ($(du -h "$OUT" | cut -f1))"

# 轮转：只留最近 KEEP 份
ls -1t "$OUT_DIR"/kaoyan-*.sql.gz 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r f; do
  rm -f "$f"
  echo "[backup] 轮转删除 $f"
done

# 恢复方法（写在备份里提醒未来的自己）：
#   gunzip -c kaoyan-xxx.sql.gz | docker exec -i $PGCONTAINER psql -U $PGUSER kaoyan
