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

# --- 3. CONFIGURACIÓN DE LA PÁGINA Y CSS (ESTILO NEÓN AÑADIDO) ---
st.set_page_config(page_title="VAPA Service Desk", layout="wide", page_icon="logo_vapa.png")

def cargar_css_corporativo():
    # He mantenido tu estructura de CSS pero inyectando los colores neón y oscuros solicitados
    st.markdown("""
        <style>
            /* --- PALETA VAPA CYBER-DARK --- */
            :root {
                --vapa-yellow: #FFCC00;
                --vapa-neon: #F0FF42;
                --bg-main: #0E1117;
                --bg-card: #161B22;
                --border-color: #30363d;
            }

            .stApp { background-color: var(--bg-main); color: #E6EDF3; }
            
            /* Sidebar Dark con borde fluorescente */
            [data-testid="stSidebar"] { 
                background-color: #010409 !important; 
                border-right: 2px solid var(--vapa-yellow); 
            }
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] label { 
                color: #FFFFFF !important; 
            }

            /* Botones Neón con Efecto Glow */
            .stButton > button { 
                background-color: transparent !important; 
                color: var(--vapa-yellow) !important; 
                border: 2px solid var(--vapa-yellow) !important;
                font-weight: 800; border-radius: 8px; transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .stButton > button:hover { 
                background-color: var(--vapa-yellow) !important; 
                color: #000000 !important;
                box-shadow: 0 0 20px var(--vapa-yellow);
                transform: translateY(-2px);
            }

            /* Títulos y Headers */
            h1, h2, h3 { 
                color: var(--vapa-yellow) !important; 
                text-shadow: 0 0 10px rgba(255, 204, 0, 0.4); 
                font-weight: 800;
            }
            h1 { border-bottom: 3px solid var(--vapa-yellow); padding-bottom: 10px; }

            /* Inputs y TextAreas */
            .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div {
                background-color: #0d1117 !important;
                color: #c9d1d9 !important;
                border: 1px solid var(--border-color) !important;
            }
            .stTextInput>div>div>input:focus {
                border-color: var(--vapa-neon) !important;
                box-shadow: 0 0 8px var(--vapa-neon) !important;
            }

            /* Tabs Personalizados */
            .stTabs [data-baseweb="tab-list"] { gap: 20px; }
            .stTabs [aria-selected="true"] { 
                color: #000 !important; 
                background-color: var(--vapa-yellow) !important; 
                border-radius: 5px; font-weight: bold; 
            }

            /* Estilo para las alertas e info */
            .stInfo { background-color: rgba(255, 204, 0, 0.1) !important; border-left: 5px solid var(--vapa-yellow) !important; color: #E6EDF3 !important; }
            
            /* Tarjetas de Ticket (Contenedores) */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background-color: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 12px;
            }
        </style>
    """, unsafe_allow_html=True)

# --- 4. GESTIÓN DE SEGURIDAD ---
def hash_pass(password): 
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_pass(password, hashed):
    try:
        # Importante: aseguramos bytes para la comparación
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        print(f"Error al verificar contraseña: {e}")
        return False

def sanitizar_nombre_archivo(nombre):
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', nombre)

# --- 5. GESTIÓN DE BASE DE DATOS (ESTRUCTURA ORIGINAL COMPLETA) ---
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
        
        # Migraciones (Tus ALTER TABLE originales)
        c.execute("PRAGMA table_info(incidencias)")
        columnas_inc = [col[1] for col in c.fetchall()]
        if 'prioridad' not in columnas_inc: c.execute("ALTER TABLE incidencias ADD COLUMN prioridad TEXT DEFAULT 'Media'")
        if 'categoria' not in columnas_inc: c.execute("ALTER TABLE incidencias ADD COLUMN categoria TEXT DEFAULT 'Otros'")
        if 'fecha_limite' not in columnas_inc: c.execute("ALTER TABLE incidencias ADD COLUMN fecha_limite TEXT")
        if 'fecha_resolucion' not in columnas_inc: c.execute("ALTER TABLE incidencias ADD COLUMN fecha_resolucion TEXT")

        c.execute("PRAGMA table_info(usuarios)")
        columnas_usr = [col[1] for col in c.fetchall()]
        if 'debe_cambiar_pass' not in columnas_usr: c.execute("ALTER TABLE usuarios ADD COLUMN debe_cambiar_pass INTEGER DEFAULT 0")

        # Carga de datos iniciales
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

# --- 6. FUNCIONES AUXILIARES (CORREO, EXPORTACIÓN, PDF) ---
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
    else: pdf.set_xy(10, 15)
        
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

# --- 7. VISTA: DETALLE DE INCIDENCIA (FRAGMENTO AÑADIDO PARA CHAT) ---
@st.fragment
def seccion_chat_incidencia(id_inc, autor_reporte, tecnico_asig):
    """Refresca solo el chat sin recargar toda la página"""
    st.subheader("💬 Historial de Comentarios")
    comentarios = run_query("SELECT autor, fecha, comentario FROM comentarios_incidencia WHERE incidencia_id = ? ORDER BY id ASC", (id_inc,))
    
    # Altura fija para el chat
    chat_container = st.container(height=350)
    with chat_container:
        if comentarios:
            for autor, fecha, comentario in comentarios:
                with st.chat_message("user" if autor == autor_reporte else "assistant"):
                    st.write(f"**{autor}** <small>{fecha}</small>", unsafe_allow_html=True)
                    st.write(comentario)
        else:
            st.info("Aún no hay comentarios en este ticket.")

    nuevo_comentario = st.chat_input("Escribe una actualización...")
    if nuevo_comentario:
        fecha_coment = pendulum.now().to_datetime_string()
        autor_actual = st.session_state['username']
        run_query("INSERT INTO comentarios_incidencia (incidencia_id, autor, fecha, comentario) VALUES (?, ?, ?, ?)", 
                  (id_inc, autor_actual, fecha_coment, nuevo_comentario))
        
        # Notificaciones (Lógica original)
        if autor_actual == autor_reporte and tecnico_asig != "Sin Asignar":
            mail_tec = run_query("SELECT email FROM usuarios WHERE username = ?", (tecnico_asig,))
            if mail_tec: disparar_correo_async(mail_tec[0][0], f"Comentario Usuario - Ticket #{id_inc}", f"{autor_actual} dice: {nuevo_comentario}")
        elif autor_actual != autor_reporte:
            mail_usr = run_query("SELECT email FROM usuarios WHERE username = ?", (autor_reporte,))
            if mail_usr: disparar_correo_async(mail_usr[0][0], f"Respuesta Técnica - Ticket #{id_inc}", f"El técnico {autor_actual} ha respondido.")
        st.rerun()

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
        if st.button("⬅️ Volver"):
            st.session_state['incidencia_seleccionada'] = None
            st.rerun()
    with col_btn2:
        try:
            com_pdf = run_query("SELECT autor, fecha, comentario FROM comentarios_incidencia WHERE incidencia_id = ? ORDER BY id ASC", (inc[0],))
            pdf_bytes = generar_pdf(inc, com_pdf)
            st.download_button(label="📄 Descargar PDF", data=pdf_bytes, file_name=f"VAPA_Ticket_{inc[0]}.pdf", mime="application/pdf")
        except Exception as e: st.warning(f"Error PDF: {e}")

    col_info1, col_info2 = st.columns([2, 1])
    with col_info1:
        with st.container(border=True):
            st.subheader(f"{inc[1]}") 
            st.caption(f"Categoría: **{categoria}**")
            st.write("**Descripción:**")
            st.info(inc[2])
            
            st.markdown("#### 📎 Archivos Adjuntos")
            nombre_archivo = inc[7]
            if nombre_archivo and nombre_archivo != "Sin archivo":
                ruta_completa = os.path.join(CARPETA_SUBIDAS, nombre_archivo)
                if os.path.exists(ruta_completa):
                    with open(ruta_completa, "rb") as f:
                        st.download_button(label=f"📥 Descargar {nombre_archivo}", data=f.read(), file_name=nombre_archivo)
                else: st.warning("⚠️ Archivo no encontrado.")
            else: st.text("No hay archivos.")

    with col_info2:
        with st.container(border=True):
            st.markdown("#### 👤 Detalles y SLAs")
            st.write(f"**Usuario:** {inc[3]}")
            st.write(f"**Asignado a:** {inc[4]}")
            
            h_sla = run_query("SELECT horas FROM slas WHERE prioridad = ?", (prioridad,))
            h_permitidas = h_sla[0][0] if h_sla else "N/A"
            
            st.divider()
            st.write(f"**🗓️ Creación:** {inc[6]}")
            st.write(f"**⏳ Límite ({h_permitidas}h):** {fecha_limite if fecha_limite else 'N/A'}")
            
            # --- LÓGICA DE BADGES SLA ---
            estado_sla_badge = "⚪ N/A"
            if fecha_limite:
                try:
                    limite_dt = pendulum.parse(fecha_limite)
                    if inc[5] in ["Validada/Terminada", "Pendiente de validación"]:
                        if fecha_resolucion:
                            resol_dt = pendulum.parse(fecha_resolucion)
                            estado_sla_badge = "🔴 Retrasada" if resol_dt > limite_dt else "🟢 En tiempo"
                        else: estado_sla_badge = "🟢 Resuelta"
                    else:
                        ahora = pendulum.now()
                        if ahora > limite_dt: estado_sla_badge = "🔴 Retrasada"
                        elif (limite_dt - ahora).in_hours() < 24: estado_sla_badge = "🟡 Crítico"
                        else: estado_sla_badge = "🟢 En tiempo"
                except: estado_sla_badge = "Error de fecha"
            
            st.write(f"**📊 SLA:** {estado_sla_badge}")
            color_prio = "red" if prioridad == "Urgente" else "orange" if prioridad == "Alta" else "blue"
            st.markdown(f"**Gravedad:** :{color_prio}[**{prioridad}**]")

    st.divider()
    # Llamamos al fragmento del chat
    seccion_chat_incidencia(inc[0], inc[3], inc[4])

    # Gestión técnica (Solo para Admin/Tecnico asignado)
    puede_editar = (st.session_state['rol'] == 'Administrador') or (st.session_state['rol'] == 'Tecnico' and st.session_state['username'] == inc[4])

    if puede_editar:
        st.divider()
        st.subheader("🛠️ Gestión Técnica y Resolución")
        plantillas = {
            "--- Manual ---": inc[8] if inc[8] else "",
            "🔧 Reinicio": "Se ha procedido a reiniciar el servicio. Funcionamiento restablecido.",
            "🧹 Caché": "Borrado de caché y datos temporales realizado. Portal operativo.",
            "🚀 Escalado N2": "Problema persistente. Se escala a Nivel 2 para revisión de base de datos."
        }
        p_sel = st.selectbox("Plantillas de respuesta:", list(plantillas.keys()))
        
        with st.form("form_gestion"):
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                n_informe = st.text_area("Informe Técnico Final:", value=plantillas[p_sel], height=150)
            with col_g2:
                est_disp = ["Abierta", "En resolución", "Pendiente de validación", "Validada/Terminada"]
                idx_est = est_disp.index(inc[5]) if inc[5] in est_disp else 0
                n_estado = st.selectbox("Estado", est_disp, index=idx_est)
                nueva_prio = st.selectbox("Modificar Gravedad", ["Baja", "Media", "Alta", "Urgente"], index=["Baja", "Media", "Alta", "Urgente"].index(prioridad))

            if st.form_submit_button("💾 Guardar Cambios"):
                n_limite = fecha_limite
                n_resolucion = fecha_resolucion
                
                if n_estado in ["Validada/Terminada", "Pendiente de validación"] and inc[5] not in ["Validada/Terminada", "Pendiente de validación"]:
                    n_resolucion = pendulum.now().to_datetime_string()
                elif n_estado not in ["Validada/Terminada", "Pendiente de validación"]: n_resolucion = None

                if nueva_prio != prioridad:
                    h_sla_n = run_query("SELECT horas FROM slas WHERE prioridad = ?", (nueva_prio,))
                    h_calc = h_sla_n[0][0] if h_sla_n else 72
                    try:
                        f_crea_dt = pendulum.parse(inc[6])
                        n_limite = f_crea_dt.add(hours=h_calc).to_datetime_string()
                    except: pass
                
                run_query("UPDATE incidencias SET informe_tecnico=?, estado=?, prioridad=?, fecha_limite=?, fecha_resolucion=? WHERE id=?", 
                          (n_informe, n_estado, nueva_prio, n_limite, n_resolucion, inc[0]))
                
                if n_estado != inc[5]:
                    m_usr = run_query("SELECT email FROM usuarios WHERE username = ?", (inc[3],))
                    if m_usr: disparar_correo_async(m_usr[0][0], f"Estado Ticket #{inc[0]}", f"Estado actualizado a: {n_estado}")
                
                st.success("Ticket actualizado.")
                st.rerun()

# --- 10. INTERFAZ PRINCIPAL ---
def main():
    cargar_css_corporativo()

    # Inicialización de estado (Original)
    v_defecto = {'logged_in': False, 'username': None, 'rol': None, 'incidencia_seleccionada': None, 'pagina_actual': 'resumen', 'debe_cambiar_pass': 0}
    for k, v in v_defecto.items():
        if k not in st.session_state: st.session_state[k] = v

    init_db()
    
    with st.sidebar:
        if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, use_container_width=True)
        else: st.markdown("<h1 style='color: #FFCC00;'>VAPA</h1>", unsafe_allow_html=True)
        
        st.divider()
        if not st.session_state['logged_in']:
            st.subheader("Login")
            u_input = st.text_input("Usuario")
            p_input = st.text_input("Contraseña", type='password')
            if st.button("Entrar"):
                d_login = login(u_input, p_input)
                if d_login[0]:
                    st.session_state.update({'logged_in': True, 'username': u_input, 'rol': d_login[0], 'debe_cambiar_pass': d_login[1], 'pagina_actual': 'resumen'})
                    st.rerun()
                else: st.error("Acceso denegado")
        else:
            st.write(f"Usuario: **{st.session_state['username']}**")
            st.caption(f"Acceso: {st.session_state['rol']}")
            
            if st.session_state['debe_cambiar_pass'] == 0:
                if st.button("📊 Resumen", use_container_width=True):
                    st.session_state.update({'pagina_actual': 'resumen', 'incidencia_seleccionada': None})
                    st.rerun()
                if st.button("⚙️ Administración", use_container_width=True):
                    st.session_state.update({'pagina_actual': 'administracion', 'incidencia_seleccionada': None})
                    st.rerun()
                
                st.divider()
                st.subheader("🔍 Buscar")
                b_id = st.number_input("ID Ticket", min_value=1, step=1, value=None)
                if st.button("Ir al Ticket"):
                    if b_id:
                        if run_query("SELECT id FROM incidencias WHERE id=?", (b_id,)):
                            st.session_state.update({'incidencia_seleccionada': b_id, 'pagina_actual': 'resumen'})
                            st.rerun()
                        else: st.error("No existe")

            st.divider()
            if st.button("Cerrar Sesión", use_container_width=True):
                st.session_state.update(v_defecto)
                st.rerun()

    if st.session_state['logged_in']:
        if st.session_state['debe_cambiar_pass'] == 1:
            st.title("🔒 Cambio de Contraseña")
            with st.form("f_pass"):
                p1 = st.text_input("Nueva pass", type="password")
                p2 = st.text_input("Repetir pass", type="password")
                if st.form_submit_button("Actualizar"):
                    if p1 and p1 == p2:
                        run_query("UPDATE usuarios SET password=?, debe_cambiar_pass=0 WHERE username=?", (hash_pass(p1), st.session_state['username']))
                        st.session_state['debe_cambiar_pass'] = 0
                        st.success("Actualizada!")
                        st.rerun()
                    else: st.error("No coinciden")

        elif st.session_state['pagina_actual'] == 'administracion':
            st.title("⚙️ Administración")
            if st.session_state['rol'] == 'Administrador':
                st.subheader("Copia de Seguridad")
                if os.path.exists(DB_PATH):
                    with open(DB_PATH, "rb") as db_f:
                        st.download_button("📥 Descargar DB", db_f, f"vapa_{pendulum.now().format('YYYYMMDD')}.db")
                
                st.divider()
                st.subheader("Gestión de Usuarios")
                u_bd = run_query("SELECT username, rol, estado, email FROM usuarios")
                df_u = pd.DataFrame(u_bd, columns=["Usuario", "Rol", "Estado", "Email"])
                df_u["Reset Pass"] = False
                e_df = st.data_editor(df_u, num_rows="dynamic", use_container_width=True)
                if st.button("Guardar Usuarios"):
                    for _, r in e_df.iterrows():
                        u, rl, es, em, res = r['Usuario'], r['Rol'], r['Estado'], r['Email'], r['Reset Pass']
                        if run_query("SELECT username FROM usuarios WHERE username=?", (u,)):
                            run_query("UPDATE usuarios SET rol=?, estado=?, email=? WHERE username=?", (rl, es, em, u))
                            if res: run_query("UPDATE usuarios SET password=?, debe_cambiar_pass=1 WHERE username=?", (hash_pass("1234"), u))
                        else: run_query("INSERT INTO usuarios VALUES (?,?,?,?,?,1)", (u, hash_pass("1234"), rl, es, em))
                    st.success("Base de datos actualizada")

                st.divider()
                st.subheader("Tiempos SLA")
                slas_bd = run_query("SELECT prioridad, horas FROM slas")
                df_slas = pd.DataFrame(slas_bd, columns=["Prioridad", "Horas"])
                e_slas = st.data_editor(df_slas, use_container_width=True)
                if st.button("Guardar SLAs"):
                    for _, r in e_slas.iterrows(): run_query("UPDATE slas SET horas=? WHERE prioridad=?", (int(r['Horas']), r['Prioridad']))
                    st.success("SLA actualizado")
            else: st.error("🔒 Sin permisos")

        elif st.session_state['pagina_actual'] == 'resumen':
            if st.session_state['incidencia_seleccionada']:
                ver_detalle_incidencia(st.session_state['incidencia_seleccionada'])
            else:
                st.title("Panel de Control")
                t_noms = ["📋 Incidencias", "➕ Crear Nueva", "📊 Dashboard", "📖 Conocimiento"]
                tabs = st.tabs(t_noms)
                
                with tabs[0]: # LISTADO
                    q_l = "SELECT id, titulo, prioridad, categoria, usuario_reporte, tecnico_asignado, estado, fecha_limite FROM incidencias"
                    if st.session_state['rol'] == 'Tecnico': q_l += f" WHERE tecnico_asignado='{st.session_state['username']}'"
                    elif st.session_state['rol'] == 'Usuario': q_l += f" WHERE usuario_reporte='{st.session_state['username']}'"
                    
                    incs = run_query(q_l)
                    if incs:
                        df_i = pd.DataFrame(incs, columns=['ID', 'Título', 'Prioridad', 'Categoría', 'Reporta', 'Técnico', 'Estado', 'Fecha Límite'])
                        v_tipo = st.radio("Vista:", ["Tarjetas", "Tabla"], horizontal=True)
                        if v_tipo == "Tarjetas":
                            for i in incs:
                                with st.container():
                                    c_a, c_b, c_c = st.columns([4, 2, 1])
                                    c_a.write(f"**#{i[0]} - {i[1]}**")
                                    c_b.write(f"Estado: `{i[6]}`")
                                    if c_c.button("👁️", key=f"t_{i[0]}"):
                                        st.session_state.incidencia_seleccionada = i[0]
                                        st.rerun()
                        else:
                            st.download_button("📥 Excel", exportar_excel(df_i), "vapa_export.xlsx")
                            gb = GridOptionsBuilder.from_dataframe(df_i)
                            gb.configure_selection('single')
                            grid = AgGrid(df_i, gridOptions=gb.build(), theme='streamlit')
                            sel = grid.get('selected_rows')
                            if sel is not None and len(sel) > 0:
                                sid = sel.iloc[0]['ID'] if isinstance(sel, pd.DataFrame) else sel[0]['ID']
                                if st.button(f"Abrir #{sid}"):
                                    st.session_state.incidencia_seleccionada = int(sid)
                                    st.rerun()
                    else: st.info("Sin incidencias")

                with tabs[1]: # CREAR
                    with st.form("f_inc"):
                        col1, col2 = st.columns(2)
                        with col1:
                            m_id = st.number_input("ID (Manual)", min_value=1)
                            m_tit = st.text_input("Asunto")
                            m_cat = st.selectbox("Categoría", ["Hardware", "Software", "Redes", "Accesos", "Otros"])
                        with col2:
                            m_prio = st.selectbox("Gravedad", ["Baja", "Media", "Alta", "Urgente"], index=1)
                            m_tec = "Sin Asignar" if st.session_state.rol == 'Usuario' else st.selectbox("Técnico", ["Sin Asignar"]+[t[0] for t in run_query("SELECT username FROM usuarios WHERE rol='Tecnico'")])
                            m_file = st.file_uploader("Archivo")
                        m_desc = st.text_area("Descripción")
                        if st.form_submit_button("Registrar Ticket"):
                            if m_tit and m_id:
                                if run_query("SELECT id FROM incidencias WHERE id=?", (m_id,)): st.error("ID duplicado")
                                else:
                                    f_c = pendulum.now()
                                    h_sla_c = run_query("SELECT horas FROM slas WHERE prioridad=?", (m_prio,))
                                    f_l = f_c.add(hours=h_sla_c[0][0] if h_sla_c else 72).to_datetime_string()
                                    n_a = "Sin archivo"
                                    if m_file:
                                        n_a = f_c.format("YYYYMMDD_HHmm_")+sanitizar_nombre_archivo(m_file.name)
                                        with open(os.path.join(CARPETA_SUBIDAS, n_a), "wb") as f: f.write(m_file.getbuffer())
                                    run_query("INSERT INTO incidencias (id, titulo, descripcion, usuario_reporte, tecnico_asignado, estado, fecha, archivo, prioridad, categoria, fecha_limite) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                              (m_id, m_tit, m_desc, st.session_state.username, m_tec, 'Abierta', f_c.to_datetime_string(), n_a, m_prio, m_cat, f_l))
                                    st.success("Registrado!")
                                    st.rerun()

                with tabs[2]: # DASHBOARD
                    d_d = run_query("SELECT estado, categoria, prioridad FROM incidencias")
                    if d_d:
                        df_d = pd.DataFrame(d_d, columns=['Estado', 'Cat', 'Prio'])
                        c_d1, c_d2 = st.columns(2)
                        with c_d1:
                            st.write("### Estados")
                            v_e = df_d['Estado'].value_counts().to_dict()
                            st_echarts({"series": [{"type": "pie", "data": [{"value": v, "name": k} for k, v in v_e.items()]}]})
                        with c_d2:
                            st.write("### Prioridades")
                            v_p = df_d['Prio'].value_counts().to_dict()
                            st_echarts({"xAxis": {"type": "category", "data": list(v_p.keys())}, "yAxis": {"type": "value"}, "series": [{"data": list(v_p.values()), "type": "bar"}]})

                with tabs[3]: # FAQ
                    st.subheader("📖 Base de Conocimiento")
                    with st.expander("🔑 Restablecer Pass"): st.write("Contacta con soporte N1.")
                    with st.expander("🌐 Sin Internet"): st.write("Reinicia el router y tu equipo.")

if __name__ == '__main__':
    main()
