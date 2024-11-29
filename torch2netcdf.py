import torch
import xarray as xr
import numpy as np
import sys

def pt_to_netcdf(pt_file, netcdf_file):
    # Load the prediction from the .pt file
    predictions = torch.load(pt_file)
    
    # Convert to NumPy array
    predictions_np = predictions.numpy()
    
    # Check the shape of the predictions
    print(f"Predictions shape: {predictions_np.shape}")
    
    # Assuming the shape is (time, lev, lat, lon)
    # Adjust the dimensions as needed
    if predictions_np.ndim == 5:
        print("Reshaping the predictions")
        time, lev, depth, lat, lon = predictions_np.shape
        predictions_np = predictions_np.reshape(time, lev, lat, lon)
    else:
        print("DIM LOW THAN 5")
    # Print dimensions and their sizes
    print(f"Dimensions: time={time}, lev={lev}, lat={lat}, lon={lon}")

    # Create NetCDF dataset
    ds = xr.Dataset(
        {
            "M": (("time", "lev", "lat", "lon"), predictions_np)
        },
        coords={
            "time": np.arange(predictions_np.shape[0]),
            "lev": np.arange(predictions_np.shape[1]),
            "lat": np.arange(predictions_np.shape[2]),
            "lon": np.arange(predictions_np.shape[3]),
        },
    )
    
    # Add attributes
    ds["time"].attrs = {
        "standard_name": "time",
        "units": "hours since 2008-01-01 12:00",
        "calendar": "standard",
        "axis": "T"
    }
    ds["lat"].attrs = {
        "standard_name": "latitude",
        "long_name": "Latitude",
        "units": "degrees_north",
        "axis": "Y"
    }
    ds["lon"].attrs = {
        "standard_name": "longitude",
        "long_name": "Longitude",
        "units": "degrees_east",
        "axis": "X"
    }
    ds["lev"].attrs = {
        "long_name": "Vertical levels",
        "units": "m",
        "axis": "Z"
    }
    ds["M"].attrs = {
        "_FillValue": -999.0,
        "missing_value": -999.0
    }
    
    # Save as NetCDF file
    ds.to_netcdf(netcdf_file, mode="w", format="NETCDF4")
    print(f"Predictions saved to {netcdf_file}")

# Example usage
if __name__ == "__main__":
    pt_file = sys.argv[1]
    netcdf_file = sys.argv[2]
    pt_to_netcdf(pt_file, netcdf_file)