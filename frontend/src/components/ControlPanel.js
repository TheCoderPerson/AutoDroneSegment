import React, { useState } from 'react';
import {
  Box,
  TextField,
  Button,
  FormControlLabel,
  Checkbox,
  Typography,
  Divider,
  Paper,
  FormGroup,
  Input
} from '@mui/material';
import CalculateIcon from '@mui/icons-material/Calculate';
import DownloadIcon from '@mui/icons-material/Download';

function ControlPanel({ onCalculate, onExportKML, hasSegments, disabled }) {
  const [params, setParams] = useState({
    projectName: 'SAR Mission',
    droneAltitude: 120, // meters (400 ft)
    segmentSize: 100, // acres
    maxVLOS: 500, // meters
    accessTypes: ['road', 'trail'],
    deviationDistance: 50, // meters
    gridSpacing: 50, // meters
    demFile: null,
    vegetationFile: null
  });

  const handleChange = (field) => (event) => {
    setParams({ ...params, [field]: event.target.value });
  };

  const handleNumberChange = (field) => (event) => {
    const value = parseFloat(event.target.value);
    setParams({ ...params, [field]: isNaN(value) ? 0 : value });
  };

  const handleAccessTypeChange = (type) => (event) => {
    const checked = event.target.checked;
    let newAccessTypes = [...params.accessTypes];

    if (checked) {
      if (!newAccessTypes.includes(type)) {
        newAccessTypes.push(type);
      }
    } else {
      newAccessTypes = newAccessTypes.filter(t => t !== type);
    }

    setParams({ ...params, accessTypes: newAccessTypes });
  };

  const handleFileChange = (field) => (event) => {
    const file = event.target.files[0];
    setParams({ ...params, [field]: file });
  };

  const handleCalculate = () => {
    if (params.accessTypes.length === 0) {
      alert('Please select at least one access type');
      return;
    }
    onCalculate(params);
  };

  const convertMetersToFeet = (meters) => (meters * 3.28084).toFixed(0);
  const convertFeetToMeters = (feet) => (feet / 3.28084).toFixed(1);

  return (
    <Box
      sx={{
        width: 350,
        backgroundColor: '#f5f5f5',
        padding: 2,
        overflowY: 'auto',
        borderRight: '1px solid #ddd'
      }}
    >
      <Typography variant="h6" gutterBottom>
        Project Settings
      </Typography>

      <Paper sx={{ p: 2, mb: 2 }}>
        <TextField
          fullWidth
          label="Project Name"
          value={params.projectName}
          onChange={handleChange('projectName')}
          margin="normal"
          disabled={disabled}
        />

        <TextField
          fullWidth
          label="Drone Altitude (meters)"
          type="number"
          value={params.droneAltitude}
          onChange={handleNumberChange('droneAltitude')}
          margin="normal"
          helperText={`≈ ${convertMetersToFeet(params.droneAltitude)} feet`}
          disabled={disabled}
        />

        <TextField
          fullWidth
          label="Preferred Segment Size (acres)"
          type="number"
          value={params.segmentSize}
          onChange={handleNumberChange('segmentSize')}
          margin="normal"
          disabled={disabled}
        />

        <TextField
          fullWidth
          label="Max VLOS Distance (meters)"
          type="number"
          value={params.maxVLOS}
          onChange={handleNumberChange('maxVLOS')}
          margin="normal"
          helperText={`≈ ${convertMetersToFeet(params.maxVLOS)} feet`}
          disabled={disabled}
        />
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          Access Types
        </Typography>
        <FormGroup>
          <FormControlLabel
            control={
              <Checkbox
                checked={params.accessTypes.includes('road')}
                onChange={handleAccessTypeChange('road')}
                disabled={disabled}
              />
            }
            label="Road"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={params.accessTypes.includes('trail')}
                onChange={handleAccessTypeChange('trail')}
                disabled={disabled}
              />
            }
            label="Trail"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={params.accessTypes.includes('off_road')}
                onChange={handleAccessTypeChange('off_road')}
                disabled={disabled}
              />
            }
            label="Off-Road"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={params.accessTypes.includes('anywhere')}
                onChange={handleAccessTypeChange('anywhere')}
                disabled={disabled}
              />
            }
            label="Anywhere"
          />
        </FormGroup>

        <TextField
          fullWidth
          label="Access Deviation (meters)"
          type="number"
          value={params.deviationDistance}
          onChange={handleNumberChange('deviationDistance')}
          margin="normal"
          helperText="Buffer distance for roads/trails"
          disabled={disabled}
        />
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          Advanced Settings
        </Typography>

        <TextField
          fullWidth
          label="Grid Spacing (meters)"
          type="number"
          value={params.gridSpacing}
          onChange={handleNumberChange('gridSpacing')}
          margin="normal"
          helperText="Spacing between candidate points"
          disabled={disabled}
        />
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          DEM Files
        </Typography>

        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" gutterBottom>
            DEM File (required)
          </Typography>
          <Input
            type="file"
            onChange={handleFileChange('demFile')}
            disabled={disabled}
            fullWidth
            inputProps={{ accept: '.tif,.tiff' }}
          />
          {params.demFile && (
            <Typography variant="caption" color="text.secondary">
              {params.demFile.name}
            </Typography>
          )}
        </Box>

        <Box>
          <Typography variant="body2" gutterBottom>
            Vegetation File (optional)
          </Typography>
          <Input
            type="file"
            onChange={handleFileChange('vegetationFile')}
            disabled={disabled}
            fullWidth
            inputProps={{ accept: '.tif,.tiff' }}
          />
          {params.vegetationFile && (
            <Typography variant="caption" color="text.secondary">
              {params.vegetationFile.name}
            </Typography>
          )}
        </Box>
      </Paper>

      <Divider sx={{ my: 2 }} />

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Button
          variant="contained"
          startIcon={<CalculateIcon />}
          onClick={handleCalculate}
          disabled={disabled}
          fullWidth
          size="large"
        >
          Calculate Segments
        </Button>

        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={onExportKML}
          disabled={!hasSegments || disabled}
          fullWidth
        >
          Export KML
        </Button>
      </Box>

      <Box sx={{ mt: 2 }}>
        <Typography variant="caption" color="text.secondary">
          1. Draw a search polygon on the map
          <br />
          2. Upload DEM file
          <br />
          3. Configure settings
          <br />
          4. Click Calculate Segments
        </Typography>
      </Box>
    </Box>
  );
}

export default ControlPanel;
