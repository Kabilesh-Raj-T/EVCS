import React, { useEffect, useRef } from 'react';
import { SPACE_COLORS } from '../../utils/tokens';

const Starfield = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    const starCount = Math.min(Math.floor(width * 0.06), 80);
    const stars = Array.from({ length: starCount }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      xRel: (Math.random() - 0.5) * width,
      yRel: (Math.random() - 0.5) * height,
      z: Math.random(),
      size: Math.random() * 1.6 + 0.4,
      layer: Math.random() < 0.3 ? 1 : Math.random() < 0.7 ? 2 : 3,
      alpha: Math.random() * 0.7 + 0.3,
      twinkleSpeed: Math.random() * 0.02 + 0.005,
      twinkleDir: Math.random() < 0.5 ? 1 : -1
    }));

    let scrollY = 0;
    let lastScrollY = 0;
    let scrollSpeed = 0;
    let idleOffset = 0;
    const scrollContainer = document.querySelector('.portfolio-wrapper');

    const handleScroll = () => {
      const scrollRoot = document.querySelector('.portfolio-wrapper');
      if (scrollRoot) {
        scrollY = scrollRoot.scrollTop;
      } else {
        scrollY = window.scrollY || window.pageYOffset || document.documentElement.scrollTop;
      }
    };

    if (scrollContainer) {
      scrollContainer.addEventListener('scroll', handleScroll, { passive: true });
    }
    window.addEventListener('scroll', handleScroll, { capture: true, passive: true });

    const render = () => {
      // Sync canvas position with scroll to bypass transform containing-block bugs
      if (canvas) {
        canvas.style.transform = `translate3d(0, ${scrollY}px, 0)`;
      }

      ctx.clearRect(0, 0, width, height);

      // Dynamic slow background drift
      idleOffset += 0.08;

      // Track scroll velocity (speed of viewport movement)
      const deltaY = Math.abs(scrollY - lastScrollY);
      lastScrollY = scrollY;
      
      // Target speed capped at 40px/frame, smoothed using linear interpolation (lerp)
      const targetSpeed = Math.min(deltaY * 0.45, 40);
      scrollSpeed += (targetSpeed - scrollSpeed) * 0.12;

      // 1. Projects Section Horizontal Progress (using bounding client rects)
      let horizontalProgress = 0;
      let projectsScrollRange = 0;
      const projectsWrapper = document.querySelector('.projects-scroll-wrapper');
      if (projectsWrapper && scrollContainer) {
        const wrapperRect = projectsWrapper.getBoundingClientRect();
        const scrollRootTop = scrollContainer.getBoundingClientRect().top;
        const relTop = wrapperRect.top - scrollRootTop;
        projectsScrollRange = projectsWrapper.offsetHeight - scrollContainer.clientHeight;
        if (projectsScrollRange > 0) {
          horizontalProgress = Math.min(Math.max(-relTop / projectsScrollRange, 0), 1);
        }
      }

      // Freeze vertical scroll parallax when viewport is sticky (scrolling horizontally)
      let parallaxScrollY = scrollY;
      if (horizontalProgress > 0 && horizontalProgress < 1) {
        parallaxScrollY = scrollY - (horizontalProgress * projectsScrollRange);
      } else if (horizontalProgress >= 1) {
        parallaxScrollY = scrollY - projectsScrollRange;
      }

      // 2. Skills Section Forward Zoom Progress (using bounding client rects)
      let rawProgress = 0;
      const skillsContainer = document.querySelector('.skills-scroll-container');
      if (skillsContainer && scrollContainer) {
        const containerRect = skillsContainer.getBoundingClientRect();
        const scrollRootTop = scrollContainer.getBoundingClientRect().top;
        const relTop = containerRect.top - scrollRootTop;
        const scrollRange = skillsContainer.offsetHeight - scrollContainer.clientHeight;
        if (scrollRange > 0) {
          rawProgress = -relTop / scrollRange;
        }
      }

      const skillsScrollProgress = Math.max(0, Math.min(rawProgress, 1));

      stars.forEach((star) => {
        star.alpha += star.twinkleSpeed * star.twinkleDir;
        if (star.alpha > 0.95 || star.alpha < 0.2) {
          star.twinkleDir *= -1;
        }

        // Base vertical scroll parallax + continuous idle drift (layered by depth)
        const parallaxOffsetY = (parallaxScrollY * 0.06 + idleOffset) * star.layer;
        
        // Accelerated vertical depth travel in Section 02 (Technical Skills)
        const skillsShiftY = skillsScrollProgress * (height * 0.5) * (star.layer * 0.8);
        
        let drawY = (star.y - parallaxOffsetY - skillsShiftY) % height;
        if (drawY < 0) drawY += height;

        // Horizontal star drift in Section 01 (Projects)
        const horizontalShiftX = horizontalProgress * (width * 0.4) * (star.layer * 0.6);
        let drawX = (star.x - horizontalShiftX) % width;
        if (drawX < 0) drawX += width;

        // Render star as a beautiful, realistic circular dot
        ctx.fillStyle = star.layer === 3 ? SPACE_COLORS.nebulaCyan : SPACE_COLORS.starWhite;
        ctx.globalAlpha = star.alpha;
        ctx.beginPath();
        ctx.arc(drawX, drawY, Math.max(0.4, star.size), 0, Math.PI * 2);
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      if (scrollContainer) {
        scrollContainer.removeEventListener('scroll', handleScroll);
      }
      window.removeEventListener('scroll', handleScroll, { capture: true });
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="starfield-canvas"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 2,
        opacity: 0.85
      }}
    />
  );
};

export default Starfield;
