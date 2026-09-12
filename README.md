# LIVE AIR WRITING AI 🖐️✨

> **Write Without Touch. Create Without Limits.**

**LIVE AIR WRITING AI** is a local-first Python desktop application that enables users to write in the air using hand tracking via webcam, rendering smooth digital handwriting on a futuristic, glassmorphic PySide6 virtual canvas with optional AI-powered handwriting recognition and text synthesis.

---

## 🌟 Key Features

- 🖐️ **Real-Time Air Writing**: Write naturally in front of your camera without touching physical screens or devices.
- 📐 **MediaPipe Hand Tracking**: Accurate 21 3D-landmark tracking with optional cybernetic neon skeleton visualization.
- 🎯 **Smart Gesture Engine**: Automatic gesture recognition (Pointing finger to draw, Peace V-sign to hover/stop, Fist to erase).
- ✏️ **Low-Latency Smoothing**: Exponential Moving Average (EMA) and spline interpolation eliminate hand tremors and jitter.
- 🎨 **Glassmorphism 3D-Inspired UI**: Premium dark futuristic workspace built with PySide6, glowing neon accents, and dimensional card controls.
- 🤖 **Optional OpenAI Integration**: Vision-powered handwriting recognition (`gpt-4o-mini` / `gpt-4o`), text cleanup, note summarization, and clipboard copying.
- 🔒 **100% Local-First & Private**: Core computer vision, drawing, canvas, and gestures run offline without any cloud server dependency or camera frame streaming.
- 💾 **Export & Canvas Control**: Vector stroke history, Undo/Redo stacks, dark/light/transparent canvas modes, and PNG export.

---

## 🛠️ Technology Stack

- **GUI Framework**: PySide6 (Qt for Python)
- **Computer Vision**: OpenCV (`cv2`)
- **Hand Tracking**: Google MediaPipe Hands
- **Mathematical Processing**: NumPy
- **AI Processing (Optional)**: OpenAI API (`openai`, `python-dotenv`)
- **Packaging**: PyInstaller

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.13)
- Windows / macOS / Linux with accessible webcam

### 2. Clone / Navigate to Directory
```bash
cd C:\Users\sahap\.gemini\antigravity\scratch\Live-Air-Writing-AI
```

### 3. Create Virtual Environment & Install Dependencies
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🎮 How to Run

Launch the application:
```powershell
.\venv\Scripts\python main.py
```

---

## 🤏 Gesture Controls Guide

| Gesture | Hand Pose | Action |
| :--- | :--- | :--- |
| **DRAW** | Index finger extended pointing up | Draws continuous digital strokes on canvas |
| **HOVER / STOP** | Index + Middle fingers extended (Peace V-Sign) | Pauses drawing; allows moving hand without creating lines |
| **ERASER** | Closed fist OR 3 fingers (Index+Middle+Ring) extended | Erases strokes under fingertip |
| **CLEAR** | Open Palm held flat | Clears or hovers over canvas |

*Note: All controls are also accessible directly via the floating GUI toolbar.*

---

## 🔑 OpenAI AI Configuration (Optional)

1. Copy `.env.example` to `.env`:
   ```powershell
   copy .env.example .env
   ```
2. Open `.env` and add your key:
   ```env
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```
3. Alternatively, click **⚙️ Settings** inside the app and enter your key in the **OpenAI API Key** field.

---

## 📦 Building Standalone Windows Executable

To package the application into a single standalone `.exe` using PyInstaller:

```powershell
.\venv\Scripts\pyinstaller --noconfirm --onedir --windowed --name "Live-Air-Writing-AI" main.py
```
The generated executable will be placed in `dist/Live-Air-Writing-AI/Live-Air-Writing-AI.exe`.

---

## ⚙️ Troubleshooting

- **Webcam Not Detected**: Open **Settings** -> **Select Webcam** to switch camera index (0, 1, etc.). Ensure no other application (Zoom, Teams, Skype) is locking the webcam.
- **Hand Tracking Lag**: Lower camera resolution to `640x480` in Settings or increase `Smoothing Level`.
- **OpenAI Error**: Ensure valid API key is set. Core air-writing works 100% offline without OpenAI.
