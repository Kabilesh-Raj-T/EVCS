import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import plutoTextureImg from '../../assets/pluto_texture.jpg';

const Moon3D = () => {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Get parent dimensions
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Scene Setup
    const scene = new THREE.Scene();

    // Camera Setup (orthographic camera keeps it looking flat but spherically mapped)
    const aspect = width / height;
    const d = 2;
    const camera = new THREE.OrthographicCamera(
      -d * aspect,
      d * aspect,
      d,
      -d,
      1,
      1000
    );
    camera.position.set(0, 0, 5);

    // Renderer Setup (with transparent background)
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    renderer.shadowMap.enabled = false;
    container.appendChild(renderer.domElement);

    // Geometry & Texture loading (radius 2.0 fills the 2.0 bounds completely)
    const geometry = new THREE.SphereGeometry(2.0, 64, 64);
    
    const textureLoader = new THREE.TextureLoader();
    const texture = textureLoader.load(plutoTextureImg);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.wrapS = THREE.RepeatWrapping;

    // Material with low specular reflections for a dusty surface
    const material = new THREE.MeshStandardMaterial({
      map: texture,
      roughness: 0.95,
      metalness: 0.05,
    });

    const moon = new THREE.Mesh(geometry, material);
    // Slight tilt of the moon axis (lunar obliquity ~1.5 degrees, tilted slightly for aesthetics)
    moon.rotation.x = 0.15;
    scene.add(moon);

    // Lighting (shines from top-left, matching the previous radial shading angle)
    const dirLight = new THREE.DirectionalLight(0xffffff, 3.8);
    dirLight.position.set(-3.5, 3.5, 4);
    scene.add(dirLight);

    // Subtle dark ambient space light
    const ambientLight = new THREE.AmbientLight(0x050505);
    scene.add(ambientLight);

    // Render loop
    let animationFrameId;
    const animateLoop = () => {
      // Slow rotation along the Y-axis
      moon.rotation.y += 0.0022;
      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animateLoop);
    };
    animateLoop();

    // Handle Resize
    const handleResize = () => {
      if (!container || !renderer) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      
      const newAspect = w / h;
      camera.left = -d * newAspect;
      camera.right = d * newAspect;
      camera.top = d;
      camera.bottom = -d;
      camera.updateProjectionMatrix();

      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
      if (renderer) {
        renderer.dispose();
        if (container.contains(renderer.domElement)) {
          container.removeChild(renderer.domElement);
        }
      }
      geometry.dispose();
      material.dispose();
      texture.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: '50%',
        overflow: 'hidden'
      }}
    />
  );
};

export default Moon3D;
