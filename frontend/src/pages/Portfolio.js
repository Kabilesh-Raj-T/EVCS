import React, { useEffect } from 'react';
import './Portfolio.css';
import { animate, createTimeline, stagger } from '../utils/motion';
import Starfield from '../components/motion/Starfield';
import HeroSection from '../components/Portfolio/HeroSection';
import ProjectsSection from '../components/Portfolio/ProjectsSection';
import SkillsSection from '../components/Portfolio/SkillsSection';
import TimelineSection from '../components/Portfolio/TimelineSection';
import Footer from '../components/Portfolio/Footer';

const Portfolio = ({ isTransitioning, isBackendReady, onToggleApp }) => {

  useEffect(() => {
    // -------------------------------------------------------------
    // 1. INTERSTELLAR CINEMATIC HERO TEXT TIMELINE (Anime.js v4)
    // -------------------------------------------------------------
    const startHeroTimeline = () => {
      const chars = document.querySelectorAll('.hero-name .reveal-char');
      const words = document.querySelectorAll('.hero-description .reveal-word');
      const role = document.querySelector('.hero-role');
      const scrollIndicator = document.querySelector('.hero-scroll-indicator');

      const heroTl = createTimeline({ defaults: { ease: 'outExpo' } });

      // Step 1: Hero Name Hologram / Spatial Coalesce Reveal
      if (chars.length) {
        heroTl.add(chars, {
          opacity: [0, 1],
          translateZ: ['-180px', '0px'],
          rotateY: ['-45deg', '0deg'],
          scale: [0.65, 1],
          filter: ['blur(14px) brightness(2.8)', 'blur(0px) brightness(1)'],
          delay: stagger(30),
          duration: 950,
          ease: 'outExpo'
        });
      }

      // Step 2: Role Badge Cosmic Expansion Settle
      if (role) {
        heroTl.add(role, {
          opacity: [0, 1],
          translateY: ['24px', '0px'],
          scale: [0.85, 1],
          filter: ['blur(8px) brightness(2)', 'blur(0px) brightness(1)'],
          duration: 750,
          ease: 'outExpo'
        }, '-=500');
      }

      // Step 3: Bio Description Spatial Depth Word Stagger
      if (words.length) {
        heroTl.add(words, {
          opacity: [0, 1],
          rotateX: ['40deg', '0deg'],
          translateY: ['25px', '0px'],
          filter: ['blur(10px) brightness(1.8)', 'blur(0px) brightness(1)'],
          delay: stagger(20),
          duration: 700,
          ease: 'outExpo'
        }, '-=450');
      }

      if (scrollIndicator) {
        animate(scrollIndicator, {
          translateY: ['0px', '8px', '0px'],
          duration: 1400,
          loop: true,
          ease: 'inOutSine',
        });
      }
    };

    const timerId = setTimeout(startHeroTimeline, 60);

    // -------------------------------------------------------------
    // 2. INTERSTELLAR SCROLL REVEALS
    // -------------------------------------------------------------
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
          }
        });
      },
      { threshold: 0.05, rootMargin: '0px 0px -30px 0px' }
    );

    document.querySelectorAll('.project-card-slide, .timeline-item, .portfolio-section, .timeline-layout').forEach((el) => {
      revealObserver.observe(el);
    });

    let ticking = false;
    const domCache = {};
    const getEl = (sel) => domCache[sel] || (domCache[sel] = document.querySelector(sel));
    
    const getScrollRoot = () => getEl('.portfolio-wrapper');

    // Three snap points: card 1 at progress=0, card 2 at 0.5, card 3 at 1.0
    const SNAP_POINTS = [0, 0.5, 1.0];
    const SNAP_RADIUS = 0.12;

    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const scrollRoot = getScrollRoot();
          if (!scrollRoot) {
            ticking = false;
            return;
          }

          // -------------------------------------------------------------
          // HORIZONTAL SCROLL TRACK — MAGNETIC SNAP (projects section)
          // -------------------------------------------------------------
          const projectsWrapper = getEl('.projects-scroll-wrapper');
          const projectsTrack   = getEl('.projects-track');
          if (projectsWrapper && projectsTrack) {
            const wrapperRect  = projectsWrapper.getBoundingClientRect();
            const scrollRootTop = scrollRoot.getBoundingClientRect().top;
            const relTop       = wrapperRect.top - scrollRootTop;
            const scrollRange  = projectsWrapper.offsetHeight - scrollRoot.clientHeight;
            let progress = 0;
            if (scrollRange > 0) {
              progress = Math.min(Math.max(-relTop / scrollRange, 0), 1);
            }

            // Find nearest snap point
            let nearestIdx = 0;
            let minDist    = Infinity;
            SNAP_POINTS.forEach((sp, i) => {
              const d = Math.abs(progress - sp);
              if (d < minDist) { minDist = d; nearestIdx = i; }
            });

            // Magnetic pull: outside SNAP_RADIUS = pure linear
            //                inside SNAP_RADIUS  = cubic gravity well toward snap
            let displayProgress = progress;
            if (minDist < SNAP_RADIUS) {
              const t    = minDist / SNAP_RADIUS;         // 1 at edge → 0 at snap
              const pull = 1 - Math.pow(t, 2.5);         // accelerates hard near snap
              displayProgress = progress + (SNAP_POINTS[nearestIdx] - progress) * pull;
            }



            const translateX = -displayProgress * 66.666;
            projectsTrack.style.transform = `translate3d(${translateX.toFixed(4)}%, 0, 0)`;

            // -------------------------------------------------------------
            // TARS ROBOT PROGRESS BAR WALK SIMULATION
            // -------------------------------------------------------------
            const tarsContainer = getEl('.tars-container');
            const tarsLimb1 = getEl('.tars-limb.limb-1');
            const tarsLimb2 = getEl('.tars-limb.limb-2');
            const tarsLimb3 = getEl('.tars-limb.limb-3');
            const tarsLimb4 = getEl('.tars-limb.limb-4');
            const tarsShadow = getEl('.tars-shadow');
            const tarsProgressFill = getEl('.tars-progress-fill');

            if (tarsContainer && tarsLimb1 && tarsLimb2 && tarsLimb3 && tarsLimb4) {
              const containerWidth = tarsContainer.parentElement ? tarsContainer.parentElement.clientWidth : 180;
              const robotWidth = window.innerWidth <= 900 ? 33 : 43;
              const maxTravel = containerWidth - robotWidth;
              const currentX = progress * maxTravel;

              // 14 walk cycles across the section scroll progress
              const walkingAngle = Math.sin(progress * Math.PI * 14) * 22;
              const bobY = Math.abs(Math.sin(progress * Math.PI * 14)) * 3.5;

              tarsContainer.style.transform = `translate3d(${currentX.toFixed(2)}px, ${bobY.toFixed(2)}px, 0)`;

              tarsLimb1.style.transform = `rotate(${walkingAngle.toFixed(2)}deg)`;
              tarsLimb4.style.transform = `rotate(${walkingAngle.toFixed(2)}deg)`;
              tarsLimb2.style.transform = `rotate(${-walkingAngle.toFixed(2)}deg)`;
              tarsLimb3.style.transform = `rotate(${-walkingAngle.toFixed(2)}deg)`;

              if (tarsProgressFill) {
                tarsProgressFill.style.width = `${(progress * 100).toFixed(2)}%`;
              }

              if (tarsShadow) {
                const shadowScaleX = 1 + Math.abs(walkingAngle) * 0.012;
                const shadowOpacity = 0.8 - (bobY * 0.05);
                tarsShadow.style.transform = `scaleX(${shadowScaleX.toFixed(2)})`;
                tarsShadow.style.opacity = shadowOpacity.toFixed(2);
              }
            }
          }

          // -------------------------------------------------------------
          // 3D ZOOMING TRANSPARENT CARDS (TECHNICAL SKILLS)
          // -------------------------------------------------------------
          const skillsContainer = getEl('.skills-scroll-container');
          const ringGraphic = getEl('.skills-ring-graphic');

          if (skillsContainer) {
            const containerRect = skillsContainer.getBoundingClientRect();
            const scrollRootTop = scrollRoot.getBoundingClientRect().top;
            const relTop = containerRect.top - scrollRootTop;
            const scrollRange = skillsContainer.offsetHeight - scrollRoot.clientHeight;
            
            let p = 0;
            if (scrollRange > 0) {
              p = Math.min(Math.max(-relTop / scrollRange, 0), 1);
            }


            // Magnetic snap points for the 3 focal cards
            const SKILLS_SNAP_POINTS = [0.18, 0.50, 0.82];
            const SKILLS_SNAP_RADIUS = 0.12;

            // Find nearest snap point
            let nearestIdx = 0;
            let minDist = Infinity;
            SKILLS_SNAP_POINTS.forEach((sp, i) => {
              const d = Math.abs(p - sp);
              if (d < minDist) {
                minDist = d;
                nearestIdx = i;
              }
            });

            // Magnetic gravity well pull (cubic easing)
            let displayP = p;
            if (minDist < SKILLS_SNAP_RADIUS) {
              const t = minDist / SKILLS_SNAP_RADIUS;
              const pull = 1 - Math.pow(t, 2.5);
              displayP = p + (SKILLS_SNAP_POINTS[nearestIdx] - p) * pull;
            }

            // Spaceship rotation alone remains perfectly linear with scroll
            const wheelRotation = -p * 100;
            if (ringGraphic) {
              ringGraphic.style.transform = `rotate(${wheelRotation.toFixed(2)}deg)`;
            }

            // Calculate relative offset to spaceship center dynamically
            const cardsWrapper = getEl('.skills-cards-wrapper');
            let targetX = 0;
            let targetY = 0;
            if (ringGraphic && cardsWrapper) {
              const ringRect = ringGraphic.getBoundingClientRect();
              const cardsRect = cardsWrapper.getBoundingClientRect();
              targetX = (ringRect.left + ringRect.width / 2) - (cardsRect.left + cardsRect.width / 2);
              targetY = (ringRect.top + ringRect.height / 2) - (cardsRect.top + cardsRect.height / 2);
            }

            // Set up zoom parameters for each card (center points in scroll progress)
            const zoomCards = document.querySelectorAll('.skills-zoom-card');
            const centers = [0.18, 0.50, 0.82];

            zoomCards.forEach((card, i) => {
              const center = centers[i];
              const offset = displayP - center;

              let scale = 0.15;
              let opacity = 0;
              let translateZ = -350; // start deep in background behind spaceship
              let currentX = 0;
              let currentY = 0;

              if (offset < -0.25) {
                // Far in background (locked behind the spaceship)
                scale = 0.15;
                opacity = 0;
                translateZ = -350;
                const scaleOffset = (1200 - translateZ) / 1200;
                currentX = targetX * scaleOffset;
                currentY = targetY * scaleOffset;
              } else if (offset >= -0.25 && offset < 0) {
                // Zooming in from spaceship background to center focal point
                const t = (offset + 0.25) / 0.25; // 0 to 1
                scale = 0.15 + t * 0.85;          // 0.15 -> 1.0
                opacity = t;                      // 0 -> 1
                translateZ = -350 + t * 350;      // -350px -> 0px
                const scaleOffset = (1200 - translateZ) / 1200;
                currentX = targetX * scaleOffset * (1 - t);
                currentY = targetY * scaleOffset * (1 - t);
              } else if (offset >= 0 && offset < 0.25) {
                // Dissolves in place at the focal point
                const t = offset / 0.25;          // 0 to 1
                scale = 1.0;                      // keep at snap size
                opacity = 1 - t;                  // gradually make it transparent
                translateZ = 0;                   // keep at snap depth
                currentX = 0;
                currentY = 0;
              } else {
                // Completely vanished
                scale = 1.0;
                opacity = 0;
                translateZ = 0;
                currentX = 0;
                currentY = 0;
              }

              // Apply 3D matrix transform with translation from spaceship position
              card.style.transform = `translate3d(${currentX.toFixed(2)}px, ${currentY.toFixed(2)}px, ${translateZ.toFixed(2)}px) scale(${scale.toFixed(4)})`;
              card.style.opacity = opacity.toFixed(4);
              card.style.filter = 'none';
              
              // Enable pointer events only when active/visible to allow chip hover interaction
              if (opacity > 0.4) {
                card.style.pointerEvents = 'auto';
                card.style.zIndex = 10;
              } else {
                card.style.pointerEvents = 'none';
                card.style.zIndex = 1;
              }
            });
          }

          // -------------------------------------------------------------
          // TIMELINE PROGRESS LINE DRAW (MORSE CODE STAY TRACK)
          // -------------------------------------------------------------
          const timelineList = getEl('.timeline-list');
          const progressLine = getEl('.timeline-progress-line');
          if (timelineList && progressLine) {
            const rect = timelineList.getBoundingClientRect();
            const viewHeight = window.innerHeight;
            const lineProgress = Math.min(Math.max((viewHeight - rect.top) / (rect.height + viewHeight * 0.3), 0), 1);
            const clipPercent = ((1 - lineProgress) * 100).toFixed(2);
            progressLine.style.clipPath = `inset(0 0 ${clipPercent}% 0)`;
          }

          ticking = false;
        });
        ticking = true;
      }
    };

    // -------------------------------------------------------------
    // HAMILTON WATCH MORSE CODE TICK TIMELINE LOOP ("STAY")
    // -------------------------------------------------------------
    const steps = [
      // S: . . .
      { angle: 6, delay: 180 }, { angle: 12, delay: 180 }, { angle: 18, delay: 500 },
      // T: -
      { angle: 36, delay: 700 },
      // A: . -
      { angle: 42, delay: 180 }, { angle: 60, delay: 700 },
      // Y: - . - -
      { angle: 78, delay: 500 }, { angle: 84, delay: 180 }, { angle: 102, delay: 500 }, { angle: 120, delay: 1000 }
    ];

    let stepIndex = 0;
    let currentAngle = 0;
    let watchTimeoutId;

    const runWatchTick = () => {
      const hand = document.querySelector('.watch-second-hand');
      if (hand) {
        const step = steps[stepIndex];
        currentAngle = Math.floor(currentAngle / 360) * 360 + step.angle;
        hand.style.transform = `rotate(${currentAngle}deg)`;

        const led = document.querySelector('.watch-led');
        if (led) {
          led.style.opacity = '1';
          setTimeout(() => { led.style.opacity = '0.15'; }, 100);
        }

        stepIndex = (stepIndex + 1) % steps.length;
        watchTimeoutId = setTimeout(runWatchTick, step.delay);
      } else {
        watchTimeoutId = setTimeout(runWatchTick, 300);
      }
    };

    runWatchTick();

    const scrollRoot = getScrollRoot();
    if (scrollRoot) {
      scrollRoot.addEventListener('scroll', handleScroll, { passive: true });
    }
    // Fallback capturing listener on window to handle nested scrolling environments robustly
    window.addEventListener('scroll', handleScroll, { capture: true, passive: true });
    window.addEventListener('resize', handleScroll, { passive: true });

    handleScroll();
    requestAnimationFrame(handleScroll);

    return () => {
      clearTimeout(timerId);
      clearTimeout(watchTimeoutId);
      revealObserver.disconnect();
      if (scrollRoot) {
        scrollRoot.removeEventListener('scroll', handleScroll);
      }
      window.removeEventListener('scroll', handleScroll, { capture: true });
      window.removeEventListener('resize', handleScroll);
    };
  }, []);

  return (
    <div className={`portfolio-container ${isTransitioning ? 'transitioning' : ''}`}>
      <Starfield />
      <HeroSection isBackendReady={isBackendReady} />
      <ProjectsSection onToggleApp={onToggleApp} />
      <SkillsSection />
      <TimelineSection />
      <Footer />
    </div>
  );
};

export default Portfolio;
