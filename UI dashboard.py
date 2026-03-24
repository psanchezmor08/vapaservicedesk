import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from database import run_query


def vista_dashboard():
    d_d = run_query("SELECT estado, categoria, prioridad FROM incidencias")
    if not d_d:
        st.info("No hay datos suficientes para mostrar estadísticas.")
        return

    df_d       = pd.DataFrame(d_d, columns=['Estado', 'Cat', 'Prio'])
    c_d1, c_d2 = st.columns(2)

    with c_d1:
        st.write("### Estados")
        v_e = df_d['Estado'].value_counts().to_dict()
        st_echarts({"series": [{"type": "pie",
                                 "data": [{"value": v, "name": k} for k, v in v_e.items()]}]})
    with c_d2:
        st.write("### Prioridades")
        v_p = df_d['Prio'].value_counts().to_dict()
        st_echarts({
            "xAxis": {"type": "category", "data": list(v_p.keys())},
            "yAxis": {"type": "value"},
            "series": [{"data": list(v_p.values()), "type": "bar"}]
        })
