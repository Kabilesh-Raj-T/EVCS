import React from 'react';
import { Card, Spinner, Alert } from 'react-bootstrap';
import './MapViewer.css';

function MapViewer({ mapHtml, loading, error }) {
  return (
    <Card className="map-viewer">
      <Card.Body className="map-body">
        {loading && (
          <div className="loading-container">
            <Spinner animation="border" variant="primary" />
            <p className="mt-3">Generating optimized station locations...</p>
          </div>
        )}
        
        {error && (
          <Alert variant="danger" className="error-alert">
            <Alert.Heading>Error Loading Map</Alert.Heading>
            <p>{error}</p>
            <p className="mb-0">
              Please ensure the Flask backend is running on port 5000.
            </p>
          </Alert>
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
            <p>Initializing map...</p>
          </div>
        )}
      </Card.Body>
    </Card>
  );
}

export default MapViewer;
