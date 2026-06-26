import React from 'react';
import './MapViewer.css';

function MapViewer({ mapHtml, loading, error }) {
  return (
    <div className="map-viewer">
      <div className="map-body">
        {loading && (
          <div className="loading-container">
            <div className="spatial-spinner"></div>
            <p className="loading-text">Generating optimized station locations...</p>
          </div>
        )}
        
        {error && (
          <div className="error-alert">
            <h3 className="error-title">Error Loading Map</h3>
            <p className="error-desc">{error}</p>
            <p className="error-hint">
              The optimization service may be waking up. Please wait a moment and try again.
            </p>
          </div>
        )}
        
        {!loading && !error && mapHtml && (
          <div className="map-container">
            <iframe
              srcDoc={mapHtml}
              title="EV Station Optimization Map"
              className="map-iframe"
            />
          </div>
        )}
        
        {!loading && !error && !mapHtml && (
          <div className="loading-container">
            <p className="loading-text">Initializing map canvas...</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default MapViewer;
