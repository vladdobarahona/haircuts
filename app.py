# Autor: Vladimir Alonso B. P. (para uso empresarial)

# -*- coding: utf-8 -*-
"""
Haircuts DCV – Repos y Deuda Externa (BanRep) • Streamlit App
Autor: vbarahona
Fecha: 2026-01-05

Mejoras:
- Validación automática (HEAD) antes de descargar.
- Modo batch: lista todos los meses del año según tipo seleccionado.
- Texto adicional en color naranja.
"""

import io
import zipfile
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

st.markdown(
    "<span style='color:#F59B1D; font-size:0.5em; font-family:\"Century Gothic\", sans-serif;'>"
    "Creado por Copilot con base a idea de web scrapping en selenium originada por Vladimir Barahona."
    "</span>",
    unsafe_allow_html=True
)

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
    return f"{BASE_CLOUDFRONT}/{tipo}-{mes}-{anio}.xlsx"

def validar_existencia_archivo(url: str) -> bool:
    try:
        r = requests.head(url, timeout=15)
        return r.status_code == 200
    except Exception:
        return False

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

tipo = st.radio("Tipo de haircuts", ["haircuts-repos", "haircuts-deuda-externa", "ambos"], horizontal=True)
col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("Año", years, index=len(years) - 1)
with col2:
    mes_texto = st.selectbox("Mes", meses, index=hoy.month - 1)

modo_batch = st.checkbox("Modo batch: listar todos los meses del año")

# -----------------------------
# Funciones principales
# -----------------------------
def flujo_descarga(tipo_sel: str, mes_sel: str, anio_sel: int):
    url = construir_url(tipo_sel, mes_sel, anio_sel)
    st.info(f"URL construida: {url}")

    if not validar_existencia_archivo(url):
        st.error("Archivo no encontrado. Puede que aún no esté publicado.")
        return

    binario = descargar_binario(url)
    if not binario:
        st.error("Fallo al descargar el archivo.")
        return

    nombre_archivo = f"{tipo_sel}-{mes_sel}-{anio_sel}.xlsx"
    st.download_button(
        f"Descargar Excel",
        data=binario,
        file_name=nombre_archivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl-{tipo_sel}-{mes_sel}-{anio_sel}"
    )

    try:
        with io.BytesIO(binario) as bio:
            df_preview = pd.read_excel(bio, engine="openpyxl")
        st.subheader("Vista previa (primeras filas)")
        st.dataframe(df_preview.head(50), use_container_width=True)
    except Exception as e:
        st.warning(f"No fue posible mostrar vista previa: {e}")

def descargar_batch(anio_sel: int, tipo_sel: str):
    meses = listar_meses()
    tipos = ["haircuts-repos", "haircuts-deuda-externa"] if tipo_sel == "ambos" else [tipo_sel]
    resultados = []
    archivos_zip = io.BytesIO()
    with zipfile.ZipFile(archivos_zip, "w") as zipf:
        for mes in meses:
            for tipo in tipos:
                url = construir_url(tipo, mes, anio_sel)
                existe = validar_existencia_archivo(url)
                if existe:
                    binario = descargar_binario(url)
                    if binario:
                        nombre_archivo = f"{tipo}-{mes}-{anio_sel}.xlsx"
                        zipf.writestr(nombre_archivo, binario)
                        resultados.append({"Mes": mes, "Tipo": tipo, "Estado": "Disponible"})
                    else:
                        resultados.append({"Mes": mes, "Tipo": tipo, "Estado": "Error descarga"})
                else:
                    resultados.append({"Mes": mes, "Tipo": tipo, "Estado": "No disponible"})
    return resultados, archivos_zip

# -----------------------------
# Acciones
# -----------------------------
if st.button("Buscar y descargar"):
    with st.spinner("Procesando..."):
        if modo_batch:
            resultados, archivos_zip = descargar_batch(year, tipo)
            st.subheader(f"Resultados para {year}")
            st.dataframe(pd.DataFrame(resultados))
            st.download_button(
                "Descargar ZIP con archivos disponibles",
                data=archivos_zip.getvalue(),
                file_name=f"haircuts-{year}.zip",
                mime="application/zip"
            )
        else:
            if tipo == "ambos":
                st.markdown("### Repos")
                flujo_descarga("haircuts-repos", mes_texto, year)
                st.markdown("---")
                st.markdown("### Deuda Externa")
                flujo_descarga("haircuts-deuda-externa", mes_texto, year)
            else:
                flujo_descarga(tipo, mes_texto, year)
