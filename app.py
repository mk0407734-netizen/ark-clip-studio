import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
WORK_DIR = BASE_DIR / "clips_output"
WORK_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Dark Clip Studio</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 20px;
      background: #0b0f17;
      color: #f3f4f6;
      font-family: system-ui, -apple-system, sans-serif;
    }
    .card {
      max-width: 540px;
      margin: 0 auto;
      background: #131a26;
      border: 1px solid #243044;
      border-radius: 16px;
      padding: 20px;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.45);
    }
    h1 {
      margin: 0 0 6px;
      font-size: 22px;
      color: #ffffff;
    }
    .sub {
      margin: 0 0 18px;
      font-size: 13px;
      color: #9ca3af;
    }
    label {
      display: block;
      margin-top: 14px;
      margin-bottom: 6px;
      font-size: 13px;
      font-weight: 600;
      color: #d1d5db;
    }
    input[type="text"],
    input[type="number"],
    input[type="file"] {
      width: 100%;
      padding: 11px 12px;
      background: #0b0f17;
      border: 1px solid #2b3950;
      border-radius: 10px;
      color: #ffffff;
      font-size: 14px;
    }
    .quick-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-top: 8px;
    }
    .q-btn {
      padding: 9px;
      border-radius: 9px;
      border: 1px solid #2b3950;
      background: #1a2436;
      color: #e5e7eb;
      font-weight: 600;
      cursor: pointer;
    }
    .q-btn.active {
      background: #2563eb;
      border-color: #3b82f6;
      color: #ffffff;
    }
    .check-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 14px;
      font-size: 14px;
      color: #e5e7eb;
    }
    .check-row input {
      width: 18px;
      height: 18px;
    }
    .primary-btn {
      width: 100%;
      margin-top: 18px;
      padding: 13px;
      border: none;
      border-radius: 11px;
      background: #2563eb;
      color: #ffffff;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }
    .primary-btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    .status {
      margin-top: 14px;
      font-size: 13px;
      color: #93c5fd;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .error {
      margin-top: 14px;
      padding: 12px;
      border-radius: 10px;
      background: rgba(239, 68, 68, 0.14);
      border: 1px solid rgba(239, 68, 68, 0.45);
      color: #fca5a5;
      font-size: 13px;
      white-space: pre-wrap;
      word-break: break-word;
      display: none;
    }
    .clips-list {
      margin-top: 18px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .clip-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #0b0f17;
      border: 1px solid #243044;
      padding: 10px 12px;
      border-radius: 10px;
      font-size: 13px;
    }
    .dl-link {
      background: #16a34a;
      color: #ffffff;
      text-decoration: none;
      padding: 7px 12px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 12px;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>Dark Clip Studio</h1>
    <p class="sub">Upload a video file or paste a YouTube link to generate clips.</p>

    <form id="clipForm">
      <label for="videoFile">Upload Video File (Recommended on Mobile)</label>
      <input type="file" id="videoFile" name="video_file" accept="video/*" />

      <label for="youtubeUrl">YouTube Video Link (Optional if uploading file)</label>
      <input type="text" id="youtubeUrl" name="youtube_url" placeholder="https://www.youtube.com/watch?v=..." />

      <label>Quick Clip Count</label>
      <div class="quick-row">
        <button type="button" class="q-btn" data-count="1">1 Clip</button>
        <button type="button" class="q-btn active" data-count="5">5 Clips</button>
        <button type="button" class="q-btn" data-count="10">10 Clips</button>
      </div>

      <label for="clipCount">Clips Ki Tadaad</label>
      <input type="number" id="clipCount" name="clip_count" min="1" max="30" value="5" required />

      <label for="clipDuration">Har Clip Ki Lambai (sec)</label>
      <input type="number" id="clipDuration" name="clip_duration" min="3" max="180" value="15" required />

      <div class="check-row">
        <input type="checkbox" id="verticalCrop" name="vertical_crop" checked />
        <label for="verticalCrop" style="margin:0; font-weight:500;">9:16 Vertical Crop (Shorts / Reels)</label>
      </div>

      <button type="submit" class="primary-btn" id="submitBtn">Generate Real Clips</button>
    </form>

    <div class="status" id="statusBox"></div>
    <div class="error" id="errorBox"></div>
    <div class="clips-list" id="clipsList"></div>
  </div>

  <script>
    const form = document.getElementById("clipForm");
    const countInput = document.getElementById("clipCount");
    const quickBtns = document.querySelectorAll(".q-btn");
    const submitBtn = document.getElementById("submitBtn");
    const statusBox = document.getElementById("statusBox");
    const errorBox = document.getElementById("errorBox");
    const clipsList = document.getElementById("clipsList");

    function syncQuickButtons(val) {
      quickBtns.forEach((btn) => {
        btn.classList.toggle("active", Number(btn.dataset.count) === Number(val));
      });
    }

    quickBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        countInput.value = btn.dataset.count;
        syncQuickButtons(btn.dataset.count);
      });
    });

    countInput.addEventListener("input", () => syncQuickButtons(countInput.value));

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      errorBox.style.display = "none";
      errorBox.textContent = "";
      clipsList.innerHTML = "";
      statusBox.textContent = "Processing video and generating clips... Please wait.";
      submitBtn.disabled = true;

      try {
        const formData = new FormData(form);
        const res = await fetch("/api/generate", {
          method: "POST",
          body: formData,
        });
        const data = await res.json();

        if (!res.ok || !data.ok) {
          throw new Error(data.error || "Failed to generate clips.");
        }

        statusBox.textContent = `Done! Generated ${data.clips.length} clips.`;
        data.clips.forEach((clip) => {
          const row = document.createElement("div");
          row.className = "clip-item";
          row.innerHTML = `
            <span>${clip.name}</span>
            <a class="dl-link" href="${clip.url}" download>Download</a>
          `;
          clipsList.appendChild(row);
        });
      } catch (err) {
        statusBox.textContent = "";
        errorBox.textContent = "Error: " + err.message;
        errorBox.style.display = "block";
      } finally {
        submitBtn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


def get_ffmpeg_bin() -> str:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def get_video_duration(ffmpeg_bin: str, input_path: Path) -> float:
    cmd = [ffmpeg_bin, "-i", str(input_path)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    if not match:
        return 0.0
    hours, minutes, seconds = int(match.group(1)), int(match.group(2)), float(match.group(3))
    return hours * 3600 + minutes * 60 + seconds


def download_youtube_video(youtube_url: str, output_path: Path) -> None:
    import yt_dlp

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(output_path),
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
    }
    cookies_file = BASE_DIR / "cookies.txt"
    if cookies_file.exists():
        ydl_opts["cookiefile"] = str(cookies_file)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])


def cut_clips(
    ffmpeg_bin: str,
    source_path: Path,
    job_dir: Path,
    clip_count: int,
    clip_duration: int,
    vertical_crop: bool,
) -> list[dict]:
    total_dur = get_video_duration(ffmpeg_bin, source_path)
    max_start = max(0.0, total_dur - clip_duration) if total_dur > 0 else float(clip_count * clip_duration)

    if clip_count == 1 or max_start <= 0:
        starts = [0.0]
    else:
        step = max_start / (clip_count - 1)
        starts = [round(i * step, 2) for i in range(clip_count)]

    clips = []
    for idx, start_sec in enumerate(starts, start=1):
        out_name = f"clip_{idx:02d}.mp4"
        out_path = job_dir / out_name

        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss",
            str(start_sec),
            "-i",
            str(source_path),
            "-t",
            str(clip_duration),
        ]
        if vertical_crop:
            cmd += [
                "-vf",
                "crop=ih*9/16:ih,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            ]
        cmd += [
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "24",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(out_path),
        ]

        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0 or not out_path.exists():
            raise RuntimeError(proc.stderr.strip() or f"FFmpeg failed on clip {idx}")

        clips.append({
            "name": out_name,
            "url": f"/download/{job_dir.name}/{out_name}",
        })

    return clips


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        clip_count = max(1, min(30, int(request.form.get("clip_count", 5))))
        clip_duration = max(3, min(180, int(request.form.get("clip_duration", 15))))
        vertical_crop = request.form.get("vertical_crop") == "on"
        youtube_url = (request.form.get("youtube_url") or "").strip()
        uploaded = request.files.get("video_file")

        job_id = uuid.uuid4().hex[:10]
        job_dir = WORK_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        source_path = job_dir / "source.mp4"

        if uploaded and uploaded.filename:
            safe_name = secure_filename(uploaded.filename)
            ext = Path(safe_name).suffix.lower() or ".mp4"
            if ext not in ALLOWED_EXTENSIONS:
                return jsonify({"ok": False, "error": f"Unsupported video format: {ext}"}), 400
            raw_upload = job_dir / f"upload{ext}"
            uploaded.save(str(raw_upload))
            source_path = raw_upload
        elif youtube_url:
            download_youtube_video(youtube_url, source_path)
            if not source_path.exists():
                found = list(job_dir.glob("source.*"))
                if found:
                    source_path = found[0]
        else:
            return jsonify({
                "ok": False,
                "error": "Please upload a video file or enter a YouTube video link.",
            }), 400

        ffmpeg_bin = get_ffmpeg_bin()
        clips = cut_clips(
            ffmpeg_bin=ffmpeg_bin,
            source_path=source_path,
            job_dir=job_dir,
            clip_count=clip_count,
            clip_duration=clip_duration,
            vertical_crop=vertical_crop,
        )
        return jsonify({"ok": True, "clips": clips})

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/download/<job_id>/<filename>")
def download_file(job_id: str, filename: str):
    safe_job = secure_filename(job_id)
    safe_file = secure_filename(filename)
    directory = WORK_DIR / safe_job
    return send_from_directory(directory, safe_file, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
      
