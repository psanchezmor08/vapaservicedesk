import os
from dotenv import load_dotenv

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
CARPETA_SUBIDAS = os.path.join(BASE_DIR, "archivos_subidos")
LOGO_PATH       = os.path.join(BASE_DIR, "logo_vapa.png")
DB_PATH         = os.path.join(BASE_DIR, 'gestion_incidencias_v3.db')

load_dotenv(os.path.join(BASE_DIR, ".env"))

EMAIL_EMISOR   = os.getenv("EMAIL_EMISOR",   "correo_por_defecto@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "password_por_defecto")

if not os.path.exists(CARPETA_SUBIDAS):
    os.makedirs(CARPETA_SUBIDAS)
