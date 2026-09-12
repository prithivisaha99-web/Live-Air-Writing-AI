/**
 * Live Air Writing AI - Browser Air Canvas & Vector Stroke Engine (Phase 6)
 * Handles velocity-adaptive EMA smoothing, linear stroke interpolation, quadratic Bezier curve rendering,
 * vector stroke history for Undo/Redo, brush color/size selection, eraser, canvas modes, HD High-DPI scaling, and PNG export.
 */

export class VectorStroke {
  constructor(options = {}) {
    this.points = options.points || []; // Array of {x, y} normalized [0.0..1.0]
    this.color = options.color || '#00F0FF';
    this.width = options.width || 8;
    this.isEraser = options.isEraser || false;
  }

  addPoint(x, y) {
    this.points.push({
      x: Math.max(0.0, Math.min(1.0, x)),
      y: Math.max(0.0, Math.min(1.0, y))
    });
  }
}

export class BrowserAirCanvas {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) {
      throw new Error(`[AirCanvas] Canvas element with id '${canvasId}' not found.`);
    }
    this.ctx = this.canvas.getContext('2d');

    // Engine & Canvas Configuration
    this.mode = options.mode || 'camera'; // 'camera', 'dark', 'light'
    this.currentColor = options.color || '#00F0FF';
    this.brushWidth = options.width || 8;
    this.isEraserActive = false;
    this.eraserWidth = options.eraserWidth || 30;

    // Vector Stroke History
    this.history = []; // Array of committed VectorStroke
    this.redoStack = []; // Array of popped VectorStroke for Redo
    this.activeStroke = null; // Live stroke currently being drawn

    // Velocity-Adaptive EMA & Smoothing Parameters
    this.minAlpha = 0.20;
    this.maxAlpha = 0.80;
    this.minDistThreshold = 0.0008; // Suppress stationary jitter (~0.5px)
    this.interpStep = 0.004; // Linear interpolation step (~2.5px spacing)

    // State Tracking
    this.prevSmoothed = null; // {x, y}
    this.isWriting = false;
    this.currentStrokePoints = [];

    // Callbacks
    this.onHistoryChange = options.onHistoryChange || null;

    // Initialize Canvas Resolution & Event Listeners
    this.initCanvasResolution();
    this.setupPointerListeners();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  setupPointerListeners() {
    if (!this.canvas) return;

    let isPointerDown = false;

    const getNormalizedPos = (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const clientX = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
      const clientY = e.clientY || (e.touches && e.touches[0] ? e.touches[0].clientY : 0);
      const px = clientX - rect.left;
      const py = clientY - rect.top;
      return {
        x: Math.max(0.0, Math.min(1.0, px / rect.width)),
        y: Math.max(0.0, Math.min(1.0, py / rect.height))
      };
    };

    this.canvas.addEventListener('pointerdown', (e) => {
      isPointerDown = true;
      const normPt = getNormalizedPos(e);
      const gesture = this.isEraserActive ? 'ERASER' : 'DRAW';
      this.processPoint(normPt, true, gesture);
    });

    this.canvas.addEventListener('pointermove', (e) => {
      if (!isPointerDown) return;
      const normPt = getNormalizedPos(e);
      const gesture = this.isEraserActive ? 'ERASER' : 'DRAW';
      this.processPoint(normPt, true, gesture);
    });

    const endPointer = () => {
      if (isPointerDown) {
        isPointerDown = false;
        this.processPoint(null, false, 'NO HAND');
      }
    };

    this.canvas.addEventListener('pointerup', endPointer);
    this.canvas.addEventListener('pointercancel', endPointer);
    this.canvas.addEventListener('pointerleave', endPointer);
  }

  initCanvasResolution() {
    this.resizeCanvas();
  }

  resizeCanvas() {
    if (!this.canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    
    // Set display resolution accounting for High DPI screens
    const displayWidth = Math.round(rect.width * dpr);
    const displayHeight = Math.round(rect.height * dpr);

    if (this.canvas.width !== displayWidth || this.canvas.height !== displayHeight) {
      this.canvas.width = displayWidth > 0 ? displayWidth : 640;
      this.canvas.height = displayHeight > 0 ? displayHeight : 480;
      this.render();
    }
  }

  setCanvasMode(mode) {
    this.mode = mode;
    this.render();
  }

  setColor(colorHex) {
    this.currentColor = colorHex;
    this.isEraserActive = false;
  }

  setBrushWidth(width) {
    this.brushWidth = Math.max(1, Math.min(100, parseInt(width, 10)));
  }

  setEraser(active, width = 30) {
    this.isEraserActive = !!active;
    if (width) this.eraserWidth = Math.max(4, Math.min(100, parseInt(width, 10)));
  }

  toggleEraser() {
    this.isEraserActive = !this.isEraserActive;
    return this.isEraserActive;
  }

  // ----------------------------------------------------
  // Velocity-Adaptive Exponential Moving Average (EMA)
  // ----------------------------------------------------
  applyEMA(rawX, rawY) {
    if (!this.prevSmoothed) {
      this.prevSmoothed = { x: rawX, y: rawY };
      return { x: rawX, y: rawY };
    }

    const dist = Math.hypot(rawX - this.prevSmoothed.x, rawY - this.prevSmoothed.y);

    const lowDist = 0.0015;
    const highDist = 0.020;
    let alpha;
    if (dist <= lowDist) {
      alpha = this.minAlpha;
    } else if (dist >= highDist) {
      alpha = this.maxAlpha;
    } else {
      const t = (dist - lowDist) / (highDist - lowDist);
      alpha = this.minAlpha + t * (this.maxAlpha - this.minAlpha);
    }

    const smoothedX = alpha * rawX + (1.0 - alpha) * this.prevSmoothed.x;
    const smoothedY = alpha * rawY + (1.0 - alpha) * this.prevSmoothed.y;

    this.prevSmoothed = { x: smoothedX, y: smoothedY };
    return { x: smoothedX, y: smoothedY };
  }

  // ----------------------------------------------------
  // Core Point Processing & Air Writing State Machine
  // ----------------------------------------------------
  processPoint(rawPt, isDrawingGesture, gestureName) {
    const isEraserGesture = (gestureName === 'ERASER') || this.isEraserActive;

    // Case 1: No point / Hand tracking lost -> End current stroke
    if (!rawPt || typeof rawPt.x !== 'number' || typeof rawPt.y !== 'number') {
      this.commitActiveStroke();
      this.prevSmoothed = null;
      return { isWriting: false, strokePointsCount: 0 };
    }

    const normX = Math.max(0.0, Math.min(1.0, rawPt.x));
    const normY = Math.max(0.0, Math.min(1.0, rawPt.y));

    // Always update smoothed position when hand is visible
    const smoothed = this.applyEMA(normX, normY);

    // Case 2: Gesture is NOT drawing or eraser -> End active stroke
    if (!isDrawingGesture && gestureName !== 'ERASER') {
      this.commitActiveStroke();
      return { isWriting: false, strokePointsCount: 0 };
    }

    const strokeColor = isEraserGesture ? 'rgba(0,0,0,0)' : this.currentColor;
    const strokeWidth = isEraserGesture ? this.eraserWidth : this.brushWidth;

    // Case 3: Start new stroke if writing was not active
    if (!this.isWriting || !this.activeStroke) {
      this.isWriting = true;
      this.activeStroke = new VectorStroke({
        points: [{ x: smoothed.x, y: smoothed.y }],
        color: strokeColor,
        width: strokeWidth,
        isEraser: isEraserGesture
      });
      this.render();
      return { isWriting: true, strokePointsCount: 1 };
    }

    // Case 4: Active stroke continuing -> Check distance to avoid stationary tremor jitter
    const lastPt = this.activeStroke.points[this.activeStroke.points.length - 1];
    const dist = Math.hypot(smoothed.x - lastPt.x, smoothed.y - lastPt.y);

    if (dist < this.minDistThreshold) {
      this.render();
      return { isWriting: true, strokePointsCount: this.activeStroke.points.length };
    }

    // High-Density Linear Interpolation
    const stepSize = this.interpStep > 0 ? this.interpStep : 0.004;
    const numSteps = Math.max(1, Math.ceil(dist / stepSize));

    for (let i = 1; i <= numSteps; i++) {
      const t = i / numSteps;
      const interpX = lastPt.x + t * (smoothed.x - lastPt.x);
      const interpY = lastPt.y + t * (smoothed.y - lastPt.y);
      this.activeStroke.addPoint(interpX, interpY);
    }

    this.render();
    return { isWriting: true, strokePointsCount: this.activeStroke.points.length };
  }

  commitActiveStroke() {
    if (this.activeStroke && this.activeStroke.points.length > 0) {
      this.history.push(this.activeStroke);
      this.redoStack = []; // Clear redo stack on new action
      if (typeof this.onHistoryChange === 'function') {
        this.onHistoryChange(this.canUndo(), this.canRedo());
      }
    }
    this.activeStroke = null;
    this.isWriting = false;
    this.render();
  }

  // ----------------------------------------------------
  // Undo, Redo & Clear Stack Commands
  // ----------------------------------------------------
  undo() {
    if (this.history.length === 0) return false;
    const stroke = this.history.pop();
    this.redoStack.push(stroke);
    if (typeof this.onHistoryChange === 'function') {
      this.onHistoryChange(this.canUndo(), this.canRedo());
    }
    this.render();
    return true;
  }

  redo() {
    if (this.redoStack.length === 0) return false;
    const stroke = this.redoStack.pop();
    this.history.push(stroke);
    if (typeof this.onHistoryChange === 'function') {
      this.onHistoryChange(this.canUndo(), this.canRedo());
    }
    this.render();
    return true;
  }

  clearCanvas() {
    this.history = [];
    this.redoStack = [];
    this.activeStroke = null;
    this.isWriting = false;
    if (typeof this.onHistoryChange === 'function') {
      this.onHistoryChange(this.canUndo(), this.canRedo());
    }
    this.render();
  }

  canUndo() {
    return this.history.length > 0;
  }

  canRedo() {
    return this.redoStack.length > 0;
  }

  // ----------------------------------------------------
  // Canvas Rendering & Quadratic Bezier Vector Drawing
  // ----------------------------------------------------
  render() {
    if (!this.canvas || !this.ctx) return;
    const ctx = this.ctx;
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();

    const w = rect.width;
    const h = rect.height;

    // Reset transform & clear frame
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Apply High DPI coordinate scaling
    ctx.scale(dpr, dpr);

    // Render Mode Background & Grid
    if (this.mode === 'dark') {
      ctx.fillStyle = '#0B0F17';
      ctx.fillRect(0, 0, w, h);
      this.drawGrid(ctx, w, h, 'rgba(255, 255, 255, 0.05)');
    } else if (this.mode === 'light') {
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, w, h);
      this.drawGrid(ctx, w, h, 'rgba(0, 0, 0, 0.05)');
    }
    // Note: 'camera' mode leaves background transparent so video feed displays underneath.

    // Render History Strokes
    for (const stroke of this.history) {
      this.drawVectorStroke(ctx, stroke, w, h);
    }

    // Render Active Live Stroke
    if (this.activeStroke) {
      this.drawVectorStroke(ctx, this.activeStroke, w, h);
    }

    // Render 21 Hand Landmark Skeleton Overlay when hand is detected
    if (this.handLandmarks && this.handLandmarks.length === 21) {
      this.drawHandSkeleton(ctx, this.handLandmarks, w, h);
    }
  }

  setHandLandmarks(landmarks) {
    this.handLandmarks = landmarks && landmarks.length === 21 ? landmarks : null;
    this.render();
  }

  drawHandSkeleton(ctx, landmarks, w, h) {
    if (!landmarks || landmarks.length !== 21) return;

    const connections = [
      // Thumb
      [0, 1], [1, 2], [2, 3], [3, 4],
      // Index finger
      [0, 5], [5, 6], [6, 7], [7, 8],
      // Middle finger
      [9, 10], [10, 11], [11, 12],
      // Ring finger
      [13, 14], [14, 15], [15, 16],
      // Pinky
      [0, 17], [17, 18], [18, 19], [19, 20],
      // Palm bridges
      [5, 9], [9, 13], [13, 17]
    ];

    // Map 21 MediaPipe 3D coordinates (with scaleX(-1) mirror horizontal flip) to canvas pixels
    const pts = landmarks.map(lm => ({
      x: (1.0 - lm.x) * w,
      y: lm.y * h
    }));

    ctx.save();
    ctx.globalCompositeOperation = 'source-over';

    // 1. Draw Skeleton Connecting Lines
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.75)'; // Translucent Neon Cyan
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';

    for (const [startIdx, endIdx] of connections) {
      const p0 = pts[startIdx];
      const p1 = pts[endIdx];
      ctx.beginPath();
      ctx.moveTo(p0.x, p0.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.stroke();
    }

    // 2. Draw 21 Joint Circles
    for (let i = 0; i < pts.length; i++) {
      const pt = pts[i];
      ctx.beginPath();
      if (i === 8) {
        // Highlight Index Tip (Landmark 8) in Vibrant Yellow
        ctx.fillStyle = '#FFE600';
        ctx.arc(pt.x, pt.y, 5, 0, Math.PI * 2);
      } else if (i === 0) {
        // Wrist (Landmark 0) in Electric Purple
        ctx.fillStyle = '#A855F7';
        ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
      } else {
        // Other Joints in Neon Emerald Green
        ctx.fillStyle = '#10B981';
        ctx.arc(pt.x, pt.y, 3, 0, Math.PI * 2);
      }
      ctx.fill();
    }

    ctx.restore();
  }

  drawGrid(ctx, width, height, strokeColor) {
    const gridSize = 40;
    ctx.save();
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 2]);

    for (let x = 0; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
    ctx.restore();
  }

  drawVectorStroke(ctx, stroke, canvasW, canvasH) {
    if (!stroke || stroke.points.length === 0) return;

    const points = stroke.points.map(pt => ({
      x: pt.x * canvasW,
      y: pt.y * canvasH
    }));

    ctx.save();

    if (stroke.isEraser) {
      if (this.mode === 'camera') {
        // Clear strokes to reveal video feed underneath
        ctx.globalCompositeOperation = 'destination-out';
        ctx.strokeStyle = 'rgba(0,0,0,1)';
      } else if (this.mode === 'dark') {
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = '#0B0F17';
      } else {
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = '#FFFFFF';
      }
      ctx.lineWidth = stroke.width;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      this.renderStrokePath(ctx, points);
      ctx.stroke();
    } else {
      ctx.globalCompositeOperation = 'source-over';

      // Neon Glow Effect for Dark/Camera mode
      if (this.mode !== 'light') {
        ctx.save();
        ctx.strokeStyle = stroke.color;
        ctx.globalAlpha = 0.25;
        ctx.lineWidth = stroke.width + 8;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        this.renderStrokePath(ctx, points);
        ctx.stroke();
        ctx.restore();
      }

      // Core Vector Stroke
      ctx.strokeStyle = stroke.color;
      ctx.lineWidth = stroke.width;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      this.renderStrokePath(ctx, points);
      ctx.stroke();
    }

    ctx.restore();
  }

  renderStrokePath(ctx, points) {
    if (points.length === 1) {
      ctx.beginPath();
      ctx.arc(points[0].x, points[0].y, ctx.lineWidth / 2, 0, Math.PI * 2);
      ctx.fill();
      return;
    }

    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);

    if (points.length === 2) {
      ctx.lineTo(points[1].x, points[1].y);
      return;
    }

    // Midpoint Quadratic Bezier Curves for silky smooth air writing
    const firstMidX = (points[0].x + points[1].x) / 2;
    const firstMidY = (points[0].y + points[1].y) / 2;
    ctx.lineTo(firstMidX, firstMidY);

    for (let i = 1; i < points.length - 1; i++) {
      const p0 = points[i];
      const p1 = points[i + 1];
      const midX = (p0.x + p1.x) / 2;
      const midY = (p0.y + p1.y) / 2;
      ctx.quadraticCurveTo(p0.x, p0.y, midX, midY);
    }

    ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
  }

  // ----------------------------------------------------
  // Canvas PNG Export
  // ----------------------------------------------------
  exportPNG(filename = '') {
    if (!this.canvas) return null;

    // Render offscreen canvas with background filled for export
    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = this.canvas.width;
    exportCanvas.height = this.canvas.height;
    const exportCtx = exportCanvas.getContext('2d');

    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;

    exportCtx.scale(dpr, dpr);

    // Export Background
    const bgColor = this.mode === 'light' ? '#FFFFFF' : '#0B0F17';
    exportCtx.fillStyle = bgColor;
    exportCtx.fillRect(0, 0, w, h);

    // Grid
    this.drawGrid(exportCtx, w, h, this.mode === 'light' ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)');

    // History Strokes
    for (const stroke of this.history) {
      this.drawVectorStroke(exportCtx, stroke, w, h);
    }

    const dataUrl = exportCanvas.toDataURL('image/png');

    if (!filename) {
      const now = new Date();
      const timestamp = now.toISOString().replace(/[-:T.]/g, '').slice(0, 15);
      filename = `air_writing_${timestamp}.png`;
    }

    const link = document.createElement('a');
    link.download = filename;
    link.href = dataUrl;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    console.log(`[AirCanvas] Canvas exported successfully as ${filename}`);
    return dataUrl;
  }
}
