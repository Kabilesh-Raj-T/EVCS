import React from 'react';
import { animate } from '../../utils/motion';

export const SKILLS_DATA = [
  { num: '01.', title: 'Languages', chips: ['Python', 'C++', 'JavaScript', 'Verilog'] },
  { num: '02.', title: 'Frameworks', chips: ['Flask', 'React', 'Pandas', 'NumPy', 'Scikit-Learn', 'GeoPandas'] },
  { num: '03.', title: 'Tools & Platforms', chips: ['MySQL', 'Docker', 'Azure Cloud', 'Git', 'GitHub Actions', 'Vivado / Vivado HLS', 'MATLAB'] },
];

export const splitText = (text) => {
  return text.split('').map((char, index) => {
    if (char === ' ') {
      return <span key={index} style={{ display: 'inline-block', width: '0.25em' }}>&nbsp;</span>;
    }
    return (
      <span key={index} className="reveal-char-wrapper">
        <span className="reveal-char">
          {char}
        </span>
      </span>
    );
  });
};

export const splitWords = (text) => {
  return text.split(' ').map((word, index) => {
    return (
      <span key={index} className="reveal-word-wrapper">
        <span className="reveal-word">
          {word}&nbsp;
        </span>
      </span>
    );
  });
};

export const handleChipHover = (e) => {
  animate(e.currentTarget, {
    scale: [1, 1.18, 1.05],
    rotate: ['0deg', '4deg', '0deg'],
    duration: 350,
    ease: 'outBack',
  });
};
