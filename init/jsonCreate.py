''' Script to add .json files for state oversight in LabelingGUI
    Editar dataset_path
    Running again resets all of the json files on the desired paths if existing
'''
import os
import json
import sys
from config import BASE_DIR

dtypes = ["AXIAL", "SAGITTAL", "DYNAMIC"]


# Iterate through the individual folders
for dtype in dtypes:
    dataset_path = f'{BASE_DIR}/DATASET_{dtype}'
    for individual in os.listdir(dataset_path):
        individual_path = os.path.join(dataset_path, individual)
        
        if os.path.isdir(individual_path):
            # Iterate through the knee folders (LEFT or RIGHT)
            # print(individual_path)
            for knee in os.listdir(individual_path):
                knee_path = os.path.join(individual_path, knee)
                if os.path.isdir(knee_path):
                    # Iterate through the sequence folders
                    for sequence in os.listdir(knee_path):
                        sequence_path = os.path.join(knee_path, sequence)

                        if os.path.isdir(sequence_path):
                            # Create an empty .json file with the same name as the sequence folder
                            json_file_path = os.path.join(sequence_path, f"{sequence}.json")
                            with open(json_file_path, "w") as json_file:
                                json.dump({}, json_file)
