import os
import json
from config import STATUS_FILE

'''
    Script to populate status.json
    Editar dataset_path e status_file
'''
dtypes = ["AXIAL", "SAGITTAL", "DYNAMIC"]
status_file = STATUS_FILE

# Load the existing status dictionary or create a new one if the file doesn't exist yet
if os.path.isfile(status_file):
    with open(status_file, 'r') as f:
        status_dict = json.load(f)
else:
    status_dict = {}
for dtype in dtypes:
    dataset_path = f'D:/DataOrtho/DATASET_{dtype}'
    individual_dirs = [item for item in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, item))]
    for individual in sorted(individual_dirs, key=int):
        individual_path = os.path.join(dataset_path, individual)

        # knee folders left -> right
        for knee in sorted(os.listdir(individual_path)):
            knee_path = os.path.join(individual_path, knee)
            if os.path.isdir(knee_path):
                # iterate through the sequence folders
                for sequence in os.listdir(knee_path):
                    sequence_path = os.path.join(knee_path, sequence)
                    if os.path.isdir(sequence_path):
                        status_dict[sequence_path] = 0
# Save the status dictionary back to the status file
with open(status_file, 'w') as f:
    json.dump(status_dict, f, indent=4)