import sys
import os

# Añade la ruta de tu proyecto a la variable de entorno PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__))

# Importa la aplicación desde el archivo app.py en la carpeta main
from main.app import app as application
