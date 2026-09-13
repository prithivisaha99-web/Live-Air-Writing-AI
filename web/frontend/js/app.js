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

  // DOM Element References - AI Assist Panel & Writing Chat
  const btnAiRecognize = document.getElementById('btn-ai-recognize');
  const btnAiAnalyzeScene = document.getElementById('btn-ai-analyze-scene');
  const btnAiClean = document.getElementById('btn-ai-clean');
  const btnAiSummarize = document.getElementById('btn-ai-summarize');
  const btnAiCopy = document.getElementById('btn-ai-copy');
  const lblApiStatus = document.getElementById('lbl-api-status');
  const aiProgressBar = document.getElementById('ai-progress-bar');

  const lblContextWriting = document.getElementById('lbl-context-writing');
  const lblContextDesc = document.getElementById('lbl-context-desc');
  const chatDisplayArea = document.getElementById('chat-display-area');
  const txtChatInput = document.getElementById('txt-chat-input');
  const btnChatSend = document.getElementById('btn-chat-send');

  let activeColor = '#00F0FF';
  let brushSize = 8;
  let isEraserActive = false;

  let currentWriting = '';
  let currentDescription = '';
  let chatHistory = [];

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
      hudGesture.className = gesture === 'DRAW' ? 'hud-val green' : (gesture === 'ERASER' ? 'hud-val red' : 'hud-val yellow');
    }

    if (hudIsDrawing) {
      hudIsDrawing.textContent = isDrawing.toString();
      hudIsDrawing.className = isDrawing ? 'hud-val green' : 'hud-val red';
    }

    if (hudStrokePts && canvasState) {
      hudStrokePts.textContent = canvasState.activeStrokeCount.toString();
    }

    if (hudFps) {
      hudFps.textContent = fps.toString();
    }
  }

  function updateHudElement(el, state) {
    if (!el) return;
    el.textContent = state;
    el.className = state === 'EXTENDED' ? 'hud-val green' : (state === 'FOLDED' ? 'hud-val red' : 'hud-val yellow');
  }

  function resetHudReadouts() {
    if (lblHandCount) { lblHandCount.textContent = 'Hands: 0'; lblHandCount.className = 'status-item hand-off'; }
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
  // 2. Toolbar & Preset Actions
  // ----------------------------------------------------
  colorBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      colorBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeColor = btn.dataset.color;
      isEraserActive = false;
      if (btnEraser) btnEraser.classList.remove('active');
      airCanvas.setColor(activeColor);
      updateBrushPreview();
    });
  });

  if (customColorPicker) {
    customColorPicker.addEventListener('input', (e) => {
      activeColor = e.target.value;
      colorBtns.forEach(b => b.classList.remove('active'));
      isEraserActive = false;
      if (btnEraser) btnEraser.classList.remove('active');
      airCanvas.setColor(activeColor);
      updateBrushPreview();
    });
  }

  if (brushSlider) {
    brushSlider.addEventListener('input', (e) => {
      brushSize = parseInt(e.target.value, 10);
      if (lblBrushSize) lblBrushSize.textContent = `${brushSize}px`;
      airCanvas.setLineWidth(brushSize);
      updateBrushPreview();
    });
  }

  function updateBrushPreview() {
    if (brushPreview) {
      brushPreview.style.width = `${Math.min(24, Math.max(4, brushSize))}px`;
      brushPreview.style.height = `${Math.min(24, Math.max(4, brushSize))}px`;
      brushPreview.style.backgroundColor = isEraserActive ? '#FF334B' : activeColor;
    }
  }
  updateBrushPreview();

  // ----------------------------------------------------
  // 3. Eraser, Canvas Mode & History Actions
  // ----------------------------------------------------
  if (btnEraser) {
    btnEraser.addEventListener('click', () => {
      isEraserActive = !isEraserActive;
      btnEraser.classList.toggle('active', isEraserActive);
      if (isEraserActive) {
        airCanvas.setColor('ERASER');
      } else {
        airCanvas.setColor(activeColor);
      }
      updateBrushPreview();
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
      airCanvas.clear();
      currentWriting = '';
      currentDescription = '';
      if (lblContextWriting) lblContextWriting.textContent = 'Writing: (Canvas cleared)';
      if (lblContextDesc) lblContextDesc.textContent = "Description: Air-write and click 'Recognize Writing' to set context";
    });
  }

  if (btnExportPng) {
    btnExportPng.addEventListener('click', () => {
      airCanvas.exportPNG('air-writing-drawing.png');
    });
  }

  // ----------------------------------------------------
  // 4. Settings Modal Management
  // ----------------------------------------------------
  if (btnSettings) {
    btnSettings.addEventListener('click', async () => {
      if (settingsModal) settingsModal.classList.remove('hidden');
      await populateCameraDeviceList();
    });
  }

  if (btnCloseModal) {
    btnCloseModal.addEventListener('click', () => {
      if (settingsModal) settingsModal.classList.add('hidden');
    });
  }

  if (btnSaveSettings) {
    btnSaveSettings.addEventListener('click', async () => {
      const selectedDeviceId = selectCameraInput ? selectCameraInput.value : null;
      const isMirrored = chkMirrorCamera ? chkMirrorCamera.checked : true;

      cameraManager.setMirrored(isMirrored);
      airCanvas.setMirrored(isMirrored);

      if (selectedDeviceId && selectedDeviceId !== cameraManager.currentDeviceId) {
        if (cameraManager.isCameraRunning) {
          handTracker.stopTracking();
          const success = await cameraManager.startCamera(selectedDeviceId);
          if (success) {
            handTracker.startTracking(cameraManager.videoElement, onHandTrackingResults);
          }
        } else {
          cameraManager.currentDeviceId = selectedDeviceId;
        }
      }

      if (settingsModal) settingsModal.classList.add('hidden');
    });
  }

  async function populateCameraDeviceList() {
    if (!selectCameraInput) return;
    const devices = await cameraManager.getVideoDevices();
    selectCameraInput.innerHTML = '';
    devices.forEach((device, idx) => {
      const opt = document.createElement('option');
      opt.value = device.deviceId;
      opt.textContent = device.label || `Camera ${idx + 1}`;
      if (device.deviceId === cameraManager.currentDeviceId) {
        opt.selected = true;
      }
      selectCameraInput.appendChild(opt);
    });
  }

  // ----------------------------------------------------
  // 5. AI Assist API Integration & AI Writing Chat
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
      return data.result || data.answer || data;
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

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function appendChatMessage(role, content, isHtml = false) {
    if (!chatDisplayArea) return null;

    const msgDiv = document.createElement('div');
    msgDiv.style.marginBottom = '8px';

    const safeContent = isHtml ? content : escapeHtml(content);

    if (role === 'user') {
      msgDiv.style.textAlign = 'right';
      msgDiv.innerHTML = `<span style="background: rgba(0,240,255,0.15); color: #00F0FF; padding: 4px 8px; border-radius: 8px; border: 1px solid rgba(0,240,255,0.3);"><b>You:</b> ${safeContent}</span>`;
    } else if (role === 'assistant') {
      msgDiv.style.textAlign = 'left';
      msgDiv.innerHTML = `<span style="background: rgba(168,85,247,0.15); color: #E2E8F0; padding: 4px 8px; border-radius: 8px; border: 1px solid rgba(168,85,247,0.3);"><b style="color: #A855F7;">🤖 AI:</b> ${safeContent}</span>`;
    } else {
      msgDiv.style.textAlign = 'center';
      msgDiv.innerHTML = `<span style="color: #94A3B8; font-size: 10px;">${safeContent}</span>`;
    }

    chatDisplayArea.appendChild(msgDiv);
    chatDisplayArea.scrollTop = chatDisplayArea.scrollHeight;
    return msgDiv;
  }

  async function sendChatMessage() {
    const question = txtChatInput ? txtChatInput.value.trim() : '';
    console.log('[AI CHAT] sendChatMessage called. Question:', question);

    if (!question) {
      console.warn('[AI CHAT] Empty question provided.');
      appendChatMessage('assistant', '⚠️ Please type a question before clicking Send.', true);
      return;
    }

    // Append user question & clear input
    console.log('[AI CHAT] Appending user message to chat UI...');
    appendChatMessage('user', question);
    if (txtChatInput) txtChatInput.value = '';

    // Disable input controls during API request
    if (btnChatSend) btnChatSend.disabled = true;
    if (txtChatInput) txtChatInput.disabled = true;

    const loadingMsgEl = appendChatMessage('assistant', '⌛ AI is thinking...', true);

    try {
      const payload = {
        writing: currentWriting || '',
        description: currentDescription || '',
        question: question,
        history: [...chatHistory]
      };

      console.log('[AI CHAT] Sending POST /api/chat-writing payload:', payload);
      const responseText = await callAiApi('/api/chat-writing', payload);
      const answer = typeof responseText === 'string' ? responseText : (responseText.answer || responseText.result || 'No response text');

      console.log('[AI CHAT] Received AI response:', answer);
      if (loadingMsgEl) loadingMsgEl.remove();

      appendChatMessage('assistant', answer, false);

      chatHistory.push({ role: 'user', content: question });
      chatHistory.push({ role: 'assistant', content: answer });
    } catch (err) {
      if (loadingMsgEl) loadingMsgEl.remove();
      console.error('[Web Chat Error]', err);
      appendChatMessage('assistant', `❌ ${err.message}`, true);
    } finally {
      if (btnChatSend) btnChatSend.disabled = false;
      if (txtChatInput) txtChatInput.disabled = false;
      if (txtChatInput) txtChatInput.focus();
    }
  }

  // 1. Recognize Writing
  if (btnAiRecognize) {
    btnAiRecognize.addEventListener('click', async () => {
      if (!airCanvas || !airCanvas.canvas) return;

      try {
        const loadingMsgEl = appendChatMessage('assistant', '⌛ Analyzing handwriting and context with Gemini Vision...', true);
        const dataUrl = airCanvas.canvas.toDataURL('image/png');
        const result = await callAiApi('/api/recognize', { image: dataUrl });

        if (loadingMsgEl) loadingMsgEl.remove();

        const text = typeof result === 'string' ? result : (result.result || result.text || '');
        currentWriting = text;
        currentDescription = `Handwritten content: '${text}'`;

        if (lblContextWriting) lblContextWriting.textContent = `Writing: ${currentWriting}`;
        if (lblContextDesc) lblContextDesc.textContent = `Description: ${currentDescription}`;

        appendChatMessage(
          'assistant',
          `Detected: <b>"${escapeHtml(currentWriting)}"</b><br><i style="color:#94A3B8;">Description: ${escapeHtml(currentDescription)}</i><br><br>Ask me any question about your writing below!`,
          true
        );
      } catch (err) {
        console.error('[AI Recognize Error]', err);
        appendChatMessage('assistant', `❌ ${err.message}`, true);
      }
    });
  }

  // 2. Analyze Scene
  if (btnAiAnalyzeScene) {
    btnAiAnalyzeScene.addEventListener('click', async () => {
      const frameDataUrl = captureWorkspaceFrame();
      if (!frameDataUrl) {
        appendChatMessage('assistant', '⚠️ No active camera stream or canvas image available to analyze.', true);
        return;
      }

      try {
        const loadingMsgEl = appendChatMessage('assistant', '🔍 Analyzing scene & objects via Gemini AI...', true);
        const result = await callAiApi('/api/analyze-scene', { image: frameDataUrl });
        if (loadingMsgEl) loadingMsgEl.remove();
        const text = typeof result === 'string' ? result : (result.result || result.analysis || '');
        appendChatMessage('assistant', `🔍 <b>Scene Analysis:</b><br>${escapeHtml(text)}`, true);
      } catch (err) {
        console.error('[AI Scene Analysis Error]', err);
        appendChatMessage('assistant', `❌ ${err.message}`, true);
      }
    });
  }

  // 3. Clean Fix Text
  if (btnAiClean) {
    btnAiClean.addEventListener('click', async () => {
      if (!currentWriting) {
        appendChatMessage('assistant', '⚠️ Please recognize writing first before cleaning.', true);
        return;
      }

      try {
        const loadingMsgEl = appendChatMessage('assistant', '⌛ Cleaning and formatting text via Gemini AI...', true);
        const result = await callAiApi('/api/clean', { text: currentWriting });
        if (loadingMsgEl) loadingMsgEl.remove();
        const text = typeof result === 'string' ? result : (result.result || result.text || currentWriting);
        currentWriting = text;
        if (lblContextWriting) lblContextWriting.textContent = `Writing: ${currentWriting}`;
        appendChatMessage('assistant', `✍️ <b>Cleaned Text:</b><br>${escapeHtml(currentWriting)}`, true);
      } catch (err) {
        console.error('[AI Clean Error]', err);
        appendChatMessage('assistant', `❌ ${err.message}`, true);
      }
    });
  }

  // 4. Summarize Notes
  if (btnAiSummarize) {
    btnAiSummarize.addEventListener('click', async () => {
      if (!currentWriting) {
        appendChatMessage('assistant', '⚠️ Please recognize writing first before summarizing.', true);
        return;
      }

      try {
        const loadingMsgEl = appendChatMessage('assistant', '⌛ Summarizing notes via Gemini AI...', true);
        const result = await callAiApi('/api/summarize', { text: currentWriting });
        if (loadingMsgEl) loadingMsgEl.remove();
        const text = typeof result === 'string' ? result : (result.result || result.summary || currentWriting);
        appendChatMessage('assistant', `📝 <b>Summary:</b><br>${escapeHtml(text)}`, true);
      } catch (err) {
        console.error('[AI Summarize Error]', err);
        appendChatMessage('assistant', `❌ ${err.message}`, true);
      }
    });
  }

  // 5. Clipboard Copy
  if (btnAiCopy) {
    btnAiCopy.addEventListener('click', () => {
      if (!currentWriting) {
        btnAiCopy.textContent = '⚠️ No Text to Copy';
        setTimeout(() => { btnAiCopy.textContent = '📋 Copy Text'; }, 1500);
        return;
      }

      navigator.clipboard.writeText(currentWriting).then(() => {
        btnAiCopy.textContent = '✅ Copied!';
        setTimeout(() => { btnAiCopy.textContent = '📋 Copy Text'; }, 1500);
      }).catch(err => {
        console.error('Clipboard copy failed:', err);
      });
    });
  }

  // 6. Chat Input & Send Button Event Listeners
  if (btnChatSend) {
    console.log('[AI CHAT] Attaching click listener to #btn-chat-send');
    btnChatSend.addEventListener('click', (e) => {
      e.preventDefault();
      console.log('[AI CHAT] Send button click event triggered');
      sendChatMessage();
    });
  } else {
    console.warn('[AI CHAT] #btn-chat-send element not found in DOM during initApp()');
  }

  if (txtChatInput) {
    console.log('[AI CHAT] Attaching keydown listener to #txt-chat-input');
    txtChatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        console.log('[AI CHAT] Enter keydown event triggered in #txt-chat-input');
        sendChatMessage();
      }
    });
  } else {
    console.warn('[AI CHAT] #txt-chat-input element not found in DOM during initApp()');
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}

