# Salt Lake County Winter Air Quality: PM2.5 and Temperature

> **Status: work in progress.** Data loading, cleaning, the CSV export and the SQL summaries run. Statistics and HTML charts are still to do.

## Question

How do winter PM2.5 levels in Salt Lake County, Utah change with temperature, and how many days per year exceed the 24-hour health standard?

The analysis covers three periods: the first five years (2015–2019), the second five years (2020–2024) and all ten years together.

## Data

| Source | What it provides |
|---|---|
| [EPA AirData](https://www.epa.gov/outdoor-air-quality-data) | Daily PM2.5 readings from monitors in Salt Lake County (files named `ad_viz_plotval_data_<year>.csv`) |
| [NOAA GHCN-Daily](https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily) | Daily high and low temperature at Salt Lake City International Airport, station USW00024127 (`noaa_slc_air_temps.csv`) |

Both sources are free and public. The raw files are **not stored in this repository**. Download them and place them in a `data/` folder before running the script.

## Method

1. **Load** the yearly EPA PM2.5 files and the NOAA temperature file.
2. **Clean:** drop missing or negative PM2.5 readings, convert NOAA temperatures from °F to °C, and average all county monitors into one PM2.5 value per day.
3. **Join** PM2.5 and temperature by date.
4. **Flag** winter days (December, January, February) and days above the 24-hour standard of 35 µg/m³ (check this against the current EPA value).
5. **Summarize with SQL** (SQLite), once per period:
   - days over the standard, by year
   - average PM2.5 by month
   - cold vs. mild winter days (split at 0 °C average temperature)
   - the ten worst days

## Outputs

Written to `output/`:

- `clean_daily.csv`: the cleaned, joined daily table
- `daily.db`: the same table in SQLite
- `first_5yr/`, `last_5yr/`, `full_10yr/`: one `query_results.txt` per period

## How to run

```bash
pip install -r requirements.txt
python slcAirQuality.py
```

## To-Do

- [ ] **HTML charts** (Plotly, saved to `output/charts/`):
  - [ ] Monthly average PM2.5 over time
  - [ ] Winter temperature vs. PM2.5 scatter with trend line
  - [ ] Days over the standard, by year
  - [ ] First five years vs. second five years comparison
- [ ] Statistics: winter correlation of temperature and PM2.5, and a cold vs. mild significance test
- [ ] Count winter-only exceedance days
- [ ] Count days when any single monitor exceeds the standard
- [ ] Write up findings

## Limitations

- Averaging all monitors into one daily value can hide days when a single monitor exceeds the standard.
- The set of active monitors changed over the ten years, which affects comparisons between periods.
- Summer wildfire smoke also causes exceedances, so not every exceedance day is a winter day.
- Temperature comes from the airport, not from each monitor.
- Correlation is not causation.

## Tools

Python, pandas, SQLite, SciPy (planned), Plotly (planned)