import os
import pandas as pd
from sklearn.linear_model import LinearRegression
from config import PROCESSED_DIR

def predict_next_pos():
    csv_path = os.path.join(PROCESSED_DIR, 'ndvi_summary.csv')
    if not os.path.exists(csv_path):
        return {"message": "Run preprocessing first."}
        
    df = pd.read_csv(csv_path).dropna(subset=['year', 'doy', 'mean_ndvi'])
    if df.empty: return {"message": "Not enough data for forecast."}

    pos_data = df.loc[df.groupby('year')['mean_ndvi'].idxmax()]
    if len(pos_data) < 2:
        return {"message": "At least two years of data are needed to forecast."}

    X = pos_data['year'].values.reshape(-1, 1)
    y = pos_data['doy'].values
    model = LinearRegression().fit(X, y)
    
    next_year = int(pos_data['year'].max()) + 1
    predicted_doy = model.predict([[next_year]])[0]
    predicted_date = (pd.to_datetime(f'{next_year}-01-01') + pd.to_timedelta(int(predicted_doy) - 1, unit='d')).date().isoformat()

    return {
        "next_year": next_year,
        "predicted_pos_date": predicted_date
    }