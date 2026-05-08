import streamlit as st
import requests
import pandas as pd

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="MedGemma Prescription Review",
    layout="wide"
)

st.title("MedGemma Prescription Review")

# -----------------------------
# SESSION STATE
# -----------------------------

if "extraction_data" not in st.session_state:
    st.session_state.extraction_data = None

if "review_response" not in st.session_state:
    st.session_state.review_response = None

# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.title("Actions")

if st.sidebar.button("Refresh Records"):

    try:
        records_response = requests.get(
            f"{API_BASE}/records"
        )

        st.session_state.records = (
            records_response.json()
        )

    except Exception as e:
        st.sidebar.error(str(e))

if st.sidebar.button("Export JSON"):

    try:
        export_response = requests.get(
            f"{API_BASE}/export/json"
        )

        st.sidebar.success(
            "Export Completed"
        )

        st.sidebar.json(
            export_response.json()
        )

    except Exception as e:
        st.sidebar.error(str(e))

# -----------------------------
# MAIN LAYOUT
# -----------------------------

left_col, right_col = st.columns([1, 1])

# =============================
# LEFT COLUMN
# =============================

with left_col:

    st.header("Upload Prescription")

    uploaded_file = st.file_uploader(
        "Choose Prescription File",
        type=["png", "jpg", "jpeg", "txt"]
    )

    if uploaded_file:

        st.image(
            uploaded_file,
            width=350
        )

        st.success(
            f"Uploaded: {uploaded_file.name}"
        )

        files = {
            "file": (
                uploaded_file.name,
                uploaded_file,
                uploaded_file.type
            )
        }

        upload_response = requests.post(
            f"{API_BASE}/upload",
            files=files
        )

        upload_data = upload_response.json()

        st.subheader("Upload Response")

        st.json(upload_data)

        if st.button("Run Extraction"):

            try:

                extract_response = requests.get(
                    f"{API_BASE}/extract",
                    params={
                        "file_name": uploaded_file.name
                    }
                )

                st.session_state.extraction_data = (
                    extract_response.json()
                )

                st.success(
                    "Extraction Completed"
                )

            except Exception as e:
                st.error(str(e))

# =============================
# RIGHT COLUMN
# =============================

with right_col:

    if st.session_state.extraction_data:

        extraction_data = (
            st.session_state.extraction_data
        )

        st.header("Extraction Result")

        st.json(extraction_data)

        record_id = extraction_data["record_id"]

        st.header("Review Actions")

        reviewer_notes = st.text_area(
            "Reviewer Notes"
        )

        col1, col2 = st.columns(2)

        with col1:

            if st.button("Approve"):

                try:

                    review_response = requests.put(
                        f"{API_BASE}/review/{record_id}",
                        params={
                            "status": "approved",
                            "reviewer_notes": reviewer_notes
                        }
                    )

                    st.session_state.review_response = (
                        review_response.json()
                    )

                    st.success(
                        "Record Approved"
                    )

                except Exception as e:
                    st.error(str(e))

        with col2:

            if st.button("Reject"):

                try:

                    review_response = requests.put(
                        f"{API_BASE}/review/{record_id}",
                        params={
                            "status": "rejected",
                            "reviewer_notes": reviewer_notes
                        }
                    )

                    st.session_state.review_response = (
                        review_response.json()
                    )

                    st.error(
                        "Record Rejected"
                    )

                except Exception as e:
                    st.error(str(e))

        # -----------------------------
        # REVIEW RESPONSE
        # -----------------------------

        if st.session_state.review_response:

            st.subheader(
                "Review Response"
            )

            st.json(
                st.session_state.review_response
            )

# -----------------------------
# RECORDS SECTION
# -----------------------------

st.divider()

st.header("Stored Records")

try:

    records_response = requests.get(
        f"{API_BASE}/records"
    )

    records_data = records_response.json()

    formatted_records = []

    for record in records_data:

        formatted_records.append({
            "Record ID": record["record_id"],
            "Source File": record["source_file"],
            "Method": record["method"]
        })

    if formatted_records:

        df = pd.DataFrame(
            formatted_records
        )

        st.dataframe(
            df,
            use_container_width=True
        )

    else:
        st.info("No records found")

except Exception as e:
    st.error(str(e))