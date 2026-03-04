@echo off
title VAPA Service Desk - Iniciando...

echo [1/3] Comprobando e instalando dependencias en modo silencioso...
:: El flag -q hace que la instalacion sea silenciosa (quiet)
:: Se han añadido bcrypt, pendulum, yagmail y streamlit-echarts. Se ha retirado plotly.
pip install -q streamlit pandas python-dotenv streamlit-aggrid fpdf2 openpyxl bcrypt pendulum yagmail streamlit-echarts

echo [2/3] Levantando el servidor de VAPA Service Desk...
:: Inicia streamlit en segundo plano y en modo headless (para que no intente abrir el navegador por defecto de Windows)
:: NOTA: Asegúrate de que tu archivo de código fuente se siga llamando 'proyecto.py'
start /B streamlit run proyecto.py --server.headless true > nul 2>&1

:: Esperamos 4 segundos para darle tiempo al servidor local a arrancar correctamente
timeout /t 4 /nobreak > NUL

echo [3/3] Abriendo Google Chrome...
:: Forzamos a que se abra especificamente en Google Chrome
start chrome "http://localhost:8501"

echo ¡Todo listo! Puedes cerrar esta ventana negra.
exit