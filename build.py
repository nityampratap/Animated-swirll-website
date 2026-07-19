#!/usr/bin/env python3
"""
SWIRL Scroll-Film — Video Processing Pipeline
===============================================
Usage:
    python build.py probe    → Probe clips + generate contact sheets
    python build.py build    → Concat clips + extract WebP frames
    python build.py serve    → Start local HTTP server
    python build.py all      → probe + build in one go
"""

import sys, os, json, subprocess, shutil, math, struct
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
VIDEOS_DIR   = SCRIPT_DIR.parent / "videos for animation"
OUTPUT_DIR   = SCRIPT_DIR
CS_DIR       = OUTPUT_DIR / "contact-sheets"
FRAMES_DIR   = OUTPUT_DIR / "frames"
STILLS_DIR   = OUTPUT_DIR / "stills"
MASTER_FILE  = OUTPUT_DIR / "master.mp4"
MANIFEST     = OUTPUT_DIR / "frame-manifest.json"
CHAPTERS_TMP = OUTPUT_DIR / "_chapters.json"

TARGET_FPS     = 12
TARGET_WIDTH   = 1400
XFADE_DUR      = 0.4       # seconds per crossfade
WEBP_QUALITY   = 82

# Story order — glob patterns matched against filenames in VIDEOS_DIR
STORY = [
    {
        "glob":     "Video Project",
        "id":       "foundation",
        "name":     "The Foundation",
        "caption":  "THE FOUNDATION",
        "subtitle": "Every masterpiece begins with a single layer",
    },
    {
        "glob":     "Video Project 1",
        "id":       "craft",
        "name":     "The Craft",
        "caption":  "THE CRAFT",
        "subtitle": "Patience, precision, the perfect peak",
    },
    {
        "glob":     "Video Project 2",
        "id":       "pour",
        "name":     "The Pour",
        "caption":  "THE POUR",
        "subtitle": "Silk meets glass",
    },
    {
        "glob":     "Video Project 3",
        "id":       "finish",
        "name":     "The Finish",
        "caption":  "THE FINISH",
        "subtitle": "Details make the difference",
    },
    {
        "glob":     "Video Project 6",
        "id":       "ensemble",
        "name":     "The Ensemble",
        "caption":  "THE ENSEMBLE",
        "subtitle": "Together, extraordinary",
    },
    {
        "glob":     "Video Project 4",
        "id":       "moment",
        "name":     "The Moment",
        "caption":  "THE MOMENT",
        "subtitle": "Ready when you are",
    },
    {
        "glob":     "Video Project 5",
        "id":       "ingredients",
        "name":     "The Ingredients",
        "caption":  "THE INGREDIENTS",
        "subtitle": "Nature's finest, in orbit",
    },
]

FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"

# ─── Binary Resolver ────────────────────────────────────────────────

def resolve_binaries():
    global FFMPEG_BIN, FFPROBE_BIN
    
    # Try finding in system path
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    
    if ffmpeg_path and ffprobe_path:
        FFMPEG_BIN = ffmpeg_path
        FFPROBE_BIN = ffprobe_path
        return
        
    # Try finding in current directory (local exe)
    local_ffmpeg = SCRIPT_DIR / "ffmpeg.exe"
    local_ffprobe = SCRIPT_DIR / "ffprobe.exe"
    
    if local_ffmpeg.exists() and local_ffprobe.exists():
        FFMPEG_BIN = str(local_ffmpeg)
        FFPROBE_BIN = str(local_ffprobe)
        return
        
    # Not found. Prompt to download
    print("\n" + "!" * 64)
    print("  FFmpeg / FFprobe were not found in your PATH or current directory.")
    print("  This script requires FFmpeg to probe and build the film.")
    print("!" * 64)
    print("\n  We can automatically download a official static build of FFmpeg")
    print("  (release essentials) from gyan.dev and extract ffmpeg.exe & ffprobe.exe here.")
    
    try:
        ans = input("  Would you like to download FFmpeg automatically? (y/n): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        ans = 'n'
        
    if ans != 'y':
        print("\n  Please install FFmpeg manually (e.g. winget install ffmpeg) and add to PATH.")
        sys.exit(1)
        
    print("\n  Downloading FFmpeg release essentials (~90MB)... This may take a minute...")
    import urllib.request
    import zipfile
    import io
    
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response:
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024 * 1024 # 1MB
            data = io.BytesIO()
            downloaded = 0
            while True:
                block = response.read(block_size)
                if not block:
                    break
                data.write(block)
                downloaded += len(block)
                if total_size:
                    percent = (downloaded / total_size) * 100
                    print(f"  Progress: {percent:.1f}% ({downloaded/(1024*1024):.1f}MB / {total_size/(1024*1024):.1f}MB)", end="\r")
                else:
                    print(f"  Downloaded: {downloaded/(1024*1024):.1f}MB", end="\r")
            print("\n  Download complete! Extracting binaries...")
            
            zip_data = data.getvalue()
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
                for name in zip_ref.namelist():
                    if name.endswith("ffmpeg.exe"):
                        with open(local_ffmpeg, "wb") as f:
                            f.write(zip_ref.read(name))
                    elif name.endswith("ffprobe.exe"):
                        with open(local_ffprobe, "wb") as f:
                            f.write(zip_ref.read(name))
            print("  Extraction complete!")
            FFMPEG_BIN = str(local_ffmpeg)
            FFPROBE_BIN = str(local_ffprobe)
    except Exception as e:
        print(f"\n  Failed to download/extract FFmpeg: {e}")
        print("  Please download manually from: https://www.gyan.dev/ffmpeg/builds/")
        print("  Or run: winget install \"FFmpeg (Essentials Build)\" in administrative PowerShell.")
        sys.exit(1)


# ─── Helpers ────────────────────────────────────────────────────────

def find_video(pattern):
    """Locate a .mp4 whose name or stem matches pattern exactly (case-insensitive), falling back to substring."""
    lo = pattern.lower()
    # 1. Exact stem match
    for f in VIDEOS_DIR.iterdir():
        if f.suffix.lower() == ".mp4" and f.stem.lower() == lo:
            return f
    # 2. Exact filename match
    for f in VIDEOS_DIR.iterdir():
        if f.suffix.lower() == ".mp4" and f.name.lower() == lo:
            return f
    # 3. Substring match
    for f in sorted(VIDEOS_DIR.iterdir()):
        if f.suffix.lower() == ".mp4" and lo in f.name.lower():
            return f
    return None


def ffprobe_duration(path):
    r = subprocess.run(
        [FFPROBE_BIN, "-v", "quiet", "-print_format", "json",
         "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(r.stdout)["format"]["duration"])


def clear_dir_safely(dir_path):
    if not dir_path.exists():
        return
    for item in dir_path.iterdir():
        if item.is_file():
            try:
                item.unlink()
            except Exception:
                pass # Skip if locked by OneDrive


def extract_frame_at(video, time_s, out_path, width=400):
    subprocess.run(
        [FFMPEG_BIN, "-y", "-ss", f"{time_s:.3f}", "-i", str(video),
         "-frames:v", "1", "-vf", f"crop=in_w:in_h-50:0:0,scale={width}:-1",
         "-q:v", "2", str(out_path)],
        capture_output=True, check=True,
    )


# ─── Step 1: Probe ─────────────────────────────────────────────────

def cmd_probe():
    CS_DIR.mkdir(exist_ok=True)
    chapters = []

    print("\n" + "=" * 64)
    print("  SWIRL — Video Asset Probe")
    print("=" * 64)

    for idx, ch in enumerate(STORY, 1):
        vid = find_video(ch["glob"])
        if vid is None:
            print(f"\n  ⚠  CH{idx} [{ch['name']}]  — NOT FOUND  (pattern: {ch['glob']})")
            continue

        dur = ffprobe_duration(vid)
        chapters.append({**ch, "path": str(vid), "duration": dur})

        print(f"\n  CH{idx}  {ch['name']}")
        print(f"       File     : {vid.name}")
        print(f"       Duration : {dur:.2f}s")

        # ── contact sheet: 5 key frames ──
        positions = [0.05, 0.25, 0.50, 0.75, 0.95]
        tmp_frames = []
        for i, p in enumerate(positions):
            tmp = CS_DIR / f"_tmp_{idx}_{i}.png"
            extract_frame_at(vid, dur * p, tmp, width=400)
            tmp_frames.append(tmp)

        cs_out = CS_DIR / f"ch{idx:02d}_{ch['id']}.jpg"
        inputs_args = []
        for tf in tmp_frames:
            inputs_args += ["-i", str(tf)]

        subprocess.run(
            [FFMPEG_BIN, "-y"] + inputs_args +
            ["-filter_complex",
             "[0]scale=400:-1[a];[1]scale=400:-1[b];[2]scale=400:-1[c];"
             "[3]scale=400:-1[d];[4]scale=400:-1[e];"
             "[a][b][c][d][e]hstack=inputs=5",
             "-q:v", "2", str(cs_out)],
            capture_output=True,
        )
        for tf in tmp_frames:
            tf.unlink(missing_ok=True)

        print(f"       Sheet    : {cs_out.name}")

    # save for build step
    CHAPTERS_TMP.write_text(json.dumps(chapters, indent=2))

    total_raw = sum(c["duration"] for c in chapters)
    total_master = total_raw - (len(chapters) - 1) * XFADE_DUR
    est_frames = int(total_master * TARGET_FPS)

    print(f"\n{'─' * 64}")
    print(f"  Raw total      : {total_raw:.2f}s")
    print(f"  After crossfades: {total_master:.2f}s  ({len(chapters)-1} × {XFADE_DUR}s)")
    print(f"  Est. frames @{TARGET_FPS}fps: {est_frames}")
    print(f"\n  Contact sheets → {CS_DIR}")
    print(f"  Next step      → python build.py build")
    print("=" * 64 + "\n")


# ─── Step 2: Build ─────────────────────────────────────────────────

def cmd_build():
    if not CHAPTERS_TMP.exists():
        print("Run  python build.py probe  first.")
        return

    chapters = json.loads(CHAPTERS_TMP.read_text())
    if not chapters:
        print("No chapters found. Check your videos directory.")
        return

    n = len(chapters)
    durations = [c["duration"] for c in chapters]

    print("\n" + "=" * 64)
    print("  SWIRL — Building Master Film + WebP Frames")
    print("=" * 64)

    # ── 2a. Concatenate with xfade ──────────────────────────────────
    print("\n  [1/4]  Concatenating clips with crossfades …")

    inputs_args = []
    for c in chapters:
        inputs_args += ["-i", c["path"]]

    if n == 1:
        fc = "[0:v]scale=1920:-1,setsar=1[outv]"
        master_dur = durations[0]
    else:
        parts = []
        accumulated = durations[0]
        for i in range(n - 1):
            src1 = "[0:v]" if i == 0 else f"[xf{i-1}]"
            src2 = f"[{i+1}:v]"
            offset = accumulated - XFADE_DUR
            tag  = "[outv]" if i == n - 2 else f"[xf{i}]"
            parts.append(
                f"{src1}{src2}xfade=transition=fade:"
                f"duration={XFADE_DUR}:offset={offset:.4f}{tag}"
            )
            accumulated += durations[i + 1] - XFADE_DUR
        fc = ";".join(parts)
        master_dur = accumulated

    subprocess.run(
        [FFMPEG_BIN, "-y"] + inputs_args +
        ["-filter_complex", fc,
         "-map", "[outv]", "-c:v", "libx264", "-crf", "18",
         "-preset", "fast", "-an", str(MASTER_FILE)],
        check=True,
    )
    print(f"         → master.mp4  ({master_dur:.2f}s)")

    # ── 2b. Extract PNG frames ──────────────────────────────────────
    print(f"\n  [2/4]  Extracting frames @{TARGET_FPS}fps, {TARGET_WIDTH}px wide …")

    import tempfile
    tmp_dir_obj = tempfile.TemporaryDirectory(prefix="swirl_tmp_")
    tmp_png = Path(tmp_dir_obj.name)

    subprocess.run(
        [FFMPEG_BIN, "-y", "-i", str(MASTER_FILE),
         "-vf", f"crop=in_w:in_h-50:0:0,fps={TARGET_FPS},scale={TARGET_WIDTH}:-1",
         str(tmp_png / "frame_%05d.png")],
        check=True,
    )

    png_files = sorted(tmp_png.glob("frame_*.png"))
    total_frames = len(png_files)
    print(f"         → {total_frames} PNG frames extracted")

    # ── 2c. Convert to WebP via Pillow ──────────────────────────────
    print(f"\n  [3/4]  Converting to WebP (Pillow, q={WEBP_QUALITY}) …")

    try:
        from PIL import Image
    except ImportError:
        print("  ⚠  Pillow not installed. Run:  pip install Pillow")
        print("     Then re-run:  python build.py build")
        return

    clear_dir_safely(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    for i, png in enumerate(png_files):
        with Image.open(png) as img:
            webp_path = FRAMES_DIR / f"frame_{i:05d}.webp"
            img.save(webp_path, "WEBP", quality=WEBP_QUALITY, method=4)
        if (i + 1) % 50 == 0 or i == total_frames - 1:
            print(f"         {i+1}/{total_frames}")

    try:
        tmp_dir_obj.cleanup()
    except Exception as e:
        print(f"  ⚠ Note: Could not clean up temporary directory: {e}.")

    # ── 2d. Extract stills for homepage ─────────────────────────────
    print(f"\n  [4/4]  Extracting hero stills …")

    clear_dir_safely(STILLS_DIR)
    STILLS_DIR.mkdir(parents=True, exist_ok=True)

    for idx, ch in enumerate(chapters):
        dur = ch["duration"]
        still_path = STILLS_DIR / f"ch{idx+1:02d}_{ch['id']}.webp"
        # extract at 40% through the clip
        tmp_still = STILLS_DIR / f"_tmp_{idx}.png"
        extract_frame_at(ch["path"], dur * 0.4, tmp_still, width=TARGET_WIDTH)
        with Image.open(tmp_still) as img:
            img.save(still_path, "WEBP", quality=90)
        tmp_still.unlink(missing_ok=True)
        print(f"         → {still_path.name}")

    # ── 2e. Compute scroll-fraction ranges ──────────────────────────
    # Each chapter's effective contribution:
    #   first:  D[0]  − XFADE/2
    #   middle: D[i]  − XFADE
    #   last:   D[-1] − XFADE/2
    effective = []
    for i, d in enumerate(durations):
        if n == 1:
            effective.append(d)
        elif i == 0:
            effective.append(d - XFADE_DUR / 2)
        elif i == n - 1:
            effective.append(d - XFADE_DUR / 2)
        else:
            effective.append(d - XFADE_DUR)

    eff_total = sum(effective)
    chapter_manifest = []
    cum_scroll = 0.0
    cum_frame = 0

    print(f"\n{'─' * 64}")
    print(f"  {'Chapter':<22} {'Scroll Range':<22} {'Frames':<16}")
    print(f"{'─' * 64}")

    for i, ch in enumerate(chapters):
        frac = effective[i] / eff_total
        scroll_start = cum_scroll
        scroll_end   = cum_scroll + frac
        start_frame  = cum_frame
        end_frame    = min(total_frames - 1, start_frame + round(frac * total_frames))

        chapter_manifest.append({
            "id":          ch["id"],
            "name":        ch["name"],
            "caption":     ch["caption"],
            "subtitle":    ch["subtitle"],
            "scrollStart": round(scroll_start, 4),
            "scrollEnd":   round(scroll_end, 4),
            "startFrame":  start_frame,
            "endFrame":    end_frame,
        })

        print(f"  {ch['name']:<22} {scroll_start:.4f} – {scroll_end:.4f}"
              f"      {start_frame}–{end_frame}")

        cum_scroll = scroll_end
        cum_frame  = end_frame

    manifest_data = {
        "totalFrames": total_frames,
        "fps":         TARGET_FPS,
        "width":       TARGET_WIDTH,
        "masterDuration": round(master_dur, 3),
        "chapters":    chapter_manifest,
    }
    MANIFEST.write_text(json.dumps(manifest_data, indent=2))

    print(f"{'─' * 64}")
    print(f"  Total frames : {total_frames}")
    print(f"  Manifest     : {MANIFEST.name}")
    print(f"  Stills       : {STILLS_DIR.name}/")
    print(f"  Frames       : {FRAMES_DIR.name}/")
    print(f"\n  Next step    → python build.py serve")
    print("=" * 64 + "\n")


# ─── Step 3: Serve ─────────────────────────────────────────────────

def cmd_serve():
    import http.server, socketserver, webbrowser, socket

    def free_port(start=8080):
        for p in range(start, start + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", p)) != 0:
                    return p
        return start

    port = free_port()
    os.chdir(OUTPUT_DIR)

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        url = f"http://localhost:{port}"
        print(f"\n  SWIRL dev server → {url}")
        print(f"  Press Ctrl+C to stop\n")
        webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server stopped.")


# ─── Main ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    cmds = sys.argv[1:] if len(sys.argv) > 1 else ["all"]
    
    if any(c in ["probe", "build", "all"] for c in cmds):
        resolve_binaries()

    for cmd in cmds:
        if cmd == "probe":
            cmd_probe()
        elif cmd == "build":
            cmd_build()
        elif cmd == "serve":
            cmd_serve()
        elif cmd == "all":
            cmd_probe()
            cmd_build()
        else:
            print(f"Unknown command: {cmd}")
            print(__doc__)
