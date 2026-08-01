import React from 'react';

const EnduranceGraphic = () => {
  return (
    <div className="endurance-photo-container">
      <img
        src={`${process.env.PUBLIC_URL}/assets/endurance_spaceship.png`}
        alt="Interstellar Endurance Spaceship Ring"
        className="endurance-photo-img"
      />
    </div>
  );
};

export default EnduranceGraphic;
