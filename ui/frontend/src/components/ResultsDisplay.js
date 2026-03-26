import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Tabs,
  Tab,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Divider
} from '@mui/material';
import {
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  Description as DescriptionIcon,
  CheckCircle as CheckCircleIcon
} from '@mui/icons-material';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { docco } from 'react-syntax-highlighter/dist/esm/styles/hljs';

const ResultsDisplay = ({ executionId, onReset }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [idfPreview, setIdfPreview] = useState('');
  const [files, setFiles] = useState({ idfs: [], logs: [], simulation_results: [] });
  const [logData, setLogData] = useState(null);
  const [loading, setLoading] = useState({ preview: false, files: false, log: false });
  const [error, setError] = useState(null);

  const loadFiles = useCallback(async () => {
    setLoading(prev => ({ ...prev, files: true }));
    try {
      const response = await axios.get(`/api/files/list/${executionId}`);
      setFiles(response.data);
    } catch (err) {
      console.error('Failed to load files:', err);
    } finally {
      setLoading(prev => ({ ...prev, files: false }));
    }
  }, [executionId]);

  const loadLog = useCallback(async () => {
    setLoading(prev => ({ ...prev, log: true }));
    try {
      const response = await axios.get(`/api/files/log/${executionId}`);
      setLogData(response.data);
    } catch (err) {
      console.error('Failed to load log:', err);
    } finally {
      setLoading(prev => ({ ...prev, log: false }));
    }
  }, [executionId]);

  const loadIdfPreview = useCallback(async () => {
    setLoading(prev => ({ ...prev, preview: true }));
    setIdfPreview(''); // Clear preview first
    setError(null);
    try {
      console.log('Loading IDF preview for executionId:', executionId);
      // Add timestamp to prevent caching
      const timestamp = new Date().getTime();
      const response = await axios.get(`/api/files/preview/${executionId}?lines=500&t=${timestamp}`);
      console.log('Preview API response:', {
        status: response.status,
        dataKeys: Object.keys(response.data),
        success: response.data.success,
        filename: response.data.filename,
        contentLength: response.data.content ? response.data.content.length : 0
      });
      if (response.data.success) {
        setIdfPreview(response.data.content);
        console.log('✓ IDF preview set successfully');
        console.log('  - Filename:', response.data.filename);
        console.log('  - Content length:', response.data.content.length);
        console.log('  - Is FINAL file:', response.data.filename?.includes('_FINAL') || false);
      } else {
        console.warn('❌ API response success is false:', response.data);
        setError('Preview not available');
      }
    } catch (err) {
      setError('Failed to load IDF preview');
      console.error('❌ Failed to load preview:', err);
    } finally {
      setLoading(prev => ({ ...prev, preview: false }));
    }
  }, [executionId]);

  useEffect(() => {
    loadFiles();
    loadIdfPreview();
    loadLog();
  }, [loadFiles, loadIdfPreview, loadLog]);

  // Add effect to refresh data after a short delay when component mounts
  // This ensures final files are fully written before loading
  useEffect(() => {
    const refreshTimer = setTimeout(() => {
      console.log('Refreshing data after mount delay...');
      loadFiles();
      loadIdfPreview();
      loadLog();
    }, 2000);

    return () => clearTimeout(refreshTimer);
  }, [loadFiles, loadIdfPreview, loadLog]);

  const handleDownload = async () => {
    try {
      const response = await axios.get(`/api/files/download/${executionId}`, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${executionId}_generated.idf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError('Failed to download file');
    }
  };

  const handleRefreshPreview = useCallback(() => {
    console.log('Manual refresh triggered');
    loadFiles();
    loadIdfPreview();
    loadLog();
  }, [loadFiles, loadIdfPreview, loadLog]);

  return (
    <Paper elevation={3} sx={{ p: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h5" gutterBottom>
            Step 4: Results
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Your HVAC system has been generated successfully
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={onReset}
        >
          Start New Generation
        </Button>
      </Box>

      {/* Success Summary */}
      <Alert severity="success" icon={<CheckCircleIcon />} sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Generation Complete!
        </Typography>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          {logData && (
            <>
              <Grid item xs={6} md={3}>
                <Typography variant="caption" color="text.secondary">
                  Status
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  {logData.final_status || 'SUCCESS'}
                </Typography>
              </Grid>
              <Grid item xs={6} md={3}>
                <Typography variant="caption" color="text.secondary">
                  Iterations
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  {logData.correction_iterations || 0}
                </Typography>
              </Grid>
              <Grid item xs={6} md={3}>
                <Typography variant="caption" color="text.secondary">
                  Execution Time
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  {logData.total_execution_time_seconds
                    ? `${logData.total_execution_time_seconds.toFixed(1)}s`
                    : 'N/A'}
                </Typography>
              </Grid>
              <Grid item xs={6} md={3}>
                <Typography variant="caption" color="text.secondary">
                  LLM Provider
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  {logData.llm_provider || 'N/A'}
                </Typography>
              </Grid>
            </>
          )}
        </Grid>
      </Alert>

      {/* Download Button */}
      <Button
        variant="contained"
        size="large"
        startIcon={<DownloadIcon />}
        onClick={handleDownload}
        fullWidth
        sx={{ mb: 3 }}
      >
        Download Generated IDF File
      </Button>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
          <Tab label="IDF Preview" icon={<VisibilityIcon />} iconPosition="start" />
          <Tab label="Files" icon={<DescriptionIcon />} iconPosition="start" />
          <Tab label="Details" icon={<CheckCircleIcon />} iconPosition="start" />
        </Tabs>
      </Box>

      {/* Tab Panels */}
      {activeTab === 0 && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Generated IDF Preview</Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={handleRefreshPreview}
            >
              Refresh Preview
            </Button>
          </Box>
          {loading.preview ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Paper
              variant="outlined"
              sx={{
                maxHeight: 600,
                overflow: 'auto',
                bgcolor: 'grey.50'
              }}
            >
              {idfPreview ? (
                <>
                  <Box sx={{ p: 2, bgcolor: 'primary.main', color: 'white' }}>
                    <Typography variant="body2">
                      📁 Showing: Generated IDF with HVAC content ({idfPreview.split('\n').length} lines)
                    </Typography>
                  </Box>
                  <SyntaxHighlighter
                    language="text"
                    style={docco}
                    customStyle={{
                      margin: 0,
                      padding: '16px',
                      fontSize: '12px',
                      backgroundColor: '#fafafa'
                    }}
                    showLineNumbers
                  >
                    {idfPreview}
                  </SyntaxHighlighter>
                </>
              ) : (
                <Box sx={{ p: 4, textAlign: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    No preview available - Click "Refresh Preview" to reload
                  </Typography>
                </Box>
              )}
            </Paper>
          )}
        </Box>
      )}

      {activeTab === 1 && (
        <Box>
          {loading.files ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Grid container spacing={2}>
              {/* IDF Files */}
              <Grid item xs={12} md={6}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      IDF Files ({files.idfs.length})
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <List dense>
                      {files.idfs.map((file, idx) => (
                        <ListItem key={idx}>
                          <ListItemText
                            primary={file.filename}
                            secondary={`${file.size_kb} KB${file.is_final ? ' (Final)' : ''}`}
                          />
                        </ListItem>
                      ))}
                      {files.idfs.length === 0 && (
                        <Typography variant="body2" color="text.secondary" align="center">
                          No IDF files found
                        </Typography>
                      )}
                    </List>
                  </CardContent>
                </Card>
              </Grid>

              {/* Log Files */}
              <Grid item xs={12} md={6}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Log Files ({files.logs.length})
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <List dense>
                      {files.logs.map((file, idx) => (
                        <ListItem key={idx}>
                          <ListItemText
                            primary={file.filename}
                            secondary={`${file.size_kb} KB`}
                          />
                        </ListItem>
                      ))}
                      {files.logs.length === 0 && (
                        <Typography variant="body2" color="text.secondary" align="center">
                          No log files found
                        </Typography>
                      )}
                    </List>
                  </CardContent>
                </Card>
              </Grid>

              {/* Simulation Results */}
              <Grid item xs={12}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Simulation Results ({files.simulation_results.length})
                    </Typography>
                    <Divider sx={{ mb: 2 }} />
                    <List dense>
                      {files.simulation_results.map((result, idx) => (
                        <ListItem key={idx}>
                          <ListItemText
                            primary={result.folder}
                            secondary={`${result.files.length} files`}
                          />
                        </ListItem>
                      ))}
                      {files.simulation_results.length === 0 && (
                        <Typography variant="body2" color="text.secondary" align="center">
                          No simulation results found
                        </Typography>
                      )}
                    </List>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </Box>
      )}

      {activeTab === 2 && (
        <Box>
          {loading.log ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : logData ? (
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Pipeline Execution Details
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  fontSize: '12px',
                  backgroundColor: '#f5f5f5',
                  padding: '16px',
                  borderRadius: '4px',
                  overflow: 'auto',
                  maxHeight: '500px'
                }}>
                  {JSON.stringify(logData, null, 2)}
                </pre>
              </CardContent>
            </Card>
          ) : (
            <Typography variant="body2" color="text.secondary" align="center">
              No log data available
            </Typography>
          )}
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Paper>
  );
};

export default ResultsDisplay;
