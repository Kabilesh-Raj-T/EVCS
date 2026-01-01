import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ControlPanel from './components/ControlPanel';
import MapViewer from './components/MapViewer';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

function App() {
  const [mapHtml, setMapHtml] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [params, setParams] = useState({
    k: 0, // default to 0 stations for better visualization
    resolution: 100,
    lat_min: 8.0,
    lat_max: 13.5,
    lon_min: 76.0,
    lon_max: 80.5
  });

  //  Azure backend URL
  const API_BASE_URL = 'https://evcsapi-cugngxfxc2d8eubv.centralindia-01.azurewebsites.net';

  //  Fetch optimized map from backend
  const fetchMap = async (parameters) => {
    setLoading(true);
    setError(null);
    try {
      // FIX: Removed { responseType: 'text' } so axios automatically parses the JSON response
      const response = await axios.post(
        `${API_BASE_URL}/optimize`,
        parameters
      );
      
      // FIX: Access the 'map_html' property from the JSON object returned by app.py
      setMapHtml(response.data.map_html);
      
    } catch (err) {
      console.error('Error fetching map:', err);
      setError(
        err.response
          ? `Server error (${err.response.status}): ${err.response.statusText}`
          : 'Failed to connect to backend. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  //  Load map once on page load
  useEffect(() => {
    fetchMap(params);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  //  Handle optimize button click
  const handleOptimize = (newParams) => {
    setParams(newParams);
    fetchMap(newParams);
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>Placitude</h1>
        <p>
          Optimize electric vehicle charging station placement using
          data-driven spatial insights.
        </p>
      </header>

      <div className="app-container">
        <ControlPanel
          params={params}
          onOptimize={handleOptimize}
          loading={loading}
        />
        <MapViewer mapHtml={mapHtml} loading={loading} error={error} />
      </div>
    </div>
  );
}

export default App;
