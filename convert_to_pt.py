import xarray as xr
import torch
import os
import sys

# Input files
d04_nc = sys.argv[1]
d05_nc = sys.argv[2]

# Output files
d04_pt = "d04_tensor.pt"
d05_pt = "d05_tensor.pt"

def netcdf_to_tensor(input_file, output_file):
    print(f"Processing {input_file}...")
    
    # Load NetCDF data
    ds = xr.open_dataset(input_file)
    
    # Select variable "M"
    if "M" not in ds:
        raise ValueError(f"'M' variable not found in {input_file}.")
    data = ds["M"].values  # Shape: [time, lat, lon]
    
    # Add channel dimension (1 for single variable)
    data = data[:, None, :, :]  # Shape: [time, 1, lat, lon]
    
    # Convert to PyTorch tensor
    tensor = torch.tensor(data, dtype=torch.float32)
    
    # Save as .pt file
    torch.save(tensor, output_file)
    print(f"Saved to {output_file} (shape: {tensor.shape})")

# Convert and save tensors
netcdf_to_tensor(d04_nc, d04_pt)
netcdf_to_tensor(d05_nc, d05_pt)

print("Conversion complete!")

