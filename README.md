# Development

## Prerequisites
- Install [GDAL](https://gdal.org/en/latest/download.html).
  - `brew install gdal` (MacOS)
- (Recommended) Use `uv` as package manager, install [here](https://docs.astral.sh/uv/#installation). Alternatively, use Python 3.11 and `pip install -r requirements.txt`.

## Run
- `uv run main.py`

- Run `uv run main.py --help` to list the available arguments (e.g., `logLevel`).

## Backtesting
- Configure by editing `backtest-v2.py`.
- Run `uv run backtest-v2.py` or `uv run backtest-v2.py -l DEBUG`
