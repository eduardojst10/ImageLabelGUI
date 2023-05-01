''' Script to add .json files for state oversight in imageGUI
'''
import os
import json



# Set the path to the dataset folder
dataset_path = "PATH/TO/DESIRED/DATASET"

# Iterate through the individual folders
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
