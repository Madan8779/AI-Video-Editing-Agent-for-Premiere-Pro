from pathlib import Path
from PySide6.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QLabel, QFormLayout,
                               QHBoxLayout, QLineEdit, QPushButton, QFileDialog)


class SetupWizard(QWizard):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Maddy AI Video Editor")
        self.resize(700, 450)
        welcome = QWizardPage()
        welcome.setTitle("Set up your local editing workspace")
        layout = QVBoxLayout(welcome)
        text = QLabel("Import and analyze video locally, review proposed cuts, and save edit plans.\n\n"
                      "Your source files are preserved. Cloud upload is disabled. Premiere is optional "
                      "for analysis and requires a separately installed companion for connection.\n\n"
                      "This development preview does not enable automatic timeline changes or export.")
        text.setWordWrap(True)
        layout.addWidget(text)
        self.addPage(welcome)
        tools = QWizardPage()
        tools.setTitle("Choose local processing tools")
        form = QFormLayout(tools)
        self.fields = {}
        for key, label in (("ffmpeg", "FFmpeg executable"), ("ffprobe", "ffprobe executable")):
            row = QHBoxLayout()
            edit = QLineEdit(settings.get(key, ""))
            edit.setAccessibleName(label)
            browse = QPushButton("Browse…")
            browse.clicked.connect(lambda checked=False, e=edit: self.choose(e))
            row.addWidget(edit, 1)
            row.addWidget(browse)
            form.addRow(label, row)
            self.fields[key] = edit
        note = QLabel("Use executables from a trusted FFmpeg Windows distribution. You can finish "
                      "without them and configure Settings later; analysis will stay unavailable.\n\n"
                      "Offline speech models are optional and selected later in Settings.")
        note.setWordWrap(True)
        form.addRow(note)
        self.addPage(tools)
        ready = QWizardPage()
        ready.setTitle("Review connection prerequisites")
        box = QVBoxLayout(ready)
        info = QLabel("Premiere Pro 25.6 or later, a licensed installation, Creative Cloud Desktop, "
                      "and the Maddy UXP companion are needed for project inspection.\n\n"
                      "For development, load the companion using Adobe UXP Developer Tool. "
                      "Developer Mode is a manual Premiere preference.\n\n"
                      "The desktop header reports tools and free disk space. Import a video to select "
                      "its folder for local processing, then analyze and review your cuts.")
        info.setWordWrap(True)
        box.addWidget(info)
        self.addPage(ready)

    def choose(self, edit):
        value, _ = QFileDialog.getOpenFileName(self, "Select executable", "", "Executables (*.exe)")
        if value:
            edit.setText(value)

    def values(self):
        return {key: edit.text().strip() for key, edit in self.fields.items()}
