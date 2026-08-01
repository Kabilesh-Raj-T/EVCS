import React from 'react';
import './BackendStatus.css';

const BackendStatus = ({ isReady }) => {
  return (
    <div className={`backend-status ${isReady ? 'ready' : ''}`}>
      {!isReady ? (
        <>
          <div className="spinner"></div>
          Waking up backend...
        </>
      ) : (
        <>
          <div className="check-icon">
            <svg width="12" height="10" viewBox="0 0 12 10" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M1 5L4.5 8.5L11 1.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          Backend is online!
        </>
      )}
    </div>
  );
};

export default BackendStatus;
