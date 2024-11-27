import sys
import torch
file_path=sys.argv[1]

data = torch.load(file_path)
print(data)
print(f"Type of data: {type(data)}")
if isinstance(data, dict):
    print("Keys in the dictionary:")
    print(data.keys())

    print("\nInspecting contents:")
    for key, value in data.items():
        if isinstance(value, torch.Tensor):
            print(f"{key}: Tensor with shape {value.shape}")
        else:
            print(f"{key}: {type(value)}")
elif isinstance(data, (list, tuple)):
    print(f"Data is a {type(data)} with {len(data)} elements.")
    for i, item in enumerate(data):
        if isinstance(item, torch.Tensor):
            print(f"Element {i}: Tensor with shape {item.shape}")
        else:
            print(f"Element {i}: {type(item)}")
elif isinstance(data, torch.Tensor):
    print(f"Data is a Tensor with shape {data.shape}")
else:
    print("Unknown data structure. Try inspecting attributes with dir(data):")
    print(dir(data))

