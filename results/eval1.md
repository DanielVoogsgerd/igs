Components used:
- CHIRPS data source.
- InaRISK flood index.
- H-MHEWS historical index.

Configuration
- Date range: a full year: 2022-01-01 - 2022-12-31
- Hazard index threshold: 6.
- Commit: `c92d120` (the remaining options used can be found in this commit).

Metrics:
- TP:   173
- FP:  4652
- FN:   433
- TN: 41827

Results:
- Accuracy: 0.892
- Precision: 0.036
- Recall: 0.285
- F1 Score: 0.064

The following command was run: `uv run backtest-v2.py`. It depends on the DIBI database being online.
