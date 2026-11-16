from pathlib import Path
import pandas as pd
import scipy.stats as stats
import sqlite3

# Parameters
YEARS = range(2015, 2025)
PM25_STANDARD = 35.0

DATA = Path("data")
OUTPUT = Path("output")
CHARTS = OUTPUT / "charts"
for p in (DATA, OUTPUT, CHARTS):
    p.mkdir(parents=True, exist_ok=True)

# The three analysis periods: first half, second half, and everything.
_ys = list(YEARS)
_half = len(_ys) // 2
PERIODS = {
    f"first_{_half}yr": (_ys[0], _ys[_half - 1]),
    f"last_{len(_ys) - _half}yr": (_ys[_half], _ys[-1]),
    f"full_{len(_ys)}yr": (_ys[0], _ys[-1]),
}

# Load the EPA Data
def load_epa() -> pd.DataFrame:
    frames = []
    for year in YEARS:
        path = DATA/f"ad_viz_plotval_data_{year}.csv"
        frames.append(pd.read_csv(path, low_memory=False))
    df = pd.concat(frames, ignore_index=True)

    df["date"] = pd.to_datetime(df["Date"])
    df["pm25"] = pd.to_numeric(df["Daily Mean PM2.5 Concentration"], errors="coerce")
    print(f"EPA rows for Salt Lake County: {len(df):,}")
    return df[["date", "Local Site Name", "pm25"]]

# Load the NOAA Data
def load_noaa() -> pd.DataFrame:
    path = DATA/"noaa_slc_air_temps.csv"
    print(f"Loading {path}")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["DATE"])
    # This NOAA export is in degrees Fahrenheit; convert to Celsius
    for c in ("TMAX", "TMIN"):
        df[c] = (pd.to_numeric(df[c], errors="coerce") - 32) * 5 / 9
    df["tavg_c"] = (df["TMAX"] + df["TMIN"]) / 2
    return df[["date", "TMAX", "TMIN", "tavg_c"]]

def build_daily(epa: pd.DataFrame, noaa: pd.DataFrame) -> pd.DataFrame:
    before = len(epa)
    # Drop NaN, None, and negative readings
    epa = epa.dropna(subset=["pm25"])
    epa = epa[epa["pm25"] >= 0]
    print(f"Dropped {before - len(epa):,} EPA rows with missing/negative PM2.5.")

    daily = epa.groupby("date", as_index=False).agg(pm25=("pm25", "mean"), monitors=("Local Site Name", "nunique"))
    merged = daily.merge(noaa, on="date", how="inner")
    merged = merged.dropna(subset=["tavg_c"])
    merged["year"] = merged["date"].dt.year
    merged["month"] = merged["date"].dt.month
    merged["winter"] = merged["month"].isin([12, 1, 2])
    merged["exceeds_standard"] = (merged["pm25"] > PM25_STANDARD).astype(int)
    merged["date"] = merged["date"].dt.strftime("%Y-%m-%d")
    print(f"Joined daily rows: {len(merged):,}")
    return merged

# SQL (run once per period)
QUERIES = {
    "Days over the standard, by year": """
        SELECT year, SUM(exceeds_standard) AS days_over, COUNT(*) AS days_measured
        FROM daily WHERE year BETWEEN {y0} AND {y1}
        GROUP BY year ORDER BY year;""",
    "Average PM2.5 by month": """
        SELECT month, ROUND(AVG(pm25), 1) AS avg_pm25
        FROM daily WHERE year BETWEEN {y0} AND {y1}
        GROUP BY month ORDER BY month;""",
    "Winter days: cold vs. mild (split at 0 C average)": """
        SELECT CASE WHEN tavg_c < 0 THEN 'cold (below 0 C)' ELSE 'mild (0 C or above)' END AS temp_group,
               COUNT(*) AS days, ROUND(AVG(pm25), 1) AS avg_pm25,
               SUM(exceeds_standard) AS days_over
        FROM daily WHERE winter = 1 AND year BETWEEN {y0} AND {y1}
        GROUP BY temp_group;""",
    "Worst 10 days": """
        SELECT date, ROUND(pm25, 1) AS pm25, ROUND(tavg_c, 1) AS tavg_c
        FROM daily WHERE year BETWEEN {y0} AND {y1}
        ORDER BY pm25 DESC LIMIT 10;""",
}

def run_sql(daily: pd.DataFrame) -> None:
    con = sqlite3.connect(OUTPUT/"daily.db")
    daily.to_sql("daily", con, if_exists="replace", index=False)
    for label, (y0, y1) in PERIODS.items():
        folder = OUTPUT/label
        folder.mkdir(exist_ok=True)
        lines = [f"##### {label}: {y0} to {y1} #####\n"]
        for title, sql in QUERIES.items():
            res = pd.read_sql(sql.format(y0=y0, y1=y1), con=con)
            lines.append(f"== {title} ==\n{res.to_string(index=False)}\n")
        text = "\n".join(lines)
        (folder/"query_results.txt").write_text(text)
        print(text)
    con.close()

if __name__ == "__main__":
    epa = load_epa()
    noaa = load_noaa()
    daily = build_daily(epa, noaa)
    daily.to_csv(OUTPUT/"clean_daily.csv", index=False)
    run_sql(daily)