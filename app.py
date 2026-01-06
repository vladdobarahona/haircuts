# Autor: Vladimir Alonso B. P. (para uso empresarial)
# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
"""
Haircuts DCV – Repos y Deuda Externa (BanRep) • Streamlit App
Autor: vbarahona
Fecha: 2026-01-05

Descripción:
- Interfaz para seleccionar Tipo (Repos / Deuda Externa), Mes y Año.
- Busca el detalle mensual en el listado oficial del Banco de la República.
- Localiza el adjunto (Excel, PDF, CSV) y permite descargarlo.
- Muestra vista previa del Excel si es posible.
"""

import io
import re
import datetime as dt
from typing import Optional, List

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# -----------------------------
# Configuración de la página
# -----------------------------
st.set_page_config(
    page_title="Haircuts DCV (Repos & Deuda Externa) – BanRep",
    page_icon="💼",
    layout="centered"
)

st.title("Haircuts DCV – Repos y Deuda Externa (BanRep)")
st.caption(
    "La app consulta el listado oficial del Banco de la República y localiza la publicación mensual "
    "para descargar el adjunto en formato Excel, PDF o CSV, cuando esté disponible."
)
st.markdown(
    "[Ver página de listado oficial](https://www.banrep.gov.co/es/sistemas-pago/dcv/haircuts-repos-deuda-externa)"
)

# -----------------------------
# Constantes y utilidades
# -----------------------------
BASE = "https://www.banrep.gov.co"
LISTADO_URL = f"{BASE}/es/sistemas-pago/dcv/haircuts-repos-deuda-externa"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (haircuts-app; +https://github.com/tu-usuario/haircuts-app)"
}

def listar_meses() -> List[dict]:
    return [
        {"num": 1, "nombre_largo": "enero"},
        {"num": 2, "nombre_largo": "febrero"},
        {"num": 3, "nombre_largo": "marzo"},
        {"num": 4, "nombre_largo": "abril"},
        {"num": 5, "nombre_largo": "mayo"},
        {"num": 6, "nombre_largo": "junio"},
        {"num": 7, "nombre_largo": "julio"},
        {"num": 8, "nombre_largo": "agosto"},
        {"num": 9, "nombre_largo": "septiembre"},
        {"num": 10, "nombre_largo": "octubre"},
        {"num": 11, "nombre_largo": "noviembre"},
        {"num": 12, "nombre_largo": "diciembre"},
    ]

def _get_soup(url: str) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None

@st.cache_data(ttl=600)
def _listar_paginas_listado() -> List[str]:
    urls = [LISTADO_URL]
    soup = _get_soup(LISTADO_URL)
    if not soup:
        return urls
    for a in soup.select("ul.pager a[href]"):
        href = a.get("href", "")
        if href.startswith("/"):
            href = BASE + href
        if href and href not in urls:
            urls.append(href)
    return urls

def _titulo_publicacion(tipo: str, mes_largo: str, year: int) -> str:
    prefijo = "Haircuts Repos" if tipo == "haircuts-repos" else "Haircuts deuda externa"
    return f"{prefijo} - {mes_largo} {year}"

def _construir_slug_detalle(tipo: str, mes_largo: str, year: int) -> str:
    return f"/es/sistemas-pago/dcv/{tipo}-{mes_largo}-{year}"

def _encontrar_url_detalle_mensual_por_texto(tipo: str, mes_largo: str, year: int) -> Optional[str]:
    titulo_objetivo = _titulo_publicacion(tipo, mes_largo, year)
    pattern = re.compile(rf"^{re.escape(titulo_objetivo)}$", flags=re.I)
    for url in _listar_paginas_listado():
        soup = _get_soup(url)
        if not soup:
            continue
        for a in soup.select("a[href]"):
            text = a.get_text(strip=True)
            if pattern.match(text):
                href = a.get("href", "")
                return href if href.startswith("http") else BASE + href
    return None

def encontrar_url_detalle_mensual(tipo: str, mes_largo: str, year: int) -> Optional[str]:
    url = _encontrar_url_detalle_mensual_por_texto(tipo, mes_largo, year)
    if url:
        return url
    candidata = BASE + _construir_slug_detalle(tipo, mes_largo, year)
    soup = _get_soup(candidata)
    return candidata if soup else None

def encontrar_enlace_archivo(url_detalle: str) -> tuple[Optional[str], Optional[str]]:
    soup = _get_soup(url_detalle)
    if not soup:
        return None, None
    for ext in [".xlsx", ".xls", ".csv", ".pdf"]:
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if "/sites/default/files/" in href and href.lower().endswith(ext):
                url = href if href.startswith("http") else BASE + href
                tipo = ext.replace(".", "").upper()
                return url, tipo
    return None, None

def descargar_binario(url_archivo: str) -> Optional[bytes]:
    try:
        r = requests.get(url_archivo, headers=HEADERS, timeout=60, stream=True)
        r.raise_for_status()
        return r.content
    except Exception:
        return None

# -----------------------------
# Controles de la interfaz
# -----------------------------
hoy = dt.date.today()
meses = listar_meses()
years = list(range(2019, hoy.year + 1))

tipo = st.radio("Tipo de haircuts", ["haircuts-repos", "haircuts-deuda-externa"], horizontal=True)
col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("Año", years, index=len(years) - 1)
with col2:
    mes_texto = st.selectbox("Mes (español)", [m["nombre_largo"] for m in meses], index=hoy.month - 1)

descargar_ambos = st.checkbox("Descargar ambos (Repos y Deuda Externa) para el mes/año seleccionados")

# -----------------------------
# Acción principal
# -----------------------------
def flujo_descarga(tipo_sel: str, mes_sel: str, anio_sel: int):
    url_detalle = encontrar_url_detalle_mensual(tipo_sel, mes_sel, anio_sel)
    if not url_detalle:
        st.error(f"No se encontró la página de detalle para: {tipo_sel} – {mes_sel} {anio_sel}.")
        return

    st.success(f"Detalle localizado: {url_detalle}")
    url_archivo, tipo_archivo = encontrar_enlace_archivo(url_detalle)
    if not url_archivo:
        st.warning("No se encontró ningún archivo adjunto (.xlsx, .xls, .csv, .pdf) en el detalle.")
        st.markdown(f"Abrir página manualmente")
        return

    st.info(f"Archivo encontrado ({tipo_archivo}): {url_archivo}")
    binario = descargar_binario(url_archivo)
    if not binario:
        st.error("Fallo al descargar el archivo.")
        return

    nombre_sugerido = f"{tipo_sel}-{mes_sel}-{anio_sel}.{tipo_archivo.lower()}"
    st.download_button(
        f"Descargar {tipo_archivo}",
        data=binario,
        file_name=nombre_sugerido,
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
            st.warning(f"No fue posible mostrar vista previa del Excel: {e}")
    else:
        st.caption("Vista previa no disponible para archivos PDF/CSV.")

if st.button("Buscar y descargar"):
    with st.spinner("Consultando el portal de BanRep…"):
        if descargar_ambos:
            st.markdown("### Repos")
            flujo_descarga("haircuts-repos", mes_texto, year)
            st.markdown("---")
            st.markdown("### Deuda Externa")
            flujo_descarga("haircuts-deuda-externa", mes_texto, year)
        else:
            flujo_descarga(tipo, mes_texto, year)
