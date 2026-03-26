# Quick Start Guide - HVAC-LLM UI

## 🚀 Fast Setup (5 minutes)

### Step 1: Install Backend Dependencies

Run from project root:

```bash
pip install Flask flask-cors flask-socketio werkzeug python-socketio eventlet python-engineio
```

Or install from requirements file:

```bash
pip install -r ui/backend/requirements.txt
```

### Step 2: Install Frontend Dependencies

```bash
cd ui/frontend
npm install
cd ../..
```

### Step 3: Make Scripts Executable

```bash
chmod +x ui/setup.sh
chmod +x ui/start.sh
```

### Step 4: Start the UI

**Option A - Automated (Recommended):**
```bash
./ui/start.sh
```

**Option B - Manual:**

Terminal 1 (Backend):
```bash
cd ui/backend
python app.py
```

Terminal 2 (Frontend):
```bash
cd ui/frontend
npm start
```

### Step 5: Open in Browser

Navigate to: **http://localhost:3000**

---

## ✅ Verify Installation

### Test Backend

```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "EnergyPlus HVAC-LLM API",
  "version": "1.0.0"
}
```

### Test Frontend

Open browser to `http://localhost:3000` - you should see:
- Upload IDF step
- Material-UI interface
- "EnergyPlus HVAC-LLM Interface" header

---

## 🐛 Troubleshooting

### Backend won't start?

**Error: `ModuleNotFoundError: No module named 'flask'`**
```bash
pip install Flask flask-cors flask-socketio eventlet
```

**Error: Port 5000 already in use**
```bash
# Find process using port 5000
lsof -i :5000
# Kill it
kill -9 <PID>
```

**Error: Import errors**
- Make sure you're running from project root
- Check that `__init__.py` files exist in backend directories

### Frontend won't start?

**Error: `npm: command not found`**
```bash
# Install Node.js 16+ from nodejs.org or:
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Error: Port 3000 already in use**
```bash
# Find and kill process
lsof -i :3000
kill -9 <PID>
```

**Error: `package.json not found`**
- Make sure you're in `ui/frontend` directory
- Check that `package.json` file exists

### WebSocket connection fails?

1. Check backend is running: `curl http://localhost:5000/api/health`
2. Check CORS settings in `ui/backend/config.py`
3. Clear browser cache
4. Try different browser

### Pipeline execution fails?

1. **Check LLM API Keys**:
   - Claude: Set API key in `config/settings.py`
   - Gemini: Set API key
   - Mistral: Check model paths

2. **Check EnergyPlus**:
   ```bash
   # Verify EnergyPlus is installed
   ls ~/Documents/Ayeen/Energy+
   ```

3. **Check permissions**:
   ```bash
   # Make sure output directories are writable
   ls -la outputs/
   ```

---

## 📦 Dependencies Summary

### Backend (Python)
- Flask ✓
- flask-cors ✓
- flask-socketio ✓
- werkzeug ✓
- python-socketio ✓
- eventlet ✓
- python-engineio ✓
- (plus all existing project dependencies)

### Frontend (Node.js)
- react ✓
- react-dom ✓
- axios ✓
- socket.io-client ✓
- @mui/material ✓
- react-dropzone ✓
- react-syntax-highlighter ✓

---

## 🎯 First Time Usage

After setup is complete:

1. **Upload a Test IDF**:
   - Use one from `data/base_idfs/`
   - Example: `SmallOffice.idf`

2. **Try an Example Request**:
   - Click on any example card
   - Or type: "Design a VRF system with heat recovery for office building"

3. **Watch the Agents Work**:
   - See real-time progress
   - Agent 1, 1.5, and 3 indicators
   - Live execution log

4. **Download Result**:
   - Preview the IDF
   - Download button
   - Check `outputs/ui_generated/`

---

## 💡 Tips

- **Use Chrome or Firefox** for best compatibility
- **Enable RAG** for better results
- **Claude Opus 4.6** recommended as LLM provider
- **Check logs** in `backend.log` and `frontend.log`
- **Keep terminal open** to see server output

---

## 📚 More Help

- Backend API: See `ui/backend/README.md`
- Frontend: See `ui/frontend/README.md`
- Main docs: See `ui/README.md`

---

## 🔥 Quick Command Reference

```bash
# Full setup from scratch
pip install Flask flask-cors flask-socketio eventlet
cd ui/frontend && npm install && cd ../..
chmod +x ui/*.sh

# Start UI
./ui/start.sh

# Stop UI
# Press Ctrl+C in the terminal running start.sh

# Check backend health
curl http://localhost:5000/api/health

# View logs
tail -f backend.log
tail -f frontend.log

# Clean reinstall frontend
cd ui/frontend
rm -rf node_modules package-lock.json
npm install
cd ../..
```

---

## ✨ You're Ready!

Open **http://localhost:3000** and start generating HVAC systems!
