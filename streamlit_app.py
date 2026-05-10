import streamlit as st
import requests
import json

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="MedGemma Prescription Review",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── GLOBAL STYLES ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* TOP NAV */
.topnav {
    background: #f7f9fb;
    border-bottom: 1px solid #c3c6d7;
    padding: 0 48px;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 999;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.topnav-brand {
    display: flex; align-items: center; gap: 10px;
    font-family: 'Manrope', sans-serif;
    font-size: 1.4rem; font-weight: 800;
    color: #004ac6;
}
.topnav-nav { display: flex; align-items: center; gap: 32px; }
.topnav-nav a {
    text-decoration: none; font-size: 0.9rem;
    color: #434655; padding-bottom: 4px;
    transition: color 0.15s;
}
.topnav-nav a.active {
    color: #004ac6; border-bottom: 2px solid #004ac6; font-weight: 600;
}
.topnav-nav a:hover { color: #004ac6; }
.avatar {
    width: 40px; height: 40px; border-radius: 50%;
    background: #dbe1ff; display: flex; align-items: center;
    justify-content: center; font-weight: 700; color: #004ac6;
    font-size: 0.9rem; border: 1px solid #c3c6d7;
}

/* MAIN CONTENT - padding applied via block-container override */
.block-container { padding: 2rem 3rem 2rem 3rem !important; max-width: 100% !important; background: #f7f9fb; }

/* PAGE HEADER */
.page-title {
    font-family: 'Manrope', sans-serif;
    font-size: 2.1rem; font-weight: 700;
    color: #191c1e; margin-bottom: 6px;
}
.page-subtitle { color: #434655; font-size: 1rem; margin-bottom: 32px; }

/* STEP CARDS */
.step-card {
    background: #ffffff;
    border: 1px solid #c3c6d7;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    margin-bottom: 4px;
}
.step-label {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #004ac6; margin-bottom: 10px;
    display: flex; align-items: center; gap: 8px;
}
.dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #004ac6; display: inline-block;
    animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.35} }
.step-title {
    font-family: 'Manrope', sans-serif;
    font-size: 1.25rem; font-weight: 700; color: #191c1e; margin-bottom: 4px;
}
.step-desc { font-size: 0.84rem; color: #434655; margin-bottom: 16px; }

/* UPLOAD ZONE */
.upload-zone {
    border: 2px dashed #c3c6d7; border-radius: 10px;
    padding: 36px 20px; text-align: center; background: #f2f4f6;
}
.upload-hint { font-size: 0.75rem; color: #737686; margin-top: 8px; }

/* LOCKED */
.locked-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: #fff; border: 1px solid #c3c6d7;
    border-radius: 99px; padding: 8px 18px;
    font-size: 0.8rem; font-weight: 600; color: #434655;
    box-shadow: 0 2px 6px rgba(0,0,0,0.07);
    margin-top: 10px;
}

/* SECTION TITLE */
.sec-title {
    font-family: 'Manrope', sans-serif;
    font-size: 1.15rem; font-weight: 700;
    color: #191c1e; margin-bottom: 14px;
    display: flex; align-items: center; gap: 8px;
}

/* BADGE */
.badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 99px;
    font-size: 0.72rem; font-weight: 700;
}
.badge-completed { background: #e6f9f2; color: #006242; }
.badge-pending   { background: #dbe1ff; color: #004ac6; }
.badge-rejected  { background: #ffdad6; color: #ba1a1a; }

/* RECORDS TABLE */
.records-table {
    width: 100%; border-collapse: collapse;
    background: #fff; border-radius: 12px; overflow: hidden;
    border: 1px solid #c3c6d7; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.records-table th {
    background: #f2f4f6; padding: 12px 20px;
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; color: #737686; text-align: left;
    border-bottom: 1px solid #c3c6d7;
}
.records-table td {
    padding: 14px 20px; font-size: 0.88rem;
    color: #191c1e; border-bottom: 1px solid #e0e3e5;
}
.records-table tr:last-child td { border-bottom: none; }
.records-table tr:hover td { background: #f2f4f6; }

/* BUTTON OVERRIDES */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    transition: all 0.15s !important;
}

/* FOOTER */
.site-footer {
    background: #fff; border-top: 1px solid #c3c6d7;
    padding: 20px 48px;
    display: flex; align-items: center; justify-content: space-between;
    font-size: 0.78rem; color: #737686;
}
.site-footer a { color: #434655; text-decoration: none; margin-left: 20px; }
.site-footer a:hover { color: #004ac6; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ──────────────────────────────────────────────────────────────
for key in ["extraction_data", "review_response", "upload_data", "uploaded_file_name"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ── TOP NAV ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topnav">
    <div class="topnav-brand">⚕️ MedGemma</div>
    <nav class="topnav-nav">
        <a href="#">Dashboard</a>
        <a href="#" class="active">Prescriptions</a>
        <a href="#">Analytics</a>
        <a href="#">Patients</a>
    </nav>
    <div class="avatar">Dr</div>
</div>
""", unsafe_allow_html=True)

# ── MAIN CONTENT ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-title">💊 MedGemma Prescription Review</div>
<div class="page-subtitle">Advanced AI-powered clinical verification and digital record extraction system.</div>
""", unsafe_allow_html=True)

# ── STEP CARDS ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("""
    <div class="step-card">
        <div class="step-label"><span class="dot"></span> STEP 01</div>
        <div class="step-title">1. Upload Prescription</div>
        <div class="step-desc">Choose an image of the physical prescription to initiate scanning.</div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        st.image(uploaded_file, use_container_width=True)
        if st.session_state.uploaded_file_name != uploaded_file.name:
            with st.spinner("Uploading…"):
                try:
                    resp = requests.post(
                        f"{API_BASE}/upload",
                        files={"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                    )
                    st.session_state.upload_data = resp.json()
                    st.session_state.uploaded_file_name = uploaded_file.name
                    st.session_state.extraction_data = None
                    st.session_state.review_response = None
                except Exception as e:
                    st.error(f"Upload failed: {e}")

        if st.session_state.upload_data:
            st.success(f"✅ **{st.session_state.upload_data.get('filename', uploaded_file.name)}** ready for extraction")
    else:
        st.markdown("""
        <div class="upload-zone">
            <div style="font-size:2.5rem;margin-bottom:12px">☁️</div>
            <div style="font-size:0.88rem;color:#434655;font-weight:500">Drop your file here or use the uploader above</div>
            <div class="upload-hint">200MB per file &nbsp;·&nbsp; PNG, JPG, JPEG</div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    unlocked = uploaded_file is not None and st.session_state.upload_data is not None
    opacity = "1" if unlocked else "0.5"

    st.markdown(f"""
    <div class="step-card" style="opacity:{opacity}">
        <div class="step-label">STEP 02</div>
        <div class="step-title">2. Run Extraction</div>
        <div class="step-desc">AI reads the prescription and extracts structured clinical data.</div>
    </div>
    """, unsafe_allow_html=True)

    if unlocked:
        if st.button("✨ Run AI Analysis", type="primary", use_container_width=True):
            with st.spinner("MedGemma reading prescription… (~60s)"):
                try:
                    r = requests.get(
                        f"{API_BASE}/extract",
                        params={"file_name": uploaded_file.name}
                    )
                    st.session_state.extraction_data = r.json()
                    st.session_state.review_response = None
                    st.success("✅ Extraction complete!")
                except Exception as e:
                    st.error(str(e))

        # ── EXTRACTION RESULTS ────────────────────────────────────────────────
        if st.session_state.extraction_data and "record_id" in st.session_state.extraction_data:
            data = st.session_state.extraction_data
            meta = data.get("run_metadata", {})

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class="sec-title">
                📋 Extraction Results &nbsp;
                <span style="font-size:0.76rem;background:#dbe1ff;color:#004ac6;
                padding:3px 12px;border-radius:99px;font-weight:600">
                    {data.get('record_id','')}
                </span>
            </div>
            """, unsafe_allow_html=True)

            st.json(data)
            st.caption(
                f"🤖 **{meta.get('model_name','')} {meta.get('model_version','')}** &nbsp;·&nbsp; "
                f"⏱ {meta.get('latency_ms',0)/1000:.1f}s &nbsp;·&nbsp; "
                f"🏷 {meta.get('prompt_template','')}"
            )

            # ── REVIEW ────────────────────────────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="sec-title">✍️ Review</div>', unsafe_allow_html=True)

            reviewer_notes = st.text_area(
                "Reviewer Notes (optional)",
                placeholder="Add clinical notes, flags, or comments…",
                height=90
            )

            record_id = data.get("record_id")
            b1, b2, _ = st.columns([1, 1, 4])

            with b1:
                if st.button("✅ Approve", type="primary", use_container_width=True):
                    try:
                        r = requests.put(
                            f"{API_BASE}/review/{record_id}",
                            params={"status": "approved", "reviewer_notes": reviewer_notes}
                        )
                        st.session_state.review_response = r.json()
                    except Exception as e:
                        st.error(str(e))

            with b2:
                if st.button("❌ Reject", use_container_width=True):
                    try:
                        r = requests.put(
                            f"{API_BASE}/review/{record_id}",
                            params={"status": "rejected", "reviewer_notes": reviewer_notes}
                        )
                        st.session_state.review_response = r.json()
                    except Exception as e:
                        st.error(str(e))

            if st.session_state.review_response:
                st.json(st.session_state.review_response)

    else:
        st.markdown("""
        <div class="locked-badge">🔒 &nbsp;Complete Step 1 First</div>
        """, unsafe_allow_html=True)

# ── STORED RECORDS ─────────────────────────────────────────────────────────────
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<div class="sec-title">🗃️ Stored Records</div>', unsafe_allow_html=True)

try:
    records_resp = requests.get(f"{API_BASE}/records")
    records = records_resp.json()

    if records:
        rows = []
        for rec in records:
            review = json.loads(rec.get("review_json", "{}"))
            status = review.get("status", "pending")
            if status == "approved":
                badge = '<span class="badge badge-completed">● Completed</span>'
            elif status == "rejected":
                badge = '<span class="badge badge-rejected">● Rejected</span>'
            else:
                badge = '<span class="badge badge-pending">● Pending</span>'
            rows.append({
                "patient":   rec.get("patient_name", "—"),
                "med":       rec.get("medication", "—"),
                "uploaded":  rec.get("uploaded_at", rec.get("source_file", "—")),
                "status":    badge,
                "record_id": rec.get("record_id", "—"),
            })

        table_rows = ""
        for row in rows:
            table_rows += f"""
            <tr>
                <td style="font-weight:600">{row['patient']}</td>
                <td style="color:#434655">{row['med']}</td>
                <td style="color:#434655">{row['uploaded']}</td>
                <td>{row['status']}</td>
                <td style="color:#737686;font-size:0.78rem">{row['record_id']}</td>
            </tr>"""

        st.markdown(f"""
        <table class="records-table">
            <thead>
                <tr>
                    <th>Patient Name</th>
                    <th>Medication</th>
                    <th>Uploaded</th>
                    <th>Status</th>
                    <th>Record ID</th>
                </tr>
            </thead>
            <tbody>{table_rows}</tbody>
        </table>
        <div style="margin-top:8px;font-size:0.78rem;color:#737686">{len(rows)} records total</div>
        """, unsafe_allow_html=True)
    else:
        st.info("No records yet.")

except Exception as e:
    st.error(str(e))


# ── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="site-footer">
    <div>© 2024 MedGemma Clinical Systems. &nbsp; HIPAA Compliant.</div>
    <div>
        <a href="#">Privacy Protocol</a>
        <a href="#">Terms of Service</a>
        <a href="#">Security Whitepaper</a>
    </div>
</div>
""", unsafe_allow_html=True)