# Indonesia GIS Precipitation Forecast

A GIS visualization tool for precipitation forecasts and historical data in Indonesia, with a focus on the Bandung region.


## Setup


1Set up the virtual environment and install dependencies:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install streamlit
   ```

## Usage

### Command Line Mode

To run the standard map visualization with default settings:

```bash
./run.sh
```


### Interactive Streamlit Interface

To run the interactive Streamlit interface:

```bash
./run.sh streamlit
```


## Requirements

- Python 3.9+
- See `requirements.txt` for full list of dependencies