# MCH estate: analytical foundation plan

The plan workbook, the per-task plans (`plans/`) and the scripts that generate them are kept in private storage, not in this repository (decision DEC-AF-12).

This folder keeps only:

- `data/universe_snapshot_2026-10-03.csv`: 898 named companies taken from the public hub on 2026-10-06.
- `examples/`: an illustrative AAPL report page and the script that builds it.

## Rebuild the workbook

Use the generator package from private storage (`build_workbook.py`, `build_plans.py` and the `content_*.py` modules), placed in this folder:

```bash
python3 build_workbook.py
python3 build_plans.py          # writes plans/AF-xxx.md
python3 <xlsx-skill>/scripts/recalc.py MCH_Analytical_Foundation_Plan_2026-10-06.xlsx 300
```

`.gitignore` keeps the workbook, the plans and the generator out of git.
