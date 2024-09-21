# styles

# CSS for buttons
button_style = '''
            QPushButton {
            background-color: rgb(255,255,255); /* White */
            border: none;
            color: black;
            padding: 15px 32px;
            text-align: center;
            text-decoration: none;
            font-size: 16px;
            font-weight: DemiBold;
            margin: 4px 2px;
            border-radius: 2px;
        }
        QPushButton:hover {
            background-color: #26488A; 
        }
        '''
        
# CSS for clear and save buttons
buttonState_style = '''
            QPushButton {
                background-color: #26488A; /* Blue */
                border: none;
                color: white;
                padding: 15px 32px;
                text-align: center;
                text-decoration: none;
                font-size: 16px;
                font-weight: DemiBold;
                margin: 4px 2px;
                border-radius: 2px;
            }
        '''
buttonToggle_style = '''
            QPushButton {
                background-color: #26488A; /* Blue */
                color: white;
                text-align: center;
                font-size: 8px;
                font-weight: bold;
                margin: 4px 2px;
                border-radius: 2px;
            }
        '''
# CSS for the toggle button
buttonReset_Style = '''
            QPushButton {
                font-size: 14px;
                font-family: "Helvetica", sans-serif;
                font-weight: bold;
                color: #121421;
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                  stop: 0 #c0c0c0, stop: 1 #a3a3a3); 
                border: none;
                border-radius: 2px;
                text-align: center;
                padding: 5px 10px;
                margin: 5px;
                min-width: 10px;
                min-height: 10px;
            }  
            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                  stop: 0 #0056b3, stop: 1 #003f7f); /* Gradient from vibrant blue to darker blue on hover */
            }
        '''      
# Title Label style 
label_style = 'color: white; font-size: 14px; font-weight: bold;'
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

            QComboBox QAbstractItemView {
                border: 1px solid darkgray;
                selection-background-color: gray;
                color: white ;
            }
        '''
        
# CSS frame box
frame_number_style = '''
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF; /* White */
                background-color: #26488A; /* blue */
                /* border: 1px solid #FFFFFF; /* White */             
                border: thick inset hsl(120, 100%, 50%);
                border-radius: 2px;
                text-align: center;
                padding: 5px 10px;
                margin: 5px;
                min-width: 10px;
                min-height: 10px;
            }
        '''
        
coordinates_box_style = '''
            QListWidget{
                background-color: #f0f0f0;
                color: #333;
                border: 2px solid #666;
                border-radius: 4px;
            }   
        '''
        
# Title style   
title_style = '''
    QLabel {
        font-size: 20px;
        font-weight: bold;
        color: #121421; 
        background-color: #C0C0C0; /* Light gray */
        border: 1px inset #C0C0C0; /* Medium gray */
        border-radius: 2px;
        padding: 5px 10px;
        margin: 5px;
    }
'''  
#Tree view style
tree_view_style = '''
            QTreeView {
                background-color: #FFFFFF;
                alternate-background-color: #F0F0F0;
                border: 1px solid #CCCCCC;
                show-decoration-selected: 1;
            }

            QTreeView::item {
                border: 1px solid #D9D9D9;
                border-top-color: transparent;
                border-bottom-color: transparent;
            }

            QTreeView::item:selected,
            QTreeView::item:selected:active {
                background-color: #6D9EEB;
                color: #FFFFFF;
            }

            QTreeView::item:selected:!active {
                background-color: #E0E0E0;
                color: #000000;
            }

            QTreeView::branch {
                background-color: transparent;
            }

            QTreeView::branch:has-siblings:adjoins-item {
                border-image: url(images/your_branch_line_image.png) 0;
            }

            QTreeView::branch:closed:has-children {
                image: url(images/your_closed_branch_icon.png);
            }

            QTreeView::branch:open:has-children {
                image: url(images/your_open_branch_icon.png);
            }
        '''


scrollbar_css = '''
        QTreeView {
            border: none;
        }

        QScrollBar:horizontal {
            border: none;
            background-color: #E0E0E0;
            height: 15px;
            margin: 0;
        }

        QScrollBar::handle:horizontal {
            background-color: #A0A0A0;
            min-width: 20px;
        }

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            background: none;
            width: 0px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }

        QScrollBar:left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
            background: none;
            width: 0px;
            height: 0px;
        }
'''

message_box_style = '''
    QLabel{ color: white; font-size: 11px;}
    QPushButton{ width:30px; font-size: 11px; }
    QMessageBox{ background-color: #4b4b4b; }
'''

