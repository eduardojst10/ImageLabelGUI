from PyQt5 import QtCore
from PyQt5.QtGui import QStandardItem, QCursor, QStandardItemModel, QImageReader, QPixmap
from PyQt5.QtCore import Qt, QDir, QFileInfo, pyqtSignal, QObject
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QDockWidget,
        QHBoxLayout, QVBoxLayout, QSlider, QPushButton, QMessageBox,
        QFrame, QLabel, QComboBox, QTextEdit, QTreeView, QAbstractItemView, QListWidget)
import re
import json
import os
import sys
import vtk.util.numpy_support as nps
import numpy as np
from pathlib import Path
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from styles import button_style, combo_style,frame_number_style,coordinates_box_style, title_style, tree_view_style,scrollbar_css, buttonState_style, label_style, buttonReset_Style, buttonToggle_style
from dicomProcessing import DICOMImage, Landmark

''' -------------------  Global Vars -------------------'''
base_dir= 'D:/DataOrtho/'
status_file = 'D:/DataOrtho/status.json'
help_path = 'D:/DataOrthoHelp/'
excel_paths = {'DATASET_AXIAL': 'D:/DataOrtho/DAT ASET_AXIAL/dataset_axial.xlsx', 
                            'DATASET_SAGITTAL': 'D:/DataOrtho/DATASET_SAGITTAL/dataset_sagittal.xlsx',
                            'DATASET_DYNAMIC': 'D:/DataOrtho/DATASET_DYNAMIC/dataset_dynamic.xlsx'}
max_landmarks = {'DATASET_AXIAL':11,'DATASET_SAGITTAL':7,'DATASET_DYNAMIC':18} 

# SignalHandler class for Landmarks handling
class SignalHandler(QObject):
    landmarkAdded = pyqtSignal(int)
    landmarkRemoved = pyqtSignal(int)
    writeLandmark = pyqtSignal(int, int, float, float)
    clearLandmarks = pyqtSignal()
    nextSlice = pyqtSignal()
    previousSlice = pyqtSignal()

''' Custom interactor Style class for VTK window  '''

class CustomInteractorStyle(vtk.vtkInteractorStyleUser):
    def __init__(self,signalHandler,renderer,image_width,image_height,current_image,landmark_count,max_count,point_counter_label,parent=None):
        self.signalHandler = signalHandler
        self.AddObserver("MouseMoveEvent",self.mouse_move) 
        self.AddObserver("LeftButtonPressEvent",self.OnLeftButtonDown)
        self.AddObserver("RightButtonPressEvent",self.OnRightButtonDown)
        self.AddObserver("MouseWheelForwardEvent", self.OnMouseWheelForward)
        self.AddObserver("MouseWheelBackwardEvent", self.OnMouseWheelBackward)
        self.AddObserver("LeftButtonReleaseEvent",self.OnLeftButtonUp)
        #instead of pixel lets work with voxel
        self.picker = vtk.vtkCellPicker() 
        self.ren = renderer
        #Landmark treatment
        self.landmark_count = landmark_count
        self.max_count = max_count
        #Image stats
        self.current_image = current_image
        self.point_counter_label = point_counter_label
        self.image_width = image_width
        self.image_height = image_height
        print('|-> Image dimension for Interactor: ', (image_width,image_height), ' |')   
        # Camera settingsa
        self.panning = False # var to allow camera move
        self.init_camera_pos = self.ren.GetActiveCamera().GetPosition()  
        self.init_camera_focal_point = self.ren.GetActiveCamera().GetFocalPoint()
        self.init_camera_view_up = self.ren.GetActiveCamera().GetViewUp()
        self.signalHandler.clearLandmarks.connect(self.reset_landmark_count)
    
    # Needed? yup, get me them mouse moves
    '''
        Altering both the position and the focal point of the camera in the same direction. 
        appearing the camera to move parallel to the image plane, giving the effect of "panning" the image.
    '''
    def update_parameters(self,image_width,image_height,current_image,landmark_count, max_count):
            self.image_width = image_width
            self.image_height = image_height
            self.current_image = current_image
            self.landmark_count = landmark_count
            self.max_count = max_count
            print('|-> New Image dimension for Interactor: ', (self.image_height,self.image_width), '|')   
            # Reset initial camera parameters
            self.init_camera_pos = self.ren.GetActiveCamera().GetPosition()  
            self.init_camera_focal_point = self.ren.GetActiveCamera().GetFocalPoint() 
            self.init_camera_view_up = self.ren.GetActiveCamera().GetViewUp()
    
    def mouse_move(self,obj,event):
        if self.panning:
            zoomFactor = 0.05
            lastXYPos = self.GetInteractor().GetLastEventPosition()  
            curXYPos = self.GetInteractor().GetEventPosition()  
            camera = self.ren.GetActiveCamera()  

            dx = lastXYPos[0] -curXYPos[0] 
            dy = lastXYPos[1] - curXYPos[1] 

            cameraPos = camera.GetPosition()
            focalPos = camera.GetFocalPoint()
    
            camera.SetPosition(cameraPos[0] + dx * zoomFactor, cameraPos[1] - dy * zoomFactor, cameraPos[2])
            camera.SetFocalPoint(focalPos[0] + dx * zoomFactor, focalPos[1] - dy * zoomFactor, focalPos[2])
            self.ren.ResetCameraClippingRange() 
            self.ren.GetRenderWindow().Render()
    
    def OnLeftButtonDown(self,obj,event):
        shift_key = self.GetInteractor().GetShiftKey()
        if shift_key:
            self.panning = True
        else:
            x,y = self.GetInteractor().GetEventPosition()
            self.picker.Pick(x,y,0,self.ren)
            if self.landmark_count < self.max_count:            
                world_pos = self.picker.GetPickPosition()
                # vtk z-value does not interests us the labeling for now, lets pass the image index                
                image_pos = (world_pos[0],world_pos[1],self.current_image.index)
                if (0 <= image_pos[0] < self.image_width) and (0 <= image_pos[1] < self.image_height):
                    self.current_image.add_landmark(image_pos)
                    self.landmark_count+=1
                    print(f'+ Added Landmark {self.landmark_count} on slice {image_pos[2]} with coordinates: ', (image_pos[0],image_pos[1]))
                    self.point_counter_label.setText(f"Points: {self.landmark_count} - MAX: {self.max_count}")
                    self.signalHandler.landmarkAdded.emit(self.landmark_count)
                    self.signalHandler.writeLandmark.emit(image_pos[2], self.landmark_count, image_pos[0],image_pos[1])
    
    # Always stop the panning if not pressing    
    def OnLeftButtonUp(self,obj,event):
        if self.panning:
            self.panning = False
            
    def OnRightButtonDown(self,obj,event):
        remove, pos = self.current_image.remove_landmark()
        if self.landmark_count > 0 and remove: #just a pop?
            #if self.landmark_count != self.max_count:
            self.signalHandler.landmarkRemoved.emit(self.landmark_count)
            print(f'- Removed landmark {self.landmark_count} on slice {pos[2]} with coordinates: ', (pos[1],pos[0]))
            self.landmark_count-=1
            self.point_counter_label.setText(f"Points: {self.landmark_count} - MAX: {self.max_count}")
                 
    def OnMouseWheelForward(self,obj,event):
        shift_key = self.GetInteractor().GetShiftKey()
        if shift_key:    
            camera= self.ren.GetActiveCamera()
            camera.Dolly(1.1)
            self.ren.ResetCameraClippingRange()
            self.ren.GetRenderWindow().Render()
        else:
            self.signalHandler.nextSlice.emit()
    
    def OnMouseWheelBackward(self,obj,event):
        shift_key = self.GetInteractor().GetShiftKey()
        if shift_key: 
            camera = self.ren.GetActiveCamera()
            camera.Dolly(0.9)  # Zoom out
            self.ren.ResetCameraClippingRange()
            self.ren.GetRenderWindow().Render()
        else:
            self.signalHandler.previousSlice.emit()
        
    # Reseting the camera to its original values, position and focal point   
    def reset_camera(self):
        # Reset the camera to its initial parameters
        self.ren.GetActiveCamera().SetPosition(self.init_camera_pos)
        self.ren.GetActiveCamera().SetFocalPoint(self.init_camera_focal_point)
        self.ren.GetActiveCamera().SetViewUp(self.init_camera_view_up)
        self.ren.ResetCameraClippingRange()
        self.ren.GetRenderWindow().Render()
        
    def reset_landmark_count(self):
        print(f'- Removed {self.landmark_count} landmarks !')
        self.landmark_count = 0       

class LabelingGUIWindow(QMainWindow):
    def __init__(self, ):
        super().__init__()
        self.setWindowTitle("LabelingGUI")
        print("-- Welcome to LabelingGUIWindow's logs --\n")
        self.setGeometry(100, 100, 1400, 800)  # position and size of the initial window
        self.frameWidget = QWidget()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frameWidget)  
        
        ''' -------------  Variables of state -------------'''
        # First Current path is decided by current state - read of json 
        self.current_sequence_path, self.current_subset_path = self.getCurrentSequence()
        
        #Current help index
        self.help_image_index = 0
        self.help_images = []
        self.status = 0
        ''' -------------  GUI COMPONENTS -------------'''
        self.title_label = QLabel(self)
        self.title_label.setText("LabelingGUI")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.title_label.setStyleSheet(title_style)
        
        #Individual info, below imagebox
        self.image_path_label = QLabel(self)
        self.image_path_label.setStyleSheet(frame_number_style)
        #self.image_path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Updating the image_path_label
        self.update_image_path_label(self.current_sequence_path)
        
        # Landmark Points Counter
        self.landmark_count = 0
        self.max_count = max_landmarks[self.get_image_type(self.current_sequence_path)]
        self.point_counter_label = QLabel(self)
        self.point_counter_label.setText(f"Points: {0} - MAX: {self.max_count}")
        self.point_counter_label.setStyleSheet(frame_number_style)
        self.point_counter_label.setFixedSize(400,80)
        self.point_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
        
        # Add a number of Frame/Slice to localize in dataset 
        slice_label = QLabel("Frame/Slice:")
        slice_label.setStyleSheet(label_style)
        self.slice_number = QLabel(self)
        self.slice_number.setStyleSheet(frame_number_style)
        self.slice_number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        ''' -------------  IMAGE LOADING and HANDLING -------------'''
        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.current_image = DICOMImage(self.current_sequence_path,self.ren)
        image_width = self.current_image.width
        image_height = self.current_image.height
        self.vtkWidget.GetRenderWindow().Render()
        # initial parameters 
        camera = self.ren.GetActiveCamera()
        camera.SetFocalPoint(self.current_image.image_data.GetCenter())
        camera.SetPosition(self.current_image.image_data.GetCenter()[0], self.current_image.image_data.GetCenter()[1], -1)
        camera.SetViewUp(0, -1, 0)
        self.ren.ResetCamera()
        self.signalHandler = SignalHandler()
        self.signalHandler.landmarkAdded.connect(self.next_help_image)
        self.signalHandler.landmarkRemoved.connect(self.prev_help_image)
        self.signalHandler.landmarkRemoved.connect(self.remove_last_landmark_box)
        self.signalHandler.writeLandmark.connect(self.add_landmark_box)
        self.signalHandler.nextSlice.connect(self.next_image)
        self.signalHandler.previousSlice.connect(self.prev_image)
        self.interactor = self.vtkWidget.GetRenderWindow().GetInteractor()
        self.interactorStyle = CustomInteractorStyle(self.signalHandler,self.current_image.ren,image_width,image_height, 
                                                     self.current_image,0,self.max_count,self.point_counter_label)
        self.interactor.SetInteractorStyle(self.interactorStyle)
        
        ''' ------------  GUI OPERATERS -------------'''
        #---- slider ----  
        windowSlider_label = QLabel("Adjust Window Contrast:")
        windowSlider_label.setStyleSheet(label_style)      
        levelSlider_label = QLabel("Adjust Brightness Level:")
        levelSlider_label.setStyleSheet(label_style)   
        self.windowSlider = QSlider(QtCore.Qt.Horizontal)
        self.levelSlider = QSlider(QtCore.Qt.Horizontal) 
        self.windowSlider.setMinimum(0)
        self.windowSlider.setMaximum(255)
        self.levelSlider.setMinimum(0)
        self.levelSlider.setMaximum(255)
        self.windowSlider.valueChanged.connect(self.update_window)
        self.levelSlider.valueChanged.connect(self.update_level)
        
        # set up the initiall values of the sliders with the current values of the current_image
        window = self.current_image.get_image_property().GetColorWindow()
        level = self.current_image.get_image_property().GetColorLevel()
        self.windowSlider.setValue(window)
        self.levelSlider.setValue(level)
        #indexes start with 0, with to treat the slices starting from 1
        self.slice = self.current_image.index+1
        self.slice_number.setText(str(self.slice))
        
        #-- buttons --
        self.nextButton = QPushButton("Next",self)
        self.prevButton = QPushButton("Previous",self)
        self.clear_button = QPushButton('Clear Coordinates', self)
        self.save_button = QPushButton('Save Coordinates', self)
        self.resetView_button = QPushButton("Reset View",self)
        self.removeSequence_button = QPushButton("Remove Current Sequence",self)
        
        
        self.nextButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.prevButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.clear_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.save_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.resetView_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.removeSequence_button.setCursor(QCursor(Qt.PointingHandCursor))
        
        self.nextButton.setStyleSheet(button_style)
        self.prevButton.setStyleSheet(button_style)
        self.clear_button.setStyleSheet(buttonState_style)
        self.save_button.setStyleSheet(buttonState_style)
        self.resetView_button.setStyleSheet(buttonReset_Style)
        self.removeSequence_button.setStyleSheet(buttonReset_Style)
        
        self.nextButton.clicked.connect(self.next_image)
        self.prevButton.clicked.connect(self.prev_image)
        self.clear_button.clicked.connect(self.clear_Landmarks)
        self.save_button.clicked.connect(self.save_Landmarks)
        self.resetView_button.clicked.connect(self.reset_view)
        self.removeSequence_button.clicked.connect(self.remove_current_sequence)
        
        #-- lines --
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: black; border-style: inset;")
        
        line2 = QFrame(self)
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)
        
        #-- Combobox --        
        source_label = QLabel("Source Directory:")
        source_label.setStyleSheet(label_style)
        self.choose_picture_comboboxSource = QComboBox(source_label)
        self.choose_picture_comboboxSource.setStyleSheet(combo_style)
        self.choose_picture_comboboxSource.setFixedHeight(30)
        self.choose_picture_comboboxSource.addItems(self.getDirectories())
        self.choose_picture_comboboxSource.currentIndexChanged.connect(self.update_tree_view)
        
        #-- Tree View --
        self.tree_view = QTreeView(self)
        self.model = QStandardItemModel()
        self.tree_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_view.setModel(self.model)
        combined_css = tree_view_style + scrollbar_css
        self.tree_view.setStyleSheet(combined_css)       
        self.tree_view.clicked.connect(self.on_sequence_clicked)
        self.model.setHorizontalHeaderLabels(['Folder','Status','Landmarks'])
        self.add_folder_to_model(self.current_subset_path, self.model.invisibleRootItem(),0)
        
        #-- Read-only textlist for the display coordinates (help layout)-- 
        self.coordinates_box = QListWidget(self)
        self.coordinates_box.setMaximumWidth(500)
        self.coordinates_box.setStyleSheet(coordinates_box_style)
        self.coordinates_box.setSelectionMode(QAbstractItemView.NoSelection)
        self.coordinates_box.setEditTriggers(QAbstractItemView.NoEditTriggers)
              
        #-- Help Image holder --
        self.image_holder = QLabel(self)
        #self.image_holder.setScaledContents(True)
        self.load_help_images(self.get_image_type(self.current_sequence_path))
        
        ''' -------------------  LAYOUTS & MAIN WIDGETS -------------------'''
        # Operate layout composed by sub layouts:
            #  Source of patients data choice combobox Layout
        self.choose_data_layout = QVBoxLayout()
        self.choose_data_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.choose_data_layout.addWidget(source_label)
        self.choose_data_layout.addWidget(self.choose_picture_comboboxSource)
        self.choose_data_layout.addWidget(self.tree_view)
        self.choose_data_layout.setSpacing(5)
        
            # Image iteration button layout
        self.buttonIter_layout = QHBoxLayout()
        self.buttonIter_layout.addWidget(self.prevButton)
        self.buttonIter_layout.addWidget(self.nextButton)
        
            # Landmark state button layout
        self.buttonStat_layout = QHBoxLayout()
        self.buttonStat_layout.addWidget(self.clear_button)
        self.buttonStat_layout.addWidget(self.save_button)
        
            # slider layout
        self.slider_layout = QVBoxLayout()
        self.slider_layout.addWidget(windowSlider_label)
        self.slider_layout.addWidget(self.create_slider_with_labels(self.windowSlider,False))
        self.slider_layout.addWidget(levelSlider_label)
        self.slider_layout.addWidget(self.create_slider_with_labels(self.levelSlider,True))
        
        self.help_layout = QHBoxLayout()
        self.help_layout.addWidget(self.coordinates_box)
        self.help_layout.addWidget(self.image_holder)
        
            # Operate Layout
        self.operate_layout = QVBoxLayout()
        self.operate_layout.addWidget(self.title_label)
        self.operate_layout.addLayout(self.choose_data_layout)
        self.operate_layout.addLayout(self.slider_layout)
        self.operate_layout.addLayout(self.buttonIter_layout)
        self.operate_layout.addWidget(slice_label)
        self.operate_layout.addWidget(self.slice_number)
        self.operate_layout.addWidget(line2)
        self.operate_layout.addLayout(self.help_layout)
        self.operate_layout.addLayout(self.buttonStat_layout)
        
            # image Layout
        self.image_layout = QVBoxLayout()
        self.image_layout.addWidget(self.vtkWidget)
        self.image_layout.addWidget(self.point_counter_label,alignment=Qt.AlignmentFlag.AlignCenter)
        self.image_layout.addWidget(self.image_path_label,alignment=Qt.AlignmentFlag.AlignCenter)
        self.image_layout.addWidget(line2)

        self.image_Sublayout = QHBoxLayout()
        self.image_Sublayout.addWidget(self.resetView_button,alignment=Qt.AlignCenter)
        self.image_Sublayout.addWidget(self.removeSequence_button, alignment=Qt.AlignCenter)
        self.image_layout.addLayout(self.image_Sublayout)
        
        self.operate_widget = QWidget()
        self.operate_widget.setStyleSheet('background-color:#636E72')

        # Dock widget
        self.operate_dock = QDockWidget("Image Operate")
        self.operate_dock.setWidget(self.operate_widget)
        self.operate_dock.setAllowedAreas(Qt.RightDockWidgetArea)  # Allow only right docking
        self.operate_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.operate_widget.setLayout(self.operate_layout)
        
        
        self.image_widget = QWidget()
        self.image_widget.setLayout(self.image_layout)
        self.image_widget.setStyleSheet('background-color:#1e1f1c')
            # Main Layout
        self.mainPage_layout = QHBoxLayout()
        self.mainPage_layout.addWidget(self.image_widget)
        
        self.frameWidget.setLayout(self.mainPage_layout)
        self.setCentralWidget(self.frameWidget)
        self.setStyleSheet('background-color:#1e1f1c')
        self.addDockWidget(Qt.RightDockWidgetArea, self.operate_dock)
         # Create a button to toggle the dock widget
        self.toggle_dock_button = QPushButton("Toggle Operate", self.image_widget)
        self.toggle_dock_button.setStyleSheet(buttonToggle_style)
        self.toggle_dock_button.clicked.connect(self.toggle_operate_dock)
        
        #-- Interactor Initialization--
        self.interactor.Initialize()
        self.interactor.Start()
    
    # ---------------------------------------------- FUNCTIONS --------------------------------------#
    ''' ---------------------- TOGGLE OPERATE BLOCK ----------------------'''
    def toggle_operate_dock(self):
        # Hide the dock widget if it's visible, show it if it's hidden
        if self.operate_dock.isVisible():
            self.operate_dock.hide()
        else:
            self.operate_dock.show()
        ''' ---------------------- PATH HELPERS ----------------------'''
    # Get properties from images sequence path
    def extract_components(self,image_path):
        # Define the regex pattern
        pattern = r"(?P<Dataset>DATASET_\w+)[\\/](?P<Individual>\d+)[\\/](?P<Knee>LEFT|RIGHT)[\\/](?P<Sequence>[\w-]+)[\\/]*"
        # using regex pattern
        match = re.search(pattern, image_path)
        # matched groups as a dictionary if true
        if match:
            return match.groupdict()
        else:
            return None
        
    # In case of the new image_path 
    def get_relative_path(self, path, start):
        if os.path.splitdrive(path)[0] == os.path.splitdrive(start)[0]:
            return os.path.relpath(path, start)
        else:
            return os.path.abspath(path)
        
    # Quickly get the type of the Dataset: AXIAL, SAGITTAL, DYNAMIC  
    def get_image_type(self,image_path):
        # path relative to the base directory
        rel_path = self.get_relative_path(image_path,base_dir)
        parts = rel_path.split(os.path.sep)
        # get the the subset of DataOrtho name containing the type
        image_type = parts[0]
        return image_type
    
    ''' ------------------  BUTTONS AND SLIDER HANDLING ------------------'''
    #---- Slider handling ----
    # adjust brightness (window)
    def update_window(self):
        window = self.windowSlider.value()
        image_property = self.current_image.get_image_property()
        image_property.SetColorWindow(window)
        self.vtkWidget.GetRenderWindow().Render()
    
    # adjust contrast (level)
    def update_level(self):
        level = self.levelSlider.value()
        image_property = self.current_image.get_image_property()
        image_property.SetColorLevel(level)
        self.vtkWidget.GetRenderWindow().Render()
        
        
    def create_slider_with_labels(self, slider,inverse):
        layout = QHBoxLayout()

        minus_label = QLabel('-')
        plus_label = QLabel('+')
        minus_label.setStyleSheet('color: white; font-weight: DemiBold;')
        plus_label.setStyleSheet('color: white; font-weight: DemiBold;')

        if inverse:
            layout.addWidget(plus_label)
            layout.addWidget(slider)
            layout.addWidget(minus_label)
            
        else:
            layout.addWidget(minus_label)
            layout.addWidget(slider)
            layout.addWidget(plus_label)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    #---- Button handling ----
    # Next image
    def next_image(self):
        if self.slice != self.current_image.max_slice:
            self.slice+=1
            self.current_image.next_image()
            self.vtkWidget.GetRenderWindow().Render()
            # Update interactor style
            self.slice_number.setText(str(self.slice))
            self.interactorStyle.image_width = self.current_image.width
            self.interactorStyle.image_height = self.current_image.height
    #Previous image
    def prev_image(self):
        if self.slice != 1:
            self.slice-=1
            self.current_image.prev_image()  
            self.vtkWidget.GetRenderWindow().Render()
            self.slice_number.setText(str(self.slice))
            # Update interactor style
            self.interactorStyle.image_width = self.current_image.width
            self.interactorStyle.image_height = self.current_image.height
    
    # Clear all Landmarks call     
    def clear_Landmarks(self):
        # DICOMImage function to clear all the landmarks
        completed = self.current_image.clear_landmarks()
        self.reset_help_images()
        self.reset_landmark_box()
        self.point_counter_label.setText(f"Points: {self.landmark_count} - MAX: {self.max_count}")
        self.signalHandler.clearLandmarks.emit()
        if completed == 1:
            with open(status_file, 'r') as f:
                status_dict = json.load(f)
            # Update the status for the current sequence
            status_dict[self.current_sequence_path] = 0
            self.updateStatusTree(0)
            # Save the updated status dictionary
            with open(status_file, 'w') as f:
                json.dump(status_dict, f, indent=4)
            
     
    # Save landmarks call    
    def save_Landmarks(self):
        # Clean the coordinates box
        msgBox = QMessageBox()
        print(f'-> Save landmarks button pressed with {self.landmark_count} landmarks')
        if self.landmark_count == self.max_count:
            # status de current_image to 1
            self.current_image.save_landmarks()
            # Load the status dictionary
            with open(status_file, 'r') as f:
                status_dict = json.load(f)
            # Update the status for the current sequence
            status_dict[self.current_sequence_path] = 1
            self.updateStatusTree(1)
            # Save the updated status dictionary
            with open(status_file, 'w') as f:
                json.dump(status_dict, f, indent=4)
            msgBox.setWindowTitle("Success!") 
            msgBox.setText("Landmarks succesfully saved.")
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setStyleSheet("QLabel{ color: white; font-size: 11px;} QPushButton{ width:30px; font-size: 11px; } QMessageBox{ background-color: #4b4b4b; }")
            msgBox.exec()
        else:
            
            msgBox.setWindowTitle("Incomplete Landmarks")
            msgBox.setText(f"Please mark all the {self.max_count} landmarks before saving.")
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setStyleSheet("QLabel{ color: white; font-size: 11px;} QPushButton{ width:30px; font-size: 11px; } QMessageBox{ background-color: #4b4b4b; }")
            msgBox.exec()
    
    # Reset the view of the camera 
    def reset_view(self):
        self.interactorStyle.reset_camera()     
        
          
    def remove_current_sequence(self):
        # Confirm the user wants to delete
        confirmation = QMessageBox()
        confirmation.setIcon(QMessageBox.Question)
        confirmation.setWindowTitle('Remove Sequence')
        confirmation.setText("Are you sure you want to remove the current sequence and its possible Landmarks?")
        confirmation.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirmation.setStyleSheet("QLabel{ color: white; font-size: 11px;} QPushButton{ width:30px; font-size: 11px; } QMessageBox{ background-color: #4b4b4b; }")
        ret = confirmation.exec()
        
        if ret == QMessageBox.Yes:
            return 
        else:
            return
        # Check for status on status.json
        # Eliminate the landmarks on coordinate box
        # Update à tree 
        # Qual o próximo joelho a ser displayed?
        
    ''' ----------------------  STATUS OF LANDMARK LABELING ----------------------'''   
    # Finds the first unchecked sequence
    def find_first_unchecked_sequence(self):
        # Load the status dictionary
        with open(status_file, 'r') as f:
            status_dict = json.load(f)
        # Find the first sequence with status 0

        for sequence_path, status in status_dict.items():
            if status == 0:
                return sequence_path          
        return ''
    
    # Get status for a sequence
    def get_status_for_sequence(self,sequence_path):
        # sequence_path = D:/DataOrtho/DATASET_AXIAL/94/RIGHT/pd_tse_fs_tra_12\ exemplo
        with open(status_file, 'r') as f:
                status_dict = json.load(f)
        split_index = sequence_path.find('DATASET_') + len('DATASET_')
        part1 = sequence_path[:split_index]
        part2 = sequence_path[split_index:]
        
        # replace the forward slashes in part2, wow string operation
        part2 = part2.replace('/', '\\')
        sequence_path = part1 + part2
        return status_dict[sequence_path]
    
    # Method that follows the logic explained above, returns the state sequence and the subset (the first 0 sequence) 
    def getCurrentSequence(self):
        src_subsets = [os.path.join(base_dir, d) for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
        current = self.find_first_unchecked_sequence() # finds the first 0 status available: axial -> dynamic -> sagittal
        subset = next((s for s in src_subsets if current.startswith(s)), '')           
        return current,subset
    
    # Update of Individual info on Individual label
    def update_image_path_label(self, current_path):
        components = []
        tail = ''  # Initialize tail as an empty string
        while tail is not None:
            current_path, tail = os.path.split(current_path)
            if tail:
                components.insert(0, tail)
            else:
                tail = None  # Add this line to exit the loop when there's no more path to split
        # check if the first element is 'DataOrtho'
        if components and components[0] == 'DataOrtho':
            components.pop(0)
            #components.pop()   # Remove the last element, if necessary      
        path_string = " - ".join(components)
        self.image_path_label.setText(path_string)
        
    # Update of landmarks marked in the coordinates_box
    def add_landmark_box(self, slice_number, landmark_index, x, y):
        item = f'Landmark {landmark_index} - Slice {slice_number}: ({x},{y})'
        self.coordinates_box.addItem(item)
        self.landmark_count+=1
        
    # Method that undo a marked landmark on the coordinates_box
    def remove_last_landmark_box(self):
        last_item_index = self.coordinates_box.count() - 1
        if last_item_index >= 0:
            item_to_remove = self.coordinates_box.takeItem(last_item_index)
            del item_to_remove  # delete the item or it will linger in memory
        self.landmark_count-=1
    
    # Reset of the coordinates box     
    def reset_landmark_box(self):
        self.coordinates_box.clear()
        self.landmark_count=0          

    ''' ------------------  COMBOBOX AND TREE VIEW HANDLING ------------------'''  
    #Subsets for the combobobox
    def getDirectories(self):
        # Use pathlib to get a list of all directories in the parent directory of the current pathh
        return [str(d) for d in Path(base_dir).iterdir() if d.is_dir()]      

    # Tree View of each dataset, accordingly to the dataset choosen
    # Gives the status for each sequence
    def add_folder_to_model(self, folder_path, parent_item, depth=0):
        folder = QDir(folder_path)
        folder.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs | QDir.Filter.Files)
        
        entry_list = folder.entryList()
        entry_list = [entry for entry in entry_list if QFileInfo(folder.filePath(entry)).isDir()]       
        if depth == 0:
            entry_list = sorted(entry_list, key=lambda x: int(x))
            
        for entry in entry_list:
            child_path = folder.filePath(entry)
            child_info = QFileInfo(child_path)
            if child_info.isDir():
                child_item = QStandardItem(child_info.fileName())
                
                self.add_folder_to_model(child_path, child_item,depth+1)
                if depth == 2:
                    status_item = QStandardItem()
                    status = self.get_status_for_sequence(child_path)
                    status_item.setText(str(status))
                    parent_item.appendRow([child_item, status_item]) 
                else:
                    parent_item.appendRow(child_item)

    # Updates the tree givin the choice made in the combobox
    def update_tree_view(self,index):
        selected_dataset = self.choose_picture_comboboxSource.itemText(index)
        selected_dataset = selected_dataset.replace("\\", "/")
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['Folder', 'Status', 'Landmarks'])
        self.add_folder_to_model(selected_dataset, self.model.invisibleRootItem(), 0)
        self.current_subset_path = selected_dataset
   
        
    # Change status after save_Landmarks   
    def updateStatusTree(self,status):
        sequence_path_components = self.extract_components(self.current_sequence_path)
        if sequence_path_components is None:
            print(f"|Error|-> Failed to extract components from sequence path: {self.current_sequence_path}")
            return
        
        path_parts_in_tree_order = [sequence_path_components["Individual"], sequence_path_components["Knee"], sequence_path_components["Sequence"]]
        parent_item = self.model.invisibleRootItem() #ROOT item
        for part in path_parts_in_tree_order:
        # finding basically the child of parent_item that has the sequence part
            for row in range(parent_item.rowCount()):
                child_item = parent_item.child(row)
                if child_item.text() == part:
                    parent_item = child_item
                    break
        index = self.model.indexFromItem(parent_item)
        status_index = index.sibling(index.row(), 1)
        status_item = self.model.itemFromIndex(status_index)
        if status_item is not None:
            print(f"-> Changed {parent_item.text()} status from {status_item.text()} para {status}")
            status_item.setText(str(status))
        else:
            print(f"No status item found for sequence: {self.current_sequence_path}")
    
    # Load a new Sequence of Images
    def load_new_DICOMImage(self, item_path,status,dataset_type):
        if self.current_image is not None:
            self.current_image.ren.RemoveActor(self.current_image.actor)
        self.current_image = DICOMImage(item_path,self.ren)
        # reset the renderer and add the new image
        self.current_image.ren.RemoveAllViewProps()
        self.current_image.ren.AddActor(self.current_image.actor)
        image_center = self.current_image.get_center()
        # update the camera position to be centered on the new image with the corrected axis
        camera = self.ren.GetActiveCamera()
        camera.SetFocalPoint(image_center)
        camera.SetPosition(image_center[0], image_center[1], -1)  # Assume the camera is placed on the negative Z-axis
        camera.SetViewUp(0, -1, 0)
        self.ren.ResetCamera()
        # Redraw the image
        self.vtkWidget.GetRenderWindow().Render()
        # The camera is now updated with the correspondent correct values
        self.interactorStyle.update_parameters(self.current_image.width,self.current_image.height,self.current_image,0,max_landmarks[dataset_type])
        # if new item_path completed lets load landmarks from Json
        if status == 1:  
            json_path = os.path.join(self.current_image.dicom_dir, f"{self.current_image.sequence}.json")  
            self.current_image.status = 1
            print(f"-> Got json values for: New current path choosen {json_path} |")
            with open(json_path, 'r') as file:
                slice_data_dict = json.load(file)
            landmark_index = 1
            for slice_id, data in slice_data_dict.items():
                slice_index = int(slice_id)
                landmarks = data["Landmarks"]
                for landmark in landmarks:
                    self.current_image.add_landmark([landmark["Position"][0], landmark["Position"][1], slice_index])   
                    self.add_landmark_box(slice_index, landmark_index,  landmark["Position"][0],landmark["Position"][1])
                    landmark_index+=1
            self.landmark_count = max_landmarks[self.current_image.dataset_type]
            self.interactorStyle.landmark_count=max_landmarks[self.current_image.dataset_type]
            self.point_counter_label.setText(f"Points: {self.landmark_count} - MAX: {max_landmarks[self.current_image.dataset_type]}")

        else:
            print(f'|-> Tree clicked: New current path choosen {self.current_sequence_path}|')
            self.coordinates_box.clear()
            # restore and update the point counter
            self.landmark_count = 0
            self.max_count = max_landmarks[self.current_image.dataset_type]
            self.point_counter_label.setText(f"Points: {self.landmark_count} - MAX: {max_landmarks[self.current_image.dataset_type]} ")      
                 
    # choosing the sequence for any individual to display
    def on_sequence_clicked(self,index):
        depth = 0
        parent = index.parent()
        while parent.isValid():
            depth+=1
            parent = parent.parent()
        # Check if the clicked item is at depth == 2
        if depth == 2:
            # clear no matter what
            self.coordinates_box.clear()
            # Path of the clicked item
            item_path = self.get_sequence_path(index)
            self.current_sequence_path = item_path
            with open(status_file, "r") as f:
                status_dict = json.load(f)
            # Dataset type 
            subset = self.get_image_type(self.current_sequence_path)        
            self.current_subset_path = subset
            self.load_new_DICOMImage(item_path,status_dict.get(self.current_sequence_path),subset)  
            # update the image label
            self.update_image_path_label(item_path)
            # load new help images            
            self.load_help_images(subset)
            self.landmark_count = 0
            self.slice = self.current_image.index+1
            self.slice_number.setText(str(self.slice))
            
    # Given an index of the click gives the path of Subset
    def get_sequence_path(self,index):
        sequence_path_parts = []
        while index.isValid():
            sequence_path_parts.insert(0, index.data())
            index = index.parent()
        sequence_path_parts.insert(0,self.current_subset_path)
        #  joins all the parts of the sequence path to form the complete file path
        item_path = os.path.join(base_dir,*sequence_path_parts)
        return item_path  
    

    ''' ------------------  HELP IMAGES AND LANDMARK TEXT VIEWING HANDLING ------------------''' 
    def load_help_images(self,subset):
        # To enable the load help images, the dataset and the knee in current path
        # To check which type of help is need, the current path must be checked for the current dataset
        # clear the help_images before updating
        self.help_images.clear()
        if subset == 'DATASET_AXIAL':
            info = self.extract_components(self.current_sequence_path)
            help_folder = os.path.join(help_path, subset, info['Knee'])
            # ascending sort
            file_paths = sorted(os.listdir(help_folder), key=lambda x: int(x.split('.')[0]))
            for file_path in file_paths:
                if file_path.endswith(".png"):
                    self.help_images.append(os.path.join(help_folder, file_path))
        else:
            help_folder = os.path.join(help_path,subset)
            file_paths = sorted(os.listdir(help_folder), key=lambda x: int(x.split('.')[0]))
            for file_path in file_paths:
                if file_path.endswith(".png"):
                    self.help_images.append(os.path.join(help_folder, file_path))
                    
        # Set the first help image in the image holder
        if len(self.help_images) > 0:
            pixmap = self.load_image(self.help_images[0])
            self.image_holder.setPixmap(pixmap)

    # Basic display of image given an image_path
    def load_image(self, image_path):
        reader = QImageReader(image_path)
        image = reader.read()
        pixmap = QPixmap.fromImage(image)
        max_width = 320
        max_height = 320
        pixmap = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio)
        self.image_holder.setFixedSize(pixmap.width(), pixmap.height())
        return pixmap
    
    # Displays the next image in help_images
    def next_help_image(self,count):
        if count < self.max_count:
            self.help_image_index = count
            pixmap = self.load_image(self.help_images[self.help_image_index])
            self.image_holder.setPixmap(pixmap)
        
    # Display the previous image in help_images
    def prev_help_image(self,count):
        if self.help_image_index > 0:
            self.help_image_index = count - 1
            pixmap = self.load_image(self.help_images[self.help_image_index])
            self.image_holder.setPixmap(pixmap)  
    
    # On the clear coordinates button call      
    def reset_help_images(self):
        self.help_image_index = 0
        pixmap = self.load_image(self.help_images[self.help_image_index])
        self.image_holder.setPixmap(pixmap) 
        
if __name__ == "__main__":
    app = QApplication(sys.argv)  
    mainWindow = LabelingGUIWindow()
    mainWindow.show() 
    sys.exit(app.exec_())  # start the app