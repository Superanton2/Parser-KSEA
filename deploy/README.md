# Deployment — daily automated run

The parser is meant to run **once per day** on your server. Because the free
Google Custom Search quota (~100 queries/day) is smaller than a full run needs,
a run that hits the quota checkpoints its progress to `search_state.json` and
exits cleanly; the next day's run resumes the remaining queries automatically.
Only when **all** queries finish does it sort, push to Sheets/Drive, and clear
the checkpoint.

## Option A — systemd timer (recommended on a VM / host)

1. Copy the project to the server, e.g. `/opt/parser-ksea`, and create a venv:
   ```bash
   cd /opt/parser-ksea
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   ```
2. Put `credentials.json` (service-account key) in the project dir and create
   `/opt/parser-ksea/.env`:
   ```
   GOOGLE_CREDENTIALS_PATH=/opt/parser-ksea/credentials.json
   SPREADSHEET_NAME=KSE_Agrocenter_Parser
   SEARCH_STATE_PATH=/opt/parser-ksea/search_state.json
   ```
3. Edit `WorkingDirectory`, `ExecStart`, and `User` in `ksea-parser.service` to
   match your paths, then install the units:
   ```bash
   sudo cp deploy/ksea-parser.service deploy/ksea-parser.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now ksea-parser.timer
   ```
4. Verify / operate:
   ```bash
   systemctl list-timers ksea-parser.timer   # next scheduled run
   sudo systemctl start ksea-parser.service   # run once now
   journalctl -u ksea-parser.service -f       # follow logs
   ```

## Option B — cron (simplest, e.g. inside a container)

Add to the crontab of the user that owns the project:
```cron
0 4 * * * cd /opt/parser-ksea && /opt/parser-ksea/venv/bin/python main.py >> /var/log/ksea-parser.log 2>&1
```

## Option C — Docker container

If the container itself is the unit of deployment, run the daily schedule from
the host (Option A/B) and invoke `docker exec <container> python main.py`, or
bake a cron daemon into the image. Keep `search_state.json` on a mounted volume
so progress survives container restarts.

## Notes
- Logs also stream to the Google Sheet `Logs` tab via `GoogleSheetsLogHandler`.
- To reduce per-run API calls (and finish in one day), lower `MAX_RESULTS` in
  the `Bot_Params` sheet — each 10 results = 1 API call per query.
