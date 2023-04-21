from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import (
    QMainWindow, QApplication,QLabel,QComboBox, QPlainTextEdit,QFrame,
    QStackedWidget,QPushButton,QWidget, QSlider,QHBoxLayout,QVBoxLayout,QTextEdit,
    QTreeView, QAbstractItemView
)
from PyQt6.QtGui import QPixmap, QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, QDir,QFileInfo, QSize, QStandardPaths

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
plt.rcParams.update({'figure.max_open_warning': 60})
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt5.QtGui import QImage, QPixmap, QPainter
import pydicom
import numpy as np
import pandas as pd
import json
import math
import sys
import os
from pathlib import Path



class ImageBox(FigureCanvasQTAgg):
    def __init__(self, parent, image_path, width=5, height=4, dpi=120, aspect_ratio=1.0):
        self.parent = parent
        self.image_path = image_path
        adjusted_heigth = width/aspect_ratio
        self.fig = Figure(figsize=(width, adjusted_heigth), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(ImageBox, self).__init__(self.fig)

        ds = pydicom.dcmread(image_path)
        im = self.axes.imshow(ds.pixel_array, cmap='gray')

        # Calculate the scaling factor and the offset
        ax_width = self.axes.get_window_extent().width
        ax_height = self.axes.get_window_extent().height
        img_width = im.get_size()[0]
        img_height = im.get_size()[1]

        self.scale_x = img_width / ax_width
        self.scale_y = img_height / ax_height

        self.offset_x = (ax_width - img_width / self.scale_x) / 2
        self.offset_y = (ax_height - img_height / self.scale_y) / 2       
        
    def mousePressEvent(self, event):
        current_widget = self.parent.stacked_widget.currentIndex()
        current_widget_obj = self.parent.stacked_widget.widget(current_widget)
        # Get the mouse click position relative to the current image widget
        x = event.pos().x() - current_widget_obj.pos().x()
        y = event.pos().y() - current_widget_obj.pos().y()

        # Transform the coordinates to the image space
        x_img = (x - self.offset_x) * self.scale_x
        y_img = (y - self.offset_y) * self.scale_y

        image_path = self.image_path
        self.parent.labels[image_path] = (x_img, y_img)
        print(self.image_path,': (',x,',',y,')')
        
# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        # Name Window
        self.setWindowTitle("frameLabelGUI")
        # Background color
        self.setStyleSheet('background-color:#37516b;')
        
        
        # C:\Users\USER\Desktop\test
        self.base_dir = 'D:/DataOrtho/'
        self.root_path = 'D:/DataOrtho/DATASET_AXIAL_ANONYMOUS'
        self.current_path = 'D:/DataOrtho/DATASET_AXIAL_ANONYMOUS/1/LEFT/pd_tse_fs_tra_320_3'
        # CSS for buttons
        button_style = '''
            QPushButton {
            background-color: rgb(255,255,255); /* White */
            border: none;
            color: black;
            padding: 15px 32px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #2A78AC; /* Dark green */
        }
        '''
        # CSS for ComboBox
        combo_style = '''
            QComboBox {
                background-color: #f7f7f7;
                border: 1px solid #c9c9c9;
                border-radius: 2.5px;
                padding: 1px 18px 1px 3px;
                min-width: 6em;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: darkgray;
                border-left-style: solid;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #d3d3d3, stop:1 #c3c3c3);
            }

            QComboBox::down-arrow {
                image: url(path/to/arrow_down.png);
            }

            QComboBox QAbstractItemView {
                border: 1px solid darkgray;
                selection-background-color: lightgray;
            }
        '''
        # CSS frame box
        frame_number_style = '''
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #FFFFFF; /* White */
                background-color: #121421; /* Dark blue */
                border: 2px solid #FFFFFF; /* White */
                border-radius: 3px;
                text-align: center;
                padding: 5px 10px;
                margin: 10px;
                min-width: 60px;
                min-height: 30px;
            }
        '''
        
        coordinates_box_style = '''
            QPlainTextEdit{
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #999;
                border-radius: 2px;
            }   
        '''
        
        instructions_style = '''
            QTextEdit {
                background-color: #121421;
                color: white;
                border: 1px solid #999;
                border-radius: 2px;
            } 
        '''
        
        self.normal_image_paths,self.dicom_paths = self.loadImagesFromSequence(self.current_path)
        # To hold multiple Images/Frames
        self.stacked_widget = QStackedWidget(self)
        # TODO: Used for obtaining coordinates self.labels
        self.labels = {}
        
        # Box to display marked landmarks
        self.coordinates_box = QPlainTextEdit(self)
        self.coordinates_box.setReadOnly(True)
        self.coordinates_box.setMaximumHeight(150)
        self.coordinates_box.setStyleSheet(coordinates_box_style)
        
        
        self.instructions_box = QTextEdit(self)
        self.instructions_box.setReadOnly(True)
        self.instructions_box.setMaximumHeight(150)
        self.instructions_box.setStyleSheet(instructions_style)
        self.instructions_box.setPlainText("frameLabelGUI:\n\n1. 'Next' and 'Previous' or slider buttons to navigate between images.\n2. Click on the image to mark a landmark.\n3. 'Clear Coordinates' button to remove landmarks.\n4. 'Save Coordinates' button to save the marked landmarks.")

    
        # Image paths received from loadImagesFromSequence
        if  self.dicom_paths:
            for image_path in self.dicom_paths:
                ds = pydicom.dcmread(image_path)
                canvas = ImageBox(self, image_path)
                canvas.axes.imshow(ds.pixel_array, cmap='gray')
                
                self.stacked_widget.addWidget(canvas)
        
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
        
        # Clear Coordinates button
        self.clear_button = QPushButton('Clear Coordinates', self)
        self.clear_button.setStyleSheet(button_style)
        self.clear_button.clicked.connect(self.clearCoordinates)
        
        # Save Coordinates button
        self.save_button = QPushButton('Save Coordinates', self)
        self.save_button.setStyleSheet(button_style)
        # TODO: self.save_button.connect(self.SaveCoordinates) 
        

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
        self.tree_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # setting up the file system model
        self.model = QStandardItemModel()
        self.tree_view.setModel(self.model)
        self.tree_view.clicked.connect(self.on_sequence_clicked)
        self.model.setHorizontalHeaderLabels(['Folder','Status','Landmarks'])
        self.add_folder_to_model(self.root_path, self.model.invisibleRootItem(),0)
        choose_data_layout.addWidget(self.tree_view)
        
        # Add a Frame Number
        self.frame_number = QLabel()
        self.frame_number.setText("1")
        self.frame_number.setStyleSheet(frame_number_style)
        self.frame_number.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
        
        # 'Previous' and 'Next' button 
        btn_changeframe_layout = QHBoxLayout()
        btn_changeframe_layout.addWidget(self.prev_button)
        btn_changeframe_layout.addWidget(self.next_button)
        
        # 'Save' and 'Clear' coordinates
        btnframeState_layout = QHBoxLayout()
        btnframeState_layout.addWidget(self.clear_button)
        btnframeState_layout.addWidget(self.save_button)

   
        # Left layout . Create a layout for the image and the stacked widget and the actual frame represented
        image_layout = QVBoxLayout()
        image_layout.addWidget(self.stacked_widget)
        image_layout.addWidget(self.frame_number)

        # SLIDER to  change the image
        slider_layout = QVBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.valueChanged.connect(self.updateImageSlider)
        slider_layout.addWidget(self.slider)
        
        # LINES
        # a layout for the whole window, with the image on the left and the buttons on the right
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Raised)
        line2.setMidLineWidth(2)
              
        # The Right layout
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(5, 5, 5, 5)

        # Add choose_data_layout, slider_layout, and buttons to the right_layout
        right_layout.addWidget(self.instructions_box)
        right_layout.addLayout(choose_data_layout)
        right_layout.addWidget(line2)
        right_layout.addLayout(btn_changeframe_layout)
        right_layout.addLayout(slider_layout)
        right_layout.addStretch(1)
        
        right_layout.addWidget(self.coordinates_box)
        right_layout.addLayout(btnframeState_layout)
             
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

    # Given a path it loads images from a folder
    def loadImagesFromSequence(self,sequence_path):
        # Use QDir to get a list of image file names in the folder
        print("SEQUENCE PATH",sequence_path)
        mdir = QDir(sequence_path)
        filters = ['*.jpg', '*.jpeg', '*.png','*.dcm']
        mdir.setNameFilters(filters)
        filenames = mdir.entryList()
    
        # Create a list of image paths from the filenames
        paths = [f'{sequence_path}/{filename}' for filename in filenames]
        #print(paths)
        
        # Just for debbuging
        normal_images = []
        dicom_images = []
        
        for path in paths:
            _, ext = os.path.splitext(path)
            if ext.lower() in ['.jpg', '.jpeg', '.png']:
                normal_images.append(path)
            elif ext.lower() == ".dcm":
                dicom_images.append(path)
        return normal_images, dicom_images

    
    # Method clearCoordinates
    def clearCoordinates(self):
        current_widget = self.stacked_widget.currentWidget()

        if current_widget in self.labels.keys():
            pixmap = self.labels[current_widget]
            current_widget.setPixmap(pixmap)
            
    def save_coordinates(self):
        return

    # Method showPrev - button previous
    def showPrev(self):
        # Decrement the current index of the stacked widget
        current_index = self.stacked_widget.currentIndex()
        new_index = current_index - 1 if current_index > 0 else self.stacked_widget.count() - 1
        self.stacked_widget.setCurrentIndex(new_index)
        
        # Update the frame number
        self.frame_number.setText(f"{new_index + 1}")
        
        # Update the slider value
        slider_value = int((new_index / (self.stacked_widget.count()-1))*100)
        self.slider.setValue(slider_value)
        
    # Method showNext - button next
    def showNext(self):
        # Increment the current index of the stacked widget
        current_index = self.stacked_widget.currentIndex()
        new_index = (current_index + 1) % self.stacked_widget.count()
        self.stacked_widget.setCurrentIndex(new_index)
        # Update the slider value
        slider_value = int((new_index / (self.stacked_widget.count()-1))*100)
        self.slider.setValue(slider_value)
               
        # Update the frame number
        self.frame_number.setText(f"{new_index + 1}")
        
    # Method updateImage - slider component
    def updateImageSlider(self, value):
        # Update the image displayed in the stacked widget based on the slider value
        if not self.dicom_paths:
            image_paths = self.normal_image_paths
        else:
            image_paths = self.dicom_paths
        index = int(value * (len(image_paths) - 1) / 100)
        self.stacked_widget.setCurrentIndex(index)
        # Update the frame number
        self.frame_number.setText(f"{index + 1}")
    
    #Datasets for the combobobox
    def getDirectories(self):
        # Use pathlib to get a list of all directories in the parent directory of the current pathh
        return [str(d) for d in Path(self.base_dir).iterdir() if d.is_dir()]
    
    # Tree View of each dataset, accordingly to the dataset choosen
    def add_folder_to_model(self, folder_path, parent_item, depth=0):
        folder = QDir(folder_path)
        folder.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs | QDir.Filter.Files)
        
        entry_list = folder.entryList()       
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
                    status_item.setText(status)
                    parent_item.setChild(child_item.row(),1,status_item)
                    
            #elif child_info.isFile():
             #   child_item = QStandardItem(child_info.fileName())
             #   parent_item.appendRow(child_item)
                
    # Status method that inform of the state of the landmarks annotated in the sequence, the state of the .json 
    def get_status_for_sequence(self,sequence_path):
        total_sequences = 0
        annotated_sequences = 0

        json_path = os.path.join(sequence_path, f"{os.path.basename(sequence_path)}.json")
        #print(json_path)
        if os.path.isfile(json_path):
            total_sequences += 1
            with open(json_path, "r") as json_file:
                data = json.load(json_file)
                if "dataset" in data and "individual" in data and "knee" in data and "sequence" in data and "frame" in data and "landmarks" in data and "coordinates" in data:
                    annotated_sequences += 1
                    total_sequences+=1
                else:
                    total_sequences+=1

        return f"{annotated_sequences}/{total_sequences}"
    
    # Updates the tree givin the choice made in the combobox
    def update_tree_view(self,index):
        selected_dataset = self.choose_picture_comboboxSource.itemText(index)
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['Folder', 'Status', 'Landmarks'])
        self.add_folder_to_model(selected_dataset, self.model.invisibleRootItem(), 0)
    
    # Choosing the sequence for a any individual to display
    def on_sequence_clicked(self,index):
        depth = 0
        parent = index.parent()
        while parent.isValid():
            depth+=1
            parent = parent.parent()
        # Check if the clicked item is at depth == 2
        if depth == 2:
            # print(f"Clicked on item at depth 2: {index.data()}")
            # Path of the clicked item
            item_path = self.get_sequence_path(index)
            print(f"Item path: {item_path}")
            # Update the display
            self.updateImageBox(item_path)
            
    def get_sequence_path(self,index):
        sequence_path_parts = []
        while index.isValid():
            sequence_path_parts.insert(0, index.data())
            index = index.parent()
        sequence_path_parts.insert(0,self.root_path)
        item_path = os.path.join(*sequence_path_parts)
        return item_path
    
    
    # TODO: Escolher o número de Landmarks
    #       Ideia: Right click, left click remove
    #       Definir um Max?       

    def updateImageBox(self,sequence_path):
        while self.stacked_widget.count() > 0:
            self.stacked_widget.removeWidget(self.stacked_widget.currentWidget())

    # Load images from the sequence path
        normal_images, dicom_images = self.loadImagesFromSequence(sequence_path)

        # Add images to the stacked_widget
        if dicom_images:
            for image_path in dicom_images:
                ds = pydicom.dcmread(image_path)
                canvas = ImageBox(self)
                canvas.axes.imshow(ds.pixel_array, cmap='gray')
                self.stacked_widget.addWidget(canvas)
        else:
            for image_path in normal_images:
                ds = mpimg.imread(image_path)
                canvas = ImageBox(self)
                canvas.axes.imshow(ds, cmap='gray')
                self.stacked_widget.addWidget(canvas)
                self.stacked_widget.setCurrentIndex(0)    
                
 
        
app = QApplication([])
w = MainWindow()
w.show()
app.exec()