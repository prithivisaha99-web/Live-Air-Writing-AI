/**
 * Live Air Writing AI - Browser Gesture Detector (Phase 5)
 * Multi-signal geometric palm-relative finger classifier with temporal hysteresis.
 */

export class BrowserGestureDetector {
  static WRIST = 0;
  static INDEX_MCP = 5; static INDEX_PIP = 6; static INDEX_DIP = 7; static INDEX_TIP = 8;
  static MIDDLE_MCP = 9; static MIDDLE_PIP = 10; static MIDDLE_DIP = 11; static MIDDLE_TIP = 12;
  static RING_MCP = 13; static RING_PIP = 14; static RING_DIP = 15; static RING_TIP = 16;
  static PINKY_MCP = 17; static PINKY_PIP = 18; static PINKY_DIP = 19; static PINKY_TIP = 20;

  constructor(bufferSize = 4) {
    this.bufferSize = bufferSize;
    this.history = [];
    this.currentGesture = "NO HAND";
  }

  _getDistance(ptA, ptB) {
    const dx = ptA.x - ptB.x;
    const dy = ptA.y - ptB.y;
    const dz = (ptA.z !== undefined && ptB.z !== undefined) ? (ptA.z - ptB.z) : 0;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  }

  _getPalmCenterAndScale(landmarks) {
    const wrist = landmarks[BrowserGestureDetector.WRIST];
    const idxMcp = landmarks[BrowserGestureDetector.INDEX_MCP];
    const midMcp = landmarks[BrowserGestureDetector.MIDDLE_MCP];
    const rngMcp = landmarks[BrowserGestureDetector.RING_MCP];
    const pnkMcp = landmarks[BrowserGestureDetector.PINKY_MCP];

    const cx = (wrist.x + idxMcp.x + midMcp.x + rngMcp.x + pnkMcp.x) / 5.0;
    const cy = (wrist.y + idxMcp.y + midMcp.y + rngMcp.y + pnkMcp.y) / 5.0;
    const cz = (wrist.z !== undefined) ? (wrist.z + idxMcp.z + midMcp.z + rngMcp.z + pnkMcp.z) / 5.0 : 0;

    const palmCenter = { x: cx, y: cy, z: cz };
    const handSize = this._getDistance(wrist, midMcp);

    return { palmCenter, handSize: Math.max(1e-4, handSize) };
  }

  _evaluateFingerPalmRelative(landmarks, palmCenter, handSize, tipIdx, pipIdx) {
    const tip = landmarks[tipIdx];
    const pip = landmarks[pipIdx];

    const tipDist = this._getDistance(tip, palmCenter);
    const pipDist = this._getDistance(pip, palmCenter);

    const tipRatio = tipDist / handSize;
    const pipRatio = pipDist / handSize;
    const extensionRatio = tipDist / Math.max(1e-4, pipDist);

    let isExtended = false;
    if (tipIdx === BrowserGestureDetector.INDEX_TIP) {
      isExtended = (tipRatio > pipRatio * 1.05) && (extensionRatio >= 1.10);
    } else if (tipIdx === BrowserGestureDetector.PINKY_TIP) {
      isExtended = (tipRatio > pipRatio * 1.10) && (extensionRatio >= 1.12);
    } else { // Middle & Ring
      isExtended = (tipRatio > pipRatio * 1.12) && (extensionRatio >= 1.15);
    }

    return { isExtended, tipRatio, pipRatio, extensionRatio };
  }

  evaluateAllFingers(landmarks) {
    if (!landmarks || landmarks.length < 21) return null;

    const { palmCenter, handSize } = this._getPalmCenterAndScale(landmarks);

    const indexEval = this._evaluateFingerPalmRelative(landmarks, palmCenter, handSize, BrowserGestureDetector.INDEX_TIP, BrowserGestureDetector.INDEX_PIP);
    const middleEval = this._evaluateFingerPalmRelative(landmarks, palmCenter, handSize, BrowserGestureDetector.MIDDLE_TIP, BrowserGestureDetector.MIDDLE_PIP);
    const ringEval = this._evaluateFingerPalmRelative(landmarks, palmCenter, handSize, BrowserGestureDetector.RING_TIP, BrowserGestureDetector.RING_PIP);
    const pinkyEval = this._evaluateFingerPalmRelative(landmarks, palmCenter, handSize, BrowserGestureDetector.PINKY_TIP, BrowserGestureDetector.PINKY_PIP);

    return {
      Index: indexEval,
      Middle: middleEval,
      Ring: ringEval,
      Pinky: pinkyEval,
      handSize
    };
  }

  detectRawGesture(landmarks) {
    const evalData = this.evaluateAllFingers(landmarks);
    if (!evalData) return "NO HAND";

    const idxExt = evalData.Index.isExtended;
    const midExt = evalData.Middle.isExtended;
    const rngExt = evalData.Ring.isExtended;
    const pnkExt = evalData.Pinky.isExtended;

    // 1. ERASER: All 4 fingers folded in (Closed Fist)
    const isFist = (!idxExt) && (!midExt) && (!rngExt) && (!pnkExt);
    if (isFist) return "ERASER";

    // 2. DRAW: Pointing Index Finger
    const idxTr = evalData.Index.tipRatio;
    const midTr = evalData.Middle.tipRatio;
    const rngTr = evalData.Ring.tipRatio;
    const pnkTr = evalData.Pinky.tipRatio;

    const midFoldDiff = idxTr - midTr;
    const rngFoldDiff = idxTr - rngTr;
    const pnkFoldDiff = idxTr - pnkTr;

    const strongSeparation = (midFoldDiff >= 0.18) && (rngFoldDiff >= 0.18) && (pnkFoldDiff >= 0.18);
    const allOtherFolded = (!midExt) && (!rngExt) && (!pnkExt);

    if (idxExt && (strongSeparation || allOtherFolded)) {
      return "DRAW";
    }

    // 3. HOVER / STOP: Open palm or neutral/ambiguous pose
    return "HOVER";
  }

  update(landmarks) {
    if (!landmarks || landmarks.length < 21) {
      this.history = [];
      this.currentGesture = "NO HAND";
      return {
        gesture: "NO HAND",
        fingerStates: { Index: "NONE", Middle: "NONE", Ring: "NONE", Pinky: "NONE" },
        isDrawing: false
      };
    }

    const evalData = this.evaluateAllFingers(landmarks);
    if (!evalData) {
      this.history = [];
      this.currentGesture = "NO HAND";
      return {
        gesture: "NO HAND",
        fingerStates: { Index: "NONE", Middle: "NONE", Ring: "NONE", Pinky: "NONE" },
        isDrawing: false
      };
    }

    const fingerStates = {
      Index: evalData.Index.isExtended ? "EXTENDED" : "FOLDED",
      Middle: evalData.Middle.isExtended ? "EXTENDED" : "FOLDED",
      Ring: evalData.Ring.isExtended ? "EXTENDED" : "FOLDED",
      Pinky: evalData.Pinky.isExtended ? "EXTENDED" : "FOLDED"
    };

    const raw = this.detectRawGesture(landmarks);
    this.history.push(raw);
    if (this.history.length > this.bufferSize) {
      this.history.shift();
    }

    // Temporal Hysteresis
    if (this.currentGesture === "DRAW") {
      const recent = this.history.slice(-3);
      const nonDrawCount = recent.filter(g => g !== "DRAW").length;
      if (nonDrawCount >= 3) {
        this.currentGesture = this._getMostCommon(this.history);
      }
    } else {
      const mostCommon = this._getMostCommon(this.history);
      const count = this.history.filter(g => g === mostCommon).length;
      if (count >= Math.floor(this.bufferSize / 2) + 1) {
        this.currentGesture = mostCommon;
      }
    }

    return {
      gesture: this.currentGesture,
      fingerStates,
      isDrawing: (this.currentGesture === "DRAW")
    };
  }

  _getMostCommon(arr) {
    if (arr.length === 0) return "NO HAND";
    const counts = {};
    let maxCount = 0;
    let mostCommon = arr[0];
    for (const item of arr) {
      counts[item] = (counts[item] || 0) + 1;
      if (counts[item] > maxCount) {
        maxCount = counts[item];
        mostCommon = item;
      }
    }
    return mostCommon;
  }
}
