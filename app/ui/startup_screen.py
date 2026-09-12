"""Startup Screen Widget with Animated 3D/Futuristic Visuals."""
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont


class CyberHandVisualizer(QWidget):
    """Futuristic 3D/Cybernetic animated graphic related to hand tracking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 280)
        self.angle = 0.0
        
        # Animation timer (30 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_animate)
        self.timer.start(33)

    def _on_animate(self) -> None:
        self.angle += 0.04
        if self.angle > 2 * math.pi:
            self.angle -= 2 * math.pi
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        cx, cy = self.width() / 2.0, self.height() / 2.0
        radius = min(cx, cy) - 20

        # Draw concentric pulsing cybernetic rings
        pulse = math.sin(self.angle) * 8.0
        
        # Outer ring
        pen_outer = QPen(QColor(0, 240, 255, 120), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen_outer)
        painter.drawEllipse(cx - (radius + pulse), cy - (radius + pulse), (radius + pulse) * 2, (radius + pulse) * 2)

        # Middle rotating ring
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(math.degrees(self.angle * 0.5))
        pen_mid = QPen(QColor(168, 85, 247, 180), 2)
        painter.setPen(pen_mid)
        painter.drawRect(-radius * 0.6, -radius * 0.6, radius * 1.2, radius * 1.2)
        painter.restore()

        # Simulated 3D Hand Skeleton Nodes & Connections
        nodes = [
            (0, radius * 0.5),                    # Wrist
            (-radius * 0.4, 0),                    # Thumb tip
            (-radius * 0.15, -radius * 0.65),     # Index tip
            (0.1 * radius, -radius * 0.75),       # Middle tip
            (0.35 * radius, -radius * 0.6),       # Ring tip
            (0.55 * radius, -radius * 0.35)       # Pinky tip
        ]

        # Apply slight 3D rotation wobble
        wobble_x = math.cos(self.angle) * 15.0
        wobble_y = math.sin(self.angle * 1.5) * 15.0

        transformed_nodes = []
        for nx, ny in nodes:
            tx = cx + nx + wobble_x
            ty = cy + ny + wobble_y
            transformed_nodes.append((tx, ty))

        wrist = transformed_nodes[0]
        pen_line = QPen(QColor(0, 240, 255, 200), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen_line)

        for tip in transformed_nodes[1:]:
            painter.drawLine(wrist[0], wrist[1], tip[0], tip[1])

        # Draw glowing joint points
        for i, (tx, ty) in enumerate(transformed_nodes):
            if i == 2:  # Index Tip Highlight
                painter.setBrush(QBrush(QColor(0, 240, 255)))
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawEllipse(tx - 10, ty - 10, 20, 20)
            else:
                painter.setBrush(QBrush(QColor(168, 85, 247)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(tx - 6, ty - 6, 12, 12)

        painter.end()


class StartupScreen(QWidget):
    """Polished Startup / Splash Screen."""

    start_requested = Signal()
    settings_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(40, 40, 40, 40)

        # Glassmorphic Dimensional Card Container
        card = QFrame()
        card.setObjectName("glass-card")
        card.setProperty("class", "glass-card")
        card.setStyleSheet("""
            QFrame#glass-card {
                background-color: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(0, 240, 255, 0.25);
                border-radius: 24px;
            }
        """)

        # Add elevation shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 240, 255, 40))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(48, 48, 48, 48)
        card_layout.setSpacing(24)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Header Title
        title = QLabel("LIVE AIR WRITING AI")
        title.setProperty("class", "title-primary")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 36px;
            font-weight: 900;
            color: #00F0FF;
            letter-spacing: 2px;
        """)

        # Subtitle
        subtitle = QLabel("Write Without Touch. Create Without Limits.")
        subtitle.setProperty("class", "title-sub")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 16px;
            color: #94A3B8;
            font-weight: 500;
        """)

        # Animated Cyber Graphic
        self.visualizer = CyberHandVisualizer()

        # Action Buttons Layout
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(14)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_start = QPushButton("🚀 START WRITING")
        btn_start.setProperty("class", "btn-primary")
        btn_start.setMinimumWidth(260)
        btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_start.clicked.connect(self.start_requested.emit)

        btn_settings = QPushButton("⚙️ SETTINGS")
        btn_settings.setMinimumWidth(260)
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.clicked.connect(self.settings_requested.emit)

        btn_exit = QPushButton("❌ EXIT")
        btn_exit.setMinimumWidth(260)
        btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exit.clicked.connect(self.exit_requested.emit)

        btn_layout.addWidget(btn_start)
        btn_layout.addWidget(btn_settings)
        btn_layout.addWidget(btn_exit)

        # Assembly
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(self.visualizer, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addSpacing(10)
        card_layout.addLayout(btn_layout)

        main_layout.addWidget(card)
