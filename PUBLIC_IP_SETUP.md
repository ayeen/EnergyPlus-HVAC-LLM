# Public IP Access Setup Guide

## Your Public IP: **163.180.125.76**

This guide will help you share your application via your system's public IP address.

---

## 🚀 Quick Start

### Step 1: Open Firewall Ports (One-time setup)

```bash
./open_firewall.sh
```

This opens ports 3000 (Frontend) and 5000 (Backend) in your firewall.

### Step 2: Restart Your Services

Since we updated the configuration, restart both services:

**Terminal 1 - Backend:**
```bash
cd ui/backend
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd ui/frontend
npm start
```

### Step 3: Check Status

```bash
./check_public_access.sh
```

This will show:
- Your public IP
- Service status
- Firewall configuration
- Public URLs

---

## 🌐 Your Public URLs

### For Users (Share this!)
**Frontend:** http://163.180.125.76:3000

Users only need this URL to access your full application!

### For API Testing
**Backend:** http://163.180.125.76:5000

Direct API endpoint access (health check: http://163.180.125.76:5000/api/health)

---

## 📋 What Was Changed

### 1. Backend Configuration (`ui/backend/backend_config.py`)
- Added your public IP to CORS_ORIGINS
- Allows cross-origin requests from your public IP

### 2. Frontend Configuration (`ui/frontend/.env`)
- Added `HOST=0.0.0.0` to listen on all interfaces
- Frontend now accepts connections from external IPs

### 3. Frontend Package Script (`ui/frontend/package.json`)
- Updated start script to use `HOST=0.0.0.0`
- Ensures React dev server is publicly accessible

---

## 🔒 Security Considerations

1. **Development Server Warning**
   - You're using development servers (Flask debug mode and React dev server)
   - These are NOT recommended for production use
   - Consider using production servers (Gunicorn, Nginx) for real deployments

2. **Firewall Configuration**
   - Only ports 3000 and 5000 are opened
   - Consider restricting access to specific IP ranges if needed

3. **Authentication**
   - Currently no authentication is implemented
   - Anyone with the URL can access your application
   - Consider adding authentication for sensitive environments

4. **HTTPS**
   - Currently using HTTP (unencrypted)
   - For production, use HTTPS with SSL certificates

---

## 🔍 Troubleshooting

### Can't Access from External Network

1. **Check if services are running:**
   ```bash
   ./check_public_access.sh
   ```

2. **Verify firewall is open:**
   ```bash
   sudo ufw status
   # or
   sudo firewall-cmd --list-ports
   ```

3. **Test from your local network (another device):**
   ```bash
   curl http://163.180.125.76:5000/api/health
   ```

4. **Check if router/NAT is blocking:**
   - If accessing from outside your local network, you may need to configure port forwarding on your router
   - Ports 3000 and 5000 need to be forwarded to 163.180.125.76

### Frontend Can't Connect to Backend

1. **Check CORS configuration:**
   - Verify `ui/backend/backend_config.py` includes your public IP

2. **Check backend logs:**
   ```bash
   tail -f backend.log
   ```

3. **Test backend directly:**
   ```bash
   curl http://163.180.125.76:5000/api/health
   ```

### Services Not Starting

1. **Backend issues:**
   ```bash
   cd ui/backend
   python app.py
   # Check output for errors
   ```

2. **Frontend issues:**
   ```bash
   cd ui/frontend
   npm start
   # Check output for errors
   ```

---

## 🔄 Restarting Services

After any configuration changes, restart your services:

```bash
# Kill existing processes
pkill -f "python.*app.py"
pkill -f "react-scripts"

# Restart backend
cd ui/backend && python app.py > ../../backend.log 2>&1 &

# Restart frontend
cd ui/frontend && npm start > ../../frontend.log 2>&1 &
```

Or use the provided script:
```bash
./restart_services.sh
```

---

## 📊 Network Information

### Local Access
- Frontend: http://localhost:3000
- Backend: http://localhost:5000

### Public Access (Same Network)
- Frontend: http://163.180.125.76:3000
- Backend: http://163.180.125.76:5000

### External Access (Internet)
If you want to access from outside your local network:
1. Configure port forwarding on your router
2. Forward external ports 3000 and 5000 to internal IP 163.180.125.76
3. Use your external/WAN IP address (check at https://whatismyipaddress.com)

---

## 🎯 For Production Deployment

If you want to deploy this properly for production use:

1. **Use Production Servers:**
   ```bash
   # Backend: Use Gunicorn instead of Flask dev server
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app

   # Frontend: Build and serve with Nginx
   cd ui/frontend
   npm run build
   # Serve build folder with Nginx
   ```

2. **Setup HTTPS:**
   - Get SSL certificate (Let's Encrypt)
   - Configure Nginx as reverse proxy
   - Use HTTPS for all connections

3. **Add Authentication:**
   - Implement user authentication
   - Add API key or JWT tokens
   - Restrict access to authorized users

4. **Setup Process Manager:**
   ```bash
   # Use PM2 or systemd to keep services running
   npm install -g pm2
   pm2 start app.py --name backend
   ```

---

## 📝 Scripts Reference

- `check_public_access.sh` - Check service status and get public URLs
- `open_firewall.sh` - Open required firewall ports
- `restart_services.sh` - Restart both frontend and backend

---

## 🆘 Need Help?

If you encounter issues:
1. Run `./check_public_access.sh` to diagnose
2. Check logs: `backend.log` and `frontend.log`
3. Verify firewall settings
4. Ensure no other services are using ports 3000 or 5000
