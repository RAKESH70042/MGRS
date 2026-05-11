import streamlit as st
import requests
import json
import time

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Medical Scribe — MGRS",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem !important; max-width: 100% !important; background: #f7f9fb; }

.topnav {
    background: #f7f9fb; border-bottom: 1px solid #c3c6d7;
    padding: 0 48px; height: 64px; display: flex;
    align-items: center; justify-content: space-between;
    position: sticky; top: 0; z-index: 999;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.topnav-brand {
    font-family: 'Manrope', sans-serif; font-size: 1.4rem;
    font-weight: 800; color: #004ac6;
}
.page-title {
    font-family: 'Manrope', sans-serif; font-size: 2rem;
    font-weight: 700; color: #191c1e; margin-bottom: 4px;
}
.page-subtitle { color: #434655; font-size: 1rem; margin-bottom: 28px; }

.rec-dot {
    display: inline-block; width: 10px; height: 10px;
    border-radius: 50%; background: #ba1a1a;
    animation: blink 1s infinite; margin-right: 6px;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }

.turn-doctor {
    background: #dbe1ff; border-radius: 10px;
    padding: 8px 14px; margin: 4px 0;
    font-size: 0.88rem;
}
.turn-patient {
    background: #e6f9f2; border-radius: 10px;
    padding: 8px 14px; margin: 4px 0;
    font-size: 0.88rem;
}
.speaker-label {
    font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin-bottom: 2px;
}
.section-card {
    background: #fff; border: 1px solid #c3c6d7;
    border-radius: 12px; padding: 20px 24px;
    margin-bottom: 16px;
}
.sec-label {
    font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: #004ac6; margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# ── nav ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topnav">
    <div class="topnav-brand">⚕️ MGRS — Medical Scribe</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-title">🎙️ Consultation Assistant</div>
<div class="page-subtitle">Live AI scribe — listens, transcribes, and generates structured medical reports.</div>
""", unsafe_allow_html=True)

# ── session state ──────────────────────────────────────────────────────────────
for k, v in {
    "consultation_id": None,
    "recording":       False,
    "turns":           [],
    "report":          None,
    "summary":         None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── layout ─────────────────────────────────────────────────────────────────────
left, right = st.columns([1, 1], gap="large")

# ══════════════════════════════════════════════════════════════════════════════
# LEFT PANEL — controls + live transcript
# ══════════════════════════════════════════════════════════════════════════════
with left:

    # Patient / Doctor IDs
    st.markdown('<div class="sec-label">Session Info</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    patient_id = c1.text_input("Patient ID", placeholder="e.g. PAT001")
    doctor_id  = c2.text_input("Doctor ID",  placeholder="e.g. DR001")

    st.markdown("<br>", unsafe_allow_html=True)

    # Start / Stop buttons
    b1, b2 = st.columns(2)

    with b1:
        if st.button(
            "🔴 Start Consultation",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.recording
        ):
            try:
                r = requests.post(
                    f"{API_BASE}/consultation/start",
                    params={"patient_id": patient_id, "doctor_id": doctor_id}
                )
                data = r.json()
                st.session_state.consultation_id = data["consultation_id"]
                st.session_state.recording       = True
                st.session_state.turns           = []
                st.session_state.report          = None

                # Start audio pipeline on backend
                requests.post(f"{API_BASE}/transcription/start_pipeline")

                st.rerun()
            except Exception as e:
                st.error(str(e))

    with b2:
        if st.button(
            "⏹ Stop & Generate Report",
            use_container_width=True,
            disabled=not st.session_state.recording
        ):
            try:
                requests.post(f"{API_BASE}/consultation/stop")
                st.session_state.recording = False

                # Generate report
                cid = st.session_state.consultation_id
                with st.spinner("MedGemma generating report…"):
                    r = requests.post(f"{API_BASE}/report/generate/{cid}")
                    data = r.json()
                    st.session_state.report  = data.get("report", {})
                    st.session_state.summary = data.get("summary", "")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── LIVE TRANSCRIPT PANEL ──────────────────────────────────────────────────
    if st.session_state.recording:
        st.markdown(
            '<div class="sec-label"><span class="rec-dot"></span>Live Transcript</div>',
            unsafe_allow_html=True
        )
    elif st.session_state.turns:
        st.markdown('<div class="sec-label">Transcript</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="color:#737686;font-size:0.88rem;">Start a consultation to see the live transcript here.</div>',
            unsafe_allow_html=True
        )

    # Poll for new turns while recording
    if st.session_state.recording and st.session_state.consultation_id:
        try:
            r = requests.get(
                f"{API_BASE}/transcription/{st.session_state.consultation_id}/full",
                timeout=3
            )
            st.session_state.turns = r.json().get("turns", [])
        except Exception:
            pass
        time.sleep(0.5)
        st.rerun()

    # Render turns
    transcript_html = ""
    for turn in st.session_state.turns:
        spk  = turn.get("speaker", "Unknown")
        txt  = turn.get("text", "")
        ts   = turn.get("timestamp", 0)
        cls  = "turn-doctor" if spk == "Doctor" else "turn-patient"
        color= "#004ac6" if spk == "Doctor" else "#006242"
        transcript_html += f"""
        <div class="{cls}">
            <div class="speaker-label" style="color:{color}">{spk} &nbsp;·&nbsp; {ts:.1f}s</div>
            {txt}
        </div>"""

    if transcript_html:
        st.markdown(
            f'<div style="max-height:480px;overflow-y:auto;">{transcript_html}</div>',
            unsafe_allow_html=True
        )

# ══════════════════════════════════════════════════════════════════════════════
# RIGHT PANEL — structured report
# ══════════════════════════════════════════════════════════════════════════════
with right:
    st.markdown('<div class="sec-label">Structured Medical Report</div>', unsafe_allow_html=True)

    if not st.session_state.report:
        st.markdown(
            '<div style="color:#737686;font-size:0.88rem;">Report will appear here after the consultation ends.</div>',
            unsafe_allow_html=True
        )
    else:
        report = st.session_state.report
        cid    = st.session_state.consultation_id

        if st.session_state.summary:
            st.info(f"📝 {st.session_state.summary}")

        # ── Editable JSON view ──────────────────────────────────────────────
        with st.expander("🔍 View / Edit Raw JSON", expanded=False):
            json_key = f"report_json_{cid}"
            if json_key not in st.session_state:
                st.session_state[json_key] = json.dumps(report, indent=2)

            edited = st.text_area(
                "report_editor",
                label_visibility="collapsed",
                value=st.session_state[json_key],
                height=400,
                key=f"report_ta_{cid}"
            )
            json_ok = True
            try:
                parsed = json.loads(edited)
                st.markdown('<div style="font-size:0.76rem;color:#006242;">✔ Valid JSON</div>', unsafe_allow_html=True)
            except json.JSONDecodeError as e:
                json_ok = False
                st.markdown(f'<div style="font-size:0.76rem;color:#ba1a1a;">✘ {e}</div>', unsafe_allow_html=True)

            if st.button("💾 Save JSON edits", disabled=not json_ok):
                try:
                    requests.put(
                        f"{API_BASE}/report/{cid}",
                        json={"report": parsed}
                    )
                    st.session_state.report   = parsed
                    st.session_state[json_key] = json.dumps(parsed, indent=2)
                    st.success("Saved.")
                except Exception as e:
                    st.error(str(e))

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Structured field view ───────────────────────────────────────────
        fields = [
            ("🤒 Patient Complaints",   "patient_complaints"),
            ("🌡 Symptoms",             "symptoms"),
            ("🔬 Doctor Observations",  "doctor_observations"),
            ("🏥 Diagnosis",            "diagnosis"),
            ("🧪 Tests Recommended",    "tests_recommended"),
            ("📋 Treatment Plan",       "treatment_plan"),
            ("🔁 Follow-up",            "follow_up_instructions"),
            ("⚠️ Important Notes",      "important_notes"),
            ("🏷 ICD-10 Suggestions",   "icd10_suggestions"),
        ]

        for label, key in fields:
            val = report.get(key)
            if val:
                st.markdown(f"""
                <div class="section-card">
                    <div class="sec-label">{label}</div>
                    <div style="font-size:0.88rem;color:#191c1e;">{val}</div>
                </div>""", unsafe_allow_html=True)

        # ── Medications table ───────────────────────────────────────────────
        meds = report.get("prescribed_medicines", [])
        if meds:
            st.markdown("""
            <div class="sec-label">💊 Prescribed Medicines</div>
            """, unsafe_allow_html=True)
            st.dataframe(meds, use_container_width=True, hide_index=True)

        # ── SOAP Note ──────────────────────────────────────────────────────
        soap = report.get("soap_note")
        if soap:
            st.markdown("""
            <div class="sec-label">📄 SOAP Note</div>
            """, unsafe_allow_html=True)
            st.code(soap, language=None)

# ── CONSULTATION HISTORY ───────────────────────────────────────────────────────
st.markdown("<br><br>", unsafe_allow_html=True)
with st.expander("🗃️ Consultation History", expanded=False):
    try:
        resp = requests.get(f"{API_BASE}/consultations")
        records = resp.json()
        if records:
            rows = []
            for rec in records:
                rows.append({
                    "ID":         rec.get("consultation_id", "—"),
                    "Patient":    rec.get("patient_id") or "—",
                    "Doctor":     rec.get("doctor_id")  or "—",
                    "Started":    (rec.get("started_at") or "—")[:19],
                    "Status":     rec.get("status", "—"),
                    "Summary":    rec.get("summary") or "—",
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("No consultations yet.")
    except Exception as e:
        st.error(str(e))