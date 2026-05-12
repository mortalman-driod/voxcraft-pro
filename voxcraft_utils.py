"""VoxCraft utility functions - audio, ffmpeg, waveform, SSML, music generation."""
import os, subprocess, wave, io, json, math, struct
import numpy as np

# Locate ffmpeg
_ffmpeg_exe = "ffmpeg"
try:
      import imageio_ffmpeg
      _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
      pass

def get_ffmpeg():
      return _ffmpeg_exe

def get_audio_duration(filepath):
      try:
                cmd = [_ffmpeg_exe, "-i", filepath, "-f", "null", "-"]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                for line in r.stderr.split('\n'):
                              if 'Duration' in line:
                                                t = line.split('Duration:')[1].split(',')[0].strip().split(':')
                                                return float(t[0])*3600 + float(t[1])*60 + float(t[2])
      except Exception:
                pass
            return os.path.getsize(filepath) / 2000.0

def get_video_duration(filepath):
      return get_audio_duration(filepath)

def stitch_audio_files(file_paths, output_path):
      """Concatenate audio files efficiently. Uses concat demuxer for many files."""
    if not file_paths:
              return
          if len(file_paths) == 1:
                    import shutil
                    shutil.copy2(file_paths[0], output_path)
                    return

    # Use concat demuxer for efficiency with many files (good for 1hr+ projects)
    list_path = output_path + ".list.txt"
    with open(list_path, "w", encoding="utf-8") as f:
              for fp in file_paths:
                            # ffmpeg concat demuxer needs escaped paths
                            abs_path = os.path.abspath(fp).replace("\\\\", "/")
                            f.write(f"file '{abs_path}'\n")

          try:
                    cmd = [_ffmpeg_exe, "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", "-y", output_path]
                    # If 'copy' fails (e.g. different sample rates), fallback to re-encode
                    result = subprocess.run(cmd, capture_output=True, timeout=300)
                    if result.returncode != 0:
                                  # Fallback to filter_complex (re-encode)
                                  inputs = []
                                  parts = []
                                  for i, fp in enumerate(file_paths):
                                                    inputs.extend(["-i", fp])
                                                    parts.append(f"[{i}:a]")
                                                filt = "".join(parts) + f"concat=n={len(file_paths)}:v=0:a=1[out]"
                                  cmd = [_ffmpeg_exe] + inputs + ["-filter_complex", filt, "-map", "[out]", "-y", output_path]
                                  subprocess.run(cmd, capture_output=True, timeout=600)
          finally:
        if os.path.exists(list_path):
                      os.remove(list_path)

def normalize_audio(input_path, output_path):
      cmd = [_ffmpeg_exe, "-i", input_path, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-y", output_path]
    subprocess.run(cmd, capture_output=True, timeout=60)

def mix_audio_with_music(voice_path, music_path, output_path, music_vol=0.15):
      cmd = [_ffmpeg_exe, "-i", voice_path, "-i", music_path,
                        "-filter_complex", f"[1:a]volume={music_vol}[m];[0:a][m]amix=inputs=2:duration=first[out]",
                        "-map", "[out]", "-y", output_path]
    subprocess.run(cmd, capture_output=True, timeout=120)

def export_video_with_audio(audio_path, output_path, duration):
      """Create a simple waveform video with the audio baked in."""
    cmd = [_ffmpeg_exe, "-f", "lavfi", "-i", f"color=c=0x0a0a1a:s=1280x720:d={duration}",
                      "-i", audio_path, "-shortest",
                      "-vf", "drawtext=text='VoxCraft Voice Over':fontcolor=white:fontsize=28:x=(w-text_w)/2:y=h/2",
                      "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-y", output_path]
    subprocess.run(cmd, capture_output=True, timeout=180)

def make_waveform(audio_path):
      import matplotlib
      matplotlib.use('Agg')
      import matplotlib.pyplot as plt
      wav_path = audio_path + ".tmp.wav"
      subprocess.run([_ffmpeg_exe, "-i", audio_path, "-ac", "1", "-ar", "16000", "-y", wav_path], capture_output=True, timeout=30)
      try:
                with wave.open(wav_path, 'rb') as wf:
                              samples = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32)
                          samples = samples / (np.max(np.abs(samples)) + 1e-8)
finally:
        if os.path.exists(wav_path): os.remove(wav_path)
              chunk = max(1, len(samples) // 2000)
    ds = [np.max(np.abs(samples[i:i+chunk])) for i in range(0, len(samples), chunk)]
    fig, ax = plt.subplots(figsize=(12, 2), facecolor='#0a0a1a')
    ax.set_facecolor('#0a0a1a')
    x = np.linspace(0, len(ds), len(ds))
    ax.fill_between(x, ds, alpha=0.6, color='#7c5cfc')
    ax.fill_between(x, [-v for v in ds], alpha=0.6, color='#7c5cfc')
    ax.plot(x, ds, color='#a090ff', linewidth=0.5)
    ax.plot(x, [-v for v in ds], color='#a090ff', linewidth=0.5)
    ax.set_xlim(0, len(ds)); ax.set_ylim(-1.1, 1.1)
    ax.axis('off'); plt.tight_layout(pad=0)
    buf = io.BytesIO(); fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#0a0a1a'); plt.close(fig)
    buf.seek(0); return buf

def fmt_time(s):
      h=int(s//3600); m=int((s%3600)//60); sec=int(s%60); ms=int((s%1)*1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

def gen_srt(segments_data):
      srt, offset = [], 0.0
    for seg in segments_data:
              dur = seg.get('duration', 3.0)
              words = seg['text'].split()
              chunks = [' '.join(words[j:j+6]) for j in range(0, len(words), 6)]
              tpc = dur / max(len(chunks), 1)
              for ci, chunk in enumerate(chunks):
                            s = offset + ci*tpc; e = s + tpc
                            srt.append(f"{len(srt)+1}\n{fmt_time(s)} --> {fmt_time(e)}\n{chunk}\n")
                        offset += dur
    return "\n".join(srt)

def estimate_duration(text, rate_str):
      words = len(text.split())
    rv = int(rate_str.replace('%','').replace('+',''))
    return max(1.0, (words / (155 * (1 + rv/100))) * 60)

# -- SSML Helpers --
def apply_ssml(text, style=None):
      """Wrap text with SSML tags if style is specified."""
    if not style or style == "default":
              return text
    return text  # edge_tts handles styles differently

def apply_pronunciation(text, pron_dict):
      for word, replacement in pron_dict.items():
                text = text.replace(word, replacement)
            return text

def insert_ssml_pause(text, position, duration_ms=500):
      return text[:position] + f" ... " + text[position:]

# -- Background Music Generator --
def generate_ambient_music(duration_sec, style="cinematic", output_path="workspace/bg_music.mp3"):
      """Generate audible and pleasant ambient background music using ffmpeg synthesis."""
    d = int(duration_sec) + 2
    # Define styles with richer synthesis (ambient pads)
    styles = {
              "cinematic": f"anoisesrc=d={d}:c=pink:a=0.1,lowpass=f=100[n];sine=f=60:d={d},volume=0.5[b];sine=f=120:d={d},volume=0.2[s1];[n][b][s1]amix=inputs=3[out]",
              "calm": f"anoisesrc=d={d}:c=pink:a=0.05,lowpass=f=300[n];sine=f=220:d={d},volume=0.1[s1];sine=f=330:d={d},volume=0.08[s2];[n][s1][s2]amix=inputs=3[out]",
              "energetic": f"sine=f=80:d={d},volume=0.4[b];sine=f=300:d={d}:beat=4,volume=0.2[s];[b][s]amix=inputs=2,aecho=0.8:0.8:500:0.3[out]",
              "mysterious": f"anoisesrc=d={d}:c=brown:a=0.1,lowpass=f=80[n];sine=f=45:d={d},volume=0.6[b];sine=f=110:d={d},volume=0.2,tremolo=f=4:d=0.6[s];[n][b][s]amix=inputs=3[out]",
              "inspiring": f"sine=f=130:d={d},volume=0.2[s1];sine=f=165:d={d},volume=0.2[s2];sine=f=196:d={d},volume=0.2[s3];[s1][s2][s3]amix=inputs=3,aecho=0.8:0.8:1000:0.4[out]",
              "ambient": f"anoisesrc=d={d}:c=pink:a=0.08,lowpass=f=200[n];sine=f=75:d={d},volume=0.2[s];[n][s]amix=inputs=2[out]",

  }
    filt = styles.get(style, styles["cinematic"])
    cmd = [_ffmpeg_exe, "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo", 
                      "-filter_complex", filt, "-map", "[out]",
                      "-t", str(d), "-c:a", "libmp3lame", "-q:a", "4", "-y", output_path]
    subprocess.run(cmd, capture_output=True, timeout=120)
    return output_path
