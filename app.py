# Autor: Vladimir Alonso B. P. (para uso empresarial)
# -*- coding: utf-8 -*-
"""
Haircuts DCV – Repos y Deuda Externa (BanRep) • Streamlit App
Autor: vbarahona
Fecha: 2026-01-05

Descripción:
- Interfaz para seleccionar Tipo (Repos / Deuda Externa), Mes y Año.
- Busca el detalle mensual en el listado oficial del Banco de la República.
- Localiza el adjunto .xlsx y permite descargarlo.
- Muestra vista previa del Excel si es posible.

Notas de fuente (para referencia):
- Listado oficial de Haircuts Repos BR y Haircuts Deuda Externa:
  https://www.banrep.gov.co/es/sistemas-pago/dcv/haircuts-repos-deuda-externa
- Ejemplo de detalle publicado (enero 2026, deuda externa):
  https://www.banrep.gov.co/es/sistemas-pago/dcv/haircuts-deuda-externa-enero-2026
- Cambios en estructura/nombres de archivos (v1.03, 2024-01-09):
  https://www.banrep.gov.co/es/sistemas-pago/dcv/estructura-archivo-emisiones-vigentes-haircuts
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
    "para descargar el adjunto en formato Excel, cuando esté disponible."
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
    """Devuelve lista de dicts con nombres de meses en español (formato público del portal)."""
    return [
        {"num": 1, "num_2d": "01", "nombre_largo": "enero"},
        {"num": 2, "num_2d": "02", "nombre_largo": "febrero"},
        {"num": 3, "num_2d": "03", "nombre_largo": "marzo"},
        {"num": 4, "num_2d": "04", "nombre_largo": "abril"},
        {"num": 5, "num_2d": "05", "nombre_largo": "mayo"},
        {"num": 6, "num_2d": "06", "nombre_largo": "junio"},
        {"num": 7, "num_2d": "07", "nombre_largo": "julio"},
        {"num": 8, "num_2d": "08", "nombre_largo": "agosto"},
        {"num": 9, "num_2d": "09", "nombre_largo": "septiembre"},
        {"num": 10, "num_2d": "10", "nombre_largo": "octubre"},
        {"num": 11, "num_2d": "11", "nombre_largo": "noviembre"},
        {"num": 12, "num_2d": "12", "nombre_largo": "diciembre"},
    ]


def _get_soup(url: str) -> Optional[BeautifulSoup]:
    """Devuelve el BeautifulSoup de la página o None si hay error."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None


@st.cache_data(ttl=600)
def _listar_paginas_listado() -> List[str]:
    """
    Devuelve URLs de todas las páginas del listado (paginación: 1, 2, … último).
    Se cachea por 10 minutos.
    """
    urls = [LISTADO_URL]
    soup = _get_soup(LISTADO_URL)
    if not soup:
        return urls

    # Enlaces del paginador típicamente en <ul class="pager">  (ver listado oficial)
    for a in soup.select("ul.pager a[href]"):
        href = a.get("href", "")
        if href.startswith("/"):
            href = BASE + href
        if href and href not in urls:
            urls.append(href)
    return urls


def _titulo_publicacion(tipo: str, mes_largo: str, year: int) -> str:
    """
    Texto visible del enlace tal como aparece en el listado:
      - "Haircuts Repos - enero 2026"
      - "Haircuts deuda externa - enero 2026"
    (observado en la página oficial de listado)
    """
    prefijo = "Haircuts Repos" if tipo == "haircuts-repos" else "Haircuts deuda externa"
    return f"{prefijo} - {mes_largo} {year}"


def _construir_slug_detalle(tipo: str, mes_largo: str, year: int) -> str:
    """
    Slug esperado del detalle (muchas veces coincide con la URL publicada):
    /es/sistemas-pago/dcv/haircuts-deuda-externa-enero-2026
    /es/sistemas-pago/dcv/haircuts-repos-enero-2026
    """
    return f"/es/sistemas-pago/dcv/{tipo}-{mes_largo}-{year}"


def _encontrar_url_detalle_mensual_por_texto(tipo: str, mes_largo: str, year: int) -> Optional[str]:
    """
    Recorre todas las páginas del listado y busca el <a> cuyo texto visible
    coincide con el título esperado (case-insensitive).
    """
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
                if href.startswith("http"):
                    return href
                elif href.startswith("/"):
                    return BASE + href
    return None


def encontrar_url_detalle_mensual(tipo: str, mes_largo: str, year: int) -> Optional[str]:
    """
    1) Intenta localizar el detalle buscando por el TEXTO visible del enlace
       en todas las páginas del listado oficial (robusto frente a cambios).
    2) Fallback: intenta la URL directa construida por slug.
       Ejemplo verificado: deuda externa enero 2026.
    """
    # Paso 1: por texto visible en el listado
    url = _encontrar_url_detalle_mensual_por_texto(tipo, mes_largo, year)
    if url:
        return url

    # Paso 2: fallback por slug (si el portal lo expone así)
    candidata = BASE + _construir_slug_detalle(tipo, mes_largo, year)
    soup = _get_soup(candidata)
    return candidata if soup else None


def encontrar_enlace_xlsx(url_detalle: str) -> Optional[str]:
    """
    En el detalle, buscar adjunto .xlsx bajo /sites/default/files/…
    (ruta típica de adjuntos públicos del portal).
    Si no hay .xlsx, intenta .xls o .csv como alternativas.
    """
    soup = _get_soup(url_detalle)
    if not soup:
        return None

    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "/sites/default/files/" in href and href.lower().endswith(".xlsx"):
            return href if href.startswith("http") else BASE + href

    # Alternativas: xls / csv
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "/sites/default/files/" in href and re.search(r"\.(xls|csv)$", href, flags=re.I):
            return href if href.startswith("http") else BASE + href

    return None


def descargar_binario(url_archivo: str) -> Optional[bytes]:
    """Descarga y devuelve el binario del archivo (xlsx/xls/csv)."""
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
years = list(range(2019, hoy.year + 1))  # según disponibilidad pública desde 2019

tipo = st.radio(
    "Tipo de haircuts",
    ["haircuts-repos", "haircuts-deuda-externa"],
    horizontal=True
)

col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("Año", years, index=len(years) - 1)
with col2:
    mes_texto = st.selectbox(
        "Mes (español)",
        [m["nombre_largo"] for m in meses],
        index=hoy.month - 1
    )

descargar_ambos = st.checkbox("Descargar ambos (Repos y Deuda Externa) para el mes/año seleccionados")


# -----------------------------
# Acción principal
# -----------------------------
def flujo_descarga(tipo_sel: str, mes_sel: str, anio_sel: int):
    url_detalle = encontrar_url_detalle_mensual(tipo_sel, mes_sel, anio_sel)

    if not url_detalle:
        st.error(
            f"No se encontró la página de detalle para: {tipo_sel} – {mes_sel} {anio_sel}. "
            "Prueba otro mes/año o verifica si hay cambios de publicación."
        )
        return

    st.success(f"Detalle localizado: {url_detalle}")

    url_xlsx = encontrar_enlace_xlsx(url_detalle)
    if not url_xlsx:
        st.warning(
            "No se encontró un archivo .xlsx en el detalle. "
            "Es posible que la publicación sea PDF u otro formato."
        )
        return

    st.info(f"Archivo a descargar: {url_xlsx}")
    binario = descargar_binario(url_xlsx)
    if not binario:
        st.error("Fallo al descargar el archivo.")
        return

    nombre_sugerido = f"{tipo_sel}-{mes_sel}-{anio_sel}.xlsx"
    st.download_button(
        "Descargar Excel",
        data=binario,
        file_name=nombre_sugerido,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl-{tipo_sel}-{mes_sel}-{anio_sel}"
    )

    # Vista previa del Excel (si es legible)
    try:
        with io.BytesIO(binario) as bio:
            df_preview = pd.read_excel(bio, engine="openpyxl")
        st.subheader("Vista previa (primeras filas)")
        st.dataframe(df_preview.head(50), use_container_width=True)
    except Exception as e:
        st.warning(f"No fue posible mostrar vista previa del Excel: {e}")


if st.button("Buscar y descargar"):
    with st.spinner("Consultando el portal de BanRep…"):
        if descargar_ambos:
            # Descargar Repos y luego Deuda Externa para el mismo mes/año
            st.markdown("### Repos")
            flujo_descarga("haircuts-repos", mes_texto, year)

            st.markdown("---")
            st.markdown("### Deuda Externa")
            flujo_descarga("haircuts-deuda-externa", mes_texto, year)
        else:
            flujo_descarga(tipo, mes_texto, year)
