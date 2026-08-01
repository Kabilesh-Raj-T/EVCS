import './ProjectsSection.css';
import React from 'react';
import { splitWords, handleChipHover } from './utils';

const ProjectsSection = ({ onToggleApp }) => {
  return (
    <div id="work" className="projects-scroll-wrapper">
      <div className="projects-sticky-pin">
        <div className="projects-sticky-inner">
          <div className="section-label">01 / Projects</div>

          {/* TARS Progress Indicator (parallel to title) */}
          <div className="tars-progress-container">
            <span className="tars-progress-label">Mission Progress</span>
            <div className="tars-progress-line">
              <div className="tars-progress-fill"></div>
            </div>
            <div className="tars-container">
              <div className="tars-shadow"></div>
              <div className="tars-robot">
                <div className="tars-limb limb-1"></div>
                <div className="tars-limb limb-2">
                  <span className="tars-name">TARS</span>
                </div>
                <div className="tars-limb limb-3">
                  <div className="tars-sensor"></div>
                </div>
                <div className="tars-limb limb-4"></div>
              </div>
            </div>
          </div>

          <div className="projects-track-viewport">
            <div className="projects-track">

              {/* Project Card 1 */}
              <div className="project-card-slide revealed">
                <div className="project-header">
                  <h2 className="project-num">01.</h2>
                  <h3 className="project-title">
                    {splitWords("Demand-Aware EV Charging Infrastructure Optimization System")}
                  </h3>
                </div>
                <div className="project-details">
                  <ul className="project-bullets">
                    <li>Engineered a geospatial site-recommendation system for EV charging in India, fusing population-density rasters, 39K+ existing charging stations, and 3M+ OpenStreetMap road/POI records into a 4,694-location demand feature set, served via a Flask API and React frontend.</li>
                    <li>Implemented a KD-tree-accelerated greedy k-center optimization algorithm, processing 10K candidate locations in under 40 ms and accelerating nearest-neighbor queries by 135× over brute-force search.</li>
                  </ul>
                  <div className="project-tags">
                    <span onMouseEnter={handleChipHover}>Python</span>
                    <span onMouseEnter={handleChipHover}>GeoPandas</span>
                    <span onMouseEnter={handleChipHover}>Flask</span>
                    <span onMouseEnter={handleChipHover}>KD-Tree</span>
                    <span onMouseEnter={handleChipHover}>React</span>
                    <span onMouseEnter={handleChipHover}>Azure</span>
                    <span onMouseEnter={handleChipHover}>GitHub Actions</span>
                  </div>
                  <button onClick={onToggleApp} className="project-link-btn">
                    Launch Live Application →
                  </button>
                </div>
              </div>

              {/* Project Card 2 */}
              <div className="project-card-slide revealed">
                <div className="project-header">
                  <h2 className="project-num">02.</h2>
                  <h3 className="project-title">
                    {splitWords("Machine Learning–Based Edible Oil Adulteration Detection")}
                  </h3>
                </div>
                <div className="project-details">
                  <ul className="project-bullets">
                    <li>Built a real-time oil-degradation sensing system fusing OTDR-based fiber-optic reflectance with AS7341 11-channel multispectral sensing on a custom ESP32 + PCB, streaming readings to a REST API for cloud-hosted inference.</li>
                    <li>Trained and benchmarked 5+ regression models (Linear, Ridge, Lasso, Random Forest, Gradient Boosting, Stacking) per oil type, selecting the best performer per oil to predict thermal degradation stage at up to R² = 0.974.</li>
                  </ul>
                  <div className="project-tags">
                    <span onMouseEnter={handleChipHover}>Python</span>
                    <span onMouseEnter={handleChipHover}>Scikit-Learn</span>
                    <span onMouseEnter={handleChipHover}>Flask</span>
                    <span onMouseEnter={handleChipHover}>ESP32</span>
                    <span onMouseEnter={handleChipHover}>IoT Sensing</span>
                    <span onMouseEnter={handleChipHover}>Pandas</span>
                  </div>
                  <a href="https://oiladulterationmlmodels-xzq2pkrg5ubjm5t4hfprmr.streamlit.app/" target="_blank" rel="noreferrer" className="project-link">
                    View Streamlit Demo ↗
                  </a>
                </div>
              </div>

              {/* Project Card 3 */}
              <div className="project-card-slide revealed">
                <div className="project-header">
                  <h2 className="project-num">03.</h2>
                  <h3 className="project-title">
                    {splitWords("CLI-Based Cloud Retail Management System")}
                  </h3>
                </div>
                <div className="project-details">
                  <ul className="project-bullets">
                    <li>Built and containerized an object-oriented retail management system using Python, MySQL, and Docker, deployed on Azure with Azure Database for MySQL Flexible Server.</li>
                    <li>Built a dynamic pricing engine that adjusts prices using days-to-expiry and trailing 30-day demand, and indexed core MySQL tables across 100k+ records to cut query latency by up to 84%.</li>
                  </ul>
                  <div className="project-tags">
                    <span onMouseEnter={handleChipHover}>Python</span>
                    <span onMouseEnter={handleChipHover}>MySQL</span>
                    <span onMouseEnter={handleChipHover}>Docker</span>
                    <span onMouseEnter={handleChipHover}>Azure Database</span>
                    <span onMouseEnter={handleChipHover}>OOP</span>
                    <span onMouseEnter={handleChipHover}>Query Tuning</span>
                  </div>
                  <a href="https://github.com/Kabilesh-Raj-T/SMS" target="_blank" rel="noreferrer" className="project-link">
                    View Repository ↗
                  </a>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectsSection;
