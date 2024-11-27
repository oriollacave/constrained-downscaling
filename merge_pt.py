import torch
import os
import sys

base_dir = sys.argv[1]
train_test_val = sys.argv[2]
dir = base_dir + "/" + train_test_val + "/"

print("Merging training data from " + dir)

d04_files = [os.path.join(dir, f) for f in os.listdir(dir) if f.startswith("d04_tensor")]
d05_files = [os.path.join(dir, f) for f in os.listdir(dir) if f.startswith("d05_tensor")]

def merge_tensors(file_list):
    tensors = [torch.load(f) for f in file_list]
    return torch.cat(tensors, dim=0)

d04_merged = merge_tensors(d04_files)
d05_merged = merge_tensors(d05_files)
print(os.path.join(str(dir), "d04_"+train_test_val+"_merged.pt"))

torch.save(d04_merged, os.path.join(str(dir), "d04_"+train_test_val+"_merged.pt"))
torch.save(d05_merged, os.path.join(str(dir), "d05_"+train_test_val+"_merged.pt"))

print(f"Training data merged and saved to {dir}.")

