import os
import sys
import time
import math
import shutil
import urllib.parse
import subprocess
import traceback
from datetime import datetime, timezone, timedelta
import keyboard
import numpy as np
import pyaudiowpatch as pyaudio

# Indian Standard Time (IST) is UTC+5:30
IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30))

def get_current_ist_time() -> str:
    """Returns the current Indian Standard Time (IST) in HH:MM format."""
    return datetime.now(IST_TIMEZONE).strftime("%H:%M")

# --- Local User Storage Configuration ---
def get_user_data_filepath() -> str:
    """
    Dynamically generates the user-specific storage file path.
    Prioritizes user-specific directories:
    1. User's home directory (e.g. ~/.venom_notch_user.txt)
    2. Windows %APPDATA% directory fallback
    This ensures that each user who runs the application/executable has their
    username stored strictly in their own local file on their own PC, keeping
    user data completely decentralized and private.
    """
    home_dir = os.path.expanduser("~")
    primary_path = os.path.join(home_dir, ".venom_notch_user.txt")
    if os.path.exists(primary_path):
        return primary_path

    appdata = os.environ.get("APPDATA")
    if appdata:
        appdata_file = os.path.join(appdata, "VenomNotch", "user_data.txt")
        if os.path.exists(appdata_file):
            return appdata_file
        appdata_dot = os.path.join(appdata, ".venom_notch_user.txt")
        if os.path.exists(appdata_dot):
            return appdata_dot

    return primary_path


USER_DATA_FILE = get_user_data_filepath()


def get_stored_username() -> str | None:
    """
    Reads username from the local user-specific storage file if it exists and contains non-empty text
    (clamped to max 15 chars). Also checks backward-compatible legacy project paths for one-time migration.
    """
    # Candidate paths to inspect for username:
    candidate_paths = [
        USER_DATA_FILE,
        os.path.join(os.path.expanduser("~"), ".venom_notch_user.txt"),
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidate_paths.append(os.path.join(appdata, "VenomNotch", "user_data.txt"))
        candidate_paths.append(os.path.join(appdata, ".venom_notch_user.txt"))

    # Legacy static project repository path (checked for one-time backward-compatibility migration)
    legacy_repo_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data.txt")
    candidate_paths.append(legacy_repo_file)

    for path in candidate_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        name = line.strip()
                        if name:
                            clean_name = name[:15]
                            # If read from legacy repo file, migrate it to the user-specific file
                            if path == legacy_repo_file and path != USER_DATA_FILE:
                                save_username(clean_name)
                            return clean_name
            except Exception as e:
                print(f"[ERROR] Failed reading {path}: {e}")
    return None


def save_username(username: str):
    """
    Saves username into the local user-specific file on the user's PC,
    ensuring decentralized, private user storage.
    """
    try:
        parent_dir = os.path.dirname(USER_DATA_FILE)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            f.write(username.strip() + "\n")
        print(f"[INFO] Username '{username.strip()}' saved to local user storage: {USER_DATA_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed saving username to {USER_DATA_FILE}: {e}")

from PyQt6.QtCore import (
    Qt,
    QSize,
    QRectF,
    QObject,
    QPoint,
    QPointF,
    pyqtSignal,
    pyqtProperty,
    QPropertyAnimation,
    QEasingCurve,
    QThread,
    QTimer
)
from PyQt6.QtGui import (
    QPainter,
    QPainterPath,
    QColor,
    QPen,
    QBrush,
    QFont,
    QLinearGradient,
    QRadialGradient,
    QShortcut,
    QKeySequence
)
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QPushButton,
    QLineEdit,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QMenu,
    QDialog,
    QLabel,
    QSlider,
    QSpinBox,
    QComboBox,
    QMessageBox,
    QCheckBox
)

# --- Configuration Constants ---
DEFAULT_COLLAPSED_WIDTH = 230  # Strict default width for collapsed notch
DEFAULT_COLLAPSED_HEIGHT = 40  # Strict default height for collapsed notch
VOLUME_THRESHOLD = 0.015       # RMS threshold to detect media playback (low threshold)
SILENCE_TIMEOUT = 3.0          # Seconds of continuous silence before auto-collapse
NUM_BARS = 24                  # Number of visualizer frequency bars
CHUNK_SIZE = 1024              # Audio buffer chunk size
DECAY_RATE = 0.82              # Visualizer fall-off / decay smoothing factor

# --- Synced Cinematic Intro Timing Constants ---
WELCOME_DURATION = 1.5         # Seconds welcome text remains in focus (Phase A)
SHATTER_DURATION = 0.6         # Seconds for welcome text to fracture and slide apart (Phase B)
SYMBIOTE_START = 2.0           # Seconds when border tendrils ignite and crawl (Phase C)
SYMBIOTE_DURATION = 1.8        # Seconds for symbiote border crawl, retract, swirl and form notch
TOTAL_INTRO_DURATION = SYMBIOTE_START + SYMBIOTE_DURATION  # 3.8s total cinematic sequence


def get_browser_executable(browser_choice: str) -> tuple[str | None, str, bool]:
    """
    Resolves the browser executable path, canonical browser name, and incognito flag.
    Supported browsers: Brave, Edge, Chrome.
    Returns:
        (exe_path, browser_name, is_incognito)
        - exe_path: Full path to the executable if found on the Windows system, or None if missing.
                    (Edge is native to Windows 11, so it falls back to msedge.exe if full path isn't resolved).
        - browser_name: 'Brave', 'Edge', or 'Chrome'
        - is_incognito: True if incognito/private mode was selected.
    """
    choice = (browser_choice or "").strip()
    is_incognito = "(Incognito)" in choice

    if choice.startswith("Brave"):
        browser_name = "Brave"
        exe_candidates = ["brave.exe", "brave"]
        paths = [
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
    elif choice.startswith("Chrome"):
        browser_name = "Chrome"
        exe_candidates = ["chrome.exe", "chrome"]
        paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
    else:
        browser_name = "Edge"
        exe_candidates = ["msedge.exe", "msedge"]
        paths = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        ]

    # 1. Check known default filesystem installation paths
    for p in paths:
        if p and os.path.isfile(p):
            return (p, browser_name, is_incognito)

    # 2. Check PATH environment variable via shutil.which
    for cand in exe_candidates:
        w = shutil.which(cand)
        if w and os.path.isfile(w):
            return (w, browser_name, is_incognito)

    # 3. Check Windows App Paths in Registry (HKLM and HKCU)
    try:
        import winreg
        for cand in exe_candidates:
            cand_exe = cand if cand.endswith(".exe") else cand + ".exe"
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{cand_exe}") as key:
                        val, _ = winreg.QueryValueEx(key, "")
                        if val and os.path.isfile(val):
                            return (val, browser_name, is_incognito)
                except Exception:
                    pass
    except Exception:
        pass

    # 4. Fallback for native Microsoft Edge on Windows 11
    if browser_name == "Edge":
        return ("msedge.exe", browser_name, is_incognito)

    # Browser not installed
    return (None, browser_name, is_incognito)


def open_or_focus_ai(ai_name: str, url: str, is_incognito: bool = False, browser: str = "Edge"):
    """
    Robust window-switching function using a PowerShell command with Win32 API (user32.dll via C# Add-Type):
    When an AI icon (Gemini, ChatGPT, Claude) is clicked:
    1. Searches open desktop windows for a title containing the specific AI name ('Gemini', 'ChatGPT', or 'Claude').
    2. If a matching window is already open (e.g., an existing Microsoft Edge window), uses SetForegroundWindow
       and ShowWindowAsync to bring that exact window to the front and focus it, preventing redundant tabs from opening.
    3. If no matching Edge window is open, launches a fresh tab specifically using Microsoft Edge
       (msedge.exe or start msedge <url>), completely removing any dependency on other browsers for the AI buttons.
    4. Respects normal/incognito mode from the search dropdown (launching with -inprivate when an incognito profile is active).
    """
    if isinstance(is_incognito, str):
        incog_flag = "(Incognito)" in is_incognito
    else:
        incog_flag = bool(is_incognito) or ("(Incognito)" in str(browser))

    # Resolve Microsoft Edge executable path
    edge_exe, _, _ = get_browser_executable("Edge")
    target_exe = edge_exe if edge_exe else "msedge.exe"
    launch_args = f"-inprivate {url}" if incog_flag else url
    fallback_cmd = f'start msedge -inprivate "{url}"' if incog_flag else f'start msedge "{url}"'

    target_exe_ps = target_exe.replace('"', '`"')
    launch_args_ps = launch_args.replace('"', '`"')

    ps_code = f"""
$csharp = @'
using System;
using System.Text;
using System.Runtime.InteropServices;

public class Win32Focus {{
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    public static extern int GetWindowTextLength(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool BringWindowToTop(IntPtr hWnd);

    public static IntPtr FindWindowByTitle(string substring) {{
        IntPtr result = IntPtr.Zero;
        EnumWindows((hWnd, lParam) => {{
            if (!IsWindowVisible(hWnd)) return true;
            int length = GetWindowTextLength(hWnd);
            if (length == 0) return true;
            StringBuilder sb = new StringBuilder(length + 1);
            GetWindowText(hWnd, sb, sb.Capacity);
            string title = sb.ToString();
            if (title.IndexOf(substring, StringComparison.OrdinalIgnoreCase) >= 0) {{
                result = hWnd;
                return false;
            }}
            return true;
        }}, IntPtr.Zero);
        return result;
    }}

    public static bool FocusWindow(IntPtr hWnd) {{
        ShowWindowAsync(hWnd, 9); // SW_RESTORE
        BringWindowToTop(hWnd);
        return SetForegroundWindow(hWnd);
    }}
}}
'@

try {{
    Add-Type -TypeDefinition $csharp -ErrorAction Stop
}} catch {{
}}

$hWnd = [Win32Focus]::FindWindowByTitle("{ai_name}")
if ($hWnd -ne [IntPtr]::Zero) {{
    [Win32Focus]::FocusWindow($hWnd)
    Write-Output "SUCCESS: Found and focused existing Edge window for {ai_name}"
}} else {{
    Write-Output "INFO: No open Edge window found for {ai_name}. Opening fresh tab in Microsoft Edge (incognito={incog_flag})..."
    try {{
        Start-Process "{target_exe_ps}" -ArgumentList "{launch_args_ps}"
    }} catch {{
        {fallback_cmd}
    }}
}}
"""
    try:
        print(f"[AI LAUNCH] Searching open windows for '{ai_name}' (target: Microsoft Edge, inprivate={incog_flag})...")
        proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", ps_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        def _check_result():
            try:
                res = proc.communicate(timeout=6)
                if isinstance(res, tuple) and len(res) == 2:
                    stdout, stderr = res
                    if stdout:
                        print(f"[AI LAUNCH] {stdout.strip()}")
                    if stderr:
                        print(f"[ERROR] PowerShell stderr: {stderr.strip()}")
            except subprocess.TimeoutExpired:
                print(f"[WARNING] PowerShell launch query timed out.")
            except Exception as ex:
                print(f"[ERROR] Failed reading launch output: {ex}")

        import threading
        threading.Thread(target=_check_result, daemon=True).start()

    except Exception as e:
        print(f"[ERROR] Failed to execute open_or_focus_ai for '{ai_name}': {e}")
        traceback.print_exc()


class CircularAIButton(QWidget):
    """
    Circular Edge-detecting icon label component:
    Displays a circular badge with glowing brand accent, icon symbol, and name label.
    """
    clicked = pyqtSignal()

    def __init__(self, name: str, icon_symbol: str, accent_color: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.icon_symbol = icon_symbol
        self.accent_color = accent_color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(58, 54)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.button = QPushButton(icon_symbol, self)
        self.button.setFixedSize(34, 34)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1.5px solid rgba(255, 255, 255, 0.16);
                border-radius: 17px;
                color: #FFFFFF;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.18);
                border: 1.5px solid {accent_color};
            }}
            QPushButton:focus {{
                background-color: rgba(0, 255, 255, 0.25);
                border: 2px solid cyan;
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.28);
            }}
        """)
        self.button.clicked.connect(self.clicked.emit)

        self.label = QLabel(name, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                font-family: 'Segoe UI', sans-serif;
                font-size: 9px;
                font-weight: 600;
                background: transparent;
            }
        """)

        layout.addWidget(self.button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class AudioCaptureThread(QThread):
    """
    Dedicated non-blocking audio capture QThread:
    Uses non-blocking PyAudio stream callbacks and isolates device querying and
    chunk processing entirely inside the thread so the PyQt main event loop NEVER blocks.
    """
    audio_data_ready = pyqtSignal(float, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.num_bars = NUM_BARS
        self.chunk_size = CHUNK_SIZE
        self.latest_data = None
        self.has_new_data = False
        self.last_audio_timestamp = 0.0

    def _compute_frequency_bars(self, samples: np.ndarray) -> np.ndarray:
        if len(samples) < 128:
            return np.zeros(self.num_bars, dtype=np.float32)

        windowed = samples * np.hanning(len(samples))
        fft = np.abs(np.fft.rfft(windowed))
        fft[0] = 0.0

        bars = []
        n_fft = len(fft)
        for i in range(self.num_bars):
            start = int(n_fft * ((i / self.num_bars) ** 2.2))
            end = max(start + 1, int(n_fft * (((i + 1) / self.num_bars) ** 2.2)))
            band_mean = float(np.mean(fft[start:end]))
            treble_boost = 1.0 + (i / self.num_bars) * 3.0
            scaled = np.log1p(band_mean * treble_boost * 9.0) / 3.2
            bars.append(min(1.0, max(0.0, float(scaled))))

        return np.array(bars, dtype=np.float32)

    def run(self):
        """Runs completely in background. Main thread never waits on audio stream."""
        p = None
        stream = None
        try:
            p = pyaudio.PyAudio()

            device = None
            try:
                device = p.get_default_wasapi_loopback()
            except Exception as dev_err:
                print(f"[WARNING] get_default_wasapi_loopback fallback: {dev_err}")
                for loopback in p.get_loopback_device_info_generator():
                    device = loopback
                    break

            if not device:
                print("[ERROR] No WASAPI loopback device found.")
                return

            device_index = int(device["index"])
            channels = int(device["maxInputChannels"])
            rate = int(device["defaultSampleRate"])

            print(f"[AUDIO] Non-blocking loopback stream initialized: {device['name']} @ {rate}Hz ({channels} ch)")

            # Non-blocking C-level callback mode to ensure GIL is never blocked
            def _audio_callback(in_data, frame_count, time_info, status):
                if in_data:
                    self.latest_data = in_data
                    self.has_new_data = True
                return (None, pyaudio.paContinue)

            stream = p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=_audio_callback
            )
            stream.start_stream()

            while self.running:
                if self.has_new_data and self.latest_data:
                    self.has_new_data = False
                    raw_bytes = self.latest_data
                    samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                    if channels > 1:
                        samples = samples.reshape(-1, channels).mean(axis=1)

                    rms = float(np.sqrt(np.mean(samples ** 2)))
                    bars = self._compute_frequency_bars(samples)
                    self.audio_data_ready.emit(rms, bars.tolist())
                    self.last_audio_timestamp = time.time()
                else:
                    # If no audio packets received for > 70ms, report silence
                    if time.time() - self.last_audio_timestamp > 0.07:
                        self.audio_data_ready.emit(0.0, [0.0] * self.num_bars)

                time.sleep(0.025)

        except Exception as e:
            print(f"[ERROR] Audio capture thread error: {e}")
            traceback.print_exc()
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass
            print("[AUDIO] Audio capture thread terminated cleanly.")

    def stop(self):
        self.running = False


class HotkeyBridge(QObject):
    toggle_requested = pyqtSignal()
    force_close_requested = pyqtSignal()
    up_arrow_requested = pyqtSignal()
    down_arrow_requested = pyqtSignal()
    left_arrow_requested = pyqtSignal()
    right_arrow_requested = pyqtSignal()


class AudioVisualizerWidget(QWidget):
    """
    Dedicated transparent child canvas that renders ONLY the audio wave / bars / pulse dots / matrix rain,
    leaving the QFrame background to be drawn reliably by Qt style sheets.
    """
    def __init__(self, pill_widget, parent=None):
        super().__init__(parent)
        self.pill_widget = pill_widget
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(66)
        self.matrix_drops = [float((i * 11) % 66) for i in range(32)]
        self.matrix_chars = ["0", "1", "A", "Z", "8", "9", "X", "$", "#", "%", "Ø", "§", "Ψ", "Δ"]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        num_bars = len(self.pill_widget.rendered_bars)
        if num_bars == 0:
            return

        alpha = 240
        style = self.pill_widget.visualizer_style

        if style in ("Waveform", "Wave"):
            wave_path = QPainterPath()
            wave_path.moveTo(0.0, h)
            pts = []
            for i in range(num_bars):
                val = float(self.pill_widget.rendered_bars[i])
                bx = i * (w / (num_bars - 1))
                by = h - max(4.0, val * (h - 6.0))
                pts.append((bx, by))

            for bx, by in pts:
                wave_path.lineTo(bx, by)

            wave_path.lineTo(w, h)
            wave_path.closeSubpath()

            wave_fill = QLinearGradient(0, 0, 0, h)
            wave_fill.setColorAt(0.0, QColor(0, 255, 255, int(alpha * 0.45)))
            wave_fill.setColorAt(0.5, QColor(220, 38, 38, int(alpha * 0.35)))
            wave_fill.setColorAt(1.0, QColor(6, 6, 10, int(alpha * 0.05)))
            painter.setBrush(QBrush(wave_fill))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(wave_path)

            line_path = QPainterPath()
            line_path.moveTo(pts[0][0], pts[0][1])
            for bx, by in pts[1:]:
                line_path.lineTo(bx, by)

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(0, 255, 255, alpha), 2.2))
            painter.drawPath(line_path)

        elif style in ("Frequency Bars", "Bars"):
            gap = 5.0
            bar_w = max(3.0, (w - (num_bars - 1) * gap) / num_bars)
            for i in range(num_bars):
                val = float(self.pill_widget.rendered_bars[i])
                bh = max(3.0, val * h)
                bx = i * (bar_w + gap)
                by = h - bh

                bar_gradient = QLinearGradient(bx, 0, bx, h)
                bar_gradient.setColorAt(0.0, QColor(0, 255, 255, alpha))
                bar_gradient.setColorAt(0.5, QColor(220, 38, 38, alpha))
                bar_gradient.setColorAt(1.0, QColor(10, 10, 14, alpha))

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(bar_gradient))
                painter.drawRoundedRect(QRectF(bx, by, bar_w, bh), 2.5, 2.5)

        elif style in ("Circular Pulse", "Pulse Dots"):
            num_dots = 14
            dot_spacing = w / (num_dots - 1)
            center_y = h / 2.0
            for i in range(num_dots):
                bar_idx = min(num_bars - 1, int(i * (num_bars / num_dots)))
                val = float(self.pill_widget.rendered_bars[bar_idx])
                cx = i * dot_spacing
                r = 3.5 + val * 16.0

                glow = QColor(0, 255, 255, int(alpha * 0.4)) if i % 2 == 0 else QColor(220, 38, 38, int(alpha * 0.4))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow)
                painter.drawEllipse(QPointF(cx, center_y), r, r)

                painter.setBrush(QColor(255, 255, 255, alpha))
                painter.drawEllipse(QPointF(cx, center_y), 3.0, 3.0)

        elif style in ("Matrix Rain", "Matrix"):
            num_cols = 24
            col_w = w / num_cols
            font = QFont("Consolas", 8, QFont.Weight.Bold)
            painter.setFont(font)
            rms = float(self.pill_widget.current_rms)

            for c in range(num_cols):
                bar_idx = min(num_bars - 1, int(c * (num_bars / num_cols)))
                bar_val = float(self.pill_widget.rendered_bars[bar_idx])

                speed = 1.0 + rms * 16.0 + bar_val * 6.0
                if c < len(self.matrix_drops):
                    self.matrix_drops[c] = (self.matrix_drops[c] + speed) % max(1.0, h + 30.0)
                    lead_y = self.matrix_drops[c]
                else:
                    lead_y = h / 2.0

                cx = c * col_w + 2.0
                trail_len = 4 + int(bar_val * 4)
                for tr in range(trail_len):
                    char_y = lead_y - tr * 11.0
                    if 0 <= char_y <= h:
                        ch = self.matrix_chars[(c * 3 + tr + int(lead_y // 10)) % len(self.matrix_chars)]
                        if tr == 0:
                            painter.setPen(QColor(240, 255, 255, 250))
                        elif tr == 1:
                            painter.setPen(QColor(0, 255, 255, 210))
                        elif tr == 2:
                            painter.setPen(QColor(0, 230, 160, 160) if c % 2 == 0 else QColor(220, 38, 38, 160))
                        else:
                            painter.setPen(QColor(0, 160, 120, 75))
                        painter.drawText(QPointF(cx, char_y), ch)

        # Highlight when focused via keyboard Down Arrow controls
        if self.hasFocus():
            focus_pen = QPen(QColor(0, 255, 255, 200), 1.5)
            focus_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(focus_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(1, 1, int(w - 2), int(h - 2), 6, 6)


class MiniVisualizerWidget(QWidget):
    """Mini 4-bar dancing indicator for the collapsed notch."""
    def __init__(self, pill_widget, parent=None):
        super().__init__(parent)
        self.pill_widget = pill_widget
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(26, 16)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        bar_w = 2.5
        gap = 2.0
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(4):
            val = self.pill_widget.rendered_bars[i * 5] if len(self.pill_widget.rendered_bars) > i * 5 else 0.1
            bh = max(3.0, val * h)
            bx = i * (bar_w + gap)
            by = (h - bh) / 2.0
            color = QColor(0, 255, 255, 230) if self.pill_widget.is_playing else QColor(130, 135, 145, 180)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(bx, by, bar_w, bh), 1.2, 1.2)


class SettingsDialog(QDialog):
    """
    Dedicated UI Settings popup dialog with QFormLayout for real-time notch adjustments:
    - User Profile & Username management (Change Username)
    - RGB Breathing / Neon Border effect toggle
    - Base Width & Height dimensions
    - Top Y offset positioning
    - Audio Visualizer style selector
    """
    def __init__(self, main_window: "NotchMainWindow", parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle("UI Settings")
        self.setFixedWidth(410)

        self.setStyleSheet("""
            QDialog {
                background-color: #141418;
                color: #F3F4F6;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #D1D5DB;
                font-size: 11px;
                font-weight: 500;
            }
            QSpinBox {
                background-color: #22222A;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 11px;
                padding: 4px 8px;
                min-width: 65px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #282832;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: cyan;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
            QComboBox {
                background-color: #22222A;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 11px;
                padding: 5px 10px;
                min-width: 140px;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1A22;
                border: 1px solid cyan;
                color: #FFFFFF;
                selection-background-color: cyan;
                selection-color: black;
                padding: 4px;
            }
            QPushButton {
                background-color: cyan;
                color: #000000;
                border: none;
                border-radius: 8px;
                font-size: 11px;
                font-weight: 700;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #00cccc;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(18)

        header = QLabel("⚙️  UI Settings")
        header.setStyleSheet("font-size: 15px; font-weight: 600; color: #FFFFFF;")
        layout.addWidget(header)

        form_layout = QFormLayout()
        form_layout.setSpacing(14)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        # 1. User Profile & Username Row
        user_container = QWidget()
        u_box = QHBoxLayout(user_container)
        u_box.setContentsMargins(0, 0, 0, 0)
        u_box.setSpacing(10)

        self.user_display = QLabel((self.main_window.username or "Host")[:15])
        self.user_display.setStyleSheet("""
            color: #FFFFFF;
            font-family: 'Segoe UI', sans-serif;
            font-size: 12px;
            font-weight: 700;
        """)
        u_box.addWidget(self.user_display)

        self.btn_change_username = QPushButton("Change Username")
        self.btn_change_username.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_change_username.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 255, 255, 0.15);
                color: cyan;
                border: 1.5px solid cyan;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 0.35);
                color: #FFFFFF;
            }
        """)
        self.btn_change_username.clicked.connect(self._on_change_username_clicked)
        u_box.addWidget(self.btn_change_username)
        u_box.addStretch()
        form_layout.addRow("Username:", user_container)

        # 2. RGB Breathing / Neon Border Effect Toggle
        rgb_container = QWidget()
        rgb_box = QHBoxLayout(rgb_container)
        rgb_box.setContentsMargins(0, 0, 0, 0)
        rgb_box.setSpacing(10)

        rgb_on = self.main_window.pill_widget.rgb_border_enabled
        self.rgb_toggle_btn = QPushButton("Toggle RGB Border: ON" if rgb_on else "Toggle RGB Border: OFF")
        self.rgb_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rgb_toggle_btn.setFixedHeight(28)
        self._update_rgb_btn_style(rgb_on)
        self.rgb_toggle_btn.clicked.connect(self._on_toggle_rgb_clicked)
        rgb_box.addWidget(self.rgb_toggle_btn)

        self.rgb_checkbox = QCheckBox("Breathing / Neon")
        self.rgb_checkbox.setChecked(rgb_on)
        self.rgb_checkbox.toggled.connect(self._on_rgb_checkbox_toggled)
        self.rgb_checkbox.setStyleSheet("""
            QCheckBox {
                color: #EDEDED;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 500;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border-radius: 4px;
                border: 1.5px solid cyan;
                background-color: rgba(22, 22, 30, 0.9);
            }
            QCheckBox::indicator:checked {
                background-color: cyan;
            }
        """)
        rgb_box.addWidget(self.rgb_checkbox)
        rgb_box.addStretch()
        form_layout.addRow("RGB Border:", rgb_container)

        # 3. Base Width Slider & SpinBox
        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setRange(DEFAULT_COLLAPSED_WIDTH, 420)
        self.width_slider.setValue(max(DEFAULT_COLLAPSED_WIDTH, self.main_window.base_width))

        self.width_spin = QSpinBox()
        self.width_spin.setRange(DEFAULT_COLLAPSED_WIDTH, 420)
        self.width_spin.setValue(max(DEFAULT_COLLAPSED_WIDTH, self.main_window.base_width))
        self.width_spin.setSuffix(" px")

        width_container = QWidget()
        w_box = QHBoxLayout(width_container)
        w_box.setContentsMargins(0, 0, 0, 0)
        w_box.setSpacing(8)
        w_box.addWidget(self.width_slider)
        w_box.addWidget(self.width_spin)
        form_layout.addRow("Base Width:", width_container)

        # 4. Base Height Slider & SpinBox
        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(DEFAULT_COLLAPSED_HEIGHT, 70)
        self.height_slider.setValue(max(DEFAULT_COLLAPSED_HEIGHT, self.main_window.base_height))

        self.height_spin = QSpinBox()
        self.height_spin.setRange(DEFAULT_COLLAPSED_HEIGHT, 70)
        self.height_spin.setValue(max(DEFAULT_COLLAPSED_HEIGHT, self.main_window.base_height))
        self.height_spin.setSuffix(" px")

        height_container = QWidget()
        h_box = QHBoxLayout(height_container)
        h_box.setContentsMargins(0, 0, 0, 0)
        h_box.setSpacing(8)
        h_box.addWidget(self.height_slider)
        h_box.addWidget(self.height_spin)
        form_layout.addRow("Base Height:", height_container)

        # 5. Y-Axis Position Slider & SpinBox
        self.y_slider = QSlider(Qt.Orientation.Horizontal)
        self.y_slider.setRange(0, 150)
        self.y_slider.setValue(self.main_window.top_offset)

        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 150)
        self.y_spin.setValue(self.main_window.top_offset)
        self.y_spin.setSuffix(" px")

        y_container = QWidget()
        y_box = QHBoxLayout(y_container)
        y_box.setContentsMargins(0, 0, 0, 0)
        y_box.setSpacing(8)
        y_box.addWidget(self.y_slider)
        y_box.addWidget(self.y_spin)
        form_layout.addRow("Y Position:", y_container)

        # 6. Audio Visualizer Style ComboBox
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Waveform", "Frequency Bars", "Circular Pulse", "Matrix Rain"])
        cur_style = self.main_window.pill_widget.visualizer_style
        if cur_style == "Wave": cur_style = "Waveform"
        elif cur_style == "Bars": cur_style = "Frequency Bars"
        elif cur_style == "Pulse Dots": cur_style = "Circular Pulse"
        self.style_combo.setCurrentText(cur_style)
        form_layout.addRow("Visualizer Style:", self.style_combo)

        layout.addLayout(form_layout)

        btn_close = QPushButton("Done")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        self.width_slider.valueChanged.connect(self.width_spin.setValue)
        self.width_spin.valueChanged.connect(self.width_slider.setValue)
        self.width_slider.valueChanged.connect(self.main_window.update_base_width)

        self.height_slider.valueChanged.connect(self.height_spin.setValue)
        self.height_spin.valueChanged.connect(self.height_slider.setValue)
        self.height_slider.valueChanged.connect(self.main_window.update_base_height)

        self.y_slider.valueChanged.connect(self.y_spin.setValue)
        self.y_spin.valueChanged.connect(self.y_slider.setValue)
        self.y_slider.valueChanged.connect(self.main_window.update_top_offset)

        self.style_combo.currentTextChanged.connect(self.main_window.update_visualizer_style)

    def _update_rgb_btn_style(self, rgb_on: bool):
        if rgb_on:
            self.rgb_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 255, 255, 0.2);
                    color: cyan;
                    border: 1.5px solid cyan;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 4px 14px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 255, 255, 0.35);
                }
            """)
        else:
            self.rgb_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #A0AEC0;
                    border: 1.5px solid rgba(255, 255, 255, 0.18);
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 4px 14px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.14);
                    color: #FFFFFF;
                }
            """)

    def _on_toggle_rgb_clicked(self):
        self.main_window.pill_widget.toggle_rgb_border()
        rgb_on = self.main_window.pill_widget.rgb_border_enabled
        self.rgb_toggle_btn.setText("Toggle RGB Border: ON" if rgb_on else "Toggle RGB Border: OFF")
        self._update_rgb_btn_style(rgb_on)
        self.rgb_checkbox.blockSignals(True)
        self.rgb_checkbox.setChecked(rgb_on)
        self.rgb_checkbox.blockSignals(False)

    def _on_rgb_checkbox_toggled(self, checked):
        if checked != self.main_window.pill_widget.rgb_border_enabled:
            self.main_window.pill_widget.toggle_rgb_border()
        rgb_on = self.main_window.pill_widget.rgb_border_enabled
        self.rgb_toggle_btn.setText("Toggle RGB Border: ON" if rgb_on else "Toggle RGB Border: OFF")
        self._update_rgb_btn_style(rgb_on)

    def _on_change_username_clicked(self):
        current_name = getattr(self.main_window, "username", "") or "Host"
        dlg = UsernameDialog(
            parent=self,
            title="Change Username",
            subtitle="Enter a new username for your Symbiote desktop notch:",
            button_text="Update Username",
            current_username=current_name,
            allow_cancel=True
        )
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            dlg.move(geo.x() + (geo.width() - dlg.width()) // 2,
                     geo.y() + (geo.height() - dlg.height()) // 2)

        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.chosen_username:
            new_name = dlg.chosen_username.strip()[:15]
            if new_name:
                self.main_window.update_username(new_name)
                self.user_display.setText(new_name)

    def refresh_values(self):
        if hasattr(self, "user_display"):
            self.user_display.setText((self.main_window.username or "Host")[:15])
        rgb_on = self.main_window.pill_widget.rgb_border_enabled
        if hasattr(self, "rgb_toggle_btn"):
            self.rgb_toggle_btn.setText("Toggle RGB Border: ON" if rgb_on else "Toggle RGB Border: OFF")
            self._update_rgb_btn_style(rgb_on)
        if hasattr(self, "rgb_checkbox"):
            self.rgb_checkbox.blockSignals(True)
            self.rgb_checkbox.setChecked(rgb_on)
            self.rgb_checkbox.blockSignals(False)

    def closeEvent(self, event):
        self.main_window.settings_dialog = None
        super().closeEvent(event)


UISettingsDialog = SettingsDialog


class UsernameDialog(QDialog):
    """
    Sleek, dark-themed popup dialog for setting or changing the username.
    Enforces strict <= 15 characters validation.
    """
    def __init__(
        self,
        parent=None,
        title: str = "Set a username",
        subtitle: str = "Enter your name to synchronize your Symbiote desktop notch:",
        button_text: str = "Initialize Notch",
        current_username: str = "",
        allow_cancel: bool = False
    ):
        super().__init__(parent)
        self.allow_cancel = allow_cancel
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(380, 240)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.card = QFrame(self)
        self.card.setStyleSheet("""
            QFrame {
                background-color: rgba(18, 18, 26, 0.98);
                border: 2px solid cyan;
                border-radius: 16px;
            }
        """)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        icon_label = QLabel("⚡", self.card)
        icon_label.setStyleSheet("color: cyan; font-size: 18px; background: transparent; border: none;")
        header_layout.addWidget(icon_label)

        title_label = QLabel(title, self.card)
        title_label.setStyleSheet("""
            color: #FFFFFF;
            font-family: 'Segoe UI', sans-serif;
            font-size: 16px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        if allow_cancel:
            btn_close = QPushButton("✕", self.card)
            btn_close.setFixedSize(24, 24)
            btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_close.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #718096;
                    border: none;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    color: cyan;
                }
            """)
            btn_close.clicked.connect(self.reject)
            header_layout.addWidget(btn_close)

        card_layout.addLayout(header_layout)

        sub_label = QLabel(subtitle, self.card)
        sub_label.setWordWrap(True)
        sub_label.setStyleSheet("""
            color: #A0AEC0;
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
            background: transparent;
            border: none;
        """)
        card_layout.addWidget(sub_label)

        self.input_edit = QLineEdit(self.card)
        self.input_edit.setPlaceholderText("e.g., Venom, Alex, Saar...")
        self.input_edit.setMaxLength(15)
        self.input_edit.setFixedHeight(36)
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background-color: rgba(26, 26, 36, 0.95);
                border: 1.5px solid rgba(0, 255, 255, 0.4);
                border-radius: 8px;
                color: #FFFFFF;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
                padding: 4px 10px;
                selection-background-color: cyan;
                selection-color: black;
            }
            QLineEdit:focus {
                border: 2px solid cyan;
                background-color: rgba(30, 30, 42, 1.0);
            }
        """)
        if current_username:
            self.input_edit.setText(current_username)
            self.input_edit.selectAll()

        self.input_edit.returnPressed.connect(self._on_submit)
        card_layout.addWidget(self.input_edit)

        limit_hint = QLabel("Maximum 15 characters allowed", self.card)
        limit_hint.setStyleSheet("color: #718096; font-size: 9px; font-family: 'Segoe UI'; background: transparent; border: none;")
        card_layout.addWidget(limit_hint)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if allow_cancel:
            self.btn_cancel = QPushButton("Cancel", self.card)
            self.btn_cancel.setFixedHeight(34)
            self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_cancel.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                    color: #E2E8F0;
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 4px 16px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.16);
                    color: #FFFFFF;
                }
            """)
            self.btn_cancel.clicked.connect(self.reject)
            btn_layout.addWidget(self.btn_cancel)

        self.btn_submit = QPushButton(button_text, self.card)
        self.btn_submit.setFixedHeight(34)
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 255, 255, 0.15);
                border: 1.5px solid cyan;
                border-radius: 8px;
                color: #FFFFFF;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 700;
                padding: 4px 20px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 0.35);
                border: 2px solid #5DFEFE;
                color: cyan;
            }
            QPushButton:pressed {
                background-color: rgba(0, 255, 255, 0.55);
            }
        """)
        self.btn_submit.clicked.connect(self._on_submit)
        btn_layout.addWidget(self.btn_submit)

        card_layout.addLayout(btn_layout)
        main_layout.addWidget(self.card)

        self.chosen_username = ""

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.allow_cancel:
                self.reject()
            return
        super().keyPressEvent(event)

    def _on_submit(self):
        val = self.input_edit.text().strip()
        if not val:
            self.input_edit.setPlaceholderText("Please enter a username!")
            return
        if len(val) > 15:
            val = val[:15]
        self.chosen_username = val
        self.accept()


class SmartSearchLineEdit(QLineEdit):
    """
    Enhanced QLineEdit for the Smart Search sub-notch:
    - Allows normal cursor movement (Left/Right arrows) for in-text navigation.
    - Seamlessly propagates Right Arrow (→) to switch to AI Hub when input is empty
      or when the cursor reaches the end of the text.
    - Seamlessly propagates Up Arrow (↑) to return to compact pill mode.
    - Seamlessly propagates Down Arrow (↓) to switch to Audio Visualizer mode.
    - Seamlessly propagates Escape to exit search.
    """
    def __init__(self, pill_widget=None, parent=None):
        super().__init__(parent)
        self.pill_widget = pill_widget

    def keyPressEvent(self, event):
        key = event.key()
        main_win = getattr(self.pill_widget, "main_window", None) if self.pill_widget else None

        if key == Qt.Key.Key_Right:
            text_len = len(self.text())
            cursor_pos = self.cursorPosition()
            # If search input is empty OR cursor is at the end of the text with no active selection,
            # propagate the Right Arrow to switch sub-notches to the AI Hub
            if text_len == 0 or (cursor_pos >= text_len and not self.hasSelectedText()):
                if main_win:
                    main_win.handle_right_arrow()
                    event.accept()
                    return
            # Otherwise, allow normal cursor movement within text
            super().keyPressEvent(event)
            return

        elif key == Qt.Key.Key_Left:
            # Standard cursor navigation within text
            super().keyPressEvent(event)
            return

        elif key == Qt.Key.Key_Up:
            if main_win:
                main_win.handle_up_arrow()
                event.accept()
                return

        elif key == Qt.Key.Key_Down:
            if main_win:
                main_win.handle_down_arrow()
                event.accept()
                return

        elif key == Qt.Key.Key_Escape:
            if main_win:
                main_win._on_esc_requested()
                event.accept()
                return

        super().keyPressEvent(event)


class PillWidget(QFrame):
    """
    Main central widget as a QFrame:
    Enforces a modular multi-notch / sub-panel architecture:
    - Mode 0 (MODE_COMPACT): Main compact pill displaying 15-char username & real IST clock.
    - Mode 1 (MODE_SEARCH): Dedicated wider Smart Search sub-notch with browser & incognito dropdown.
    - Mode 2 (MODE_AI_HUB): Dedicated AI Hub sub-notch with Gemini, ChatGPT, Claude badges.
    - Mode 3 (MODE_VISUALIZER): Dedicated Audio Visualizer sub-notch with real-time style selector.
    """
    MODE_COMPACT = 0
    MODE_SEARCH = 1
    MODE_AI_HUB = 2
    MODE_VISUALIZER = 3

    def __init__(self, main_window: "NotchMainWindow"):
        super().__init__(main_window)
        self.main_window = main_window

        self.setObjectName("pill_frame")
        self.setFixedSize(DEFAULT_COLLAPSED_WIDTH, DEFAULT_COLLAPSED_HEIGHT)
        self.setStyleSheet("""
            QFrame#pill_frame {
                background-color: rgba(15, 15, 15, 255);
                border-radius: 20px;
                border: 2px solid cyan;
            }
        """)

        self.current_mode = self.MODE_COMPACT
        self._current_size = QSize(DEFAULT_COLLAPSED_WIDTH, DEFAULT_COLLAPSED_HEIGHT)

        # Dynamic Audio-Reactive Background Opacity State
        self.current_bg_alpha = 250.0
        self.target_bg_alpha = 250.0

        # RGB Breathing / Moving Neon Border Effect
        self.rgb_border_enabled = True
        self.rgb_timer = QTimer(self)
        self.rgb_timer.timeout.connect(self._update_rgb_border)
        self.rgb_timer.start(35)

        # Audio & Visualizer state
        self.current_rms = 0.0
        self.rendered_bars = np.zeros(NUM_BARS, dtype=np.float32)
        self.silence_remaining = 0.0
        self.is_playing = False
        self.visualizer_style = "Waveform"

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # =====================================================================
        # 1. COMPACT PANEL (Main Pill: IST Clock, Status, 15-Char Username, Mini Vis, 3-Dots Menu)
        # =====================================================================
        self.compact_panel = QWidget(self)
        self.compact_panel.setStyleSheet("background: transparent; border: none;")
        self.compact_layout = QHBoxLayout(self.compact_panel)
        self.compact_layout.setContentsMargins(12, 0, 10, 0)
        self.compact_layout.setSpacing(6)

        self.clock_label_compact = QLabel(get_current_ist_time(), self.compact_panel)
        self.clock_label_compact.setStyleSheet("""
            color: #E2E8F0;
            font-family: 'Segoe UI', 'Consolas', sans-serif;
            font-size: 11px;
            font-weight: 700;
            background: transparent;
            border: none;
            padding-right: 2px;
        """)
        self.compact_layout.addWidget(self.clock_label_compact, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.status_dot = QLabel("●", self.compact_panel)
        self.status_dot.setStyleSheet("color: cyan; font-size: 11px; background: transparent; border: none;")
        self.compact_layout.addWidget(self.status_dot)

        display_name = (self.main_window.username or "Host")[:15]
        self.username_label = QLabel(display_name, self.compact_panel)
        self.username_label.setStyleSheet("""
            color: #FFFFFF;
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
            font-weight: 600;
            background: transparent;
            border: none;
        """)
        self.compact_layout.addWidget(self.username_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.mini_vis = MiniVisualizerWidget(self, self.compact_panel)
        self.compact_layout.addWidget(self.mini_vis)

        # Sleek, minimalist 3-dots menu button (...)
        self.btn_dots_menu = QPushButton("⋮", self.compact_panel)
        self.btn_dots_menu.setFixedSize(20, 20)
        self.btn_dots_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dots_menu.setToolTip("Options Menu")
        self.btn_dots_menu.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 10px;
                color: #A0AEC0;
                font-size: 14px;
                font-weight: bold;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 0.22);
                border: 1px solid rgba(0, 255, 255, 0.6);
                color: cyan;
            }
            QPushButton:pressed {
                background-color: rgba(0, 255, 255, 0.4);
                color: #FFFFFF;
            }
        """)
        self.btn_dots_menu.clicked.connect(self._on_dots_menu_clicked)
        self.compact_layout.addWidget(self.btn_dots_menu)

        # 1-second timer for IST clock
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

        # Initial call to apply RGB neon border
        self._update_rgb_border()

        # =====================================================================
        # 2. SEARCH PANEL (Dedicated Smart Search Sub-Notch)
        # =====================================================================
        self.search_panel = QWidget(self)
        self.search_panel.setStyleSheet("background: transparent; border: none;")
        self.search_layout = QHBoxLayout(self.search_panel)
        self.search_layout.setContentsMargins(14, 4, 14, 4)
        self.search_layout.setSpacing(8)

        self.search_icon_label = QLabel("🔍", self.search_panel)
        self.search_icon_label.setStyleSheet("color: cyan; font-size: 13px; background: transparent; border: none;")
        self.search_layout.addWidget(self.search_icon_label)

        self.search_bar = SmartSearchLineEdit(self, self.search_panel)
        self.search_input = self.search_bar
        self.search_bar.setPlaceholderText("Search with Google...")
        self.search_bar.setFixedHeight(32)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: rgba(22, 22, 30, 0.95);
                border: 1.5px solid rgba(255, 255, 255, 0.22);
                border-radius: 8px;
                color: #FFFFFF;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                padding: 4px 10px;
                selection-background-color: cyan;
                selection-color: black;
            }
            QLineEdit:focus {
                border: 1.5px solid cyan;
                background-color: rgba(26, 26, 36, 0.98);
            }
        """)
        self.search_bar.returnPressed.connect(self.execute_search)
        self.search_layout.addWidget(self.search_bar, stretch=1)

        self.browser_combo = QComboBox(self.search_panel)
        self.browser_combo.addItems([
            "Brave (Normal)",
            "Brave (Incognito)",
            "Edge (Normal)",
            "Edge (Incognito)",
            "Chrome (Normal)",
            "Chrome (Incognito)"
        ])
        self.browser_combo.setFixedHeight(32)
        self.browser_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(22, 22, 30, 0.95);
                border: 1.5px solid rgba(255, 255, 255, 0.22);
                border-radius: 8px;
                color: #EDEDED;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: 600;
                padding: 2px 8px;
                min-width: 120px;
            }
            QComboBox:hover {
                border: 1.5px solid cyan;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1A22;
                border: 1px solid cyan;
                color: #FFFFFF;
                selection-background-color: cyan;
                selection-color: black;
                padding: 4px;
            }
        """)
        self.search_layout.addWidget(self.browser_combo)

        self.btn_close_search = QPushButton("✕", self.search_panel)
        self.btn_close_search.setFixedSize(22, 22)
        self.btn_close_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_search.setToolTip("Return to Compact Notch (Esc)")
        self.btn_close_search.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 11px;
                color: #CCCCCC;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 60, 60, 0.35);
                border: 1px solid #FF3B30;
                color: #FFFFFF;
            }
        """)
        self.btn_close_search.clicked.connect(lambda: self.switch_mode(self.MODE_COMPACT))
        self.search_layout.addWidget(self.btn_close_search)

        # =====================================================================
        # 3. AI HUB PANEL (Dedicated AI Hub Sub-Notch)
        # =====================================================================
        self.ai_hub_panel = QWidget(self)
        self.ai_hub_panel.setStyleSheet("background: transparent; border: none;")
        self.ai_hub_layout = QHBoxLayout(self.ai_hub_panel)
        self.ai_hub_layout.setContentsMargins(16, 2, 16, 2)
        self.ai_hub_layout.setSpacing(0)

        # Left header container (balanced width with right container for pixel-perfect centering)
        left_container = QWidget(self.ai_hub_panel)
        left_container.setFixedWidth(80)
        left_layout = QHBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.ai_hub_title = QLabel("⚡ AI HUB", left_container)
        self.ai_hub_title.setStyleSheet("color: cyan; font-family: 'Segoe UI'; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        left_layout.addWidget(self.ai_hub_title, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.ai_hub_layout.addWidget(left_container)

        self.ai_hub_layout.addStretch(1)

        # Center container hosting the 3 circular AI badges
        center_container = QWidget(self.ai_hub_panel)
        center_layout = QHBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(18)

        self.btn_gemini = CircularAIButton("Gemini", "✨", "#8AB4F8", center_container)
        self.btn_chatgpt = CircularAIButton("ChatGPT", "✳", "#10A37F", center_container)
        self.btn_claude = CircularAIButton("Claude", "✦", "#D97757", center_container)

        center_layout.addWidget(self.btn_gemini)
        center_layout.addWidget(self.btn_chatgpt)
        center_layout.addWidget(self.btn_claude)

        self.btn_gemini.clicked.connect(lambda: self._on_ai_clicked("Gemini", "https://gemini.google.com"))
        self.btn_chatgpt.clicked.connect(lambda: self._on_ai_clicked("ChatGPT", "https://chatgpt.com"))
        self.btn_claude.clicked.connect(lambda: self._on_ai_clicked("Claude", "https://claude.ai"))

        self.ai_hub_layout.addWidget(center_container)

        self.ai_hub_layout.addStretch(1)

        # Right container (80px width matching left container for symmetry)
        right_container = QWidget(self.ai_hub_panel)
        right_container.setFixedWidth(80)
        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.btn_close_ai = QPushButton("✕", right_container)
        self.btn_close_ai.setFixedSize(22, 22)
        self.btn_close_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_ai.setToolTip("Return to Compact Notch (Esc)")
        self.btn_close_ai.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 11px;
                color: #CCCCCC;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 60, 60, 0.35);
                border: 1px solid #FF3B30;
                color: #FFFFFF;
            }
        """)
        self.btn_close_ai.clicked.connect(lambda: self.switch_mode(self.MODE_COMPACT))
        right_layout.addWidget(self.btn_close_ai, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.ai_hub_layout.addWidget(right_container)

        # =====================================================================
        # 4. VISUALIZER PANEL (Dedicated Visualizer Sub-Notch with Style Selector)
        # =====================================================================
        self.visualizer_panel = QWidget(self)
        self.visualizer_panel.setStyleSheet("background: transparent; border: none;")
        self.visualizer_layout = QVBoxLayout(self.visualizer_panel)
        self.visualizer_layout.setContentsMargins(16, 8, 16, 8)
        self.visualizer_layout.setSpacing(6)

        vis_header = QWidget(self.visualizer_panel)
        vis_header.setStyleSheet("background: transparent; border: none;")
        vis_h_box = QHBoxLayout(vis_header)
        vis_h_box.setContentsMargins(0, 0, 0, 0)
        vis_h_box.setSpacing(8)

        self.vis_header_title = QLabel("🎵 System Audio", vis_header)
        self.vis_header_title.setStyleSheet("color: #FFFFFF; font-family: 'Segoe UI'; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        vis_h_box.addWidget(self.vis_header_title)

        self.btn_vis_replay = QPushButton("🔄", vis_header)
        self.btn_vis_replay.setFixedSize(22, 22)
        self.btn_vis_replay.setToolTip("Replay Intro Animation")
        self.btn_vis_replay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_vis_replay.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                color: #EDEDED;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 255, 0.25);
                border: 1px solid cyan;
                color: cyan;
            }
        """)
        self.btn_vis_replay.clicked.connect(self.main_window.replay_intro_animation)
        vis_h_box.addWidget(self.btn_vis_replay)

        vis_h_box.addStretch()

        # Visualizer Style Selector (QComboBox)
        self.vis_style_combo = QComboBox(vis_header)
        self.vis_style_combo.addItems(["Waveform", "Frequency Bars", "Circular Pulse", "Matrix Rain"])
        self.vis_style_combo.setFixedHeight(24)
        self.vis_style_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(22, 22, 30, 0.95);
                border: 1.5px solid rgba(0, 255, 255, 0.35);
                border-radius: 6px;
                color: #FFFFFF;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: 600;
                padding: 1px 8px;
                min-width: 125px;
            }
            QComboBox:hover {
                border: 1.5px solid cyan;
            }
            QComboBox QAbstractItemView {
                background-color: #1A1A22;
                border: 1px solid cyan;
                color: #FFFFFF;
                selection-background-color: cyan;
                selection-color: black;
                padding: 4px;
            }
        """)
        self.vis_style_combo.currentTextChanged.connect(self._on_vis_style_changed)
        vis_h_box.addWidget(self.vis_style_combo)

        # Opaque close button
        self.btn_close_vis = QPushButton("✕", vis_header)
        self.btn_close_vis.setFixedSize(22, 22)
        self.btn_close_vis.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_vis.setToolTip("Return to Compact Notch (Esc)")
        self.btn_close_vis.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 30, 42, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 11px;
                color: #CCCCCC;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 60, 60, 0.55);
                border: 1px solid #FF3B30;
                color: #FFFFFF;
            }
        """)
        self.btn_close_vis.clicked.connect(lambda: self.switch_mode(self.MODE_COMPACT))
        vis_h_box.addWidget(self.btn_close_vis)

        self.visualizer_layout.addWidget(vis_header)

        # Visualizer Canvas (fully opaque wave lines and bars)
        self.visualizer_canvas = AudioVisualizerWidget(self, self.visualizer_panel)
        self.visualizer_layout.addWidget(self.visualizer_canvas)

        # Backwards compatibility aliases
        self.title_label = self.username_label
        self.header_title = self.vis_header_title
        self.header_status = None
        self.clock_label_collapsed = self.clock_label_compact
        self.btn_replay = self.btn_vis_replay
        self.footer_label = None

        # Set initial visibility for default compact state
        self.compact_panel.setVisible(True)
        self.search_panel.setVisible(False)
        self.ai_hub_panel.setVisible(False)
        self.visualizer_panel.setVisible(False)

    def get_mode_size(self, mode: int) -> QSize:
        bw = max(DEFAULT_COLLAPSED_WIDTH, self.main_window.base_width)
        bh = max(DEFAULT_COLLAPSED_HEIGHT, self.main_window.base_height)
        if mode == self.MODE_SEARCH:
            return QSize(max(510, bw + 270), 44)
        elif mode == self.MODE_AI_HUB:
            return QSize(max(420, bw + 190), 58)
        elif mode == self.MODE_VISUALIZER:
            return QSize(max(510, bw + 280), 122)
        else:
            return QSize(bw, bh)

    def switch_mode(self, mode: int):
        self.current_mode = mode
        self.main_window.last_sound_time = time.time()

        # Update panel visibility
        self.compact_panel.setVisible(mode == self.MODE_COMPACT)
        self.search_panel.setVisible(mode == self.MODE_SEARCH)
        self.ai_hub_panel.setVisible(mode == self.MODE_AI_HUB)
        self.visualizer_panel.setVisible(mode == self.MODE_VISUALIZER)

        # Dynamic Audio-Reactive Background Opacity
        if mode == self.MODE_VISUALIZER and self.is_playing:
            self.target_bg_alpha = 135.0
        else:
            self.target_bg_alpha = 250.0

        if not self.rgb_border_enabled:
            self._apply_frame_style()

        target_size = self.get_mode_size(mode)
        self.main_window.animate_to_size(target_size)

        # Focus target controls
        if mode == self.MODE_SEARCH:
            search_input = getattr(self, "search_input", self.search_bar)
            search_input.setFocus()
            search_input.activateWindow()
            search_input.selectAll()
            QTimer.singleShot(30, lambda: (search_input.activateWindow(), search_input.setFocus(), search_input.selectAll()))
        elif mode == self.MODE_AI_HUB:
            QTimer.singleShot(60, self.btn_gemini.button.setFocus)
        elif mode == self.MODE_VISUALIZER:
            QTimer.singleShot(60, self.visualizer_canvas.setFocus)

    def focus_search_input(self):
        """Automatically focuses and activates the search input field for instant typing."""
        search_input = getattr(self, "search_input", self.search_bar)
        search_input.setFocus()
        search_input.activateWindow()
        search_input.selectAll()

    def _on_vis_style_changed(self, new_style: str):
        self.visualizer_style = new_style
        if hasattr(self.main_window, "settings_dialog") and self.main_window.settings_dialog:
            self.main_window.settings_dialog.style_combo.blockSignals(True)
            self.main_window.settings_dialog.style_combo.setCurrentText(new_style)
            self.main_window.settings_dialog.style_combo.blockSignals(False)
        self.visualizer_canvas.update()
        print(f"[VISUALIZER] Switched style to '{new_style}'")

    def cycle_visualizer_style(self):
        styles = ["Waveform", "Frequency Bars", "Circular Pulse", "Matrix Rain"]
        cur = self.visualizer_style
        if cur == "Wave": cur = "Waveform"
        elif cur == "Bars": cur = "Frequency Bars"
        elif cur == "Pulse Dots": cur = "Circular Pulse"

        try:
            idx = styles.index(cur)
            next_style = styles[(idx + 1) % len(styles)]
        except ValueError:
            next_style = styles[0]

        self.vis_style_combo.setCurrentText(next_style)

    def focus_next_ai_button(self):
        ai_buttons = [self.btn_gemini, self.btn_chatgpt, self.btn_claude]
        next_idx = 0
        for i, btn in enumerate(ai_buttons):
            if btn.button.hasFocus():
                next_idx = (i + 1) % len(ai_buttons)
                break
        ai_buttons[next_idx].button.setFocus()
        print(f"[AI HUB] Focused {ai_buttons[next_idx].name} badge.")

    def _update_clock(self):
        """Updates the digital clock labels with real-time Indian Standard Time (HH:MM)."""
        ist_time = get_current_ist_time()
        if hasattr(self, "clock_label_compact"):
            self.clock_label_compact.setText(ist_time)

    def reveal_search_hub(self):
        self.switch_mode(self.MODE_SEARCH)

    def focus_ai_hub(self):
        if self.current_mode != self.MODE_AI_HUB:
            self.switch_mode(self.MODE_AI_HUB)
        else:
            self.focus_next_ai_button()

    def toggle_or_focus_visualizer(self):
        if self.current_mode != self.MODE_VISUALIZER:
            self.switch_mode(self.MODE_VISUALIZER)
        else:
            self.cycle_visualizer_style()

    def open_search_bar(self):
        self.switch_mode(self.MODE_SEARCH)

    def close_search_bar(self):
        self.switch_mode(self.MODE_COMPACT)

    def toggle_search_bar(self):
        if self.current_mode == self.MODE_SEARCH:
            self.switch_mode(self.MODE_COMPACT)
        else:
            self.switch_mode(self.MODE_SEARCH)

    @property
    def search_visible(self) -> bool:
        return self.current_mode == self.MODE_SEARCH

    @search_visible.setter
    def search_visible(self, val: bool):
        pass

    @property
    def collapsed_size(self) -> QSize:
        return self.get_mode_size(self.MODE_COMPACT)

    @collapsed_size.setter
    def collapsed_size(self, size: QSize):
        pass

    @property
    def expanded_size(self) -> QSize:
        return self.get_mode_size(self.MODE_VISUALIZER)

    @expanded_size.setter
    def expanded_size(self, size: QSize):
        pass

    def sizeHint(self) -> QSize:
        return self._current_size

    def get_pill_size(self) -> QSize:
        return self._current_size

    def set_pill_size(self, size: QSize):
        self._current_size = size
        self.setFixedSize(size)
        self.main_window.setFixedSize(size)

        screen = self.main_window.screen() or QApplication.primaryScreen()
        if screen:
            scr = screen.geometry()
            new_x = scr.x() + (scr.width() - size.width()) // 2
            new_y = scr.y() + self.main_window.top_offset
            self.main_window.move(new_x, new_y)

        w, h = size.width(), size.height()
        if hasattr(self, "compact_panel"):
            self.compact_panel.setGeometry(0, 0, w, h)
        if hasattr(self, "search_panel"):
            self.search_panel.setGeometry(0, 0, w, h)
        if hasattr(self, "ai_hub_panel"):
            self.ai_hub_panel.setGeometry(0, 0, w, h)
        if hasattr(self, "visualizer_panel"):
            self.visualizer_panel.setGeometry(0, 0, w, h)

        self.update()

    pillSize = pyqtProperty(QSize, get_pill_size, set_pill_size)

    def show_browser_not_installed_dialog(self):
        """
        Displays a cleanly-styled error popup warning the user to install the browser first,
        centered perfectly on the user's primary monitor.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Browser Not Found")
        msg_box.setText("Please Install the Browser first")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #121218;
                border: 1.5px solid rgba(255, 60, 60, 0.8);
                border-radius: 12px;
            }
            QLabel {
                color: #EDEDED;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 500;
                padding: 8px;
            }
            QPushButton {
                background-color: rgba(255, 60, 60, 0.25);
                border: 1.5px solid #FF3B30;
                border-radius: 8px;
                color: #FFFFFF;
                font-family: 'Segoe UI', sans-serif;
                font-weight: 600;
                font-size: 12px;
                padding: 6px 18px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #FF3B30;
                color: #000000;
            }
        """)

        # Calculate primary screen center geometry and position popup dead-center
        screen = QApplication.primaryScreen()
        if screen:
            screen_geom = screen.geometry()
            box_size = msg_box.sizeHint()
            try:
                b_w = box_size.width()
                b_h = box_size.height()
            except Exception:
                b_w, b_h = 280, 85
            x = int(screen_geom.x() + (screen_geom.width() - b_w) / 2)
            y = int(screen_geom.y() + (screen_geom.height() - b_h) / 2)
            msg_box.move(x, y)

        msg_box.exec()
        return msg_box

    def execute_search(self):
        query = self.search_bar.text().strip()
        if not query:
            return

        self.main_window.last_sound_time = time.time()
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?q={encoded_query}"
        browser_choice = self.browser_combo.currentText().strip()

        print(f"[SEARCH] Query: '{query}' -> URL: {search_url} | Option: '{browser_choice}'")

        # 1. Resolve browser executable, canonical name, and incognito mode
        exe_path, browser_name, is_incognito = get_browser_executable(browser_choice)

        # 2. Check if selected browser is installed (Brave, Chrome)
        if exe_path is None:
            print(f"[SEARCH WARNING] Browser '{browser_name}' not installed. Displaying centered error popup.")
            self.show_browser_not_installed_dialog()
            return

        # 3. Build command with incognito/private flags when requested:
        cmd = [exe_path]
        if is_incognito:
            if browser_name == "Edge":
                cmd.append("-inprivate")
            else:
                cmd.append("--incognito")
        cmd.append(search_url)

        try:
            print(f"[SEARCH LAUNCH] Launching browser command: {cmd}")
            subprocess.Popen(cmd)
        except Exception as e:
            print(f"[ERROR] Failed to launch search query with command {cmd}: {e}")
            try:
                if is_incognito:
                    flag = "-inprivate" if browser_name == "Edge" else "--incognito"
                    subprocess.Popen(f'start "" "{exe_path}" {flag} "{search_url}"', shell=True)
                else:
                    subprocess.Popen(f'start "" "{exe_path}" "{search_url}"', shell=True)
            except Exception as ex:
                print(f"[ERROR] Shell fallback also failed: {ex}")
                traceback.print_exc()

        self.search_bar.clear()
        self.switch_mode(self.MODE_COMPACT)

    def _on_ai_clicked(self, name: str, url: str):
        self.main_window.last_sound_time = time.time()
        # Read incognito mode from the search dropdown if applicable
        selected_option = self.browser_combo.currentText().strip()
        is_incognito = "(Incognito)" in selected_option
        # AI icons strictly open in Microsoft Edge by default
        open_or_focus_ai(name, url, is_incognito=is_incognito, browser="Edge")

    def update_audio_state(self, rms: float, bars: list, is_playing: bool, silence_remaining: float):
        self.current_rms = rms
        self.is_playing = is_playing
        self.silence_remaining = silence_remaining

        new_bars = np.array(bars, dtype=np.float32)
        self.rendered_bars = np.maximum(self.rendered_bars * DECAY_RATE, new_bars)

        # Update UI indicators
        if hasattr(self, "status_dot") and self.status_dot:
            if is_playing:
                self.status_dot.setStyleSheet("color: #DC2626; font-size: 11px; background: transparent; border: none;")
            else:
                self.status_dot.setStyleSheet("color: cyan; font-size: 11px; background: transparent; border: none;")

        # Dynamic Audio-Reactive Background Transparency:
        # In visualizer mode with active playback, lower alpha to ~135 so desktop/media subtly peeks through;
        # when audio is silent or stopped, revert to solid dark shade (~250) for crisp readability.
        if self.current_mode == self.MODE_VISUALIZER and is_playing:
            self.target_bg_alpha = 135.0
        else:
            self.target_bg_alpha = 250.0

        if not self.rgb_border_enabled:
            self._apply_frame_style()

        self.visualizer_canvas.update()
        self.mini_vis.update()

    def _is_interactive_control(self, child) -> bool:
        """Determines whether a child widget is an interactive control (button, input, dropdown)."""
        if child is None:
            return False
        curr = child
        while curr is not None and curr is not self:
            if isinstance(curr, (QPushButton, QLineEdit, QComboBox, CircularAIButton)):
                return True
            curr = curr.parent()
        return False

    def _on_dots_menu_clicked(self):
        """Opens options dropdown menu anchored below the 3-dots button."""
        self.main_window.last_sound_time = time.time()
        pos = self.btn_dots_menu.mapToGlobal(QPoint(-20, self.btn_dots_menu.height() + 4))
        self.show_custom_context_menu(pos)

    def _apply_frame_style(self):
        """Applies dynamic frame background transparency and RGB border styling."""
        self.current_bg_alpha += (self.target_bg_alpha - self.current_bg_alpha) * 0.22
        bg_alpha = int(self.current_bg_alpha)

        if self.rgb_border_enabled:
            t = time.time()
            # Smooth hue cycle (~3.5s per revolution)
            h = (t * 0.28) % 1.0

            # Breathing glow factor (sine oscillation between 0.88 and 1.0)
            breath = 0.88 + 0.12 * math.sin(t * 3.2)

            # Neon hues shifting through cyan, purple, crimson, green
            c1 = QColor.fromHsvF(h % 1.0, 0.95, breath)
            c2 = QColor.fromHsvF((h + 0.33) % 1.0, 0.95, breath)
            c3 = QColor.fromHsvF((h + 0.66) % 1.0, 0.95, breath)

            # Rotating gradient angle
            theta = t * 1.5
            x1 = 0.5 - 0.5 * math.cos(theta)
            y1 = 0.5 - 0.5 * math.sin(theta)
            x2 = 0.5 + 0.5 * math.cos(theta)
            y2 = 0.5 + 0.5 * math.sin(theta)

            border_str = (
                f"2px solid qlineargradient(x1:{x1:.2f}, y1:{y1:.2f}, x2:{x2:.2f}, y2:{y2:.2f}, "
                f"stop:0 {c1.name()}, stop:0.5 {c2.name()}, stop:1 {c3.name()})"
            )
        else:
            border_str = "2px solid cyan"

        self.setStyleSheet(f"""
            QFrame#pill_frame {{
                background-color: rgba(15, 15, 15, {bg_alpha});
                border-radius: 20px;
                border: {border_str};
            }}
        """)

    def _update_rgb_border(self):
        """Continuously called by rgb_timer to update RGB neon gradient and background transparency."""
        self._apply_frame_style()

    def toggle_rgb_border(self, enabled: bool | None = None):
        """Toggles RGB breathing neon border between dynamic gradient and static cyan."""
        if enabled is None:
            self.rgb_border_enabled = not self.rgb_border_enabled
        else:
            self.rgb_border_enabled = enabled

        if self.rgb_border_enabled:
            if not self.rgb_timer.isActive():
                self.rgb_timer.start(35)
            self._apply_frame_style()
            print("[RGB] Neon breathing border: ON")
        else:
            self.rgb_timer.stop()
            self._apply_frame_style()
            print("[RGB] Neon breathing border: OFF (frozen cyan)")

        if hasattr(self.main_window, "settings_dialog") and self.main_window.settings_dialog:
            self.main_window.settings_dialog.rgb_checkbox.blockSignals(True)
            self.main_window.settings_dialog.rgb_checkbox.setChecked(self.rgb_border_enabled)
            self.main_window.settings_dialog.rgb_checkbox.blockSignals(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            pos = event.position().toPoint()
            child = self.childAt(pos)
            if self._is_interactive_control(child):
                super().mousePressEvent(event)
                return

            self.show_custom_context_menu(event.globalPosition().toPoint())
            event.accept()
            return
        elif event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            child = self.childAt(pos)
            if self._is_interactive_control(child):
                super().mousePressEvent(event)
                return

            # Direct left-click on the notch background is completely removed!
            event.accept()
            return

        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        pos = event.pos()
        child = self.childAt(pos)
        if self._is_interactive_control(child):
            super().contextMenuEvent(event)
            return

        self.show_custom_context_menu(event.globalPos())
        event.accept()

    def show_custom_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(18, 18, 24, 250);
                border: 1.5px solid cyan;
                border-radius: 10px;
                padding: 6px;
                color: #EDEDED;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 500;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 255, 255, 0.25);
                color: cyan;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.15);
                margin: 4px 8px;
            }
        """)

        # Clean, essential high-level actions only
        settings_action = menu.addAction("⚙️  UI Settings")
        settings_action.setObjectName("action_ui_settings")
        settings_action.setData("UI Settings")

        replay_action = menu.addAction("🔄  Replay Intro Animation")
        replay_action.setObjectName("action_replay_intro")
        replay_action.setData("Replay Intro Animation")

        menu.addSeparator()

        exit_action = menu.addAction("❌  Exit")
        exit_action.setObjectName("action_exit")
        exit_action.setData("Exit")

        settings_action.triggered.connect(self.open_settings_dialog)
        replay_action.triggered.connect(self.main_window.replay_intro_animation)
        exit_action.triggered.connect(QApplication.instance().quit)

        menu.exec(global_pos)

    def prompt_change_username(self):
        """
        Prompts the user with a clean, dark-themed dialog to change their username.
        Enforces validation (<= 15 characters, non-empty), overwrites local storage,
        and refreshes the live UI immediately.
        """
        current_name = getattr(self.main_window, "username", "") or "Host"
        dlg = UsernameDialog(
            parent=self,
            title="Change Username",
            subtitle="Enter a new username for your Symbiote desktop notch:",
            button_text="Update Username",
            current_username=current_name,
            allow_cancel=True
        )
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            dlg.move(geo.x() + (geo.width() - dlg.width()) // 2,
                     geo.y() + (geo.height() - dlg.height()) // 2)

        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.chosen_username:
            new_name = dlg.chosen_username.strip()[:15]
            if new_name:
                self.main_window.update_username(new_name)

    def update_username(self, new_name: str):
        """Refreshes the live compact notch UI with the new username immediately."""
        clean_name = (new_name or "").strip()[:15]
        if not clean_name:
            return
        if hasattr(self, "username_label") and self.username_label:
            self.username_label.setText(clean_name)
            self.username_label.adjustSize()
        if hasattr(self, "title_label") and self.title_label:
            self.title_label.setText(clean_name)
            self.title_label.adjustSize()
        if hasattr(self, "compact_panel") and self.compact_panel:
            self.compact_panel.update()
        self.update()

    def open_settings_dialog(self):
        if not hasattr(self.main_window, "settings_dialog") or self.main_window.settings_dialog is None:
            self.main_window.settings_dialog = SettingsDialog(self.main_window)
        else:
            self.main_window.settings_dialog.refresh_values()
        self.main_window.settings_dialog.show()
        self.main_window.settings_dialog.raise_()
        self.main_window.settings_dialog.activateWindow()


class SymbioteAnimationOverlay(QWidget):
    """
    Synced Cinematic Intro Overlay:
    1. Welcome Phase (0.0s - 1.5s): Displays glowing 'Welcome, [Username]' in the center of the screen.
    2. Shatter/Transition Phase (1.5s - 2.1s): Visually fractures, dissolves, and slides apart with glowing
       symbiote filaments and shockwave rings blasting toward the monitor margins.
    3. Symbiote Integration Phase (2.0s - 3.8s): Seamlessly triggers the fullscreen Venom/Carnage border-crawl
       and inward-pull animation, finally swirling and forming the pill-shaped notch at the top-center.
    Calls .hide() immediately upon finish, leaving only the styled QFrame visible.
    """
    def __init__(self, main_window: "NotchMainWindow"):
        super().__init__()
        self.main_window = main_window
        self.start_time = 0.0

        # Standalone click-through overlay flags
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        else:
            self.resize(1920, 1080)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)

    def start_intro(self):
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())
        self.start_time = time.time()
        self.timer.start(16)
        self.show()
        self.raise_()
        self.update()
        print(f"[INTRO] Fullscreen cinematic sequence started for user '{self.main_window.username}'.")

    def _on_tick(self):
        elapsed = time.time() - self.start_time
        self.update()

        if elapsed >= TOTAL_INTRO_DURATION:
            self.timer.stop()
            self.hide()
            print("[INTRO] Synced cinematic intro finished. Overlay hidden.")
            self.main_window.on_intro_finished()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = float(self.width())
        h = float(self.height())
        target_x = w / 2.0
        target_y = float(self.main_window.top_offset)

        elapsed = time.time() - self.start_time
        username = self.main_window.username or "Host"
        welcome_text = f"Welcome, {username}"

        # -----------------------------------------------------------------
        # PHASE A & B: WELCOME TEXT & SHATTER / DISSOLVE TRANSITION
        # -----------------------------------------------------------------
        if elapsed < SYMBIOTE_START + 0.2:
            center_x = w / 2.0
            center_y = h / 2.0

            if elapsed < WELCOME_DURATION:
                # Phase A: Welcome Text Display (0.0s - 1.5s)
                fade_in = min(1.0, elapsed / 0.4)
                alpha = int(255 * fade_in)

                # Ambient symbiote aura
                aura = QRadialGradient(center_x, center_y, 400.0)
                aura.setColorAt(0.0, QColor(0, 255, 255, int(40 * fade_in)))
                aura.setColorAt(0.4, QColor(185, 28, 28, int(25 * fade_in)))
                aura.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.setBrush(QBrush(aura))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(center_x, center_y), 420.0, 220.0)

                # Overline badge
                over_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
                over_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
                painter.setFont(over_font)
                painter.setPen(QColor(0, 255, 255, int(210 * fade_in)))
                painter.drawText(
                    int(center_x - 300), int(center_y - 70), 600, 30,
                    Qt.AlignmentFlag.AlignCenter, "⚡ SYMBIOTE PROTOCOL ACTIVE ⚡"
                )

                # Main Welcome Typography
                main_font = QFont("Segoe UI", 42, QFont.Weight.Bold)
                painter.setFont(main_font)

                # Soft drop shadow / glow
                painter.setPen(QColor(0, 255, 255, int(80 * fade_in)))
                painter.drawText(
                    int(center_x - 450), int(center_y - 30) + 2, 900, 70,
                    Qt.AlignmentFlag.AlignCenter, welcome_text
                )

                # Primary text fill
                painter.setPen(QColor(255, 255, 255, alpha))
                painter.drawText(
                    int(center_x - 450), int(center_y - 30), 900, 70,
                    Qt.AlignmentFlag.AlignCenter, welcome_text
                )

                # Subtitle
                sub_font = QFont("Segoe UI", 11, QFont.Weight.DemiBold)
                painter.setFont(sub_font)
                painter.setPen(QColor(160, 174, 192, int(190 * fade_in)))
                painter.drawText(
                    int(center_x - 300), int(center_y + 45), 600, 30,
                    Qt.AlignmentFlag.AlignCenter, "Neural link synchronized • Desktop system online"
                )

            else:
                # Phase B: Shatter / Dissolve Phase (1.5s - 2.1s)
                shatter_p = min(1.0, (elapsed - WELCOME_DURATION) / SHATTER_DURATION)
                alpha = int(255 * (1.0 - (shatter_p ** 1.3)))

                # Expanding radial shockwave rings
                wave_r = shatter_p * 650.0
                wave_alpha = int(220 * (1.0 - shatter_p))
                wave_pen = QPen(QColor(0, 255, 255, wave_alpha), max(1.0, 3.5 * (1.0 - shatter_p)))
                painter.setPen(wave_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(center_x, center_y), wave_r, wave_r * 0.55)

                crimson_wave_pen = QPen(QColor(220, 38, 38, wave_alpha), max(1.0, 2.0 * (1.0 - shatter_p)))
                painter.setPen(crimson_wave_pen)
                painter.drawEllipse(QPointF(center_x, center_y), wave_r * 0.75, wave_r * 0.4)

                # Fractured shards of the welcome text sliding and flying outward
                main_font = QFont("Segoe UI", 42, QFont.Weight.Bold)
                painter.setFont(main_font)

                num_chars = len(welcome_text)
                base_text_width = num_chars * 26.0
                start_x = center_x - (base_text_width / 2.0)

                for idx, ch in enumerate(welcome_text):
                    if ch == " ":
                        continue
                    char_frac = (idx / float(max(1, num_chars - 1))) - 0.5
                    angle = char_frac * 2.2 + math.sin(idx * 2.7) * 0.4
                    dist = (shatter_p ** 1.6) * 520.0 + (idx % 3) * 35.0

                    shard_x = (start_x + idx * 26.0) + math.sin(angle) * dist
                    shard_y = (center_y - 10.0) + math.cos(angle) * (dist * 0.55) + math.sin(idx * 3.1) * shatter_p * 90.0

                    # Tendril filament trail from center to shard
                    filament_path = QPainterPath()
                    filament_path.moveTo(center_x, center_y)
                    ctrl_x = (center_x + shard_x) / 2.0 + math.sin(idx + shatter_p * 5.0) * 45.0
                    ctrl_y = (center_y + shard_y) / 2.0 + math.cos(idx + shatter_p * 5.0) * 45.0
                    filament_path.quadTo(ctrl_x, ctrl_y, shard_x, shard_y)

                    painter.setPen(QPen(QColor(220, 38, 38, int(alpha * 0.5)), 1.5))
                    painter.drawPath(filament_path)

                    # Draw flying letter shard
                    painter.setPen(QColor(255, 255, 255, alpha))
                    painter.drawText(int(shard_x), int(shard_y), 40, 60, Qt.AlignmentFlag.AlignCenter, ch)

        # -----------------------------------------------------------------
        # PHASE C: SYMBIOTE INTEGRATION (Border Crawl & Inward Retract)
        # -----------------------------------------------------------------
        if elapsed < SYMBIOTE_START:
            return

        p = min(1.0, (elapsed - SYMBIOTE_START) / SYMBIOTE_DURATION)

        origins = []
        for i in range(10):
            origins.append((i * (w / 9.0), h, "bottom"))
        for i in range(6):
            origins.append((0.0, (i + 0.5) * (h / 6.0), "left"))
            origins.append((w, (i + 0.5) * (h / 6.0), "right"))

        for idx, (ox, oy, side) in enumerate(origins):
            phase = idx * 1.35

            if p < 0.88:
                u = max(0.0, (p - 0.25) / 0.63)
                root_t = u ** 2.2
                rx = ox + (target_x - ox) * root_t * 0.95
                ry = oy + (target_y - oy) * root_t * 0.95

                tip_u = min(1.0, p / 0.80)
                tip_t = tip_u ** 1.6
                tx = ox + (target_x - ox) * tip_t
                ty = oy + (target_y - oy) * tip_t

                path = QPainterPath()
                path.moveTo(rx, ry)

                num_pts = 16
                for s in range(1, num_pts + 1):
                    frac = s / float(num_pts)
                    bx = rx + (tx - rx) * frac
                    by = ry + (ty - ry) * frac

                    wave_amp = math.sin(frac * math.pi) * (32.0 * (1.0 - p * 0.6))
                    wave_val = math.sin(frac * 8.0 - p * 14.0 + phase) * wave_amp

                    dx = tx - rx
                    dy = ty - ry
                    dist = math.hypot(dx, dy) + 0.001
                    nx = -dy / dist
                    ny = dx / dist

                    bx += nx * wave_val
                    by += ny * wave_val
                    path.lineTo(bx, by)

                core_w = max(2.5, (14.0 - p * 10.0) * (1.0 + (idx % 3) * 0.35))
                painter.setPen(QPen(QColor(6, 6, 10, 240), core_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                painter.drawPath(path)

                crimson_w = max(1.5, core_w * 0.58)
                crimson_color = QColor(185, 28, 28, 240) if idx % 2 == 0 else QColor(220, 38, 38, 245)
                painter.setPen(QPen(crimson_color, crimson_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                painter.drawPath(path)

                if idx % 2 == 1:
                    painter.setPen(QPen(QColor(255, 65, 65, int(200 * (1.0 - p * 0.4))), 1.2))
                    painter.drawPath(path)

            if p >= 0.70:
                vortex_p = (p - 0.70) / 0.30
                swirl_angle = vortex_p * math.pi * 6.5 + phase
                swirl_r = (1.0 - vortex_p) * 150.0 + math.sin(vortex_p * math.pi) * 35.0

                sx = target_x + math.cos(swirl_angle) * swirl_r
                sy = target_y + math.sin(swirl_angle) * (swirl_r * 0.5) + (vortex_p * 20.0)

                v_path = QPainterPath()
                v_path.moveTo(target_x, target_y)
                v_path.quadTo(
                    target_x + math.cos(swirl_angle + 1.0) * (swirl_r * 0.7),
                    target_y + (swirl_r * 0.3),
                    sx, sy
                )
                painter.setPen(QPen(QColor(220, 38, 38, int(255 * (1.0 - vortex_p * 0.25))), 2.0))
                painter.drawPath(v_path)

        if p >= 0.75:
            form_p = (p - 0.75) / 0.25
            cur_w = float(max(DEFAULT_COLLAPSED_WIDTH, self.main_window.base_width)) * min(1.0, form_p * 1.15)
            cur_h = float(max(DEFAULT_COLLAPSED_HEIGHT, self.main_window.base_height)) * min(1.0, form_p * 1.15)

            burst = QRadialGradient(target_x, cur_h / 2.0, max(1.0, cur_w * 0.8))
            burst.setColorAt(0.0, QColor(0, 255, 255, int(180 * (1.0 - form_p))))
            burst.setColorAt(0.6, QColor(220, 38, 38, int(140 * (1.0 - form_p))))
            burst.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(burst))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(target_x, cur_h / 2.0), cur_w * 0.8, cur_h * 2.0)


class NotchMainWindow(QMainWindow):
    """
    Main desktop notch window:
    - Uses self.setCentralWidget() with a strictly sized QFrame (230, 40).
    - Window is transparent (WA_TranslucentBackground), QFrame is solid (rgba(15, 15, 15, 255)).
    - Audio capture is completely isolated in a non-blocking thread via callbacks and signals.
    - Forces show(), raise_(), and QApplication.processEvents() before audio starts.
    """

    def __init__(self, username: str = "Host"):
        super().__init__()

        self.username = username
        self.base_width = DEFAULT_COLLAPSED_WIDTH
        self.base_height = DEFAULT_COLLAPSED_HEIGHT
        self.top_offset = 0
        self.settings_dialog = None

        # Persistent window flags: Tool | FramelessWindowHint | WindowStaysOnTopHint
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Place the cyan-bordered QFrame inside it with a strict setFixedSize(230, 40)
        self.pill_widget = PillWidget(self)
        self.search_input = self.pill_widget.search_bar
        self.setCentralWidget(self.pill_widget)
        self.setFixedSize(DEFAULT_COLLAPSED_WIDTH, DEFAULT_COLLAPSED_HEIGHT)

        # Position notch at top-center of primary screen
        screen = QApplication.primaryScreen() or self.screen()
        scr = screen.geometry() if screen else QRectF(0, 0, 1920, 1080).toRect()
        new_x = scr.x() + (scr.width() - self.base_width) // 2
        new_y = scr.y() + self.top_offset
        self.move(new_x, new_y)

        self.last_sound_time = 0.0

        # Animation for expansion and collapse
        self.animation = QPropertyAnimation(self.pill_widget, b"pillSize")
        self.animation.setDuration(320)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Hotkeys
        self.bridge = HotkeyBridge()
        self.bridge.toggle_requested.connect(self.toggle_expansion)
        self.bridge.force_close_requested.connect(self._on_esc_requested)
        self.bridge.up_arrow_requested.connect(self.handle_up_arrow)
        self.bridge.down_arrow_requested.connect(self.handle_down_arrow)
        self.bridge.left_arrow_requested.connect(self.handle_left_arrow)
        self.bridge.right_arrow_requested.connect(self.handle_right_arrow)
        self._setup_shortcuts()

        # Dedicated Non-blocking Audio Thread
        self.audio_thread = AudioCaptureThread(self)
        self.audio_thread.audio_data_ready.connect(self.handle_audio_data)

        # Separate fullscreen symbiote intro overlay
        self.intro_overlay = SymbioteAnimationOverlay(self)

    def animate_to_size(self, target_size: QSize):
        """Smoothly animates the notch to the specified target size."""
        if self.pill_widget.get_pill_size() == target_size:
            return
        self.animation.stop()
        self.animation.setStartValue(self.pill_widget.get_pill_size())
        self.animation.setEndValue(target_size)
        self.animation.start()

    def start_intro(self):
        """Hides the notch window and starts intro overlay."""
        self.hide()
        self.intro_overlay.start_intro()

    def replay_intro_animation(self):
        """
        Hides the settled notch widget, resets state, and re-triggers
        the fullscreen symbiote intro overlay animation from the beginning.
        """
        print("[INFO] Replaying Symbiote Intro Animation.")

        # Close settings dialog if open
        if self.settings_dialog:
            try:
                self.settings_dialog.close()
            except Exception:
                pass

        # Reset to compact mode
        self.pill_widget.search_bar.clear()
        self.pill_widget.switch_mode(self.pill_widget.MODE_COMPACT)
        self.pill_widget.set_pill_size(self.pill_widget.get_mode_size(self.pill_widget.MODE_COMPACT))

        # Hide the settled notch widget
        self.hide()

        # Instantly re-enable and re-trigger the fullscreen transparent overlay
        self.intro_overlay.start_intro()

    def on_intro_finished(self):
        """
        Called when intro animation finishes and overlay is hidden.
        Forces painting of UI explicitly before starting the audio thread.
        """
        self.pill_widget.switch_mode(self.pill_widget.MODE_COMPACT)
        self._apply_sizes()

        # Force Paint: Explicitly call show, raise, and processEvents immediately
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.processEvents()

        # Start non-blocking audio capture only AFTER UI is forced to paint
        if not self.audio_thread.isRunning():
            self.audio_thread.start()

        print(f"[INFO] Notch formed at ({self.x()}, {self.y()}, {self.width()}, {self.height()}). Audio thread running.")

    def _apply_sizes(self):
        target_size = self.pill_widget.get_mode_size(self.pill_widget.current_mode)
        self.pill_widget.set_pill_size(target_size)

    def update_base_width(self, width: int):
        self.base_width = max(DEFAULT_COLLAPSED_WIDTH, width)
        self._apply_sizes()

    def update_base_height(self, height: int):
        self.base_height = max(DEFAULT_COLLAPSED_HEIGHT, height)
        self._apply_sizes()

    def update_top_offset(self, offset: int):
        self.top_offset = offset
        cur_size = self.pill_widget.get_pill_size()
        self.pill_widget.set_pill_size(cur_size)

    def update_visualizer_style(self, style: str):
        self.pill_widget.visualizer_style = style
        self.pill_widget.vis_style_combo.blockSignals(True)
        self.pill_widget.vis_style_combo.setCurrentText(style)
        self.pill_widget.vis_style_combo.blockSignals(False)
        self.pill_widget.visualizer_canvas.update()

    def update_username(self, new_username: str):
        """
        Updates the username in runtime memory, overwrites local user storage,
        and refreshes the live UI immediately without restarting the app.
        """
        cleaned = (new_username or "").strip()[:15]
        if not cleaned:
            return

        self.username = cleaned
        save_username(cleaned)

        # Refresh the live UI on the compact notch immediately
        if hasattr(self, "pill_widget") and self.pill_widget:
            self.pill_widget.update_username(cleaned)

        # Refresh settings dialog if open
        if hasattr(self, "settings_dialog") and self.settings_dialog:
            self.settings_dialog.refresh_values()

        print(f"[INFO] Username updated to '{cleaned}' and live UI refreshed.")

    def prompt_change_username(self):
        """Opens dialog to change username and updates runtime & storage."""
        if hasattr(self, "pill_widget") and self.pill_widget:
            self.pill_widget.prompt_change_username()

    @property
    def is_expanded(self) -> bool:
        return self.pill_widget.current_mode != self.pill_widget.MODE_COMPACT

    @is_expanded.setter
    def is_expanded(self, val: bool):
        pass

    def expand(self):
        self.pill_widget.switch_mode(self.pill_widget.MODE_VISUALIZER)

    def collapse(self):
        self.pill_widget.switch_mode(self.pill_widget.MODE_COMPACT)

    def toggle_expansion(self):
        if self.pill_widget.current_mode == self.pill_widget.MODE_COMPACT:
            self.pill_widget.switch_mode(self.pill_widget.MODE_VISUALIZER)
        else:
            self.pill_widget.switch_mode(self.pill_widget.MODE_COMPACT)

    def handle_up_arrow(self):
        """Up Arrow (↑): Controls the main compact pill state (showing username & real IST clock)."""
        self.last_sound_time = time.time()
        self.pill_widget.switch_mode(self.pill_widget.MODE_COMPACT)
        self.raise_()
        self.activateWindow()

    def handle_down_arrow(self):
        """Down Arrow (↓): Focus or open the visualizer sub-notch, or cycle styles if already open."""
        self.last_sound_time = time.time()
        self.raise_()
        self.activateWindow()
        self.pill_widget.toggle_or_focus_visualizer()

    def handle_left_arrow(self):
        """Left Arrow (←): Instantly open/reveal the dedicated Smart Search sub-notch."""
        self.last_sound_time = time.time()
        self.raise_()
        self.activateWindow()
        self.pill_widget.switch_mode(self.pill_widget.MODE_SEARCH)
        QApplication.processEvents()
        search_input = getattr(self.pill_widget, "search_input", self.pill_widget.search_bar)
        search_input.setFocus()
        search_input.activateWindow()
        search_input.selectAll()

    def handle_right_arrow(self):
        """Right Arrow (→): Instantly open the dedicated AI Icons hub sub-notch."""
        self.last_sound_time = time.time()
        search_input = getattr(self.pill_widget, "search_input", self.pill_widget.search_bar)
        if search_input.hasFocus():
            text_len = len(search_input.text())
            cursor_pos = search_input.cursorPosition()
            if text_len > 0 and cursor_pos < text_len:
                return
        self.raise_()
        self.activateWindow()
        self.pill_widget.focus_ai_hub()

    def _setup_shortcuts(self):
        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.esc_shortcut.activated.connect(self._on_esc_requested)

        # In-app / focused window keyboard shortcuts
        self.up_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        self.up_shortcut.activated.connect(self.handle_up_arrow)

        self.down_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        self.down_shortcut.activated.connect(self.handle_down_arrow)

        self.left_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.left_shortcut.activated.connect(self._on_qt_left)

        self.right_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.right_shortcut.activated.connect(self._on_qt_right)

        try:
            keyboard.add_hotkey("ctrl+alt+n", self.bridge.toggle_requested.emit, suppress=False)
            keyboard.add_hotkey("f9", self.bridge.toggle_requested.emit, suppress=False)
            keyboard.add_hotkey("esc", self.bridge.force_close_requested.emit, suppress=False)

            # Precise Global Keyboard Arrow Key Controls
            keyboard.add_hotkey("up", self._on_global_up, suppress=False)
            keyboard.add_hotkey("down", self._on_global_down, suppress=False)
            keyboard.add_hotkey("left", self._on_global_left, suppress=False)
            keyboard.add_hotkey("right", self._on_global_right, suppress=False)

            print("[INFO] Shortcuts registered: Esc (compact/exit), F9/Ctrl+Alt+N (toggle), ↑ (compact), ↓ (visualizer/style), ← (search), → (AI hub).")
        except Exception as e:
            print(f"[ERROR] Failed to register global hotkey: {e}")

    def _on_global_up(self):
        if self.pill_widget.browser_combo.hasFocus() or self.pill_widget.vis_style_combo.hasFocus():
            return
        self.bridge.up_arrow_requested.emit()

    def _on_global_down(self):
        if self.pill_widget.browser_combo.hasFocus() or self.pill_widget.vis_style_combo.hasFocus():
            return
        self.bridge.down_arrow_requested.emit()

    def _on_global_left(self):
        search_input = getattr(self.pill_widget, "search_input", self.pill_widget.search_bar)
        if search_input.hasFocus():
            cursor_pos = search_input.cursorPosition()
            if cursor_pos > 0:
                return
        self.bridge.left_arrow_requested.emit()

    def _on_global_right(self):
        search_input = getattr(self.pill_widget, "search_input", self.pill_widget.search_bar)
        if search_input.hasFocus():
            text_len = len(search_input.text())
            cursor_pos = search_input.cursorPosition()
            if text_len > 0 and cursor_pos < text_len:
                return
        self.bridge.right_arrow_requested.emit()

    def _on_qt_left(self):
        search_input = getattr(self.pill_widget, "search_input", self.pill_widget.search_bar)
        if search_input.hasFocus():
            cursor_pos = search_input.cursorPosition()
            if cursor_pos > 0:
                search_input.setCursorPosition(cursor_pos - 1)
                return
        self.handle_left_arrow()

    def _on_qt_right(self):
        search_input = getattr(self.pill_widget, "search_input", self.pill_widget.search_bar)
        if search_input.hasFocus():
            text_len = len(search_input.text())
            cursor_pos = search_input.cursorPosition()
            if text_len > 0 and cursor_pos < text_len:
                search_input.setCursorPosition(cursor_pos + 1)
                return
        self.handle_right_arrow()

    def _on_esc_requested(self):
        """Esc handler: returns to compact notch if in a sub-notch, or closes app if already compact."""
        if self.pill_widget.current_mode != self.pill_widget.MODE_COMPACT:
            self.pill_widget.switch_mode(self.pill_widget.MODE_COMPACT)
        else:
            self._force_close()

    def _force_close(self):
        print("[INFO] Force close shortcut triggered (Esc). Terminating cleanly.")
        QApplication.instance().quit()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self._on_esc_requested()
            event.accept()
            return
        elif key == Qt.Key.Key_Up:
            if not self.pill_widget.browser_combo.hasFocus() and not self.pill_widget.vis_style_combo.hasFocus():
                self.handle_up_arrow()
                event.accept()
                return
        elif key == Qt.Key.Key_Down:
            if not self.pill_widget.browser_combo.hasFocus() and not self.pill_widget.vis_style_combo.hasFocus():
                self.handle_down_arrow()
                event.accept()
                return
        elif key == Qt.Key.Key_Left:
            search_input = getattr(self.pill_widget, "search_input", self.pill_widget.search_bar)
            if not search_input.hasFocus():
                self.handle_left_arrow()
                event.accept()
                return
        elif key == Qt.Key.Key_Right:
            search_input = getattr(self.pill_widget, "search_input", self.pill_widget.search_bar)
            if not search_input.hasFocus():
                self.handle_right_arrow()
                event.accept()
                return
            else:
                text_len = len(search_input.text())
                cursor_pos = search_input.cursorPosition()
                if text_len == 0 or cursor_pos >= text_len:
                    self.handle_right_arrow()
                    event.accept()
                    return
        super().keyPressEvent(event)

    def handle_audio_data(self, rms: float, bars: list):
        if not self.isVisible():
            return

        current_time = time.time()

        if self.pill_widget.current_mode == self.pill_widget.MODE_SEARCH or self.pill_widget.search_bar.hasFocus():
            self.last_sound_time = current_time

        is_playing = (rms >= VOLUME_THRESHOLD)

        if is_playing:
            self.last_sound_time = current_time
            silence_remaining = SILENCE_TIMEOUT
            # Auto-expand to visualizer ONLY when in compact mode
            if self.pill_widget.current_mode == self.pill_widget.MODE_COMPACT:
                self.pill_widget.switch_mode(self.pill_widget.MODE_VISUALIZER)
        else:
            silence_elapsed = current_time - self.last_sound_time if self.last_sound_time > 0 else SILENCE_TIMEOUT
            silence_remaining = max(0.0, SILENCE_TIMEOUT - silence_elapsed)
            # If in visualizer mode and silence elapsed, return to compact
            if self.pill_widget.current_mode == self.pill_widget.MODE_VISUALIZER and (silence_elapsed >= SILENCE_TIMEOUT):
                self.pill_widget.switch_mode(self.pill_widget.MODE_COMPACT)

        self.pill_widget.update_audio_state(rms, bars, is_playing, silence_remaining)

    def closeEvent(self, event):
        try:
            self.intro_overlay.close()
        except Exception:
            pass

        if self.settings_dialog:
            try:
                self.settings_dialog.close()
            except Exception:
                pass

        try:
            self.audio_thread.stop()
            # Do NOT block with long wait in closeEvent
            self.audio_thread.wait(200)
        except Exception:
            pass

        try:
            keyboard.unhook_all()
        except Exception:
            pass

        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SymbioteNotch")

    app.aboutToQuit.connect(lambda: keyboard.unhook_all())

    # Step 1: Check if user-specific local storage file exists and contains a username
    username = get_stored_username()
    if not username:
        # First-time user setup: display sleek dark-themed dialog asking 'Set a username'
        dlg = UsernameDialog()
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            dlg.move(geo.x() + (geo.width() - dlg.width()) // 2,
                     geo.y() + (geo.height() - dlg.height()) // 2)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.chosen_username:
            username = dlg.chosen_username
        else:
            username = dlg.chosen_username or "Host"
        save_username(username)

    # Step 2: Initialize MainWindow with the username
    window = NotchMainWindow(username=username)
    # Force initial paint immediately
    window.show()
    window.raise_()
    QApplication.processEvents()

    # Step 3: Start Synced Cinematic Intro (Welcome -> Shatter -> Symbiote -> Notch)
    window.start_intro()

    sigint_timer = QTimer()
    sigint_timer.timeout.connect(lambda: None)
    sigint_timer.start(250)

    print(f"[INFO] Symbiote Desktop Notch running for user '{username}'.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
