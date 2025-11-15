import React, { useState, useEffect } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  CircularProgress,
  LinearProgress,
  Snackbar,
  Alert,
  Button,
  Paper
} from '@mui/material';
import CancelIcon from '@mui/icons-material/Cancel';
import MapView from './MapView';
import ControlPanel from './ControlPanel';
import api from '../services/api';
import { VERSION, BUILD_DATE } from '../version';

function MainLayout() {
  const [searchPolygon, setSearchPolygon] = useState(null);
  const [segments, setSegments] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  const [currentProject, setCurrentProject] = useState(null);

  // Log version on mount
  useEffect(() => {
    console.log('='.repeat(80));
    console.log(`Drone Search Segment Planning Tool - Frontend`);
    console.log(`Version: ${VERSION}`);
    console.log(`Build Date: ${BUILD_DATE}`);
    console.log('='.repeat(80));

    // Fetch backend version
    api.getVersion().then(response => {
      console.log(`Backend Version: ${response.data.version}`);
      console.log(`Backend Build Date: ${response.data.build_date}`);
    }).catch(error => {
      console.error('Could not fetch backend version:', error);
    });
  }, []);

  const handlePolygonCreated = (polygon) => {
    setSearchPolygon(polygon);
    setSegments(null); // Clear previous segments
  };

  const handleCalculateSegments = async (params) => {
    try {
      setLoading(true);

      // Create project
      const projectData = {
        name: params.projectName || 'Unnamed Project',
        search_polygon: searchPolygon,
        drone_agl_altitude: params.droneAltitude,
        preferred_segment_size_acres: params.segmentSize,
        max_vlos_m: params.maxVLOS,
        access_types: params.accessTypes,
        access_deviation_m: params.deviationDistance,
        grid_spacing_m: params.gridSpacing
      };

      const projectResponse = await api.createProject(projectData);
      setCurrentProject(projectResponse.data);

      showNotification('Project created successfully', 'success');

      // Upload DEM if provided
      if (params.demFile) {
        await api.uploadDEM(projectResponse.data.id, params.demFile, params.vegetationFile);
        showNotification('DEM uploaded successfully', 'success');
      }

      // Start calculation
      await api.calculateSegments(projectResponse.data.id);
      showNotification('Segment calculation started', 'info');

      // Poll for results
      pollForResults(projectResponse.data.id);

    } catch (error) {
      console.error('Error calculating segments:', error);
      showNotification('Error calculating segments: ' + error.message, 'error');
      setLoading(false);
    }
  };

  const pollForResults = async (projectId) => {
    const maxAttempts = 1800; // 60 minutes with 2-second intervals
    let attempts = 0;

    const poll = async () => {
      try {
        const statusResponse = await api.getProjectStatus(projectId);
        const status = statusResponse.data;

        // Debug logging
        console.log('Status poll:', status);

        // Update progress display
        setProgress(status.progress || 0);
        setCurrentStep(status.current_step || '');

        console.log('Updated progress state:', status.progress, status.current_step);

        if (status.status === 'completed') {
          // Get segments
          const segmentsResponse = await api.getSegments(projectId);
          setSegments(segmentsResponse.data);
          showNotification('Segments calculated successfully!', 'success');
          setLoading(false);
          setProgress(100);
          setCurrentStep('Complete');
          return;
        } else if (status.status === 'failed') {
          showNotification('Calculation failed: ' + (status.error_message || 'Unknown error'), 'error');
          setLoading(false);
          setProgress(0);
          setCurrentStep('Failed');
          return;
        } else if (status.status === 'cancelled') {
          showNotification('Processing cancelled', 'warning');
          setLoading(false);
          setProgress(0);
          setCurrentStep('Cancelled');
          return;
        } else if (status.status === 'processing') {
          attempts++;
          if (attempts < maxAttempts) {
            setTimeout(poll, 2000); // Poll every 2 seconds
          } else {
            showNotification('Calculation timeout', 'error');
            setLoading(false);
          }
        }
      } catch (error) {
        console.error('Error polling for results:', error);
        showNotification('Error checking status', 'error');
        setLoading(false);
      }
    };

    poll();
  };

  const handleCancelProcessing = async () => {
    if (!currentProject) {
      return;
    }

    try {
      await api.cancelProject(currentProject.id);
      showNotification('Cancellation requested', 'info');
    } catch (error) {
      console.error('Error cancelling project:', error);
      showNotification('Error cancelling: ' + error.message, 'error');
    }
  };

  const handleExportKML = async () => {
    if (!currentProject) {
      showNotification('No project to export', 'warning');
      return;
    }

    try {
      const blob = await api.exportKML(currentProject.id);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${currentProject.name}.kml`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      showNotification('KML exported successfully', 'success');
    } catch (error) {
      console.error('Error exporting KML:', error);
      showNotification('Error exporting KML', 'error');
    }
  };

  const showNotification = (message, severity = 'info') => {
    setNotification({ open: true, message, severity });
  };

  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Drone Search Segment Planning Tool
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.8 }}>
            v{VERSION}
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Control Panel */}
        <ControlPanel
          onCalculate={handleCalculateSegments}
          onExportKML={handleExportKML}
          hasSegments={!!segments}
          disabled={loading}
        />

        {/* Map */}
        <Box sx={{ flex: 1, position: 'relative' }}>
          <MapView
            onPolygonCreated={handlePolygonCreated}
            segments={segments}
          />

          {/* Loading Overlay */}
          {loading && (
            <Box
              sx={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000
              }}
            >
              <Paper
                sx={{
                  p: 4,
                  minWidth: 400,
                  textAlign: 'center'
                }}
              >
                <Typography variant="h6" gutterBottom>
                  Processing Segments
                </Typography>

                <Box sx={{ mt: 3, mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {currentStep || 'Starting...'}
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={progress}
                    sx={{ height: 10, borderRadius: 5, mt: 1 }}
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {progress}%
                  </Typography>
                </Box>

                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<CancelIcon />}
                  onClick={handleCancelProcessing}
                  sx={{ mt: 2 }}
                >
                  Cancel
                </Button>
              </Paper>
            </Box>
          )}
        </Box>
      </Box>

      {/* Notifications */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseNotification}
          severity={notification.severity}
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default MainLayout;
