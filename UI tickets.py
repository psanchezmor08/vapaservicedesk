import streamlit as st
import pandas as pd
import pendulum
import io
import os
import re
from st_aggrid import AgGrid, GridOptionsBuilder

from database import run_query
from utils_pdf import generar_pdf
from utils_email import disparar_correo_async
from config import CARPETA_SUBIDAS


def sanitizar_nombre_archivo(nombre):
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', nombre)


def exportar_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Incidencias')
    return output.getvalue()


# ── Chat de comentarios (fragmento para no recargar toda la página) ─────────
@st.fragment
def seccion_chat_incidencia(id_inc, autor_reporte, tecnico_asig):
    st.subheader("💬 Historial de Comentarios")
    comentarios = run_query(
        "SELECT autor, fecha, comentario FROM comentarios_incidencia "
        "WHERE incidencia_id = ? ORDER BY id ASC", (id_inc,)
    )

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
        run_query(
            "INSERT INTO comentarios_incidencia (incidencia_id, autor, fecha, comentario) VALUES (?,?,?,?)",
            (id_inc, autor_actual, fecha_coment, nuevo_comentario)
        )
        if autor_actual == autor_reporte and tecnico_asig != "Sin Asignar":
            mail_tec = run_query("SELECT email FROM usuarios WHERE username = ?", (tecnico_asig,))
            if mail_tec:
                disparar_correo_async(mail_tec[0][0], f"Comentario Usuario - Ticket #{id_inc}",
                                      f"{autor_actual} dice: {nuevo_comentario}")
        elif autor_actual != autor_reporte:
            mail_usr = run_query("SELECT email FROM usuarios WHERE username = ?", (autor_reporte,))
            if mail_usr:
                disparar_correo_async(mail_usr[0][0], f"Respuesta Técnica - Ticket #{id_inc}",
                                      f"El técnico {autor_actual} ha respondido.")
        st.rerun()


# ── Detalle completo de una incidencia ──────────────────────────────────────
def ver_detalle_incidencia(id_incidencia):
    datos = run_query("SELECT * FROM incidencias WHERE id = ?", (id_incidencia,))
    if not datos:
        st.error("Incidencia no encontrada.")
        st.session_state['incidencia_seleccionada'] = None
        st.rerun()
        return

    inc              = datos[0]
    prioridad        = inc[9]  if len(inc) > 9  else "Media"
    categoria        = inc[10] if len(inc) > 10 else "Otros"
    fecha_limite     = inc[11] if len(inc) > 11 and inc[11] else None
    fecha_resolucion = inc[12] if len(inc) > 12 and inc[12] else None

    st.markdown(f"## 📂 Detalle Incidencia #{inc[0]}")
    col_btn1, col_btn2 = st.columns([1, 5])

    with col_btn1:
        if st.button("⬅️ Volver"):
            st.session_state['incidencia_seleccionada'] = None
            st.rerun()

    with col_btn2:
        try:
            com_pdf   = run_query(
                "SELECT autor, fecha, comentario FROM comentarios_incidencia "
                "WHERE incidencia_id = ? ORDER BY id ASC", (inc[0],)
            )
            pdf_bytes = generar_pdf(inc, com_pdf)
            st.download_button("📄 Descargar PDF", pdf_bytes,
                               f"VAPA_Ticket_{inc[0]}.pdf", "application/pdf")
        except Exception as e:
            st.warning(f"Error PDF: {e}")

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
                        st.download_button(f"📥 Descargar {nombre_archivo}", f.read(), nombre_archivo)
                else:
                    st.warning("⚠️ Archivo no encontrado.")
            else:
                st.text("No hay archivos.")

    with col_info2:
        with st.container(border=True):
            st.markdown("#### 👤 Detalles y SLAs")
            st.write(f"**Usuario:** {inc[3]}")
            st.write(f"**Asignado a:** {inc[4]}")
            h_sla        = run_query("SELECT horas FROM slas WHERE prioridad = ?", (prioridad,))
            h_permitidas = h_sla[0][0] if h_sla else "N/A"
            st.divider()
            st.write(f"**🗓️ Creación:** {inc[6]}")
            st.write(f"**⏳ Límite ({h_permitidas}h):** {fecha_limite if fecha_limite else 'N/A'}")

            estado_sla_badge = "⚪ N/A"
            if fecha_limite:
                try:
                    limite_dt = pendulum.parse(fecha_limite)
                    if inc[5] in ["Validada/Terminada", "Pendiente de validación"]:
                        if fecha_resolucion:
                            resol_dt         = pendulum.parse(fecha_resolucion)
                            estado_sla_badge = "🔴 Retrasada" if resol_dt > limite_dt else "🟢 En tiempo"
                        else:
                            estado_sla_badge = "🟢 Resuelta"
                    else:
                        ahora = pendulum.now()
                        if ahora > limite_dt:
                            estado_sla_badge = "🔴 Retrasada"
                        elif (limite_dt - ahora).in_hours() < 24:
                            estado_sla_badge = "🟡 Crítico"
                        else:
                            estado_sla_badge = "🟢 En tiempo"
                except:
                    estado_sla_badge = "Error de fecha"

            st.write(f"**📊 SLA:** {estado_sla_badge}")
            color_prio = "red" if prioridad == "Urgente" else "orange" if prioridad == "Alta" else "blue"
            st.markdown(f"**Gravedad:** :{color_prio}[**{prioridad}**]")
            st.divider()

    seccion_chat_incidencia(inc[0], inc[3], inc[4])

    puede_editar = (st.session_state['rol'] == 'Administrador') or \
                   (st.session_state['rol'] == 'Tecnico' and st.session_state['username'] == inc[4])

    if puede_editar:
        st.divider()
        st.subheader("🛠️ Gestión Técnica y Resolución")
        plantillas = {
            "--- Manual ---":  inc[8] if inc[8] else "",
            "🔧 Reinicio":     "Se ha procedido a reiniciar el servicio. Funcionamiento restablecido.",
            "🧹 Caché":        "Borrado de caché y datos temporales realizado. Portal operativo.",
            "🚀 Escalado N2":  "Problema persistente. Se escala a Nivel 2 para revisión de base de datos."
        }
        p_sel = st.selectbox("Plantillas de respuesta:", list(plantillas.keys()))

        with st.form("form_gestion"):
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                n_informe = st.text_area("Informe Técnico Final:", value=plantillas[p_sel], height=150)
            with col_g2:
                est_disp   = ["Abierta", "En resolución", "Pendiente de validación", "Validada/Terminada"]
                idx_est    = est_disp.index(inc[5]) if inc[5] in est_disp else 0
                n_estado   = st.selectbox("Estado", est_disp, index=idx_est)
                nueva_prio = st.selectbox("Modificar Gravedad", ["Baja", "Media", "Alta", "Urgente"],
                                          index=["Baja", "Media", "Alta", "Urgente"].index(prioridad))

            if st.form_submit_button("💾 Guardar Cambios"):
                n_limite     = fecha_limite
                n_resolucion = fecha_resolucion
                if n_estado in ["Validada/Terminada", "Pendiente de validación"] and \
                   inc[5] not in ["Validada/Terminada", "Pendiente de validación"]:
                    n_resolucion = pendulum.now().to_datetime_string()
                elif n_estado not in ["Validada/Terminada", "Pendiente de validación"]:
                    n_resolucion = None

                if nueva_prio != prioridad:
                    h_sla_n = run_query("SELECT horas FROM slas WHERE prioridad = ?", (nueva_prio,))
                    h_calc  = h_sla_n[0][0] if h_sla_n else 72
                    try:
                        n_limite = pendulum.parse(inc[6]).add(hours=h_calc).to_datetime_string()
                    except:
                        pass

                run_query(
                    "UPDATE incidencias SET informe_tecnico=?, estado=?, prioridad=?, "
                    "fecha_limite=?, fecha_resolucion=? WHERE id=?",
                    (n_informe, n_estado, nueva_prio, n_limite, n_resolucion, inc[0])
                )
                if n_estado != inc[5]:
                    m_usr = run_query("SELECT email FROM usuarios WHERE username = ?", (inc[3],))
                    if m_usr:
                        disparar_correo_async(m_usr[0][0], f"Estado Ticket #{inc[0]}",
                                              f"Estado actualizado a: {n_estado}")
                st.success("Ticket actualizado.")
                st.rerun()


# ── Listado de incidencias ───────────────────────────────────────────────────
def vista_listado():
    q_l = ("SELECT id, titulo, prioridad, categoria, usuario_reporte, "
           "tecnico_asignado, estado, fecha_limite FROM incidencias")
    if st.session_state['rol'] == 'Tecnico':
        q_l += f" WHERE tecnico_asignado='{st.session_state['username']}'"
    elif st.session_state['rol'] == 'Usuario':
        q_l += f" WHERE usuario_reporte='{st.session_state['username']}'"

    incs = run_query(q_l)
    if not incs:
        st.info("Sin incidencias")
        return

    df_i   = pd.DataFrame(incs, columns=['ID', 'Título', 'Prioridad', 'Categoría',
                                          'Reporta', 'Técnico', 'Estado', 'Fecha Límite'])
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
        gb   = GridOptionsBuilder.from_dataframe(df_i)
        gb.configure_selection('single')
        grid = AgGrid(df_i, gridOptions=gb.build(), theme='streamlit')
        sel  = grid.get('selected_rows')
        if sel is not None and len(sel) > 0:
            sid = sel.iloc[0]['ID'] if isinstance(sel, pd.DataFrame) else sel[0]['ID']
            if st.button(f"Abrir #{sid}"):
                st.session_state.incidencia_seleccionada = int(sid)
                st.rerun()


# ── Formulario de creación de ticket ────────────────────────────────────────
def vista_crear_ticket():
    with st.form("f_inc"):
        col1, col2 = st.columns(2)
        with col1:
            m_id   = st.number_input("ID (Manual)", min_value=1)
            m_tit  = st.text_input("Asunto")
            m_cat  = st.selectbox("Categoría", ["Hardware", "Software", "Redes", "Accesos", "Otros"])
        with col2:
            m_prio = st.selectbox("Gravedad", ["Baja", "Media", "Alta", "Urgente"], index=1)
            m_tec  = "Sin Asignar" if st.session_state.rol == 'Usuario' else \
                     st.selectbox("Técnico", ["Sin Asignar"] +
                                  [t[0] for t in run_query("SELECT username FROM usuarios WHERE rol='Tecnico'")])
            m_file = st.file_uploader("Archivo")
        m_desc = st.text_area("Descripción")

        if st.form_submit_button("Registrar Ticket"):
            if m_tit and m_id:
                if run_query("SELECT id FROM incidencias WHERE id=?", (m_id,)):
                    st.error("ID duplicado")
                else:
                    f_c     = pendulum.now()
                    h_sla_c = run_query("SELECT horas FROM slas WHERE prioridad=?", (m_prio,))
                    f_l     = f_c.add(hours=h_sla_c[0][0] if h_sla_c else 72).to_datetime_string()
                    n_a     = "Sin archivo"
                    if m_file:
                        n_a = f_c.format("YYYYMMDD_HHmm_") + sanitizar_nombre_archivo(m_file.name)
                        with open(os.path.join(CARPETA_SUBIDAS, n_a), "wb") as f:
                            f.write(m_file.getbuffer())
                    run_query(
                        "INSERT INTO incidencias (id, titulo, descripcion, usuario_reporte, "
                        "tecnico_asignado, estado, fecha, archivo, prioridad, categoria, fecha_limite) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (m_id, m_tit, m_desc, st.session_state.username,
                         m_tec, 'Abierta', f_c.to_datetime_string(), n_a, m_prio, m_cat, f_l)
                    )
                    st.success("Registrado!")
                    st.rerun()
