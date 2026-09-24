# Incident Command Dashboard

This is a separate, read-only dashboard for the incident records written by
`alert-action/app.py`. The incident service is not modified.

## Run

From the repository root:

```bash
source alert-action/venv/bin/activate
python dashboard/app.py
```

Open `http://127.0.0.1:5050`.

The default state file is `~/.alert-action/acknowledgements.json`, matching the
incident service. Set `ACK_STATE_FILE` when the service uses another path:

```bash
ACK_STATE_FILE=/var/lib/alert-action/acknowledgements.json python dashboard/app.py
```

Keep `DASHBOARD_HOST=127.0.0.1` and put the service behind an authenticated
reverse proxy in production.
