import streamlit as st
import pandas as pd
import sqlite3
import bcrypt
import pendulum
import yagmail
from fpdf import FPDF
import os
import threading
import io
import re
from dotenv import load_dotenv
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit_echarts import st_echarts

# --- 1. CONFIGURACIÓN DE RUTAS Y ALMACENAMIENTO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_SUBIDAS = os.path.join(BASE_DIR, "archivos_subidos")
LOGO_PATH = os.path.join(BASE_DIR, "logo_vapa.png")
DB_PATH = os.path.join(BASE_DIR, 'gestion_incidencias_v3.db')

if not os.path.exists(CARPETA_SUBIDAS):
    os.makedirs(CARPETA_SUBIDAS)

# --- 2. CONFIGURACIÓN DE CORREO (YAGMAIL + .ENV) ---
load_dotenv(os.path.join(BASE_DIR, ".env"))
EMAIL_EMISOR = os.getenv("EMAIL_EMISOR", "correo_por_defecto@gmail.com") 
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "password_por_defecto") 

# --- 3. CONFIGURACIÓN DE LA PÁGINA Y CSS ---
st.set_page_config(page_title="VAPA Service Desk", layout="wide", page_icon="logo_vapa.png")

def cargar_css_corporativo():
    st.markdown("""
        <style>
            /* --- PALETA VAPA (DOMINANCIA AMARILLA) --- */
            .stApp { background-color: #F9F9F9; color: #1A1A1A; }
            [data-testid="stSidebar"] { background-color: #1A1A1A; border-right: 5px solid #FFCC00; }
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown { color: #FFFFFF !important; }
            [data-testid="stSidebar"] .st-emotion-cache-10trblm { color: #FFCC00 !important; }
            .stButton > button { background-color: #FFCC00 !important; color: #1A1A1A !important; border: 2px solid #FFCC00 !important; font-weight: 800; border-radius: 8px; transition: all 0.2s ease; }
            .stButton > button:hover { background-color: #e6b800 !important; border-color: #e6b800 !important; box-shadow: 0 4px 10px rgba(255, 204, 0, 0.4); transform: translateY(-2px); }
            [data-testid="stSidebar"] .stButton > button { background-color: transparent !important; color: #FFCC00 !important; border: 2px solid #FFCC00 !important; }
            [data-testid="stSidebar"] .stButton > button:hover { background-color: #FFCC00 !important; color: #1A1A1A !important; }
            h1, h2, h3 { color: #1A1A1A !important; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: 800; }
            h1 { border-bottom: 5px solid #FFCC00; padding-bottom: 5px; display: inline-block; }
            .stTabs [data-baseweb="tab-list"] { gap: 20px; }
            .stTabs [aria-selected="true"] { color: #1A1A1A !important; background-color: #FFCC00 !important; border-radius: 5px 5px 0 0; font-weight: bold; padding: 0px 15px; }
            .stTabs [data-baseweb="tab-highlight"] { background-color: #FFCC00 !important; }
            .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus, .stSelectbox>div>div>div[aria-expanded="true"] { border-color: #FFCC00 !important; box-shadow: 0 0 0 2px rgba(255, 204, 0, 0.5) !important; }
            .stAlert[data-baseweb="notification"] { border-left-width: 8px !important; }
            .stInfo { border-left-color: #FFCC00 !important; background-color: rgba(255, 204, 0, 0.1) !important; color: #1A1A1A !important; }
            a { color: #cc9900 !important; font-weight: bold; }
            .stCheckbox > label > div > div { background-color: #FFCC00 !important; border-color: #FFCC00 !important; }
        </style>
    """, unsafe_allow_html=True)

# --- 4. GESTIÓN DE SEGURIDAD ---
def hash_pass(password): 
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_pass(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        print(f"Error al verificar contraseña: {e}")
        return False

def sanitizar_nombre_archivo(nombre):
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', nombre)

# --- 5. GESTIÓN DE BASE DE DATOS ---
@st.cache_resource
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                     (username TEXT PRIMARY KEY, password TEXT, rol TEXT, estado TEXT, email TEXT)''')
                     
        c.execute('''CREATE TABLE IF NOT EXISTS incidencias
                     (id INTEGER PRIMARY KEY, titulo TEXT, descripcion TEXT, 
                     usuario_reporte TEXT, tecnico_asignado TEXT, estado TEXT, fecha TEXT,
                     archivo TEXT, informe_tecnico TEXT)''')
                     
        c.execute('''CREATE TABLE IF NOT EXISTS comentarios_incidencia
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, incidencia_id INTEGER,
                     autor TEXT, fecha TEXT, comentario TEXT)''')
                     
        c.execute('''CREATE TABLE IF NOT EXISTS slas (prioridad TEXT PRIMARY KEY, horas INTEGER)''')
        
        c.execute("PRAGMA table_info(incidencias)")
        columnas_inc = [col[1] for col in c.fetchall()]
        if 'prioridad' not in columnas_inc: 
            c.execute("ALTER TABLE incidencias ADD COLUMN prioridad TEXT DEFAULT 'Media'")
        if 'categoria' not in columnas_inc: 
            c.execute("ALTER TABLE incidencias ADD COLUMN categoria TEXT DEFAULT 'Otros'")
        if 'fecha_limite' not in columnas_inc: 
            c.execute("ALTER TABLE incidencias ADD COLUMN fecha_limite TEXT")
        if 'fecha_resolucion' not in columnas_inc: 
            c.execute("ALTER TABLE incidencias ADD COLUMN fecha_resolucion TEXT")

        c.execute("PRAGMA table_info(usuarios)")
        columnas_usr = [col[1] for col in c.fetchall()]
        if 'debe_cambiar_pass' not in columnas_usr: 
            c.execute("ALTER TABLE usuarios ADD COLUMN debe_cambiar_pass INTEGER DEFAULT 0")

        c.execute('SELECT count(*) FROM usuarios')
        if c.fetchone()[0] == 0:
            usuarios_iniciales = [
                ('admin', hash_pass('admin'), 'Administrador', 'Activo', 'admin@empresa.com', 0),
                ('tec1', hash_pass('tec1'), 'Tecnico', 'Activo', 'tecnico1@ejemplo.com', 0),
                ('tec2', hash_pass('tec2'), 'Tecnico', 'Activo', 'tecnico2@ejemplo.com', 0),
                ('user1', hash_pass('user1'), 'Usuario', 'Activo', 'user1@ejemplo.com', 0)
            ]
            c.executemany("INSERT INTO usuarios VALUES (?, ?, ?, ?, ?, ?)", usuarios_iniciales)
            
        c.execute('SELECT count(*) FROM slas')
        if c.fetchone()[0] == 0:
            slas_iniciales = [('Baja', 120), ('Media', 72), ('Alta', 24), ('Urgente', 4)]
            c.executemany("INSERT INTO slas VALUES (?, ?)", slas_iniciales)

def run_query(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(query, params)
        if query.strip().upper().startswith(("SELECT", "PRAGMA")):
            return c.fetchall()
        else:
            conn.commit()
            return c.lastrowid

# --- 6. FUNCIONES AUXILIARES ---
def enviar_correo_base(destinatario, asunto, cuerpo):
    try:
        yag = yagmail.SMTP(EMAIL_EMISOR, EMAIL_PASSWORD)
        yag.send(to=destinatario, subject=asunto, contents=cuerpo)
    except Exception as e:
        print(f"Aviso - No se pudo enviar el correo: {e}")

def disparar_correo_async(destinatario, asunto, cuerpo):
    if destinatario:
        threading.Thread(target=enviar_correo_base, args=(destinatario, asunto, cuerpo)).start()

def login(username, password):
    result = run_query("SELECT password, rol, debe_cambiar_pass FROM usuarios WHERE username = ?", (username,))
    if result:
        db_hash, rol, debe_cambiar = result[0]
        if check_pass(password, db_hash):
            return (rol, debe_cambiar)
    return (None, None)

def exportar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Incidencias')
    return output.getvalue()

def limpiar_texto(texto):
    if not texto: return "N/A"
    return str(texto)

def generar_pdf(inc, comentarios):
    pdf = FPDF()
    pdf.add_page()
    
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=10, y=8, w=35)
        pdf.set_xy(50, 15)
    else:
        pdf.set_xy(10, 15)
        
    pdf.set_font("Helvetica", style="B", size=22)
    pdf.set_text_color(255, 204, 0)
    pdf.cell(0, 15, text="VAPA Service Desk", new_x="LMARGIN", new_y="NEXT", align='L')
    pdf.set_text_color(26, 26, 26)
    
    pdf.set_y(45)
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, text=limpiar_texto(f"Reporte de Incidencia #{inc[0]}"), new_x="LMARGIN", new_y="NEXT", align='C')
    
    prio = inc[9] if len(inc) > 9 else 'Media'
    cat = inc[10] if len(inc) > 10 else 'Otros'
    limite = inc[11] if len(inc) > 11 and inc[11] else 'Sin límite'
    resol = inc[12] if len(inc) > 12 and inc[12] else 'Pendiente'
    
    pdf.set_font("Helvetica", size=12)
    pdf.ln(5)
    pdf.cell(0, 10, text=limpiar_texto(f"Titulo: {inc[1]}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=limpiar_texto(f"Categoria: {cat} | Prioridad: {prio}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=limpiar_texto(f"Reportado por: {inc[3]} | Asignado a: {inc[4]}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=limpiar_texto(f"Estado: {inc[5]}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=limpiar_texto(f"Fecha Creacion: {inc[6]}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=limpiar_texto(f"Fecha Limite: {limite} | Fecha Resolucion: {resol}"), new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.set_fill_color(255, 204, 0)
    pdf.cell(0, 8, text="  Descripcion:", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 8, text=limpiar_texto(inc[2]))
    
    if inc[8]:
        pdf.ln(5)
        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(0, 8, text="  Informe Tecnico Final:", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 8, text=limpiar_texto(inc[8]))
        
    if comentarios:
        pdf.ln(10)
        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(0, 8, text="  Historial de Comentarios:", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_font("Helvetica", size=10)
        for c_autor, c_fecha, c_texto in comentarios:
            pdf.multi_cell(0, 6, text=limpiar_texto(f"[{c_fecha}] {c_autor}: {c_texto}"))
            
    return bytes(pdf.output())

# --- 7. VISTA: DETALLE DE INCIDENCIA ---
def ver_detalle_incidencia(id_incidencia):
    datos = run_query("SELECT * FROM incidencias WHERE id = ?", (id_incidencia,))
    if not datos:
        st.error("Incidencia no encontrada.")
        st.session_state['incidencia_seleccionada'] = None
        st.rerun()
        return

    inc = datos[0]
    prioridad = inc[9] if len(inc) > 9 else "Media"
    categoria = inc[10] if len(inc) > 10 else "Otros"
    fecha_limite = inc[11] if len(inc) > 11 and inc[11] else None
    fecha_resolucion = inc[12] if len(inc) > 12 and inc[12] else None
    
    st.markdown(f"## 📂 Detalle Incidencia #{inc[0]}")
    
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("⬅️ Volver al Resumen"):
            st.session_state['incidencia_seleccionada'] = None
            st.rerun()
    with col_btn2:
        try:
            comentarios_pdf = run_query("SELECT autor, fecha, comentario FROM comentarios_incidencia WHERE incidencia_id = ? ORDER BY id ASC", (inc[0],))
            pdf_bytes = generar_pdf(inc, comentarios_pdf)
            st.download_button(label="📄 Descargar PDF del Ticket", data=pdf_bytes, file_name=f"VAPA_Ticket_{inc[0]}.pdf", mime="application/pdf")
        except Exception as e:
            st.warning(f"No se pudo generar el PDF: {e}")

    col_info1, col_info2 = st.columns([2, 1])
    
    with col_info1:
        with st.container(border=True):
            st.subheader(f"{inc[1]}") 
            st.caption(f"Categoría: **{categoria}**")
            st.write(f"**Descripción:**")
            st.info(inc[2])
            
            st.markdown("#### 📎 Archivos Adjuntos")
            nombre_archivo = inc[7]
            if nombre_archivo and nombre_archivo != "Sin archivo":
                ruta_completa = os.path.join(CARPETA_SUBIDAS, nombre_archivo)
                if os.path.exists(ruta_completa):
                    with open(ruta_completa, "rb") as f:
                        st.download_button(label=f"📥 Descargar {nombre_archivo}", data=f.read(), file_name=nombre_archivo)
                else:
                    st.warning("⚠️ Archivo no encontrado en disco.")
            else:
                st.text("No hay archivos adjuntos.")

    with col_info2:
        with st.container(border=True):
            st.markdown("#### 👤 Detalles y SLAs")
            st.write(f"**Usuario:** {inc[3]}")
            st.write(f"**Asignado a:** {inc[4]}")
            
            horas_bd = run_query("SELECT horas FROM slas WHERE prioridad = ?", (prioridad,))
            horas_permitidas = horas_bd[0][0] if horas_bd else "N/A"
            
            st.divider()
            st.write(f"**🗓️ Creación:** {inc[6]}")
            st.write(f"**⏳ Límite SLA ({horas_permitidas}h):** {fecha_limite if fecha_limite else 'N/A'}")
            
            if fecha_resolucion:
                st.write(f"**✅ Resolución:** {fecha_resolucion}")
            
            estado_sla_badge = "⚪ N/A"
            if fecha_limite:
                try:
                    limite_dt = pendulum.parse(fecha_limite)
                    if inc[5] in ["Validada/Terminada", "Pendiente de validación"]:
                        if fecha_resolucion:
                            resol_dt = pendulum.parse(fecha_resolucion)
                            estado_sla_badge = "🔴 Retrasada" if resol_dt > limite_dt else "🟢 En tiempo"
                        else: 
                            estado_sla_badge = "🟢 Resuelta"
                    else:
                        ahora = pendulum.now()
                        if ahora > limite_dt: 
                            estado_sla_badge = "🔴 Retrasada"
                        elif (limite_dt - ahora).in_hours() < 24: 
                            estado_sla_badge = "🟡 A punto de expirar"
                        else: 
                            estado_sla_badge = "🟢 En tiempo"
                except Exception:
                    estado_sla_badge = "Error de formato de fecha"
                    
            st.write(f"**📊 Estado SLA:** {estado_sla_badge}")
            st.divider()
            
            color_prio = "red" if prioridad == "Urgente" else "orange" if prioridad == "Alta" else "blue" if prioridad == "Baja" else "green"
            st.markdown(f"**Gravedad:** :{color_prio}[**{prioridad}**]")
            
            color_estado = "red" if inc[5] == "Abierta" else "orange" if inc[5] == "En resolución" else "green"
            st.markdown(f"**Estado:** :{color_estado}[**{inc[5]}**]")

    st.divider()

    st.subheader("💬 Historial de Comentarios")
    comentarios = run_query("SELECT autor, fecha, comentario FROM comentarios_incidencia WHERE incidencia_id = ? ORDER BY id ASC", (inc[0],))
    
    if comentarios:
        for autor, fecha, comentario in comentarios:
            with st.chat_message("user" if autor == inc[3] else "assistant"):
                st.write(f"**{autor}** - {fecha}")
                st.write(comentario)

    nuevo_comentario = st.chat_input("Escribe un comentario...")
    if nuevo_comentario:
        fecha_coment = pendulum.now().to_datetime_string()
        autor_actual = st.session_state['username']
        run_query("INSERT INTO comentarios_incidencia (incidencia_id, autor, fecha, comentario) VALUES (?, ?, ?, ?)", 
                  (inc[0], autor_actual, fecha_coment, nuevo_comentario))
        
        if autor_actual == inc[3] and inc[4] != "Sin Asignar": 
            mail_tec = run_query("SELECT email FROM usuarios WHERE username = ?", (inc[4],))
            if mail_tec: 
                disparar_correo_async(mail_tec[0][0], f"Nuevo comentario - Ticket #{inc[0]}", f"El usuario {autor_actual} ha comentado:\n\n{nuevo_comentario}")
        elif autor_actual != inc[3]: 
            mail_usr = run_query("SELECT email FROM usuarios WHERE username = ?", (inc[3],))
            if mail_usr: 
                disparar_correo_async(mail_usr[0][0], f"Respuesta Técnica - Ticket #{inc[0]}", f"El técnico {autor_actual} ha comentado:\n\n{nuevo_comentario}")
        st.rerun()

    puede_editar = (st.session_state['rol'] == 'Administrador') or \
                   (st.session_state['rol'] == 'Tecnico' and st.session_state['username'] == inc[4])

    if puede_editar:
        st.divider()
        st.subheader("🛠️ Gestión Técnica y Resolución")
        
        plantillas = {
            "--- Escribir manualmente ---": inc[8] if inc[8] else "",
            "🔧 Reinicio de Servicio": "Se ha procedido a reiniciar el servicio/equipo afectado. El funcionamiento se ha restablecido con éxito. Se cierra la incidencia.",
            "🧹 Limpieza de Caché": "Se han borrado los datos de navegación y caché del equipo. El portal vuelve a cargar correctamente.",
            "🚀 Escalado a Nivel 2": "Tras las pruebas iniciales, el problema persiste. Se escala la incidencia al equipo de Soporte Nivel 2 para una revisión más profunda.",
            "✅ Solucionado por el usuario": "El usuario reporta que el problema se ha solucionado por sí mismo. Se procede al cierre del ticket."
        }
        plantilla_sel = st.selectbox("Insertar respuesta rápida (Plantillas):", list(plantillas.keys()))
        
        with st.form("form_gestion"):
            col_gest1, col_gest2 = st.columns(2)
            with col_gest1:
                nuevo_informe = st.text_area("Informe Técnico Final:", value=plantillas[plantilla_sel], height=150)
            with col_gest2:
                estados_disponibles = ["Abierta", "En espera", "En resolución", "Pendiente de validación", "Validada/Terminada"]
                idx_estado = estados_disponibles.index(inc[5]) if inc[5] in estados_disponibles else 0
                nuevo_estado = st.selectbox("Actualizar Estado", estados_disponibles, index=idx_estado)

                prioridades = ["Baja", "Media", "Alta", "Urgente"]
                idx_prio = prioridades.index(prioridad) if prioridad in prioridades else 1
                nueva_prio = st.selectbox("Modificar Gravedad", prioridades, index=idx_prio)

            if st.form_submit_button("💾 Guardar Cambios"):
                nuevo_limite = fecha_limite
                nueva_resolucion = fecha_resolucion
                
                if nuevo_estado in ["Validada/Terminada", "Pendiente de validación"] and inc[5] not in ["Validada/Terminada", "Pendiente de validación"]:
                    nueva_resolucion = pendulum.now().to_datetime_string()
                elif nuevo_estado not in ["Validada/Terminada", "Pendiente de validación"]:
                    nueva_resolucion = None

                if nueva_prio != prioridad:
                    horas_sla = run_query("SELECT horas FROM slas WHERE prioridad = ?", (nueva_prio,))
                    horas_calc = horas_sla[0][0] if horas_sla else 72
                    try:
                        fecha_crea_dt = pendulum.parse(inc[6])
                        nuevo_limite = fecha_crea_dt.add(hours=horas_calc).to_datetime_string()
                    except Exception: 
                        pass
                
                run_query("UPDATE incidencias SET informe_tecnico = ?, estado = ?, prioridad = ?, fecha_limite = ?, fecha_resolucion = ? WHERE id = ?", 
                          (nuevo_informe, nuevo_estado, nueva_prio, nuevo_limite, nueva_resolucion, inc[0]))
                
                if nuevo_estado != inc[5]:
                    mail_usr = run_query("SELECT email FROM usuarios WHERE username = ?", (inc[3],))
                    if mail_usr: 
                        disparar_correo_async(mail_usr[0][0], f"Cambio de estado - Ticket #{inc[0]}", f"Tu ticket ha cambiado de estado a: {nuevo_estado}")
                
                st.success("Actualizado correctamente.")
                st.rerun()
    elif inc[8]:
        st.divider()
        st.subheader("Informe Técnico Final")
        st.info(inc[8])

# --- 8. INTERFAZ PRINCIPAL ---
def main():
    cargar_css_corporativo()

    valores_por_defecto = {
        'logged_in': False, 'username': None, 'rol': None, 
        'incidencia_seleccionada': None, 'pagina_actual': 'resumen', 'debe_cambiar_pass': 0
    }
    for clave, valor in valores_por_defecto.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor

    init_db()
    
    with st.sidebar:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center; color: #FFCC00 !important; font-size: 3em;'>VAPA</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center;'>Service Desk</p>", unsafe_allow_html=True)
        
        st.divider()
        
        if not st.session_state['logged_in']:
            st.subheader("Iniciar Sesión")
            username_input = st.text_input("Usuario", key="login_user")
            password_input = st.text_input("Contraseña", type='password', key="login_pass")
            
            if st.button("Entrar", key="login_btn"):
                datos_login = login(username_input, password_input)
                if datos_login[0]:
                    st.session_state.update({
                        'logged_in': True, 'username': username_input, 
                        'rol': datos_login[0], 'debe_cambiar_pass': datos_login[1], 'pagina_actual': 'resumen'
                    })
                    st.rerun()
                else:
                    st.error("Error credenciales")
        else:
            st.write(f"Hola, **{st.session_state['username']}**")
            st.caption(f"Rol: {st.session_state['rol']}")
            
            if st.session_state['debe_cambiar_pass'] == 0:
                st.divider()
                if st.button("📊 Resumen", use_container_width=True):
                    st.session_state.update({'pagina_actual': 'resumen', 'incidencia_seleccionada': None})
                    st.rerun()
                    
                if st.button("⚙️ Administración", use_container_width=True):
                    st.session_state.update({'pagina_actual': 'administracion', 'incidencia_seleccionada': None})
                    st.rerun()
                
                st.divider()
                st.subheader("🔍 Buscador Rápido")
                buscar_id = st.number_input("ID del Ticket", min_value=1, step=1, value=None)
                if st.button("Ir al Ticket", use_container_width=True):
                    if buscar_id:
                        existe = run_query("SELECT id FROM incidencias WHERE id=?", (buscar_id,))
                        if existe:
                            st.session_state.update({'incidencia_seleccionada': buscar_id, 'pagina_actual': 'resumen'})
                            st.rerun()
                        else:
                            st.error("Ticket no encontrado")
            
            st.divider()
            if st.button("Cerrar Sesión", use_container_width=True):
                st.session_state.update({'logged_in': False, 'username': None, 'rol': None, 'incidencia_seleccionada': None, 'pagina_actual': 'resumen', 'debe_cambiar_pass': 0})
                st.rerun()

    if st.session_state['logged_in']:
        
        if st.session_state['debe_cambiar_pass'] == 1:
            st.title("🔒 Seguridad VAPA: Actualización Obligatoria")
            st.warning("Por políticas de seguridad, debes establecer una nueva contraseña para acceder al portal.")
            with st.form("form_fuerza_pass"):
                nueva_pass_1 = st.text_input("Nueva contraseña", type="password")
                nueva_pass_2 = st.text_input("Confirmar nueva contraseña", type="password")
                if st.form_submit_button("Establecer Contraseña"):
                    if nueva_pass_1 and nueva_pass_1 == nueva_pass_2:
                        run_query("UPDATE usuarios SET password = ?, debe_cambiar_pass = 0 WHERE username = ?", (hash_pass(nueva_pass_1), st.session_state['username']))
                        st.session_state['debe_cambiar_pass'] = 0
                        st.success("✅ Contraseña actualizada.")
                        st.rerun()
                    else:
                        st.error("❌ Las contraseñas no coinciden o están vacías.")
                        
        elif st.session_state['pagina_actual'] == 'administracion':
            st.title("⚙️ Administración del Sistema VAPA")
            if st.session_state['rol'] == 'Administrador':
                
                st.subheader("💾 Copia de Seguridad (Backup)")
                st.info("Descarga una copia completa de todos los tickets, usuarios y configuraciones en formato SQLite.")
                if os.path.exists(DB_PATH):
                    with open(DB_PATH, "rb") as db_file:
                        st.download_button(label="📥 Descargar Base de Datos (.db)", data=db_file, file_name=f"backup_vapa_{pendulum.now().format('YYYYMMDD')}.db", mime="application/octet-stream")
                
                st.divider()
                st.subheader("👥 Gestión de Usuarios")
                usuarios_bd = run_query("SELECT username, rol, estado, email FROM usuarios")
                df_usuarios = pd.DataFrame(usuarios_bd, columns=["Usuario", "Rol", "Estado", "Email"])
                df_usuarios["Restablecer Pass (a 1234)"] = False 
                
                config_columnas = {
                    "Usuario": st.column_config.TextColumn("Usuario (ID)", required=True),
                    "Rol": st.column_config.SelectboxColumn("Rol", options=["Tecnico", "Usuario", "Administrador"], required=True),
                    "Estado": st.column_config.SelectboxColumn("Estado", options=["Activo", "Inactivo", "En Prácticas"], required=True),
                    "Email": st.column_config.TextColumn("Email", required=True),
                    "Restablecer Pass (a 1234)": st.column_config.CheckboxColumn("Restablecer Pass (a 1234)", default=False)
                }
                
                edited_df = st.data_editor(df_usuarios, num_rows="dynamic", column_config=config_columnas, use_container_width=True, hide_index=True)
                if st.button("💾 Guardar Cambios de Usuarios"):
                    for index, row in edited_df.iterrows():
                        usr, rol, est, em, resetear = row['Usuario'], row['Rol'], row['Estado'], row['Email'], row['Restablecer Pass (a 1234)']
                        if pd.isna(usr) or str(usr).strip() == "": continue
                        existe = run_query("SELECT username FROM usuarios WHERE username=?", (usr,))
                        if existe:
                            run_query("UPDATE usuarios SET rol=?, estado=?, email=? WHERE username=?", (rol, est, em, usr))
                            if resetear: run_query("UPDATE usuarios SET password=?, debe_cambiar_pass=1 WHERE username=?", (hash_pass("1234"), usr))
                        else:
                            run_query("INSERT INTO usuarios (username, password, rol, estado, email, debe_cambiar_pass) VALUES (?, ?, ?, ?, ?, 1)", (usr, hash_pass("1234"), rol, est, em))
                    st.success("✅ Base de datos de usuarios actualizada.")
                    st.rerun()

                st.divider()
                st.subheader("⏱️ Configuración de SLAs (Tiempos de Respuesta)")
                slas_bd = run_query("SELECT prioridad, horas FROM slas")
                df_slas = pd.DataFrame(slas_bd, columns=["Gravedad / Prioridad", "Horas Límite para Resolver"])
                
                config_slas = {
                    "Gravedad / Prioridad": st.column_config.TextColumn("Gravedad / Prioridad", disabled=True),
                    "Horas Límite para Resolver": st.column_config.NumberColumn("Horas Límite para Resolver", min_value=1, required=True, step=1, format="%d h")
                }
                edited_slas = st.data_editor(df_slas, column_config=config_slas, use_container_width=True, hide_index=True, key="editor_slas")
                if st.button("⏳ Guardar Configuración de SLA"):
                    for index, row in edited_slas.iterrows():
                        run_query("UPDATE slas SET horas = ? WHERE prioridad = ?", (int(row['Horas Límite para Resolver']), row['Gravedad / Prioridad']))
                    st.success("✅ Configuración de SLAs actualizada.")
                    st.rerun()
            else:
                st.error("🔒 Acceso denegado. Se requieren permisos de Administrador.")

        elif st.session_state['pagina_actual'] == 'resumen':
            if st.session_state['incidencia_seleccionada'] is not None:
                ver_detalle_incidencia(st.session_state['incidencia_seleccionada'])
            else:
                st.title("Panel de Control")
                
                tabs_nombres = ["📋 Listado de Incidencias", "➕ Crear Nueva"]
                if st.session_state['rol'] != 'Usuario': 
                    tabs_nombres.append("📊 Dashboard Analítico")
                tabs_nombres.append("📖 Base de Conocimiento")
                
                tabs = st.tabs(tabs_nombres)
                
                with tabs[0]:
                    if st.session_state['rol'] == 'Administrador': 
                        query_lista = "SELECT id, titulo, prioridad, categoria, usuario_reporte, tecnico_asignado, estado, fecha_limite FROM incidencias"
                        params_lista = ()
                    elif st.session_state['rol'] == 'Tecnico': 
                        query_lista = "SELECT id, titulo, prioridad, categoria, usuario_reporte, tecnico_asignado, estado, fecha_limite FROM incidencias WHERE tecnico_asignado = ?"
                        params_lista = (st.session_state['username'],)
                    else: 
                        query_lista = "SELECT id, titulo, prioridad, categoria, usuario_reporte, tecnico_asignado, estado, fecha_limite FROM incidencias WHERE usuario_reporte = ?"
                        params_lista = (st.session_state['username'],)

                    incidencias = run_query(query_lista, params_lista)
                    if incidencias:
                        df_inc = pd.DataFrame(incidencias, columns=['ID', 'Título', 'Prioridad', 'Categoría', 'Reporta', 'Técnico', 'Estado', 'Fecha Límite'])
                        vista = st.radio("Vista:", ["Tarjetas", "Tabla Avanzada (AgGrid)"], horizontal=True)
                        if vista == "Tarjetas":
                            for inc in incidencias:
                                with st.container(border=True):
                                    col_a, col_b, col_c, col_d = st.columns([1, 4, 2, 2])
                                    col_a.write(f"**#{inc[0]}**")
                                    col_b.write(f"**{inc[1]}**")
                                    col_b.caption(f"Reporta: {inc[4]} | Prio: {inc[2]}")
                                    col_c.write(f"Estado: `{inc[6]}`")
                                    if col_d.button("👁️ Abrir Ticket", key=f"btn_ver_{inc[0]}"):
                                        st.session_state['incidencia_seleccionada'] = inc[0]
                                        st.rerun()
                        else:
                            st.download_button("📥 Exportar a Excel", data=exportar_excel(df_inc), file_name="incidencias_vapa.xlsx")
                            gb = GridOptionsBuilder.from_dataframe(df_inc)
                            gb.configure_selection('single')
                            grid_response = AgGrid(df_inc, gridOptions=gb.build(), theme='streamlit', update_mode='SELECTION_CHANGED')
                            try:
                                selected = grid_response.get('selected_rows')
                                if selected is not None:
                                    if isinstance(selected, pd.DataFrame) and not selected.empty:
                                        if st.button(f"Abrir Incidencia #{selected.iloc[0]['ID']}"): 
                                            st.session_state['incidencia_seleccionada'] = int(selected.iloc[0]['ID'])
                                            st.rerun()
                                    elif isinstance(selected, list) and len(selected) > 0:
                                        id_sel = selected[0]['ID'] if isinstance(selected[0], dict) else selected[0]
                                        if st.button(f"Abrir Incidencia #{id_sel}"): 
                                            st.session_state['incidencia_seleccionada'] = int(id_sel)
                                            st.rerun()
                            except Exception as e: 
                                st.error(f"Error en la tabla: {e}")
                    else: 
                        st.info("No hay incidencias registradas.")

                with tabs[1]:
                    with st.form("form_incidencia"):
                        c1, c2 = st.columns(2)
                        with c1:
                            id_manual = st.number_input("ID del Ticket (Personalizado)", min_value=1, step=1, value=None)
                            titulo = st.text_input("Título")
                            descripcion = st.text_area("Descripción")
                            categoria_sel = st.selectbox("Categoría", ["Hardware", "Software", "Redes e Internet", "Accesos/Contraseñas", "Otros"])
                        with c2:
                            if st.session_state['rol'] == 'Usuario':
                                tecnico_sel = "Sin Asignar"
                                st.info("Un administrador te asignará un técnico en breve.")
                            else:
                                datos_tech = run_query("SELECT username FROM usuarios WHERE rol = 'Tecnico'")
                                tecnico_sel = st.selectbox("Asignar Técnico", ["Sin Asignar"] + [t[0] for t in datos_tech])
                            prioridad_sel = st.selectbox("Gravedad / Prioridad", ["Baja", "Media", "Alta", "Urgente"], index=1)
                            
                            archivo = st.file_uploader("Adjuntar archivo", type=["pdf", "png", "jpg", "jpeg", "docx", "xlsx", "txt"])
                        
                        if st.form_submit_button("Registrar Incidencia"):
                            if titulo and id_manual:
                                existe_id = run_query("SELECT id FROM incidencias WHERE id = ?", (id_manual,))
                                
                                if existe_id:
                                    st.error(f"❌ El ID #{id_manual} ya está en uso. Por favor, elige otro número.")
                                else:
                                    now = pendulum.now()
                                    horas_sla = run_query("SELECT horas FROM slas WHERE prioridad = ?", (prioridad_sel,))
                                    horas_calc = horas_sla[0][0] if horas_sla else 72 
                                    fecha_limite = now.add(hours=horas_calc).to_datetime_string()

                                    nom_arch = "Sin archivo"
                                    if archivo:
                                        nombre_seguro = sanitizar_nombre_archivo(archivo.name)
                                        nom_arch = now.format("YYYYMMDD_HHmmss_") + nombre_seguro
                                        with open(os.path.join(CARPETA_SUBIDAS, nom_arch), "wb") as f: 
                                            f.write(archivo.getbuffer())

                                    fecha_creacion = now.to_datetime_string()
                                    
                                    run_query("""INSERT INTO incidencias (id, titulo, descripcion, usuario_reporte, tecnico_asignado, estado, fecha, archivo, informe_tecnico, prioridad, categoria, fecha_limite) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                                              (id_manual, titulo, descripcion, st.session_state['username'], tecnico_sel, 'Abierta', fecha_creacion, nom_arch, '', prioridad_sel, categoria_sel, fecha_limite))
                                    
                                    if tecnico_sel != "Sin Asignar":
                                        mail_tec = run_query("SELECT email FROM usuarios WHERE username = ?", (tecnico_sel,))
                                        if mail_tec: 
                                            disparar_correo_async(mail_tec[0][0], f"Asignación - Ticket #{id_manual}", f"Nueva incidencia asignada: #{id_manual}\nTítulo: {titulo}\nSLA Límite: {fecha_limite}")
                                    
                                    st.success(f"Ticket #{id_manual} creado correctamente. (Límite: {horas_calc} horas)")
                                    st.rerun()
                            else:
                                st.error("⚠️ Falta el título o el ID del ticket.")

                idx_dash = 2 if st.session_state['rol'] != 'Usuario' else -1
                idx_faq = 3 if st.session_state['rol'] != 'Usuario' else 2

                if idx_dash != -1:
                    with tabs[idx_dash]:
                        st.subheader("📊 Análisis de Incidencias y SLAs VAPA")
                        datos_dash = run_query("SELECT estado, tecnico_asignado, prioridad, categoria, fecha_limite, fecha_resolucion FROM incidencias")
                        if datos_dash:
                            df_dash = pd.DataFrame(datos_dash, columns=['Estado', 'Técnico', 'Prioridad', 'Categoría', 'Limite', 'Resolucion'])
                            
                            def evaluar_sla(row):
                                if not row['Limite']: return "Sin Límite"
                                try:
                                    limite = pendulum.parse(row['Limite'])
                                    if row['Estado'] in ["Validada/Terminada", "Pendiente de validación"]:
                                        if row['Resolucion']:
                                            resolucion = pendulum.parse(row['Resolucion'])
                                            return "Retrasada" if resolucion > limite else "En tiempo"
                                        return "En tiempo" 
                                    else:
                                        ahora = pendulum.now()
                                        return "Retrasada" if ahora > limite else "En tiempo"
                                except Exception: 
                                    return "Desconocido"

                            df_dash['Cumplimiento SLA'] = df_dash.apply(evaluar_sla, axis=1)
                            
                            # --- CÁLCULOS ECHARTS ---
                            # 1. Gauge SLA
                            total_tickets = len(df_dash)
                            en_tiempo = len(df_dash[df_dash['Cumplimiento SLA'] == 'En tiempo'])
                            porcentaje_sla = round((en_tiempo / total_tickets) * 100, 1) if total_tickets > 0 else 0
                            
                            # 2. Embudo Estados
                            estado_counts = df_dash['Estado'].value_counts().to_dict()
                            funnel_data = [{"value": v, "name": k} for k, v in estado_counts.items()]
                            
                            # 3. Tarta Categorías
                            cat_counts = df_dash['Categoría'].value_counts().to_dict()
                            pie_data = [{"value": v, "name": k} for k, v in cat_counts.items()]

                            col_c1, col_c2 = st.columns(2)
                            
                            with col_c1: 
                                st.markdown("##### Cumplimiento Global de SLA")
                                gauge_options = {
                                    "series": [{
                                        "type": 'gauge',
                                        "progress": {"show": True, "width": 18, "itemStyle": {"color": '#FFCC00'}},
                                        "axisLine": {"lineStyle": {"width": 18}},
                                        "detail": {"valueAnimation": True, "formatter": '{value}%'},
                                        "data": [{"value": porcentaje_sla, "name": 'A tiempo'}]
                                    }]
                                }
                                st_echarts(options=gauge_options, height="350px")

                            with col_c2:
                                st.markdown("##### Ciclo de Vida (Estados)")
                                funnel_options = {
                                    "tooltip": {"trigger": 'item', "formatter": '{b} : {c}'},
                                    "series": [{
                                        "type": 'funnel',
                                        "left": '10%', "width": '80%',
                                        "label": {"formatter": '{b} ({c})'},
                                        "itemStyle": {"borderColor": '#fff', "borderWidth": 1},
                                        "data": funnel_data
                                    }]
                                }
                                st_echarts(options=funnel_options, height="350px")
                            
                            st.divider()
                            st.markdown("##### Distribución por Categorías")
                            pie_options = {
                                "tooltip": {"trigger": 'item'},
                                "legend": {"top": '5%', "left": 'center'},
                                "series": [{
                                    "name": 'Categoría',
                                    "type": 'pie',
                                    "radius": ['40%', '70%'],
                                    "avoidLabelOverlap": False,
                                    "itemStyle": {"borderRadius": 10, "borderColor": '#fff', "borderWidth": 2},
                                    "label": {"show": False, "position": 'center'},
                                    "emphasis": {"label": {"show": True, "fontSize": 20, "fontWeight": 'bold'}},
                                    "labelLine": {"show": False},
                                    "data": pie_data
                                }]
                            }
                            st_echarts(options=pie_options, height="400px")

                        else:
                            st.info("No hay suficientes datos para las gráficas.")

                with tabs[idx_faq]:
                    st.subheader("📖 Base de Conocimiento (FAQ)")
                    st.write("Consulta estas guías rápidas antes de abrir una incidencia para resolver tu problema al instante.")
                    
                    with st.expander("🔑 ¿Cómo restablecer mi contraseña de Windows?"):
                        st.write("1. En la pantalla de bloqueo, haz clic en 'Olvidé mi contraseña'.\n2. Sigue las instrucciones enviadas a tu teléfono móvil corporativo.\n3. Si no tienes acceso, abre un ticket en la categoría 'Accesos/Contraseñas'.")
                    with st.expander("🖨️ ¿Cómo conectar la impresora de la oficina?"):
                        st.write("1. Asegúrate de estar conectado a la red VAPA-WIFI.\n2. Ve a Configuración > Impresoras > Añadir nueva.\n3. Escribe la IP: `192.168.1.50` y selecciona el modelo genérico.")
                    with st.expander("🌐 No tengo acceso a Internet, ¿qué hago?"):
                        st.write("1. Revisa que el cable de red esté bien conectado o el Wi-Fi encendido.\n2. Reinicia tu equipo.\n3. Si el problema persiste, abre un ticket con Gravedad 'Alta'.")

    else:
        st.info("👈 Por favor, inicia sesión para continuar en VAPA Service Desk.")

if __name__ == '__main__':
    main()
