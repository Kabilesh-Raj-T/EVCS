import React, { useState } from 'react';
import './App.css';

function App() {
    const [file, setFile] = useState(null);
    const [latMin, setLatMin] = useState('9.2');
    const [latMax, setLatMax] = useState('12.9');
    const [lonMin, setLonMin] = useState('76.9');
    const [lonMax, setLonMax] = useState('79.9');
    const [numNew, setNumNew] = useState('5');
    const [mapHtml, setMapHtml] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file) {
            setError('Please select a CSV file.');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('lat_min', latMin);
        formData.append('lat_max', latMax);
        formData.append('lon_min', lonMin);
        formData.append('lon_max', lonMax);
        formData.append('num_new', numNew);

        setLoading(true);
        setError('');
        setMapHtml('');

        try {
            const response = await fetch('http://localhost:8080/api/process', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Something went wrong');
            }

            const data = await response.json();
            setMapHtml(data.map_html);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="App">
            <header className="App-header">
                <h1>EV Station Locator</h1>
            </header>
            <main>
                <form onSubmit={handleSubmit} className="control-panel">
                    <h2>Controls</h2>
                    <div className="form-group">
                        <label>Upload CSV:</label>
                        <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files[0])} required />
                    </div>
                    <div className="form-group">
                        <label>Latitude Range:</label>
                        <input type="number" value={latMin} onChange={(e) => setLatMin(e.target.value)} placeholder="Min" step="any" required />
                        <input type="number" value={latMax} onChange={(e) => setLatMax(e.target.value)} placeholder="Max" step="any" required />
                    </div>
                    <div className="form-group">
                        <label>Longitude Range:</label>
                        <input type="number" value={lonMin} onChange={(e) => setLonMin(e.target.value)} placeholder="Min" step="any" required />
                        <input type="number" value={lonMax} onChange={(e) => setLonMax(e.target.value)} placeholder="Max" step="any" required />
                    </div>
                    <div className="form-group">
                        <label>Number of New Stations:</label>
                        <input type="number" value={numNew} onChange={(e) => setNumNew(e.target.value)} min="1" required />
                    </div>
                    <button type="submit" disabled={loading}>
                        {loading ? 'Processing...' : 'Find Optimal Locations'}
                    </button>
                    {error && <p className="error">{error}</p>}
                </form>
                <div className="map-container">
                    {loading && <div className="loader"></div>}
                    {mapHtml ? (
                        <iframe
                            title="map"
                            srcDoc={mapHtml}
                            style={{ width: '100%', height: '100%', border: 'none' }}
                        />
                    ) : (
                        !loading && <div className="placeholder">Map will be displayed here</div>
                    )}
                </div>
            </main>
        </div>
    );
}

export default App;
