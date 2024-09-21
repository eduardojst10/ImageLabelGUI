import os
from dotenv import load_dotenv

# load .env file 
load_dotenv()

# environment variables 
BASE_DIR = os.getenv('BASE_DIR', '/default/path')
STATUS_FILE = os.getenv('STATUS_FILE', '/default/status.json')
HELP_PATH = os.getenv('HELP_PATH', '/default/help/path')

EXCEL_PATHS = {
    'DATASET_AXIAL': os.getenv('DATASET_AXIAL', '/default/path/dataset_axial.xlsx'),
    'DATASET_SAGITTAL': os.getenv('DATASET_SAGITTAL', '/default/path/dataset_sagittal.xlsx'),
    'DATASET_DYNAMIC': os.getenv('DATASET_DYNAMIC', '/default/path/dataset_dynamic.xlsx')
}