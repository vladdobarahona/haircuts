# Autor: Vladimir Alonso B. P. (para uso empresarial)
# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
"""
Haircuts DCV – Repos y Deuda Externa (BanRep) • Streamlit App
Autor: vbarahona
Fecha: 2026-01-05

Descripción:
- Construye la URL directa del archivo en CloudFront.
- Descarga el archivo si existe (Excel).
- Muestra vista previa si es Excel.
"""

import io
import datetime as dt
import pandas as pd
import requests
import streamlit as st

# -----------------------------
# Configuración de la página
# -----------------------------
st.set_page_config(page_title="Haircuts DCV – BanRep", page_icon="💼", layout="centered")
st.title("Haircuts DCV – Repos y Deuda Externa (BanRep)")
st.caption("Descarga directa desde el repositorio oficial (CloudFront) del Banco de la República.")

# -----------------------------
# Constantes y utilidades
# -----------------------------
BASE_CLOUDFRONT = "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files"

def listar_meses():
    return [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

def construir_url(tipo: str, mes: str, anio: int) -> str:
    """
    Construye la URL directa del archivo .xlsx en CloudFront.
    Ejemplo:
    https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/haircuts-repos-enero-2026.xlsx
    """
    return f"{BASE_CLOUDFRONT}/{tipo}-{mes}-{anio}.xlsx"

def descargar_binario(url: str) -> bytes | None:
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return r.content
        return None
    except Exception:
        return None

# -----------------------------
# Interfaz
# -----------------------------
hoy = dt.date.today()
meses = listar_meses()
years = list(range(2019, hoy.year + 1))

tipo = st.radio("Tipo de haircuts", ["haircuts-repos", "haircuts-deuda-externa"], horizontal=True)
col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("Año", years, index=len(years) - 1)
with col2:
    mes_texto = st.selectbox("Mes", meses, index=hoy.month - 1)

descargar_ambos = st.checkbox("Descargar ambos (Repos y Deuda Externa)")

# -----------------------------
# Acción principal
# -----------------------------
def flujo_descarga(tipo_sel: str, mes_sel: str, anio_sel: int):
    url = construir_url(tipo_sel, mes_sel, anio_sel)
    st.info(f"URL construida: {url}")

    binario = descargar_binario(url)
    if not binario:
        st.error("Archivo no encontrado. Puede que aún no esté publicado.")
        return

    nombre_archivo = f"{tipo_sel}-{mes_sel}-{anio_sel}.xlsx"
    st.download_button(
        f"Descargar Excel",
        data=binario,
        file_name=nombre_archivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl-{tipo_sel}-{mes_sel}-{anio_sel}"
    )

    # Vista previa
    try:
        with io.BytesIO(binario) as bio:
            df_preview = pd.read_excel(bio, engine="openpyxl")
        st.subheader("Vista previa (primeras filas)")
        st.dataframe(df_preview.head(50), use_container_width=True)
    except Exception as e:
        st.warning(f"No fue posible mostrar vista previa: {e}")

if st.button("Buscar y descargar"):
    with st.spinner("Consultando CloudFront…"):
        if descargar_ambos:
            st.markdown("### Repos")
            flujo_descarga("haircuts-repos", mes_texto, year)
            st.markdown("---")
            st.markdown("### Deuda Externa")
            flujo_descarga("haircuts-deuda-externa", mes_texto, year)
        else:
            flujo_descarga(tipo, mes_texto, year)
