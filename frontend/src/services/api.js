import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = {
  // Create a new project
  createProject: async (projectData) => {
    return axios.post(`${API_BASE_URL}/projects`, projectData);
  },

  // Upload DEM files
  uploadDEM: async (projectId, demFile, vegetationFile = null) => {
    const formData = new FormData();
    formData.append('dem_file', demFile);
    if (vegetationFile) {
      formData.append('vegetation_file', vegetationFile);
    }

    return axios.post(
      `${API_BASE_URL}/projects/${projectId}/upload-dem`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
  },

  // Start segment calculation
  calculateSegments: async (projectId) => {
    return axios.post(`${API_BASE_URL}/projects/${projectId}/calculate`);
  },

  // Get project details
  getProject: async (projectId) => {
    return axios.get(`${API_BASE_URL}/projects/${projectId}`);
  },

  // Get project status (for polling)
  getProjectStatus: async (projectId) => {
    return axios.get(`${API_BASE_URL}/projects/${projectId}/status`);
  },

  // Cancel project processing
  cancelProject: async (projectId) => {
    return axios.post(`${API_BASE_URL}/projects/${projectId}/cancel`);
  },

  // Get segments for a project
  getSegments: async (projectId) => {
    return axios.get(`${API_BASE_URL}/projects/${projectId}/segments`);
  },

  // Export to KML
  exportKML: async (projectId) => {
    const response = await axios.get(
      `${API_BASE_URL}/projects/${projectId}/export-kml`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  },

  // List all projects
  listProjects: async () => {
    return axios.get(`${API_BASE_URL}/projects`);
  },

  // Delete a project
  deleteProject: async (projectId) => {
    return axios.delete(`${API_BASE_URL}/projects/${projectId}`);
  },
};

export default api;
