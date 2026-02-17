# Deploy: Dispatch on systemd (port 8990)

## Quick Start

1. **Install the unit**
   ```bash
   sudo cp /srv/projects/client/dispatch/deploy/dispatch.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

2. **Enable and start**
   ```bash
   sudo systemctl enable dispatch
   sudo systemctl start dispatch
   sudo systemctl status dispatch
   ```

## Essential Commands

- **Start:** `sudo systemctl start dispatch`
- **Stop:** `sudo systemctl stop dispatch`
- **Restart:** `sudo systemctl restart dispatch`
- **Status:** `sudo systemctl status dispatch`
- **Logs:** `journalctl -u dispatch -f`

## Full Documentation

For complete systemd guide with troubleshooting, see: **[systemd-basics.md](./systemd-basics.md)**

## Notes

- Nginx should proxy to `127.0.0.1:8990` (see `/etc/nginx/sites-available/greencandledispatch.com`)
- Service auto-restarts on failure (configured in service file)
- Logs are available via `journalctl -u dispatch`
