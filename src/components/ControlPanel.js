import React, { useState } from 'react';
import { Form, Button, Card } from 'react-bootstrap';
import './ControlPanel.css';

function ControlPanel({ params, onOptimize, loading }) {
  const [formData, setFormData] = useState(params);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: parseFloat(value) || 0
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
    <Card className="control-panel">
      <Card.Body>
        <Card.Title className="panel-title">⚙️ Optimization Parameters</Card.Title>
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3">
            <Form.Label>Number of New Stations (k)</Form.Label>
            <Form.Control
              type="number"
              name="k"
              value={formData.k}
              onChange={handleChange}
              min="1"
              max="50"
              required
            />
            <Form.Text className="text-muted">
              Number of new EV stations to suggest
            </Form.Text>
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Resolution</Form.Label>
            <Form.Control
              type="number"
              name="resolution"
              value={formData.resolution}
              onChange={handleChange}
              min="10"
              max="500"
              required
            />
            <Form.Text className="text-muted">
              Grid resolution for optimization (higher = more precise but slower)
            </Form.Text>
          </Form.Group>

          <hr />

          <h6 className="section-title">Geographic Bounds</h6>

          <Form.Group className="mb-3">
            <Form.Label>Latitude Min</Form.Label>
            <Form.Control
              type="number"
              name="lat_min"
              value={formData.lat_min}
              onChange={handleChange}
              step="0.1"
              required
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Latitude Max</Form.Label>
            <Form.Control
              type="number"
              name="lat_max"
              value={formData.lat_max}
              onChange={handleChange}
              step="0.1"
              required
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Longitude Min</Form.Label>
            <Form.Control
              type="number"
              name="lon_min"
              value={formData.lon_min}
              onChange={handleChange}
              step="0.1"
              required
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>Longitude Max</Form.Label>
            <Form.Control
              type="number"
              name="lon_max"
              value={formData.lon_max}
              onChange={handleChange}
              step="0.1"
              required
            />
          </Form.Group>

          <div className="button-group">
            <Button 
              variant="primary" 
              type="submit" 
              disabled={loading}
              className="w-100 mb-2"
            >
              {loading ? 'Optimizing...' : '🔍 Optimize Stations'}
            </Button>
            <Button 
              variant="outline-secondary" 
              onClick={handleReset}
              disabled={loading}
              className="w-100"
            >
              Reset to Defaults
            </Button>
          </div>
        </Form>
      </Card.Body>
    </Card>
  );
}

export default ControlPanel;
