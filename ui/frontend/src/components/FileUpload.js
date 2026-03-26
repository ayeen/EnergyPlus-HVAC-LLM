import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import {
  Box,
  Paper,
  Typography,
  Button,
  CircularProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  Chip,
  Divider
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon
} from '@mui/icons-material';

const FileUpload = ({ onFileUploaded }) => {
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState(null);

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setUploading(true);
    setError(null);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post('/api/upload/idf', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setUploadResult(response.data);

      // Notify parent component
      if (onFileUploaded && response.data.success) {
        onFileUploaded(response.data);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [onFileUploaded]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.idf']
    },
    multiple: false,
    maxSize: 50 * 1024 * 1024 // 50MB
  });

  return (
    <Paper elevation={3} sx={{ p: 4 }}>
      <Typography variant="h5" gutterBottom>
        Step 1: Upload Base IDF File
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Upload an EnergyPlus IDF file containing building geometry and zones without HVAC systems
      </Typography>

      <Box
        {...getRootProps()}
        sx={{
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'grey.400',
          borderRadius: 2,
          p: 4,
          textAlign: 'center',
          backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
          cursor: 'pointer',
          transition: 'all 0.3s',
          '&:hover': {
            borderColor: 'primary.main',
            backgroundColor: 'action.hover',
          }
        }}
      >
        <input {...getInputProps()} />
        <CloudUploadIcon sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />

        {uploading ? (
          <Box>
            <CircularProgress size={40} sx={{ mb: 2 }} />
            <Typography>Uploading and validating...</Typography>
          </Box>
        ) : (
          <Box>
            <Typography variant="h6" gutterBottom>
              {isDragActive
                ? 'Drop the IDF file here'
                : 'Drag and drop IDF file, or click to browse'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Supported format: .idf (Max size: 50MB)
            </Typography>
          </Box>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mt: 3 }} icon={<ErrorIcon />}>
          {error}
        </Alert>
      )}

      {uploadResult && uploadResult.success && (
        <Alert severity="success" sx={{ mt: 3 }} icon={<CheckCircleIcon />}>
          <Box>
            <Typography variant="subtitle1" gutterBottom>
              File uploaded successfully!
            </Typography>

            <Divider sx={{ my: 2 }} />

            <List dense>
              <ListItem>
                <ListItemText
                  primary="Filename"
                  secondary={uploadResult.filename}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="File Size"
                  secondary={`${uploadResult.size_kb} KB`}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Validation Status"
                  secondary={
                    <Chip
                      label={uploadResult.validation.valid ? 'Valid' : 'Invalid'}
                      color={uploadResult.validation.valid ? 'success' : 'error'}
                      size="small"
                      sx={{ mt: 0.5 }}
                    />
                  }
                />
              </ListItem>
              {uploadResult.validation.valid && (
                <>
                  <ListItem>
                    <ListItemText
                      primary="Zone Count"
                      secondary={uploadResult.validation.zone_count}
                    />
                  </ListItem>
                  {uploadResult.validation.zones.length > 0 && (
                    <ListItem>
                      <ListItemText
                        primary="Detected Zones"
                        secondary={
                          <Box sx={{ mt: 1 }}>
                            {uploadResult.validation.zones.slice(0, 10).map((zone, idx) => (
                              <Chip
                                key={idx}
                                label={zone}
                                size="small"
                                sx={{ mr: 0.5, mb: 0.5 }}
                              />
                            ))}
                            {uploadResult.validation.zone_count > 10 && (
                              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                                ...and {uploadResult.validation.zone_count - 10} more
                              </Typography>
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                  )}
                </>
              )}
            </List>

            <Button
              variant="contained"
              fullWidth
              sx={{ mt: 2 }}
              onClick={() => onFileUploaded(uploadResult)}
            >
              Continue to HVAC Configuration
            </Button>
          </Box>
        </Alert>
      )}
    </Paper>
  );
};

export default FileUpload;
