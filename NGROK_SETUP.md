# Ngrok Setup Guide for EnergyPlus HVAC-LLM

This guide will help you expose your application publicly using ngrok.

## Prerequisites

- Frontend running on http://localhost:3000
- Backend running on http://localhost:5000

## Quick Start

### 1. Get your ngrok authtoken

1. Sign up at https://dashboard.ngrok.com/signup
2. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken

### 2. Configure ngrok

Run the setup script and enter your authtoken when prompted:

```bash
./setup_ngrok.sh
```

Or manually add your authtoken to `ngrok.yml`:
```bash
~/bin/ngrok config add-authtoken YOUR_TOKEN_HERE
```

### 3. Start your services

Make sure both frontend and backend are running:

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

### 4. Start ngrok tunnels

**Terminal 3 - Ngrok:**
```bash
./start_ngrok.sh
```

### 5. Get your public URLs

After ngrok starts, open a new terminal and run:
```bash
./get_public_urls.sh
```

This will display your public URLs that you can share with others.

## Important Notes

### Frontend Configuration

Your React frontend has a proxy configured to `http://localhost:5000`. When accessing the app via ngrok:

- Users should access the **frontend URL** (port 3000)
- The frontend will handle API requests to the backend

### Ngrok Dashboard

View live requests and inspect traffic at:
- http://localhost:4040

### Free Plan Limitations

- 1 account per user
- 1 online ngrok process (but multiple tunnels)
- 40 connections/minute
- Random URLs (changes every restart)
- Tunnels expire after 2 hours

### Upgrade for Better Features

For persistent URLs and longer sessions, consider upgrading to a paid plan:
- https://ngrok.com/pricing

## Usage Examples

### Share with users:
```
Frontend: https://abc123.ngrok-free.app
```

Users can access your full application through this single URL!

### For API testing only:
```
Backend: https://xyz456.ngrok-free.app
```

## Troubleshooting

### "Cannot connect to ngrok API"
- Make sure ngrok is running (`./start_ngrok.sh`)
- Wait a few seconds for ngrok to start

### "Authtoken not configured"
- Run `./setup_ngrok.sh` to add your authtoken
- Or update `ngrok.yml` with your token

### Backend connection issues
- Make sure backend is running on port 5000
- Check `backend.log` for errors

### Frontend connection issues
- Make sure frontend is running on port 3000
- Check `frontend.log` for errors

## Scripts Reference

- `setup_ngrok.sh` - Configure ngrok authtoken
- `start_ngrok.sh` - Start ngrok tunnels
- `get_public_urls.sh` - Display public URLs
- `ngrok.yml` - Ngrok configuration file

## Security Notes

- Don't commit your authtoken to git
- Consider adding authentication to your app
- Monitor the ngrok dashboard for suspicious activity
- Use HTTPS URLs only (provided by default)

## Alternative: Using ngrok directly

If you prefer manual control:

```bash
# Expose frontend only
~/bin/ngrok http 3000

# Expose backend only
~/bin/ngrok http 5000

# Expose both (requires config file)
~/bin/ngrok start --all --config ngrok.yml
```

## Need Help?

- Ngrok documentation: https://ngrok.com/docs
- Check ngrok dashboard: http://localhost:4040
