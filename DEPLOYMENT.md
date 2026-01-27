# MailMind Deployment Guide

## Docker Deployment (Recommended)

### Quick Start

1. **Build and run with docker-compose:**
   ```bash
   docker-compose up -d
   ```

2. **View logs:**
   ```bash
   docker-compose logs -f mailmind
   ```

3. **Stop the service:**
   ```bash
   docker-compose down
   ```

### Manual Docker Build

```bash
# Build the image
docker build -t mailmind:latest .

# Run the container
docker run -d \
  --name mailmind \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  mailmind:latest
```

---

## Systemd Deployment (Linux)

### Installation Steps

1. **Create mailmind user:**
   ```bash
   sudo useradd -r -s /bin/false mailmind
   ```

2. **Create directories:**
   ```bash
   sudo mkdir -p /opt/mailmind/data
   sudo mkdir -p /var/log/mailmind
   sudo chown -R mailmind:mailmind /opt/mailmind
   sudo chown -R mailmind:mailmind /var/log/mailmind
   ```

3. **Copy files:**
   ```bash
   sudo cp mailmind.py /opt/mailmind/
   sudo cp config.json /opt/mailmind/
   sudo cp .env /opt/mailmind/
   sudo cp requirements.txt /opt/mailmind/
   ```

4. **Create virtual environment:**
   ```bash
   cd /opt/mailmind
   sudo -u mailmind python3 -m venv venv
   sudo -u mailmind venv/bin/pip install -r requirements.txt
   ```

5. **Install systemd service:**
   ```bash
   sudo cp mailmind.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable mailmind
   sudo systemctl start mailmind
   ```

6. **Check status:**
   ```bash
   sudo systemctl status mailmind
   sudo journalctl -u mailmind -f
   ```

---

## Environment Setup

Before deploying, ensure your `.env` file is properly configured:

```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

---

## Monitoring

### Docker

```bash
# View logs
docker-compose logs -f

# Check resource usage
docker stats mailmind

# Restart service
docker-compose restart
```

### Systemd

```bash
# View logs
sudo journalctl -u mailmind -f

# Restart service
sudo systemctl restart mailmind

# Stop service
sudo systemctl stop mailmind
```

---

## Backup

### Database Backup

```bash
# Docker
docker exec mailmind cp /app/data/mailmind.db /app/data/mailmind.db.backup

# Systemd
sudo cp /opt/mailmind/data/mailmind.db /opt/mailmind/data/mailmind.db.backup
```

### Automated Backups

Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * docker exec mailmind cp /app/data/mailmind.db /app/data/mailmind-$(date +\%Y\%m\%d).db
```

---

## Troubleshooting

### Docker Issues

**Container won't start:**
```bash
docker-compose logs mailmind
docker-compose down && docker-compose up -d
```

**Permission issues:**
```bash
sudo chown -R 1000:1000 data/ logs/
```

### Systemd Issues

**Service fails to start:**
```bash
sudo journalctl -u mailmind -n 50
sudo systemctl status mailmind
```

**Permission denied:**
```bash
sudo chown -R mailmind:mailmind /opt/mailmind
```

---

## Updating

### Docker

```bash
docker-compose down
git pull
docker-compose build
docker-compose up -d
```

### Systemd

```bash
sudo systemctl stop mailmind
cd /opt/mailmind
sudo -u mailmind git pull
sudo -u mailmind venv/bin/pip install -r requirements.txt
sudo systemctl start mailmind
```
