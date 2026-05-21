# Smooth Loop Studio

Aplikasi desktop profesional berbasis Python (PySide6 + FFmpeg + OpenCV) untuk membuat **video looping super halus** yang siap diputar berjam-jam tanpa terlihat jeda. Cocok untuk:

- Live streaming (24/7 YouTube, Twitch)
- ASMR & ambience video
- Aesthetic / lo-fi background
- Wallpaper Engine
- TikTok / Reels / Shorts loop
- Video musik tak terbatas
- Konten otomatis (auto upload pipeline)

---

## Highlights

- **Seamless Loop Engine** — crossfade, ping-pong, reverse, freeze-smooth, optical-flow, AI smooth.
- **Smart Loop Detection** — cari titik loop terbaik otomatis dari frame yang paling mirip.
- **Long Duration Render** — 1 jam → 24 jam → unlimited dengan `-stream_loop`.
- **Multi-track Audio** — banyak musik, ambience layer, replace/mute audio asli, normalisasi loudness, crossfade.
- **Overlay System** — PNG / GIF / video overlay, blend mode, opacity, posisi, rotasi, scaling, animasi.
- **Visual Effects** — color grading, LUT 3D, cinematic tone, HDR sim, sharpen, glow, bloom, VHS, lo-fi, anime, dream, dark ambience, neon cyberpunk, grain, denoise.
- **GPU Acceleration** — NVIDIA NVENC, Intel QuickSync, AMD AMF terdeteksi otomatis.
- **Render Queue** — batch render, retry otomatis, resume, kanselasi per-job.
- **Modern UI** — dark glassmorphism (PySide6), realtime preview (OpenCV), multi-track timeline.
- **AI Tools** — frame interpolation, upscale, denoise, scene detection, beat sync, smart overlay placement.
- **FFmpeg Auto-Installer** — download portable build kalau system belum punya FFmpeg.
- **Project System** — save/load proyek `.sls.json`, auto-backup.
- **Preset Library** — YouTube 1080p/4K/24h, TikTok, Instagram, Wallpaper Engine, Livestream, WebM, dll.
- **Plugin API** — buat efek/overlay/transisi kustom dengan Python.

---

## Persyaratan

- Python 3.12+ (3.11 juga jalan)
- Windows 10/11, Linux, atau macOS
- (Opsional) GPU dengan NVENC / QSV / AMF untuk render lebih cepat
- 8 GB+ RAM untuk render panjang
- FFmpeg (akan di-install otomatis kalau belum ada)

---

## Instalasi cepat

### Windows
```bat
:: clone / unzip lalu jalankan
setup.bat
run.bat
```

### Linux / macOS
```bash
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

`setup` akan:
1. Membuat virtual environment `venv/`
2. Install semua dependency Python (`requirements.txt`)
3. Install FFmpeg portable ke `app/ffmpeg/bin/` jika system belum punya
4. Verifikasi encoder GPU yang tersedia

`run` akan otomatis melakukan auto-repair jika dependency hilang.

### Manual
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app/main.py
```

---

## Struktur proyek

```
smooth-loop-studio/
├── app/
│   ├── core/                # Engine: loop, audio, overlay, effect, export, project
│   │   ├── loop_engine.py
│   │   ├── transitions.py
│   │   ├── audio_engine.py
│   │   ├── overlay_engine.py
│   │   ├── effects.py
│   │   ├── export_engine.py
│   │   ├── ffmpeg_utils.py
│   │   ├── ffmpeg_installer.py
│   │   ├── project.py
│   │   ├── presets.py
│   │   ├── playlist.py
│   │   ├── plugin_api.py
│   │   ├── performance.py
│   │   ├── error_handler.py
│   │   ├── config.py
│   │   └── logger.py
│   ├── ui/                  # PySide6 UI panels
│   │   ├── main_window.py
│   │   ├── dashboard.py
│   │   ├── video_editor.py
│   │   ├── audio_mixer.py
│   │   ├── overlay_manager.py
│   │   ├── export_panel.py
│   │   ├── ai_tools_panel.py
│   │   ├── render_queue_panel.py
│   │   ├── plugin_manager_panel.py
│   │   ├── settings_panel.py
│   │   ├── timeline.py
│   │   ├── preview.py
│   │   ├── widgets.py
│   │   └── theme.py
│   ├── ai/                  # AI tools layer
│   │   ├── interpolation.py
│   │   ├── upscale.py
│   │   ├── denoise.py
│   │   ├── color_enhance.py
│   │   ├── scene_detection.py
│   │   ├── audio_balance.py
│   │   ├── beat_sync.py
│   │   ├── ambience.py
│   │   └── overlay_placement.py
│   ├── presets/             # Built-in JSON preset projects
│   ├── plugins/             # Drop-in Python plugins
│   ├── assets/              # Icons / static UI assets
│   ├── overlays/            # User overlay library
│   ├── music/               # User audio library
│   ├── exports/             # Default render output folder
│   ├── temp/                # Intermediate files (auto-cleaned)
│   ├── logs/                # Rotating logs
│   ├── ffmpeg/              # Locally installed FFmpeg (bin/)
│   ├── config/              # Per-user config overrides
│   └── main.py              # Entry point
├── requirements.txt
├── setup.bat / setup.sh
├── run.bat / run.sh
├── installer.bat
├── config.json              # Global default settings
└── README.md
```

---

## Pipeline render (high-level)

1. **Pilih video sumber.** Bisa pakai *Smart Loop Detection* untuk mencari titik loop terbaik otomatis.
2. **Pilih loop mode** (`crossfade`, `ping_pong`, `freeze_smooth`, `optical_flow`, dll) + transition length.
3. **Tambahkan musik / ambience** di Audio Mixer. Bisa mute audio asli, ganti, atau mix.
4. **Tambah overlay** (logo, watermark, VHS, particle) di Overlay Manager.
5. **Pilih effects** & LUT (opsional).
6. **Set duration** (1 jam, 5 jam, 24 jam, custom) + preset export (YouTube, TikTok, Wallpaper).
7. **Klik "Start Render"** → masuk ke Render Queue. Auto-retry kalau gagal, resume kalau ditutup.

Engine secara internal:
```
[source] --(LoopEngine.build_seamless_unit)--> seamless_unit.mp4
seamless_unit.mp4 --(LoopEngine.build_long_loop)--> looped.mp4 (silent, target duration)
looped.mp4 --(OverlayEngine + EffectStack)--> composed.mp4
audio_tracks --(AudioEngine)--> audio.m4a (concatenate / mix / loop)
composed.mp4 + audio.m4a --(ExportEngine final mux)--> output (GPU codec)
```

---

## Tips Performance

- Pakai **GPU encoder** (NVENC paling stabil di Windows). Settings panel akan menampilkan encoder yang tersedia.
- Loop mode `simple` paling cepat. `optical_flow` paling halus tapi 5–10× lebih lambat.
- Untuk render >10 jam, gunakan codec H.264 dengan bitrate 4–6 Mbps; H.265 file lebih kecil tapi CPU lebih berat saat playback.
- Set `engine.threads = 0` di `config.json` agar otomatis.
- Pakai preview resolution 480p untuk responsif; render full-size waktu export.

---

## Plugin API

Tempel file Python di `app/plugins/`:

```python
from app.core.plugin_api import BasePlugin

class MyEffect(BasePlugin):
    name = "My Effect"
    version = "0.1.0"

    def register(self):
        self.manager.register_effect("my_effect", lambda: "eq=saturation=1.4,unsharp=5:5:1.0")
```

Lalu klik **Plugin Manager → Reload Plugins**.

---

## Roadmap

- [ ] Bundled RIFE/FILM ONNX models untuk AI interpolation (saat ini fallback `minterpolate`)
- [ ] Audio waveform display di Audio Mixer
- [ ] Live preview untuk overlay (current preview hanya source)
- [ ] Plugin marketplace
- [ ] Streaming langsung ke RTMP

---

## Lisensi

Lisensi tersedia di repo Anda. Aplikasi ini menggunakan FFmpeg (LGPL/GPL tergantung build), OpenCV (Apache 2.0), PySide6 (LGPL), librosa (ISC), dll.
