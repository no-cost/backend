#!/bin/bash
# Archives a tenant's own data and its database dump into <backup_dir>.tar.gz:
#
#   <name>/files/app/public/...                   site files (uploads, assets, ...)
#   <name>/files/app/storage/private-shared/...   FoF Upload private files (Flarum)
#   <name>/files/etc/config.json                  unless include_private is 0
#   <name>/files/logs/...                         unless include_private is 0
#   <name>/database.sql, <name>/README.md         written into <backup_dir> beforehand
#
# where <name> is the basename of <backup_dir>.
#
# Files are streamed into the archive straight from the tenant directory (no intermediate copy),
# compressed with the fastest gzip level. Bind mounts and files hardlinked from the skeleton are
# shared by all tenants, so they are skipped.
#
# usage: backup_tenant.sh <tenant_dir> <backup_dir> <include_private: 1|0>
set -euo pipefail

tenant_dir=${1%/}
backup_dir=${2%/}
include_private=$3

parent=$(dirname "$backup_dir")
name=$(basename "$backup_dir")
list="$backup_dir.files"
archive="$backup_dir.tar.gz"

# <backup_dir>/files -> <tenant_dir>, so archive members get their final names without copying anything
ln -sfn "$tenant_dir" "$backup_dir/files"
trap 'rm -f "$list" "$archive.part" "$backup_dir/files"' EXIT

paths=(app/public app/storage/private-shared)
if [ "$include_private" = 1 ]; then
    paths+=(etc/config.json logs)
fi

# bind mounts inside the tenant (exact "<tenant_dir>/" prefix, so tenant `abc` never matches `abcd`)
prune=()
if [ -r /proc/mounts ]; then
    while IFS= read -r mount; do
        prune+=(-path "$name/files/${mount#"$tenant_dir"/}" -prune -o)
    done < <(awk -v prefix="$tenant_dir/" 'index($2, prefix) == 1 {print $2}' /proc/mounts)
fi

cd "$parent"
: > "$list"
for path in "${paths[@]}"; do
    [ -e "$name/files/$path" ] || continue
    find "$name/files/$path" ${prune[@]+"${prune[@]}"} \( -type f -links +1 \) -o -print0 >> "$list"
done
for extra in database.sql README.md; do
    if [ -e "$name/$extra" ]; then
        printf '%s\0' "$name/$extra" >> "$list"
    fi
done

# tar exits with 1 when a file changed while being read (e.g. a log being written), that's fine
set +e
tar --create --null --no-recursion --ignore-failed-read --files-from="$list" | gzip -1 > "$archive.part"
statuses=("${PIPESTATUS[@]}")
set -e
if [ "${statuses[0]}" -gt 1 ] || [ "${statuses[1]}" -ne 0 ]; then
    echo "archiving failed (tar: ${statuses[0]}, gzip: ${statuses[1]})" >&2
    exit 1
fi

mv "$archive.part" "$archive"
