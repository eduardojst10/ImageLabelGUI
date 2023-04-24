from PyQt6 import QtCore
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
from PIL import Image, ImageQt
import pydicom
from pydicom.pixel_data_handlers.util import apply_modality_lut, apply_voi_lut
import json
import os
import sys
from pathlib import Path
from styles import button_style, combo_style,frame_number_style,coordinates_box_style, instructions_style, tree_view_style,scrollbar_css



class ImageBox(QLabel):
    def __init__(self, parent,ds,image_path):
        super(ImageBox, self).__init__(parent)
        self.parent = parent
        self.setFixedSize(512, 512)
        self.setScaledContents(True)
        self.image_path = image_path
        self.load_dicom_image(ds)

    
    def load_dicom_image(self,ds):
        pixel_array = ds.pixel_array

        # Apply the Modality LUT if present
        pixel_array = apply_modality_lut(pixel_array, ds)

        # Apply the VOI LUT if present
        pixel_array = apply_voi_lut(pixel_array, ds)

        # Normalize the pixel array
        pixel_array = ((pixel_array - pixel_array.min()) * (255.0 / (pixel_array.max() - pixel_array.min()))).astype('uint8')

        pil_image = Image.fromarray(pixel_array)
        qt_image = ImageQt.ImageQt(pil_image)
        pixmap = QPixmap.fromImage(qt_image)

        self.setPixmap(pixmap)
    
  
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.pos().x()
            y = event.pos().y()

            self.parent.labels[self.image_path] = (x, y)
            print(self.image_path, ': (', x, ',', y, ')')
        else:
            self.mousePressEventExtreme(event)
      
    # ver se a de cima está bem 
    def mousePressEventExtreme(self, event):
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
    # ---------------------------------------------- Default Vars --------------------------------------
        
        self.base_dir = 'D:/DataOrtho/'

        
        # First Current path is decided by current state 
        self.current_sequence_path, self.current_subset_path = self.getCurrentSequence()    
        # Max number of landmarks too be appointed to each different dataset
        
        self.max_landmarks = {'AXIAL':6,'SAGITTAL':6,'DYNAMIC':6}
        
    # ---------------------------------------------- GUI COMPONENTS --------------------------------------      
        #Individual info
        self.image_path_label = QLabel()
        #self.image_path_label.setText(self.dicom_paths[0])
        self.image_path_label.setStyleSheet(frame_number_style)
        self.image_path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Updating the image_path_label
        self.update_image_path_label(self.current_sequence_path)
        
        
        # To hold multiple Images/Frames
        self.stacked_widget = QStackedWidget(self)
        self.labels = {}
        
        # Box to display marked landmarks
        self.coordinates_box = QPlainTextEdit(self)
        self.coordinates_box.setReadOnly(True)
        self.coordinates_box.setMaximumHeight(150)
        self.coordinates_box.setStyleSheet(coordinates_box_style)
        
        # Box to display instructions
        self.instructions_box = QTextEdit(self)
        self.instructions_box.setReadOnly(True)
        self.instructions_box.setMaximumHeight(150)
        self.instructions_box.setStyleSheet(instructions_style)
        self.instructions_box.setPlainText("frameLabelGUI:\n\n1. 'Next' and 'Previous' or slider buttons to navigate between images.\n2. Click on the image to mark a landmark.\n3. 'Clear Coordinates' button to remove landmarks.\n4. 'Save Coordinates' button to save the marked landmarks.")

        
        # Add a number of Frame to localize in dataset 
        self.frame_number = QLabel()
        self.frame_number.setText("1")
        self.frame_number.setStyleSheet(frame_number_style)
        self.frame_number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Slider to  change the image
        slider_layout = QVBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.valueChanged.connect(self.updateImageSlider)
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.frame_number)

        # self.normal_image_paths debug
        self.normal_image_paths,self.dicom_paths = self.loadImagesFromSequence(self.current_sequence_path)        
       
        # Image paths received from loadImagesFromSequence
        if  self.dicom_paths:
            for image_path in self.dicom_paths:
                ds = pydicom.dcmread(image_path)
                image = ImageBox(self,ds,image_path)
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
        combined_css = tree_view_style + scrollbar_css
        self.tree_view.setStyleSheet(combined_css)

        
        self.tree_view.clicked.connect(self.on_sequence_clicked)
        self.model.setHorizontalHeaderLabels(['Folder','Status','Landmarks'])
        self.add_folder_to_model(self.current_subset_path, self.model.invisibleRootItem(),0)
        choose_data_layout.addWidget(self.tree_view)
    

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
        image_layout.addWidget(self.image_path_label)
        
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

# ---------------------------------------------- BUTTONS AND SLIDER HANDLING --------------------------------------

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
            print(f"Item path: {item_path}")
            # Update the display
            self.updateImageBox(item_path)

            item_path = os.path.relpath(item_path, self.base_dir)
            print('New path choosen', item_path)
            self.update_image_path_label(item_path)
            
            
    # Given an index of the click
    def get_sequence_path(self,index):
        sequence_path_parts = []
        while index.isValid():
            sequence_path_parts.insert(0, index.data())
            index = index.parent()
        # sequence_path_parts.insert(0,self.current_subset_path)
        sequence_path_parts.insert(0,self.current_subset_path)
        item_path = os.path.join(*sequence_path_parts)
        return item_path
    
    # ----------------------------- STATUS OF LABELING ---------------------------------------
    
    
    # TODO: de forma a obter o última sequence à qual foi feita o labeling, segundo a lógica vou realizando 
    # as sequencias dentro do primeiro dataset, à medida que as sequências ficam feitas (o número correto e mínimo de landmarks é marcado) o status da
    # respetiva sequência fica marcado a 1 (significando que está concluido). O método getCurrentSequence vai buscar a última sequência incompleta, i.e com o
    # status a 0.
    
    # Vai começar a procurar sempre no self.base_dir
    
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
                if "dataset" in data and "individual" in data and "knee" in data and "sequence" in data and "frame" in data and "landmarks" in data and "coordinates" in data:
                    done=1
    
        return done 
    
    def find_unchecked_sequence(self, sequence_folders):
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
                        current = self.find_unchecked_sequence(sequence_folders) #
                        if current:
                            return current,subset
                        
                        
        return '',''
    
    # Update of Individual info
    def update_image_path_label(self, current_path):
        components = []
        tail = ''  # Initialize tail as an empty string
        while tail is not None:
            current_path, tail = os.path.split(current_path)
            if tail:
                components.insert(0, tail)
            else:
                tail = None  # Add this line to exit the loop when there's no more path to split

        path_string = " - ".join(components)
        self.image_path_label.setText(path_string)


    
        
# ---------------------------------------------- IMAGE HANDLING --------------------------------------
    
    # Given a path it loads images from a folder
    def loadImagesFromSequence(self,sequence_path):
        # Use QDir to get a list of image file names in the folder
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
    
    
    def updateImageBox(self,sequence_path):
        # Removing the current widgets
        while self.stacked_widget.count() > 0:
            self.stacked_widget.removeWidget(self.stacked_widget.currentWidget())
        
        # Load images from the sequence path
        normal_images, dicom_images = self.loadImagesFromSequence(sequence_path)
        
        # Add images to the stacked_widget
        if dicom_images:
            for image_path in dicom_images:
                ds = pydicom.dcmread(image_path)
                image = ImageBox(self,ds,image_path)
                self.stacked_widget.addWidget(image)
            
        else:
            for image_path in normal_images:
                ds = mpimg.imread(image_path)
                canvas = ImageBox(self,image_path)
                canvas.axes.imshow(ds, cmap='gray')
                self.stacked_widget.addWidget(canvas)
                self.stacked_widget.setCurrentIndex(0) 
    
# ---------------------------------------------- TODO: LANDMARK HANDLING --------------------------------------
    #  Escolher o número de Landmarks
    #       Ideia: Right click, left click remove
    #       Definir um Max? 
    # Guardar em json e nos excels   
    
        # Method clearCoordinates
    def clearCoordinates(self):
        current_widget = self.stacked_widget.currentWidget()

        if current_widget in self.labels.keys():
            pixmap = self.labels[current_widget]
            current_widget.setPixmap(pixmap)
            
    def save_coordinates(self):
        return 


if __name__ == "__main__":
    app = QApplication([])
    main_window = MainWindow()
    main_window.show()
    app.exec()