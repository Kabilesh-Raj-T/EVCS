import React, { useState } from 'react';
import './ControlPanel.css';

function ControlPanel({ params, onOptimize, loading }) {
  const [formData, setFormData] = useState(params);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value === '' ? '' : parseFloat(value)
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onOptimize(formData);
  };

  const handleReset = () => {
    const defaultParams = {
      k: 5,
      resolution: 100,
      lat_min: 8.0,
      lat_max: 13.5,
      lon_min: 76.0,
      lon_max: 80.5
    };
    setFormData(defaultParams);
    onOptimize(defaultParams);
  };

  return (
    <div className="control-panel">
      <h2 className="panel-title">Station Optimization</h2>
      <p className="panel-subtitle">
        Adjust parameters and explore optimized EV station placement.
      </p>

      <form onSubmit={handleSubmit}>
        <div className="form-group mb-4">
          <label className="form-label">Number of New Stations</label>
          <input
            type="number"
            name="k"
            className="form-control"
            value={formData.k}
            onChange={handleChange}
            min="1"
            max="150"
            required
          />
        </div>

        <div className="form-group mb-4">
          <label className="form-label">Grid Resolution</label>
          <input
            type="number"
            name="resolution"
            className="form-control"
            value={formData.resolution}
            onChange={handleChange}
            min="10"
            max="500"
            required
          />
          <span className="text-hint">
            Higher resolution = finer accuracy (but slower)
          </span>
        </div>

        <h3 className="section-title">Geographic Bounds</h3>

        <div className="grid-inputs">
          <div className="form-group">
            <label className="form-label">Latitude Min</label>
            <input
              type="number"
              name="lat_min"
              className="form-control"
              value={formData.lat_min}
              onChange={handleChange}
              step="0.1"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Latitude Max</label>
            <input
              type="number"
              name="lat_max"
              className="form-control"
              value={formData.lat_max}
              onChange={handleChange}
              step="0.1"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Longitude Min</label>
            <input
              type="number"
              name="lon_min"
              className="form-control"
              value={formData.lon_min}
              onChange={handleChange}
              step="0.1"
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Longitude Max</label>
            <input
              type="number"
              name="lon_max"
              className="form-control"
              value={formData.lon_max}
              onChange={handleChange}
              step="0.1"
              required
            />
          </div>
        </div>

        <div className="button-group">
          <button
            type="submit"
            disabled={loading}
            className="action-btn"
          >
            {loading ? 'Optimizing...' : 'Optimize'}
          </button>
          <button
            type="button"
            onClick={handleReset}
            disabled={loading}
            className="reset-btn"
          >
            Reset
          </button>
        </div>
      </form>
    </div>
  );
}

export default ControlPanel;
