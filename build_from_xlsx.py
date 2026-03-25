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

# Keywords for `roadmap_circuit` buckets (lowercase substrings; order only affects tie-break via score)
CIRCUIT_KEYWORDS: dict[str, list[str]] = {
    "A — Mesolimbic & striatum (VTA, NAc, striatum, VP, dopamine endpoints)": [
        "vta",
        "ventral tegmental",
        "ventral tegmentum",
        "substantia nigra",
        "snc ",
        "nucleus accumbens",
        "accumbens",
        "nac ",
        "nac-",
        "nac→",
        "nac to",
        "striatum",
        "striatal",
        "dorsomedial striatum",
        "ventral pallidum",
        "mesolimbic",
        "dopamine release",
        "dopamine signals",
        "grabda",
        "dlight",
    ],
    "B — Cortex & cortico-striatal / cortico-midbrain": [
        "prelimbic",
        "infralimbic",
        "prefrontal",
        "pfc",
        "mpfc",
        "medial prefrontal",
        "corticostriatal",
        "cortico-striatal",
        "cortical",
        "camkii",
    ],
    "C — Extended amygdala / BNST / CeA": [
        "amygdala",
        "central amygdala",
        "cea ",
        "bnst",
        "bed nucleus of",
        "bed nucleus",
    ],
    "D — Thalamus, habenula, hypothalamus": [
        "paraventricular thalamus",
        " pvt",
        "pvt→",
        "pvt-",
        "thalamus",
        "thalamostriatal",
        "habenula",
        "lateral habenula",
        "lhb",
        "hypothalamus",
        "lateral hypothalamus",
    ],
    "E — Hippocampus": [
        "hippocampus",
        "hippocampal",
        " ca1",
        "ca1 ",
        "schaffer",
        "dentate",
    ],
}


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


def _roadmap_text_blob(row: pd.Series) -> str:
    parts = [
        row.get("brain_region", ""),
        row.get("title", ""),
        row.get("short_conclusion", ""),
        row.get("neuroscience_methods", ""),
        row.get("method_family", ""),
    ]
    return " ".join(str(p) for p in parts if pd.notna(p)).lower()


def roadmap_ivsa(paradigm: str) -> str:
    return "yes" if str(paradigm).strip() == "IV self-administration" else "no"


def roadmap_species(row: pd.Series) -> str:
    cat = str(row.get("category", "")).lower()
    pt = str(row.get("paper_type", "")).lower()
    if "review" in cat or "methods" in cat or pt == "review":
        return "Review / cross-species (see `species` column)"
    s = str(row.get("species", "")).lower()
    has_m = "mouse" in s
    has_r = "rat" in s
    if has_m and has_r:
        return "Mouse + rat"
    if has_m:
        return "Mouse"
    if has_r or s.strip() == "rodent":
        return "Rat"
    if "rodent" in s:
        return "Rodent (unspecified)"
    return "Mixed / other (see `species`)"


def roadmap_mouse_yn(row: pd.Series) -> str:
    """Binary-style gate for 'is this primarily mouse work?' (spreadsheet-friendly)."""
    rs = roadmap_species(row)
    if rs.startswith("Review"):
        return "n/a"
    if rs == "Mouse":
        return "yes"
    if rs == "Mouse + rat":
        return "partial"
    return "no"


def roadmap_circuit(row: pd.Series) -> str:
    cat = str(row.get("category", "")).lower()
    pt = str(row.get("paper_type", "")).lower()
    if "review" in cat or pt == "review":
        return "Z — Review / survey (use title for topics)"

    text = _roadmap_text_blob(row)
    if not text.strip():
        return "Z — Not tagged (no region text in index)"

    scores: dict[str, int] = {k: 0 for k in CIRCUIT_KEYWORDS}
    for label, keys in CIRCUIT_KEYWORDS.items():
        scores[label] = sum(1 for k in keys if k in text)

    mx = max(scores.values())
    if mx == 0:
        mf = str(row.get("method_family", "")).lower()
        par = str(row.get("paradigm", ""))
        if "behavioral only" in mf and roadmap_ivsa(par) == "yes":
            return "Z — IVSA behavioral / no circuit tag in index"
        return "Z — Not tagged / distributed or unclear"

    best = sorted([lab for lab, sc in scores.items() if sc == mx])
    if len(best) == 1:
        return best[0]
    letters = [b.split("—", 1)[0].strip() for b in best]
    return (
        "Multi ("
        + " + ".join(letters)
        + ") — overlapping keywords; check `title` / `brain_region`"
    )


def enrich_roadmap(merged: pd.DataFrame) -> pd.DataFrame:
    out = merged.copy()
    out["roadmap_ivsa"] = out["paradigm"].map(roadmap_ivsa)
    out["roadmap_species"] = out.apply(roadmap_species, axis=1)
    out["roadmap_mouse_yn"] = out.apply(roadmap_mouse_yn, axis=1)
    out["roadmap_circuit"] = out.apply(roadmap_circuit, axis=1)
    return out


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
    merged = enrich_roadmap(merged)

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
    lines.append("## Hierarchical roadmap (narrowing the list)")
    lines.append("")
    lines.append(
        "Use the CSV in decision order: **`roadmap_ivsa`** → **`roadmap_mouse_yn`** (or **`roadmap_species`**) → **`roadmap_circuit`**. "
        "Circuit labels (**A–E**, **Z**, **Multi**) are auto-tagged from `title`, `brain_region`, `method_family`, "
        "and `neuroscience_methods` (keyword heuristics). Always confirm in the original paper."
    )
    lines.append("")
    lines.append("### Step 1: Intravenous self-administration (IVSA)?")
    lines.append("")
    lines.append("| `roadmap_ivsa` | Meaning | Count |")
    lines.append("| --- | --- | ---: |")
    ivsa_counts = merged["roadmap_ivsa"].value_counts()
    for v in ["yes", "no"]:
        lines.append(f"| **{v}** | {'IVSA model' if v == 'yes' else 'Experimenter-administered injection (not IVSA)'} | {int(ivsa_counts.get(v, 0))} |")
    lines.append("")
    lines.append("### Step 2: Mouse? (yes / no / partial / n/a)")
    lines.append("")
    lines.append(
        "| `roadmap_mouse_yn` | How to read it | Count |\n"
        "| --- | --- | ---: |"
    )
    mouse_order = ["yes", "no", "partial", "n/a"]
    m_counts = merged["roadmap_mouse_yn"].value_counts()
    mouse_help = {
        "yes": "Mouse-only (or clearly mouse primary) experimental row",
        "no": "Rat-only, other species, or rodent unspecified",
        "partial": "Explicit mouse + rat in `species`",
        "n/a": "Review / methods row; use `species` and title instead",
    }
    for key in mouse_order:
        lines.append(f"| **{key}** | {mouse_help[key]} | {int(m_counts.get(key, 0))} |")
    lines.append("")
    lines.append("**Finer species bucket** (`roadmap_species`, optional third sort key):")
    lines.append("")
    lines.append("| `roadmap_species` | Count |")
    lines.append("| --- | ---: |")
    for lab, cnt in merged["roadmap_species"].value_counts().items():
        lines.append(f"| {lab} | {int(cnt)} |")
    lines.append("")
    lines.append("### Step 3: Circuit / region bucket (`roadmap_circuit`)")
    lines.append("")
    lines.append(
        "| Code | What it roughly marks |\n"
        "| --- | --- |\n"
        "| **A** | Mesolimbic & striatum: VTA, NAc, dorsal striatum, ventral pallidum, terminal dopamine readouts |\n"
        "| **B** | Prefrontal / prelimbic cortex and cortico-striatal or cortico-midbrain emphasis |\n"
        "| **C** | Extended amygdala: amygdala, CeA, BNST |\n"
        "| **D** | Thalamus (incl. PVT), habenula, hypothalamus / LH |\n"
        "| **E** | Hippocampus (e.g., CA1) |\n"
        "| **Multi** | Two or more buckets tied (keywords overlap) |\n"
        "| **Z** | Reviews, purely behavioral IVSA rows without region keywords, or not tagged from this index |"
    )
    lines.append("")
    lines.append("**Counts in this snapshot:**")
    lines.append("")
    lines.append("| `roadmap_circuit` | N |")
    lines.append("| --- | ---: |")
    for lab, cnt in merged["roadmap_circuit"].value_counts().items():
        safe = str(lab).replace("|", "\\|")
        lines.append(f"| {safe} | {int(cnt)} |")
    lines.append("")
    lines.append("### Visual map (same decisions)")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart TD")
    lines.append("  R[All rows in references_unified.csv] --> Q1{roadmap_ivsa}")
    lines.append("  Q1 -->|yes| IVSA[IVSA papers]")
    lines.append("  Q1 -->|no| INJ[Experimenter injection papers]")
    lines.append("  IVSA --> Q2{roadmap_species}")
    lines.append("  INJ --> Q2")
    lines.append("  Q2 --> MS[roadmap_mouse_yn: yes no partial n/a]")
    lines.append("  MS --> Q3{roadmap_circuit A–E, Multi, Z}")
    lines.append("  Q3 --> DONE[Shortlist + open url column]")
    lines.append("```")
    lines.append("")
    lines.append("### Quick filter examples (spreadsheet / pandas)")
    lines.append("")
    lines.append("- **IVSA + mouse + PFC-ish:** `roadmap_ivsa` = yes, `roadmap_mouse_yn` = yes, `roadmap_circuit` contains `B`.")
    lines.append("- **Injection + NAc / VTA:** `roadmap_ivsa` = no, sort `roadmap_circuit` for **A**.")
    lines.append("- **In vivo imaging during behavior:** filter `in_vivo_imaging` = yes (orthogonal to the roadmap steps).")
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
        "| `url` | PubMed or publisher link |\n"
        "| `roadmap_ivsa` | **yes** = IVSA; **no** = experimenter-administered injection |\n"
        "| `roadmap_mouse_yn` | **yes** / **no** / **partial** / **n/a** for reviews (mouse gate) |\n"
        "| `roadmap_species` | Mouse vs rat vs mixed vs review-oriented grouping (quick filter) |\n"
        "| `roadmap_circuit` | Circuit bucket **A–E**, **Multi**, or **Z** (keyword heuristic; see README roadmap) |"
    )
    lines.append("")
    args.out_readme.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out_csv} ({len(merged)} rows)")
    print(f"Wrote {args.out_readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
