# Fixed PyQt5 Speech-to-Text App
# Requirements: pip install PyQt5 speechrecognition pyaudio pyperclip

import sys
import json
import os
import threading
import speech_recognition as sr
import pyperclip
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class SpeechApp(QMainWindow):
    # Signals for thread communication
    status_signal = pyqtSignal(str)
    text_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # Initialize variables
        self.is_recording = False
        self.settings_file = os.path.join(os.path.expanduser("~"), "speech_settings.json")
        self.settings = self.load_settings()
        
        # Initialize speech components
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.init_microphone()
        
        # Setup UI
        self.init_ui()
        
        # Connect signals
        self.status_signal.connect(self.update_status)
        self.text_signal.connect(self.add_text)
        
        print("✅ App initialized successfully")
        
    def load_settings(self):
        """Load settings safely"""
        defaults = {
            'language': 'en-US',
            'auto_copy': True,
            'always_on_top': False
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    saved = json.load(f)
                    return {**defaults, **saved}
        except:
            pass
        
        return defaults
    
    def save_settings(self):
        """Save settings safely"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            print("✅ Settings saved")
            return True
        except Exception as e:
            print(f"❌ Settings save failed: {e}")
            return False
    
    def init_microphone(self):
        """Initialize microphone"""
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("🎤 Microphone ready")
        except Exception as e:
            print(f"🎤 Microphone error: {e}")
    
    def init_ui(self):
        """Create the user interface"""
        self.setWindowTitle("🎙️ Speech AI")
        self.setFixedSize(360, 450)
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background: #1e1e1e;
                border-radius: 12px;
            }
            QWidget {
                background: #1e1e1e;
                color: white;
                font-family: 'Segoe UI';
            }
        """)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title bar
        self.create_title_bar(layout)
        
        # Status
        self.status_label = QLabel("Ready to record")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background: rgba(0, 123, 255, 0.2);
                border: 1px solid #007bff;
                border-radius: 8px;
                padding: 10px;
                color: #007bff;
                font-weight: 500;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Record button
        self.record_btn = QPushButton("🎙️")
        self.record_btn.setFixedSize(70, 70)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #28a745, stop:1 #20c997);
                border: none;
                border-radius: 35px;
                color: white;
                font-size: 28px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #218838, stop:1 #1c7431);
            }
        """)
        
        # Center record button
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.addStretch()
        btn_layout.addWidget(self.record_btn)
        btn_layout.addStretch()
        layout.addWidget(btn_container)
        
        # Control buttons
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        
        self.stop_btn = QPushButton("⏹️")
        self.stop_btn.setFixedSize(45, 35)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover:enabled {
                background: #5a6268;
            }
            QPushButton:disabled {
                background: #495057;
                color: #adb5bd;
            }
        """)
        controls_layout.addWidget(self.stop_btn)
        
        clear_btn = QPushButton("🗑️")
        clear_btn.setFixedSize(45, 35)
        clear_btn.clicked.connect(self.clear_text)
        clear_btn.setStyleSheet(self.get_button_style())
        controls_layout.addWidget(clear_btn)
        
        copy_btn = QPushButton("📋")
        copy_btn.setFixedSize(45, 35)
        copy_btn.clicked.connect(self.copy_text)
        copy_btn.setStyleSheet(self.get_button_style())
        controls_layout.addWidget(copy_btn)
        
        controls_layout.addStretch()
        layout.addWidget(controls)
        
        # Text area
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("Transcribed text appears here...")
        self.text_area.setStyleSheet("""
            QTextEdit {
                background: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 12px;
                color: white;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: 1px solid #007bff;
            }
        """)
        self.text_area.textChanged.connect(self.update_word_count)
        layout.addWidget(self.text_area)
        
        # Bottom bar
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        
        self.word_count = QLabel("0 words")
        self.word_count.setStyleSheet("color: #adb5bd; font-size: 11px;")
        bottom_layout.addWidget(self.word_count)
        
        bottom_layout.addStretch()
        
        # Settings button
        settings_btn = QPushButton("⚙️")
        settings_btn.setFixedSize(30, 30)
        settings_btn.clicked.connect(self.show_settings)
        settings_btn.setStyleSheet(self.get_small_button_style())
        bottom_layout.addWidget(settings_btn)
        
        layout.addWidget(bottom)
        
        # Apply settings
        if self.settings.get('always_on_top'):
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()
        
        self.center_window()
    
    def create_title_bar(self, layout):
        """Create title bar"""
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("🎙️ Speech AI")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: white;")
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        # Window controls
        min_btn = QPushButton("—")
        min_btn.setFixedSize(25, 25)
        min_btn.clicked.connect(self.showMinimized)
        min_btn.setStyleSheet(self.get_small_button_style())
        title_layout.addWidget(min_btn)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(25, 25)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c82333;
            }
        """)
        title_layout.addWidget(close_btn)
        
        layout.addWidget(title_bar)
    
    def get_button_style(self):
        """Standard button style"""
        return """
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """
    
    def get_small_button_style(self):
        """Small button style"""
        return """
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                color: white;
                font-size: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """
    
    def toggle_recording(self):
        """Toggle recording state"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        """Start recording"""
        if not self.microphone:
            self.status_signal.emit("❌ Microphone not available")
            return
        
        self.is_recording = True
        self.record_btn.setText("🔴")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #dc3545, stop:1 #c82333);
                border: none;
                border-radius: 35px;
                color: white;
                font-size: 28px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #c82333, stop:1 #bd2130);
            }
        """)
        self.stop_btn.setEnabled(True)
        self.status_signal.emit("🎙️ Recording... Speak now!")
        
        # Start recording in thread
        threading.Thread(target=self.record_worker, daemon=True).start()
    
    def stop_recording(self):
        """Stop recording"""
        self.is_recording = False
        self.record_btn.setText("🎙️")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #28a745, stop:1 #20c997);
                border: none;
                border-radius: 35px;
                color: white;
                font-size: 28px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                           stop:0 #218838, stop:1 #1c7431);
            }
        """)
        self.stop_btn.setEnabled(False)
        self.status_signal.emit("✅ Recording stopped")
    
    def record_worker(self):
        """Recording worker thread"""
        while self.is_recording:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=8)
                
                if not self.is_recording:
                    break
                
                self.status_signal.emit("🔄 Processing...")
                
                text = self.recognizer.recognize_google(audio, language=self.settings.get('language', 'en-US'))
                
                if text.strip():
                    self.text_signal.emit(text)
                    
                    if self.settings.get('auto_copy'):
                        QTimer.singleShot(100, self.copy_text)
                
                if self.is_recording:
                    self.status_signal.emit("🎙️ Continue speaking...")
                    
            except sr.WaitTimeoutError:
                if self.is_recording:
                    self.status_signal.emit("🎙️ Listening...")
                continue
            except sr.UnknownValueError:
                if self.is_recording:
                    self.status_signal.emit("🎙️ Didn't catch that...")
                continue
            except Exception as e:
                self.status_signal.emit(f"❌ Error: {str(e)}")
                break
        
        # Reset UI when done
        QTimer.singleShot(0, self.stop_recording)
    
    def clear_text(self):
        """Clear text area"""
        self.text_area.clear()
        self.status_signal.emit("🗑️ Text cleared")
    
    def copy_text(self):
        """Copy text to clipboard"""
        text = self.text_area.toPlainText()
        if text.strip():
            pyperclip.copy(text)
            self.status_signal.emit("📋 Copied!")
        else:
            self.status_signal.emit("❌ No text to copy")
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(message)
    
    def add_text(self, text):
        """Add text to text area"""
        current = self.text_area.toPlainText()
        new_text = f"{current} {text}".strip() if current else text
        self.text_area.setPlainText(new_text)
        
        # Move cursor to end
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.text_area.setTextCursor(cursor)
    
    def update_word_count(self):
        """Update word count"""
        text = self.text_area.toPlainText()
        words = len(text.split()) if text.strip() else 0
        self.word_count.setText(f"{words} words")
    
    def show_settings(self):
        """Show settings dialog"""
        try:
            dialog = SettingsDialog(self.settings, self)
            if dialog.exec_() == QDialog.Accepted:
                new_settings = dialog.get_settings()
                
                # Check for always on top change
                old_on_top = self.settings.get('always_on_top', False)
                new_on_top = new_settings.get('always_on_top', False)
                
                self.settings.update(new_settings)
                
                if self.save_settings():
                    self.status_signal.emit("⚙️ Settings saved!")
                    
                    # Apply always on top
                    if old_on_top != new_on_top:
                        if new_on_top:
                            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
                        else:
                            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
                        self.show()
                else:
                    self.status_signal.emit("❌ Settings save failed")
        except Exception as e:
            print(f"Settings error: {e}")
    
    def center_window(self):
        """Center window on screen"""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)
    
    def mousePressEvent(self, event):
        """Enable dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos()
    
    def mouseMoveEvent(self, event):
        """Handle dragging"""
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_position'):
            delta = QPoint(event.globalPos() - self.drag_position)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.drag_position = event.globalPos()
    
    def closeEvent(self, event):
        """Handle app close"""
        self.is_recording = False
        self.save_settings()
        event.accept()

class SettingsDialog(QDialog):
    """Simple settings dialog"""
    
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.init_ui()
    
    def init_ui(self):
        """Create settings UI"""
        self.setWindowTitle("Settings")
        self.setFixedSize(300, 200)
        self.setModal(True)
        
        self.setStyleSheet("""
            QDialog {
                background: #2d2d2d;
                color: white;
            }
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #666;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background: #007bff;
                border: 2px solid #007bff;
            }
            QPushButton {
                background: #007bff;
                border: none;
                border-radius: 6px;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("⚙️ Settings")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Settings
        self.auto_copy_cb = QCheckBox("📋 Auto-copy to clipboard")
        self.auto_copy_cb.setChecked(self.settings.get('auto_copy', True))
        layout.addWidget(self.auto_copy_cb)
        
        self.always_on_top_cb = QCheckBox("📌 Always on top")
        self.always_on_top_cb.setChecked(self.settings.get('always_on_top', False))
        layout.addWidget(self.always_on_top_cb)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        # Center on parent
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)
    
    def get_settings(self):
        """Get updated settings"""
        return {
            'auto_copy': self.auto_copy_cb.isChecked(),
            'always_on_top': self.always_on_top_cb.isChecked(),
            'language': self.settings.get('language', 'en-US')
        }

def main():
    """Main function"""
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # Check for required modules
        try:
            import speech_recognition
            import pyaudio
            import pyperclip
        except ImportError as e:
            QMessageBox.critical(None, "Missing Module", f"Please install required module:\n\n{e}\n\nRun: pip install {str(e).split()[-1]}")
            return
        
        window = SpeechApp()
        window.show()
        
        print("🚀 Speech AI started!")
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        if 'app' in locals():
            QMessageBox.critical(None, "Error", f"Failed to start:\n\n{e}")

if __name__ == "__main__":
    main()