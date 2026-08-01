import './HeroSection.css';
import React from 'react';
import Moon3D from '../motion/Moon3D';
import { splitText, splitWords } from './utils';

const HeroSection = ({ isBackendReady }) => {
  return (
    <section className="portfolio-hero revealed">
      {!isBackendReady && (
        <div className="boot-message-container">
          <div className="boot-message">
            <span className="spinner-indicator"></span>
            Setting up spatial backend nodes (Render free tier | ~45s). Explore the portfolio in the meantime.
          </div>
        </div>
      )}

      {/* 3D Rotating Moon Graphic */}
      <div className="hero-moon-wrapper">
        <div className="hero-moon-graphic">
          <Moon3D />
        </div>
      </div>

      <div className="hero-layout" style={{ width: '100%', position: 'relative' }}>
        <div className="hero-main" style={{ width: '100%' }}>
          <h1 className="hero-name">{splitText("T KABILESH RAJ")}</h1>

          <div className="hero-tagline-group" style={{ width: '100%' }}>
            <span className="hero-role">Aspiring Software Engineer</span>
            <p className="hero-description" style={{ width: '100%', maxWidth: '100%' }}>
              {splitWords("With a strong foundation in backend development, databases, and machine learning. I build end-to-end applications that combine clean architecture, scalable systems, and data-driven decision making.")}
            </p>
          </div>
        </div>

        <div className="hero-meta">
          <div className="meta-item">
            <span className="meta-label">Education</span>
            <span className="meta-val">Madras Institute of Technology, Anna University</span>
          </div>

          <div className="meta-item">
            <span className="meta-label">Contact &amp; Socials</span>
            <div className="hero-socials">
              <a href="mailto:tkabileshraj04@gmail.com">tkabileshraj04@gmail.com</a>
              <a href="https://www.linkedin.com/in/kabilesh-raj-t-17b7ab270" target="_blank" rel="noreferrer">LinkedIn ↗</a>
              <a href="https://github.com/Kabilesh-Raj-T" target="_blank" rel="noreferrer">GitHub ↗</a>
              <a href="https://leetcode.com/u/E5HxFWQBan/" target="_blank" rel="noreferrer">LeetCode ↗</a>
            </div>
          </div>
        </div>

        <div className="hero-explore" style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
          <span className="meta-label">Explore</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem', marginTop: '0.5rem' }}>
            <a href="#work" className="hero-scroll-indicator" style={{ marginTop: 0 }}>↓ Projects</a>
            {/* Hamilton Watch Morse Indicator */}
            <div className="hamilton-watch" title="Cooper's Watch ticking 'STAY' in Morse code">
              <div className="watch-face">
                <div className="watch-center"></div>
                <div className="watch-second-hand"></div>
                <span className="watch-led"></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
