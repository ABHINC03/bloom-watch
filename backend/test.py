import os
import numpy as np
import pandas as pd
from osgeo import gdal, osr
import rasterio
from affine import Affine
from rasterio.mask import mask
from rasterio.warp import transform_geom
from shapely.geometry import box
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

print("--- Starting Diagnostic Test ---")

# --- Configuration (Copied from config.py) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TILE_DIR = os.path.join(BASE_DIR, "data", "tiles")
NDVI_SCALE = 0.0001
AREA_OF_INTEREST = [34.0, -119.5, 36.0, -117.5]

# --- IMPORTANT: VERIFY THIS FILENAME ---
# Make sure this filename exists in your 'backend/data/tiles/' folder
hdf_filename = "MOD13Q1.A2023081.h08v05.061.2023100010342.hdf"
hdf_path = os.path.join(TILE_DIR, hdf_filename)

# --- Test Logic (Copied from preprocess.py) ---
try:
    print(f"1. Opening HDF file: {hdf_filename}")
    ds = gdal.Open(hdf_path)
    if ds is None: raise RuntimeError(f"Cannot open {hdf_path}")
    sds = ds.GetSubDatasets()
    
    ndvi_path = None
    for name, desc in sds:
        if "250m 16 days NDVI" in desc: ndvi_path = name
    if not ndvi_path: raise RuntimeError("NDVI subdataset not found.")
    
    print("2. Extracting NDVI data...")
    ndvi_ds = gdal.Open(ndvi_path)
    gt = ndvi_ds.GetGeoTransform()
    projection_wkt = ndvi_ds.GetProjection()
    ndvi = ndvi_ds.ReadAsArray().astype(float) * NDVI_SCALE

    print("3. Clipping data to Area of Interest...")
    transform_obj = Affine.from_gdal(*gt)
    crs_obj = rasterio.crs.CRS.from_wkt(projection_wkt)
    aoi_geom_wgs84 = box(AREA_OF_INTEREST[1], AREA_OF_INTEREST[0], AREA_OF_INTEREST[3], AREA_OF_INTEREST[2])
    aoi_geom_native = transform_geom('EPSG:4326', crs_obj, aoi_geom_wgs84)
    with rasterio.io.MemoryFile() as memfile:
        with memfile.open(
            driver='GTiff', height=ndvi.shape[0], width=ndvi.shape[1], count=1,
            dtype=str(ndvi.dtype), crs=crs_obj, transform=transform_obj
        ) as dataset:
            dataset.write(ndvi, 1)
            clipped_array, clipped_transform = mask(dataset, [aoi_geom_native], crop=True, all_touched=True, invert=False)

    clipped_array = clipped_array.squeeze()
    nodata_val = -3000 * NDVI_SCALE
    clipped_array[clipped_array == nodata_val] = np.nan

    print("4. Generating final image with transparency...")
    # --- This is the specific logic to test ---
    cmap = plt.get_cmap('YlGn')
    cmap.set_bad(alpha=0.0)
    masked_arr = np.ma.masked_invalid(clipped_array)
    
    fig, ax = plt.subplots(figsize=(6, 6))
    im = ax.imshow(masked_arr, cmap=cmap, vmin=-0.2, vmax=1.0)
    ax.set_title("Test Frame"); ax.axis('off')
    plt.colorbar(im)
    
    output_filename = "TEST_FRAME.png"
    plt.savefig(output_filename, transparent=True, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    
    print(f"\n--- SUCCESS! ---")
    print(f"A new file named '{output_filename}' has been created in your 'backend' folder.")

except Exception as e:
    print(f"\n--- ERROR ---")
    print(f"The test failed with an error: {e}")
    import traceback
    traceback.print_exc()