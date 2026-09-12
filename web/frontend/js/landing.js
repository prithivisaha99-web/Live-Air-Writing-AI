/**
 * Futuristic 3D Landing Page Controller - Live Air Writing AI
 * Author: Prithibi Saha
 */

(function () {
  'use strict';

  let animationFrameId = null;
  let isLandingActive = true;

  // DOM Elements
  const landingOverlay = document.getElementById('landing-overlay');
  const btnStartApp = document.getElementById('btn-start-app');
  const canvasContainer = document.getElementById('canvas-3d-landing');

  if (!landingOverlay || !btnStartApp) {
    console.warn('[Landing] Landing overlay or START button not found in DOM.');
    return;
  }

  // Mouse Parallax Coordinates
  let mouseX = 0;
  let mouseY = 0;
  let targetX = 0;
  let targetY = 0;

  window.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX - window.innerWidth / 2) * 0.0005;
    mouseY = (e.clientY - window.innerHeight / 2) * 0.0005;
  }, { passive: true });

  // ----------------------------------------------------
  // 1. Try Initializing Three.js 3D Particle Visual
  // ----------------------------------------------------
  let isThreeInitialized = false;

  function initThreeJsVisual() {
    if (typeof THREE === 'undefined') return false;

    try {
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
      camera.position.z = 18;

      const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

      // Append canvas element
      renderer.domElement.id = 'three-canvas-landing';
      renderer.domElement.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;';
      canvasContainer.appendChild(renderer.domElement);

      // Create Particle Swarm Sphere
      const particleCount = 1200;
      const geometry = new THREE.BufferGeometry();
      const positions = new Float32Array(particleCount * 3);
      const colors = new Float32Array(particleCount * 3);

      const colorCyan = new THREE.Color(0x00F0FF);
      const colorPurple = new THREE.Color(0xA855F7);

      for (let i = 0; i < particleCount; i++) {
        const u = Math.random();
        const v = Math.random();
        const theta = u * 2.0 * Math.PI;
        const phi = Math.acos(2.0 * v - 1.0);
        const r = 8 + Math.random() * 6;

        positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i * 3 + 2] = r * Math.cos(phi);

        const mixedColor = colorCyan.clone().lerp(colorPurple, Math.random());
        colors[i * 3] = mixedColor.r;
        colors[i * 3 + 1] = mixedColor.g;
        colors[i * 3 + 2] = mixedColor.b;
      }

      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

      // Glowing Particle Material
      const material = new THREE.PointsMaterial({
        size: 0.22,
        vertexColors: true,
        transparent: true,
        opacity: 0.85,
        blending: THREE.AdditiveBlending
      });

      const particleSystem = new THREE.Points(geometry, material);
      scene.add(particleSystem);

      // Add Inner Torus Knot Geometry Mesh Wireframe
      const torusGeometry = new THREE.TorusKnotGeometry(3.5, 0.8, 100, 16);
      const torusMaterial = new THREE.MeshBasicMaterial({
        color: 0x00F0FF,
        wireframe: true,
        transparent: true,
        opacity: 0.18
      });
      const torusKnot = new THREE.Mesh(torusGeometry, torusMaterial);
      scene.add(torusKnot);

      // Window Resize Handler
      function onWindowResize() {
        if (!isLandingActive) return;
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
      }
      window.addEventListener('resize', onWindowResize);

      // Render Loop
      function animate() {
        if (!isLandingActive) return;

        targetX += (mouseX - targetX) * 0.05;
        targetY += (mouseY - targetY) * 0.05;

        particleSystem.rotation.y += 0.002;
        particleSystem.rotation.x += 0.001;

        torusKnot.rotation.y -= 0.005;
        torusKnot.rotation.z += 0.003;

        camera.position.x += (targetX * 20 - camera.position.x) * 0.05;
        camera.position.y += (-targetY * 20 - camera.position.y) * 0.05;
        camera.lookAt(scene.position);

        renderer.render(scene, camera);
        animationFrameId = requestAnimationFrame(animate);
      }

      animate();
      return true;
    } catch (err) {
      console.warn('[Landing] Three.js WebGL initialization failed, falling back to 2D Canvas:', err);
      return false;
    }
  }

  // ----------------------------------------------------
  // 2. Fallback 2D Canvas Particle Constellation
  // ----------------------------------------------------
  function init2DCanvasFallback() {
    const canvas = document.createElement('canvas');
    canvas.id = 'canvas-2d-fallback';
    canvas.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;';
    canvasContainer.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    window.addEventListener('resize', () => {
      if (!isLandingActive) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });

    const particles = [];
    const count = 70;

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.8,
        vy: (Math.random() - 0.5) * 0.8,
        radius: Math.random() * 2 + 1,
        color: Math.random() > 0.5 ? '#00F0FF' : '#A855F7'
      });
    }

    function animate2D() {
      if (!isLandingActive) return;

      ctx.clearRect(0, 0, width, height);

      // Connect close particles with lines
      for (let i = 0; i < count; i++) {
        const p1 = particles[i];
        p1.x += p1.vx;
        p1.y += p1.vy;

        if (p1.x < 0 || p1.x > width) p1.vx *= -1;
        if (p1.y < 0 || p1.y > height) p1.vy *= -1;

        ctx.beginPath();
        ctx.arc(p1.x, p1.y, p1.radius, 0, Math.PI * 2);
        ctx.fillStyle = p1.color;
        ctx.shadowBlur = 10;
        ctx.shadowColor = p1.color;
        ctx.fill();

        for (let j = i + 1; j < count; j++) {
          const p2 = particles[j];
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(0, 240, 255, ${0.25 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }

      animationFrameId = requestAnimationFrame(animate2D);
    }

    animate2D();
  }

  // Initialize Visual
  isThreeInitialized = initThreeJsVisual();
  if (!isThreeInitialized) {
    init2DCanvasFallback();
  }

  // ----------------------------------------------------
  // 3. START Button Transition Action
  // ----------------------------------------------------
  btnStartApp.addEventListener('click', () => {
    if (!isLandingActive) return;

    // Play click animation feedback
    btnStartApp.style.transform = 'scale(0.95)';
    btnStartApp.style.opacity = '0.8';

    // Stop 3D/2D animation loop to conserve resources for webcam/MediaPipe
    isLandingActive = false;
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
    }

    // Trigger smooth fade-out transition
    landingOverlay.classList.add('fade-out');

    // Remove landing overlay from display after transition finishes
    setTimeout(() => {
      landingOverlay.style.display = 'none';
      console.log('[Landing] Transition complete. Air Writing Web App is active.');
    }, 800);
  });

})();
