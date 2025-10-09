# EV Station Optimizer - Tamil Nadu

## Overview
An interactive web application for optimizing electric vehicle (EV) charging station placement in Tamil Nadu. The application uses data-driven insights to suggest optimal locations for new EV stations based on existing station data and geographic constraints.

## Technology Stack

### Frontend
- **React 19.2.0** - UI framework with functional components and hooks
- **React Bootstrap 2.10.10** - UI components and styling
- **Axios 1.12.2** - HTTP client for API requests
- **Bootstrap 5.3.8** - CSS framework

### Backend
- **Flask 3.1.2** - Python web framework
- **Flask-CORS 6.0.1** - Cross-origin resource sharing
- **Folium 0.20.0** - Interactive map generation
- **Pandas 2.3.3** - Data processing
- **NumPy 2.3.3** - Numerical computations
- **Scikit-learn 1.7.2** - K-means clustering for station optimization

## Features

### Core Functionality
1. **Interactive Heatmap Display** - Visualizes existing EV stations across Tamil Nadu
2. **Optimization Algorithm** - Uses K-means clustering and grid-based optimization to suggest new station locations
3. **Parameter Controls** - Adjustable settings for:
   - Number of new stations (k)
   - Optimization resolution
   - Geographic bounds (latitude/longitude)
4. **Real-time Updates** - Dynamic map regeneration based on parameter changes
5. **Tamil Nadu Boundary Overlay** - Geographic context with state boundaries

### User Interface
- Clean, modern design with gradient background
- Sidebar control panel for parameter adjustment
- Main map viewer with iframe-based Folium map rendering
- Error handling and loading states
- Responsive layout

## Project Structure

```
/
├── backend/
│   ├── app.py                    # Flask backend with /optimize endpoint
│   ├── stations.csv              # EV station data for Tamil Nadu
│   └── tamilnadu.geojson         # Geographic boundary data
├── src/
│   ├── App.js                    # Main React application
│   ├── App.css                   # App styling
│   ├── index.js                  # React entry point
│   ├── index.css                 # Global styles
│   └── components/
│       ├── ControlPanel.js       # Parameter input form
│       ├── ControlPanel.css      # Control panel styling
│       ├── MapViewer.js          # Map display component
│       └── MapViewer.css         # Map viewer styling
├── public/
│   └── index.html                # HTML template
├── package.json                  # Node.js dependencies and scripts
├── pyproject.toml                # Python dependencies
└── .gitignore                    # Git ignore rules

## Workflows

### Backend Workflow
- **Name**: Backend
- **Command**: `cd backend && python app.py`
- **Port**: 8000
- **Type**: Console (API server)

### Frontend Workflow
- **Name**: Frontend
- **Command**: `BROWSER=none PORT=5000 npm start`
- **Port**: 5000
- **Type**: Webview (React development server)

## API Endpoints

### POST /optimize
Generates optimized EV station placement suggestions.

**Request Body:**
```json
{
  "k": 5,
  "resolution": 100,
  "lat_min": 8.0,
  "lat_max": 13.5,
  "lon_min": 76.0,
  "lon_max": 80.5
}
```

**Response:**
- Returns HTML containing a Folium map with:
  - Heatmap of existing stations
  - Red markers for suggested new stations
  - Tamil Nadu boundary overlay

## Optimization Algorithm

1. **Data Filtering**: Filters existing stations within specified geographic bounds
2. **K-means Clustering**: When sufficient existing stations are present, uses K-means to find optimal cluster centers
3. **Grid-based Optimization**: For sparse data, evaluates grid points and selects locations maximizing distance from existing stations
4. **Visualization**: Generates interactive Folium map with heatmap and marker layers

## Development Notes

### Port Configuration
- Backend runs on port 8000 (Flask API)
- Frontend runs on port 5000 (React dev server with proxy to backend)
- Proxy configuration in package.json routes API requests to backend

### Data Files
- `stations.csv`: Contains 30 existing EV stations across Tamil Nadu with coordinates
- `tamilnadu.geojson`: Polygon boundary data for Tamil Nadu state

### Environment Setup
- Python 3.11 with uv package manager
- Node.js 20 with npm
- Virtual environment in `.pythonlibs/`
- Node modules in `node_modules/`

## Recent Changes (October 9, 2025)

### Initial Implementation
- Created Flask backend with optimization endpoint
- Implemented React frontend with component architecture
- Set up workflows for backend and frontend servers
- Added proxy configuration for API communication
- Fixed file path issues for data files (CSV and GeoJSON)
- Successfully tested map generation and parameter updates

## Usage

1. **Start the Application**: Both workflows start automatically
2. **View the Map**: Default map loads on page load showing Tamil Nadu
3. **Adjust Parameters**: Use the control panel to modify:
   - Number of stations to suggest
   - Optimization resolution
   - Geographic bounds
4. **Optimize**: Click "Optimize Stations" to generate new suggestions
5. **View Results**: Interactive map updates with suggested locations

## Future Enhancements

Potential features for next phase:
- User accounts for saving custom configurations
- Station placement history and comparison views
- Export functionality for map data and coordinates
- Additional constraints (population density, road networks)
- Cost estimation and ROI calculations
- Multi-region support beyond Tamil Nadu
