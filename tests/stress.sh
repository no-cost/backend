#!/usr/bin/env bash
set -euo pipefail

# stress test script: create sites until health check fails
# must be run after deploying full platform, e.g. in `screen -R stress; ~/stress.sh | tee ~/stress.log`
# first arg represents starting site number (inclusive), to resume previous run

APPS=(flarum mediawiki wordpress)
START=${1:-1}
created=0
i=$START

while true; do
    for app in "${APPS[@]}"; do
        tag="${app}${i}"
        echo "[$(date +%H:%M:%S)] creating: $tag"

        if create_site "$tag" "$app" "info+${tag}@no-cost.site" --no-send-email; then
            created=$(( created + 1 ))
        else
            echo "[$(date +%H:%M:%S)] $tag failed (exit $?), stopping"
            echo "created: $created (started from #$START)"
            exit 1
        fi
    done
    i=$(( i + 1 ))
done
