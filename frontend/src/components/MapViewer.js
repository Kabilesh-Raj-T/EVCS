import React, { useEffect, useRef, useState } from 'react';
import './MapViewer.css';
import { animate, prefersReducedMotion } from '../utils/motion';

function MapViewer({ mapHtml, pointsData = [], loading, error, onRetry }) {
  const prevMapHtmlRef = useRef('');
  const [isFlipped, setIsFlipped] = useState(false);

  // Animate map container when mapHtml first arrives or changes
  useEffect(() => {
    if (mapHtml && mapHtml !== prevMapHtmlRef.current) {
      prevMapHtmlRef.current = mapHtml;
      // Reset flip when new map arrives
      setIsFlipped(false);
      if (!prefersReducedMotion()) {
        requestAnimationFrame(() => {
          animate('.map-container', {
            opacity: [0, 1],
            scale: [0.98, 1],
            duration: 450,
            ease: 'outQuad',
          });
        });
      }
    }
  }, [mapHtml]);

  return (
    <div className="map-viewer">
      <div className="map-body">
        
        {/* Toggle Flip Button (only visible if we have data) */}
        {!loading && !error && mapHtml && pointsData.length > 0 && (
          <button 
            className="map-flip-fab"
            onClick={() => setIsFlipped(!isFlipped)}
          >
            {isFlipped ? 'View Map' : 'View Data'}
          </button>
        )}

        <div className="map-card-perspective">
          <div className={`map-card-inner ${isFlipped ? 'is-flipped' : ''}`}>
            
            {/* FRONT OF CARD (Map & Overlays) */}
            <div className="map-card-front">
              {/* Loading overlay */}
              {loading && (
                <div className="loading-overlay">
                  <div className="spatial-spinner"></div>
                  <p className="loading-text">Optimizing EV station placements…</p>
                </div>
              )}

              {error && !loading && (
                <div className="error-alert">
                  <h3 className="error-title">Backend Connection Notice</h3>
                  <p className="error-desc">{error}</p>
                  <p className="error-hint">
                    The Render spatial backend service may be spinning up from idle (~30-45s).
                  </p>
                  {onRetry && (
                    <button onClick={onRetry} className="retry-btn" style={{
                      marginTop: '12px',
                      padding: '8px 16px',
                      background: 'var(--accent-color)',
                      border: 'none',
                      borderRadius: '4px',
                      color: '#fff',
                      fontWeight: '600',
                      cursor: 'pointer'
                    }}>
                      ↻ Retry Connection
                    </button>
                  )}
                </div>
              )}

              {!error && mapHtml && (
                <div className="map-container" style={{ position: 'relative', overflow: 'hidden', height: '100%' }}>
                  <iframe
                    srcDoc={mapHtml}
                    title="EV Station Optimization Map"
                    className="map-iframe"
                  />
                </div>
              )}

              {!loading && !error && !mapHtml && (
                <div className="map-empty-state">
                  <div className="empty-icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--accent-color)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
                      <line x1="8" y1="2" x2="8" y2="18"/>
                      <line x1="16" y1="6" x2="16" y2="22"/>
                    </svg>
                  </div>
                  <h3 className="empty-title">Spatial Map Canvas Ready</h3>
                  <p className="empty-text">Configure your region &amp; parameters, then click "Optimize Placement" to generate non-clustered EV station nodes.</p>
                </div>
              )}
            </div>

            {/* BACK OF CARD (Data Table) */}
            <div className="map-card-back">
              <div className="data-table-container">
                {pointsData.length > 0 ? (
                  <table className="data-table">
                    {(() => {
                      const hasExtendedData = pointsData[0].demand_score !== undefined;
                      return (
                        <>
                          <thead>
                            <tr>
                              <th>#</th>
                              <th>Latitude</th>
                              <th>Longitude</th>
                              {hasExtendedData && <th>State</th>}
                              {hasExtendedData && <th>District</th>}
                              {hasExtendedData && <th>Demand Score</th>}
                            </tr>
                          </thead>
                          <tbody>
                            {pointsData.map((point) => (
                              <tr key={point.id}>
                                <td>{point.id}</td>
                                <td>{point.lat.toFixed(6)}</td>
                                <td>{point.lon.toFixed(6)}</td>
                                {hasExtendedData && <td>{point.state || 'N/A'}</td>}
                                {hasExtendedData && <td>{point.district || 'N/A'}</td>}
                                {hasExtendedData && <td>{point.demand_score !== null ? point.demand_score.toFixed(3) : 'N/A'}</td>}
                              </tr>
                            ))}
                          </tbody>
                        </>
                      );
                    })()}
                  </table>
                ) : (
                  <div className="empty-data-state">
                    <p>No coordinate data available.</p>
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}

export default MapViewer;
