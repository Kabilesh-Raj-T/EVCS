import './SkillsSection.css';
import React from 'react';
import EnduranceGraphic from '../motion/EnduranceGraphic';
import { SKILLS_DATA, handleChipHover } from './utils';

const SkillsSection = () => {
  return (
    <div id="skills" className="skills-scroll-container revealed">
      <div className="skills-sticky-wrapper">
        <div className="skills-section-content">
          <div className="section-label">02 / Technical Skills</div>
          <div className="skills-zoom-stage">

            {/* Central stacked zoom cards container */}
            <div className="skills-cards-wrapper">
              {SKILLS_DATA.map((cat) => (
                <div key={cat.num} className="skills-zoom-card">
                  <div className="card-header">
                    <span className="card-num">{cat.num}</span>
                    <h3>{cat.title}</h3>
                  </div>
                  <div className="skills-chips">
                    {cat.chips.map((chip) => (
                      <span key={chip} onMouseEnter={handleChipHover}>{chip}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Right: Endurance Spaceship */}
            <div className="skills-ring-graphic">
              <EnduranceGraphic />
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};

export default SkillsSection;
