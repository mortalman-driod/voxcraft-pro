"""VoxCraft utility functions — audio, ffmpeg, waveform, SSML, music generation."""
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
            abs_path = os.path.abspath(fp).replace("\\", "/")
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

# ── SSML Helpers ──
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

# ── Background Music Generator ──
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

# ── Voice Database (Multi-Language) ──
VOICES = {
    # English
    "🇺🇸 Andrew (Deep Male)": "en-US-AndrewNeural",
    "🇺🇸 Guy (Narrator)": "en-US-GuyNeural",
    "🇺🇸 Davis (Warm Male)": "en-US-DavisNeural",
    "🇺🇸 Tony (Young Male)": "en-US-TonyNeural",
    "🇺🇸 Brandon (Casual)": "en-US-BrandonNeural",
    "🇺🇸 Christopher (News)": "en-US-ChristopherNeural",
    "🇺🇸 Eric (Conversational)": "en-US-EricNeural",
    "🇺🇸 Roger (Elderly)": "en-US-RogerNeural",
    "🇺🇸 Steffan (Pro)": "en-US-SteffanNeural",
    "🇬🇧 Ryan (British)": "en-GB-RyanNeural",
    "🇬🇧 Thomas (British Pro)": "en-GB-ThomasNeural",
    "🇦🇺 William (Aussie)": "en-AU-WilliamNeural",
    "🇮🇳 Prabhat (Indian)": "en-IN-PrabhatNeural",
    "🇺🇸 Jenny (Female Pro)": "en-US-JennyNeural",
    "🇺🇸 Aria (Female Warm)": "en-US-AriaNeural",
    "🇺🇸 Sara (Female Clear)": "en-US-SaraNeural",
    "🇺🇸 Michelle (Female)": "en-US-MichelleNeural",
    "🇺🇸 Ana (Female Bright)": "en-US-AnaNeural",
    "🇬🇧 Sonia (British F)": "en-GB-SoniaNeural",
    "🇬🇧 Maisie (British Young)": "en-GB-MaisieNeural",
    "🇦🇺 Natasha (Aussie F)": "en-AU-NatashaNeural",
    "🇮🇳 Neerja (Indian F)": "en-IN-NeerjaNeural",
    "🇨🇦 Clara (Canadian F)": "en-CA-ClaraNeural",
    "🇨🇦 Liam (Canadian M)": "en-CA-LiamNeural",
    # Nigerian English (full set — Nigerian accent, best for Pidgin-adjacent content)
    "🇳🇬 Abeo (Nigerian M)": "en-NG-AbeoNeural",
    "🇳🇬 Ezinne (Nigerian F)": "en-NG-EzinneNeural",
    # African English — Kenyan accent (closest available to West African accent family)
    "🇰🇪 Chilemba (Kenyan M)": "en-KE-ChilembaNeural",
    "🇰🇪 Asilia (Kenyan F)": "en-KE-AsiliaNeural",
    # South African English
    "🇿🇦 Luke (South African M)": "en-ZA-LukeNeural",
    "🇿🇦 Leah (South African F)": "en-ZA-LeahNeural",
    # Tanzanian English
    "🇹🇿 Elimu (Tanzanian M)": "en-TZ-ElimuNeural",
    "🇹🇿 Imani (Tanzanian F)": "en-TZ-ImaniNeural",
    # Spanish
    "🇪🇸 Alvaro (Spanish M)": "es-ES-AlvaroNeural",
    "🇪🇸 Elvira (Spanish F)": "es-ES-ElviraNeural",
    "🇲🇽 Jorge (Mexican M)": "es-MX-JorgeNeural",
    "🇲🇽 Dalia (Mexican F)": "es-MX-DaliaNeural",
    # French
    "🇫🇷 Henri (French M)": "fr-FR-HenriNeural",
    "🇫🇷 Denise (French F)": "fr-FR-DeniseNeural",
    "🇨🇦 Antoine (Quebec M)": "fr-CA-AntoineNeural",
    "🇨🇦 Sylvie (Quebec F)": "fr-CA-SylvieNeural",
    # Portuguese
    "🇧🇷 Antonio (Brazil M)": "pt-BR-AntonioNeural",
    "🇧🇷 Francisca (Brazil F)": "pt-BR-FranciscaNeural",
    "🇵🇹 Duarte (Portugal M)": "pt-PT-DuarteNeural",
    # German
    "🇩🇪 Conrad (German M)": "de-DE-ConradNeural",
    "🇩🇪 Katja (German F)": "de-DE-KatjaNeural",
    # Italian
    "🇮🇹 Diego (Italian M)": "it-IT-DiegoNeural",
    "🇮🇹 Elsa (Italian F)": "it-IT-ElsaNeural",
    # Japanese
    "🇯🇵 Keita (Japanese M)": "ja-JP-KeitaNeural",
    "🇯🇵 Nanami (Japanese F)": "ja-JP-NanamiNeural",
    # Chinese
    "🇨🇳 Yunxi (Chinese M)": "zh-CN-YunxiNeural",
    "🇨🇳 Xiaoxiao (Chinese F)": "zh-CN-XiaoxiaoNeural",
    # Korean
    "🇰🇷 InJoon (Korean M)": "ko-KR-InJoonNeural",
    "🇰🇷 SunHi (Korean F)": "ko-KR-SunHiNeural",
    # Arabic
    "🇸🇦 Hamed (Arabic M)": "ar-SA-HamedNeural",
    "🇸🇦 Zariyah (Arabic F)": "ar-SA-ZariyahNeural",
    # Hindi
    "🇮🇳 Madhur (Hindi M)": "hi-IN-MadhurNeural",
    "🇮🇳 Swara (Hindi F)": "hi-IN-SwaraNeural",
    # Russian
    "🇷🇺 Dmitry (Russian M)": "ru-RU-DmitryNeural",
    "🇷🇺 Svetlana (Russian F)": "ru-RU-SvetlanaNeural",
    # Turkish
    "🇹🇷 Ahmet (Turkish M)": "tr-TR-AhmetNeural",
    "🇹🇷 Emel (Turkish F)": "tr-TR-EmelNeural",
    # Dutch
    "🇳🇱 Maarten (Dutch M)": "nl-NL-MaartenNeural",
    "🇳🇱 Colette (Dutch F)": "nl-NL-ColetteNeural",
    # Polish
    "🇵🇱 Marek (Polish M)": "pl-PL-MarekNeural",
    "🇵🇱 Zofia (Polish F)": "pl-PL-ZofiaNeural",
    # Swedish
    "🇸🇪 Mattias (Swedish M)": "sv-SE-MattiasNeural",
    "🇸🇪 Sofie (Swedish F)": "sv-SE-SofieNeural",
}

# ── ElevenLabs Integration ──────────────────────────────────────────────────
EL_BASE = "https://api.elevenlabs.io/v1"

def el_headers(api_key):
    return {"xi-api-key": api_key, "Accept": "application/json"}

def el_get_voices(api_key):
    """Return list of {voice_id, name, category, preview_url} dicts."""
    try:
        import requests, warnings; warnings.filterwarnings("ignore")
        r = requests.get(f"{EL_BASE}/voices", headers=el_headers(api_key), verify=False, timeout=15)
        if r.status_code == 200:
            voices = r.json().get("voices", [])
            return [{"voice_id": v["voice_id"], "name": v["name"],
                     "category": v.get("category","premade"),
                     "preview_url": v.get("preview_url","")} for v in voices]
        return []
    except Exception:
        return []

def el_get_subscription(api_key):
    """Return remaining character count for the free tier."""
    try:
        import requests, warnings; warnings.filterwarnings("ignore")
        r = requests.get(f"{EL_BASE}/user/subscription", headers=el_headers(api_key), verify=False, timeout=15)
        if r.status_code == 200:
            d = r.json()
            used = d.get("character_count", 0)
            limit = d.get("character_limit", 10000)
            return used, limit
        return None, None
    except Exception:
        return None, None

def el_clone_voice(api_key, name, audio_path, description="Cloned via VoxCraft Studio"):
    """Upload audio and create an Instant Voice Clone. Returns voice_id or None."""
    try:
        import requests, warnings; warnings.filterwarnings("ignore")
        with open(audio_path, "rb") as f:
            files = [("files", (os.path.basename(audio_path), f, "audio/mpeg"))]
            data = {"name": name, "description": description}
            r = requests.post(f"{EL_BASE}/voices/add",
                              headers={"xi-api-key": api_key},
                              data=data, files=files, verify=False, timeout=60)
        if r.status_code == 200:
            return r.json().get("voice_id")
        return None
    except Exception as e:
        return None

def el_delete_voice(api_key, voice_id):
    try:
        import requests, warnings; warnings.filterwarnings("ignore")
        requests.delete(f"{EL_BASE}/voices/{voice_id}", headers=el_headers(api_key), verify=False, timeout=15)
    except Exception:
        pass

def el_generate_tts(api_key, voice_id, text, output_path,
                    model_id="eleven_multilingual_v2", stability=0.5, similarity=0.8):
    """Generate TTS via ElevenLabs and save to output_path. Returns True on success."""
    try:
        import requests, warnings; warnings.filterwarnings("ignore")
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {"stability": stability, "similarity_boost": similarity}
        }
        hdrs = {**el_headers(api_key), "Content-Type": "application/json"}
        r = requests.post(f"{EL_BASE}/text-to-speech/{voice_id}",
                          headers=hdrs, json=payload, verify=False, timeout=120, stream=True)
        if r.status_code == 200:
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
            return True
        return False
    except Exception:
        return False
TEMPLATES = {
    "YouTube Intro": "Hey everyone, welcome back to the channel!\n\nIn today's video, we're going to dive deep into something really exciting. I've been working on this for weeks, and I can't wait to share it with you.\n\nSo grab your coffee, sit back, and let's get into it.",
    "Documentary": "In the heart of an untamed wilderness, a story unfolds that has remained hidden for centuries.\n\nScientists have long debated the origins of this phenomenon. But recent discoveries have shattered everything we thought we knew.\n\nWhat they found would change the course of history forever.",
    "Product Demo": "Introducing the next generation of innovation.\n\nDesigned for professionals who demand excellence, this product delivers unmatched performance, stunning reliability, and an experience that speaks for itself.\n\nAvailable now. The future starts today.",
    "Motivational": "Every champion was once a contender that refused to give up.\n\nThe road to greatness is paved with failure, doubt, and pain. But those who endure, those who push through when every voice says quit — they are the ones who change the world.\n\nYour moment is now. Rise.",
    "Podcast Intro": "You're listening to The Deep Dive, where we explore the stories behind the headlines.\n\nI'm your host, and today we have an incredible guest joining us. Their journey from obscurity to the global stage is nothing short of remarkable.\n\nLet's jump right in.",
    "Explainer": "Have you ever wondered how this actually works?\n\nMost people assume it's simple, but the reality is far more fascinating. Behind the scenes, there's an intricate process that makes everything possible.\n\nLet me break it down for you, step by step.",
}
