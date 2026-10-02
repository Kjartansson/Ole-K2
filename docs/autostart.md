# Autostart (optional)

## Linux (systemd user unit)

```ini
# ~/.config/systemd/user/ole-k2.service
[Unit]
Description=Ole K2 bridge server (loopback only)

[Service]
ExecStart=/PATH/TO/Ole-K2/.venv/bin/python /PATH/TO/Ole-K2/server.py
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now ole-k2
```

## macOS / Windows

Run `.venv/bin/python server.py` in a terminal, or wrap it in launchd /
Task Scheduler if you want it permanent.
