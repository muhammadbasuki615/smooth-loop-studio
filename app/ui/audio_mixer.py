"""Audio mixer panel."""

from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.audio_engine import AudioMixOptions, AudioTrack, PlaybackMode, SUPPORTED_AUDIO_FORMATS

from .widgets import DropList, GlassPanel, SectionTitle


class AudioMixerPanel(QWidget):
    tracks_changed = Signal(list)
    options_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tracks: List[AudioTrack] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Track list
        left = GlassPanel()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(14, 12, 14, 12)
        ll.addWidget(SectionTitle("Audio Tracks", "Drag & drop musik/ambience"))
        self.list = DropList(allowed_suffixes=SUPPORTED_AUDIO_FORMATS)
        self.list.files_dropped.connect(self._on_files_dropped)
        ll.addWidget(self.list, 1)

        btns = QHBoxLayout()
        b_add = QPushButton("Add")
        b_add.clicked.connect(self._browse)
        b_remove = QPushButton("Remove")
        b_remove.clicked.connect(self._remove_selected)
        b_clear = QPushButton("Clear")
        b_clear.clicked.connect(self._clear)
        btns.addWidget(b_add)
        btns.addWidget(b_remove)
        btns.addWidget(b_clear)
        ll.addLayout(btns)

        # Options
        right = GlassPanel()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 12, 14, 12)
        rl.addWidget(SectionTitle("Mix Options", "Behavior global audio"))
        form = QFormLayout()

        self.cb_mode = QComboBox()
        for m in PlaybackMode:
            self.cb_mode.addItem(m.value, m)

        self.cb_mute = QCheckBox("Mute audio asli video")
        self.cb_mute.setChecked(True)
        self.cb_replace = QCheckBox("Replace dengan musik di atas")
        self.cb_replace.setChecked(True)
        self.cb_normalize = QCheckBox("Loudness normalization")
        self.cb_normalize.setChecked(True)
        self.cb_ducking = QCheckBox("Ducking otomatis (sidechain)")

        self.sp_xfade = QDoubleSpinBox()
        self.sp_xfade.setRange(0.0, 30.0)
        self.sp_xfade.setSingleStep(0.5)
        self.sp_xfade.setValue(1.0)
        self.sp_xfade.setSuffix(" s")

        self.sp_sr = QSpinBox()
        self.sp_sr.setRange(8000, 192000)
        self.sp_sr.setValue(48000)

        self.cb_codec = QComboBox()
        self.cb_codec.addItems(["aac", "libmp3lame", "libopus", "flac"])
        self.cb_bitrate = QComboBox()
        self.cb_bitrate.addItems(["128k", "160k", "192k", "256k", "320k"])
        self.cb_bitrate.setCurrentText("192k")

        form.addRow("Mode", self.cb_mode)
        form.addRow("Crossfade", self.sp_xfade)
        form.addRow("Sample Rate", self.sp_sr)
        form.addRow("Codec", self.cb_codec)
        form.addRow("Bitrate", self.cb_bitrate)
        form.addRow(self.cb_mute)
        form.addRow(self.cb_replace)
        form.addRow(self.cb_normalize)
        form.addRow(self.cb_ducking)
        rl.addLayout(form)
        rl.addStretch(1)

        layout.addWidget(left, 1)
        layout.addWidget(right, 0)

        # change handlers
        for w in [self.cb_mode, self.sp_xfade, self.sp_sr, self.cb_codec, self.cb_bitrate,
                  self.cb_mute, self.cb_replace, self.cb_normalize, self.cb_ducking]:
            if hasattr(w, "stateChanged"):
                w.stateChanged.connect(self._emit_opts)
            elif hasattr(w, "valueChanged"):
                w.valueChanged.connect(self._emit_opts)
            elif hasattr(w, "currentIndexChanged"):
                w.currentIndexChanged.connect(self._emit_opts)

    # ---------------- ops ----------------

    def _browse(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add audio tracks", str(Path.home()),
            "Audio Files (*.mp3 *.wav *.flac *.aac *.ogg *.m4a *.opus);;All Files (*)",
        )
        if paths:
            self._on_files_dropped(paths)

    def _on_files_dropped(self, paths: List[str]) -> None:
        for p in paths:
            self._tracks.append(AudioTrack(path=Path(p)))
            QListWidgetItem(Path(p).name, self.list)
        self.tracks_changed.emit(list(self._tracks))

    def _remove_selected(self) -> None:
        for item in self.list.selectedItems():
            row = self.list.row(item)
            self.list.takeItem(row)
            if 0 <= row < len(self._tracks):
                del self._tracks[row]
        self.tracks_changed.emit(list(self._tracks))

    def _clear(self) -> None:
        self.list.clear()
        self._tracks.clear()
        self.tracks_changed.emit(list(self._tracks))

    def _emit_opts(self, *_: object) -> None:
        self.options_changed.emit(self.current_options())

    # ---------------- public ----------------

    def current_tracks(self) -> List[AudioTrack]:
        return list(self._tracks)

    def current_options(self) -> AudioMixOptions:
        return AudioMixOptions(
            target_duration=0.0,
            normalize=self.cb_normalize.isChecked(),
            crossfade_seconds=float(self.sp_xfade.value()),
            mode=PlaybackMode(self.cb_mode.currentData()),
            mute_video_audio=self.cb_mute.isChecked(),
            replace_video_audio=self.cb_replace.isChecked(),
            ducking=self.cb_ducking.isChecked(),
            sample_rate=int(self.sp_sr.value()),
            output_codec=self.cb_codec.currentText(),
            output_bitrate=self.cb_bitrate.currentText(),
        )
