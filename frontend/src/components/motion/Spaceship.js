import React from 'react';
import { SPACE_COLORS } from '../../utils/tokens';

const Spaceship = ({ size = 28, className = '', style = {} }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`spaceship-svg ${className}`}
      style={{ display: 'inline-block', verticalAlign: 'middle', filter: `drop-shadow(0 0 8px ${SPACE_COLORS.nebulaViolet})`, ...style }}
    >
      {/* Thruster Flame Glow */}
      <path
        d="M24 44 C20 40 22 34 24 34 C26 34 28 40 24 44 Z"
        fill={SPACE_COLORS.nebulaCyan}
        opacity="0.85"
      />
      {/* Ship Fuselage Silhouette */}
      <path
        d="M24 4 L34 32 L24 28 L14 32 Z"
        fill={SPACE_COLORS.starWhite}
        stroke={SPACE_COLORS.nebulaViolet}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      {/* Wing Fins */}
      <path
        d="M14 26 L6 34 L14 32 Z"
        fill={SPACE_COLORS.nebulaViolet}
      />
      <path
        d="M34 26 L42 34 L34 32 Z"
        fill={SPACE_COLORS.nebulaViolet}
      />
      {/* Cockpit Core */}
      <circle cx="24" cy="18" r="2.5" fill={SPACE_COLORS.nebulaCyan} />
    </svg>
  );
};

export default Spaceship;
