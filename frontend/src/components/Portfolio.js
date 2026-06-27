import React, { useEffect, useRef } from 'react';
import './Portfolio.css';

const Portfolio = ({ isTransitioning, isBackendReady, onToggleApp }) => {
  const revealRefs = useRef([]);
  revealRefs.current = [];

  const addToRefs = (el) => {
    if (el && !revealRefs.current.includes(el)) {
      revealRefs.current.push(el);
    }
  };

  const splitText = (text) => {
    return text.split('').map((char, index) => {
      if (char === ' ') {
        return <span key={index} style={{ display: 'inline-block', width: '0.25em' }}>&nbsp;</span>;
      }
      return (
        <span key={index} className="reveal-char-wrapper">
          <span className="reveal-char" style={{ transitionDelay: `${index * 0.04}s` }}>
            {char}
          </span>
        </span>
      );
    });
  };

  const splitWords = (text) => {
    return text.split(' ').map((word, index) => {
      return (
        <span key={index} className="reveal-word-wrapper">
          <span className="reveal-word" style={{ transitionDelay: `${index * 0.06}s` }}>
            {word}&nbsp;
          </span>
        </span>
      );
    });
  };

  useEffect(() => {
    const revealElementsInView = () => {
      revealRefs.current.forEach((ref) => {
        if (!ref) return;
        const rect = ref.getBoundingClientRect();
        if (rect.top < window.innerHeight * 0.92 && rect.bottom > 0) {
          ref.classList.add('revealed');
        }
      });

      document.querySelectorAll('.project-spread').forEach((proj) => {
        const rect = proj.getBoundingClientRect();
        if (rect.top < window.innerHeight * 0.85 && rect.bottom > window.innerHeight * 0.15) {
          proj.classList.add('project-active');
        }
      });
    };

    // 1. Reveal observer (adds .revealed when elements enter the screen)
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
          }
        });
      },
      { threshold: 0.05, rootMargin: '0px 0px -60px 0px' }
    );

    revealRefs.current.forEach((ref) => {
      if (ref) revealObserver.observe(ref);
    });

    // 2. Project focus observer (dims inactive projects, highlights active one)
    const projectObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('project-active');
          } else {
            entry.target.classList.remove('project-active');
          }
        });
      },
      {
        rootMargin: '-30% 0px -30% 0px', // Active when in the middle 40% of viewport
        threshold: 0.1
      }
    );

    const projects = document.querySelectorAll('.project-spread');
    projects.forEach((proj) => projectObserver.observe(proj));

    // 3. Bullet line highlighting observer (scroll-driven copy highlighting)
    const bulletObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('bullet-active');
            observer.unobserve(entry.target);
          }
        });
      },
      {
        rootMargin: '-40% 0px -40% 0px', // Focuses on the single item in the middle 20% of the screen
        threshold: 0.5
      }
    );

    const bullets = document.querySelectorAll('.project-bullets li');
    bullets.forEach((bullet) => bulletObserver.observe(bullet));

    // Scroll & Resize handler for ambient bg translation and skills circular scrollytelling
    let ticked = false;
    const handleScroll = () => {
      if (!ticked) {
        window.requestAnimationFrame(() => {
          const scrollTop = window.scrollY || document.documentElement.scrollTop;
          const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
          const ratio = scrollHeight > 0 ? scrollTop / scrollHeight : 0;
          document.documentElement.style.setProperty('--scroll-ratio', ratio.toFixed(4));
          
          // Calculate skills circular scrollytelling progress
          const skillsContainer = document.querySelector('.skills-scroll-container');
          if (skillsContainer) {
            const rect = skillsContainer.getBoundingClientRect();
            const containerHeight = rect.height;
            const scrolled = -rect.top;
            const scrollRange = containerHeight - window.innerHeight;
            let progress = 0;
            if (scrolled > 0 && scrollRange > 0) {
              progress = Math.min(Math.max(scrolled / scrollRange, 0), 1);
            }
            document.documentElement.style.setProperty('--skills-scroll-progress', progress.toFixed(4));
            
            // Calculate individual card angle and distance from center
            const cards = skillsContainer.querySelectorAll('.skills-card');
            cards.forEach((card, index) => {
              const targetProgress = index * 0.5;
              const diff = progress - targetProgress;
              const angle = diff * 70;
              const dist = Math.min(Math.abs(diff) * 2, 2);
              
              card.style.setProperty('--card-angle', `${angle.toFixed(2)}deg`);
              card.style.setProperty('--card-dist', dist.toFixed(4));
            });
          }
          ticked = false;
        });
        ticked = true;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleScroll, { passive: true });
    window.addEventListener('hashchange', revealElementsInView);
    handleScroll();
    revealElementsInView();
    requestAnimationFrame(revealElementsInView);

    return () => {
      revealObserver.disconnect();
      projectObserver.disconnect();
      bulletObserver.disconnect();
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleScroll);
      window.removeEventListener('hashchange', revealElementsInView);
    };
  }, []);

  return (
    <div className={`portfolio-container ${isTransitioning ? 'transitioning' : ''}`}>
      {/* Scroll-Driven Ambient Background Orbs */}
      <div className="ambient-bg">
        <div className="orb-wrapper orb-1">
          <div className="bg-glow-orb"></div>
        </div>
        <div className="orb-wrapper orb-2">
          <div className="bg-glow-orb"></div>
        </div>
        <div className="orb-wrapper orb-3">
          <div className="bg-glow-orb"></div>
        </div>
      </div>

      <style>{`
        .hero-description {
          text-align: justify !important;
          text-justify: inter-word !important;
          width: 100% !important;
          max-width: 100% !important;
          display: block !important;
        }
        .project-bullets li {
          text-align: justify !important;
          text-justify: inter-word !important;
          width: 100% !important;
        }
        .skills-sub-copy {
          text-align: justify !important;
          text-justify: inter-word !important;
          width: 100% !important;
        }
        .timeline-body-text {
          text-align: justify !important;
          text-justify: inter-word !important;
          width: 100% !important;
        }
      `}</style>
      {/* Intro Section */}
      <section className="portfolio-hero revealed" ref={addToRefs}>
        {!isBackendReady && (
          <div className="boot-message-container">
            <div className="boot-message">
              <span className="spinner-indicator"></span>
              Setting up spatial backend nodes (Render free tier | ~45s). Explore the portfolio in the meantime.
            </div>
          </div>
        )}

        <div className="hero-layout" style={{ width: '100%' }}>
          <div className="hero-main" style={{ width: '100%' }}>
            <h1 className="hero-name">{splitText("T KABILESH RAJ")}</h1>
            
            <div className="hero-tagline-group" style={{ width: '100%' }}>
              <span className="hero-role">Aspiring Software Engineer</span>
              <p className="hero-description" style={{ textAlign: 'justify', textJustify: 'inter-word', width: '100%', maxWidth: '100%' }}>
                With a strong foundation in backend development, databases, and machine learning. I build end-to-end applications that combine clean architecture, scalable systems, and data-driven decision making.
              </p>
            </div>
          </div>

          <div className="hero-meta">
            <div className="meta-item">
              <span className="meta-label">Education</span>
              <span className="meta-val">Madras Institute of Technology, Anna University</span>
            </div>
            
            <div className="meta-item">
              <span className="meta-label">Contact & Socials</span>
              <div className="hero-socials">
                <a href="mailto:tkabileshraj04@gmail.com">
                  tkabileshraj04@gmail.com
                </a>
                <a href="https://www.linkedin.com/in/kabilesh-raj-t-17b7ab270" target="_blank" rel="noreferrer">
                  LinkedIn ↗
                </a>
                <a href="https://github.com/Kabilesh-Raj-T" target="_blank" rel="noreferrer">
                  GitHub ↗
                </a>
                <a href="https://leetcode.com/u/E5HxFWQBan/" target="_blank" rel="noreferrer">
                  LeetCode ↗
                </a>
              </div>
            </div>
          </div>

          <div className="hero-explore" style={{ width: '100%' }}>
            <span className="meta-label">Explore</span>
            <a href="#work" className="hero-scroll-indicator">
              ↓ Projects
            </a>
          </div>
        </div>
      </section>

      {/* Projects Section */}
      <section id="work" className="portfolio-section" ref={addToRefs}>
        <div className="section-label">01 / Projects</div>
        <div className="projects-grid">
          {/* Project 1 - EV CS System */}
          <div className="project-spread" ref={addToRefs}>
            <div className="project-header">
              <h2 className="project-num">01.</h2>
              <h3 className="project-title">
                {splitWords("Geo-Optimized EV Station Placement System using Greedy KD-Tree Algorithm")}
              </h3>
            </div>
            <div className="project-details">
              <ul className="project-bullets">
                <li>Built a geospatial EV station placement system using Python, GeoPandas, Flask, and a KD-tree accelerated greedy algorithm to generate optimized, non-clustered station locations.</li>
                <li>Developed interactive maps and heatmaps using Folium and React for site analysis.</li>
                <li>Deployed the application on Azure App Services and GitHub Pages with CI/CD pipelines using GitHub Actions.</li>
              </ul>
              <div className="project-tags">
                <span>Python</span>
                <span>GeoPandas</span>
                <span>Flask</span>
                <span>KD-Tree</span>
                <span>React</span>
                <span>Azure</span>
                <span>GitHub Actions</span>
              </div>
              <button onClick={onToggleApp} className="project-link-btn">
                Launch Live Application →
              </button>
            </div>
          </div>

          {/* Project 2 - ML Edible Oil */}
          <div className="project-spread" ref={addToRefs}>
            <div className="project-header">
              <h2 className="project-num">02.</h2>
              <h3 className="project-title">
                {splitWords("Machine Learning–Based Edible Oil Adulteration Detection")}
              </h3>
            </div>
            <div className="project-details">
              <ul className="project-bullets">
                <li>Developed a real-time edible oil degradation analysis system integrating optical fiber sensing, ESP32 deployment, Flask REST APIs, and cloud-hosted ML inference.</li>
                <li>Trained and evaluated Extra Trees, AdaBoost, and MLP models using Pandas and Scikit-learn.</li>
                <li>Achieved up to R² = 0.974 for multi-oil degradation stage prediction.</li>
              </ul>
              <div className="project-tags">
                <span>Python</span>
                <span>Scikit-Learn</span>
                <span>Flask</span>
                <span>ESP32</span>
                <span>IoT Sensing</span>
                <span>Pandas</span>
              </div>
              <a href="https://oiladulterationmlmodels-xzq2pkrg5ubjm5t4hfprmr.streamlit.app/" target="_blank" rel="noreferrer" className="project-link">
                View Streamlit Demo ↗
              </a>
            </div>
          </div>

          {/* Project 3 - CLI Cloud Retail */}
          <div className="project-spread" ref={addToRefs}>
            <div className="project-header">
              <h2 className="project-num">03.</h2>
              <h3 className="project-title">
                {splitWords("CLI-Based Cloud Retail Management System")}
              </h3>
            </div>
            <div className="project-details">
              <ul className="project-bullets">
                <li>Built an object-oriented retail management system in Python using MySQL for inventory, customer, employee, and sales management.</li>
                <li>Developed a dynamic pricing engine and optimized indexed MySQL tables on 100k+ rows, improving query performance by up to 84%.</li>
                <li>Deployed the application on Azure using Docker and Azure Database for MySQL Flexible Server.</li>
              </ul>
              <div className="project-tags">
                <span>Python</span>
                <span>MySQL</span>
                <span>Docker</span>
                <span>Azure Database</span>
                <span>OOP</span>
                <span>Query Tuning</span>
              </div>
              <a href="https://github.com/Kabilesh-Raj-T/EVCS" target="_blank" rel="noreferrer" className="project-link">
                View Repository ↗
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Skills Section - Circular Scrollytelling Carousel */}
      <div className="skills-scroll-container" ref={addToRefs}>
        <div className="skills-sticky-wrapper">
          <div className="skills-stack-layout">
            <div className="skills-intro-sticky">
              <div className="section-label no-border">
                02 / Technical Skills
              </div>
            </div>
            
            <div className="skills-card-deck">
              <div className="skills-card card-1" style={{ "--card-index": 0 }}>
                <div className="card-header">
                  <span className="card-num">01.</span>
                  <h3>Languages</h3>
                </div>
                <div className="skills-chips">
                  <span>Python</span>
                  <span>C++</span>
                  <span>JavaScript</span>
                  <span>Verilog</span>
                </div>
              </div>
              
              <div className="skills-card card-2" style={{ "--card-index": 1 }}>
                <div className="card-header">
                  <span className="card-num">02.</span>
                  <h3>Frameworks</h3>
                </div>
                <div className="skills-chips">
                  <span>Flask</span>
                  <span>React</span>
                  <span>Pandas</span>
                  <span>NumPy</span>
                  <span>Scikit-Learn</span>
                  <span>GeoPandas</span>
                </div>
              </div>
              
              <div className="skills-card card-3" style={{ "--card-index": 2 }}>
                <div className="card-header">
                  <span className="card-num">03.</span>
                  <h3>Tools & Platforms</h3>
                </div>
                <div className="skills-chips">
                  <span>MySQL</span>
                  <span>Docker</span>
                  <span>Azure Cloud</span>
                  <span>Git</span>
                  <span>GitHub Actions</span>
                  <span>Vivado / Vivado HLS</span>
                  <span>MATLAB</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Accomplishments Section */}
      <section className="portfolio-section" ref={addToRefs}>
        <div className="section-label">03 / Key Milestones</div>
        
        <div className="timeline-layout">
          <div className="timeline-intro">
            <h2 className="timeline-title">
              {splitWords("Accomplishments")}
            </h2>
            <p className="timeline-desc">
              Academic recognition, developer milestones, and community leadership.
            </p>
          </div>
          
          <div className="timeline-list">
            <div className="timeline-progress-line"></div>
            <div className="timeline-item" ref={addToRefs}>
              <div className="timeline-header-row">
                <span className="timeline-index">01</span>
                <span className="timeline-marker"></span>
                <span className="timeline-heading">LeetCode Algorithm Milestones</span>
              </div>
              <p className="timeline-body-text">
                Solved 200+ selected problems focused on advanced data structures, graph theory, search algorithms, and computational efficiency.
              </p>
            </div>

            <div className="timeline-item" ref={addToRefs}>
              <div className="timeline-header-row">
                <span className="timeline-index">02</span>
                <span className="timeline-marker"></span>
                <span className="timeline-heading">Runner-Up at Futurize Fiesta</span>
              </div>
              <p className="timeline-body-text">
                Secured Runner-Up in "Futurize Fiesta," an inter-college technical competition.
              </p>
            </div>

            <div className="timeline-item" ref={addToRefs}>
              <div className="timeline-header-row">
                <span className="timeline-index">03</span>
                <span className="timeline-marker"></span>
                <span className="timeline-heading">Professional Accreditations</span>
              </div>
              <p className="timeline-body-text">
                Earned the HackerRank MySQL Intermediate designation and completed the Meta Front-End Developer specialization (Coursera) covering advanced React architecture.
              </p>
            </div>

            <div className="timeline-item" ref={addToRefs}>
              <div className="timeline-header-row">
                <span className="timeline-index">04</span>
                <span className="timeline-marker"></span>
                <span className="timeline-heading">Symposium Organizer — ElectroFocus'25</span>
              </div>
              <p className="timeline-body-text">
                Organized a university tech symposium event for 100+ attendees (ElectroFocus'25)
              </p>
            </div>

            <div className="timeline-item" ref={addToRefs}>
              <div className="timeline-header-row">
                <span className="timeline-index">05</span>
                <span className="timeline-marker"></span>
                <span className="timeline-heading">Social Service Mentorship</span>
              </div>
              <p className="timeline-body-text">
                Dedicated time through National Service Scheme (NSS) to coordinate local community educational programs and mentor young students.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer spacer */}
      <footer className="portfolio-footer">
        <span className="footer-credits">T Kabilesh Raj © 2026.</span>
      </footer>
    </div>
  );
};

export default Portfolio;
