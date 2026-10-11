import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  FormControlLabel,
  Switch,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Grid,
  Card,
  CardContent,
  CardActions,
  Alert,
  CircularProgress,
  Divider
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  ArrowBack as ArrowBackIcon,
  Lightbulb as LightbulbIcon
} from '@mui/icons-material';

const HVACRequestForm = ({ uploadedFile, onPipelineStart, onBack }) => {
  const [userRequest, setUserRequest] = useState('');
  const [systemName, setSystemName] = useState('VRF_System_' + Date.now());
  const [useRAG, setUseRAG] = useState(true);
  const [llmProvider, setLlmProvider] = useState('mistral');
  const [zones, setZones] = useState(null); // null = auto-detect
  const [examples, setExamples] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Load example requests
    axios.get('/api/pipeline/examples')
      .then(response => {
        setExamples(response.data.examples || []);
      })
      .catch(err => {
        console.error('Failed to load examples:', err);
      });
  }, []);

  const handleExampleClick = (example) => {
    setUserRequest(example.request);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post('/api/pipeline/run', {
        file_id: uploadedFile.file_id,
        user_request: userRequest,
        system_name: systemName,
        zones: zones,
        use_rag: useRAG,
        llm_provider: llmProvider
      });

      if (response.data.success) {
        onPipelineStart(response.data.execution_id);
      } else {
        setError('Failed to start pipeline');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to start pipeline');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 4 }}>
      <Typography variant="h5" gutterBottom>
        Step 2: User Request
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Describe your desired  VRF system.
      </Typography>

      {/* File Info Summary */}
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="subtitle2">
          Uploaded File: <strong>{uploadedFile.filename}</strong>
        </Typography>
        {/* <Typography variant="body2">
          Zones: {uploadedFile.validation.zone_count} detected
        </Typography> */}
      </Alert>

      <Divider sx={{ my: 3 }} />

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Prompt (Natural Language)"
              placeholder="Example: Design a VRF system with heat recovery for a commercial office building in cold climate. Prioritize energy efficiency and zonal control."
              value={userRequest}
              onChange={(e) => setUserRequest(e.target.value)}
              required
              helperText="Describe the VRF system you want to generate. Be as specific as possible about requirements."
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="System Name"
              value={systemName}
              onChange={(e) => setSystemName(e.target.value)}
              required
              helperText="Unique identifier for this HVAC system"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>LLM Provider</InputLabel>
              <Select
                value={llmProvider}
                label="LLM Provider"
                onChange={(e) => setLlmProvider(e.target.value)}
              >
                <MenuItem value="mistral">Mistral Fine-tuned (Recommended)</MenuItem>
                <MenuItem value="mistral-api">Mistral Base Model</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={useRAG}
                  onChange={(e) => setUseRAG(e.target.checked)}
                  color="primary"
                />
              }
              label={
                <Box>
                  <Typography variant="body1">
                    Enable RAG (Retrieval-Augmented Generation)
                  </Typography>
                  {/* <Typography variant="caption" color="text.secondary">
                    Uses knowledge base for better results (Recommended)
                  </Typography> */}
                </Box>
              }
            />
          </Grid>

          {/* <Grid item xs={12}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Zone Configuration
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip
                label="Auto-detect zones (Recommended)"
                color={zones === null ? 'primary' : 'default'}
                onClick={() => setZones(null)}
                sx={{ cursor: 'pointer' }}
              />
              <Chip
                label={`Use detected zones (${uploadedFile.validation.zone_count})`}
                color={zones !== null ? 'primary' : 'default'}
                onClick={() => setZones(uploadedFile.validation.zones)}
                sx={{ cursor: 'pointer' }}
              />
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Auto-detect automatically finds all zones in the IDF file
            </Typography>
          </Grid> */}

          {error && (
            <Grid item xs={12}>
              <Alert severity="error">{error}</Alert>
            </Grid>
          )}

          <Grid item xs={12}>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="outlined"
                startIcon={<ArrowBackIcon />}
                onClick={onBack}
                disabled={loading}
              >
                Back
              </Button>
              <Button
                type="submit"
                variant="contained"
                startIcon={loading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                disabled={loading || !userRequest}
                fullWidth
              >
                {loading ? 'Starting Pipeline...' : 'Generate'}
              </Button>
            </Box>
          </Grid>
        </Grid>
      </form>
    </Paper>
  );
};

export default HVACRequestForm;
