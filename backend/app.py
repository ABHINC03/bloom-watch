from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import json
import pandas as pd
from config import STATIC_DIR, AREA_OF_INTEREST # Import AREA_OF_INTEREST
from analysis import analyze_phenology
from forecast import predict_next_pos

app = Flask(__name__, static_folder=STATIC_DIR, template_folder='templates')
CORS(app)

# Path to our pre-compiled results
RESULTS_DIR = os.path.join(STATIC_DIR, 'results')

@app.route("/")
def index():
    """
    Serves the main page, now pre-loaded with all the data
    the frontend needs to display the results immediately.
    """
    try:
        analysis_results = analyze_phenology()
        forecast_results = predict_next_pos()

        # Get the list of frame filenames from the static results directory
        frames = sorted([f for f in os.listdir(RESULTS_DIR) if f.startswith('frame_') and f.endswith('.png')])
        
        # --- THIS IS THE FIX ---
        # We now use the correct bounds directly from the AREA_OF_INTEREST
        # defined in config.py, instead of an incorrect placeholder.
        # Leaflet format is [[lat_min, lon_min], [lat_max, lon_max]]
        bounds = [[AREA_OF_INTEREST[0], AREA_OF_INTEREST[1]], [AREA_OF_INTEREST[2], AREA_OF_INTEREST[3]]]

        page_data = {
            'status': 'complete',
            'gif_url': '/static/results/ndvi_animation.gif',
            'timeseries_url': '/static/results/timeseries.json',
            'analysis': analysis_results,
            'forecast': forecast_results,
            'bounds': bounds,
            'frames': frames
        }
        return render_template("index.html", page_data=page_data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"An error occurred: {e}"

# This route serves the individual frame images for the story mode and other results
@app.route('/static/results/<path:filename>')
def serve_results_file(filename):
    return send_from_directory(RESULTS_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)