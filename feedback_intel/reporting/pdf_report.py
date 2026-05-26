from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from fpdf import FPDF

matplotlib.use("Agg")


def _save_sentiment_chart(df: pd.DataFrame, path: Path) -> None:
    tmp = df.copy()
    tmp["created_at"] = pd.to_datetime(tmp["created_at"], utc=True, errors="coerce")
    tmp = tmp.dropna(subset=["created_at"])
    if tmp.empty:
        return

    tmp = tmp.set_index("created_at").sort_index()
    weekly = tmp.resample("W")["sentiment_compound"].mean()

    plt.figure(figsize=(7.2, 3.0))
    plt.plot(weekly.index, weekly.values, marker="o", linewidth=1.5)
    plt.title("Average Sentiment (Weekly)")
    plt.xlabel("Week")
    plt.ylabel("Avg compound")
    plt.ylim(-1, 1)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def _save_source_pie(df: pd.DataFrame, path: Path) -> None:
    if df.empty or "source" not in df.columns:
        return
    counts = df["source"].value_counts()
    if counts.empty:
        return

    plt.figure(figsize=(4.2, 3.0))
    plt.pie(counts.values, labels=counts.index, autopct="%1.0f%%", textprops={"fontsize": 8})
    plt.title("Feedback Sources")
    plt.tight_layout()
    plt.savefig(path, dpi=200)
    plt.close()


def generate_weekly_pdf_report(
    df: pd.DataFrame,
    *,
    out_path: Path,
    title: str = "Feedback Intelligence Weekly Report",
    top_issues: pd.DataFrame | None = None,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)

    total = int(len(df)) if df is not None else 0
    avg = float(df["sentiment_compound"].mean()) if total and "sentiment_compound" in df.columns else 0.0
    neg = int((df.get("sentiment_label") == "negative").sum()) if total else 0
    pos = int((df.get("sentiment_label") == "positive").sum()) if total else 0

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, f"Total feedback items: {total}\nAverage sentiment (compound): {avg:.3f}\n"
                         f"Positive: {pos} | Negative: {neg}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_p = Path(tmpdir)
        sentiment_png = tmpdir_p / "sentiment.png"
        sources_png = tmpdir_p / "sources.png"

        _save_sentiment_chart(df, sentiment_png)
        _save_source_pie(df, sources_png)

        if sentiment_png.exists():
            pdf.ln(1)
            pdf.image(str(sentiment_png), w=180)
        if sources_png.exists():
            pdf.ln(2)
            pdf.image(str(sources_png), w=110)

    if top_issues is not None and not top_issues.empty:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, "Top Issues (Negative Feedback)", ln=True)
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(90, 6, "Issue phrase", border=1)
        pdf.cell(30, 6, "Mentions", border=1)
        pdf.cell(30, 6, "Avg cmpd", border=1)
        pdf.cell(30, 6, "Priority", border=1, ln=True)
        pdf.set_font("Helvetica", "", 9)
        for _, r in top_issues.head(20).iterrows():
            phrase = str(r.get("phrase", ""))[:60]
            pdf.cell(90, 6, phrase, border=1)
            pdf.cell(30, 6, str(int(r.get("negative_mentions", 0))), border=1)
            pdf.cell(30, 6, f"{float(r.get('avg_compound', 0.0)):.3f}", border=1)
            pdf.cell(30, 6, f"{float(r.get('priority', 0.0)):.3f}", border=1, ln=True)

    pdf.output(str(out_path))
    return out_path
