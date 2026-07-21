import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ControlPanel from './components/ControlPanel';
import MapViewer from './components/MapViewer';
import Portfolio from './components/Portfolio';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

const DEFAULT_PARAMS = {
  region_type: 'all_india',
  region_name: '',
  district: '',
  optimizer: 'greedy',
  k: 0,
  resolution: 120
};

const isLocalHost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  (isLocalHost ? 'http://127.0.0.1:8000' : 'https://evcs-c5xn.onrender.com');

function App() {
  const [appState, setAppState] = useState('PORTFOLIO');
  // states: 'PORTFOLIO', 'APP'
  const [isReady, setIsReady] = useState(false);
  const [mapHtml, setMapHtml] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [regions, setRegions] = useState({ default_bounds: null, states: [] });
  const [regionsLoading, setRegionsLoading] = useState(false);

  const [params, setParams] = useState(DEFAULT_PARAMS);

  const fetchRegions = async () => {
    setRegionsLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/regions`);
      setRegions(response.data);
    } catch (err) {
      console.error('Error fetching regions:', err);
    } finally {
      setRegionsLoading(false);
    }
  };

  const fetchMap = async (parameters, isInitialLoad = false) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(
        `${API_BASE_URL}/optimize`,
        parameters
      );
      setMapHtml(response.data.map_html);
      return true;
    } catch (err) {
      console.error('Error fetching map:', err);
      setError(
        err.response
          ? `Server error (${err.response.status}): ${err.response.statusText}`
          : 'Failed to connect to backend. Please try again.'
      );
      return false;
    } finally {
      setLoading(false);
    }
  };

  const mayAutoOpenAppRef = useRef(true);

  useEffect(() => {
    let timeoutId;
    let isMounted = true;

    timeoutId = setTimeout(() => {
      mayAutoOpenAppRef.current = false;
    }, 1000);

    const initialize = async () => {
      await fetchRegions();
      const success = await fetchMap(params, true);

      if (isMounted && success) {
        setIsReady(true);
        if (mayAutoOpenAppRef.current) {
          setAppState('APP');
        }
      } else if (isMounted && !success) {
        setAppState('APP');
      }
    };

    initialize();

    return () => {
      isMounted = false;
      clearTimeout(timeoutId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleToggle = () => {
    if (appState === 'APP') {
      setAppState('PORTFOLIO');
    } else if (appState === 'PORTFOLIO') {
      setAppState('APP');
    }
  };

  const handleOptimize = (newParams) => {
    setParams(newParams);
    fetchMap(newParams);
  };

  const mainAppContent = (
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
          defaultParams={DEFAULT_PARAMS}
          regions={regions}
          regionsLoading={regionsLoading}
          onOptimize={handleOptimize}
          loading={loading}
        />
        <MapViewer mapHtml={mapHtml} loading={loading} error={error} />
      </div>
    </div>
  );

  const isAppActive = appState === 'APP';
  const showTab = isReady;

  return (
    <>
      {showTab && (
        <button 
          className="portfolio-tab"
          onClick={handleToggle}
        >
          {appState === 'APP' ? 'View Portfolio' : 'Go to EVCS'}
        </button>
      )}
      
      {appState === 'PORTFOLIO' && (
        <div className={`backend-status ${isReady ? 'ready' : ''}`}>
          {!isReady ? (
            <>
              <div className="spinner"></div>
              Waking up backend...
            </>
          ) : (
            <>
              <div className="check-icon">✓</div>
              Backend is online!
            </>
          )}
        </div>
      )}

      <div className={`portfolio-wrapper ${isAppActive ? 'zoom-through' : ''}`}>
        <Portfolio
          isTransitioning={isAppActive}
          isBackendReady={isReady}
          onToggleApp={handleToggle}
        />
      </div>
      <div className={`app-main ${!isAppActive ? 'background-depth' : ''}`}>
        {mainAppContent}
      </div>
    </>
  );
}

export default App;
