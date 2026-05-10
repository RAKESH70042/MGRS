import streamlit as st
import requests
import pandas as pd
import json

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="MedGemma Prescription Review",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------
# CUSTOM CSS
# -----------------------------

st.markdown("""
<style>
    /* General */
    .block-container {
        padding: 1.5rem 2rem;
        max-width: 100%;
    }

    /* Title */
    .main-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }
    .main-subtitle {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 1.5rem;
    }

    /* Section headers */
    .section-header {
        font-size: 1rem;
        font-weight: 600;
        color: #1a1a2e;
        padding: 0.4rem 0;
        border-bottom: 2px solid #e8e8f0;
        margin-bottom: 0.8rem;
    }

    /* Upload response box */
    .upload-response-box {
        background: #f0fdf4;
        border: 1px solid #86efac;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-size: 0.85rem;
        color: #166534;
        margin-top: 0.5rem;
    }

    /* Extraction card */
    .extraction-card {
        background: #fafafa;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem;
    }

    /* Medication card */
    .med-card {
        background: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
    }
    .med-name {
        font-size: 1rem;
        font-weight: 700;
        color: #1a1a2e;
    }
    .med-detail {
        font-size: 0.82rem;
        color: #555;
        margin-top: 0.2rem;
    }
    .confidence-high { color: #16a34a; font-weight: 600; }
    .confidence-mid  { color: #d97706; font-weight: 600; }
    .confidence-low  { color: #dc2626; font-weight: 600; }

    /* Patient info row */
    .info-row {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 0.8rem;
    }
    .info-chip {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 20px;
        padding: 0.25rem 0.75rem;
        font-size: 0.82rem;
        color: #1d4ed8;
    }

    /* Review buttons */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem;
    }

    /* Approve button */
    div[data-testid="column"]:nth-child(1) .stButton > button {
        background-color: #16a34a;
        color: white;
        border: none;
    }
    div[data-testid="column"]:nth-child(1) .stButton > button:hover {
        background-color: #15803d;
    }

    /* Reject button */
    div[data-testid="column"]:nth-child(2) .stButton > button {
        background-color: #dc2626;
        color: white;
        border: none;
    }
    div[data-testid="column"]:nth-child(2) .stButton > button:hover {
        background-color: #b91c1c;
    }

    /* Review response */
    .review-approved {
        background: #f0fdf4;
        border: 1px solid #86efac;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        color: #166534;
        font-size: 0.88rem;
    }
    .review-rejected {
        background: #fef2f2;
        border: 1px solid #fca5a5;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        color: #991b1b;
        font-size: 0.88rem;
    }

    /* Divider */
    hr {
        margin: 1.2rem 0;
        border-color: #e8e8f0;
    }

    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# SESSION STATE
# -----------------------------

if "extraction_data" not in st.session_state:
    st.session_state.extraction_data = None
if "review_response" not in st.session_state:
    st.session_state.review_response = None
if "upload_data" not in st.session_state:
    st.session_state.upload_data = None

# -----------------------------
# HEADER
# -----------------------------

st.markdown('<div class="main-title">🩺 MedGemma Prescription Review</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">AI-powered prescription extraction and review system</div>', unsafe_allow_html=True)

# Sidebar actions
with st.sidebar:
    st.title("⚙️ Actions")
    if st.button("🔄 Refresh Records"):
        try:
            r = requests.get(f"{API_BASE}/records")
            st.session_state.records = r.json()
            st.success("Refreshed")
        except Exception as e:
            st.error(str(e))

    if st.button("📤 Export JSON"):
        try:
            r = requests.get(f"{API_BASE}/export/json")
            st.success("Export Completed")
            st.json(r.json())
        except Exception as e:
            st.error(str(e))

# ==============================
# MAIN LAYOUT: LEFT | RIGHT
# ==============================

left_col, right_col = st.columns([1, 1.4], gap="large")

# ==============================
# LEFT COLUMN — Upload
# ==============================

with left_col:

    # --- Upload Section ---
    st.markdown('<div class="section-header">📁 Upload Prescription</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Choose a prescription image",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        st.image(uploaded_file, use_container_width=True)

        # Auto-upload on file select
        files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
        try:
            upload_response = requests.post(f"{API_BASE}/upload", files=files)
            st.session_state.upload_data = upload_response.json()
        except Exception as e:
            st.error(f"Upload failed: {e}")

        # --- Upload Response ---
        if st.session_state.upload_data:
            d = st.session_state.upload_data
            st.markdown(
                f'<div class="upload-response-box">'
                f'✅ <b>{d.get("filename","")}</b> saved successfully<br>'
                f'<span style="color:#555">Type: {d.get("content_type","")} &nbsp;|&nbsp; Path: {d.get("saved_to","")}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Extract Button ---
        if st.button("🔍 Run Extraction", use_container_width=True):
            with st.spinner("MedGemma is reading the prescription... (~60s)"):
                try:
                    r = requests.get(
                        f"{API_BASE}/extract",
                        params={"file_name": uploaded_file.name}
                    )
                    st.session_state.extraction_data = r.json()
                    st.session_state.review_response = None
                    st.success("✅ Extraction completed!")
                except Exception as e:
                    st.error(str(e))

    # --- Review Actions ---
    if st.session_state.extraction_data and "record_id" in st.session_state.extraction_data:

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">✍️ Review Actions</div>', unsafe_allow_html=True)

        record_id = st.session_state.extraction_data.get("record_id")

        reviewer_notes = st.text_area(
            "Reviewer Notes",
            placeholder="Add notes before approving or rejecting...",
            height=80
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Approve"):
                try:
                    r = requests.put(
                        f"{API_BASE}/review/{record_id}",
                        params={"status": "approved", "reviewer_notes": reviewer_notes}
                    )
                    st.session_state.review_response = r.json()
                except Exception as e:
                    st.error(str(e))

        with col2:
            if st.button("❌ Reject"):
                try:
                    r = requests.put(
                        f"{API_BASE}/review/{record_id}",
                        params={"status": "rejected", "reviewer_notes": reviewer_notes}
                    )
                    st.session_state.review_response = r.json()
                except Exception as e:
                    st.error(str(e))

        # --- Review Response ---
        if st.session_state.review_response:
            rv = st.session_state.review_response
            status = rv.get("review", {}).get("status", "")
            notes  = rv.get("review", {}).get("reviewer_notes", "")
            time   = rv.get("review", {}).get("reviewed_at", "")

            css_class = "review-approved" if status == "approved" else "review-rejected"
            icon      = "✅" if status == "approved" else "❌"

            st.markdown(
                f'<div class="{css_class}">'
                f'{icon} <b>Record {status.capitalize()}</b><br>'
                f'{"<span>Notes: " + notes + "</span><br>" if notes else ""}'
                f'<span style="opacity:0.7;font-size:0.78rem">{time}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

# ==============================
# RIGHT COLUMN — Extraction Result
# ==============================

with right_col:

    if st.session_state.extraction_data and "record_id" in st.session_state.extraction_data:

        data      = st.session_state.extraction_data
        extracted = data.get("extracted", {})
        meds      = extracted.get("medications", [])
        meta      = data.get("run_metadata", {})

        st.markdown('<div class="section-header">📋 Extraction Result</div>', unsafe_allow_html=True)

        # --- Patient Info Chips ---
        chips = []
        if extracted.get("patient_name"):
            chips.append(f"👤 {extracted['patient_name']}")
        if extracted.get("patient_age"):
            chips.append(f"🎂 Age {extracted['patient_age']}")
        if extracted.get("patient_gender"):
            chips.append(f"⚧ {extracted['patient_gender']}")
        if extracted.get("prescription_date"):
            chips.append(f"📅 {extracted['prescription_date']}")
        if extracted.get("prescriber_name"):
            chips.append(f"👨‍⚕️ {extracted['prescriber_name']}")
        if extracted.get("hospital_or_clinic"):
            chips.append(f"🏥 {extracted['hospital_or_clinic']}")

        chips_html = "".join([f'<span class="info-chip">{c}</span>' for c in chips])
        st.markdown(f'<div class="info-row">{chips_html}</div>', unsafe_allow_html=True)

        if extracted.get("diagnosis"):
            st.markdown(f"**Diagnosis:** {extracted['diagnosis']}")

        # --- Medications ---
        st.markdown(f"**💊 Medications ({len(meds)} found)**")

        for i, med in enumerate(meds):
            score = med.get("confidence_score", 100)
            if score >= 85:
                conf_class = "confidence-high"
                conf_icon  = "🟢"
            elif score >= 65:
                conf_class = "confidence-mid"
                conf_icon  = "🟡"
            else:
                conf_class = "confidence-low"
                conf_icon  = "🔴"

            details = []
            if med.get("dosage"):     details.append(f"💊 {med['dosage']}")
            if med.get("unit"):       details.append(f"📦 {med['unit']}")
            if med.get("frequency"):  details.append(f"🔁 {med['frequency']}")
            if med.get("duration"):   details.append(f"⏱ {med['duration']}")
            if med.get("quantity"):   details.append(f"# {med['quantity']}")
            if med.get("timing"):     details.append(f"🕐 {med['timing']}")
            if med.get("route"):      details.append(f"🛣 {med['route']}")

            details_html = " &nbsp;|&nbsp; ".join(details)

            si = med.get("special_instructions", "")
            un = med.get("uncertainty_notes", "")
            rt = med.get("raw_medication_text", "")

            st.markdown(
                f'<div class="med-card">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span class="med-name">{i+1}. {med.get("medication_name","")}</span>'
                f'<span class="{conf_class}">{conf_icon} {score}%</span>'
                f'</div>'
                f'<div class="med-detail">{details_html}</div>'
                f'{"<div class=\\"med-detail\\"><b>Instructions:</b> " + si + "</div>" if si else ""}'
                f'{"<div class=\\"med-detail\\" style=\\"color:#d97706\\"><b>⚠ Note:</b> " + un + "</div>" if un else ""}'
                f'{"<div class=\\"med-detail\\" style=\\"color:#999;font-style:italic\\">Raw: " + rt + "</div>" if rt else ""}'
                f'</div>',
                unsafe_allow_html=True
            )

        if extracted.get("additional_notes"):
            st.markdown(f"**📝 Additional Notes:** {extracted['additional_notes']}")

        # --- Run Metadata ---
        st.markdown(
            f'<div style="margin-top:0.8rem;padding:0.5rem 0.8rem;background:#f8f8f8;border-radius:6px;font-size:0.78rem;color:#888">'
            f'🤖 {meta.get("model_name","")} {meta.get("model_version","")} &nbsp;|&nbsp; '
            f'⏱ {meta.get("latency_ms",0)/1000:.1f}s &nbsp;|&nbsp; '
            f'🆔 {data.get("record_id","")}'
            f'</div>',
            unsafe_allow_html=True
        )

    else:
        st.markdown(
            '<div style="height:300px;display:flex;align-items:center;justify-content:center;'
            'background:#fafafa;border:2px dashed #e2e8f0;border-radius:12px;color:#aaa;font-size:0.95rem">'
            '📋 Extraction result will appear here'
            '</div>',
            unsafe_allow_html=True
        )

# ==============================
# STORED RECORDS — Collapsible
# ==============================

st.markdown("<hr>", unsafe_allow_html=True)

with st.expander("🗃️ Stored Records", expanded=False):
    try:
        r = requests.get(f"{API_BASE}/records")
        records_data = r.json()

        if records_data:
            formatted = []
            for rec in records_data:
                review  = json.loads(rec.get("review_json", "{}"))
                status  = review.get("status", "pending")
                icon    = "✅" if status == "approved" else ("❌" if status == "rejected" else "⏳")

                formatted.append({
                    "Status":      f"{icon} {status.capitalize()}",
                    "Record ID":   rec["record_id"],
                    "Source File": rec["source_file"],
                    "Method":      rec["method"],
                })

            df = pd.DataFrame(formatted)
            st.dataframe(df, use_container_width=True, height=250)
            st.caption(f"Total: {len(formatted)} records")

        else:
            st.info("No records found yet.")

    except Exception as e:
        st.error(str(e))