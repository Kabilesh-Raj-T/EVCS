# EV Station Locator

This project is a full-stack web application that helps find optimal locations for new EV charging stations in Tamil Nadu, India.

## Architecture

- **Backend:** A Python Flask server that handles data processing.
- **Frontend:** A React application that provides the user interface.

## How to Run

You will need to run two separate servers for the backend and frontend.

### 1. Backend Server

The backend is a Flask application located in the `backend/` directory.

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Install Python dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: A `requirements.txt` file will be generated in a subsequent step)*

3.  **Run the Flask server:**
    ```bash
    python app.py
    ```
    The server will start on `http://localhost:8080`.

### 2. Frontend Server

The frontend is a React application located in the `frontend/` directory.

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```

3.  **Run the React development server:**
    ```bash
    npm start
    ```
    The application will open in your browser at `http://localhost:3000`.

## How to Use

1.  Open the web application in your browser (`http://localhost:3000`).
2.  Upload a CSV file containing EV station data. A sample file (`ev-charging-stations-india.csv`) is provided in the `backend/` directory.
3.  Adjust the latitude and longitude ranges if needed.
4.  Set the number of new stations to be located.
5.  Click "Find Optimal Locations".
6.  The map will display the optimal locations for new stations.
