import React, { useState, useRef } from 'react';
import './ControlPanel.css';
import { animate, prefersReducedMotion } from '../utils/motion';

function ControlPanel({ params, defaultParams, regions, regionsLoading, onOptimize, loading, error }) {
  const [formData, setFormData] = useState(params);
  const states = regions?.states || [];
  const selectedState = states.find(state => state.name === formData.region_name);
  const districts = selectedState?.districts || [];
  // Track previous error to detect new errors (not just re-renders)
  const prevErrorRef = useRef(null);

  // ── Phase 6: Error shake on the submit button ─────────────────────────────
  // Fires whenever the error prop changes to a truthy value (new error arrived).
  if (error && error !== prevErrorRef.current) {
    prevErrorRef.current = error;
    if (!prefersReducedMotion()) {
      // rAF so we don't trigger during render
      requestAnimationFrame(() => {
        animate('.action-btn', {
          translateX: [0, -6, 6, -4, 4, -2, 2, 0],
          duration: 450,
          ease: 'linear',
        });
      });
    }
  } else if (!error) {
    prevErrorRef.current = null;
  }

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value === '' ? '' : parseInt(value, 10)
    }));
  };

  const firstState = () => states[0]?.name || '';

  const firstDistrictForState = (stateName) => {
    const state = states.find(item => item.name === stateName);
    return state?.districts?.[0]?.name || '';
  };

  const handleRegionTypeChange = (e) => {
    const regionType = e.target.value;
    const nextState = regionType === 'all_india' ? '' : (formData.region_name || firstState());
    setFormData(prev => ({
      ...prev,
      region_type: regionType,
      region_name: nextState,
      district: regionType === 'district' ? firstDistrictForState(nextState) : ''
    }));
  };

  const handleStateChange = (e) => {
    const stateName = e.target.value;
    setFormData(prev => ({
      ...prev,
      region_name: stateName,
      district: prev.region_type === 'district' ? firstDistrictForState(stateName) : ''
    }));
  };

  const handleDistrictChange = (e) => {
    setFormData(prev => ({
      ...prev,
      district: e.target.value
    }));
  };

  const handleTextChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onOptimize(formData);
  };

  const handleReset = () => {
    setFormData(defaultParams);
    onOptimize(defaultParams);
  };

  return (
    <div className="control-panel">
      <h2 className="panel-title">India Station Optimization</h2>
      <p className="panel-subtitle">
        Adjust parameters and explore EV station placement across India.
      </p>

      <form onSubmit={handleSubmit}>
        <h3 className="section-title">Region</h3>

        <div className="form-group mb-4">
          <label htmlFor="ctrl-region-type" className="form-label">Coverage Area</label>
          <select
            id="ctrl-region-type"
            name="region_type"
            className="form-select"
            value={formData.region_type}
            onChange={handleRegionTypeChange}
            disabled={loading || regionsLoading}
          >
            <option value="all_india">All India</option>
            <option value="state">State</option>
            <option value="district">District</option>
          </select>
          <span className="text-hint">
            Bounds are calculated automatically from your selection
          </span>
        </div>

        {formData.region_type !== 'all_india' && (
          <div className="form-group mb-4">
            <label htmlFor="ctrl-region-name" className="form-label">State</label>
            <select
              id="ctrl-region-name"
              name="region_name"
              className="form-select"
              value={formData.region_name}
              onChange={handleStateChange}
              disabled={loading || regionsLoading || states.length === 0}
              required
            >
              <option value="" disabled>
                {regionsLoading ? 'Loading states...' : 'Select state'}
              </option>
              {states.map(state => (
                <option key={state.name} value={state.name}>
                  {state.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {formData.region_type === 'district' && (
          <div className="form-group mb-4">
            <label htmlFor="ctrl-district" className="form-label">District</label>
            <select
              id="ctrl-district"
              name="district"
              className="form-select"
              value={formData.district}
              onChange={handleDistrictChange}
              disabled={loading || regionsLoading || districts.length === 0}
              required
            >
              <option value="" disabled>
                {districts.length === 0 ? 'Select state first' : 'Select district'}
              </option>
              {districts.map(district => (
                <option key={district.name} value={district.name}>
                  {district.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <h3 className="section-title">Optimization</h3>

        <div className="form-group mb-4">
          <label htmlFor="ctrl-optimizer" className="form-label">Optimizer</label>
          <select
            id="ctrl-optimizer"
            name="optimizer"
            className="form-select"
            value={formData.optimizer || 'weighted'}
            onChange={handleTextChange}
            disabled={loading}
          >
            <option value="greedy">Greedy Coverage</option>
            <option value="weighted">Weighted Demand</option>
          </select>
        </div>

        <div className="form-group mb-4">
          <label htmlFor="ctrl-k" className="form-label">Number of New Stations</label>
          <input
            id="ctrl-k"
            type="number"
            name="k"
            className="form-control"
            value={formData.k}
            onChange={handleChange}
            min="0"
            max="1000"
            required
          />
          <span className="text-hint">
            Use 0 to view existing station density only
          </span>
        </div>

        <div className="form-group mb-4">
          <label htmlFor="ctrl-resolution" className="form-label">Grid Resolution</label>
          <input
            id="ctrl-resolution"
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
