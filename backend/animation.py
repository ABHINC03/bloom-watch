import os
import imageio
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server
import matplotlib.pyplot as plt
import rasterio
from config import TILE_DIR, OUTPUT_DIR, STATIC_DIR
from preprocess import extract_ndvi

def create_ndvi_animation():
    """
    Creates a GIF animation of NDVI changes from the raw HDF files.
    """
    files = sorted([f for f in os.listdir(TILE_DIR) if f.lower().endswith('.hdf')])
    if not files:
        return None

    frames = []
    temp_frame_files = []
    
    for i, fname in enumerate(files):
        try:
            fpath = os.path.join(TILE_DIR, fname)
            ndvi_array = extract_ndvi(fpath)

            fig, ax = plt.subplots(figsize=(6, 6))
            im = ax.imshow(ndvi_array, cmap='YlGn', vmin=-0.2, vmax=1.0)
            ax.set_title(fname.split('.')[1])
            ax.axis('off')
            plt.colorbar(im, fraction=0.046, pad=0.04)

            frame_path = os.path.join(OUTPUT_DIR, f"frame_{i:03d}.png")
            plt.savefig(frame_path)
            plt.close(fig)
            
            frames.append(imageio.imread(frame_path))
            temp_frame_files.append(frame_path)
        except Exception as e:
            print(f"Could not create frame for {fname}: {e}")

    if not frames:
        return None

    # Save GIF to the static folder so Flask can serve it
    gif_path = os.path.join(STATIC_DIR, 'ndvi_animation.gif')
    imageio.mimsave(gif_path, frames, duration=0.5)

    # Clean up temporary frame images
    for f in temp_frame_files:
        os.remove(f)

    return gif_path
