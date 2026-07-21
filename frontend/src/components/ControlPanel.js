import React, { useState } from 'react';
import './ControlPanel.css';

function ControlPanel({ params, defaultParams, regions, regionsLoading, onOptimize, loading }) {
  const [formData, setFormData] = useState(params);
  const states = regions?.states || [];
  const selectedState = states.find(state => state.name === formData.region_name);
  const districts = selectedState?.districts || [];

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
          <label className="form-label">Coverage Area</label>
          <select
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
            <label className="form-label">State</label>
            <select
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
            <label className="form-label">District</label>
            <select
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
          <label className="form-label">Optimizer</label>
          <select
            name="optimizer"
            className="form-select"
            value={formData.optimizer || 'greedy'}
            onChange={handleTextChange}
            disabled={loading}
          >
            <option value="greedy">Greedy Coverage</option>
            <option value="weighted">Weighted Demand</option>
          </select>
        </div>

        <div className="form-group mb-4">
          <label className="form-label">Number of New Stations</label>
          <input
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
