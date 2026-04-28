# Deployment Guide - masternoder.dk

**Last Updated:** 2025-12-17

---

## 🚀 Quick Deployment

### Automated Deployment

```bash
python deploy.py
```

This script will:
- Scan for changed files
- Upload files via SFTP to server
- Restart services (uWSGI, Python proxy)
- Verify deployment status

### Manual Deployment Steps

1. **Upload Files**
   ```bash
   # Using deploy.py script
   python deploy.py
   ```

2. **Restart Services** (if needed manually)
   ```bash
   ssh root@masternoder.dk
   sudo systemctl restart uwsgi-vidgenerator.service
   sudo systemctl restart python-proxy.service
   ```

3. **Verify Deployment**
   ```bash
   # Check service status
   sudo systemctl status uwsgi-vidgenerator.service
   sudo systemctl status python-proxy.service
   ```

---

## 📋 Pre-Deployment Checklist

- [ ] All tests passing locally
- [ ] Code reviewed
- [ ] Database migrations run (if any)
- [ ] Environment variables updated (if needed)
- [ ] API keys configured (if needed)
- [ ] Static files compiled/optimized (if needed)

---

## 🔧 Configuration

### Environment Variables

Configure in `.env` file on server:
```bash
RUNWAYML_API_KEY=your_key
PIKA_LABS_API_KEY=your_key
STABILITY_AI_API_KEY=your_key
OPENAI_API_KEY=your_key
```

### Database

Database location: `/var/www/html/vidgenerator/documentaries.db`

Permissions:
```bash
sudo chown www-data:www-data /var/www/html/vidgenerator/*.db
sudo chmod 664 /var/www/html/vidgenerator/*.db
```

### Output Directories

Video output directories:
```bash
sudo mkdir -p /var/www/html/vidgenerator/output/videos/clips
sudo mkdir -p /var/www/html/vidgenerator/output/videos/thumbnails
sudo chown -R www-data:www-data /var/www/html/vidgenerator/output
sudo chmod -R 775 /var/www/html/vidgenerator/output
```

---

## 🔄 Rollback Procedure

### Quick Rollback

1. **Restore from backup**
   ```bash
   ssh root@masternoder.dk
   cd /var/www/html/vidgenerator
   # Restore from backup (if exists)
   ```

2. **Restart services**
   ```bash
   sudo systemctl restart uwsgi-vidgenerator.service
   sudo systemctl restart python-proxy.service
   ```

### Git-based Rollback

```bash
# On local machine
git checkout <previous-commit>
python deploy.py
```

---

## 📊 Monitoring

### Check Service Status

```bash
ssh root@masternoder.dk
sudo systemctl status uwsgi-vidgenerator.service
sudo systemctl status python-proxy.service
```

### Check Logs

```bash
# uWSGI logs
sudo journalctl -u uwsgi-vidgenerator.service -f

# Python proxy logs
sudo journalctl -u python-proxy.service -f

# Apache logs
sudo tail -f /var/log/apache2/error.log
sudo tail -f /var/log/apache2/access.log
```

### Test Endpoints

```bash
# Health check
curl https://masternoder.dk/vidgenerator/api/health

# Test main pages
curl https://masternoder.dk/vidgenerator/game/
curl https://masternoder.dk/vidgenerator/stats/
```

---

## 🔐 Security Notes

### Credentials

- **⚠️ WARNING:** `deploy.py` contains server credentials
- Keep credentials secure
- Consider using environment variables for credentials
- Use SSH keys instead of passwords when possible

### File Permissions

- Ensure proper file permissions on server
- Database files: `www-data` user should have write access
- Output directories: `www-data` user should have write access

---

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status uwsgi-vidgenerator.service

# Check logs
sudo journalctl -u uwsgi-vidgenerator.service -n 50

# Try manual start
sudo systemctl start uwsgi-vidgenerator.service
```

### 404 Errors

- Check Apache configuration
- Verify routes are registered in Flask app
- Check blueprint registration

### 500 Errors

- Check application logs
- Verify database permissions
- Check environment variables
- Verify file permissions on output directories

### Database Errors

```bash
# Check database permissions
ls -la /var/www/html/vidgenerator/*.db

# Fix permissions if needed
sudo chown www-data:www-data /var/www/html/vidgenerator/*.db
sudo chmod 664 /var/www/html/vidgenerator/*.db
```

---

## 📝 Deployment History

Track deployments in `docs/DEPLOYMENT_LOG.md`

---

## ✅ Success Indicators

After deployment, verify:
- [ ] All services running
- [ ] Main pages accessible (200 OK)
- [ ] API endpoints responding (200 OK)
- [ ] No errors in logs
- [ ] Static files loading correctly
- [ ] Database operations working
- [ ] Video generation working (if applicable)

---

**For more details, see:** `docs/MASTER_PLAN.md`
