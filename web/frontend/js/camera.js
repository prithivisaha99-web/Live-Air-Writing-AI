/**
 * Live Air Writing AI - Browser Camera Manager (Phase 3)
 * Handles client-side webcam access using navigator.mediaDevices.getUserMedia()
 */
export class BrowserCameraManager {
  constructor(videoElementId, statusLabelId, toggleBtnId) {
    this.videoElement = document.getElementById(videoElementId);
    this.statusLabel = document.getElementById(statusLabelId);
    this.toggleBtn = document.getElementById(toggleBtnId);

    this.mediaStream = null;
    this.isCameraRunning = false;
    this.currentDeviceId = null;
    this.isMirrored = true;

    this.init();
  }

  init() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.updateStatus('Camera API Unavailable', 'red');
      console.warn('[Camera] navigator.mediaDevices.getUserMedia is not supported by this browser.');
      return;
    }

    // Populate camera options if available
    this.enumerateCameras();
  }

  async enumerateCameras(selectElement = null) {
    try {
      if (!navigator.mediaDevices.enumerateDevices) return [];
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(device => device.kind === 'videoinput');

      if (selectElement) {
        selectElement.innerHTML = '';
        videoDevices.forEach((device, index) => {
          const option = document.createElement('option');
          option.value = device.deviceId;
          option.textContent = device.label || `Camera ${index + 1}`;
          selectElement.appendChild(option);
        });
      }
      return videoDevices;
    } catch (err) {
      console.warn('[Camera] Failed to enumerate camera devices:', err);
      return [];
    }
  }

  async startCamera(deviceId = null) {
    if (this.isCameraRunning) {
      await this.stopCamera();
    }

    this.updateStatus('Initializing Camera...', 'yellow');

    const constraints = {
      audio: false, // VIDEO ONLY - NO MICROPHONE
      video: deviceId
        ? { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } }
        : { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }
    };

    try {
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.mediaStream = stream;
      this.videoElement.srcObject = stream;
      this.isCameraRunning = true;
      this.currentDeviceId = deviceId;

      await this.videoElement.play();

      this.updateStatus('Camera: Active', 'green');
      if (this.toggleBtn) {
        this.toggleBtn.textContent = '⏹️ Stop Camera';
        this.toggleBtn.classList.add('active');
      }

      console.log('[Camera] Browser webcam started successfully.');
      return true;

    } catch (error) {
      this.isCameraRunning = false;
      console.error('[Camera] Error accessing webcam:', error);

      let userMsg = 'Camera Error';
      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        userMsg = 'Camera Permission Denied';
      } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        userMsg = 'No Camera Device Found';
      } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
        userMsg = 'Camera Already In Use';
      } else if (error.name === 'OverconstrainedError') {
        userMsg = 'Camera Resolution Unsupported';
      }

      this.updateStatus(userMsg, 'red');
      if (this.toggleBtn) {
        this.toggleBtn.textContent = '📹 Start Camera';
        this.toggleBtn.classList.remove('active');
      }
      return false;
    }
  }

  async stopCamera() {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }

    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }

    this.isCameraRunning = false;
    this.updateStatus('Camera: Stopped', 'muted');

    if (this.toggleBtn) {
      this.toggleBtn.textContent = '📹 Start Camera';
      this.toggleBtn.classList.remove('active');
    }

    console.log('[Camera] Browser webcam stopped.');
  }

  async toggleCamera() {
    if (this.isCameraRunning) {
      await this.stopCamera();
    } else {
      await this.startCamera(this.currentDeviceId);
    }
  }

  setMirror(enableMirror) {
    this.isMirrored = enableMirror;
    if (this.videoElement) {
      this.videoElement.style.transform = enableMirror ? 'scaleX(-1)' : 'scaleX(1)';
    }
  }

  updateStatus(text, state) {
    if (!this.statusLabel) return;
    this.statusLabel.textContent = text;

    this.statusLabel.classList.remove('cam-ready', 'cam-active', 'cam-error', 'hand-off');
    if (state === 'green' || state === 'cam-ready') {
      this.statusLabel.classList.add('cam-ready');
    } else if (state === 'red' || state === 'cam-error') {
      this.statusLabel.classList.add('cam-error');
    } else {
      this.statusLabel.classList.add('hand-off');
    }
  }
}
