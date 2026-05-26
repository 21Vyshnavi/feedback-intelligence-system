# Feedback Intelligence System (Python)

Multi-source feedback intelligence system:
- Google Play reviews (google-play-scraper)
- Apple App Store reviews (RSS)
- Survey CSV uploads

## Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

## Run
streamlit run streamlit_app.py

Tip: upload `data/sample_survey.csv` in the sidebar to see data immediately.
