import os
import json
import numpy as np
import pandas as pd
from osgeo import gdal, osr
import rasterio
from affine import Affine
from rasterio.transform import from_origin
from rasterio.mask import mask
from rasterio.warp import transform_geom
from shapely.geometry import box
import imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from config import TILE_DIR, PROCESSED_DIR, OUTPUT_DIR, STATIC_DIR, NDVI_SCALE, AREA_OF_INTEREST

def extract_ndvi_and_valid_fraction(hdf_file):
    ds = gdal.Open(hdf_file)
    if ds is None: raise RuntimeError(f"Cannot open {hdf_file}")
    sds = ds.GetSubDatasets()
    
    ndvi_path, qa_path = None, None
    for name, desc in sds:
        if "250m 16 days NDVI" in desc: ndvi_path = name
        if "VI Quality" in desc or "pixel reliability" in desc: qa_path = name

    if not ndvi_path: raise RuntimeError("NDVI subdataset not found in " + hdf_file)

    ndvi_ds = gdal.Open(ndvi_path)
    
    gt = ndvi_ds.GetGeoTransform()
    projection_wkt = ndvi_ds.GetProjection()

    ndvi = ndvi_ds.ReadAsArray().astype(float) * NDVI_SCALE
    if qa_path:
        qa = gdal.Open(qa_path).ReadAsArray()
        good_quality_mask = (qa <= 1)
        ndvi[~good_quality_mask] = np.nan

    transform_obj = Affine.from_gdal(*gt)
    crs_obj = rasterio.crs.CRS.from_wkt(projection_wkt)

    # 1. Create the AOI geometry in Lat/Lon (WGS84)
    aoi_geom_wgs84 = box(AREA_OF_INTEREST[1], AREA_OF_INTEREST[0], AREA_OF_INTEREST[3], AREA_OF_INTEREST[2])

    # 2. Transform the AOI geometry to the raster's native CRS (Sinusoidal)
    aoi_geom_native = transform_geom('EPSG:4326', crs_obj, aoi_geom_wgs84)

    # 3. Mask the data using the correctly projected geometry
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
    
    ulx, uly = clipped_transform.c, clipped_transform.f
    lrx = ulx + (clipped_array.shape[1] * clipped_transform.a)
    lry = uly + (clipped_array.shape[0] * clipped_transform.e)

    source_srs = osr.SpatialReference(); source_srs.ImportFromWkt(projection_wkt)
    target_srs = osr.SpatialReference(); target_srs.ImportFromEPSG(4326)
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(source_srs, target_srs)
    ul_coords = transform.TransformPoint(ulx, uly); lr_coords = transform.TransformPoint(lrx, lry)
    bounds = [[lr_coords[1], ul_coords[0]], [ul_coords[1], lr_coords[0]]]

    valid_fraction = np.count_nonzero(~np.isnan(clipped_array)) / clipped_array.size
    return clipped_array, valid_fraction, bounds

def save_geotiff(path, arr):
    pass 

def process_all_hdf_files():
    records, first_bounds = [], None
    files = sorted([f for f in os.listdir(TILE_DIR) if f.lower().endswith('.hdf')])
    if not files: return {"status": "no_files", "message": f"No .hdf files found in {TILE_DIR}"}

    for fname in files:
        fpath = os.path.join(TILE_DIR, fname)
        try:
            ndvi, valid_fraction, bounds = extract_ndvi_and_valid_fraction(fpath)
            if first_bounds is None and valid_fraction > 0 and bounds is not None: first_bounds = bounds
            if np.isnan(ndvi).all(): print(f"Warning: All pixels masked out for {fname}. Skipping."); continue
            
            parts = fname.split('.'); year, doy = int(parts[1][1:5]), int(parts[1][5:8])
            date_iso = (pd.to_datetime(f'{year}-01-01') + pd.to_timedelta(doy - 1, unit='d')).date().isoformat()
            
            mean_ndvi = float(np.nanmean(ndvi))
            records.append({'file': fname, 'year': year, 'doy': doy, 'date_iso': date_iso, 'mean_ndvi': mean_ndvi, 'valid_fraction': valid_fraction, 'ndvi_data': ndvi})
        except Exception as e: 
            print(f"Error processing {fname}: {e}")
            import traceback
            traceback.print_exc()

    if not records: return {"status": "error", "message": "No valid data could be processed."}
    
    df = pd.DataFrame(records).sort_values(['year', 'doy']).reset_index(drop=True)
    df.drop(columns=['ndvi_data']).to_csv(os.path.join(PROCESSED_DIR, 'ndvi_summary.csv'), index=False)
    
    df_json = df[['date_iso', 'mean_ndvi']].rename(columns={'date_iso': 'date'})
    with open(os.path.join(OUTPUT_DIR, 'timeseries.json'), 'w') as f: json.dump(df_json.to_dict('records'), f)

    frame_filenames = []
    for index, row in df.iterrows():
        arr = row['ndvi_data']
        masked_arr = np.ma.masked_where(arr < -0.1, arr)
        fig, ax = plt.subplots(figsize=(6, 6))
        fig.patch.set_alpha(0.0); ax.patch.set_alpha(0.0)
        im = ax.imshow(masked_arr, cmap='YlGn', vmin=-0.2, vmax=1.0);
        ax.set_title(row['date_iso']); ax.axis('off')
        plt.colorbar(im, fraction=0.046, pad=0.04)
        frame_filename = f"frame_{row['date_iso']}.png"
        plt.savefig(os.path.join(OUTPUT_DIR, frame_filename), transparent=True, bbox_inches='tight', pad_inches=0); plt.close(fig)
        frame_filenames.append(frame_filename)

    gif_frames = [imageio.imread(os.path.join(OUTPUT_DIR, f)) for f in frame_filenames]
    imageio.mimsave(os.path.join(STATIC_DIR, 'ndvi_animation.gif'), gif_frames, duration=0.5)
    
    return {'status': 'ok', 'gif_url': '/static/ndvi_animation.gif', 'timeseries_url': '/outputs/timeseries.json', 'bounds': first_bounds, 'frames': frame_filenames}