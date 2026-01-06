# Autor: Vladimir Alonso B. P. (para uso empresarial)
# -*- coding: utf-8 -*-
"""
Haircuts DCV – Repos y Deuda Externa (BanRep) • Streamlit App
Autor: vbarahona
Fecha: 2026-01-05

Características:
- Descarga directa desde CloudFront con validación HEAD.
- Resolver universal para patrones nuevos y legados (2019+).
- Modo batch con ZIP.
- Caption estilizado.
"""

import io
import zipfile
import datetime as dt
import pandas as pd
import requests
import streamlit as st
from urllib.parse import quote

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
HEADERS = {"User-Agent": "Mozilla/5.0 (haircuts-app)"}

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

def listar_meses():
    return MESES

def mes_capitalizado(mes: str) -> str:
    return mes[:1].upper() + mes[1:].lower()

def mes_mayus(mes: str) -> str:
    return mes.upper()

def validar_existencia_archivo(url: str) -> bool:
    try:
        r = requests.head(url, headers=HEADERS, timeout=15)
        return r.status_code == 200
    except Exception:
        return False

def descargar_binario(url: str) -> bytes | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r.content
        return None
    except Exception:
        return None

def construir_candidatos(tipo: str, mes: str, anio: int) -> list[tuple[str, str]]:
    """
    Genera candidatos para todos los patrones conocidos:
    - Nuevo formato: haircuts-{tipo}-{mes}-{anio}.xlsx/.xls
    - Variantes raíz y /paginas/: Haircut, Haircuts, HAIRCUT_
    - Extensiones: .xlsx, .xls, .pdf
    """
    mes_l = mes.lower()
    mes_cap = mes_capitalizado(mes_l)
    mes_up = mes_mayus(mes_l)

    candidatos = []

    # Nuevo formato
    base_new = f"{BASE_CLOUDFRONT}/{tipo}-{mes_l}-{anio}"
    candidatos += [
        (f"{base_new}.xlsx", "XLSX"),
        (f"{base_new}.xls", "XLS"),
    ]

    # Variantes raíz (sin /paginas/)
    for prefix in ["Haircut", "Haircuts"]:
        for ext in ["xlsx", "xls"]:
            fname = f"{prefix} {mes_cap} {anio}.{ext}"
            candidatos.append((f"{BASE_CLOUDFRONT}/{quote(fname)}", ext.upper()))

    # Variantes en /paginas/
    for prefix in ["Haircut", "Haircuts"]:
        for ext in ["xlsx", "xls", "pdf"]:
            fname = f"{prefix} {mes_cap} {anio}.{ext}"
            candidatos.append((f"{BASE_CLOUDFRONT}/paginas/{quote(fname)}", ext.upper()))

    # HAIRCUT_{MES}_{AÑO} (PDF y Excel)
    for ext in ["pdf", "xls", "xlsx"]:
        fname = f"HAIRCUT_{mes_up}_{anio}.{ext}"
        candidatos.append((f"{BASE_CLOUDFRONT}/paginas/{quote(fname)}", ext.upper()))
        fname2 = f"haircut_{mes_up}_{anio}.{ext}"
        candidatos.append((f"{BASE_CLOUDFRONT}/paginas/{quote(fname2)}", ext.upper()))

    return candidatos

def resolver_url_archivo(tipo: str, mes: str, anio: int) -> tuple[str | None, str | None, list[tuple[str, str]]]:
    cand = construir_candidatos(tipo, mes, anio)
    for url, ext in cand:
        if validar_existencia_archivo(url):
            return url, ext, cand
    return None, None, cand

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
    url_archivo, tipo_archivo, cand = resolver_url_archivo(tipo_sel, mes_sel, anio_sel)

    with st.expander("Diagnóstico: candidatos generados y orden de prioridad"):
        st.dataframe(pd.DataFrame(cand, columns=["URL", "Tipo"]), use_container_width=True)

    if not url_archivo:
        st.error("Archivo no encontrado con los patrones disponibles.")
        return

    st.success(f"Archivo encontrado ({tipo_archivo}): {url_archivo}")
    binario = descargar_binario(url_archivo)
    if not binario:
        st.error("Fallo al descargar el archivo.")
        return

    nombre_archivo = f"{tipo_sel}-{mes_sel}-{anio_sel}.{tipo_archivo.lower()}"
    st.download_button(
        f"Descargar {tipo_archivo}",
        data=binario,
        file_name=nombre_archivo,
        mime="application/octet-stream",
        key=f"dl-{tipo_sel}-{mes_sel}-{anio_sel}"
    )

    if tipo_archivo in ["XLSX", "XLS"]:
        try:
            with io.BytesIO(binario) as bio:
                df_preview = pd.read_excel(bio, engine="openpyxl")
            st.subheader("Vista previa (primeras filas)")
            st.dataframe(df_preview.head(50), use_container_width=True)
        except Exception as e:
            st.warning(f"No fue posible mostrar vista previa: {e}")
    else:
        st.caption("Vista previa no disponible para archivos PDF.")

def descargar_batch(anio_sel: int, tipo_sel: str):
    meses = listar_meses()
    tipos = ["haircuts-repos", "haircuts-deuda-externa"] if tipo_sel == "ambos" else [tipo_sel]
    resultados = []
    archivos_zip = io.BytesIO()

    with zipfile.ZipFile(archivos_zip, "w") as zipf:
        for mes in meses:
            for tipo_iter in tipos:
                url_archivo, tipo_archivo, _ = resolver_url_archivo(tipo_iter, mes, anio_sel)
                if url_archivo:
                    binario = descargar_binario(url_archivo)
                    if binario:
                        nombre_archivo = f"{tipo_iter}-{mes}-{anio_sel}.{(tipo_archivo or 'bin').lower()}"
                        zipf.writestr(nombre_archivo, binario)
                        resultados.append({"Mes": mes, "Tipo": tipo_iter, "Estado": "Disponible", "URL": url_archivo})
                    else:
                        resultados.append({"Mes": mes, "Tipo": tipo_iter, "Estado": "Error descarga", "URL": url_archivo})
                else:
                    resultados.append({"Mes": mes, "Tipo": tipo_iter, "Estado": "No disponible", "URL": None})

    return resultados, archivos_zip

# -----------------------------
# Acciones
# -----------------------------
if st.button("Buscar y descargar"):
    with st.spinner("Procesando..."):
        if modo_batch:
            resultados, archivos_zip = descargar_batch(year, tipo)
            st.subheader(f"Resultados para {year}")
            st.dataframe(pd.DataFrame(resultados), use_container_width=True)
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
