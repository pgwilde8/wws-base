# systemd Basics Guide for Green Candle Dispatch

Quick reference for managing the `dispatch.service` systemd unit.

---

## Quick Start

### One-Time Setup

```bash
# Copy service file to systemd
sudo cp /srv/projects/client/dispatch/deploy/dispatch.service /etc/systemd/system/

# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable dispatch

# Start the service now
sudo systemctl start dispatch

# Check status
sudo systemctl status dispatch
```

---

## Essential Commands

### Service Control

```bash
# Start service
sudo systemctl start dispatch

# Stop service
sudo systemctl stop dispatch

# Restart service (stops then starts)
sudo systemctl restart dispatch

# Reload service (if supported - sends SIGHUP, doesn't restart)
sudo systemctl reload dispatch

# Check if service is running
sudo systemctl is-active dispatch

# Check if service is enabled (starts on boot)
sudo systemctl is-enabled dispatch

# Enable service to start on boot
sudo systemctl enable dispatch

# Disable service from starting on boot
sudo systemctl disable dispatch

# Show service status (detailed)
sudo systemctl status dispatch
```

### Viewing Logs

```bash
# Follow logs in real-time (like tail -f)
sudo journalctl -u dispatch -f

# View last 50 lines
sudo journalctl -u dispatch -n 50

# View logs since today
sudo journalctl -u dispatch --since today

# View logs since specific time
sudo journalctl -u dispatch --since "2024-01-15 10:00:00"

# View logs with timestamps
sudo journalctl -u dispatch --since "1 hour ago"

# View only errors
sudo journalctl -u dispatch -p err

# View logs from last boot
sudo journalctl -u dispatch -b

# Export logs to file
sudo journalctl -u dispatch > dispatch-logs.txt
```

### Service Information

```bash
# Show service file location
systemctl show dispatch -p FragmentPath

# Show all service properties
systemctl show dispatch

# Show environment variables
systemctl show dispatch -p Environment

# Show working directory
systemctl show dispatch -p WorkingDirectory

# Show main PID
systemctl show dispatch -p MainPID
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check status for error messages
sudo systemctl status dispatch

# Check logs for errors
sudo journalctl -u dispatch -n 100

# Verify service file syntax
sudo systemd-analyze verify dispatch.service

# Check if port 8990 is already in use
sudo lsof -i :8990
# or
sudo netstat -tulpn | grep 8990

# Test the command manually
cd /srv/projects/client/dispatch
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8990
```

### Service Keeps Restarting

```bash
# Check why it's failing
sudo journalctl -u dispatch -n 100 --no-pager

# Check restart count
systemctl show dispatch -p NRestarts

# Temporarily disable auto-restart to debug
# Edit service file, change Restart=always to Restart=no
sudo systemctl edit dispatch
# Then restart
sudo systemctl daemon-reload
sudo systemctl restart dispatch
```

### Service File Issues

```bash
# Validate service file syntax
sudo systemd-analyze verify /etc/systemd/system/dispatch.service

# Check for conflicts
sudo systemd-analyze verify dispatch.service

# Reload after editing service file
sudo systemctl daemon-reload
sudo systemctl restart dispatch
```

### Permission Issues

```bash
# Check who owns the files
ls -la /srv/projects/client/dispatch

# Check if .env file is readable
cat /srv/projects/client/dispatch/.env

# If running as non-root user, check permissions
sudo -u dispatch ls -la /srv/projects/client/dispatch
```

---

## Editing the Service File

### Method 1: Edit and Reload

```bash
# Edit the service file
sudo nano /etc/systemd/system/dispatch.service

# After editing, reload systemd
sudo systemctl daemon-reload

# Restart the service
sudo systemctl restart dispatch
```

### Method 2: Use systemctl edit (Recommended)

```bash
# Creates override file (doesn't modify original)
sudo systemctl edit dispatch

# This creates: /etc/systemd/system/dispatch.service.d/override.conf
# Add only the settings you want to override

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart dispatch
```

### Method 3: Edit Source and Reinstall

```bash
# Edit the source file
nano /srv/projects/client/dispatch/deploy/dispatch.service

# Copy updated file
sudo cp /srv/projects/client/dispatch/deploy/dispatch.service /etc/systemd/system/

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart dispatch
```

---

## Common Service File Settings

### Restart Behavior

```ini
# Always restart on failure
Restart=always

# Restart only on failure (not on normal exit)
Restart=on-failure

# Never restart
Restart=no

# Wait 5 seconds before restarting
RestartSec=5
```

### Environment Variables

```ini
# Load from file (dash means don't fail if file missing)
EnvironmentFile=-/srv/projects/client/dispatch/.env

# Set specific variable
Environment=PORT=8990

# Multiple variables
Environment="VAR1=value1" "VAR2=value2"
```

### User/Group

```ini
# Run as specific user
User=dispatch
Group=dispatch

# Create user first:
# sudo useradd -r -s /bin/false dispatch
```

### Working Directory

```ini
# Set working directory
WorkingDirectory=/srv/projects/client/dispatch
```

### Logging

```ini
# Redirect stdout/stderr to journal
StandardOutput=journal
StandardError=journal

# Or to file
StandardOutput=file:/var/log/dispatch.log
StandardError=file:/var/log/dispatch-error.log
```

---

## Useful systemd Commands (General)

```bash
# List all services
systemctl list-units --type=service

# List all enabled services
systemctl list-unit-files --type=service --state=enabled

# List failed services
systemctl --failed

# Check systemd status
systemctl status

# Reload all systemd configs
sudo systemctl daemon-reload

# Check boot time
systemd-analyze

# See what's slowing boot
systemd-analyze blame
```

---

## Monitoring & Health Checks

### Check if Service is Healthy

```bash
# Quick health check script
#!/bin/bash
if systemctl is-active --quiet dispatch; then
    echo "✅ Service is running"
    # Test HTTP endpoint
    curl -f http://localhost:8990/ > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ HTTP endpoint responding"
    else
        echo "❌ HTTP endpoint not responding"
    fi
else
    echo "❌ Service is not running"
fi
```

### Set Up Monitoring

```bash
# Create a simple health check script
cat > /usr/local/bin/check-dispatch.sh << 'EOF'
#!/bin/bash
if ! systemctl is-active --quiet dispatch; then
    echo "ALERT: dispatch service is down!"
    # Send alert (email, Slack, etc.)
fi
EOF

chmod +x /usr/local/bin/check-dispatch.sh

# Add to crontab to check every minute
# crontab -e
# * * * * * /usr/local/bin/check-dispatch.sh
```

---

## Backup & Recovery

### Backup Service File

```bash
# Backup current service file
sudo cp /etc/systemd/system/dispatch.service /etc/systemd/system/dispatch.service.backup

# Restore from backup
sudo cp /etc/systemd/system/dispatch.service.backup /etc/systemd/system/dispatch.service
sudo systemctl daemon-reload
sudo systemctl restart dispatch
```

---

## Quick Reference Card

```bash
# START/STOP
sudo systemctl start dispatch      # Start
sudo systemctl stop dispatch       # Stop
sudo systemctl restart dispatch    # Restart
sudo systemctl reload dispatch      # Reload (if supported)

# STATUS
sudo systemctl status dispatch     # Detailed status
sudo systemctl is-active dispatch  # Quick check

# ENABLE/DISABLE (boot)
sudo systemctl enable dispatch      # Enable on boot
sudo systemctl disable dispatch     # Disable on boot
sudo systemctl is-enabled dispatch  # Check if enabled

# LOGS
sudo journalctl -u dispatch -f     # Follow logs
sudo journalctl -u dispatch -n 50  # Last 50 lines
sudo journalctl -u dispatch --since "1 hour ago"

# TROUBLESHOOTING
sudo systemctl status dispatch      # Check status
sudo journalctl -u dispatch -n 100 # Check logs
sudo systemd-analyze verify dispatch.service  # Validate config
```

---

## Pro Tips

1. **Always reload after editing**: `sudo systemctl daemon-reload`
2. **Check logs first**: `journalctl -u dispatch -f` when debugging
3. **Use `systemctl edit`**: Creates override files without modifying original
4. **Test manually first**: Run the command manually before adding to systemd
5. **Check dependencies**: Make sure database, Redis, etc. are running first
6. **Monitor logs**: Set up log rotation if logs get large
7. **Use `-f` flag**: `journalctl -u dispatch -f` to follow logs in real-time

---

## Example: Complete Workflow

```bash
# 1. Install service
sudo cp /srv/projects/client/dispatch/deploy/dispatch.service /etc/systemd/system/
sudo systemctl daemon-reload

# 2. Enable and start
sudo systemctl enable dispatch
sudo systemctl start dispatch

# 3. Verify it's running
sudo systemctl status dispatch

# 4. Check logs
sudo journalctl -u dispatch -f

# 5. Test endpoint
curl http://localhost:8990/

# 6. If something breaks, check logs
sudo journalctl -u dispatch -n 100 --no-pager

# 7. Restart if needed
sudo systemctl restart dispatch
```

---

## Related Files

- Service file: `/etc/systemd/system/dispatch.service`
- Source: `/srv/projects/client/dispatch/deploy/dispatch.service`
- Logs: `journalctl -u dispatch`
- App directory: `/srv/projects/client/dispatch`
- Environment: `/srv/projects/client/dispatch/.env`
