import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  CircularProgress,
  Snackbar,
  Alert
} from '@mui/material';
import MapView from './MapView';
import ControlPanel from './ControlPanel';
import api from '../services/api';

function MainLayout() {
  const [searchPolygon, setSearchPolygon] = useState(null);
  const [segments, setSegments] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  const [currentProject, setCurrentProject] = useState(null);

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
    const maxAttempts = 60; // 5 minutes with 5-second intervals
    let attempts = 0;

    const poll = async () => {
      try {
        const projectResponse = await api.getProject(projectId);
        const project = projectResponse.data;

        if (project.status === 'completed') {
          // Get segments
          const segmentsResponse = await api.getSegments(projectId);
          setSegments(segmentsResponse.data);
          showNotification('Segments calculated successfully!', 'success');
          setLoading(false);
          return;
        } else if (project.status === 'failed') {
          showNotification('Calculation failed: ' + project.error_message, 'error');
          setLoading(false);
          return;
        } else if (project.status === 'processing') {
          attempts++;
          if (attempts < maxAttempts) {
            setTimeout(poll, 5000); // Poll every 5 seconds
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
              <Box sx={{ textAlign: 'center', color: 'white' }}>
                <CircularProgress color="inherit" />
                <Typography sx={{ mt: 2 }}>Calculating segments...</Typography>
              </Box>
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
