# FMEA & Defect Pareto Analyzer

A Streamlit app that finds the defects that matter by **frequency** (Pareto) and by **risk** (FMEA), then shows how much the planned corrective actions would reduce that risk.

## What it does

| Tab | What you get |
|---|---|
| **1 · Pareto** | Load defect data (sample, CSV upload, or manual entry). Pareto chart with cumulative % line, adjustable vital-few cutoff, weekly trend, and a button that copies the vital-few defects into the FMEA. |
| **2 · FMEA worksheet** | Editable table: failure mode, effect, cause, current controls, Severity / Occurrence / Detection (1–10), recommended action, owner and the revised scores. RPN is calculated and colour-coded (High / Medium / Low). |
| **3 · Impact** | Total RPN before vs after, high-risk count before vs after, RPN Pareto, before/after chart, and a frequency-vs-risk plot showing when the most frequent defect is not the riskiest one. Includes a one-line summary you can copy. |
| **4 · Export** | Excel report (Summary, Defects, Pareto, FMEA sheets) and an FMEA CSV that can be re-imported. |

**RPN = Severity × Occurrence × Detection.** Risk bands (High ≥ 150, Medium ≥ 100 by default) are adjustable in the sidebar. A blank "New" score means that score is unchanged by the action.

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy for free (Streamlit Community Cloud)

1. Push this folder to a GitHub repository.
2. Go to <https://share.streamlit.io>, sign in with GitHub, and choose **New app**.
3. Pick the repository, branch `main`, and main file `app.py`, then deploy.

## Using your own data

Defect CSV (column names are case-insensitive; `defect`, `qty` and similar aliases are accepted):

```csv
date,defect_type,count
2026-08-03,Weld porosity,12
2026-08-03,Surface scratches,31
```

`date` is optional. Use the **same names** for defects and FMEA failure modes so the frequency-vs-risk chart can match them (the "Add vital-few defects" button does this for you).

Dataset tips for a portfolio version:

- Your own plant, lab or workshop defect log is the strongest option.
- The UCI **Steel Plates Faults** dataset has seven fault classes with an uneven spread, so it produces a meaningful Pareto.
- Avoid perfectly balanced datasets such as NEU-DET (300 images per class): every bar is the same height, so there is no Pareto to find.

## Project layout

```
app.py              Streamlit interface (four tabs)
fmea_logic.py       RPN, Pareto, cleaning and Excel export (pandas + openpyxl only)
fmea_charts.py      Plotly figures
sample_data/        Synthetic defect log and a worked sample FMEA
tests/test_logic.py Unit tests for the logic (python -m pytest, or python tests/test_logic.py)
```

## Notes and limitations

- The sample data is **synthetic**, made up to demonstrate the app. Do not quote its numbers as real results; run the app on real data and quote those.
- Data lives in the browser session only (nothing is stored on the server), so use the Excel / CSV export to keep your work.
- RPN has known weaknesses (different S/O/D combinations can give the same RPN, and severity should usually outweigh the rest). The AIAG-VDA FMEA handbook replaces RPN with Action Priority; adding an Action Priority view would be a natural next step.

## Summary line template

After running on your own data, the Impact tab generates a line like:

> Top 3 failure modes drive X% of total RPN; planned actions cut total RPN from A to B (Y% reduction).
