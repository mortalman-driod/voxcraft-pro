import streamlit as st
import os, asyncio, io, zipfile, json
import edge_tts
from voxcraft_utils import *

st.set_page_config(page_title="VoxCraft Studio", page_icon="🎙️", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

/* ── Reset & Base ── */
*,*::before,*::after{box-sizing:border-box;font-family:'Inter',sans-serif!important}
html,body,.stApp{background:#0D0D0D!important;color:#E8E8E8!important}

/* ── Hide Streamlit chrome ── */
#MainMenu,footer,[data-testid="stToolbar"]{display:none!important}

/* ── Main container ── */
.block-container{max-width:1280px!important;padding:0 2rem!important}

/* ── Sidebar ── */
div[data-testid="stSidebar"]{background:#111111!important;border-right:1px solid #222222!important;padding-top:1rem}
div[data-testid="stSidebar"] .stMarkdown p{color:#888!important;font-size:11px!important;text-transform:uppercase;letter-spacing:.08em;font-weight:600}
div[data-testid="stSidebar"] label{color:#aaa!important;font-size:13px!important}
div[data-testid="stSidebar"] .stSelectbox>div>div{background:#1A1A1A!important;border:1px solid #2A2A2A!important;color:#E8E8E8!important;border-radius:8px!important}
div[data-testid="stSidebar"] .stSlider [data-baseweb="slider"]{padding:0}

/* ── Inputs ── */
.stTextArea textarea,.stTextInput input{
  background:#1A1A1A!important;border:1px solid #2A2A2A!important;
  color:#E8E8E8!important;border-radius:8px!important;font-size:14px!important;
  transition:border-color .2s}
.stTextArea textarea:focus,.stTextInput input:focus{border-color:#FF6B35!important;box-shadow:0 0 0 2px rgba(255,107,53,.15)!important;outline:none}
.stSelectbox>div>div{background:#1A1A1A!important;border:1px solid #2A2A2A!important;color:#E8E8E8!important;border-radius:8px!important}

/* ── Buttons ── */
.stButton>button{
  background:#FF6B35!important;color:#fff!important;border:none!important;
  border-radius:8px!important;font-weight:600!important;font-size:13px!important;
  padding:10px 20px!important;transition:all .2s!important;letter-spacing:.01em}
.stButton>button:hover{background:#E55A27!important;box-shadow:0 4px 16px rgba(255,107,53,.35)!important;transform:translateY(-1px)!important}
.stButton>button:active{transform:translateY(0)!important}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{background:#111!important;border-bottom:1px solid #222!important;gap:0;padding:0}
.stTabs [data-baseweb="tab"]{
  background:transparent!important;color:#666!important;border:none!important;
  border-bottom:2px solid transparent!important;padding:12px 20px!important;
  font-size:13px!important;font-weight:500!important;transition:all .2s;margin:0}
.stTabs [aria-selected="true"]{
  color:#FF6B35!important;border-bottom:2px solid #FF6B35!important;background:transparent!important}
.stTabs [data-baseweb="tab-panel"]{padding:24px 0!important}

/* ── Cards ── */
.card{background:#161616;border:1px solid #222;border-radius:12px;padding:24px;margin-bottom:16px}
.card-sm{background:#161616;border:1px solid #222;border-radius:10px;padding:16px;margin-bottom:12px}
.card-header{font-size:11px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:.08em;margin-bottom:16px}
.card h3{font-size:16px!important;font-weight:600!important;color:#E8E8E8!important;margin:0 0 4px!important}

/* ── Segment row ── */
.seg-row{background:#161616;border:1px solid #222;border-radius:10px;padding:16px;margin-bottom:10px;transition:border-color .2s}
.seg-row:hover{border-color:#333}
.seg-num{font-size:11px;font-weight:700;color:#FF6B35;letter-spacing:.05em;margin-bottom:8px}
.seg-meta{font-size:11px;color:#555;margin-left:8px}

/* ── Metric pills ── */
.pill{display:inline-flex;align-items:center;gap:6px;background:#1A1A1A;border:1px solid #2A2A2A;border-radius:20px;padding:6px 14px;font-size:12px;color:#888}
.pill-val{font-size:16px;font-weight:700;color:#E8E8E8;margin-right:2px}
.pill-accent{color:#FF6B35!important}

/* ── Status banner ── */
.status-info{background:#1A1A1A;border:1px solid #2A2A2A;border-left:3px solid #FF6B35;border-radius:8px;padding:12px 16px;font-size:13px;color:#888}

/* ── Checkbox, radio ── */
.stCheckbox label{color:#aaa!important;font-size:13px!important}
.stRadio label{color:#aaa!important;font-size:13px!important}

/* ── Progress ── */
.stProgress>div>div{background:#FF6B35!important;border-radius:4px!important}

/* ── Expander ── */
.streamlit-expanderHeader{background:#161616!important;border:1px solid #222!important;border-radius:8px!important;color:#aaa!important}
.streamlit-expanderContent{background:#111!important;border:1px solid #222!important;border-top:none!important}

/* ── Scrollbar ── */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:#111}
::-webkit-scrollbar-thumb{background:#2A2A2A;border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:#333}
</style>""", unsafe_allow_html=True)

# ── State ──
D = st.session_state
if 'segments' not in D: D.segments = [{'text':'','voice':'en-US-AndrewNeural','rate':'-5%','pitch':'+0Hz','char':'Narrator'}]
if 'audio_files' not in D: D.audio_files = {}
if 'full_audio' not in D: D.full_audio = None
if 'segments_meta' not in D: D.segments_meta = []
if 'pron_dict' not in D: D.pron_dict = {}
if 'characters' not in D: D.characters = {'Narrator':'en-US-AndrewNeural'}
if 'bg_music_path' not in D: D.bg_music_path = None
if 'mixed_audio' not in D: D.mixed_audio = None

VL = list(VOICES.keys())
os.makedirs("workspace", exist_ok=True)

async def gen_audio(text, voice, rate, pitch, path):
    c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await c.save(path)

# ── Header ──
st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;padding:20px 0 16px;border-bottom:1px solid #1E1E1E;margin-bottom:8px">
  <div style="display:flex;align-items:center;gap:14px">
    <div style="width:38px;height:38px;background:#FF6B35;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px">🎙️</div>
    <div>
      <h1 style="margin:0;font-size:22px;font-weight:700;color:#E8E8E8;letter-spacing:-.02em">VoxCraft Studio</h1>
      <p style="margin:0;font-size:12px;color:#555">AI Voice Over · 60+ Neural Voices · 15 Languages</p>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:8px">
    <span style="background:#1A1A1A;border:1px solid #2A2A2A;border-radius:20px;padding:5px 14px;font-size:12px;font-weight:600;color:#4ADE80">● 100% FREE</span>
    <span style="background:#1A1A1A;border:1px solid #2A2A2A;border-radius:20px;padding:5px 14px;font-size:12px;color:#555">Edge Neural TTS</span>
  </div>
</div>""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("### 🎛️ Global Settings")
    default_voice = st.selectbox("Default Voice", VL, index=0)
    default_rate = st.slider("Speed", -50, 50, -5, format="%d%%")
    default_pitch = st.slider("Pitch (Hz)", -20, 20, 0, format="%+dHz")
    export_fmt = st.radio("Export Format", ["mp3","wav","ogg"], horizontal=True)
    
    st.markdown("---")
    st.markdown("### 📖 Pronunciation Dict")
    pron_input = st.text_area("word=replacement (one per line)", value="\n".join(f"{k}={v}" for k,v in D.pron_dict.items()), height=80, key="pron_ta")
    if st.button("💾 Save Dictionary", use_container_width=True):
        D.pron_dict = {}
        for line in pron_input.strip().split('\n'):
            if '=' in line:
                k,v = line.split('=',1)
                D.pron_dict[k.strip()] = v.strip()
        st.success(f"Saved {len(D.pron_dict)} entries")
    
    st.markdown("---")
    st.markdown("### 🎭 Characters")
    char_input = st.text_area("name=voice (one per line)", value="\n".join(f"{k}={v}" for k,v in D.characters.items()), height=80, key="char_ta")
    if st.button("💾 Save Characters", use_container_width=True):
        D.characters = {}
        for line in char_input.strip().split('\n'):
            if '=' in line:
                k,v = line.split('=',1)
                D.characters[k.strip()] = v.strip()
        st.success(f"Saved {len(D.characters)} characters")
    
    st.markdown("---")
    st.markdown("### 💾 Project")
    if st.button("📥 Save Project", use_container_width=True):
        proj = {'segments': D.segments, 'pron_dict': D.pron_dict, 'characters': D.characters}
        with open("workspace/project.json","w") as f: json.dump(proj, f, indent=2)
        st.success("Project saved!")
    proj_file = st.file_uploader("📂 Load Project", type=["json"], label_visibility="collapsed")
    if proj_file:
        proj = json.loads(proj_file.read())
        D.segments = proj.get('segments', D.segments)
        D.pron_dict = proj.get('pron_dict', {})
        D.characters = proj.get('characters', {'Narrator':'en-US-AndrewNeural'})
        st.success("Project loaded!")
        st.rerun()

    if st.button("🎧 Preview Voice"):
        p = "workspace/preview.mp3"
        asyncio.run(gen_audio("Hello! I'm your voice over artist.", VOICES[default_voice], f"{default_rate:+d}%", f"{default_pitch:+d}Hz", p))
        st.audio(p)

# ── Tabs ──
tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs(["📝 Script","🎤 Voice Studio","⚡ Generate","🎵 Music Mix","🔊 Preview","📤 Export"])

# ═══ TAB 1: SCRIPT EDITOR ═══
with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### ✍️ Script Editor")
    tc1,tc2 = st.columns([3,1])
    with tc1:
        tmpl = st.selectbox("📋 Load Template", ["— Select —"] + list(TEMPLATES.keys()))
        bulk = st.text_area("Paste script here", height=160, placeholder="Each paragraph becomes a segment...", key="bulk",
                           value=TEMPLATES[tmpl] if tmpl != "— Select —" else "")
    with tc2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✂️ Split by Paragraphs", use_container_width=True):
            if bulk.strip():
                paras = [p.strip() for p in bulk.strip().split('\n\n') if p.strip()]
                if not paras: paras = [p.strip() for p in bulk.strip().split('\n') if p.strip()]
                D.segments = [{'text':p,'voice':VOICES[default_voice],'rate':f'{default_rate:+d}%','pitch':f'{default_pitch:+d}Hz','char':'Narrator'} for p in paras]
                st.rerun()
        if st.button("➕ Add Segment", use_container_width=True):
            D.segments.append({'text':'','voice':VOICES[default_voice],'rate':f'{default_rate:+d}%','pitch':f'{default_pitch:+d}Hz','char':'Narrator'})
            st.rerun()
        # SSML quick inserts
        st.markdown("**SSML Quick Insert:**")
        ssml_type = st.selectbox("Insert", ["Pause (500ms)","Pause (1s)","Pause (2s)","...long pause..."], label_visibility="collapsed")
        
        uploaded = st.file_uploader("📄 Import .txt", type=["txt"], label_visibility="collapsed")
        if uploaded:
            content = uploaded.read().decode('utf-8')
            paras = [p.strip() for p in content.split('\n\n') if p.strip()]
            D.segments = [{'text':p,'voice':VOICES[default_voice],'rate':f'{default_rate:+d}%','pitch':f'{default_pitch:+d}Hz','char':'Narrator'} for p in paras]
            st.rerun()
        # Batch upload
        batch = st.file_uploader("📁 Batch .txt files", type=["txt"], accept_multiple_files=True, label_visibility="collapsed")
        if batch:
            D.segments = []
            for f in batch:
                txt = f.read().decode('utf-8').strip()
                D.segments.append({'text':txt,'voice':VOICES[default_voice],'rate':f'{default_rate:+d}%','pitch':f'{default_pitch:+d}Hz','char':'Narrator'})
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Segments
    tw = 0; te = 0.0
    for i, seg in enumerate(D.segments):
        wc = len(seg['text'].split()); ed = estimate_duration(seg['text'], seg['rate'])
        tw += wc; te += ed
        st.markdown(f'<div class="seg-row"><span style="color:#7c5cfc;font-weight:600">Segment {i+1}</span> <span style="color:#4444aa;font-size:12px">· {wc} words · ~{ed:.1f}s · 🎭 {seg["char"]}</span></div>', unsafe_allow_html=True)
        s1,s2 = st.columns([3,1])
        with s1:
            nt = st.text_area("Text", value=seg['text'], height=90, key=f"st_{i}", label_visibility="collapsed", placeholder="Enter narration...")
            D.segments[i]['text'] = nt
        with s2:
            cvl = [k for k,v in VOICES.items() if v==seg['voice']]
            vi = VL.index(cvl[0]) if cvl else 0
            nv = st.selectbox("Voice", VL, index=vi, key=f"sv_{i}")
            D.segments[i]['voice'] = VOICES[nv]
            r1,r2 = st.columns(2)
            with r1:
                rv = st.slider("Spd", -50, 50, int(seg['rate'].replace('%','').replace('+','')), key=f"sr_{i}")
                D.segments[i]['rate'] = f"{rv:+d}%"
            with r2:
                pv = st.slider("Pit", -20, 20, int(seg['pitch'].replace('Hz','').replace('+','')), key=f"sp_{i}")
                D.segments[i]['pitch'] = f"{pv:+d}Hz"
            # Character assignment
            char_name = st.selectbox("Character", list(D.characters.keys()), index=0, key=f"sc_{i}")
            D.segments[i]['char'] = char_name
            bc1,bc2,bc3 = st.columns(3)
            with bc1:
                if i > 0 and st.button("⬆️", key=f"up_{i}"):
                    D.segments[i], D.segments[i-1] = D.segments[i-1], D.segments[i]
                    st.rerun()
            with bc2:
                if i < len(D.segments)-1 and st.button("⬇️", key=f"dn_{i}"):
                    D.segments[i], D.segments[i+1] = D.segments[i+1], D.segments[i]
                    st.rerun()
            with bc3:
                if len(D.segments) > 1 and st.button("🗑️", key=f"rm_{i}"):
                    D.segments.pop(i); st.rerun()
    
    m1,m2,m3 = st.columns(3)
    with m1: st.markdown(f'<div class="pill-box"><h3>{len(D.segments)}</h3><p>Segments</p></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="pill-box"><h3>{tw}</h3><p>Words</p></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="pill-box"><h3>~{te:.0f}s</h3><p>Est. Duration</p></div>', unsafe_allow_html=True)

# ═══ TAB 2: VOICE STUDIO ═══
with tab2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🎤 Voice A/B Comparison")
    st.markdown("Hear the same text in different voices to find your perfect match.")
    comp_text = st.text_input("Comparison text", value="The future belongs to those who believe in the beauty of their dreams.", key="comp_txt")
    cc1,cc2,cc3 = st.columns(3)
    with cc1:
        va = st.selectbox("Voice A", VL, index=0, key="va")
    with cc2:
        vb = st.selectbox("Voice B", VL, index=1, key="vb")
    with cc3:
        vc = st.selectbox("Voice C", VL, index=13, key="vc")
    
    if st.button("🔊 Compare All Three", use_container_width=True):
        for idx, (label, voice_label) in enumerate([("A",va),("B",vb),("C",vc)]):
            p = f"workspace/compare_{label}.mp3"
            asyncio.run(gen_audio(comp_text, VOICES[voice_label], f"{default_rate:+d}%", f"{default_pitch:+d}Hz", p))
            st.markdown(f"**Voice {label}: {voice_label}**")
            st.audio(p)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🌍 Voice Explorer")
    lang_filter = st.selectbox("Filter by Language", ["All","English","Spanish","French","Portuguese","German","Italian","Japanese","Chinese","Korean","Arabic","Hindi","Russian","Turkish","Dutch","Polish","Swedish"])
    lang_codes = {"English":"en","Spanish":"es","French":"fr","Portuguese":"pt","German":"de","Italian":"it","Japanese":"ja","Chinese":"zh","Korean":"ko","Arabic":"ar","Hindi":"hi","Russian":"ru","Turkish":"tr","Dutch":"nl","Polish":"pl","Swedish":"sv"}
    filtered = VOICES if lang_filter=="All" else {k:v for k,v in VOICES.items() if v.startswith(lang_codes.get(lang_filter,"en"))}
    cols = st.columns(3)
    for i,(label,vid) in enumerate(filtered.items()):
        with cols[i%3]:
            st.markdown(f'<div class="seg-row" style="padding:8px 12px"><b style="color:#b0a0ff;font-size:13px">{label}</b><br><code style="font-size:10px;color:#4444aa">{vid}</code></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ═══ TAB 3: GENERATE ═══
with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### ⚡ Generate Voice Over")
    do_normalize = st.checkbox("🔊 Normalize audio levels", value=True)
    gc1,gc2 = st.columns(2)
    with gc1: gen_ind = st.button("🎤 Generate All Segments", use_container_width=True)
    with gc2: gen_full = st.button("🎬 Generate & Stitch Full", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if gen_ind or gen_full:
        valid = [s for s in D.segments if s['text'].strip()]
        if not valid:
            st.error("❌ No segments with text.")
        else:
            bar = st.progress(0, text="🎙️ Starting...")
            D.audio_files = {}
            D.segments_meta = []
            # Parallel generation for speed (crucial for 30-60 min scripts)
            sem = asyncio.Semaphore(5)
            
            async def gen_task(idx, s):
                async with sem:
                    out_path = f"workspace/segment_{idx}.mp3"
                    txt = apply_pronunciation(s['text'], D.pron_dict)
                    voice = D.characters.get(s.get('char',''), s['voice']) if s.get('char','') in D.characters else s['voice']
                    await gen_audio(txt, voice, s['rate'], s['pitch'], out_path)
                    if do_normalize:
                        norm_out = f"workspace/segment_{idx}_norm.mp3"
                        normalize_audio(out_path, norm_out)
                        if os.path.exists(norm_out) and os.path.getsize(norm_out) > 0:
                            os.replace(norm_out, out_path)
                    dur = get_audio_duration(out_path)
                    return idx, out_path, dur, s['text']

            async def run_all():
                tasks = [gen_task(i, s) for i, s in enumerate(valid)]
                return await asyncio.gather(*tasks)

            try:
                results = asyncio.run(run_all())
                for idx, path, dur, text in sorted(results):
                    D.audio_files[idx] = path
                    D.segments_meta.append({'text': text, 'duration': dur, 'path': path})
                
                if gen_full and D.segments_meta:
                    bar.progress(90, text="🎬 Stitching...")
                    full_path = f"workspace/full_voiceover.{export_fmt}"
                    stitch_audio_files([m['path'] for m in D.segments_meta], full_path)
                    D.full_audio = full_path
                    tdur = sum(m['duration'] for m in D.segments_meta)
                    bar.progress(100, text="✅ Done!")
                    st.success(f"🎉 Full voiceover generated! Total duration: {tdur/60:.1f} minutes")
                else:
                    bar.progress(100, text="✅ All segments generated!")
            except Exception as e:
                st.error(f"❌ Generation failed: {e}")

# ═══ TAB 4: MUSIC MIX ═══
with tab4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🎵 Background Music Mixer")
    if D.full_audio and os.path.exists(D.full_audio):
        mc1,mc2,mc3 = st.columns(3)
        with mc1:
            music_style = st.selectbox("Music Style", ["cinematic","calm","energetic","mysterious","inspiring","ambient"])
        with mc2:
            music_vol = st.slider("Music Volume", 0.05, 0.5, 0.12, 0.01)
        with mc3:
            st.markdown("<br>", unsafe_allow_html=True)
            gen_music = st.button("🎵 Generate & Mix", use_container_width=True)
        
        if gen_music:
            with st.spinner("🎵 Generating ambient music..."):
                dur = get_audio_duration(D.full_audio)
                music_path = generate_ambient_music(dur, music_style)
                D.bg_music_path = music_path
                st.audio(music_path)
                st.success("✅ Music generated!")
            with st.spinner("🔀 Mixing voice + music..."):
                mixed = f"workspace/mixed_output.{export_fmt}"
                mix_audio_with_music(D.full_audio, music_path, mixed, music_vol)
                D.mixed_audio = mixed
                st.audio(mixed)
                st.success("🎉 Mixed audio ready!")
    else:
        st.markdown('<div class="status-info">⏳ Generate your voiceover first (Tab 3), then come here to add background music.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ═══ TAB 5: PREVIEW ═══
with tab5:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🔊 Preview & Waveform")
    # Full audio
    final = D.mixed_audio if D.mixed_audio and os.path.exists(str(D.mixed_audio or '')) else D.full_audio
    if final and os.path.exists(final):
        st.markdown("#### 🎬 Full Project")
        st.audio(final)
        try:
            wf = make_waveform(final)
            st.image(wf, use_container_width=True)
        except Exception as e:
            st.warning(f"Waveform: {e}")
        st.markdown("---")
    # Individual segments
    if D.audio_files:
        st.markdown("#### 🎤 Individual Segments")
        for idx, path in D.audio_files.items():
            if os.path.exists(path):
                with st.expander(f"Segment {idx+1} — {D.segments[idx]['text'][:50]}...", expanded=False):
                    st.audio(path)
                    try: st.image(make_waveform(path), use_container_width=True)
                    except: pass
    else:
        st.markdown('<div class="status-info">⏳ No audio yet. Generate in Tab 3.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Video timeline
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🎬 Video Timeline Sync")
    video_file = st.file_uploader("Upload your video to sync", type=["mp4","mov","avi","mkv"])
    if video_file and D.segments_meta:
        vpath = "workspace/uploaded_video" + os.path.splitext(video_file.name)[1]
        with open(vpath, "wb") as f: f.write(video_file.read())
        vdur = get_video_duration(vpath)
        tdur = sum(m['duration'] for m in D.segments_meta)
        st.markdown(f"**Video:** {vdur:.1f}s &nbsp;|&nbsp; **Voiceover:** {tdur:.1f}s")
        if abs(vdur - tdur) > 2:
            diff = vdur - tdur
            label = "Video" if diff > 0 else "Voiceover"
            st.warning(f"⚠️ {label} is {abs(diff):.1f}s longer. Adjust speed to match.")
            suggested_rate = int(((tdur / vdur) - 1) * 100)
            st.info(f"💡 Suggested global speed: {suggested_rate:+d}%")
        # Timeline visualization
        if D.segments_meta:
            cols_tl = st.columns(len(D.segments_meta))
            colors = ["#7c5cfc","#5caafc","#5cfcaa","#fc5c7c","#fcaa5c","#aa5cfc"]
            for i, (col, meta) in enumerate(zip(cols_tl, D.segments_meta)):
                with col:
                    pct = (meta['duration']/max(tdur,0.1))*100
                    st.markdown(f'<div style="background:{colors[i%len(colors)]};border-radius:6px;padding:6px;text-align:center;font-size:10px;color:#fff">S{i+1}<br>{meta["duration"]:.1f}s</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ═══ TAB 6: EXPORT ═══
with tab6:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 📤 Export")
    final_audio = D.mixed_audio if D.mixed_audio and os.path.exists(str(D.mixed_audio or '')) else D.full_audio
    if final_audio and os.path.exists(final_audio):
        e1,e2,e3,e4 = st.columns(4)
        with e1:
            with open(final_audio,'rb') as f:
                st.download_button(f"⬇️ Audio (.{export_fmt})", f, file_name=f"VoxCraft_voiceover.{export_fmt}", mime=f"audio/{export_fmt}", use_container_width=True)
        with e2:
            if D.segments_meta:
                st.download_button("📄 SRT Subtitles", gen_srt(D.segments_meta), file_name="subtitles.srt", mime="text/plain", use_container_width=True)
        with e3:
            if D.audio_files:
                zbuf = io.BytesIO()
                with zipfile.ZipFile(zbuf,'w',zipfile.ZIP_DEFLATED) as zf:
                    for idx,path in D.audio_files.items():
                        if os.path.exists(path): zf.write(path, f"segment_{idx+1}.mp3")
                    if os.path.exists(final_audio): zf.write(final_audio, f"full_voiceover.{export_fmt}")
                    if D.segments_meta: zf.writestr("subtitles.srt", gen_srt(D.segments_meta))
                    proj = {'segments':D.segments,'pron_dict':D.pron_dict,'characters':D.characters}
                    zf.writestr("project.json", json.dumps(proj, indent=2))
                zbuf.seek(0)
                st.download_button("📦 ZIP Bundle", zbuf, file_name="VoxCraft_project.zip", mime="application/zip", use_container_width=True)
        with e4:
            if st.button("🎬 Export Video", use_container_width=True):
                with st.spinner("🎬 Creating video..."):
                    dur = get_audio_duration(final_audio)
                    vout = "workspace/voiceover_video.mp4"
                    export_video_with_audio(final_audio, vout, dur)
                    if os.path.exists(vout):
                        with open(vout,'rb') as f:
                            st.download_button("⬇️ Download MP4", f, file_name="VoxCraft_video.mp4", mime="video/mp4", use_container_width=True)
                        st.success("✅ Video exported!")
        st.markdown('---')
        st.markdown('<div class="status-info">💡 Import the SRT into Premiere Pro, DaVinci Resolve, or CapCut for auto-synced subtitles.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-info">⏳ Generate your voiceover first.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div style="text-align:center;padding:12px;color:#4444aa;font-size:11px"><b style="color:#7c5cfc">VoxCraft Pro</b> · Free AI Voice Over Agent · 60+ Voices · 15 Languages · No API Keys</div>', unsafe_allow_html=True)
