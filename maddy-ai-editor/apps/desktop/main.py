import argparse
import json
import os
import shutil
import socket
import sys
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QComboBox, QFrame, QSplitter, QTabWidget,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QMessageBox, QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox)

from apps.desktop.theme import STYLE
from apps.desktop.preview import Preview
from apps.desktop.onboarding import SetupWizard
from services.agent.jobs import JobQueue
from services.agent.models import Preset, EditPlan, create_plan, to_edl, to_srt, retime_transcript
from services.agent.bridge import BridgeState, create_app
from services.agent.security import PathPolicy
from services.media.engine import MediaEngine, Cancelled
from services.media.transcription import transcribe_local


def data_dir():
    root = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "MaddyAIEditor"
    root.mkdir(parents=True, exist_ok=True)
    return root


def load_settings(path):
    try:
        settings = json.loads(path.read_text(encoding="utf-8-sig"))
        return settings if isinstance(settings, dict) else {}
    except (OSError, ValueError):
        return {}


class Worker(QObject):
    progress = Signal(int, str)
    result = Signal(object)
    failed = Signal(str)
    done = Signal()

    def __init__(self, engine, source, preset, cancel, model="", language="en"):
        super().__init__()
        self.engine, self.source, self.preset = engine, source, preset
        self.cancel, self.model, self.language = cancel, model, language

    def run(self):
        try:
            self.progress.emit(5, "Inspecting video streams")
            info = self.engine.probe(self.source, self.cancel)
            silences, scenes = self.engine.analyze(info, self.cancel, self.progress.emit)
            plan = create_plan(info, silences, self.preset)
            transcript = []
            if self.model:
                self.progress.emit(96, "Transcribing with your local model")
                transcript = transcribe_local(self.source, self.model, self.language, self.cancel)
            if self.cancel.is_set():
                raise Cancelled("Job cancelled")
            self.result.emit((info, silences, scenes, plan, transcript))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.done.emit()


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing settings")
        self.resize(650, 320)
        layout = QFormLayout(self)
        self.fields = {}
        for key, label in (("ffmpeg", "FFmpeg executable"), ("ffprobe", "ffprobe executable"),
                           ("model", "Offline model folder")):
            row = QHBoxLayout()
            edit = QLineEdit(settings.get(key, ""))
            edit.setAccessibleName(label)
            button = QPushButton("Browse…")
            button.clicked.connect(lambda checked=False, k=key, e=edit: self.choose(k, e))
            row.addWidget(edit, 1)
            row.addWidget(button)
            self.fields[key] = edit
            layout.addRow(label, row)
        note = QLabel("Models are used locally. No model is downloaded automatically.\nCloud transcription is not enabled in this build.")
        note.setWordWrap(True)
        layout.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def choose(self, key, edit):
        value = (QFileDialog.getExistingDirectory(self, "Select local model") if key == "model" else
                 QFileDialog.getOpenFileName(self, "Select executable", "", "Executables (*.exe)")[0])
        if value:
            edit.setText(value)

    def values(self):
        return {key: edit.text().strip() for key, edit in self.fields.items()}


class MainWindow(QMainWindow):
    def __init__(self, settings_path=None, start_bridge=True):
        super().__init__()
        self.setWindowTitle("Maddy AI Video Editor")
        self.resize(1320, 880)
        self.setMinimumSize(1000, 700)
        self.settings_path = Path(settings_path) if settings_path else data_dir() / "settings.json"
        self.settings = load_settings(self.settings_path)
        self.engine = MediaEngine(self.settings.get("ffmpeg", ""), self.settings.get("ffprobe", ""))
        self.bridge = BridgeState(self.engine)
        self.server = None
        self.server_thread = None
        self.thread = None
        self.cancel = threading.Event()
        self.source, self.plan, self.info = None, None, None
        self.transcript = []
        self.queue = JobQueue(self.settings_path.parent / "jobs.json")
        self.active_job_id = None
        self.queue_running = False
        self._updating = False
        self._build_ui()
        self.preflight()
        self.refresh_queue()
        if start_bridge:
            self.start_bridge()
            if not self.settings.get("onboarded"):
                QTimer.singleShot(250, self.onboard)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_connection)
        self.timer.start(2000)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(26, 22, 26, 16)
        layout.setSpacing(16)
        top = QHBoxLayout()
        title = QVBoxLayout()
        eyebrow = QLabel("YOUR FOOTAGE. YOUR FINAL SAY.")
        eyebrow.setObjectName("eyebrow")
        brand = QLabel("Maddy AI Video Editor")
        brand.setObjectName("brand")
        subtitle = QLabel("Local analysis  /  Reviewable cuts  /  Premiere companion")
        subtitle.setObjectName("subtitle")
        title.addWidget(eyebrow)
        title.addWidget(brand)
        title.addWidget(subtitle)
        top.addLayout(title, 1)
        self.connection = QLabel("Premiere • disconnected")
        top.addWidget(self.connection)
        settings = QPushButton("Settings")
        settings.clicked.connect(self.open_settings)
        top.addWidget(settings)
        layout.addLayout(top)
        self.preflight_label = QLabel()
        self.preflight_label.setWordWrap(True)
        self.preflight_label.setObjectName("subtitle")
        layout.addWidget(self.preflight_label)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)
        left = QFrame()
        left.setObjectName("card")
        left.setMinimumWidth(290)
        left.setMaximumWidth(390)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(20, 22, 20, 20)
        ll.setSpacing(14)
        label = QLabel("01  Source & workflow")
        label.setObjectName("cardTitle")
        ll.addWidget(label)
        self.import_button = QPushButton("＋  Import video")
        self.import_button.clicked.connect(self.import_media)
        ll.addWidget(self.import_button)
        self.source_label = QLabel("Choose a local video to begin.\nMP4 · MOV · MKV · AVI · WebM")
        self.source_label.setWordWrap(True)
        self.source_label.setObjectName("subtitle")
        ll.addWidget(self.source_label)
        ll.addWidget(QLabel("Editing preset"))
        self.preset = QComboBox()
        self.preset.addItems([p.value for p in Preset])
        self.preset.setAccessibleName("Editing preset")
        ll.addWidget(self.preset)
        ll.addWidget(QLabel("Transcript language"))
        self.language = QComboBox()
        for name, code in (("English", "en"), ("Kannada", "kn"), ("Auto detect", "auto")):
            self.language.addItem(name, code)
        self.language.setAccessibleName("Transcript language")
        ll.addWidget(self.language)
        self.transcribe_check = QCheckBox("Transcribe with local model")
        ll.addWidget(self.transcribe_check)
        self.analyze_button = QPushButton("Analyze & propose cuts")
        self.analyze_button.setObjectName("primary")
        self.analyze_button.setEnabled(False)
        self.analyze_button.clicked.connect(self.analyze)
        ll.addWidget(self.analyze_button)
        self.cancel_button = QPushButton("Cancel job")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel.set)
        ll.addWidget(self.cancel_button)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        ll.addWidget(self.progress)
        self.job_label = QLabel("Ready to import")
        self.job_label.setWordWrap(True)
        ll.addWidget(self.job_label)
        ll.addStretch()
        privacy = QLabel("LOCAL BY DEFAULT\nYour source files stay untouched.\nAll proposed cuts need your review.")
        privacy.setObjectName("subtitle")
        privacy.setWordWrap(True)
        ll.addWidget(privacy)
        splitter.addWidget(left)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        self.summary = QLabel("02  Review your edit")
        self.summary.setObjectName("cardTitle")
        rl.addWidget(self.summary)
        self.metadata = QLabel("Media details and cut suggestions will appear after analysis.")
        self.metadata.setWordWrap(True)
        self.metadata.setObjectName("subtitle")
        rl.addWidget(self.metadata)
        self.tabs = QTabWidget()
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Source in (s)", "Source out (s)", "Confidence", "Why keep this range"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellChanged.connect(self.range_changed)
        self.table.setAccessibleName("Editable retained source ranges")
        self.tabs.addTab(self.table, "Cut review")
        self.json_editor = QPlainTextEdit()
        self.json_editor.setPlaceholderText("Your structured edit plan will appear here. You can edit and validate it before saving.")
        self.json_editor.setAccessibleName("Editable JSON edit plan")
        self.tabs.addTab(self.json_editor, "JSON plan")
        self.transcript_editor = QPlainTextEdit()
        self.transcript_editor.setReadOnly(True)
        self.transcript_editor.setPlaceholderText("Enable local transcription and select an existing model in Settings to generate timestamped captions.")
        self.tabs.addTab(self.transcript_editor, "Transcript")
        preview_page = QWidget()
        preview_layout = QVBoxLayout(preview_page)
        self.preview = Preview()
        preview_layout.addWidget(self.preview, 1)
        preview_button = QPushButton("Preview reviewed edit")
        preview_button.clicked.connect(self.preview_plan)
        preview_layout.addWidget(preview_button)
        self.tabs.addTab(preview_page, "Preview")
        queue_page = QWidget()
        queue_layout = QVBoxLayout(queue_page)
        self.queue_table = QTableWidget(0, 3)
        self.queue_table.setHorizontalHeaderLabels(["Video", "Status", "Details"])
        self.queue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.queue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.queue_table.cellDoubleClicked.connect(self.review_job)
        queue_layout.addWidget(self.queue_table)
        queue_actions = QHBoxLayout()
        add_jobs = QPushButton("Add videos…")
        add_jobs.clicked.connect(self.add_jobs)
        run_jobs = QPushButton("Run queue")
        run_jobs.clicked.connect(self.run_queue)
        queue_actions.addWidget(add_jobs)
        queue_actions.addWidget(run_jobs)
        retry_jobs = QPushButton("Retry selected")
        retry_jobs.clicked.connect(self.retry_job)
        queue_actions.addWidget(retry_jobs)
        queue_layout.addLayout(queue_actions)
        self.tabs.addTab(queue_page, "Job queue")
        self.activity = QPlainTextEdit()
        self.activity.setReadOnly(True)
        self.activity.document().setMaximumBlockCount(1000)
        self.tabs.addTab(self.activity, "Activity")
        rl.addWidget(self.tabs, 1)
        actions = QHBoxLayout()
        for label, callback in (("Validate plan", self.validate_current), ("Save JSON", self.save_json),
                                ("Export EDL", self.save_edl), ("Save SRT", self.save_srt)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        rl.addLayout(actions)
        bottom = QHBoxLayout()
        connect = QPushButton("Connect Premiere…")
        connect.clicked.connect(self.connect_instructions)
        bottom.addWidget(connect)
        apply = QPushButton("Apply in Premiere • awaiting verification")
        apply.setEnabled(False)
        apply.setToolTip("Enabled only after UXP timeline and recovery tests pass in Premiere.")
        bottom.addWidget(apply, 1)
        rl.addLayout(bottom)
        splitter.addWidget(right)
        splitter.setSizes([330, 940])
        self.statusBar().showMessage("Sources are preserved · No cloud upload · v0.1 development build")

    def log(self, message):
        self.activity.appendPlainText(f"{datetime.now():%H:%M:%S}  {message}")

    def preflight(self):
        tools = self.engine.tools()
        premiere = Path("C:/Program Files/Adobe/Adobe Premiere Pro 2026/Adobe Premiere Pro.exe").is_file()
        free = shutil.disk_usage(self.settings_path.parent).free / 1024**3
        self.preflight_label.setText(
            f"Setup check   •   Premiere {'installed; plugin check pending' if premiere else 'not detected'}   •   "
            f"FFmpeg {'ready' if tools['ffmpeg'] else 'missing'}   •   ffprobe {'ready' if tools['ffprobe'] else 'missing'}   •   "
            f"{free:.1f} GB free   •   Offline model {'selected' if self.settings.get('model') else 'not selected'}")
        self.log("Setup checks refreshed")

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.Accepted:
            self.settings.update(dialog.values())
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
            self.engine = MediaEngine(self.settings["ffmpeg"], self.settings["ffprobe"])
            self.bridge.engine = self.engine
            self.preflight()

    def onboard(self):
        wizard = SetupWizard(self.settings, self)
        if wizard.exec() == QDialog.Accepted:
            self.settings.update(wizard.values())
            self.settings["onboarded"] = True
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
            self.engine = MediaEngine(self.settings.get("ffmpeg", ""), self.settings.get("ffprobe", ""))
            self.bridge.engine = self.engine
            self.preflight()

    def import_media(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import source video", "", "Video (*.mp4 *.mov *.mkv *.avi *.webm)")
        if path:
            self.set_source(path)

    def set_source(self, path):
        source = Path(path).resolve(strict=True)
        if not source.is_file():
            raise ValueError("Select a video file")
        self.source = source
        self.preview.load(source)
        self.bridge.policy = PathPolicy([source.parent])
        self.plan, self.info, self.transcript = None, None, []
        self.json_editor.clear()
        self.table.setRowCount(0)
        self.transcript_editor.clear()
        self.source_label.setText(source.name + "\n" + str(source.parent))
        self.analyze_button.setEnabled(True)
        self.metadata.setText("Ready for local analysis.")
        self.job_label.setText("Queued • " + source.name)
        self.progress.setValue(0)
        self.log("Imported " + source.name)

    def analyze(self):
        if self.thread or not self.source:
            return
        if self.transcribe_check.isChecked() and not self.settings.get("model"):
            self.show_error("Select an existing offline model folder in Settings first.")
            return
        self.cancel = threading.Event()
        self.thread = QThread(self)
        self.worker = Worker(self.engine, self.source, Preset(self.preset.currentText()), self.cancel,
                             self.settings.get("model", "") if self.transcribe_check.isChecked() else "",
                             self.language.currentData())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.result.connect(self.on_result)
        self.worker.failed.connect(self.job_failed)
        self.worker.done.connect(self.thread.quit)
        self.worker.done.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.job_finished)
        self.thread.finished.connect(self.thread.deleteLater)
        self.import_button.setEnabled(False)
        self.analyze_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.thread.start()

    def on_progress(self, value, message):
        self.progress.setValue(value)
        self.job_label.setText(message)
        self.log(message)

    def on_result(self, result):
        self.info, silences, scenes, self.plan, self.transcript = result
        self.refresh_plan()
        self.metadata.setText(f"{self.info.width} × {self.info.height}   •   {self.info.fps:.3f} fps   •   "
                              f"{self.info.video_codec.upper()}   •   {len(silences)} silent intervals   •   {len(scenes)} scene boundaries")
        self.transcript_editor.setPlainText(to_srt(self.transcript) if self.transcript else
                                           "No transcript generated. Silence analysis does not recognize words.")
        self.progress.setValue(100)
        self.job_label.setText("Complete • review suggested cuts")
        self.log("Analysis complete. Original media was not modified.")
        if self.active_job_id:
            output_dir = self.settings_path.parent / "plans"
            output_dir.mkdir(parents=True, exist_ok=True)
            output = output_dir / (self.active_job_id + ".json")
            output.write_text(self.plan.model_dump_json(indent=2), encoding="utf-8")
            if self.transcript:
                output.with_suffix("srt").write_text(to_srt(retime_transcript(self.transcript, self.plan)), encoding="utf-8")
            self.queue.update(self.active_job_id, "complete", str(output))
            self.refresh_queue()

    def job_failed(self, message):
        self.job_label.setText(message)
        self.log(message)
        if self.active_job_id:
            self.queue.update(self.active_job_id, "cancelled" if self.cancel.is_set() else "failed", message[:500])
            self.refresh_queue()
        if not self.cancel.is_set():
            self.show_error(message)

    def job_finished(self):
        self.thread = None
        self.active_job_id = None
        self.import_button.setEnabled(True)
        self.analyze_button.setEnabled(bool(self.source))
        self.cancel_button.setEnabled(False)
        if self.cancel.is_set():
            self.queue_running = False
        if self.queue_running:
            QTimer.singleShot(100, self.run_queue)

    def refresh_queue(self):
        self.queue_table.setRowCount(len(self.queue.jobs))
        for i, job in enumerate(self.queue.jobs):
            for col, text in enumerate((Path(job["source"]).name, job["status"], job.get("message", ""))):
                self.queue_table.setItem(i, col, QTableWidgetItem(text))

    def add_jobs(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Queue local videos", "", "Video (*.mp4 *.mov *.mkv *.avi *.webm)")
        for file in files:
            self.queue.add(file, self.preset.currentText())
        self.refresh_queue()

    def retry_job(self):
        row = self.queue_table.currentRow()
        if row >= 0 and self.queue.jobs[row]["status"] in ("failed", "cancelled", "interrupted"):
            self.queue.update(self.queue.jobs[row]["id"], "queued", "Queued for retry")
            self.refresh_queue()

    def review_job(self, row, column):
        if self.thread:
            return
        job = self.queue.jobs[row]
        if job["status"] != "complete":
            return
        try:
            plan = EditPlan.model_validate_json(Path(job["message"]).read_text(encoding="utf-8"))
            self.set_source(plan.source_path)
            self.info = self.engine.probe(self.source)
            self.plan = plan
            self.refresh_plan()
            self.tabs.setCurrentIndex(0)
        except (OSError, ValueError, RuntimeError) as exc:
            self.show_error(str(exc))

    def run_queue(self):
        if self.thread:
            return
        job = self.queue.next()
        if not job:
            self.queue_running = False
            return
        if self.transcribe_check.isChecked() and not self.settings.get("model"):
            self.show_error("Select a model or disable transcription before running the queue.")
            return
        try:
            self.set_source(job["source"])
        except (OSError, ValueError) as exc:
            self.queue.update(job["id"], "failed", str(exc))
            self.refresh_queue()
            QTimer.singleShot(100, self.run_queue)
            return
        self.preset.setCurrentText(job["preset"])
        self.active_job_id = job["id"]
        self.queue.update(job["id"], "running", "Processing locally")
        self.queue_running = True
        self.refresh_queue()
        self.analyze()

    def preview_plan(self):
        try:
            self.preview.preview_ranges(self.current_plan().keeps)
        except ValueError as exc:
            self.show_error(str(exc))

    def refresh_plan(self):
        self._updating = True
        self.table.setRowCount(len(self.plan.keeps))
        for row, cut in enumerate(self.plan.keeps):
            for col, value in enumerate((f"{cut.start:.3f}", f"{cut.end:.3f}", f"{cut.confidence:.2f}", cut.rationale)):
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.json_editor.setPlainText(self.plan.model_dump_json(indent=2))
        self.summary.setText(f"02  Review your edit   •   {self.plan.source_duration:.1f}s → {self.plan.output_duration:.1f}s")
        self._updating = False

    def range_changed(self, row, column):
        if self._updating or not self.plan:
            return
        try:
            data = self.plan.model_dump()
            for i in range(self.table.rowCount()):
                data["keeps"][i] = {"start": float(self.table.item(i, 0).text()),
                    "end": float(self.table.item(i, 1).text()), "confidence": float(self.table.item(i, 2).text()),
                    "rationale": self.table.item(i, 3).text()}
            self.plan = EditPlan.model_validate(data)
            self.refresh_plan()
        except (ValueError, AttributeError) as exc:
            self.show_error(str(exc))
            self.refresh_plan()

    def current_plan(self):
        plan = EditPlan.model_validate_json(self.json_editor.toPlainText())
        if not self.source or Path(plan.source_path).resolve() != self.source:
            raise ValueError("Plan source must match the imported video")
        if not self.info or abs(plan.source_duration - self.info.duration) > 0.001 or abs(plan.fps - self.info.fps) > 0.001:
            raise ValueError("Plan duration and frame rate must match the inspected source")
        return plan

    def validate_current(self):
        try:
            self.plan = self.current_plan()
            self.refresh_plan()
            self.log("Plan valid • " + self.plan.digest()[:12])
            self.statusBar().showMessage("Plan validated. Review retained ranges before interchange.")
        except ValueError as exc:
            self.show_error(str(exc))

    def save_text(self, title, extension, text):
        default = str(self.source.with_name(self.source.stem + ".maddy." + extension)) if self.source else "maddy." + extension
        path, _ = QFileDialog.getSaveFileName(self, title, default, f"{extension.upper()} (*.{extension})")
        if path:
            if Path(path).suffix.lower() != "." + extension:
                path += "." + extension
            if self.source and Path(path).resolve() == self.source:
                raise ValueError("Cannot overwrite source media")
            Path(path).write_text(text, encoding="utf-8")
            self.log("Saved " + Path(path).name)

    def save_json(self):
        try:
            self.save_text("Save reviewed edit plan", "json", self.current_plan().model_dump_json(indent=2))
        except (ValueError, OSError) as exc:
            self.show_error(str(exc))

    def save_edl(self):
        try:
            self.save_text("Export EDL for manual Premiere import", "edl", to_edl(self.current_plan()))
        except (ValueError, OSError) as exc:
            self.show_error(str(exc))

    def save_srt(self):
        try:
            if not self.transcript:
                raise ValueError("Generate a local transcript first. No caption text is invented.")
            self.save_text("Save captions timed to reviewed edit", "srt",
                           to_srt(retime_transcript(self.transcript, self.current_plan())))
        except (ValueError, OSError) as exc:
            self.show_error(str(exc))

    def start_bridge(self):
        import uvicorn
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if os.name == "nt":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("127.0.0.1", 8765))
            sock.listen(16)
            self.server = uvicorn.Server(uvicorn.Config(create_app(self.bridge), host="127.0.0.1", port=8765,
                log_level="warning", access_log=False, log_config=None, limit_concurrency=8, timeout_keep_alive=5))
            self.server_thread = threading.Thread(target=self.server.run, kwargs={"sockets": [sock]}, daemon=True)
            self.server_thread.start()
            self.log("Authenticated local bridge listening on 127.0.0.1:8765")
        except OSError:
            sock.close()
            self.server = None
            self.log("Bridge port unavailable; close another app instance. Offline analysis is available.")

    def refresh_connection(self):
        state = self.bridge.connection()
        if state["connected"]:
            inspection = state["inspection"]
            self.connection.setText("Premiere • " + (inspection["project_name"] or "no open project"))
        else:
            self.connection.setText("Premiere • disconnected")

    def connect_instructions(self):
        if not self.server:
            self.show_error("Local bridge is unavailable. Check Activity and restart the app.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Connect the Premiere UXP companion")
        dialog.resize(640, 300)
        layout = QVBoxLayout(dialog)
        text = QLabel("1. Load integrations/premiere_uxp/manifest.json in Adobe UXP Developer Tool.\n"
                      "2. In Premiere, open Window > UXP Plugins > Maddy Companion.\n"
                      "3. Paste this session key and connect. It expires when this app closes.\n\n"
                      "Project inspection only. Timeline edits remain gated pending real-host QA.")
        text.setWordWrap(True)
        layout.addWidget(text)
        key = QLineEdit(self.bridge.token)
        key.setReadOnly(True)
        key.setEchoMode(QLineEdit.Password)
        layout.addWidget(key)
        copy = QPushButton("Copy session key")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.bridge.token))
        layout.addWidget(copy)
        done = QDialogButtonBox(QDialogButtonBox.Close)
        done.rejected.connect(dialog.reject)
        layout.addWidget(done)
        dialog.exec()

    def show_error(self, message):
        QMessageBox.warning(self, "Action needs attention", message[:1800])

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.cancel.set()
            self.job_label.setText("Cancelling job before close. Close again when it stops.")
            event.ignore()
            return
        if self.server:
            self.server.should_exit = True
        self.preview.stop()
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--screenshot")
    parser.add_argument("--settings", help="Optional settings file for portable/dev runs")
    parser.add_argument("--smoke-media", help="Analyze a fixture before taking the smoke screenshot")
    parser.add_argument("--smoke-transcribe", action="store_true", help="Exercise selected local model in fixture smoke")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow(settings_path=args.settings, start_bridge=not args.smoke)
    window.show()
    if args.smoke:
        def capture():
            exit_code = 0
            if args.smoke_transcribe and not window.transcript:
                exit_code = 3
            if args.screenshot:
                Path(args.screenshot).parent.mkdir(parents=True, exist_ok=True)
                window.grab().save(args.screenshot)
                report = {"analysis_complete": bool(window.plan),
                          "output_duration": window.plan.output_duration if window.plan else None,
                          "transcript": [segment.model_dump() for segment in window.transcript]}
                Path(args.screenshot).with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            window.close()
            app.exit(exit_code)
        if args.smoke_media:
            window.set_source(args.smoke_media)
            window.transcribe_check.setChecked(args.smoke_transcribe)
            def smoke_error(message):
                window.log(message)
                if window.thread:
                    window.thread.quit()
                QTimer.singleShot(500, lambda: app.exit(1))
            window.show_error = smoke_error
            def analyze_and_capture():
                window.analyze()
                window.smoke_timer = QTimer(window)
                def poll_finished():
                    if window.plan and window.thread is None:
                        window.smoke_timer.stop()
                        capture()
                window.smoke_timer.timeout.connect(poll_finished)
                window.smoke_timer.start(100)
            QTimer.singleShot(200, analyze_and_capture)
            QTimer.singleShot(120000, lambda: app.exit(2))
        else:
            QTimer.singleShot(1500, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
