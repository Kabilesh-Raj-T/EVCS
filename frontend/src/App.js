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
    k: 0,
    resolution: 100,
    lat_min: 8.0,
    lat_max: 13.5,
    lon_min: 76.0,
    lon_max: 80.5
  });

  const fetchMap = async (parameters) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post('/optimize', parameters, {
        responseType: 'text'
      });
      setMapHtml(response.data);
    } catch (err) {
      setError(err.message || 'Failed to load map');
      console.error('Error fetching map:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMap(params);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleOptimize = (newParams) => {
    setParams(newParams);
    fetchMap(newParams);
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>🚗 EV Station Optimizer - Tamil Nadu</h1>
        <p>Optimize electric vehicle charging station placement using data-driven insights</p>
      </header>
      <div className="app-container">
        <ControlPanel 
          params={params}
          onOptimize={handleOptimize}
          loading={loading}
        />
        <MapViewer 
          mapHtml={mapHtml}
          loading={loading}
          error={error}
        />
      </div>
    </div>
  );
}

export default App;
