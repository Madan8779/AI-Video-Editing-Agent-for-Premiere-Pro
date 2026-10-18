from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider


class Preview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.video = QVideoWidget()
        self.video.setMinimumHeight(230)
        layout.addWidget(self.video, 1)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.5)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.ranges = []
        self.range_index = 0
        self.pending_seek = None
        self.label = QLabel("Select a retained range to preview the source or reviewed edit.")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setAccessibleName("Source playback position")
        self.slider.sliderMoved.connect(self.seek_source)
        self.player.durationChanged.connect(lambda duration: self.slider.setRange(0, duration))
        self.player.positionChanged.connect(self.position_changed)
        self.player.mediaStatusChanged.connect(self.media_status)
        self.player.errorOccurred.connect(lambda error, message: self.label.setText("Preview unavailable: " + message))
        layout.addWidget(self.slider)
        controls = QHBoxLayout()
        play = QPushButton("Play / pause source")
        play.clicked.connect(self.toggle)
        stop = QPushButton("Stop")
        stop.clicked.connect(self.stop)
        controls.addWidget(play)
        controls.addWidget(stop)
        layout.addLayout(controls)

    def load(self, path):
        self.stop()
        self.player.setSource(QUrl.fromLocalFile(str(path)))

    def media_status(self, status):
        if status == QMediaPlayer.LoadedMedia and self.pending_seek is not None:
            self.player.setPosition(self.pending_seek)
            self.pending_seek = None

    def toggle(self):
        self.ranges = []
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def seek_source(self, position):
        self.ranges = []
        self.player.setPosition(position)

    def stop(self):
        self.ranges = []
        self.player.stop()

    def preview_ranges(self, ranges):
        self.ranges = [(round(c.start * 1000), round(c.end * 1000)) for c in ranges]
        self.range_index = 0
        if self.ranges:
            self.player.setPosition(self.ranges[0][0])
            self.label.setText("Reviewed edit playback • skips proposed cuts without changing the source")
            self.player.play()

    def position_changed(self, position):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        if self.ranges and position >= self.ranges[self.range_index][1]:
            self.range_index += 1
            if self.range_index >= len(self.ranges):
                self.stop()
                self.label.setText("Reviewed edit preview finished. Source file is unchanged.")
            else:
                self.player.setPosition(self.ranges[self.range_index][0])
