# references_forOpioid

Curated reference lists for **opioid intravenous self-administration (IVSA)** and **experimenter-administered opioid injection** studies in rodent neuroscience (with an emphasis on circuits, methods, and imaging).

Source spreadsheets are merged into one table for filtering and sorting.

## Files

| File | Description |
| --- | --- |
| [`data/references_unified.csv`](data/references_unified.csv) | All rows, unified columns |
| [`build_from_xlsx.py`](build_from_xlsx.py) | Regenerate CSV/README from local `.xlsx` copies |

## Regenerate from Excel

Requires Python 3 with `pandas` and `openpyxl` (`pip install pandas openpyxl`).

```bash
python build_from_xlsx.py \
  --ivsa path/to/opioid_ivsa_paper_index_v3.xlsx \
  --injection "path/to/opioid_injection_morphine_fentanyl_circuit_papers (1).xlsx"
```

## Summary counts

- **IV self-administration:** 45 papers
- **Experimenter-administered injection:** 26 papers

### By fine-grained category

| Paradigm | Category | N |
| --- | --- | ---: |
| Experimenter-administered injection | Fentanyl injection | 7 |
| Experimenter-administered injection | Morphine injection | 15 |
| Experimenter-administered injection | Review / methods | 4 |
| IV self-administration | Fentanyl IVSA | 9 |
| IV self-administration | Heroin IVSA | 15 |
| IV self-administration | Morphine IVSA | 8 |
| IV self-administration | Oxycodone IVSA | 4 |
| IV self-administration | Remifentanil IVSA | 5 |
| IV self-administration | Review/Methods | 4 |

## Column guide (`references_unified.csv`)

| Column | Meaning |
| --- | --- |
| `paradigm` | IV self-administration vs experimenter-administered injection |
| `category` | Drug or topic subgroup (e.g., Heroin IVSA, Fentanyl injection) |
| `citation` | Short citation string |
| `year` | Publication year when parsed or provided |
| `title` | Title or short description |
| `drug` | Opioid or drug focus |
| `species` | Species |
| `paper_type` | Review vs experimental (injection set) |
| `exposure_paradigm` | Dosing / exposure description (injection set) |
| `route` | Route of administration (injection set) |
| `acute_chronic` | Acute, chronic, or withdrawal context (injection set) |
| `brain_region` | Region or circuit emphasis (injection set) |
| `short_conclusion` | One-line takeaway |
| `method_family` | High-level methods bucket |
| `neuroscience_methods` | Methods detail |
| `imaging_type` | Modalities when specified (injection set) |
| `in_vivo_imaging` | yes / no |
| `confidence` | Indexing confidence |
| `notes` | Extra notes (IVSA set) |
| `url` | PubMed or publisher link |
