// utils/motion.js
// Central re-export for anime.js v4 — import from here throughout the app

export {
  animate,
  createTimeline,
  stagger,
  onScroll,
  utils,
  svg,
  spring,
  createSpring,
  createMotionPath,
  createDrawable,
  morphTo,
  createScope,
  createAnimatable,
  createDraggable
} from 'animejs';

/**
 * Returns true if the OS/browser has prefers-reduced-motion set.
 */
export const prefersReducedMotion = () =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;
