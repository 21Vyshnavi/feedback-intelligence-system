from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from feedback_intel.config import load_settings
from feedback_intel.issues import extract_top_issues
from feedback_intel.pipeline import build_dataset
from feedback_intel.reporting.pdf_report import generate_weekly_pdf_report
from feedback_intel.storage import load_dataset, upsert_dataset
from feedback_intel.trends import compute_weekly_trends


def _as_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce").dt.date


def main() -> None:
    load_dotenv()
    settings = load_settings()

    st.set_page_config(page_title="Feedback Intelligence System", layout="wide")
    st.title("Multi-Source Feedback Intelligence System")

    with st.sidebar:
        st.subheader("Sources")
        google_play_app_id = st.text_input("Google Play app id (package name)", value=settings.google_play_app_id or "")
        apple_app_id = st.text_input("Apple app id", value=settings.apple_app_id or "")
        apple_country = st.text_input("Apple country", value=settings.apple_country)
        google_play_country = st.text_input("Google Play country", value=settings.google_play_country)
        google_play_lang = st.text_input("Google Play language", value=settings.google_play_lang)

        st.subheader("Fetch")
        max_gp = st.number_input("Max Google Play reviews", min_value=0, max_value=5000, value=settings.google_play_max_reviews)
        max_as_pages = st.number_input("Max App Store RSS pages", min_value=0, max_value=50, value=settings.apple_max_pages)
        survey_files = st.file_uploader("Survey CSV uploads", type=["csv"], accept_multiple_files=True)

        fetch_clicked = st.button("Fetch & Update Dataset", type="primary")

    if fetch_clicked:
        survey_paths: list[Path] = []
        if survey_files:
            uploads_dir = settings.data_dir / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            for f in survey_files:
                out = uploads_dir / f.name
                out.write_bytes(f.getvalue())
                survey_paths.append(out)

        with st.status("Fetching data…", expanded=True):
            try:
                df_new = build_dataset(
                    google_play_app_id=google_play_app_id.strip() or None,
                    apple_app_id=apple_app_id.strip() or None,
                    apple_country=apple_country.strip() or "us",
                    google_play_country=google_play_country.strip() or "us",
                    google_play_lang=google_play_lang.strip() or "en",
                    google_play_max_reviews=int(max_gp),
                    apple_max_pages=int(max_as_pages),
                    survey_csv_paths=survey_paths or None,
                )
                st.write(f"Fetched {len(df_new)} items.")
                df_all = upsert_dataset(settings.data_dir, df_new)
                st.success(f"Dataset updated: {len(df_all)} total rows.")
            except Exception as e:
                st.error(f"Fetch failed: {e}")

    df = load_dataset(settings.data_dir)
    if df.empty:
        st.info("No dataset yet. Use the sidebar to fetch sources or upload a survey CSV.")
        return

    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df = df.dropna(subset=["created_at"])
    df["created_date"] = _as_date(df["created_at"])

    min_d = df["created_date"].min()
    max_d = df["created_date"].max()

    col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.0, 1.0])
    with col1:
        sources = sorted(df["source"].dropna().unique().tolist())
        src_filter = st.multiselect("Source", options=sources, default=sources)
    with col2:
        sentiments = ["negative", "neutral", "positive"]
        sent_filter = st.multiselect("Sentiment", options=sentiments, default=sentiments)
    with col3:
        start_d, end_d = st.date_input("Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
    with col4:
        min_rating, max_rating = st.slider("Rating", min_value=0.0, max_value=5.0, value=(0.0, 5.0), step=0.5)

    filt = df.copy()
    if src_filter:
        filt = filt[filt["source"].isin(src_filter)]
    if sent_filter and "sentiment_label" in filt.columns:
        filt = filt[filt["sentiment_label"].isin(sent_filter)]
    if isinstance(start_d, date) and isinstance(end_d, date):
        filt = filt[(filt["created_date"] >= start_d) & (filt["created_date"] <= end_d)]
    if "rating" in filt.columns:
        r = pd.to_numeric(filt["rating"], errors="coerce")
        filt = filt[(r.isna()) | ((r >= min_rating) & (r <= max_rating))]

    k1, k2, k3, k4 = st.columns(4)
    total = int(len(filt))
    avg_sent = float(filt["sentiment_compound"].mean()) if total and "sentiment_compound" in filt.columns else 0.0
    neg = int((filt.get("sentiment_label") == "negative").sum()) if total else 0
    pos = int((filt.get("sentiment_label") == "positive").sum()) if total else 0
    k1.metric("Feedback items", f"{total}")
    k2.metric("Avg sentiment", f"{avg_sent:.3f}")
    k3.metric("Negative", f"{neg}")
    k4.metric("Positive", f"{pos}")

    left, right = st.columns([1.7, 1.0])
    with left:
        st.subheader("Trend")
        trend = compute_weekly_trends(filt)
        if not trend.weekly.empty:
            st.line_chart(trend.weekly.set_index("week")[["avg_sentiment"]])
        else:
            st.caption("Not enough data to compute weekly trends.")

    with right:
        st.subheader("Top Issues")
        top_issues = extract_top_issues(filt, top_k=15, min_df=2)
        if not top_issues.empty:
            st.dataframe(top_issues, use_container_width=True, height=320)
        else:
            st.caption("No recurring negative issues found (or insufficient data).")

    st.subheader("Feedback Table")
    show_cols = [
        "created_at",
        "source",
        "rating",
        "sentiment_label",
        "sentiment_confidence",
        "title",
        "text",
    ]
    show_cols = [c for c in show_cols if c in filt.columns]
    st.dataframe(filt.sort_values("created_at", ascending=False)[show_cols], use_container_width=True, height=420)

    st.subheader("Weekly PDF Report")
    report_col1, report_col2 = st.columns([1.0, 2.0])
    with report_col1:
        report_title = st.text_input("Report title", value="Feedback Intelligence Weekly Report")
        out_name = st.text_input("Output filename", value="weekly_report.pdf")
        make_pdf = st.button("Generate PDF", type="secondary")

    with report_col2:
        if make_pdf:
            out_path = settings.data_dir / "reports" / out_name
            try:
                path = generate_weekly_pdf_report(filt, out_path=out_path, title=report_title, top_issues=top_issues)
                st.success(f"Report generated: {path}")
                st.download_button(
                    "Download PDF",
                    data=path.read_bytes(),
                    file_name=path.name,
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"PDF generation failed: {e}")


if __name__ == "__main__":
    main()

