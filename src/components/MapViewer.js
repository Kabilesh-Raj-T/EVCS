import React from 'react';

function MapViewer({ mapHtml, loading, error }) {
  if (loading) return <p>Loading map...</p>;
  if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;
  if (!mapHtml) return <p>Initializing map...</p>;

  return (
    <iframe
      srcDoc={mapHtml}
      title="EV Map"
      style={{ width: '100%', height: '600px', border: 'none' }}
      sandbox="allow-scripts allow-same-origin"
    />
  );
}

export default MapViewer;
