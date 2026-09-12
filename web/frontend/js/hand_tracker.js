/**
 * Live Air Writing AI - Browser MediaPipe Hand Tracker (Phase 4 & Phase 8 Fix)
 * Dynamically loads official @mediapipe/tasks-vision SDK in VIDEO mode with GPU -> CPU fallback.
 * Asynchronous initialization ensures CDN or WebGL failures never block UI buttons or camera operations.
 */

export class BrowserHandTracker {
  constructor(options = {}) {
    this.handLandmarker = null;
    this.isReady = false;
    this.isTracking = false;
    this.animFrameId = null;
    this.lastVideoTime = -1;
    this.initError = null;

    // FPS calculation state
    this.fps = 0;
    this.frameCount = 0;
    this.lastFpsTime = performance.now();

    // Configuration thresholds
    this.numHands = options.numHands || 1;
    this.minDetectionConfidence = options.minDetectionConfidence || 0.2;
    this.minTrackingConfidence = options.minTrackingConfidence || 0.2;

    this.onResultsCallback = null;
    this.initPromise = this.init();
  }

  async init() {
    try {
      console.log('[MediaPipe] Dynamically loading Tasks Vision SDK...');
      const visionModule = await import("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14");
      const { HandLandmarker, FilesetResolver } = visionModule;

      console.log('[MediaPipe] Initializing FilesetResolver for Vision WASM...');
      const vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
      );

      console.log('[MediaPipe] Creating HandLandmarker in VIDEO mode...');
      // Try GPU delegate first; fallback to CPU if GPU WebGL context is unavailable
      try {
        this.handLandmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            delegate: "GPU"
          },
          runningMode: "VIDEO",
          numHands: this.numHands,
          minHandDetectionConfidence: this.minDetectionConfidence,
          minHandPresenceConfidence: this.minTrackingConfidence,
          minTrackingConfidence: this.minTrackingConfidence
        });
      } catch (gpuErr) {
        console.warn('[MediaPipe] GPU delegate failed, falling back to CPU:', gpuErr);
        this.handLandmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            delegate: "CPU"
          },
          runningMode: "VIDEO",
          numHands: this.numHands,
          minHandDetectionConfidence: this.minDetectionConfidence,
          minHandPresenceConfidence: this.minTrackingConfidence,
          minTrackingConfidence: this.minTrackingConfidence
        });
      }

      this.isReady = true;
      console.log('[MediaPipe] HandLandmarker initialized successfully.');
    } catch (err) {
      console.error('[MediaPipe] Asynchronous initialization failed:', err);
      this.initError = err;
      this.isReady = false;
    }
  }

  startTracking(videoElement, onResults) {
    if (!videoElement) {
      console.warn('[MediaPipe] Cannot start tracking: Video element missing.');
      return;
    }

    this.onResultsCallback = onResults;
    this.isTracking = true;
    this.lastVideoTime = -1;

    const processFrame = () => {
      if (!this.isTracking) return;

      const now = performance.now();

      // Calculate FPS
      this.frameCount++;
      if (now - this.lastFpsTime >= 1000) {
        this.fps = Math.round((this.frameCount * 1000) / (now - this.lastFpsTime));
        this.frameCount = 0;
        this.lastFpsTime = now;
      }

      if (
        this.isReady &&
        this.handLandmarker &&
        videoElement.currentTime !== this.lastVideoTime &&
        videoElement.readyState >= 2
      ) {
        this.lastVideoTime = videoElement.currentTime;

        try {
          const results = this.handLandmarker.detectForVideo(videoElement, now);
          this.handleDetections(results, videoElement);
        } catch (err) {
          console.error('[MediaPipe] Error during detectForVideo:', err);
        }
      } else if (!this.isReady) {
        if (this.onResultsCallback) {
          const statusMsg = this.initError ? 'MediaPipe Offline (Mouse/Touch active)' : 'Loading MediaPipe Model...';
          this.onResultsCallback({
            handCount: 0,
            landmarks: null,
            rawIndex: null,
            indexPixel: null,
            fps: this.fps,
            status: statusMsg
          });
        }
      }

      this.animFrameId = requestAnimationFrame(processFrame);
    };

    this.animFrameId = requestAnimationFrame(processFrame);
    console.log('[MediaPipe] Hand tracking loop started.');
  }

  handleDetections(results, videoElement) {
    if (!this.onResultsCallback) return;

    const rawHandsCount = results && results.landmarks ? results.landmarks.length : 0;

    if (rawHandsCount > 0) {
      const primaryLandmarks = results.landmarks[0]; // 21 hand landmarks
      const indexTip = primaryLandmarks[8]; // Landmark 8 = INDEX_TIP

      const vw = videoElement.videoWidth || 640;
      const vh = videoElement.videoHeight || 480;

      // Mirrored horizontal coordinate for scaleX(-1) display
      const normX = 1.0 - indexTip.x;
      const normY = indexTip.y;

      const px = Math.round(normX * vw);
      const py = Math.round(normY * vh);

      this.onResultsCallback({
        handCount: 1,
        landmarks: primaryLandmarks,
        rawIndex: { x: normX, y: normY },
        indexPixel: { x: px, y: py },
        fps: this.fps,
        status: 'Hand Detected'
      });
    } else {
      this.onResultsCallback({
        handCount: 0,
        landmarks: null,
        rawIndex: null,
        indexPixel: null,
        fps: this.fps,
        status: 'No Hand Detected'
      });
    }
  }

  stopTracking() {
    this.isTracking = false;
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    console.log('[MediaPipe] Hand tracking loop stopped.');
  }
}
