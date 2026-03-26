# EnergyPlus HVAC-LLM User Interface

Complete web-based user interface for the EnergyPlus HVAC-LLM system. This UI allows users to interact with AI agents to automatically generate HVAC systems for EnergyPlus building models.

## Overview

This UI system consists of:
- **Backend**: Flask REST API with WebSocket support (port 5000)
- **Frontend**: React web application (port 3000)

## Features

✅ **Upload Base IDF Files**: Drag-and-drop interface with validation
✅ **Natural Language Requests**: Describe HVAC systems in plain English
✅ **Real-time Agent Monitoring**: Watch AI agents work via WebSocket
✅ **IDF Preview & Download**: View and download generated files
✅ **Multiple LLM Providers**: Claude, Gemini, Mistral support
✅ **RAG Integration**: Retrieval-Augmented Generation for better results
✅ **Error Correction**: Automatic error detection and fixing

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   React Frontend                         │
│  - File Upload                                          │
│  - HVAC Request Form                                    │
│  - Real-time Progress                                   │
│  - Results Display                                      │
└─────────────────┬───────────────────────────────────────┘
                  │ HTTP/WebSocket
┌─────────────────▼───────────────────────────────────────┐
│                   Flask Backend API                      │
│  - REST Endpoints                                       │
│  - WebSocket Server                                     │
│  - File Management                                      │
│  - Pipeline Service                                     │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              HVAC-LLM Pipeline                          │
│  - Agent 1: HVAC Generator                              │
│  - Agent 1.5: Quick Validator                           │
│  - Agent 3: Error Corrector                             │
│  - RAG Knowledge Base                                   │
│  - EnergyPlus Simulation                                │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- EnergyPlus installed
- All project dependencies (see main `requirements.txt`)

### 1. Install Backend Dependencies

```bash
cd ui/backend
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd ui/frontend
npm install
```

### 3. Start Backend Server

```bash
cd ui/backend
python app.py
```

Backend will run at: `http://localhost:5000`

### 4. Start Frontend Development Server

```bash
cd ui/frontend
npm start
```

Frontend will run at: `http://localhost:3000`

### 5. Open Browser

Navigate to `http://localhost:3000` and start using the interface!

## Usage Workflow

### Step 1: Upload Base IDF File
1. Drag and drop your IDF file (building without HVAC)
2. System validates file and detects zones
3. Click "Continue" when validation succeeds

### Step 2: Configure HVAC Request
1. Write your HVAC request in natural language
   - Example: "Design a VRF system with heat recovery for cold climate"
2. Choose LLM provider (Claude Opus 4.6 recommended)
3. Enable/disable RAG (recommended: enabled)
4. Select zone configuration (auto-detect recommended)
5. Click "Generate HVAC System"

### Step 3: Monitor Pipeline Execution
1. Watch real-time progress updates
2. See which agent is currently working
3. View execution log
4. Wait for completion (typically 2-5 minutes)

### Step 4: View Results
1. Preview generated IDF file
2. Download final IDF
3. View execution details and logs
4. Start a new generation or make modifications

## API Endpoints

### Upload
- `POST /api/upload/idf` - Upload IDF file
- `GET /api/upload/validate/<file_id>` - Validate IDF
- `GET /api/upload/list` - List uploads

### Pipeline
- `POST /api/pipeline/run` - Start pipeline
- `GET /api/pipeline/status/<execution_id>` - Get status
- `POST /api/pipeline/cancel/<execution_id>` - Cancel execution
- `GET /api/pipeline/examples` - Get example requests

### Files
- `GET /api/files/download/<execution_id>` - Download IDF
- `GET /api/files/preview/<execution_id>` - Preview IDF
- `GET /api/files/list/<execution_id>` - List execution files
- `GET /api/files/log/<execution_id>` - Get execution log

### General
- `GET /api/health` - Health check
- `GET /api/config` - Get configuration

## WebSocket Events

Real-time progress updates:

```javascript
socket.on('pipeline_progress', (data) => {
  // data = {
  //   execution_id: "...",
  //   step: "agent1_generation",
  //   progress: 35,
  //   message: "Generating HVAC...",
  //   details: {...},
  //   timestamp: "2026-03-25T10:30:00"
  // }
});
```

## Configuration

### Backend Configuration (`backend/config.py`)

```python
# Upload settings
UPLOAD_FOLDER = "ui/backend/uploads"
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

# Output settings
OUTPUT_FOLDER = "outputs/ui_generated"

# Pipeline settings
DEFAULT_RAG_ENABLED = True
DEFAULT_LLM_PROVIDER = 'claude-opus-4.6'
PIPELINE_TIMEOUT = 600  # 10 minutes

# CORS settings
CORS_ORIGINS = ['http://localhost:3000']
```

### Frontend Configuration (`frontend/package.json`)

```json
{
  "proxy": "http://localhost:5000"
}
```

## Production Deployment

### Backend (Flask)

Use a production WSGI server like Gunicorn with eventlet:

```bash
pip install gunicorn eventlet
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 ui.backend.app:app
```

Or use the built-in production mode:

```bash
export FLASK_ENV=production
python ui/backend/app.py
```

### Frontend (React)

Build optimized production bundle:

```bash
cd ui/frontend
npm run build
```

Serve with a web server (nginx, Apache, etc.) or use serve:

```bash
npm install -g serve
serve -s build -l 3000
```

## Directory Structure

```
ui/
├── backend/
│   ├── app.py                  # Main Flask app
│   ├── config.py              # Configuration
│   ├── requirements.txt       # Python dependencies
│   ├── routes/                # API routes
│   │   ├── upload.py
│   │   ├── pipeline.py
│   │   └── files.py
│   ├── services/              # Business logic
│   │   └── pipeline_service.py
│   ├── uploads/               # Uploaded files (created on start)
│   └── README.md
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUpload.js
│   │   │   ├── HVACRequestForm.js
│   │   │   ├── PipelineMonitor.js
│   │   │   └── ResultsDisplay.js
│   │   ├── App.js
│   │   ├── index.js
│   │   └── index.css
│   ├── package.json
│   └── README.md
│
└── README.md (this file)
```

## Troubleshooting

### Backend Issues

**Issue**: Backend won't start
**Solution**: Ensure all dependencies installed, check Python version (3.8+)

**Issue**: CORS errors
**Solution**: Update `CORS_ORIGINS` in `backend/config.py`

**Issue**: Pipeline fails
**Solution**: Check EnergyPlus installation, API keys (for LLM providers), and file permissions

### Frontend Issues

**Issue**: Frontend won't start
**Solution**: Run `npm install`, check Node.js version (16+)

**Issue**: WebSocket connection fails
**Solution**: Ensure backend is running, check CORS settings

**Issue**: Upload fails
**Solution**: Check file size (<50MB), file extension (.idf), backend upload folder permissions

## Example Request

Here's a complete example using curl:

```bash
# 1. Upload IDF
curl -X POST http://localhost:5000/api/upload/idf \
  -F "file=@building.idf"

# Response: {"file_id": "550e8400-...", ...}

# 2. Run Pipeline
curl -X POST http://localhost:5000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "550e8400-...",
    "user_request": "Design VRF system with heat recovery",
    "use_rag": true,
    "llm_provider": "claude-opus-4.6"
  }'

# Response: {"execution_id": "123e4567-...", ...}

# 3. Download Result
curl -O http://localhost:5000/api/files/download/123e4567-...
```

## Support

For issues, questions, or contributions:
- Check the main project documentation in `/docs`
- Review backend README: `ui/backend/README.md`
- Review frontend README: `ui/frontend/README.md`

## License

Part of the EnergyPlus HVAC-LLM Research Project
