# Stock Analyzer Pipeline

This project pulls Robinhood positions, merges them with holdings data from a GUI (
The GUI data is sourced from a previous Java project I worked on, Github link:
[stock-manager-gui](https://github.com/reazwrahman/stock-manager-gui)), and loads the result into SQLite.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install robin-stocks
```

## Run Individual Steps

### 1) Pull Robinhood data

```bash
python robinhood_accessor.py
```

This writes `robinhood_positions.json`.

### 2) Merge with GUI data

The GUI data is sourced from a previous Java project I worked on, Github link:
[stock-manager-gui](https://github.com/reazwrahman/stock-manager-gui)

By default, `data_merger.py` looks for `StockOutput.json` in the current folder.  
To use a file in another location, set `GUI_DATA_PATH` in `local.env` file:

```
GUI_DATA_PATH=/full/path/to/StockOutput.json
```
then run: `python data_merger.py`

This writes `merged_data.json`.

### 3) Load merged JSON into SQLite

```bash
python db_updater.py
```

This recreates `merged_data.db` and repopulates table `merged_positions`.

## Run Full Pipeline

```bash
python main.py
```

This runs:
1. `robinhood_accessor.py`
2. `data_merger.py`
3. `db_updater.py`

## Notes

- Generated data files are ignored by git via `.gitignore`.
- `robinhood_accessor.py` uses interactive login and does not hardcode credentials.
