import os
import shutil
import subprocess
import uuid
from flask import Flask, jsonify, render_template_string, request, send_from_directory
import yt_dlp

app = Flask(__name__)

BASE_DIR = os.path.abspath("clips_workspace")
os.makedirs(BASE_DIR, exist_ok=True)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Dark Clip Studio</title>
  <style>
    :root {
      --bg: #090b10;
      --card: #121620;
      --card-2: #181e2b;
      --border: #252d3d;
      --text: #f1f5f9;
      --muted: #94a3b8;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
      --ok: #22c55e;
      --err: #ef4444;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 20px;
    }
    .wrap {
      max-width: 720px;
      margin: 0 auto;
    }
    h1 {
      margin: 0 0 6px;
      font-size: 1.5rem;
    }
    .sub {
      margin: 0 0 18px;
      color: var(--muted);
      font-size: 0.92rem;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      margin-bottom: 18px;
    }
    label {
      display: block;
      font-size: 0.88rem;
      color: var(--muted);
      margin-bottom: 6px;
    }
    input[type="text"], input[type="number"] {
      width: 100%;
      padding: 11px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: var(--card-2);
      color: var(--text);
      font-size: 0.95rem;
      margin-bottom: 14px;
    }
    .presets {
      display: flex;
      gap: 8px;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }
    .preset-btn {
      background: var(--card-2);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 7px 14px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 600;
    }
    .preset-btn.active {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    @media (max-width: 560px) {
      .row { grid-template-columns: 1fr; }
    }
    .check-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 16px;
    }
    button.primary {
      width: 100%;
      padding: 12px 16px;
      border: none;
      border-radius: 10px;
      background: var(--accent);
      color: #fff;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
    }
    button.primary:hover { background: var(--accent-hover); }
    button.primary:disabled { opacity: 0.55; cursor: not-allowed; }
    .status {
      margin-top: 12px;
      font-size: 0.9rem;
      color: var(--muted);
      white-space: pre-line;
    }
    .status.ok { color: var(--ok); }
    .status.err { color: var(--err); }
    .clip-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--card-2);
      border: 1px solid var(--border);
      padding: 10px 12px;
      border-radius: 10px;
      margin-bottom: 8px;
      gap: 10px;
    }
    .clip-item a {
      color: #60a5fa;
      text-decoration: none;
      font-weight: 600;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Dark Clip Studio</h1>
    <p class="sub">YouTube link dein aur 1, 5, 10 ya us se zyada real clips banayein.</p>

    <div class="card">
      <label for="url">YouTube Video Link</label>
      <input id="url" type="text" placeholder="https://www.youtube.com/watch?v=..." />

      <label>Quick Clip Count</label>
      <div class="presets">
        <button type="button" class="preset-btn" onclick="setClips(1, this)">1 Clip</button>
        <button type="button" class="preset-btn active" onclick="setClips(5, this)">5 Clips</button>
        <button type="button" class="preset-btn" onclick="setClips(10, this)">10 Clips</button>
      </div>

      <div class="row">
        <div>
          <label for="numClips">Clips Ki Tadaad</label>
          <input id="numClips" type="number" min="1" max="50" value="5" />
        </div>
        <div>
          <label for="duration">Har Clip Ki Lambai (sec)</label>
          <input id="duration" type="number" min="3" max="300" value="30" />
        </div>
      </div>

      <div class="check-row">
        <input id="vertical916" type="checkbox" />
        <label for="vertical916" style="margin:0; color:var(--text);">9:16 Vertical Crop (Shorts / Reels)</label>
      </div>

      <button id="genBtn" class="primary" onclick="generateClips()">Generate Real Clips</button>
      <div id="status" class="status"></div>
    </div>

    <div class="card" id="resultsCard" style="display:none;">
      <h3 style="margin-top:0;">Generated Clips</h3>
      <div id="clipsList"></div>
    </div>
  </div>

  <script>
    function setClips(n, btn) {
      document.getElementById("numClips").value = n;
      document.querySelectorAll(".preset-btn").forEach(b => b.classList.remove("active"));
      if (btn) btn.classList.add("active");
    }

    async function generateClips() {
      const url = document.getElementById("url").value.trim();
      const num_clips = parseInt(document.getElementById("numClips").value, 10);
      const clip_duration = parseInt(document.getElementById("duration").value, 10);
      const vertical_9_16 = document.getElementById("vertical916").checked;

      const btn = document.getElementById("genBtn");
      const status = document.getElementById("status");
      const resultsCard = document.getElementById("resultsCard");
      const clipsList = document.getElementById("clipsList");

      if (!url) {
        status.className = "status err";
        status.textContent = "Barah-e-karam YouTube link enter karein.";
        return;
      }

      btn.disabled = true;
      status.className = "status";
      status.textContent = "Video download ho rahi hai aur clips ban rahi hain...";
      resultsCard.style.display = "none";
      clipsList.innerHTML = "";

      try {
        const res = await fetch("/api/clip", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, num_clips, clip_duration, vertical_9_16 })
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || "Clipping mein masla aaya.");
        }

        status.className = "status ok";
        status.textContent = `Mukammal! ${data.clips.length} clips ban gayi hain.`;
        resultsCard.style.display = "block";

        data.clips.forEach(item => {
          const div = document.createElement("div");
          div.className = "clip-item";
          div.innerHTML = `
            <span><strong>${item.name}</strong> (${item.start}s - ${item.end}s)</span>
            <a href="${item.download_url}" download>Download</a>
          `;
          clipsList.appendChild(div);
        });
      } catch (err) {
        status.className = "status err";
        status.textContent = "Error: " + err.message;
      } finally {
        btn.disabled = false;
      }
    }
  </script>
</body>
</html>
"""


def find_ffmpeg() -> str:
    ff = shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("FFmpeg nahi mila. Terminal mein 'sudo apt-get install -y ffmpeg' chalayein.")
    return ff


def get_duration(video_path: str, ffmpeg_exe: str) -> float:
    proc = subprocess.run(
        [ffmpeg_exe, "-i", video_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    for line in proc.stderr.splitlines():
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError("Video ki duration maloom nahi ho saki.")


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/api/clip", methods=["POST"])
def api_clip():
    data = request.get_json(force=True) or {}
    url = (data.get("url") or "").strip()
    num_clips = int(data.get("num_clips") or 5)
    clip_duration = int(data.get("clip_duration") or 30)
    vertical_9_16 = bool(data.get("vertical_9_16"))

    if not url:
        return jsonify({"error": "YouTube link zaroori hai."}), 400
    if num_clips < 1 or num_clips > 50 or clip_duration < 1:
        return jsonify({"error": "Clips count (1-50) aur duration sahi dein."}), 400

    job_id = uuid.uuid4().hex[:8]
    job_dir = os.path.join(BASE_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    source_path = os.path.join(job_dir, "source.mp4")

    try:
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": source_path,
            "merge_output_format": "mp4",
            "quiet": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(source_path):
            return jsonify({"error": "Video download nahi ho saki."}), 400

        ffmpeg_exe = find_ffmpeg()
        total_dur = get_duration(source_path, ffmpeg_exe)

        if total_dur <= clip_duration:
            starts = [0.0]
        elif num_clips == 1:
            starts = [0.0]
        else:
            max_start = max(0.0, total_dur - clip_duration)
            step = max_start / (num_clips - 1)
            starts = [round(i * step, 2) for i in range(num_clips)]

        clips_out = []
        for idx, start_sec in enumerate(starts, start=1):
            actual_dur = min(clip_duration, max(1.0, total_dur - start_sec))
            fname = f"clip_{idx:02d}.mp4"
            out_path = os.path.join(job_dir, fname)

            cmd = [ffmpeg_exe, "-y", "-ss", str(start_sec), "-i", source_path, "-t", str(actual_dur)]
            if vertical_9_16:
                cmd += ["-vf", "crop=ih*(9/16):ih,scale=1080:1920"]
            cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", "-c:a", "aac", "-b:a", "128k", out_path]

            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            clips_out.append({
                "name": fname,
                "start": start_sec,
                "end": round(start_sec + actual_dur, 1),
                "download_url": f"/download/{job_id}/{fname}",
            })

        if os.path.exists(source_path):
            os.remove(source_path)

        return jsonify({"clips": clips_out})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download/<job_id>/<fname>")
def download_file(job_id, fname):
    safe_dir = os.path.abspath(os.path.join(BASE_DIR, job_id))
    if not safe_dir.startswith(BASE_DIR):
        return "Invalid path", 400
    return send_from_directory(safe_dir, fname, as_attachment=True)


if __name__ == "__main__":
    print("Dark Clip Studio running on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
