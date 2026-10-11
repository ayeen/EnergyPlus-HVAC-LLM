import React, { useState, useEffect } from 'react';
import axios from 'axios';
import io from 'socket.io-client';
import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Alert,
  Card,
  CardContent,
  Grid,
  Divider
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  PlayArrow as PlayArrowIcon,
  Psychology as PsychologyIcon,
  Build as BuildIcon,
  Speed as SpeedIcon
} from '@mui/icons-material';

const AGENT_INFO = {
  'agent1_generation': {
    name: 'Agent 1: HVAC Generator',
    icon: <PsychologyIcon />,
    color: 'primary',
    description: 'Generating VRF-HVAC system configuration from your request'
  },
  'agent1_5_validation': {
    name: 'Agent 1.5: Quick Validator',
    icon: <SpeedIcon />,
    color: 'info',
    description: 'Performing quick validation checks'
  },
  'agent3_correction': {
    name: 'Agent 3: Error Corrector',
    icon: <BuildIcon />,
    color: 'warning',
    description: 'Analyzing and correcting errors'
  }
};

const PipelineMonitor = ({ executionId, onComplete }) => {
  const [status, setStatus] = useState('initializing');
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [logs, setLogs] = useState([]);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [socket, setSocket] = useState(null);

  useEffect(() => {
    // Connect to WebSocket
    const newSocket = io('http://localhost:5000', {
      transports: ['websocket']
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
    });

    newSocket.on('pipeline_progress', (data) => {
      if (data.execution_id === executionId) {
        setProgress(data.progress);
        setCurrentStep(data.step);

        // Check if it's an agent step
        if (AGENT_INFO[data.step]) {
          setCurrentAgent(data.step);
        }

        // Add to logs
        setLogs(prev => [...prev, {
          timestamp: data.timestamp,
          step: data.step,
          message: data.message,
          details: data.details
        }]);

        // Check for completion
        if (data.step === 'completed') {
          setStatus('completed');
          setTimeout(() => onComplete('completed'), 1000);
        } else if (data.step === 'failed' || data.step === 'error') {
          setStatus('failed');
          setTimeout(() => onComplete('failed'), 1000);
        } else {
          setStatus('running');
        }
      }
    });

    setSocket(newSocket);

    // Poll status endpoint as backup
    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/pipeline/status/${executionId}`);
        const data = response.data;

        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(pollInterval);
          setStatus(data.status);
          onComplete(data.status);
        }
      } catch (err) {
        console.error('Status poll error:', err);
      }
    }, 2000);

    return () => {
      newSocket.disconnect();
      clearInterval(pollInterval);
    };
  }, [executionId, onComplete]);

  const getAgentInfo = (step) => {
    return AGENT_INFO[step] || {
      name: step,
      icon: <PlayArrowIcon />,
      color: 'default',
      description: ''
    };
  };

  return (
    <Paper elevation={3} sx={{ p: 4 }}>
      <Typography variant="h5" gutterBottom>
        Step 3: Pipeline Execution
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Monitoring AI agents working on your VRF-HVAC system design
      </Typography>

      {/* Progress Bar */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Overall Progress
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {progress}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{ height: 10, borderRadius: 5 }}
        />
      </Box>

      {/* Current Agent Card */}
      {currentAgent && (
        <Card
          variant="outlined"
          sx={{
            mb: 3,
            borderColor: `${getAgentInfo(currentAgent).color}.main`,
            borderWidth: 2
          }}
        >
          <CardContent>
            <Grid container spacing={2} alignItems="center">
              <Grid item>
                <Box
                  sx={{
                    color: `${getAgentInfo(currentAgent).color}.main`,
                    fontSize: 40
                  }}
                >
                  {getAgentInfo(currentAgent).icon}
                </Box>
              </Grid>
              <Grid item xs>
                <Typography variant="h6" color={`${getAgentInfo(currentAgent).color}.main`}>
                  {getAgentInfo(currentAgent).name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {getAgentInfo(currentAgent).description}
                </Typography>
              </Grid>
              <Grid item>
                <Chip
                  label="Active"
                  color={getAgentInfo(currentAgent).color}
                  size="small"
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Status Alerts */}
      {status === 'completed' && (
        <Alert severity="success" icon={<CheckCircleIcon />} sx={{ mb: 3 }}>
          <Typography variant="subtitle1">
            Pipeline completed successfully!
          </Typography>
          <Typography variant="body2">
            Your VRF-HVAC system has been generated and validated.
          </Typography>
        </Alert>
      )}

      {status === 'failed' && (
        <Alert severity="error" icon={<ErrorIcon />} sx={{ mb: 3 }}>
          <Typography variant="subtitle1">
            Pipeline failed
          </Typography>
          <Typography variant="body2">
            Unable to generate a valid VRF-HVAC system. Check logs for details.
          </Typography>
        </Alert>
      )}

      <Divider sx={{ my: 3 }} />

      {/* Execution Log */}
      <Typography variant="h6" gutterBottom>
        Execution Log
      </Typography>
      <Paper
        variant="outlined"
        sx={{
          maxHeight: 400,
          overflow: 'auto',
          bgcolor: 'grey.50',
          p: 2
        }}
      >
        <List dense>
          {logs.map((log, idx) => (
            <ListItem key={idx} alignItems="flex-start">
              <ListItemIcon sx={{ minWidth: 40 }}>
                {log.step === 'completed' ? (
                  <CheckCircleIcon color="success" />
                ) : log.step === 'failed' || log.step === 'error' ? (
                  <ErrorIcon color="error" />
                ) : (
                  <PlayArrowIcon color="action" />
                )}
              </ListItemIcon>
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <Typography variant="body2" fontWeight="medium">
                      {log.message}
                    </Typography>
                    <Chip
                      label={log.step}
                      size="small"
                      variant="outlined"
                    />
                  </Box>
                }
                secondary={
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </Typography>
                    {log.details && (
                      <Typography
                        variant="caption"
                        component="div"
                        sx={{ mt: 0.5, color: 'text.secondary' }}
                      >
                        {JSON.stringify(log.details, null, 2)}
                      </Typography>
                    )}
                  </Box>
                }
              />
            </ListItem>
          ))}
        </List>

        {logs.length === 0 && (
          <Typography variant="body2" color="text.secondary" align="center">
            Waiting for pipeline updates...
          </Typography>
        )}
      </Paper>
    </Paper>
  );
};

export default PipelineMonitor;
