import React, { useState, useEffect } from 'react';
import { fetchRegionsData, fetchOptimizationMap } from './services/api';
import ControlPanel from './components/ControlPanel';
import MapViewer from './components/MapViewer';
import Portfolio from './pages/Portfolio';
import BackendStatus from './components/BackendStatus';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles/App.css';

const DEFAULT_PARAMS = {
  region_type: 'all_india',
  region_name: '',
  district: '',
  optimizer: 'weighted',
  k: 0,
  resolution: 120
};

function App() {
  const [appState, setAppState] = useState('PORTFOLIO');
  const [isReady, setIsReady] = useState(false);
  const [mapHtml, setMapHtml] = useState('');
  const [pointsData, setPointsData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [regions, setRegions] = useState({ default_bounds: null, states: [] });
  const [regionsLoading, setRegionsLoading] = useState(false);
  const [hasInitialized, setHasInitialized] = useState(false);
  const [params, setParams] = useState(DEFAULT_PARAMS);

  const fetchRegions = async () => {
    setRegionsLoading(true);
    try {
      const data = await fetchRegionsData();
      setRegions(data);
    } catch (err) {
      // Error handled in api service, but we keep local state in sync
    } finally {
      setRegionsLoading(false);
    }
  };

  const fetchMap = async (parameters, isInitialLoad = false) => {
    setLoading(true);
    setError(null);
    try {
      // Re-fetch regions if they failed to load earlier (e.g. backend was waking up)
      if (!regions || !regions.states || regions.states.length === 0) {
        const data = await fetchRegionsData();
        setRegions(data);
      }

      const data = await fetchOptimizationMap(parameters);
      setMapHtml(data.map_html);
      setPointsData(data.points || []);
      return true;
    } catch (err) {
      setError(
        err.response
          ? `Server error (${err.response.status}): ${err.response.statusText}`
          : 'Failed to connect to backend server. Please verify the backend is running.'
      );
      return false;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    const initialize = async () => {
      await fetchRegions();
      const success = await fetchMap(params, true);

      if (isMounted) {
        setHasInitialized(true);
        if (success) {
          setIsReady(true);
        }
      }
    };

    initialize();

    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // -------------------------------------------------------------
  // INSTANT VIEW SWITCH (Removed Wormhole Transition)
  // -------------------------------------------------------------
  const handleToggle = () => {
    if (appState === 'APP') {
      setAppState('PORTFOLIO');
    } else {
      setAppState('APP');
    }
  };

  const handleOptimize = (newParams) => {
    setParams(newParams);
    fetchMap(newParams);
  };

  const isAppActive = appState === 'APP';
  const showTab = isReady;
  const showStatus = appState === 'PORTFOLIO';

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
          error={error}
        />
        <MapViewer
          mapHtml={mapHtml}
          pointsData={pointsData}
          loading={loading}
          error={error}
          onRetry={async () => {
            await fetchRegions();
            await fetchMap(params);
          }}
        />
      </div>
    </div>
  );

  return (
    <>

      {showTab && (
        <button
          className="portfolio-tab"
          onClick={handleToggle}
          aria-label={appState === 'APP' ? 'Switch to portfolio view' : 'Switch to EV station optimizer app'}
        >
          {appState === 'APP' ? 'View Portfolio' : 'Go to EVCS'}
        </button>
      )}

      {showStatus && <BackendStatus isReady={isReady} />}

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
