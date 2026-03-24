import streamlit as st
import pandas as pd
import pendulum
import os

from database import run_query, hash_pass
from config import DB_PATH


def vista_administracion():
    st.title("⚙️ Administración")

    if st.session_state['rol'] != 'Administrador':
        st.error("🔒 Sin permisos")
        return

    # Copia de seguridad
    st.subheader("Copia de Seguridad")
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "rb") as db_f:
            st.download_button("📥 Descargar DB", db_f,
                               f"vapa_{pendulum.now().format('YYYYMMDD')}.db")
    st.divider()

    # Gestión de usuarios
    st.subheader("Gestión de Usuarios")
    u_bd  = run_query("SELECT username, rol, estado, email FROM usuarios")
    df_u  = pd.DataFrame(u_bd, columns=["Usuario", "Rol", "Estado", "Email"])
    df_u["Reset Pass"] = False
    e_df  = st.data_editor(df_u, num_rows="dynamic", use_container_width=True)

    if st.button("Guardar Usuarios"):
        for _, r in e_df.iterrows():
            u, rl, es, em, res = r['Usuario'], r['Rol'], r['Estado'], r['Email'], r['Reset Pass']
            if run_query("SELECT username FROM usuarios WHERE username=?", (u,)):
                run_query("UPDATE usuarios SET rol=?, estado=?, email=? WHERE username=?",
                          (rl, es, em, u))
                if res:
                    run_query("UPDATE usuarios SET password=?, debe_cambiar_pass=1 WHERE username=?",
                              (hash_pass("1234"), u))
            else:
                run_query("INSERT INTO usuarios VALUES (?,?,?,?,?,1)",
                          (u, hash_pass("1234"), rl, es, em))
        st.success("Base de datos actualizada")

    st.divider()

    # Configuración de SLAs
    st.subheader("Tiempos SLA")
    slas_bd = run_query("SELECT prioridad, horas FROM slas")
    df_slas = pd.DataFrame(slas_bd, columns=["Prioridad", "Horas"])
    e_slas  = st.data_editor(df_slas, use_container_width=True)

    if st.button("Guardar SLAs"):
        for _, r in e_slas.iterrows():
            run_query("UPDATE slas SET horas=? WHERE prioridad=?", (int(r['Horas']), r['Prioridad']))
        st.success("SLA actualizado")
