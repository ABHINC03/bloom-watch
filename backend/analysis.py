import pandas as pd
import os
from datetime import datetime, timedelta
from config import PROCESSED_DIR, THRESHOLD_FRACTION

def analyze_phenology():
    """Analyzes the NDVI summary to find key phenology dates and chart data."""
    csv_path = os.path.join(PROCESSED_DIR, 'ndvi_summary.csv')
    if not os.path.exists(csv_path):
        raise FileNotFoundError("Run preprocessing first.")
        
    df = pd.read_csv(csv_path).sort_values(["year", "doy"])
    df["date"] = df.apply(lambda r: (datetime(r["year"], 1, 1) + timedelta(days=int(r["doy"] - 1))).date(), axis=1)
    
    df["ndvi_smooth"] = df["mean_ndvi"].rolling(window=3, center=True, min_periods=1).mean()
    
    min_ndvi = df["ndvi_smooth"].min()
    max_ndvi = df["ndvi_smooth"].max()
    amplitude = max_ndvi - min_ndvi
    threshold = min_ndvi + THRESHOLD_FRACTION * amplitude
    
    sos_row, pos_row, eos_row = None, None, None
    
    above_threshold = df[df["ndvi_smooth"] >= threshold]
    if not above_threshold.empty:
        sos_row = above_threshold.iloc[0]
        eos_row = above_threshold.iloc[-1]
    
    pos_row = df.loc[df["ndvi_smooth"].idxmax()]
    
    # NEW: Prepare timeseries data for the enhanced chart
    chart_timeseries = df.apply(lambda row: {
        'date': row['date'].isoformat(),
        'mean_ndvi': row['mean_ndvi'],
        'ndvi_smooth': row['ndvi_smooth']
    }, axis=1).tolist()
    
    return {
        "start_of_season": sos_row['date'].isoformat() if sos_row is not None else "N/A",
        "peak_of_season": pos_row['date'].isoformat() if pos_row is not None else "N/A",
        "end_of_season": eos_row['date'].isoformat() if eos_row is not None else "N/A",
        "peak_ndvi": round(pos_row['mean_ndvi'], 3) if pos_row is not None else "N/A",
        # NEW: Add these keys for the frontend chart
        "threshold_value": threshold,
        "timeseries": chart_timeseries
    }