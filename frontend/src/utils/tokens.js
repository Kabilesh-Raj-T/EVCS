import { spring } from './motion';

export const SPACE_COLORS = {
  nebulaViolet: '#A78BFA',
  nebulaCyan: '#7DD3FC',
  starWhite: '#F5F3FF',
  deepSpace: '#0D0D0D',
  accentGlow: 'rgba(167, 139, 250, 0.4)',
  surfaceDark: '#171717',
  borderSubtle: 'rgba(255, 255, 255, 0.08)'
};

export const EASE = {
  launch: 'outExpo',
  settle: spring({ mass: 1, stiffness: 90, damping: 14 }),
  snap: spring({ bounce: 0.5 }),
  drift: 'inOutSine'
};
