import axios from 'axios';

const isLocalHost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
export const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  (isLocalHost ? 'http://127.0.0.1:8000' : 'https://evcs-c5xn.onrender.com');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export const fetchRegionsData = async () => {
  try {
    const response = await apiClient.get('/regions', { timeout: 8000 });
    return response.data;
  } catch (err) {
    console.warn('Error or timeout fetching regions:', err);
    throw err;
  }
};

export const fetchOptimizationMap = async (parameters) => {
  try {
    const response = await apiClient.post('/optimize', parameters, { timeout: 12000 });
    return response.data;
  } catch (err) {
    console.warn('Error or timeout fetching map:', err);
    throw err;
  }
};
