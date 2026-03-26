# HVAC-LLM Backend API

Flask API backend for the EnergyPlus HVAC-LLM user interface.

## Features

- **File Upload**: Upload base IDF files (buildings without HVAC)
- **Pipeline Execution**: Run HVAC generation pipeline with real-time progress
- **WebSocket Support**: Real-time agent execution monitoring
- **File Management**: Preview and download generated IDF files

## API Endpoints

### Upload Routes (`/api/upload`)

- `POST /api/upload/idf` - Upload base IDF file
- `GET /api/upload/validate/<file_id>` - Validate uploaded IDF
- `GET /api/upload/list` - List all uploaded files

### Pipeline Routes (`/api/pipeline`)

- `POST /api/pipeline/run` - Execute HVAC generation pipeline
- `GET /api/pipeline/status/<execution_id>` - Get pipeline status
- `POST /api/pipeline/cancel/<execution_id>` - Cancel pipeline execution
- `GET /api/pipeline/list` - List all executions
- `GET /api/pipeline/examples` - Get example HVAC requests

### File Routes (`/api/files`)

- `GET /api/files/download/<execution_id>` - Download generated IDF
- `GET /api/files/preview/<execution_id>` - Preview IDF content
- `GET /api/files/list/<execution_id>` - List all execution files
- `GET /api/files/log/<execution_id>` - Get JSON log

### General Routes

- `GET /api/health` - Health check
- `GET /api/config` - Get configuration

## WebSocket Events

The API emits real-time progress updates via WebSocket:

```javascript
socket.on('pipeline_progress', (data) => {
  console.log(data);
  // {
  //   execution_id: "uuid",
  //   step: "agent1_generation",
  //   progress: 35,
  //   message: "Generating HVAC configuration...",
  //   details: {...},
  //   timestamp: "2026-03-25T10:30:00"
  // }
});
```

## Installation

```bash
cd ui/backend
pip install -r requirements.txt
```

## Running the Server

```bash
# Development mode
python app.py

# Production mode (use gunicorn + eventlet)
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

The API will be available at `http://localhost:5000`

## Configuration

Edit `config.py` to customize:
- Upload folder location
- Output folder location
- CORS origins (for frontend)
- File size limits
- Pipeline timeouts

## Directory Structure

```
backend/
├── app.py                 # Main Flask application
├── config.py             # Configuration
├── requirements.txt      # Dependencies
├── routes/              # API routes
│   ├── upload.py        # File upload endpoints
│   ├── pipeline.py      # Pipeline execution endpoints
│   └── files.py         # File management endpoints
├── services/            # Business logic
│   └── pipeline_service.py  # Pipeline execution service
└── uploads/             # Uploaded IDF files (created on first run)
```

## Usage Example

### 1. Upload IDF File

```bash
curl -X POST http://localhost:5000/api/upload/idf \
  -F "file=@/path/to/building.idf"
```

Response:
```json
{
  "success": true,
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "building.idf",
  "validation": {
    "valid": true,
    "zone_count": 3,
    "zones": ["Zone1", "Zone2", "Zone3"]
  }
}
```

### 2. Run Pipeline

```bash
curl -X POST http://localhost:5000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_request": "Design a VRF system with heat recovery for office building",
    "zones": null,
    "use_rag": true,
    "llm_provider": "claude-opus-4.6"
  }'
```

Response:
```json
{
  "success": true,
  "execution_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Pipeline execution started"
}
```

### 3. Monitor Progress (WebSocket)

Connect to WebSocket and listen for `pipeline_progress` events.

### 4. Download Result

```bash
curl -O http://localhost:5000/api/files/download/123e4567-e89b-12d3-a456-426614174000
```

## Error Handling

All endpoints return JSON responses with appropriate HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid parameters)
- `404` - Resource not found
- `500` - Server error

Error response format:
```json
{
  "error": "Error message describing what went wrong"
}
```
