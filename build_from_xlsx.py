"""
Regenerate data/references_unified.csv and README.md from the source spreadsheets.
Default paths point to the filenames in Downloads; override with env vars or CLI.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd

YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")


def parse_year(text: str | float | None) -> str:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    s = str(text).strip()
    if not s:
        return ""
    m = YEAR_RE.search(s)
    return m.group(1) if m else ""


def year_cell(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    try:
        return str(int(float(val)))
    except (ValueError, TypeError):
        s = str(val).strip()
        return s


def fmt_author_year(author, year) -> str:
    a = "" if pd.isna(author) else str(author).strip()
    y = year_cell(year)
    if a and y:
        return f"{a}, {y}"
    return a or y


def norm_yes_no(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip().lower()
    if s in ("yes", "y", "true", "1"):
        return "yes"
    if s in ("no", "n", "false", "0"):
        return "no"
    return str(val).strip()


def load_ivsa(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Paper_Index", header=0)
    df = df.rename(
        columns={
            "Citation (as provided)": "citation",
            "Title / Short description": "title",
            "Short conclusion": "short_conclusion",
            "Method family": "method_family",
            "Neuroscience methods used": "neuroscience_methods",
            "In vivo imaging?": "in_vivo_imaging",
            "Notes": "notes",
            "Source lookup URL": "url",
        }
    )
    return pd.DataFrame(
        {
            "paradigm": "IV self-administration",
            "category": df["Category"],
            "citation": df["citation"],
            "year": df["citation"].map(parse_year),
            "title": df["title"],
            "drug": df["Drug"],
            "species": df["Species"],
            "paper_type": "",
            "exposure_paradigm": "",
            "route": "",
            "acute_chronic": "",
            "brain_region": "",
            "short_conclusion": df["short_conclusion"],
            "method_family": df["method_family"],
            "neuroscience_methods": df["neuroscience_methods"],
            "imaging_type": "",
            "in_vivo_imaging": df["in_vivo_imaging"].map(norm_yes_no),
            "confidence": df["Confidence"],
            "notes": df["notes"],
            "url": df["url"],
        }
    )


def load_injection_combined(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Combined_Index", header=None)
    hdr_idx = raw.index[raw.iloc[:, 0].astype(str).str.strip() == "Category"][0]
    df = pd.read_excel(path, sheet_name="Combined_Index", header=int(hdr_idx))
    cit = [fmt_author_year(a, y) for a, y in zip(df["First Author"], df["Year"])]
    return pd.DataFrame(
        {
            "paradigm": "Experimenter-administered injection",
            "category": df["Category"],
            "citation": cit,
            "year": [year_cell(y) for y in df["Year"]],
            "title": df["Title"],
            "drug": df["Drug"],
            "species": df["Species"],
            "paper_type": df["Paper Type"],
            "exposure_paradigm": df["Exposure Paradigm"],
            "route": df["Route"],
            "acute_chronic": df["Acute/Chronic"],
            "brain_region": df["Brain Region/Circuit"],
            "short_conclusion": df["Short Conclusion"],
            "method_family": df["Method Family"],
            "neuroscience_methods": df["Other Neuroscience Methods"],
            "imaging_type": df["Imaging Type"],
            "in_vivo_imaging": df["In Vivo Imaging?"].map(norm_yes_no),
            "confidence": df["Confidence"],
            "notes": "",
            "url": df["Source URL"],
        }
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ivsa",
        type=Path,
        default=Path(
            os.environ.get(
                "IVSA_XLSX",
                str(Path.home() / "Downloads" / "opioid_ivsa_paper_index_v3.xlsx"),
            )
        ),
    )
    ap.add_argument(
        "--injection",
        type=Path,
        default=Path(
            os.environ.get(
                "INJECTION_XLSX",
                str(
                    Path.home()
                    / "Downloads"
                    / "opioid_injection_morphine_fentanyl_circuit_papers (1).xlsx"
                ),
            )
        ),
    )
    ap.add_argument(
        "--out-csv",
        type=Path,
        default=Path(__file__).resolve().parent / "data" / "references_unified.csv",
    )
    ap.add_argument(
        "--out-readme",
        type=Path,
        default=Path(__file__).resolve().parent / "README.md",
    )
    args = ap.parse_args()

    if not args.ivsa.is_file():
        print(f"Missing IVSA workbook: {args.ivsa}", file=sys.stderr)
        return 1
    if not args.injection.is_file():
        print(f"Missing injection workbook: {args.injection}", file=sys.stderr)
        return 1

    merged = pd.concat(
        [load_ivsa(args.ivsa), load_injection_combined(args.injection)],
        ignore_index=True,
    )
    merged["url"] = merged["url"].fillna("").astype(str).str.strip()
    merged.loc[merged["url"].str.lower().isin(["nan", "none"]), "url"] = ""
    with_url = merged[merged["url"].str.startswith("http", na=False)].drop_duplicates(
        subset=["url"], keep="first"
    )
    no_url = merged[~merged["url"].str.startswith("http", na=False)]
    merged = pd.concat([with_url, no_url], ignore_index=True)

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.out_csv, index=False, encoding="utf-8")

    counts_paradigm = merged["paradigm"].value_counts()
    lines = [
        "# references_forOpioid",
        "",
        "Curated reference lists for **opioid intravenous self-administration (IVSA)** and **experimenter-administered opioid injection** studies in rodent neuroscience (with an emphasis on circuits, methods, and imaging).",
        "",
        "Source spreadsheets are merged into one table for filtering and sorting.",
        "",
        "## Files",
        "",
        "| File | Description |",
        "| --- | --- |",
        "| [`data/references_unified.csv`](data/references_unified.csv) | All rows, unified columns |",
        "| [`build_from_xlsx.py`](build_from_xlsx.py) | Regenerate CSV/README from local `.xlsx` copies |",
        "",
        "## Regenerate from Excel",
        "",
        "Requires Python 3 with `pandas` and `openpyxl` (`pip install pandas openpyxl`).",
        "",
        "```bash",
        "python build_from_xlsx.py \\",
        "  --ivsa path/to/opioid_ivsa_paper_index_v3.xlsx \\",
        '  --injection "path/to/opioid_injection_morphine_fentanyl_circuit_papers (1).xlsx"',
        "```",
        "",
        "## Summary counts",
        "",
        f"- **IV self-administration:** {int(counts_paradigm.get('IV self-administration', 0))} papers",
        f"- **Experimenter-administered injection:** {int(counts_paradigm.get('Experimenter-administered injection', 0))} papers",
        "",
        "### By fine-grained category",
        "",
    ]
    ct = merged.groupby(["paradigm", "category"], observed=True).size().reset_index(name="n")
    ct = ct.sort_values(["paradigm", "category"])
    lines.append("| Paradigm | Category | N |")
    lines.append("| --- | --- | ---: |")
    for _, r in ct.iterrows():
        lines.append(f"| {r['paradigm']} | {r['category']} | {r['n']} |")
    lines.append("")
    lines.append("## Column guide (`references_unified.csv`)")
    lines.append("")
    lines.append(
        "| Column | Meaning |\n"
        "| --- | --- |\n"
        "| `paradigm` | IV self-administration vs experimenter-administered injection |\n"
        "| `category` | Drug or topic subgroup (e.g., Heroin IVSA, Fentanyl injection) |\n"
        "| `citation` | Short citation string |\n"
        "| `year` | Publication year when parsed or provided |\n"
        "| `title` | Title or short description |\n"
        "| `drug` | Opioid or drug focus |\n"
        "| `species` | Species |\n"
        "| `paper_type` | Review vs experimental (injection set) |\n"
        "| `exposure_paradigm` | Dosing / exposure description (injection set) |\n"
        "| `route` | Route of administration (injection set) |\n"
        "| `acute_chronic` | Acute, chronic, or withdrawal context (injection set) |\n"
        "| `brain_region` | Region or circuit emphasis (injection set) |\n"
        "| `short_conclusion` | One-line takeaway |\n"
        "| `method_family` | High-level methods bucket |\n"
        "| `neuroscience_methods` | Methods detail |\n"
        "| `imaging_type` | Modalities when specified (injection set) |\n"
        "| `in_vivo_imaging` | yes / no |\n"
        "| `confidence` | Indexing confidence |\n"
        "| `notes` | Extra notes (IVSA set) |\n"
        "| `url` | PubMed or publisher link |"
    )
    lines.append("")
    args.out_readme.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out_csv} ({len(merged)} rows)")
    print(f"Wrote {args.out_readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
