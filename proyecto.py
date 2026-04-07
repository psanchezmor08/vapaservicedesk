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

# ─────────────────────────────────────────────
# 1. CONFIG
# ─────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
CARPETA_SUBIDAS = os.path.join(BASE_DIR, "archivos_subidos")
LOGO_PATH       = os.path.join(BASE_DIR, "logovapa.png")
DB_PATH         = os.path.join(BASE_DIR, "gestion_incidencias_v3.db")

load_dotenv(os.path.join(BASE_DIR, ".env"))
EMAIL_EMISOR   = os.getenv("EMAIL_EMISOR",   "correo@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "password")

if not os.path.exists(CARPETA_SUBIDAS):
    os.makedirs(CARPETA_SUBIDAS)

st.set_page_config(
    page_title="VAPA Service Desk",
    layout="wide",
    page_icon="logovapa.png",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# 2. CSS  — paleta extraída del logo VAPA
#    Verde lima:   #AADC00
#    Fondo dark:   #0D1021
#    Sidebar:      #0A0C18
#    Card:         #13172B
#    Border:       #1E2340
#    Texto claro:  #E8EAF6
# ─────────────────────────────────────────────
def cargar_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Poppins', sans-serif !important; }

    .stApp {
        background: linear-gradient(135deg, #0D1021 0%, #0A0C18 60%, #060810 100%);
        color: #E8EAF6;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0A0C18 0%, #060810 100%) !important;
        border-right: 1px solid #1E2340 !important;
    }
    [data-testid="stSidebar"] * { color: #E8EAF6 !important; }
    [data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: none !important;
        color: #9CA3AF !important;
        text-align: left !important;
        width: 100% !important;
        padding: 10px 16px !important;
        border-radius: 8px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(170,220,0,0.1) !important;
        color: #AADC00 !important;
        transform: none !important;
        box-shadow: none !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #AADC00, #88B300) !important;
        color: #0D1021 !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 8px 20px !important;
        transition: all 0.2s ease !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
        font-size: 14px !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #BBEE00, #AADC00) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 20px rgba(170,220,0,0.3) !important;
    }

    h1 { color: #AADC00 !important; font-weight: 800 !important; font-size: 1.8rem !important;
         border-bottom: 2px solid rgba(170,220,0,0.3); padding-bottom: 8px; }
    h2 { color: #AADC00 !important; font-weight: 700 !important; font-size: 1.3rem !important; }
    h3 { color: #C8F040 !important; font-weight: 600 !important; font-size: 1.1rem !important; }

    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div,
    .stNumberInput > div > div > input {
        background: #13172B !important;
        color: #E8EAF6 !important;
        border: 1px solid #1E2340 !important;
        border-radius: 8px !important;
        font-family: 'Poppins', sans-serif !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #AADC00 !important;
        box-shadow: 0 0 0 2px rgba(170,220,0,0.2) !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #13172B !important;
        border: 1px solid #1E2340 !important;
        border-radius: 12px !important;
    }

    [data-testid="stMetric"] {
        background: #13172B;
        border: 1px solid #1E2340;
        border-radius: 12px;
        padding: 16px 20px;
    }
    [data-testid="stMetricLabel"] { color: #9CA3AF !important; font-size: 13px !important; }
    [data-testid="stMetricValue"] { color: #AADC00 !important; font-size: 2rem !important; font-weight: 700 !important; }

    .stTabs [data-baseweb="tab-list"] {
        background: #13172B;
        border-radius: 10px;
        gap: 4px;
        padding: 4px;
        border: 1px solid #1E2340;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #9CA3AF !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 13px !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #AADC00, #88B300) !important;
        color: #0D1021 !important;
        font-weight: 700 !important;
    }

    .stInfo    { background: rgba(170,220,0,0.08) !important; border-left: 4px solid #AADC00 !important; border-radius: 8px !important; color: #E8EAF6 !important; }
    .stSuccess { background: rgba(170,220,0,0.12) !important; border-left: 4px solid #AADC00 !important; border-radius: 8px !important; }
    .stError   { background: rgba(255,80,80,0.1)  !important; border-left: 4px solid #FF5050 !important; border-radius: 8px !important; }
    .stWarning { background: rgba(255,180,0,0.1)  !important; border-left: 4px solid #FFB400 !important; border-radius: 8px !important; }

    hr { border-color: #1E2340 !important; }

    .badge-urgente  { background:#FF4040;color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600; }
    .badge-alta     { background:#FF8C00;color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600; }
    .badge-media    { background:#0EA5E9;color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600; }
    .badge-baja     { background:#22C55E;color:#fff;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600; }

    .badge-abierta    { background:#1E3A5F;color:#60A5FA;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #2563EB; }
    .badge-resolucion { background:#3B1F5E;color:#A78BFA;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #7C3AED; }
    .badge-validacion { background:#1A3320;color:#4ADE80;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #16A34A; }
    .badge-terminada  { background:#1E2340;color:#9CA3AF;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #374151; }

    .ticket-card {
        background: #13172B;
        border: 1px solid #1E2340;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 10px;
    }

    .metric-card {
        background: linear-gradient(135deg, #13172B 0%, #1A1F38 100%);
        border: 1px solid #1E2340;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-card .metric-value { font-size: 2.5rem; font-weight: 800; color: #AADC00; line-height: 1; }
    .metric-card .metric-label { font-size: 13px; color: #9CA3AF; margin-top: 6px; font-weight: 500; }
    .metric-card .metric-icon  { font-size: 1.5rem; margin-bottom: 8px; }

    ::-webkit-scrollbar       { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0A0C18; }
    ::-webkit-scrollbar-thumb { background: #1E2340; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #AADC00; }

    [data-testid="stChatMessage"] {
        background: #13172B !important; border: 1px solid #1E2340 !important; border-radius: 10px !important;
    }
    [data-testid="stExpander"] {
        background: #13172B !important; border: 1px solid #1E2340 !important; border-radius: 10px !important;
    }
    [data-testid="stForm"] {
        background: #13172B !important; border: 1px solid #1E2340 !important;
        border-radius: 12px !important; padding: 20px !important;
    }

    .vapa-header { display:flex; align-items:center; gap:10px; padding:8px 0 20px 0;
                   border-bottom:1px solid #1E2340; margin-bottom:20px; }
    .vapa-header .brand { font-size:1.4rem; font-weight:800; color:#AADC00; letter-spacing:-0.5px; }
    .vapa-header .brand span { color:#E8EAF6; font-weight:300; }

    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 3. BASE DE DATOS
# ─────────────────────────────────────────────
def run_query(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(query, params)
        if query.strip().upper().startswith(("SELECT", "PRAGMA")):
            return c.fetchall()
        conn.commit()
        return c.lastrowid


def hash_pass(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_pass(password, hashed):
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except:
        return False


def sanitizar(nombre):
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', nombre)


@st.cache_resource
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS usuarios
            (username TEXT PRIMARY KEY, password TEXT, rol TEXT,
             estado TEXT, email TEXT, debe_cambiar_pass INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS incidencias
            (id INTEGER PRIMARY KEY, titulo TEXT, descripcion TEXT,
             usuario_reporte TEXT, tecnico_asignado TEXT, estado TEXT,
             fecha TEXT, archivo TEXT, informe_tecnico TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS comentarios_incidencia
            (id INTEGER PRIMARY KEY AUTOINCREMENT, incidencia_id INTEGER,
             autor TEXT, fecha TEXT, comentario TEXT)""")
        c.execute("CREATE TABLE IF NOT EXISTS slas (prioridad TEXT PRIMARY KEY, horas INTEGER)")

        c.execute("PRAGMA table_info(incidencias)")
        cols = [r[1] for r in c.fetchall()]
        for col, default in [("prioridad","'Media'"),("categoria","'Otros'"),
                              ("fecha_limite","NULL"),("fecha_resolucion","NULL")]:
            if col not in cols:
                c.execute(f"ALTER TABLE incidencias ADD COLUMN {col} TEXT DEFAULT {default}")

        c.execute("PRAGMA table_info(usuarios)")
        if "debe_cambiar_pass" not in [r[1] for r in c.fetchall()]:
            c.execute("ALTER TABLE usuarios ADD COLUMN debe_cambiar_pass INTEGER DEFAULT 0")

        if not c.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
            for u, p, r in [("admin","admin","Administrador"),("tec1","tec1","Tecnico"),
                             ("tec2","tec2","Tecnico"),("user1","user1","Usuario")]:
                c.execute("INSERT INTO usuarios VALUES (?,?,?,?,?,?)",
                          (u, hash_pass(p), r, "Activo", f"{u}@vapa.es", 0))
        if not c.execute("SELECT 1 FROM slas LIMIT 1").fetchone():
            c.executemany("INSERT INTO slas VALUES (?,?)",
                          [("Baja",120),("Media",72),("Alta",24),("Urgente",4)])


# ─────────────────────────────────────────────
# 4. AUTH
# ─────────────────────────────────────────────
def login(username, password):
    r = run_query("SELECT password, rol, debe_cambiar_pass FROM usuarios WHERE username=?", (username,))
    if r and check_pass(password, r[0][0]):
        return r[0][1], r[0][2]
    return None, None


# ─────────────────────────────────────────────
# 5. EMAIL / PDF / EXCEL
# ─────────────────────────────────────────────
def _send_mail(to, subject, body):
    try:
        yagmail.SMTP(EMAIL_EMISOR, EMAIL_PASSWORD).send(to=to, subject=subject, contents=body)
    except Exception as e:
        print(f"[mail] {e}")

def async_mail(to, subject, body):
    if to:
        threading.Thread(target=_send_mail, args=(to, subject, body), daemon=True).start()

def clean(t):
    return str(t) if t else "N/A"

def generar_pdf(inc, comentarios):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=10, y=8, w=30)
        pdf.set_xy(45, 12)
    else:
        pdf.set_xy(10, 12)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(170, 220, 0)
    pdf.cell(0, 12, "VAPA Service Desk", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(30, 30, 30)
    pdf.set_y(40)
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, f"Ticket #{inc[0]} — {clean(inc[1])}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", size=11)
    pdf.ln(4)
    prio = inc[9]  if len(inc)>9  else "Media"
    cat  = inc[10] if len(inc)>10 else "Otros"
    lim  = inc[11] if len(inc)>11 and inc[11] else "Sin límite"
    res  = inc[12] if len(inc)>12 and inc[12] else "Pendiente"
    for label, val in [("Categoría/Prioridad", f"{cat} / {prio}"),
                       ("Usuario", clean(inc[3])), ("Técnico", clean(inc[4])),
                       ("Estado", clean(inc[5])), ("Creación", clean(inc[6])),
                       ("Límite / Resolución", f"{lim} / {res}")]:
        pdf.cell(0, 8, f"{label}: {val}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_fill_color(170, 220, 0)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, " Descripción:", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 7, clean(inc[2]))
    if inc[8]:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, " Informe técnico:", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 7, clean(inc[8]))
    if comentarios:
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, " Comentarios:", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_font("Helvetica", size=9)
        for au, fe, tx in comentarios:
            pdf.multi_cell(0, 6, f"[{fe}] {au}: {clean(tx)}")
    return bytes(pdf.output())

def exportar_excel(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Incidencias")
    return buf.getvalue()


# ─────────────────────────────────────────────
# 6. HELPERS UI
# ─────────────────────────────────────────────
def badge_prio(p):
    cls = {"Urgente":"urgente","Alta":"alta","Media":"media","Baja":"baja"}.get(p,"media")
    return f'<span class="badge-{cls}">{p}</span>'

def badge_estado(e):
    cls = {"Abierta":"abierta","En resolución":"resolucion",
           "Pendiente de validación":"validacion","Validada/Terminada":"terminada"}.get(e,"abierta")
    return f'<span class="badge-{cls}">{e}</span>'

def sla_badge(inc):
    fecha_limite     = inc[11] if len(inc)>11 and inc[11] else None
    fecha_resolucion = inc[12] if len(inc)>12 and inc[12] else None
    if not fecha_limite:
        return "⚪"
    try:
        lim = pendulum.parse(fecha_limite)
        if inc[5] in ["Validada/Terminada","Pendiente de validación"]:
            if fecha_resolucion:
                return "🔴" if pendulum.parse(fecha_resolucion) > lim else "🟢"
            return "🟢"
        ahora = pendulum.now()
        if ahora > lim: return "🔴"
        if (lim-ahora).in_hours() < 24: return "🟡"
        return "🟢"
    except:
        return "⚪"

def nav_button(label, key, page):
    if st.sidebar.button(label, key=key, use_container_width=True):
        st.session_state["pagina"] = page
        st.session_state["inc_sel"] = None
        st.rerun()


# ─────────────────────────────────────────────
# 7. VISTAS
# ─────────────────────────────────────────────

def vista_dashboard():
    st.markdown("## 📊 Dashboard")

    total       = run_query("SELECT COUNT(*) FROM incidencias")[0][0]
    abiertos    = run_query("SELECT COUNT(*) FROM incidencias WHERE estado='Abierta'")[0][0]
    en_res      = run_query("SELECT COUNT(*) FROM incidencias WHERE estado='En resolución'")[0][0]
    resueltos_h = run_query(
        "SELECT COUNT(*) FROM incidencias WHERE estado='Validada/Terminada' AND DATE(fecha_resolucion)=DATE('now')"
    )[0][0]
    sin_asignar = run_query(
        "SELECT COUNT(*) FROM incidencias WHERE tecnico_asignado='Sin Asignar' AND estado='Abierta'"
    )[0][0]
    todos_ab = run_query(
        "SELECT fecha_limite FROM incidencias WHERE estado NOT IN ('Validada/Terminada','Pendiente de validación')"
    )
    sla_riesgo = sum(1 for r in todos_ab if r[0] and pendulum.now() > pendulum.parse(r[0]))

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    for col, icon, val, label in [
        (c1,"📋",total,"Total tickets"),
        (c2,"🔵",abiertos,"Abiertos"),
        (c3,"🟣",en_res,"En resolución"),
        (c4,"✅",resueltos_h,"Resueltos hoy"),
        (c5,"⚠️",sin_asignar,"Sin asignar"),
        (c6,"🔴",sla_riesgo,"SLA en riesgo"),
    ]:
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### Tickets por estado")
        d = run_query("SELECT estado, COUNT(*) FROM incidencias GROUP BY estado")
        if d:
            st_echarts({
                "backgroundColor":"transparent",
                "tooltip":{"trigger":"item"},
                "legend":{"textStyle":{"color":"#9CA3AF"}},
                "series":[{"type":"pie","radius":["40%","70%"],
                           "data":[{"value":v,"name":k} for k,v in d],
                           "itemStyle":{"borderRadius":6},
                           "label":{"color":"#E8EAF6"}}],
                "color":["#AADC00","#0EA5E9","#A78BFA","#F59E0B","#EF4444"]
            }, height="280px")

    with col_b:
        st.markdown("### Tickets por prioridad")
        d2 = run_query("SELECT prioridad, COUNT(*) FROM incidencias GROUP BY prioridad")
        if d2:
            keys   = [r[0] for r in d2]
            vals   = [r[1] for r in d2]
            colors = {"Urgente":"#EF4444","Alta":"#F97316","Media":"#0EA5E9","Baja":"#22C55E"}
            st_echarts({
                "backgroundColor":"transparent",
                "xAxis":{"type":"category","data":keys,"axisLabel":{"color":"#9CA3AF"}},
                "yAxis":{"type":"value","axisLabel":{"color":"#9CA3AF"},
                         "splitLine":{"lineStyle":{"color":"#1E2340"}}},
                "series":[{"type":"bar","data":[
                    {"value":v,"itemStyle":{"color":colors.get(k,"#AADC00")}}
                    for k,v in zip(keys,vals)
                ],"barMaxWidth":50,"itemStyle":{"borderRadius":[6,6,0,0]}}],
                "tooltip":{"trigger":"axis"}
            }, height="280px")

    st.markdown("<br>", unsafe_allow_html=True)

    sin_asig = run_query(
        "SELECT id,titulo,prioridad,categoria,fecha FROM incidencias "
        "WHERE tecnico_asignado='Sin Asignar' AND estado='Abierta' ORDER BY id DESC LIMIT 8"
    )
    if sin_asig:
        st.markdown("### 🚨 Tickets sin asignar")
        for t in sin_asig:
            ca, cb, cc, cd = st.columns([1,4,2,1])
            ca.markdown(f"**#{t[0]}**")
            cb.write(t[1])
            cc.markdown(badge_prio(t[2] or "Media"), unsafe_allow_html=True)
            if cd.button("👁️", key=f"dash_t_{t[0]}"):
                st.session_state["inc_sel"] = t[0]
                st.session_state["pagina"]  = "tickets"
                st.rerun()

    recientes = run_query(
        "SELECT autor,fecha,comentario,incidencia_id FROM comentarios_incidencia ORDER BY id DESC LIMIT 5"
    )
    if recientes:
        st.markdown("### 🕐 Actividad reciente")
        for au, fe, tx, iid in recientes:
            st.markdown(
                f'<div class="ticket-card" style="padding:10px 16px;">'
                f'<small style="color:#9CA3AF">{fe} — <b style="color:#AADC00">#{iid}</b></small><br>'
                f'<span style="font-size:13px"><b>{au}:</b> {tx[:80]}{"…" if len(tx)>80 else ""}</span>'
                f'</div>', unsafe_allow_html=True
            )


def vista_tickets(filtro="todos"):
    st.markdown("## 📋 Tickets")

    col_s, col_n = st.columns([5,1])
    with col_s:
        buscar = st.text_input("🔍 Buscar por título o ID...", key="buscador_tickets", placeholder="Filtrar...")
    with col_n:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Nuevo", key="btn_nuevo_top"):
            st.session_state["pagina"] = "nuevo"
            st.rerun()

    base  = ("SELECT id,titulo,prioridad,categoria,usuario_reporte,"
             "tecnico_asignado,estado,fecha_limite,fecha,fecha_resolucion FROM incidencias")
    where = []
    rol   = st.session_state["rol"]
    user  = st.session_state["username"]

    if rol == "Tecnico":
        where.append(f"tecnico_asignado='{user}'")
    elif rol == "Usuario":
        where.append(f"usuario_reporte='{user}'")

    if filtro == "sin_asignar":
        where.append("tecnico_asignado='Sin Asignar'")
    elif filtro == "urgentes":
        where.append("prioridad='Urgente'")
    elif filtro == "mis":
        where.append(f"(usuario_reporte='{user}' OR tecnico_asignado='{user}')")
    elif filtro == "archivados":
        where.append("estado='Validada/Terminada'")
    else:
        where.append("estado != 'Validada/Terminada'")

    if buscar:
        where.append(f"(titulo LIKE '%{buscar}%' OR CAST(id AS TEXT) LIKE '%{buscar}%')")

    q    = base + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC"
    incs = run_query(q)

    if not incs:
        st.info("No hay tickets con estos filtros.")
        return

    t_card, t_tabla = st.tabs(["🃏 Tarjetas", "📊 Tabla"])

    with t_card:
        for i in incs:
            sla = sla_badge(i)
            st.markdown(f"""
            <div class="ticket-card">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                    <span style="color:#9CA3AF;font-size:12px">#{i[0]} · {i[4]} · {(i[8] or '')[:10]}</span>
                    <span>{sla}</span>
                </div>
                <div style="font-weight:600;font-size:15px;margin-bottom:8px">{i[1]}</div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
                    {badge_prio(i[2] or 'Media')}
                    {badge_estado(i[6] or 'Abierta')}
                    <span style="font-size:12px;color:#9CA3AF">🔧 {i[5]}</span>
                    <span style="font-size:12px;color:#9CA3AF">📁 {i[3]}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Ver detalle →", key=f"card_{i[0]}"):
                st.session_state["inc_sel"] = i[0]
                st.rerun()

    with t_tabla:
        df = pd.DataFrame(incs, columns=["ID","Título","Prioridad","Categoría",
                                          "Usuario","Técnico","Estado","Límite","Fecha","Resolución"])
        st.download_button("📥 Excel", exportar_excel(df), "vapa_tickets.xlsx", key="exp_excel")
        gb   = GridOptionsBuilder.from_dataframe(df)
        gb.configure_selection("single")
        grid = AgGrid(df, gridOptions=gb.build(), theme="streamlit", height=400)
        sel  = grid.get("selected_rows")
        if sel is not None and len(sel) > 0:
            sid = sel.iloc[0]["ID"] if isinstance(sel, pd.DataFrame) else sel[0]["ID"]
            if st.button(f"Abrir #{sid}", key="open_table"):
                st.session_state["inc_sel"] = int(sid)
                st.rerun()


@st.fragment
def chat_fragment(id_inc, autor_reporte, tecnico_asig):
    st.markdown("#### 💬 Comentarios")
    coms  = run_query(
        "SELECT autor,fecha,comentario FROM comentarios_incidencia WHERE incidencia_id=? ORDER BY id ASC",
        (id_inc,)
    )
    chat  = st.container(height=320)
    with chat:
        if coms:
            for au, fe, tx in coms:
                with st.chat_message("user" if au == autor_reporte else "assistant"):
                    st.markdown(f"**{au}** <small style='color:#9CA3AF'>{fe}</small>", unsafe_allow_html=True)
                    st.write(tx)
        else:
            st.info("Sin comentarios aún.")

    nuevo = st.chat_input("Escribe un comentario...")
    if nuevo:
        autor = st.session_state["username"]
        run_query("INSERT INTO comentarios_incidencia (incidencia_id,autor,fecha,comentario) VALUES (?,?,?,?)",
                  (id_inc, autor, pendulum.now().to_datetime_string(), nuevo))
        if autor == autor_reporte and tecnico_asig != "Sin Asignar":
            m = run_query("SELECT email FROM usuarios WHERE username=?", (tecnico_asig,))
            if m: async_mail(m[0][0], f"Comentario — Ticket #{id_inc}", f"{autor}: {nuevo}")
        elif autor != autor_reporte:
            m = run_query("SELECT email FROM usuarios WHERE username=?", (autor_reporte,))
            if m: async_mail(m[0][0], f"Respuesta técnica — #{id_inc}", f"El técnico {autor} respondió.")
        st.rerun()


def vista_detalle(id_inc):
    datos = run_query("SELECT * FROM incidencias WHERE id=?", (id_inc,))
    if not datos:
        st.error("Ticket no encontrado.")
        st.session_state["inc_sel"] = None
        st.rerun()
        return

    inc  = datos[0]
    prio = inc[9]  if len(inc)>9  else "Media"
    cat  = inc[10] if len(inc)>10 else "Otros"
    lim  = inc[11] if len(inc)>11 and inc[11] else None
    res  = inc[12] if len(inc)>12 and inc[12] else None
    h_s  = run_query("SELECT horas FROM slas WHERE prioridad=?", (prio,))
    h_p  = h_s[0][0] if h_s else "?"

    cb1, cb2, cb3 = st.columns([1,5,2])
    with cb1:
        if st.button("← Volver"):
            st.session_state["inc_sel"] = None
            st.rerun()
    with cb2:
        st.markdown(f"## #{inc[0]} — {inc[1]}")
        st.markdown(
            f"{badge_prio(prio)} {badge_estado(inc[5])} "
            f'<span style="color:#9CA3AF;font-size:13px"> · {cat} · {sla_badge(inc)} SLA</span>',
            unsafe_allow_html=True
        )
    with cb3:
        try:
            c2  = run_query("SELECT autor,fecha,comentario FROM comentarios_incidencia WHERE incidencia_id=? ORDER BY id ASC",(inc[0],))
            pdf = generar_pdf(inc, c2)
            st.download_button("📄 PDF", pdf, f"VAPA_#{inc[0]}.pdf", "application/pdf")
        except Exception as e:
            st.warning(f"PDF: {e}")

    st.divider()
    col_l, col_r = st.columns([3,1])

    with col_l:
        with st.container(border=True):
            st.markdown("**Descripción**")
            st.info(inc[2])
            nombre_arch = inc[7]
            if nombre_arch and nombre_arch != "Sin archivo":
                ruta = os.path.join(CARPETA_SUBIDAS, nombre_arch)
                if os.path.exists(ruta):
                    with open(ruta,"rb") as f:
                        st.download_button(f"📎 {nombre_arch}", f.read(), nombre_arch)
                else:
                    st.caption("⚠️ Archivo no encontrado en disco.")
        chat_fragment(inc[0], inc[3], inc[4])

    with col_r:
        with st.container(border=True):
            st.markdown("**Detalles**")
            st.markdown(f"👤 **Usuario:** {inc[3]}")
            st.markdown(f"🔧 **Técnico:** {inc[4]}")
            st.markdown(f"🗓️ **Creado:** {(inc[6] or '')[:10]}")
            st.markdown(f"⏳ **Límite ({h_p}h):** {lim[:10] if lim else 'N/A'}")
            st.markdown(f"✅ **Resuelto:** {res[:10] if res else '—'}")
            st.markdown(f"📊 **SLA:** {sla_badge(inc)}")

        puede_editar = (st.session_state["rol"] == "Administrador") or \
                       (st.session_state["rol"] == "Tecnico" and st.session_state["username"] == inc[4])
        if puede_editar:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("**🛠️ Gestión técnica**")
                plantillas = {
                    "Manual":     inc[8] or "",
                    "Reinicio":   "Se ha reiniciado el servicio. Funcionamiento restablecido.",
                    "Caché":      "Borrado de caché completado. Portal operativo.",
                    "Escalado N2":"Escalado a N2 para revisión avanzada."
                }
                p_sel = st.selectbox("Plantilla", list(plantillas.keys()), key="plantilla_sel")
                with st.form("form_gestion"):
                    n_inf  = st.text_area("Informe técnico", value=plantillas[p_sel], height=100)
                    ests   = ["Abierta","En resolución","Pendiente de validación","Validada/Terminada"]
                    n_est  = st.selectbox("Estado", ests, index=ests.index(inc[5]) if inc[5] in ests else 0)
                    prios  = ["Baja","Media","Alta","Urgente"]
                    n_prio = st.selectbox("Prioridad", prios, index=prios.index(prio) if prio in prios else 1)
                    if st.form_submit_button("💾 Guardar"):
                        n_lim = lim
                        n_res = res
                        if n_est in ["Validada/Terminada","Pendiente de validación"] and \
                           inc[5] not in ["Validada/Terminada","Pendiente de validación"]:
                            n_res = pendulum.now().to_datetime_string()
                        elif n_est not in ["Validada/Terminada","Pendiente de validación"]:
                            n_res = None
                        if n_prio != prio:
                            hs = run_query("SELECT horas FROM slas WHERE prioridad=?", (n_prio,))
                            h  = hs[0][0] if hs else 72
                            try: n_lim = pendulum.parse(inc[6]).add(hours=h).to_datetime_string()
                            except: pass
                        run_query(
                            "UPDATE incidencias SET informe_tecnico=?,estado=?,prioridad=?,"
                            "fecha_limite=?,fecha_resolucion=? WHERE id=?",
                            (n_inf, n_est, n_prio, n_lim, n_res, inc[0])
                        )
                        if n_est != inc[5]:
                            m = run_query("SELECT email FROM usuarios WHERE username=?", (inc[3],))
                            if m: async_mail(m[0][0], f"Estado actualizado — #{inc[0]}", f"Nuevo estado: {n_est}")
                        st.success("✅ Guardado.")
                        st.rerun()


def vista_nuevo_ticket():
    st.markdown("## ➕ Nuevo Ticket")
    with st.form("f_nuevo"):
        c1, c2 = st.columns(2)
        with c1:
            m_id  = st.number_input("ID manual", min_value=1, step=1)
            m_tit = st.text_input("Asunto *")
            m_cat = st.selectbox("Categoría", ["Hardware","Software","Redes","Accesos","Otros"])
        with c2:
            m_prio = st.selectbox("Prioridad", ["Baja","Media","Alta","Urgente"], index=1)
            if st.session_state["rol"] != "Usuario":
                tecs  = [t[0] for t in run_query("SELECT username FROM usuarios WHERE rol='Tecnico'")]
                m_tec = st.selectbox("Asignar técnico", ["Sin Asignar"] + tecs)
            else:
                m_tec = "Sin Asignar"
            m_file = st.file_uploader("Adjunto (opcional)")
        m_desc = st.text_area("Descripción *", height=120)

        if st.form_submit_button("🚀 Registrar Ticket"):
            if not m_tit or not m_desc:
                st.error("El asunto y la descripción son obligatorios.")
            elif run_query("SELECT id FROM incidencias WHERE id=?", (m_id,)):
                st.error(f"El ID #{m_id} ya existe.")
            else:
                now = pendulum.now()
                hs  = run_query("SELECT horas FROM slas WHERE prioridad=?", (m_prio,))
                lim = now.add(hours=hs[0][0] if hs else 72).to_datetime_string()
                n_a = "Sin archivo"
                if m_file:
                    n_a = now.format("YYYYMMDD_HHmm_") + sanitizar(m_file.name)
                    with open(os.path.join(CARPETA_SUBIDAS, n_a), "wb") as f:
                        f.write(m_file.getbuffer())
                run_query(
                    "INSERT INTO incidencias (id,titulo,descripcion,usuario_reporte,tecnico_asignado,"
                    "estado,fecha,archivo,prioridad,categoria,fecha_limite) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (m_id, m_tit, m_desc, st.session_state["username"],
                     m_tec, "Abierta", now.to_datetime_string(), n_a, m_prio, m_cat, lim)
                )
                st.success(f"✅ Ticket #{m_id} registrado.")
                st.session_state["pagina"] = "tickets"
                st.rerun()


def vista_admin():
    st.markdown("## ⚙️ Administración")
    if st.session_state["rol"] != "Administrador":
        st.error("🔒 Sin permisos.")
        return

    tab_u, tab_sla, tab_db = st.tabs(["👥 Usuarios","⏱️ SLAs","💾 Base de datos"])

    with tab_u:
        u_bd  = run_query("SELECT username,rol,estado,email FROM usuarios")
        df_u  = pd.DataFrame(u_bd, columns=["Usuario","Rol","Estado","Email"])
        df_u["Reset Pass"] = False
        e_df  = st.data_editor(df_u, num_rows="dynamic", use_container_width=True, key="ed_usr")
        if st.button("💾 Guardar usuarios"):
            for _, r in e_df.iterrows():
                u,rl,es,em,res = r["Usuario"],r["Rol"],r["Estado"],r["Email"],r["Reset Pass"]
                if run_query("SELECT username FROM usuarios WHERE username=?", (u,)):
                    run_query("UPDATE usuarios SET rol=?,estado=?,email=? WHERE username=?", (rl,es,em,u))
                    if res:
                        run_query("UPDATE usuarios SET password=?,debe_cambiar_pass=1 WHERE username=?",
                                  (hash_pass("1234"), u))
                else:
                    run_query("INSERT INTO usuarios VALUES (?,?,?,?,?,1)", (u,hash_pass("1234"),rl,es,em))
            st.success("✅ Usuarios actualizados.")

    with tab_sla:
        slas_bd = run_query("SELECT prioridad,horas FROM slas")
        df_sla  = pd.DataFrame(slas_bd, columns=["Prioridad","Horas"])
        e_sla   = st.data_editor(df_sla, use_container_width=True, key="ed_sla")
        if st.button("💾 Guardar SLAs"):
            for _,r in e_sla.iterrows():
                run_query("UPDATE slas SET horas=? WHERE prioridad=?", (int(r["Horas"]),r["Prioridad"]))
            st.success("✅ SLAs actualizados.")

    with tab_db:
        if os.path.exists(DB_PATH):
            with open(DB_PATH,"rb") as f:
                st.download_button("📥 Descargar backup",f.read(),
                                   f"vapa_backup_{pendulum.now().format('YYYYMMDD_HHmm')}.db")


def vista_kb():
    st.markdown("## 📖 Base de Conocimiento")
    with st.expander("🔑 ¿Cómo restablecer mi contraseña?"):
        st.write("Contacta con soporte N1 para que restablezcan tus credenciales.")
    with st.expander("🌐 No tengo conexión a Internet"):
        st.write("1. Reinicia el router.\n2. Reinicia tu equipo.\n3. Si persiste, abre un ticket en Redes.")
    with st.expander("🖥️ El equipo no arranca"):
        st.write("Abre un ticket con prioridad Alta en categoría Hardware.")
    with st.expander("📧 No recibo correos"):
        st.write("Revisa la carpeta de spam. Si persiste, abre ticket en Software.")


# ─────────────────────────────────────────────
# 8. MAIN
# ─────────────────────────────────────────────
def main():
    cargar_css()
    init_db()

    for k,v in {"logged_in":False,"username":None,"rol":None,
                "pagina":"dashboard","inc_sel":None,"debe_cambiar_pass":0}.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # LOGIN
    if not st.session_state["logged_in"]:
        _, col, _ = st.columns([1,2,1])
        with col:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if os.path.exists(LOGO_PATH):
                st.image(LOGO_PATH, width=120)
            st.markdown("## Iniciar sesión")
            st.markdown('<p style="color:#9CA3AF">VAPA Service Desk</p>', unsafe_allow_html=True)
            with st.form("f_login"):
                u = st.text_input("Usuario", placeholder="usuario")
                p = st.text_input("Contraseña", type="password", placeholder="••••••••")
                if st.form_submit_button("Entrar →", use_container_width=True):
                    rol, dcp = login(u, p)
                    if rol:
                        st.session_state.update({"logged_in":True,"username":u,
                                                  "rol":rol,"debe_cambiar_pass":dcp,"pagina":"dashboard"})
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos.")
        return

    # CAMBIO CONTRASEÑA OBLIGATORIO
    if st.session_state["debe_cambiar_pass"] == 1:
        _, col, _ = st.columns([1,2,1])
        with col:
            st.markdown("## 🔒 Cambia tu contraseña")
            with st.form("f_cambio"):
                p1 = st.text_input("Nueva contraseña", type="password")
                p2 = st.text_input("Repetir contraseña", type="password")
                if st.form_submit_button("Actualizar"):
                    if p1 and p1 == p2:
                        run_query("UPDATE usuarios SET password=?,debe_cambiar_pass=0 WHERE username=?",
                                  (hash_pass(p1), st.session_state["username"]))
                        st.session_state["debe_cambiar_pass"] = 0
                        st.success("¡Contraseña actualizada!")
                        st.rerun()
                    else:
                        st.error("Las contraseñas no coinciden.")
        return

    # SIDEBAR
    with st.sidebar:
        st.markdown("""
        <div class="vapa-header">
            <div class="brand">VAPA <span>Service Desk</span></div>
        </div>""", unsafe_allow_html=True)

        st.markdown(
            f'<div style="background:#1A1F38;border:1px solid #1E2340;border-radius:8px;'
            f'padding:10px 14px;margin-bottom:16px">'
            f'<div style="font-weight:600;color:#AADC00">{st.session_state["username"]}</div>'
            f'<div style="font-size:12px;color:#9CA3AF">{st.session_state["rol"]}</div>'
            f'</div>', unsafe_allow_html=True
        )

        st.markdown('<div style="font-size:11px;color:#6B7280;font-weight:600;'
                    'text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">NAVEGACIÓN</div>',
                    unsafe_allow_html=True)

        nav_button("📊  Dashboard",          "nav_dash",  "dashboard")
        nav_button("📋  Todos los tickets",  "nav_todos", "tickets")
        nav_button("🎯  Mis tickets",        "nav_mis",   "mis_tickets")
        nav_button("⚠️  Sin asignar",        "nav_sin",   "sin_asignar")
        nav_button("🚨  Urgentes",           "nav_urg",   "urgentes")
        nav_button("✅  Archivados",         "nav_arch",  "archivados")
        nav_button("➕  Nuevo ticket",       "nav_nuevo", "nuevo")

        st.divider()
        st.markdown('<div style="font-size:11px;color:#6B7280;font-weight:600;'
                    'text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">SISTEMA</div>',
                    unsafe_allow_html=True)
        nav_button("📖  Conocimiento", "nav_kb",    "kb")
        if st.session_state["rol"] == "Administrador":
            nav_button("⚙️  Administración", "nav_admin", "admin")

        st.divider()
        bid = st.number_input("Ir a ticket #", min_value=1, step=1, value=None, key="jump_id")
        if st.button("Ir →", key="btn_jump"):
            if bid and run_query("SELECT id FROM incidencias WHERE id=?", (bid,)):
                st.session_state["inc_sel"] = int(bid)
                st.session_state["pagina"]  = "tickets"
                st.rerun()
            elif bid:
                st.error("No existe")

        st.divider()
        if st.button("🚪 Cerrar sesión", key="btn_logout", use_container_width=True):
            for k in ["logged_in","username","rol","pagina","inc_sel","debe_cambiar_pass"]:
                st.session_state[k] = {"logged_in":False,"username":None,"rol":None,
                                       "pagina":"dashboard","inc_sel":None,"debe_cambiar_pass":0}[k]
            st.rerun()

    # CONTENIDO PRINCIPAL
    pagina = st.session_state["pagina"]

    if st.session_state["inc_sel"] and pagina in ("tickets","mis_tickets","sin_asignar","urgentes","archivados","dashboard"):
        vista_detalle(st.session_state["inc_sel"])
        return

    if   pagina == "dashboard":   vista_dashboard()
    elif pagina == "tickets":     vista_tickets("todos")
    elif pagina == "mis_tickets": vista_tickets("mis")
    elif pagina == "sin_asignar": vista_tickets("sin_asignar")
    elif pagina == "urgentes":    vista_tickets("urgentes")
    elif pagina == "archivados":  vista_tickets("archivados")
    elif pagina == "nuevo":       vista_nuevo_ticket()
    elif pagina == "admin":       vista_admin()
    elif pagina == "kb":          vista_kb()


if __name__ == "__main__":
    main()
