#!/bin/sh
# sunset_code's __main__ runs one day's capture cycle then exits (it's
# normally re-triggered daily by a systemd timer). This loop makes the
# container self-sufficient: after a cycle finishes -- either because it
# captured today's intervals or because they've already all passed -- wait
# an hour and check again, so it naturally picks up the next day's cycle
# without needing cron/systemd inside the container.
set -e

while true; do
  python -m sunset_code
  echo "[entrypoint] cycle finished, sleeping 1h before re-checking intervals"
  sleep 3600
done
