import React, { useState } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import {
  CssBaseline,
  Container,
  Box,
  AppBar,
  Toolbar,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Paper
} from '@mui/material';
import FileUpload from './components/FileUpload';
import HVACRequestForm from './components/HVACRequestForm';
import PipelineMonitor from './components/PipelineMonitor';
import ResultsDisplay from './components/ResultsDisplay';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

const steps = [
  'Upload Base IDF',
  'User Request',
  'Generate & Monitor',
  'View Results'
];

function App() {
  const [activeStep, setActiveStep] = useState(0);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [executionId, setExecutionId] = useState(null);
  const [pipelineStatus, setPipelineStatus] = useState(null);

  const handleFileUpload = (fileData) => {
    setUploadedFile(fileData);
    setActiveStep(1);
  };

  const handlePipelineStart = (execId) => {
    setExecutionId(execId);
    setActiveStep(2);
  };

  const handlePipelineComplete = (status) => {
    setPipelineStatus(status);
    if (status === 'completed') {
      setActiveStep(3);
    }
  };

  const handleReset = () => {
    setActiveStep(0);
    setUploadedFile(null);
    setExecutionId(null);
    setPipelineStatus(null);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              HuBEL - VRF-LLM
            </Typography>
            {/* <Typography variant="body2">
              Automated VRF-HVAC System 
            </Typography> */}
          </Toolbar>
        </AppBar>

        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
            <Stepper activeStep={activeStep} alternativeLabel>
              {steps.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
          </Paper>

          <Box sx={{ mt: 4 }}>
            {activeStep === 0 && (
              <FileUpload onFileUploaded={handleFileUpload} />
            )}

            {activeStep === 1 && uploadedFile && (
              <HVACRequestForm
                uploadedFile={uploadedFile}
                onPipelineStart={handlePipelineStart}
                onBack={() => setActiveStep(0)}
              />
            )}

            {activeStep === 2 && executionId && (
              <PipelineMonitor
                executionId={executionId}
                onComplete={handlePipelineComplete}
              />
            )}

            {activeStep === 3 && executionId && (
              <ResultsDisplay
                executionId={executionId}
                onReset={handleReset}
              />
            )}
          </Box>
        </Container>

        <Box
          component="footer"
          sx={{
            py: 3,
            px: 2,
            mt: 'auto',
            backgroundColor: (theme) =>
              theme.palette.mode === 'light'
                ? theme.palette.grey[200]
                : theme.palette.grey[800],
          }}
        >
          <Container maxWidth="xl">
            <Typography variant="body2" color="text.secondary" align="center">
               Human Behavior and Energy Laboratory (HuBEL) | VRF-LLM Version 1.0.0
            </Typography>
          </Container>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
