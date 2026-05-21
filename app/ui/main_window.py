"""Main window: hosts all panels and the render pipeline."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.core.config import AppConfig, load_config, save_config
from app.core.export_engine import ExportEngine, RenderJob, RenderQueue, RenderStatus
from app.core.ffmpeg_utils import FFmpeg, detect_gpu
from app.core.loop_engine import LoopOptions
from app.core.plugin_api import PluginManager
from app.core.project import Project, ProjectIO

from .ai_tools_panel import AIToolsPanel
from .audio_mixer import AudioMixerPanel
from .dashboard import DashboardPanel
from .export_panel import ExportPanel
from .overlay_manager import OverlayManagerPanel
from .plugin_manager_panel import PluginManagerPanel
from .render_queue_panel import RenderQueuePanel
from .settings_panel import SettingsPanel
from .timeline import TimelinePanel
from .video_editor import VideoEditorPanel


class MainWindow(QMainWindow):
    job_updated = Signal(object)

    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()
        self.config = config or load_config()
        self.setWindowTitle(f"{self.config.app.name} v{self.config.app.version}")
        self.resize(*self.config.ui.window_size)

        self.ffmpeg = FFmpeg(local_bin_dir=self.config.abs_path("ffmpeg_bin"))
        self.gpu = detect_gpu(self.ffmpeg)
        self.export_engine = ExportEngine(self.ffmpeg, temp_dir=self.config.abs_path("temp"), gpu_info=self.gpu)
        self.queue = RenderQueue(self.export_engine)
        self.queue.add_listener(self._on_job_update)

        self.plugins = PluginManager(self.config.abs_path("plugins"))
        self.plugins.load_all()

        # Panels
        self.dashboard = DashboardPanel()
        self.video_editor = VideoEditorPanel()
        self.audio_mixer = AudioMixerPanel()
        self.overlay_manager = OverlayManagerPanel()
        self.timeline = TimelinePanel()
        self.export_panel = ExportPanel()
        self.ai_tools = AIToolsPanel()
        self.render_queue_panel = RenderQueuePanel()
        self.plugins_panel = PluginManagerPanel(self.plugins)
        self.settings_panel = SettingsPanel(self.config)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.video_editor, "Video Editor")
        self.tabs.addTab(self.audio_mixer, "Audio Mixer")
        self.tabs.addTab(self.overlay_manager, "Overlay Manager")
        self.tabs.addTab(self.timeline, "Timeline")
        self.tabs.addTab(self.export_panel, "Export")
        self.tabs.addTab(self.ai_tools, "AI Tools")
        self.tabs.addTab(self.render_queue_panel, "Render Queue")
        self.tabs.addTab(self.plugins_panel, "Plugins")
        self.tabs.addTab(self.settings_panel, "Settings")

        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)
        v.addWidget(self.tabs)
        self.setCentralWidget(container)

        # Status bar
        self.setStatusBar(QStatusBar())
        self._status_lbl = QLabel()
        self.statusBar().addPermanentWidget(self._status_lbl)
        self._update_status()

        # Menus & toolbar
        self._build_menu()
        self._build_toolbar()

        # Wire signals
        self.export_panel.start_render_requested.connect(self._enqueue_and_start)
        self.render_queue_panel.start_requested.connect(self.queue.start)
        self.render_queue_panel.stop_requested.connect(self.queue.stop)
        self.render_queue_panel.cancel_current_requested.connect(self.queue.cancel_current)
        self.job_updated.connect(self._refresh_render_panels)

        self.current_project_path: Optional[Path] = None

        # Periodic queue refresh
        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: self.render_queue_panel.refresh(self.queue))
        self._timer.start(750)

    # ---------------- UI build ----------------

    def _build_menu(self) -> None:
        mb = self.menuBar()
        m_file = mb.addMenu("&File")
        m_file.addAction("New Project", self._new_project)
        m_file.addAction("Open Project...", self._open_project)
        m_file.addAction("Save Project", self._save_project)
        m_file.addAction("Save Project As...", self._save_project_as)
        m_file.addSeparator()
        m_file.addAction("Exit", self.close)

        m_render = mb.addMenu("&Render")
        m_render.addAction("Add Job", self._enqueue_render)
        m_render.addAction("Start Queue", self.queue.start)
        m_render.addAction("Stop Queue", self.queue.stop)

        m_help = mb.addMenu("&Help")
        m_help.addAction("About", self._show_about)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(tb.iconSize() * 1.0)
        self.addToolBar(tb)
        tb.addAction("New", self._new_project)
        tb.addAction("Open", self._open_project)
        tb.addAction("Save", self._save_project)
        tb.addSeparator()
        tb.addAction("Render", self._enqueue_and_start)

    # ---------------- status ----------------

    def _update_status(self) -> None:
        parts = []
        if self.ffmpeg.is_available():
            parts.append("FFmpeg: OK")
        else:
            parts.append("FFmpeg: MISSING")
        if self.gpu.has_any_gpu:
            gpu_names = []
            if self.gpu.has_nvidia: gpu_names.append("NVENC")
            if self.gpu.has_intel: gpu_names.append("QSV")
            if self.gpu.has_amd: gpu_names.append("AMF")
            parts.append("GPU: " + "+".join(gpu_names))
        else:
            parts.append("GPU: none")
        self._status_lbl.setText("  |  ".join(parts))

    # ---------------- project ----------------

    def _build_project_from_ui(self) -> Project:
        p = Project()
        p.source_video = Path(self.video_editor.source_path()) if self.video_editor.source_path() else None
        loop_opts = self.video_editor.current_options()
        p.target_duration = loop_opts.target_duration_seconds
        p.loop_options = loop_opts
        p.audio_tracks = self.audio_mixer.current_tracks()
        p.audio_options = self.audio_mixer.current_options()
        p.overlays = self.overlay_manager.current_layers()
        p.export_settings = self.export_panel.current_settings()
        return p

    def _new_project(self) -> None:
        QMessageBox.information(self, "New Project", "Cleared panels for a new project.")
        # Note: panels keep their state; intentionally minimal reset.
        self.current_project_path = None

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", str(Path.home()), "Smooth Loop Project (*.sls.json)"
        )
        if not path:
            return
        try:
            project = ProjectIO.load(path)
            self.current_project_path = Path(path)
            self._apply_project_to_ui(project)
            QMessageBox.information(self, "Project Loaded", f"Loaded: {project.name}")
        except Exception as e:
            QMessageBox.critical(self, "Load failed", str(e))

    def _save_project(self) -> None:
        if not self.current_project_path:
            self._save_project_as()
            return
        try:
            ProjectIO.save(self._build_project_from_ui(), self.current_project_path)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def _save_project_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", str(Path.home() / "project.sls.json"),
            "Smooth Loop Project (*.sls.json)",
        )
        if not path:
            return
        try:
            ProjectIO.save(self._build_project_from_ui(), path)
            self.current_project_path = Path(path)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def _apply_project_to_ui(self, project: Project) -> None:
        if project.source_video:
            self.video_editor.src_input.setText(str(project.source_video))
        # NOTE: a fuller implementation would re-apply all fields; we keep
        # this conservative to avoid surprising overrides.

    # ---------------- render ----------------

    def _enqueue_render(self) -> RenderJob | None:
        src = self.video_editor.source_path()
        if not src:
            QMessageBox.warning(self, "No source", "Pilih video source dulu.")
            return None
        loop = self.video_editor.current_options()
        export = self.export_panel.current_settings()
        if not export.output_path or str(export.output_path) == "output.mp4":
            ext = export.container
            export.output_path = self.config.abs_path("exports") / f"smooth_loop.{ext}"
            self.export_panel.le_out.setText(str(export.output_path))
        job = RenderJob.create(
            source_video=src,
            target_duration=loop.target_duration_seconds,
            export=export,
            loop_options=loop,
            audio_tracks=self.audio_mixer.current_tracks(),
            audio_options=self.audio_mixer.current_options(),
            overlays=self.overlay_manager.current_layers(),
        )
        self.queue.add_job(job)
        self.render_queue_panel.refresh(self.queue)
        return job

    def _enqueue_and_start(self) -> None:
        job = self._enqueue_render()
        if job is not None:
            self.queue.start()
            self.tabs.setCurrentWidget(self.render_queue_panel)

    def _on_job_update(self, job: RenderJob) -> None:
        self.job_updated.emit(job)

    def _refresh_render_panels(self, job: RenderJob) -> None:
        self.render_queue_panel.on_job_update(job)
        label = f"{job.status.value}  {job.progress:.1f}%"
        if job.eta_seconds and job.status.value not in ("done", "error", "cancelled", "pending"):
            eta_min = int(job.eta_seconds // 60)
            eta_sec = int(job.eta_seconds % 60)
            label += f"  ETA {eta_min}:{eta_sec:02d}"
        self.export_panel.set_progress(job.progress, label)
        self.dashboard.set_render_progress(job.progress, label)
        # Pop a one-shot error dialog when a job fails.
        if job.status.value == "error" and getattr(self, "_last_error_job", None) != job.job_id:
            self._last_error_job = job.job_id
            QMessageBox.critical(
                self, "Render gagal",
                f"Job {job.job_id} gagal.\n\n{job.error_message[:1200]}",
            )

    # ---------------- misc ----------------

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {self.config.app.name}",
            f"<h2>{self.config.app.name}</h2>"
            f"<p>Version {self.config.app.version}</p>"
            "<p>Aplikasi desktop untuk membuat seamless looping video profesional.</p>"
            "<p>Built with Python, PySide6, FFmpeg & OpenCV.</p>",
        )

    def closeEvent(self, event) -> None:  # noqa: D401
        try:
            self.queue.stop()
            save_config(self.config)
        finally:
            super().closeEvent(event)
