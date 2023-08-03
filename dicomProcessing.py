import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import os
import re
import json
import pydicom
import numpy as np
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut
import pandas as pd

'''
    The DICOM standard specifies the patient coordinate system in a very specific way: the positive X-axis points to the patient's left, 
    the positive Y-axis points to the anterior (front) of the patient, and the positive Z-axis points to the head. 
    In other words, if the patient is lying down in the scanner with their head pointed at the screen and their feet pointing away, 
    their left would be to the right of the screen, their anterior would be to the top of the screen, and their head would be coming out of the screen.
            
    The VTK viewer has to reconcile two different coordinate systems the vtks and the DICOM standard. 
    The -90 degrees Z rotation applied is correcting for this initial rotation, bringing the images back into their original orientation as they were in the patient.
            
'''
excel_paths = {'DATASET_AXIAL': 'D:/DataOrtho/DATASET_AXIAL/dataset_axial.xlsx', 
                            'DATASET_SAGITTAL': 'D:/DataOrtho/DATASET_SAGITTAL/dataset_sagittal.xlsx',
                            'DATASET_DYNAMIC': 'D:/DataOrtho/DATASET_DYNAMIC/dataset_dynamic.xlsx'}
max_landmarks = {'DATASET_AXIAL':11,'DATASET_SAGITTAL':7,'DATASET_DYNAMIC':18} 
class Landmark:
    def __init__(self, position):
        self.position = position # includes the index
        self.circle = vtk.vtkRegularPolygonSource()
        self.circle.SetNumberOfSides(50)
        self.circle.SetCenter(position[0], position[1], 0) 
        self.circle.SetRadius(1.5)  # Set the radius of the marker
        print(f'Landmark index: {self.position[2]}, Landmark center: {self.circle.GetCenter()} , Landmark radius: {self.circle.GetRadius()}')
        self.circleMapper = vtk.vtkPolyDataMapper()
        self.circleMapper.SetInputConnection(self.circle.GetOutputPort())
        self.circleActor = vtk.vtkActor()
        self.circleActor.SetMapper(self.circleMapper)
        r, g, b = 179/255.0, 29/255.0, 29/255.0  #normalized to 0-1 scale
        self.circleActor.GetProperty().SetColor(r,g,b)  #b31d1d color
        

class DICOMImage:
    def __init__(self, dicom_dir,ren):
        # DICOM Paths for pydicom parsing
        self.dicom_dir = dicom_dir
        self.dicom_paths = [os.path.join(dicom_dir, file_name) for file_name in sorted(os.listdir(dicom_dir)) if file_name.endswith('.dcm')]
        self.image_data = vtk.vtkImageData()
        self.actor = vtk.vtkImageActor()
        self.ren = ren
        self.ren.AddActor(self.actor)
        self.landmarks={} 
        # status
        self.status = 0
        # Image properties
        self.index = 0
        self.max_slice = len(self.dicom_paths)
        self.width = 0
        self.height = 0
        self.dataset_type = ''
        self.max_count = 0
        self.knee = ''
        self.individual = ''
        self.sequence = ''  
        self.extract_components(dicom_dir) # populate them props 
        #first load
        self.load_dicom()
        self.update_image()
        self.actor.Modified()
        self.center = self.actor.GetCenter()
    
    '''  DICOM image iteration Treatment '''  
    def load_dicom(self):
        if not self.dicom_paths:
            print("No valid DICOM images found.")
            return
        try:
            first_ds = pydicom.dcmread(self.dicom_paths[0])
            self.image_data.SetDimensions(first_ds.Columns,first_ds.Rows, len(self.dicom_paths))
            self.image_data.AllocateScalars(vtk.VTK_INT, 1)
            self.image_data.width = self.width = first_ds.Columns
            self.image_data.height = self.height = first_ds.Rows 
            for i, dicom_path in enumerate(self.dicom_paths):
                try:
                    ds = pydicom.dcmread(dicom_path)
                    arr = ds.pixel_array
                    hu = apply_modality_lut(arr, ds)
                    pixel_array = apply_voi_lut(hu, ds)
                    # normalizing the image intensities between 0 and 255 in order to display as a grayscale image.
                    pixel_array = ((pixel_array - pixel_array.min()) * (255.0 / (pixel_array.max() - pixel_array.min()))).astype('uint8') 
                    for y in range(arr.shape[0]):
                        for x in range(arr.shape[1]):
                            self.image_data.SetScalarComponentFromFloat(x, y, i, 0, pixel_array[y, x])
                except Exception as e:
                    print(f"Error reading {dicom_path} during pixel array formation: {str(e)}")
                    continue
                
        except Exception as e:
            print(f"Error reading {self.dicom_paths[0]}: {str(e)}")   
            self.dicom_paths.pop(0)
            self.load_dicom()
    # next image
    def next_image(self):
        if self.index < len(self.dicom_paths) - 1:
            self.index += 1
            self.update_image()
                    
    # prev image
    def prev_image(self):
        if self.index > 0:
            self.index -= 1
            self.update_image()     
              
    # update slice image        
    def update_image(self):
        reslice = vtk.vtkImageReslice()
        reslice.SetInputData(self.image_data)
        reslice.SetOutputDimensionality(2)
        reslice.SetResliceAxesOrigin(0, 0, self.index)
        reslice.Update()
        self.actor.GetMapper().SetInputData(reslice.GetOutput())
        self.actor.Modified()
        self.update_landmarks_visibility()
    
    # actor current properties for window/level and constrast on window
    def get_image_property(self):
        return self.actor.GetProperty()
    
    # get actor center 
    def get_center(self):
        return self.center

    ''' Landmark State Treatment '''      
    def add_landmark(self, position):
        landmark = Landmark(position)
        landmark.circleActor.SetUserTransform(self.actor.GetUserTransform())  # Apply the same transformation
        self.ren.AddActor(landmark.circleActor)
        slice_index = position[2]  # z is the slice index, and also the key
        if slice_index not in self.landmarks:
            self.landmarks[slice_index] = []
        self.landmarks[slice_index].append(landmark)
        self.update_landmarks_visibility()
        self.ren.GetRenderWindow().Render()
    
    def remove_landmark(self):
        if self.index in self.landmarks and len(self.landmarks[self.index]) > 0:
            removed_landmark = self.landmarks[self.index].pop()
            # remove the landmark actor from the renderer
            self.ren.RemoveActor(removed_landmark.circleActor)
            self.ren.GetRenderWindow().Render()
            return True, (removed_landmark.position)
        return False,()
        
    # Update of the points/landmark visibility, landmark marked on a slice are specific only to that slice
    def update_landmarks_visibility(self):
        for slice_index, landmarks in self.landmarks.items():
            for landmark in landmarks:
                # if the slice index is the current index, the landmark should be visible
                # else it should be invisible
                landmark.circleActor.SetVisibility(slice_index == self.index)
                      
    # Saves the landmarks to the supposed files - json and excel
    def save_landmarks(self):
        json_file = os.path.join(self.dicom_dir, f"{self.sequence}.json")
        print('-> Landmarks saved for json file: ', json_file)
        # dictionary where each key-value pair represents a slice/frame 
        slice_data_dict = {
            slice_id: {
                "Dataset": self.dataset_type,
                "Individual": self.individual,
                "Knee": self.knee,
                "Sequence": self.sequence,
                "Slice": slice_id,
                "#Landmarks": len(lm_list),
                "Landmarks": [
                    (lm.position[0], lm.position[1]) # change the position for the image processing coordinates
                    for lm in lm_list
                ],
            }
            for slice_id, lm_list in self.landmarks.items() if lm_list
        }

        with open(json_file, "w") as f:
            json.dump(slice_data_dict, f, ensure_ascii=False, indent=4)
        excel_file_path = excel_paths[self.dataset_type]        
        subset_df = pd.read_excel(excel_file_path)
        # checking if the sequence exists in the DataFrame
        # for each slice create a new row or update existing one
        for slice_data in slice_data_dict.values():
            slice_data["Landmarks"] = str(slice_data["Landmarks"])  # Convert list to string with correct coordinates on it
            #  if individual and sequence combination already exists check
            matching_rows = (subset_df["Individual"] == slice_data["Individual"]) & (subset_df["Sequence"] == slice_data["Sequence"]) & (subset_df["Slice"] == slice_data["Slice"])
            if matching_rows.any():
                subset_df.loc[matching_rows, slice_data.keys()] = slice_data.values()
            else:
                subset_df = subset_df.append(slice_data, ignore_index=True)
        subset_df.to_excel(excel_file_path, index=False)
        self.status = 1
        # remove slices where there are empty lists
        self.landmarks = {k: v for k,v in self.landmarks.items() if v}
        
    
    # Clear all landmarks marked in every slice and if status 1 clear json 
    def clear_landmarks(self):
        for slice_index, landmarks in self.landmarks.items():
                for landmark in landmarks:
                    self.ren.RemoveActor(landmark.circleActor)
        self.landmarks.clear()    
        self.ren.GetRenderWindow().Render()
        if self.status == 1:
            json_file = os.path.join(self.dicom_dir, f"{self.sequence}.json")
            with open(json_file,'w') as f:
                json.dump({},f,indent=4)
            self.status = 0
            excel_file_path = excel_paths[self.dataset_type]        
            subset_df = pd.read_excel(excel_file_path)
            # its not removing the landmarks
            mask = (subset_df["Individual"] == int(self.individual)) & (subset_df["Sequence"] == self.sequence)
            subset_df = subset_df[~(mask)]
            subset_df.to_excel(excel_file_path, index=False)
            return 1
        return 0
            
            
    # Get properties from any images sequence path 
    def extract_components(self,dicom_dir):
        # Define the regex pattern
        pattern = r"(?P<Dataset>DATASET_\w+)[\\/](?P<Individual>\d+)[\\/](?P<Knee>LEFT|RIGHT)[\\/](?P<Sequence>[\w-]+)[\\/]*"
        match = re.search(pattern, dicom_dir)
        # matched groups as a dictionary if true
        if match:
            # example: {'Dataset': 'DATASET_AXIAL', 'Individual': '1', 'Knee': 'LEFT', 'Sequence': 'pd_tse_fs_tra_320_3'}
            self.dataset_type = match.groupdict().get('Dataset')
            self.individual = match.groupdict().get('Individual')
            self.knee = match.groupdict().get('Knee')
            self.sequence = match.groupdict().get('Sequence')
            self.max_count = max_landmarks[self.dataset_type]
        else:
            print('Impossible to parse the string and get the properties of dicom images')