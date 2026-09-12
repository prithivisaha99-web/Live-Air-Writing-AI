/**
 * Live Air Writing AI - Web Frontend Controller & Air Canvas Connector (Phase 6)
 */
import { BrowserCameraManager } from "./camera.js";
import { BrowserHandTracker } from "./hand_tracker.js";
import { BrowserGestureDetector } from "./gesture_detector.js";
import { BrowserAirCanvas } from "./air_canvas.js";

function initApp() {
  console.log('[Web App] UI, MediaPipe, Gesture & Air Canvas Controller initialized');

  // Initialize Camera Manager, Hand Tracker, Gesture Detector & Air Canvas
  const cameraManager = new BrowserCameraManager('webcam-video', 'lbl-cam-status', 'btn-toggle-cam');
  const handTracker = new BrowserHandTracker({
    numHands: 1,
    minDetectionConfidence: 0.2,
    minTrackingConfidence: 0.2
  });
  const gestureDetector = new BrowserGestureDetector(4);

  // DOM Element References - Status Readouts & HUD
  const lblHandCount = document.getElementById('lbl-hand-count');
  const lblFingertipPos = document.getElementById('lbl-fingertip-pos');
  const lblFps = document.getElementById('lbl-fps');
  const lblGestureStatus = document.getElementById('lbl-gesture-status');

  const hudIdxState = document.getElementById('hud-idx-state');
  const hudMidState = document.getElementById('hud-mid-state');
  const hudRngState = document.getElementById('hud-rng-state');
  const hudPnkState = document.getElementById('hud-pnk-state');
  const hudGesture = document.getElementById('hud-gesture');
  const hudIsDrawing = document.getElementById('hud-is-drawing');
  const hudStrokePts = document.getElementById('hud-stroke-pts');
  const hudFps = document.getElementById('hud-fps');

  // DOM Element References - Controls
  const btnToggleCam = document.getElementById('btn-toggle-cam');
  const btnExportPng = document.getElementById('btn-export-png');

  // DOM Element References - Toolbar Controls
  const colorBtns = document.querySelectorAll('.color-btn');
  const customColorPicker = document.getElementById('picker-custom-color');
  const brushSlider = document.getElementById('slider-brush-size');
  const lblBrushSize = document.getElementById('lbl-brush-size');
  const brushPreview = document.getElementById('brush-preview');
  const btnEraser = document.getElementById('btn-toggle-eraser');
  const selectCanvasMode = document.getElementById('select-canvas-mode');
  const btnUndo = document.getElementById('btn-undo');
  const btnRedo = document.getElementById('btn-redo');
  const btnClear = document.getElementById('btn-clear');

  // DOM Element References - Settings Modal
  const btnSettings = document.getElementById('btn-settings');
  const settingsModal = document.getElementById('settings-modal');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const btnSaveSettings = document.getElementById('btn-save-settings');
  const selectCameraInput = document.getElementById('select-camera-input');
  const chkMirrorCamera = document.getElementById('chk-mirror-camera');

  // DOM Element References - AI Assist Panel
  const btnAiRecognize = document.getElementById('btn-ai-recognize');
  const btnAiAnalyzeScene = document.getElementById('btn-ai-analyze-scene');
  const btnAiClean = document.getElementById('btn-ai-clean');
  const btnAiSummarize = document.getElementById('btn-ai-summarize');
  const btnAiCopy = document.getElementById('btn-ai-copy');
  const txtAiOutput = document.getElementById('txt-ai-output');
  const lblApiStatus = document.getElementById('lbl-api-status');
  const aiProgressBar = document.getElementById('ai-progress-bar');

  let activeColor = '#00F0FF';
  let brushSize = 8;
  let isEraserActive = false;

  // Initialize Browser Air Canvas
  const airCanvas = new BrowserAirCanvas('air-canvas', {
    mode: 'camera',
    color: activeColor,
    width: brushSize,
    onHistoryChange: (canUndo, canRedo) => {
      if (btnUndo) btnUndo.disabled = !canUndo;
      if (btnRedo) btnRedo.disabled = !canRedo;
    }
  });

  // ----------------------------------------------------
  // 1. Browser Camera & MediaPipe Integration
  // ----------------------------------------------------
  if (btnToggleCam) {
    btnToggleCam.addEventListener('click', async () => {
      if (cameraManager.isCameraRunning) {
        handTracker.stopTracking();
        await cameraManager.stopCamera();
        resetHudReadouts();
        airCanvas.setHandLandmarks(null);
        airCanvas.processPoint(null, false, 'NO HAND');
      } else {
        const success = await cameraManager.startCamera(cameraManager.currentDeviceId);
        if (success) {
          handTracker.startTracking(cameraManager.videoElement, onHandTrackingResults);
        }
      }
    });
  }

  function onHandTrackingResults(data) {
    const { handCount, landmarks, rawIndex, indexPixel, fps, status } = data;

    // Render Hand Skeleton Overlay on Canvas
    if (handCount > 0 && landmarks) {
      airCanvas.setHandLandmarks(landmarks);
    } else {
      airCanvas.setHandLandmarks(null);
    }

    // Evaluate Gesture Detector
    const gestureResult = gestureDetector.update(landmarks);
    const { gesture, fingerStates, isDrawing } = gestureResult;

    // Process Fingertip Point into Air Canvas
    const canvasState = airCanvas.processPoint(rawIndex, isDrawing, gesture);

    // Update Header Status Bar
    if (lblHandCount) {
      lblHandCount.textContent = `Hands: ${handCount}`;
      lblHandCount.className = handCount > 0 ? 'status-item cam-ready' : 'status-item hand-off';
    }

    if (lblFps) {
      lblFps.textContent = `FPS: ${fps}`;
    }

    if (lblFingertipPos) {
      if (indexPixel) {
        lblFingertipPos.textContent = `Index: (${indexPixel.x}, ${indexPixel.y})`;
      } else {
        lblFingertipPos.textContent = 'Index: (0, 0)';
      }
    }

    if (lblGestureStatus) {
      lblGestureStatus.textContent = `GESTURE: ${gesture}`;
    }

    // Update Diagnostic HUD
    updateHudElement(hudIdxState, fingerStates.Index);
    updateHudElement(hudMidState, fingerStates.Middle);
    updateHudElement(hudRngState, fingerStates.Ring);
    updateHudElement(hudPnkState, fingerStates.Pinky);

    if (hudGesture) {
      hudGesture.textContent = gesture;
      hudGesture.className = gesture === 'DRAW' ? 'hud-val yellow' : (gesture === 'ERASER' ? 'hud-val purple' : 'hud-val cyan');
    }

    if (hudIsDrawing) {
      hudIsDrawing.textContent = `${isDrawing}`;
      hudIsDrawing.className = isDrawing ? 'hud-val green' : 'hud-val red';
    }

    if (hudStrokePts) {
      hudStrokePts.textContent = `${canvasState.strokePointsCount}`;
    }

    if (hudFps) {
      hudFps.textContent = `${fps}`;
    }
  }

  function updateHudElement(el, state) {
    if (!el) return;
    el.textContent = state;
    el.className = state === 'EXTENDED' ? 'hud-val green' : 'hud-val red';
  }

  function resetHudReadouts() {
    if (lblHandCount) {
      lblHandCount.textContent = 'Hands: 0';
      lblHandCount.className = 'status-item hand-off';
    }
    if (lblFingertipPos) lblFingertipPos.textContent = 'Index: (0, 0)';
    if (lblFps) lblFps.textContent = 'FPS: 0.0';
    if (lblGestureStatus) lblGestureStatus.textContent = 'GESTURE: NO HAND';

    updateHudElement(hudIdxState, 'NONE');
    updateHudElement(hudMidState, 'NONE');
    updateHudElement(hudRngState, 'NONE');
    updateHudElement(hudPnkState, 'NONE');

    if (hudGesture) { hudGesture.textContent = 'NO HAND'; hudGesture.className = 'hud-val yellow'; }
    if (hudIsDrawing) { hudIsDrawing.textContent = 'false'; hudIsDrawing.className = 'hud-val red'; }
    if (hudStrokePts) hudStrokePts.textContent = '0';
    if (hudFps) hudFps.textContent = '0.0';
  }

  if (chkMirrorCamera) {
    chkMirrorCamera.addEventListener('change', (e) => {
      cameraManager.setMirror(e.target.checked);
    });
  }

  // ----------------------------------------------------
  // 2. Color Palette & Brush Size Event Handling
  // ----------------------------------------------------
  colorBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      colorBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeColor = btn.dataset.color;
      airCanvas.setColor(activeColor);
      updateBrushPreview(activeColor, brushSize);

      if (isEraserActive) {
        isEraserActive = false;
        btnEraser.classList.remove('active');
      }
    });
  });

  if (customColorPicker) {
    customColorPicker.addEventListener('input', (e) => {
      colorBtns.forEach(b => b.classList.remove('active'));
      activeColor = e.target.value;
      airCanvas.setColor(activeColor);
      updateBrushPreview(activeColor, brushSize);
    });
  }

  if (brushSlider) {
    brushSlider.addEventListener('input', (e) => {
      brushSize = parseInt(e.target.value, 10);
      lblBrushSize.textContent = `${brushSize}px`;
      airCanvas.setBrushWidth(brushSize);
      updateBrushPreview(activeColor, brushSize);
    });
  }

  function updateBrushPreview(color, size) {
    if (brushPreview) {
      brushPreview.style.backgroundColor = isEraserActive ? '#0B0F17' : color;
      const diameter = Math.max(4, Math.min(22, size));
      brushPreview.style.width = `${diameter}px`;
      brushPreview.style.height = `${diameter}px`;
    }
  }

  // ----------------------------------------------------
  // 3. Eraser, Canvas Mode & History Actions
  // ----------------------------------------------------
  if (btnEraser) {
    btnEraser.addEventListener('click', () => {
      isEraserActive = airCanvas.toggleEraser();
      btnEraser.classList.toggle('active', isEraserActive);
      updateBrushPreview(activeColor, brushSize);
    });
  }

  if (selectCanvasMode) {
    selectCanvasMode.addEventListener('change', (e) => {
      airCanvas.setCanvasMode(e.target.value);
    });
  }

  if (btnUndo) {
    btnUndo.addEventListener('click', () => {
      airCanvas.undo();
    });
  }

  if (btnRedo) {
    btnRedo.addEventListener('click', () => {
      airCanvas.redo();
    });
  }

  if (btnClear) {
    btnClear.addEventListener('click', () => {
      airCanvas.clearCanvas();
    });
  }

  if (btnExportPng) {
    btnExportPng.addEventListener('click', () => {
      airCanvas.exportPNG();
    });
  }

  // ----------------------------------------------------
  // 4. Settings Modal Interactivity
  // ----------------------------------------------------
  if (btnSettings && settingsModal) {
    btnSettings.addEventListener('click', async () => {
      settingsModal.classList.remove('hidden');
      if (selectCameraInput) {
        await cameraManager.enumerateCameras(selectCameraInput);
      }
    });
  }

  if (btnCloseModal && settingsModal) {
    btnCloseModal.addEventListener('click', () => {
      settingsModal.classList.add('hidden');
    });
  }

  if (btnSaveSettings && settingsModal) {
    btnSaveSettings.addEventListener('click', async () => {
      const selectedCamId = selectCameraInput ? selectCameraInput.value : null;
      if (selectedCamId && cameraManager.isCameraRunning) {
        await cameraManager.startCamera(selectedCamId);
        handTracker.startTracking(cameraManager.videoElement, onHandTrackingResults);
      }
      settingsModal.classList.add('hidden');
    });
  }

  // ----------------------------------------------------
  // 5. AI Assist API Integration & Actions
  // ----------------------------------------------------
  const API_BASE = (window.location.protocol === 'http:' || window.location.protocol === 'https:') ? '' : 'http://localhost:8000';

  async function checkBackendApiStatus() {
    try {
      const response = await fetch(`${API_BASE}/api/health`);
      if (response.ok) {
        const data = await response.json();
        if (data.has_api_key) {
          if (lblApiStatus) {
            lblApiStatus.textContent = 'API Ready';
            lblApiStatus.className = 'api-status-badge badge-ready';
          }
        } else {
          if (lblApiStatus) {
            lblApiStatus.textContent = 'API Key Missing';
            lblApiStatus.className = 'api-status-badge badge-missing';
          }
        }
      }
    } catch (err) {
      console.warn('[AI Assist] Could not query backend health:', err);
    }
  }

  // Query backend status on startup
  checkBackendApiStatus();

  async function callAiApi(endpoint, payload) {
    if (aiProgressBar) aiProgressBar.classList.remove('hidden');

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || `API request failed with status ${response.status}`);
      }
      return data.result;
    } finally {
      if (aiProgressBar) aiProgressBar.classList.add('hidden');
    }
  }

  function captureWorkspaceFrame() {
    const video = cameraManager ? cameraManager.videoElement : null;
    if (cameraManager && cameraManager.isCameraRunning && video && video.videoWidth > 0 && video.videoHeight > 0) {
      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = video.videoWidth;
      tempCanvas.height = video.videoHeight;
      const ctx = tempCanvas.getContext('2d');
      if (cameraManager.isMirrored) {
        ctx.translate(tempCanvas.width, 0);
        ctx.scale(-1, 1);
      }
      ctx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);
      if (airCanvas && airCanvas.canvas) {
        ctx.drawImage(airCanvas.canvas, 0, 0, tempCanvas.width, tempCanvas.height);
      }
      return tempCanvas.toDataURL('image/png');
    } else if (airCanvas && airCanvas.canvas) {
      return airCanvas.canvas.toDataURL('image/png');
    }
    return null;
  }

  // 1. Recognize Writing
  if (btnAiRecognize) {
    btnAiRecognize.addEventListener('click', async () => {
      if (!airCanvas || !airCanvas.canvas) return;

      try {
        txtAiOutput.value = '⌛ Transcribing handwritten canvas notes via Gemini AI...';
        const dataUrl = airCanvas.canvas.toDataURL('image/png');
        const result = await callAiApi('/api/recognize', { image: dataUrl });
        txtAiOutput.value = result;
      } catch (err) {
        console.error('[AI Recognize Error]', err);
        txtAiOutput.value = `❌ ${err.message}`;
      }
    });
  }

  // 2. Analyze Scene
  if (btnAiAnalyzeScene) {
    btnAiAnalyzeScene.addEventListener('click', async () => {
      const frameDataUrl = captureWorkspaceFrame();
      if (!frameDataUrl) {
        txtAiOutput.value = '⚠️ No active camera stream or canvas image available to analyze.';
        return;
      }

      try {
        txtAiOutput.value = '⌛ Analyzing scene & objects via Gemini AI...';
        const result = await callAiApi('/api/analyze-scene', { image: frameDataUrl });
        txtAiOutput.value = result;
      } catch (err) {
        console.error('[AI Scene Analysis Error]', err);
        txtAiOutput.value = `❌ ${err.message}`;
      }
    });
  }

  // 2. Clean Fix Text
  if (btnAiClean) {
    btnAiClean.addEventListener('click', async () => {
      const currentText = txtAiOutput ? txtAiOutput.value.trim() : '';
      if (!currentText || currentText.startsWith('❌') || currentText.startsWith('⚠️') || currentText.startsWith('⌛')) {
        txtAiOutput.value = '⚠️ Please recognize or enter valid text first before cleaning.';
        return;
      }

      try {
        txtAiOutput.value = '⌛ Cleaning and formatting text via Gemini AI...';
        const result = await callAiApi('/api/clean', { text: currentText });
        txtAiOutput.value = result;
      } catch (err) {
        console.error('[AI Clean Error]', err);
        txtAiOutput.value = `❌ ${err.message}`;
      }
    });
  }

  // 3. Summarize Notes
  if (btnAiSummarize) {
    btnAiSummarize.addEventListener('click', async () => {
      const currentText = txtAiOutput ? txtAiOutput.value.trim() : '';
      if (!currentText || currentText.startsWith('❌') || currentText.startsWith('⚠️') || currentText.startsWith('⌛')) {
        txtAiOutput.value = '⚠️ Please recognize or enter valid text first before summarizing.';
        return;
      }

      try {
        txtAiOutput.value = '⌛ Summarizing notes via Gemini AI...';
        const result = await callAiApi('/api/summarize', { text: currentText });
        txtAiOutput.value = result;
      } catch (err) {
        console.error('[AI Summarize Error]', err);
        txtAiOutput.value = `❌ ${err.message}`;
      }
    });
  }

  // 4. Clipboard Copy
  if (btnAiCopy && txtAiOutput) {
    btnAiCopy.addEventListener('click', () => {
      const text = txtAiOutput.value.trim();
      if (!text || text.startsWith('❌') || text.startsWith('⚠️') || text.startsWith('⌛')) {
        btnAiCopy.textContent = '⚠️ No Text to Copy';
        setTimeout(() => { btnAiCopy.textContent = '📋 Copy Text'; }, 1500);
        return;
      }

      navigator.clipboard.writeText(text).then(() => {
        btnAiCopy.textContent = '✅ Copied!';
        setTimeout(() => { btnAiCopy.textContent = '📋 Copy Text'; }, 1500);
      }).catch(err => {
        console.error('Clipboard copy failed:', err);
      });
    });
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}

