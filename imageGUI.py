from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QMainWindow, QApplication,QLabel,QComboBox, QPlainTextEdit, QTextEdit,QFrame,
    QStackedWidget,QPushButton,QWidget, QSlider,QHBoxLayout,QVBoxLayout,QTextEdit,
    QTreeView, QAbstractItemView, QMessageBox,  QSizePolicy
)
from PyQt6.QtGui import QPixmap, QStandardItemModel, QStandardItem, QPainter, QPen, QColor, QFont, QImageReader 
from PyQt6.QtCore import Qt, QDir,QFileInfo, QPoint
from PIL import Image, ImageQt
import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut
from skimage.transform import resize
import numpy as np
import json
import pandas as pd
import os
import re
from pathlib import Path
from styles import button_style, combo_style,frame_number_style,coordinates_box_style, title_style, tree_view_style,scrollbar_css


class ImageBox(QLabel):
    # Adicionar um max
    def __init__(self, parent,ds,image_path,max_landmarks):
        super(ImageBox, self).__init__(parent)
        self.parent = parent
        self.max_width = 512
        self.max_height = 512
        self.image_path = image_path
        self.points = []
        self.max_landmarks = max_landmarks
        self.ds = ds
        self.load_dicom_image()
        self.frame_number = self.extract_frame_number(image_path)

    # Load of each time an ImageBox is created
    def load_dicom_image(self):
        pixel_array = self.ds.pixel_array

        # apply Modality LUT if present
        pixel_array = apply_modality_lut(pixel_array, self.ds)

        # apply VOI LUT if present
        pixel_array = apply_voi_lut(pixel_array, self.ds)

        # normalize the pixel array
        pixel_array = ((pixel_array - pixel_array.min()) * (255.0 / (pixel_array.max() - pixel_array.min()))).astype('uint8')

        # TODO:
        # V1 that keeps the original size of the image
        # self.setFixedSize(pixel_array.shape[1], pixel_array.shape[0])
        
        # V2 that adds a maximum size for the imagebox
        #scaled_width = min(pixel_array.shape[1], self.max_width)
        #scaled_height = min(pixel_array.shape[0], self.max_height)
        
        # V3 i can adjust the size to a default size 
        image_height, image_width = pixel_array.shape
        aspect_ratio = float(image_width) / float(image_height)
        
        if image_width > image_height:
            scaled_width = self.max_width
            scaled_height = int(self.max_width / aspect_ratio)
        else:
            scaled_width = int(self.max_height * aspect_ratio)
            scaled_height = self.max_height
        
        
        resized_pixel_array = resize(pixel_array, (scaled_height, scaled_width), preserve_range=True, anti_aliasing=True).astype('uint8')

        # add padding
        # padding to the QLabel's area, ensuring that the landmarks can only be placed within the bounds of the QLabel
        padded_image = np.zeros((self.max_height, self.max_width), dtype='uint8')
        pad_top = (self.max_height - scaled_height) // 2
        pad_left = (self.max_width - scaled_width) // 2
        padded_image[pad_top:pad_top + scaled_height, pad_left:pad_left + scaled_width] = resized_pixel_array

        pil_image = Image.fromarray(padded_image)
        qt_image = ImageQt.ImageQt(pil_image)
        pixmap = QPixmap.fromImage(qt_image)
        
        self.setFixedSize(self.max_width, self.max_height)
        self.setPixmap(pixmap)

        

    # Remove point 
    def remove_point(self,x,y):
        min_distance = float('inf')
        closest_point_index = -1
        
        # finds the closest point, and removes it from the list of points
        for i, point in enumerate(self.points):
            distance = (point[0] - x) ** 2 + (point[1] - y) ** 2
            if distance < min_distance:
                min_distance = distance
                closest_point_index = i

        if closest_point_index >= 0:
            del self.points[closest_point_index]
            self.update()
            # Update the point counter
            # max_landmarks = self.max_landmarks[self.get_image_type(current_path)]
            self.parent.point_counter_label.setText(f"Points: {len(self.points)} - MAX: {self.max_landmarks}")
        print('Removed point in ', self.image_path, ': (', x, ',', y, ')')
    
    # Add point
    def add_point(self, point):
        self.points.append(point)
        self.update()
        # Update the point counter
        self.parent.point_counter_label.setText(f"Points: {len(self.points)} - MAX: {self.max_landmarks}")
    
    
    # Mouse click handling
    def mousePressEvent(self, event):
        x = event.pos().x()
        y = event.pos().y() 
        self.parent.current_sequence = self.image_path
        if event.button() == Qt.MouseButton.LeftButton:

            if len(self.points) < self.max_landmarks:
                self.parent.current_landmarks[self.image_path] = (x, y)
                print('Added point in ', self.image_path, ': (', x, ',', y, ')')
                self.add_point((x, y))
                self.parent.next_help_image()
                # call the update_coordinates_box method
                landmark_index = len(self.points)
                self.parent.update_coordinates_box(self.frame_number, landmark_index, x, y)
            else:
                print(f"Maximum number of landmarks reached! - {self.max_landmarks}")
                self.parent.point_counter_label.setText(f"Maximum number of landmarks reached! - {self.max_landmarks}")
        
        elif event.button() == Qt.MouseButton.RightButton:
            # remove the closest point to the clicked position, if any
            self.remove_point(x, y)
            self.parent.remove_last_coordinates_box_text()
            self.parent.prev_help_image()
     
    # Extracts the frame number of a dicom file from path   
    def extract_frame_number(self, file_path):
        file_name = os.path.basename(file_path)
        match = re.search(r"IM-\d{4}-(\d{4}).dcm", file_name)
        if match:
            return int(match.group(1))
        else:
            return None
    
    # Draw kandmarks marked
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        # set up the pen for drawing points
        # 42, 120, 172       
        painter.setPen(QPen(QColor(228, 228, 52), 1))
        for point in self.points:
            painter.drawPoint(QPoint(point[0], point[1]))

        # set up the pen and font for drawing the circle and index text
        painter.setPen(QPen(Qt.GlobalColor.blue, 2))
        painter.setBrush(Qt.GlobalColor.blue)
        # set the font size
        font = QFont()
        font.setPointSize(6)
        painter.setFont(font)

        for index, point in enumerate(self.points, start=1):
            x, y = point
            radius = 5
            painter.drawEllipse(QPoint(x, y), radius, radius)
            painter.setPen(QPen(Qt.GlobalColor.white, 1))
            painter.drawText(QPoint(x - 2, y + 2), str(index))
            painter.setPen(QPen(Qt.GlobalColor.blue, 1))
            
            
        
# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # name Window
        self.setWindowTitle("FrameLabelGUI")
        # background color
        self.setStyleSheet('background-color:#37516b;') 
        
# ---------------------------------------------- VARS --------------------------------------
       
        self.base_dir = 'D:/DataOrtho/'
        self.base_help = 'D:/DataOrthoHelp/'
        self.excel_paths = {'DATASET_AXIAL': 'D:/DataOrtho/DATASET_AXIAL/dataset_axial.xlsx', 
                            'DATASET_SAGITTAL': 'D:/DataOrtho/DATASET_SAGITTAL/dataset_sagittal.xlsx',
                            'DATASET_DYNAMIC': 'D:/DataOrtho/DATASET_DYNAMIC/dataset_dynamic.xlsx'}
        # First Current path is decided by current state 
        self.current_sequence_path, self.current_subset_path = self.getCurrentSequence()
        # Max number of landmarks too be appointed to each different dataset  
        self.max_landmarks = {'DATASET_AXIAL':11,'DATASET_SAGITTAL':7,'DATASET_DYNAMIC':16}      
        
        #Current help index
        self.help_image_index = 0
        self.help_images = []
        
        # Size Policies for display
        size_policy_expand = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        size_policy_fixed = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        size_policy_minimumexpanded = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        size_policy_maximum = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        
# ---------------------------------------------- GUI COMPONENTS --------------------------------------      
        
        #Individual info, below imagebox
        self.image_path_label = QLabel(self)
        self.image_path_label.setStyleSheet(frame_number_style)
        #self.image_path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_path_label.setSizePolicy(size_policy_fixed)
        # Updating the image_path_label
        self.update_image_path_label(self.current_sequence_path)
        
        # To hold multiple Images/Frames
        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.setSizePolicy(size_policy_expand)
        
        # Dict that holds the landmarks marked and its sequence frames information associated
        self.current_landmarks = {}
        
        # Read-only textbox for displaying coordinates 
        self.coordinates_box = QTextEdit()
        self.coordinates_box.setReadOnly(True)
        self.coordinates_box.setMaximumWidth(300)
        self.coordinates_box.setStyleSheet(coordinates_box_style)

        # Image holder (QLabel)
        self.image_holder = QLabel(self)
        self.image_holder.setSizePolicy(size_policy_maximum)
        self.image_holder.setFixedSize(400, 300)
        self.image_holder.setScaledContents(True)
        self.load_help_images(self.get_image_type(self.current_sequence_path))

        
        # Title display
        self.title_label = QLabel(self)
        self.title_label.setText("FrameLabelGUI")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.title_label.setStyleSheet(title_style)
        
        # Add a number of Frame to localize in dataset 
        self.frame_number = QLabel()
        self.frame_number.setText("1")
        self.frame_number.setStyleSheet(frame_number_style)
        self.frame_number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Slider to  change the image: Currently unavailable
        slider_layout = QVBoxLayout()
        #self.slider = QSlider(Qt.Orientation.Horizontal)
        #self.slider.valueChanged.connect(self.updateImageSlider)
        #slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.frame_number)

        # self.normal_image_paths debug
        self.normal_image_paths,self.dicom_paths = self.loadImagesFromSequence(self.current_sequence_path)        
       
        # Image paths received from loadImagesFromSequence - loadImagesFromSequence used once
        if  self.dicom_paths:
            for image_path in self.dicom_paths:
                ds = pydicom.dcmread(image_path)
                image_type = self.get_image_type(image_path)
                max_landmarks_for_type = self.max_landmarks[image_type]
                image = ImageBox(self,ds,image_path,max_landmarks_for_type)
                self.stacked_widget.addWidget(image)   
                
        else:    
            for image_path in self.normal_image_paths:
                ds = mpimg.imread(image_path)
                canvas = ImageBox(self, image_path)
                canvas.axes.imshow(ds, cmap='gray')
                self.stacked_widget.addWidget(canvas)
                self.stacked_widget.setCurrentIndex(0)

        # Two QPushButton widgets to switch between image frame
        self.prev_button = QPushButton('Previous', self)
        self.next_button = QPushButton('Next', self)
        self.prev_button.setStyleSheet(button_style)
        self.next_button.setStyleSheet(button_style)

        # Connect the buttons to custom slot methods
        self.prev_button.clicked.connect(self.showPrev)
        self.next_button.clicked.connect(self.showNext)

        #  Source of patients data choice combobox Layout
        choose_data_layout = QVBoxLayout()
        choose_data_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        choose_data_layout.setSpacing(5)
        
        # Comboboxes
        source_label = QLabel("Source Directory:")
        source_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        choose_data_layout.addWidget(source_label)
        self.choose_picture_comboboxSource = QComboBox(source_label)
        self.choose_picture_comboboxSource.setStyleSheet(combo_style)
        self.choose_picture_comboboxSource.setFixedHeight(30)
        self.choose_picture_comboboxSource.addItems(self.getDirectories())
        self.choose_picture_comboboxSource.currentIndexChanged.connect(self.update_tree_view)
        choose_data_layout.addWidget(self.choose_picture_comboboxSource)
        
        # Tree View - implementar QTreeView para status de data gathering and so on
        self.tree_view = QTreeView(self)
        self.model = QStandardItemModel()
        self.tree_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree_view.setModel(self.model)
        combined_css = tree_view_style + scrollbar_css
        self.tree_view.setStyleSheet(combined_css)       
        self.tree_view.clicked.connect(self.on_sequence_clicked)
        self.model.setHorizontalHeaderLabels(['Folder','Status','Landmarks'])
        self.add_folder_to_model(self.current_subset_path, self.model.invisibleRootItem(),0)
        choose_data_layout.addWidget(self.tree_view) 
        
        # Clear Coordinates button
        self.clear_button = QPushButton('Clear Coordinates', self)
        self.clear_button.setStyleSheet(button_style)
        self.clear_button.clicked.connect(self.clearLandmarks)
        
        # Save Coordinates button
        self.save_button = QPushButton('Save Coordinates', self)
        self.save_button.setStyleSheet(button_style)
        self.save_button.clicked.connect(self.saveLandmarks) 
        
        
        # Landmark Points Counter
        self.point_counter_label = QLabel()
        self.point_counter_label.setText(f"Points: 0 - MAX: {self.max_landmarks[self.get_image_type(self.current_sequence_path)]}")
        self.point_counter_label.setStyleSheet(frame_number_style)
        self.point_counter_label.setFixedSize(400,80)
        self.point_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        

        #--- Lines ---#
        # line divider of layout for the whole window, with the image on the left and the buttons on the right
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        # line divider of left or right layout
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Raised)
        line2.setMidLineWidth(2)
        
        #--- Layouts ---#   
        
        # Help layout
        help_layout = QHBoxLayout()
        help_layout.addWidget(self.coordinates_box)
        #help_layout.setStretchFactor(self.coordinates_box, 1)
        help_layout.addWidget(self.image_holder)
        #help_layout.setStretchFactor(self.image_holder, 1)
        
        # 'Previous' and 'Next' button Layouts
        btn_changeframe_layout = QHBoxLayout()
        btn_changeframe_layout.addWidget(self.prev_button)
        btn_changeframe_layout.addWidget(self.next_button)
        
        # 'Save' and 'Clear' coordinates Layouts
        btn_frameState_layout = QHBoxLayout()
        btn_frameState_layout.addWidget(self.clear_button)
        btn_frameState_layout.addWidget(self.save_button)
        
        # Layout for the image and the stacked widget and the actual frame represented
        # TODO: Verificar se o display preserva as dimensões da imagebox 
        image_layout = QVBoxLayout()
        image_layout.addWidget(self.stacked_widget,alignment=Qt.AlignmentFlag.AlignCenter)
        image_layout.addStretch(1)
        image_layout.addWidget(self.point_counter_label,alignment=Qt.AlignmentFlag.AlignCenter)
        image_layout.addWidget(self.image_path_label,alignment=Qt.AlignmentFlag.AlignCenter)
        image_layout.setSpacing(3)
            
        # The Right layout - choose_data_layout, slider_layout, and buttons to the right_layout
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.addWidget(self.title_label)
        right_layout.addLayout(choose_data_layout)
        right_layout.addWidget(line2)
        right_layout.addLayout(btn_changeframe_layout)
        right_layout.addLayout(slider_layout)
        right_layout.addStretch(1)
        right_layout.addLayout(help_layout)
        right_layout.addLayout(btn_frameState_layout)
             
        # Main Layout
        main_layout = QHBoxLayout()
        main_layout.addLayout(image_layout)
        main_layout.addWidget(line)
        main_layout.addLayout(right_layout)

        # Widget to hold the Main Layout
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        # Set the widget as the central widget of the MainWindow
        self.setCentralWidget(main_widget)

# ---------------------------------------------- BUTTONS AND SLIDER HANDLING --------------------------------------
    # Method showPrev - button previous
    def showPrev(self):
        # Decrement the current index of the stacked widget
        current_index = self.stacked_widget.currentIndex()
        new_index = current_index - 1 if current_index > 0 else self.stacked_widget.count() - 1
        self.stacked_widget.setCurrentIndex(new_index)
        
        # update the frame number
        self.frame_number.setText(f"{new_index + 1}")
        
        # update the slider value
        #slider_value = int((new_index / (self.stacked_widget.count()-1))*100)
        #self.slider.setValue(slider_value)
        
        # update the image path label and point counter label
        current_widget = self.stacked_widget.currentWidget()
        self.update_image_path_label(current_widget.image_path)
        self.point_counter_label.setText(f"Points: {len(current_widget.points)} - MAX: {self.max_landmarks[self.get_image_type(self.current_sequence_path)]} ")
        
    # Method showNext - button next
    def showNext(self):
        # increment the current index of the stacked widget
        current_index = self.stacked_widget.currentIndex()
        new_index = (current_index + 1) % self.stacked_widget.count()
        self.stacked_widget.setCurrentIndex(new_index)
        
        # update the slider value
        #slider_value = int((new_index / (self.stacked_widget.count()-1))*100)
        #self.slider.setValue(slider_value)
               
        # update the frame number
        self.frame_number.setText(f"{new_index + 1}")
        
        # update the image path label and point counter label
        current_widget = self.stacked_widget.currentWidget()
        self.update_image_path_label(current_widget.image_path)
        self.point_counter_label.setText(f"Points: {len(current_widget.points)} - MAX: {self.max_landmarks[self.get_image_type(self.current_sequence_path)]}")
        
    # Method updateImage - slider component
    def updateImageSlider(self, value):
        # update the image displayed in the stacked widget based on the slider value
        if not self.dicom_paths:
            image_paths = self.normal_image_paths
        else:
            image_paths = self.dicom_paths
        index = int(value * (len(image_paths) - 1) / 100)
        self.stacked_widget.setCurrentIndex(index)
        
        # update the frame number
        self.frame_number.setText(f"{index + 1}") 
        # update the image path label and point counter label
        current_widget = self.stacked_widget.currentWidget()
        self.update_image_path_label(current_widget.image_path)
        self.point_counter_label.setText(f"Points: {len(current_widget.points)} - MAX: {self.max_landmarks[self.get_image_type(self.current_sequence_path)]} ")  
# ---------------------------------------------- COMBOBOX AND TREE VIEW HANDLING --------------------------------------

    #Subsets for the combobobox
    def getDirectories(self):
        # Use pathlib to get a list of all directories in the parent directory of the current pathh
        return [str(d) for d in Path(self.base_dir).iterdir() if d.is_dir()]      

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
                parent_item.appendRow(child_item)
                self.add_folder_to_model(child_path, child_item,depth+1)


                if depth == 2:
                    status_item = QStandardItem()
                    status = self.get_status_for_sequence(child_path)
                    status_item.setText(str(status))
                    parent_item.setChild(child_item.row(),1,status_item)                

    # Updates the tree givin the choice made in the combobox
    def update_tree_view(self,index):
        selected_dataset = self.choose_picture_comboboxSource.itemText(index)
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['Folder', 'Status', 'Landmarks'])
        self.add_folder_to_model(selected_dataset, self.model.invisibleRootItem(), 0)
        self.current_subset_path = selected_dataset
    
    # Choosing the sequence for a any individual to display
    def on_sequence_clicked(self,index):
        depth = 0
        parent = index.parent()
        while parent.isValid():
            depth+=1
            parent = parent.parent()
        # Check if the clicked item is at depth == 2
        if depth == 2:
            # Path of the clicked item
            item_path = self.get_sequence_path(index)
            # Update the display
            self.update_stacked_widget_imagebox(item_path)
            self.current_sequence_path = item_path
            # get new subset
            subset = self.get_image_type(self.current_sequence_path)
            print('Tree clicked: New current path choosen', item_path)
            # update the image label
            self.update_image_path_label(item_path)
            # load new help images            
            self.load_help_images(subset)
            # restore and update the point counter
            self.point_counter_label.setText(f"Points: 0 - MAX: {self.max_landmarks[subset]} ")
            # clear the coordinates_box helper. should i clear the coordinates??
            self.coordinates_box.clear()
            
    # Given an index of the click gives the path of Subset
    def get_sequence_path(self,index):
        sequence_path_parts = []
        while index.isValid():
            sequence_path_parts.insert(0, index.data())
            index = index.parent()
        sequence_path_parts.insert(0,self.current_subset_path)
        #  joins all the parts of the sequence path to form the complete file path
        item_path = os.path.join(*sequence_path_parts)
        return item_path
    
    # ----------------------------- STATUS OF LABELING ---------------------------------------
    
    # TODO: VER CASOS EXTREMOS - De forma a obter o última sequence à qual foi feita o labeling, segundo a lógica vou realizando 
    # as sequencias dentro do primeiro dataset, à medida que as sequências ficam feitas (o número correto e mínimo de landmarks é marcado) o status da
    # respetiva sequência fica marcado a 1 (significando que está concluido). O método getCurrentSequence vai buscar a última sequência incompleta, i.e com o
    # status a 0.

    
    # Get correct order of individual folders given a subset
    def get_individual_folders(self, subset):
        return sorted([os.path.join(subset, d) for d in os.listdir(subset) if os.path.isdir(os.path.join(subset, d))], key=lambda x: int(os.path.basename(x)))

    # Get correct order of sequence folders of Individual Knee 
    def get_sequence_folders(self, knee_folder):
        return [os.path.join(knee_folder, seq) for seq in os.listdir(knee_folder) if os.path.isdir(os.path.join(knee_folder, seq))]
    
    # Status method that inform of the state of the landmarks annotated in the sequence, the state of the .json 
    def get_status_for_sequence(self,sequence_path):
        # sequence_path = D:/DataOrtho/DATASET_AXIAL_ANONYMOUS/94/RIGHT/pd_tse_fs_tra_12\ exemplo
        json_path = os.path.join(sequence_path, f"{os.path.basename(sequence_path)}.json")
        if os.path.isfile(json_path):
            done=0
            with open(json_path, "r") as json_file:
                data = json.load(json_file)
                if "Dataset" in data and "Individual" in data and "Knee" in data and "Sequence" in data and "Frame" in data and "#Landmarks" in data and "Landmarks" in data:
                    done=1
    
        return done 
    
    # Finds the first unchecked sequence
    def find_first_unchecked_sequence(self, sequence_folders):
        for seq in sequence_folders:
            if self.get_status_for_sequence(seq) == 0:
                return seq
        return ''
    
    # Method that follows the logic explained above, returns the state sequence and the subset (the first 0 sequence) 
    def getCurrentSequence(self):
        src_subsets = [os.path.join(self.base_dir, d) for d in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, d))]
        for subset in src_subsets:
            individual_folders = self.get_individual_folders(subset)
            for individual_folder in individual_folders:
                for knee in ['LEFT', 'RIGHT']:
                    knee_folder = os.path.join(individual_folder, knee)
                    if os.path.exists(knee_folder):
                        sequence_folders = self.get_sequence_folders(knee_folder) # gives the sequence folder of the 
                        current = self.find_first_unchecked_sequence(sequence_folders) # finds the first 0 status available: axial -> dynamic -> sagittal
                        if current:
                            return current, subset
                                
        return '',''
    
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
    def update_coordinates_box(self, frame_number, landmark_index, x, y):
        new_formatted_text = f"<b>Frame:</b> {frame_number} | <b>Landmark:</b> {landmark_index} | <b>Coordinates:</b> ({x}, {y})"
        current_text = self.coordinates_box.toHtml()
        updated_text = current_text + "<br>" + new_formatted_text
        self.coordinates_box.setHtml(updated_text)
        
    # Method that undo a marked landmark on the coordinates_box
    # TODO: Testar casos anormais 
    def remove_last_coordinates_box_text(self):
        html_text = self.coordinates_box.toHtml()
        # convert the HTML text to plain text for easier processing
        plain_text = QTextEdit(html_text).toPlainText()
        
        # find the last line index
        last_line_index = plain_text.rfind('\n', 0, plain_text.rfind('\n'))
        new_plain_text = plain_text[:last_line_index] if last_line_index != -1 else ""
        
        # create a new QTextEdit and set the plain text
        new_text_edit = QTextEdit()
        new_text_edit.setPlainText(new_plain_text)
        
        # get the new HTML text and update the coordinates_box
        new_html_text = new_text_edit.toHtml()
        self.coordinates_box.setHtml(new_html_text)
    

        
# ---------------------------------------------- IMAGE HANDLING (IMAGEBOX and HELP)-------------------------------------- 

    # Given a path it loads images from a folder
    def loadImagesFromSequence(self,sequence_path):
        # QDir to get a list of image file names in the folder
        mdir = QDir(sequence_path)
        filters = ['*.jpg', '*.jpeg', '*.png','*.dcm']
        mdir.setNameFilters(filters)
        filenames = mdir.entryList()
       # create a list of image paths from the filenames
        paths = [f'{sequence_path}/{filename}' for filename in filenames]
        
        # just for debbuging
        normal_images = []
        dicom_images = []
        for path in paths:
            _, ext = os.path.splitext(path)
            if ext.lower() in ['.jpg', '.jpeg', '.png']:
                normal_images.append(path)
            elif ext.lower() == ".dcm":
                dicom_images.append(path)
        return normal_images, dicom_images
    
    # Update the stacked widget the the new 
    def update_stacked_widget_imagebox(self,sequence_path):
        # remove the current widgets
        while self.stacked_widget.count() > 0:
            self.stacked_widget.removeWidget(self.stacked_widget.currentWidget())
        
        # load images from the sequence path
        normal_images, dicom_images = self.loadImagesFromSequence(sequence_path)
    
        # add images to the stacked_widget
        if dicom_images:
            for image_path in dicom_images:
                ds = pydicom.dcmread(image_path)
                image_type = self.get_image_type(image_path)
                max_landmarks_for_type = self.max_landmarks[image_type]
                image = ImageBox(self,ds,image_path,max_landmarks_for_type)
                self.stacked_widget.addWidget(image)
            
        else:
            for image_path in normal_images:
                ds = mpimg.imread(image_path)
                canvas = ImageBox(self,image_path)
                canvas.axes.imshow(ds, cmap='gray')
                self.stacked_widget.addWidget(canvas)
                self.stacked_widget.setCurrentIndex(0) 
    
    # ------------------------- HELP IMAGES -------------------------           

    def load_help_images(self,subset):
        # To enable the load help images, the dataset and the knee in current path
        # To check which type of help is need, the current path must be checked for the current dataset
        # clear the help_images before updating
        self.help_images.clear()

        if subset == 'DATASET_AXIAL':
            info = self.extract_components(self.current_sequence_path)
            help_folder = os.path.join(self.base_help, subset, info['Knee'] )
            # ascending sort
            file_paths = sorted(os.listdir(help_folder), key=lambda x: int(x.split('.')[0]))
            for file_path in file_paths:
                if file_path.endswith(".png"):
                    self.help_images.append(os.path.join(help_folder, file_path))
        else:
            help_folder = os.path.join(self.base_help,subset)
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
        return pixmap
    
    # Displays the next image in help_images
    def next_help_image(self):
        self.help_image_index += 1
        if self.help_image_index >= len(self.help_images):
            self.help_image_index = 0
        pixmap = self.load_image(self.help_images[self.help_image_index])
        self.image_holder.setPixmap(pixmap)
        
    # Displays previous
    def prev_help_image(self):
        if self.help_image_index > 0:
            self.help_image_index -= 1
            pixmap = QPixmap(self.help_images[self.help_image_index])
            self.image_holder.setPixmap(pixmap)
    
# ---------------------------------------------- LANDMARK HANDLING --------------------------------------
    #  Escolher o número de Landmarks
    #       Right click add, left Click remove - done
    #       Definir um Max - done
    #       Guardar em json e excels, nos respetivos paths corretos  
    
    # In case of the new image_path 
    def get_relative_path(self, path, start):
        if os.path.splitdrive(path)[0] == os.path.splitdrive(start)[0]:
            return os.path.relpath(path, start)
        else:
            return os.path.abspath(path)
        
    
    # Method that returns the key for max_landmarks, a subset key for a max.
    def get_image_type(self,image_path):
        # path relative to the base directory
        # rel_path = os.path.relpath(image_path, self.base_dir)
        
        rel_path = self.get_relative_path(image_path,self.base_dir)
        
        # split the path into parts
        parts = rel_path.split(os.path.sep)
        # get the the subset of DataOrtho name containing the type
        image_type = parts[0]
        return image_type
    
    # Specific string required - TODO: Mesh with other related function
    # example "A:/DATASET_ALL/DATASET_AXIAL/1/LEFT/pd_tse_fs_tra_320_3/IM-0001-0001.dcm"
    def extract_components(self,image_path):
        # Define the regex pattern
        pattern = r"(?P<Dataset>DATASET_\w+)[\\/](?P<Individual>\d+)[\\/](?P<Knee>LEFT|RIGHT)[\\/](?P<Sequence>[\w-]+)[\\/]*"


        # Find the match using the regex pattern
        match = re.search(pattern, image_path)

        # If there's a match, return the matched groups as a dictionary
        if match:
            return match.groupdict()
        else:
            return None
        
    # Method clearLandmarks
    def clearLandmarks(self):
        current_widget = self.stacked_widget.currentWidget()
        current_widget.points = []
        current_widget.update()
        self.point_counter_label.setText(f"Points: {len(current_widget.points)} - MAX: {self.max_landmarks[self.get_image_type(self.current_sequence_path)]}")
            
    # Method saveLandmarks  - logic implemented    
    def saveLandmarks(self):
        if not self.all_landmarks_marked():
            QMessageBox.warning(self,"Warning", "Mark all landmarks before saving.")
            return
        
        self.update_landmarks_files()
        QMessageBox.information(self, "Success", "Points saved successfully.")
        
    # Check if all max landmarks are marked
    def all_landmarks_marked(self):
        current_image_widget = self.stacked_widget.currentWidget()
        return len(current_image_widget.points) == current_image_widget.max_landmarks
    
    # Update the landmarks marked to the appropriate paths
    def update_landmarks_files(self):
        # get do current path para campos de json
        sequence_folder = self.current_sequence_path
        json_file = os.path.join(sequence_folder, f"{os.path.basename(sequence_folder)}.json")
        print('Sequence:', sequence_folder)
        current_image_widget = self.stacked_widget.currentWidget()
        frame_number = current_image_widget.frame_number
        landmarks = current_image_widget.points
        dataset = self.get_image_type(self.current_sequence_path)
        # Get the full path because
        full_path = current_image_widget.image_path
        info = self.extract_components(full_path)
        individual = info['Individual']
        knee = info['Knee']
        sequence = info['Sequence']
        
        data = {
            "Dataset": dataset,
            "Individual":individual,
            "Knee": knee,
            "Sequence": sequence,
            "Frame": frame_number,
            "#Landmarks": self.max_landmarks[dataset],
            "Landmarks": landmarks
        }
        with open(json_file, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        # Find the correct subset DataFrame
        excel_file_path = self.excel_paths[dataset]
        
        subset_df = pd.read_excel(excel_file_path)
        # checking if the sequence exists in the DataFrame
        sequence_exists = subset_df['Sequence'].isin([sequence]).any()

        if sequence_exists:
            # Update the existing row
            for key, value in data.items():
                if key not in ["image_paths", "landmark_points", "comments", "Landmarks"]:
                    subset_df.loc[subset_df['Sequence'] == sequence, key] = str(value)
            subset_df.loc[subset_df['Sequence'] == sequence, 'Landmarks'] = str(landmarks)
        else:
            # Add the new sequence row with the data
            subset_df = pd.concat([subset_df, pd.DataFrame([data])], ignore_index=True)

        
        # update landmarks
        subset_df.loc[subset_df['Sequence'] == sequence, 'Landmarks'] = str(landmarks)
        with pd.ExcelWriter(excel_file_path) as writer:
            subset_df.to_excel(writer, index=False)
    
if __name__ == "__main__":
    app = QApplication([])
    main_window = MainWindow()
    main_window.showMaximized()
    app.exec()