import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Directory Paths ---
TILE_DIR = os.path.join(BASE_DIR, "data", "tiles")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# --- THIS IS THE FIX ---
# The PROCESSED_DIR now correctly points to the 'static/results' folder,
# where the pre-compiled ndvi_summary.csv is located for the demo.
PROCESSED_DIR = os.path.join(BASE_DIR, "static", "results")

# This path is no longer needed for the pre-compiled demo but is kept for consistency
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "outputs")

# --- Data & Model Parameters ---
NDVI_SCALE = 0.0001
THRESHOLD_FRACTION = 0.4
AREA_OF_INTEREST = [34.0, -119.5, 36.0, -117.5]

def setup_directories():
    """Creates all required directories if they don't exist."""
    # Only TILE_DIR and STATIC_DIR/RESULTS_DIR need to exist for the demo
    os.makedirs(TILE_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True) # This will now create the 'static/results' folder