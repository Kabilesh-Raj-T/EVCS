import React, { useState } from 'react';
import { Form, Button, Card } from 'react-bootstrap';
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
    <Card className="control-panel glass-card">
      <Card.Body>
        <Card.Title className="panel-title">⚙️ Station Optimization</Card.Title>
        <p className="panel-subtitle">
          Adjust parameters and explore optimized EV station placement.
        </p>

        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3">
            <Form.Label>Number of New Stations</Form.Label>
            <Form.Control
              type="number"
              name="k"
              value={formData.k}
              onChange={handleChange}
              min="1"
              max="150"
              required
            />
          </Form.Group>

          <Form.Group className="mb-4">
            <Form.Label>Grid Resolution</Form.Label>
            <Form.Control
              type="number"
              name="resolution"
              value={formData.resolution}
              onChange={handleChange}
              min="10"
              max="500"
              required
            />
            <Form.Text className="text-hint">
              Higher resolution = finer accuracy (but slower)
            </Form.Text>
          </Form.Group>

          <h6 className="section-title">🗺 Geographic Bounds</h6>

          <div className="grid-inputs">
            <Form.Group>
              <Form.Label>Lat Min</Form.Label>
              <Form.Control
                type="number"
                name="lat_min"
                value={formData.lat_min}
                onChange={handleChange}
                step="0.1"
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Lat Max</Form.Label>
              <Form.Control
                type="number"
                name="lat_max"
                value={formData.lat_max}
                onChange={handleChange}
                step="0.1"
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Lon Min</Form.Label>
              <Form.Control
                type="number"
                name="lon_min"
                value={formData.lon_min}
                onChange={handleChange}
                step="0.1"
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Lon Max</Form.Label>
              <Form.Control
                type="number"
                name="lon_max"
                value={formData.lon_max}
                onChange={handleChange}
                step="0.1"
                required
              />
            </Form.Group>
          </div>

          <div className="button-group">
            <Button
              variant="primary"
              type="submit"
              disabled={loading}
              className="w-100 mb-2 action-btn"
            >
              {loading ? 'Optimizing...' : '🔍 Run Optimization'}
            </Button>
            <Button
              variant="outline-light"
              onClick={handleReset}
              disabled={loading}
              className="w-100 reset-btn"
            >
              Reset Defaults
            </Button>
          </div>
        </Form>
      </Card.Body>
    </Card>
  );
}

export default ControlPanel;
