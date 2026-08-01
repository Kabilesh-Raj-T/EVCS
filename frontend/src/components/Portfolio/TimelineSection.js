import './TimelineSection.css';
import React from 'react';
import { splitWords } from './utils';

const TimelineSection = () => {
  return (
    <section className="portfolio-section revealed">
      <div className="timeline-layout">
        <div className="timeline-intro">
          <div className="section-label">03 / Key Milestones</div>
          <h2 className="timeline-title">{splitWords("Accomplishments")}</h2>
          <p className="timeline-desc">
            Academic recognition, developer milestones, and community leadership.
          </p>
        </div>
        <div className="timeline-list">
          <div className="timeline-progress-line"></div>

          <div className="timeline-item revealed">
            <div className="timeline-header-row">
              <span className="timeline-index">01</span>
              <span className="timeline-marker"></span>
              <span className="timeline-heading">LeetCode Algorithm Milestones</span>
            </div>
            <p className="timeline-body-text">
              Solved 200+ selected problems focused on advanced data structures, graph theory, search algorithms, and computational efficiency.
            </p>
          </div>

          <div className="timeline-item revealed">
            <div className="timeline-header-row">
              <span className="timeline-index">02</span>
              <span className="timeline-marker"></span>
              <span className="timeline-heading">Runner-Up at Futurize Fiesta</span>
            </div>
            <p className="timeline-body-text">
              Secured Runner-Up in "Futurize Fiesta," an inter-college technical competition.
            </p>
          </div>

          <div className="timeline-item revealed">
            <div className="timeline-header-row">
              <span className="timeline-index">03</span>
              <span className="timeline-marker"></span>
              <span className="timeline-heading">Professional Accreditations</span>
            </div>
            <p className="timeline-body-text">
              Earned the HackerRank MySQL Intermediate designation and completed the Meta Front-End Developer specialization (Coursera) covering advanced React architecture.
            </p>
          </div>

          <div className="timeline-item revealed">
            <div className="timeline-header-row">
              <span className="timeline-index">04</span>
              <span className="timeline-marker"></span>
              <span className="timeline-heading">Symposium Organizer — ElectroFocus'25</span>
            </div>
            <p className="timeline-body-text">
              Organized a university tech symposium event for 100+ attendees (ElectroFocus'25)
            </p>
          </div>

          <div className="timeline-item revealed">
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
  );
};

export default TimelineSection;
