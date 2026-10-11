# HVAC-LLM Frontend

React-based user interface for the EnergyPlus HVAC-LLM system.

## Features

- **Drag & Drop File Upload**: Easy IDF file upload with validation
- **Natural Language Interface**: Describe HVAC systems in plain English
- **Real-time Progress Monitoring**: Watch AI agents work via WebSocket updates
- **IDF Preview & Download**: View and download generated IDF files
- **Material-UI Design**: Professional, modern interface

## Technology Stack

- **React 18**: Modern React with hooks
- **Material-UI 5**: Component library
- **Socket.io Client**: Real-time WebSocket communication
- **Axios**: HTTP requests
- **React Syntax Highlighter**: Code preview
- **React Dropzone**: Drag & drop file upload

## Installation

```bash
cd ui/frontend
npm install
```

## Running the Development Server

```bash
npm start
```

The app will be available at `http://localhost:3000`

**Note**: The backend API must be running at `http://localhost:5000`

## Building for Production

```bash
npm run build
```

The optimized production build will be in the `build/` directory.

## Components

### FileUpload
- Drag-and-drop file upload
- IDF validation on upload
- Zone detection
- File size: up to 50MB

### HVACRequestForm
- Natural language input
- Example requests from config
- LLM provider selection
- RAG enable/disable
- Zone configuration

### PipelineMonitor
- Real-time progress updates
- Agent status cards
- Execution log
- WebSocket connection

### ResultsDisplay
- IDF file preview
- Download functionality
- File list
- Execution details

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── FileUpload.js
│   │   ├── HVACRequestForm.js
│   │   ├── PipelineMonitor.js
│   │   └── ResultsDisplay.js
│   ├── App.js
│   ├── index.js
│   └── index.css
├── package.json
└── README.md
```

## Workflow

1. **Upload**: User uploads base IDF file (building without HVAC)
2. **Configure**: User describes desired HVAC system in natural language
3. **Generate**: Pipeline executes with real-time agent monitoring
4. **Results**: View, preview, and download generated IDF file

## Configuration

The frontend is configured to connect to the backend API at `http://localhost:5000`. This is set via the `proxy` field in `package.json`.

To change the API URL for production, update the axios base URL or use environment variables.

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Development Tips

- Hot reload is enabled in development mode
- Open browser console to see WebSocket events
- Use React DevTools for component debugging
- Material-UI theme can be customized in `App.js`

## Troubleshooting

### WebSocket Connection Fails
- Ensure backend is running on port 5000
- Check CORS configuration in backend `config.py`
- Verify firewall settings

### File Upload Fails
- Check file size (max 50MB)
- Ensure file has `.idf` extension
- Verify backend upload endpoint is accessible

### Preview Not Loading
- Check browser console for errors
- Verify execution ID is correct
- Ensure IDF file was generated successfully
