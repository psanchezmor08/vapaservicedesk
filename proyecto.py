import streamlit as st
import pendulum
import os
 
from config import LOGO_PATH
from database import init_db, run_query, hash_pass
from auth import login
from ui_styles import cargar_css_corporativo
from ui_tickets import ver_detalle_incidencia, vista_listado, vista_crear_ticket
from ui_dashboard import vista_dashboard
from ui_admin import vista_administracion
 
# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(page_title="VAPA Service Desk", layout="wide", page_icon="logo_vapa.png")
 
 
def main():
    cargar_css_corporativo()
 
    # Estado de sesión por defecto
    defaults = {
        'logged_in': False, 'username': None, 'rol': None,
        'incidencia_seleccionada': None, 'pagina_actual': 'resumen',
        'debe_cambiar_pass': 0
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
 
    init_db()
 
    # ── Sidebar ─────────────────────────────────────────────────────────────
    with st.sidebar:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, use_container_width=True)
        else:
            st.markdown("<h1 style='color:#FFCC00;'>VAPA</h1>", unsafe_allow_html=True)
        st.divider()
 
        if not st.session_state['logged_in']:
            st.subheader("Login")
            u_input = st.text_input("Usuario")
            p_input = st.text_input("Contraseña", type='password')
            if st.button("Entrar"):
                rol, debe_cambiar = login(u_input, p_input)
                if rol:
                    st.session_state.update({
                        'logged_in': True, 'username': u_input,
                        'rol': rol, 'debe_cambiar_pass': debe_cambiar,
                        'pagina_actual': 'resumen'
                    })
                    st.rerun()
                else:
                    st.error("Acceso denegado")
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
                    if b_id and run_query("SELECT id FROM incidencias WHERE id=?", (b_id,)):
                        st.session_state.update({'incidencia_seleccionada': b_id, 'pagina_actual': 'resumen'})
                        st.rerun()
                    elif b_id:
                        st.error("No existe")
 
            st.divider()
            if st.button("Cerrar Sesión", use_container_width=True):
                st.session_state.update(defaults)
                st.rerun()
 
    # ── Contenido principal ──────────────────────────────────────────────────
    if not st.session_state['logged_in']:
        return
 
    # Cambio de contraseña obligatorio
    if st.session_state['debe_cambiar_pass'] == 1:
        st.title("🔒 Cambio de Contraseña")
        with st.form("f_pass"):
            p1 = st.text_input("Nueva contraseña", type="password")
            p2 = st.text_input("Repetir contraseña", type="password")
            if st.form_submit_button("Actualizar"):
                if p1 and p1 == p2:
                    run_query("UPDATE usuarios SET password=?, debe_cambiar_pass=0 WHERE username=?",
                              (hash_pass(p1), st.session_state['username']))
                    st.session_state['debe_cambiar_pass'] = 0
                    st.success("Contraseña actualizada.")
                    st.rerun()
                else:
                    st.error("Las contraseñas no coinciden")
        return
 
    # Administración
    if st.session_state['pagina_actual'] == 'administracion':
        vista_administracion()
        return
 
    # Panel principal
    if st.session_state['pagina_actual'] == 'resumen':
        if st.session_state['incidencia_seleccionada']:
            ver_detalle_incidencia(st.session_state['incidencia_seleccionada'])
        else:
            st.title("Panel de Control")
            tabs = st.tabs(["📋 Incidencias", "➕ Crear Nueva", "📊 Dashboard", "📖 Conocimiento"])
 
            with tabs[0]:
                vista_listado()
 
            with tabs[1]:
                vista_crear_ticket()
 
            with tabs[2]:
                vista_dashboard()
 
            with tabs[3]:
                st.subheader("📖 Base de Conocimiento")
                with st.expander("🔑 Restablecer contraseña"):
                    st.write("Contacta con soporte N1.")
                with st.expander("🌐 Sin Internet"):
                    st.write("Reinicia el router y tu equipo.")
 
 
if __name__ == '__main__':
    main()
