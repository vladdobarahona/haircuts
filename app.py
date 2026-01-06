# Autor: Vladimir Alonso B. P. (para uso empresarial)
# -*- coding: utf-8 -*-
"""
Haircuts DCV – Repos y Deuda Externa (BanRep) • Streamlit (descarga directa con reglas + excepciones)
Autor: vbarahona
Fecha: 2026-01-05

Características:
- Sin Selenium. Descarga directa desde CloudFront con validación HEAD.
- Diccionario de EXCEPCIONES por (tipo, año, mes) — actualizado con nuevas entradas solicitadas.
- Reglas recientes (desde mayo 2024) + patrones legados (Haircut/Haircuts/HAIRCUT_).
- Modo batch con ZIP y tabla de resultados.
- Caption estilizado (#F59B1D + Century Gothic).

Requisitos:
    pip install streamlit requests pandas openpyxl

Ejecutar:
    streamlit run app.py
"""

import io
import zipfile
import datetime as dt
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

# ------------------------------------------------------------------------------
# Configuración de la página
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Haircuts DCV – BanRep", page_icon="💼", layout="centered")
st.title("Haircuts DCV – Repos y Deuda Externa (BanRep)")
st.caption("Descarga directa desde el repositorio oficial (CloudFront) del Banco de la República.")
st.markdown(
    "<span style='color:#F59B1D; font-size:0.5em; font-family:\"Century Gothic\", sans-serif;'>"
    "Creado por Copilot con base a idea de web scrapping en selenium originada por Vladimir Barahona."
    "</span>",
    unsafe_allow_html=True
)

# ------------------------------------------------------------------------------
# Constantes y utilidades
# ------------------------------------------------------------------------------
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

def validar_existencia(url: str, timeout: int = 15) -> bool:
    """HEAD -> True si 200."""
    try:
        r = requests.head(url, headers=HEADERS, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False

def descargar_binario(url: str, timeout: int = 30) -> bytes | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code == 200:
            return r.content
        return None
    except Exception:
        return None

def ext_from_url(url: str) -> str:
    low = url.lower()
    if ".xlsx" in low:
        return "xlsx"
    if ".xls" in low:
        return "xls"
    if ".pdf" in low:
        return "pdf"
    return "bin"

# ------------------------------------------------------------------------------
# EXCEPCIONES (según ejemplos provistos + entradas nuevas solicitadas)
# Clave: (tipo, año, mes) -> lista de URLs candidatas explícitas
# ------------------------------------------------------------------------------
EXCEPCIONES: dict[tuple[str, int, str], list[str]] = {
    # --- Repos (legados y varios) ---
    ("haircuts-repos", 2019, "enero"): [
        f"{BASE_CLOUDFRONT}/paginas/{quote('Haircut Enero 2019.xls')}"
    ],
    ("haircuts-repos", 2019, "febrero"): [
        f"{BASE_CLOUDFRONT}/paginas/{quote('Haircut Febrero 2019.xls')}"
    ],
    ("haircuts-repos", 2019, "mayo"): [
        f"{BASE_CLOUDFRONT}/paginas/{quote('Haircut Mayo 2019.xls')}"
    ],
    ("haircuts-repos", 2019, "octubre"): [
        f"{BASE_CLOUDFRONT}/paginas/{quote('Haircut Octubre 2019.xls')}"
    ],
    ("haircuts-repos", 2019, "diciembre"): [
        f"{BASE_CLOUDFRONT}/paginas/{quote('Haircut Diciembre 2019.xls')}"
    ],
    ("haircuts-repos", 2020, "enero"): [
        f"{BASE_CLOUDFRONT}/paginas/{quote('Haircut Enero 2020.xls')}"
    ],
    ("haircuts-repos", 2020, "septiembre"): [
        f"{BASE_CLOUDFRONT}/paginas/{quote('Haircut Septiembre 2020.xlsx')}"
    ],
    ("haircuts-repos", 2021, "septiembre"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut Septiembre 2021.xlsx')}"
    ],
    ("haircuts-repos", 2022, "diciembre"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut Diciembre 2022.xlsx')}"
    ],
    ("haircuts-repos", 2023, "enero"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut Enero 2023.xlsx')}"
    ],
    ("haircuts-repos", 2023, "octubre"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut Octubre 2023.xlsx')}"
    ],
    ("haircuts-repos", 2023, "diciembre"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut Diciembre 2023.xlsx')}"
    ],
    ("haircuts-repos", 2024, "enero"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut Enero 2024.xlsx')}"
    ],
    ("haircuts-repos", 2024, "febrero"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut Febrero 2024.xlsx')}"
    ],
    ("haircuts-repos", 2024, "marzo"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut Marzo 2024.xlsx')}",
        f"{BASE_CLOUDFRONT}/{quote('haircut2024-03-27.xls')}"
    ],
    ("haircuts-repos", 2024, "mayo"): [
        f"{BASE_CLOUDFRONT}/dcv-haircuts-repos-mayo-2024.xlsx"
    ],
    ("haircuts-repos", 2024, "septiembre"): [
        f"{BASE_CLOUDFRONT}/dcv-haircuts-repos-septiembre-2024.xlsx"
    ],
    ("haircuts-repos", 2024, "octubre"): [
        f"{BASE_CLOUDFRONT}/dcv-haircuts-repos-octubre-2024.xlsx"
    ],
    # --- NUEVAS entradas solicitadas (repos) ---
    ("haircuts-repos", 2024, "diciembre"): [
        f"{BASE_CLOUDFRONT}/dcv-haircuts-repos-diciembre-2024.xlsx"
    ],
    ("haircuts-repos", 2025, "enero"): [
        f"{BASE_CLOUDFRONT}/haircuts-repos-enero-2025.xlsx"
    ],
    ("haircuts-repos", 2025, "diciembre"): [
        f"{BASE_CLOUDFRONT}/haircuts-repos-diciembre-2025.xlsx"
    ],
    ("haircuts-repos", 2026, "enero"): [
        f"{BASE_CLOUDFRONT}/haircuts-repos-enero-2026.xlsx"
    ],

    # --- Deuda externa (legados y varios) ---
    ("haircuts-deuda-externa", 2019, "enero"): [
        f"{BASE_CLOUDFRONT}/paginas/HAIRCUT_ENERO_2019.pdf"
    ],
    ("haircuts-deuda-externa", 2019, "febrero"): [
        f"{BASE_CLOUDFRONT}/paginas/HAIRCUT_FEBRERO_2019.pdf",
        f"{BASE_CLOUDFRONT}/paginas/{quote('Haircuts_Febrero.pdf')}"
    ],
    ("haircuts-deuda-externa", 2019, "marzo"): [
        f"{BASE_CLOUDFRONT}/paginas/HAIRCUT_MARZO_2019.pdf"
    ],
    ("haircuts-deuda-externa", 2019, "abril"): [
        f"{BASE_CLOUDFRONT}/paginas/{quote('Haircuts Abril 2019.pdf')}"
    ],
    ("haircuts-deuda-externa", 2019, "mayo"): [
        f"{BASE_CLOUDFRONT}/paginas/haircuts_mayo_0.pdf"
    ],
    ("haircuts-deuda-externa", 2019, "junio"): [
        f"{BASE_CLOUDFRONT}/paginas/Haircuts_Junio.pdf"
    ],
    ("haircuts-deuda-externa", 2019, "noviembre"): [
        f"{BASE_CLOUDFRONT}/paginas/haircut_nov.pdf"
    ],
    ("haircuts-deuda-externa", 2019, "diciembre"): [
        f"{BASE_CLOUDFRONT}/paginas/Haircuts_dic.pdf"
    ],
    ("haircuts-deuda-externa", 2021, "octubre"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut Octubre 2021.xls')}"
    ],
    ("haircuts-deuda-externa", 2023, "octubre"): [
        f"{BASE_CLOUDFRONT}/HAIRCUT_OCTUBRE_2023.pdf"
    ],
    ("haircuts-deuda-externa", 2023, "diciembre"): [
        f"{BASE_CLOUDFRONT}/HAIRCUT_DICIEMBRE_2023.pdf"
    ],
    ("haircuts-deuda-externa", 2024, "enero"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut Enero 2024.xlsx')}"
    ],
    ("haircuts-deuda-externa", 2024, "febrero"): [
        f"{BASE_CLOUDFRONT}/HAIRCUT_FEBRERO_2024.pdf"
    ],
    ("haircuts-deuda-externa", 2024, "abril"): [
        f"{BASE_CLOUDFRONT}/dcv-haircuts-deuda-externa-abril-2024.pdf"
    ],
    ("haircuts-deuda-externa", 2024, "mayo"): [
        f"{BASE_CLOUDFRONT}/dcv-haircuts-deuda-externa-mayo-2024_0.xlsx"
    ],
    ("haircuts-deuda-externa", 2024, "junio"): [
        f"{BASE_CLOUDFRONT}/dcv-haircuts-deuda-externa-junio-2024.xlsx"
    ],
    ("haircuts-deuda-externa", 2024, "septiembre"): [
        f"{BASE_CLOUDFRONT}/dcv-haircuts-deuda-externa-septiembre-2024.xlsx"
    ],
    ("haircuts-deuda-externa", 2024, "octubre"): [
        f"{BASE_CLOUDFRONT}/dcv-haircuts-deuda-externa-octubre-2024.xlsx"
    ],
    # --- NUEVAS entradas solicitadas (deuda externa) ---
    ("haircuts-deuda-externa", 2024, "diciembre"): [
        f"{BASE_CLOUDFRONT}/dcv-haircuts-deuda-externa-diciembre-2024.xlsx"
    ],
    ("haircuts-deuda-externa", 2025, "enero"): [
        f"{BASE_CLOUDFRONT}/haircuts-deuda-externa-enero-2025.xlsx"
    ],
}

# ------------------------------------------------------------------------------
# Reglas (generación de candidatos, además de las excepciones)
# ------------------------------------------------------------------------------
def candidatos_reglas(tipo: str, anio: int, mes: str) -> list[str]:
    """
    Devuelve una lista de posibles URLs construidas por reglas generales:
      1) Regla reciente (aprox. mayo 2024 en adelante): dcv-haircuts-{tipo}-{mes}-{año}.xlsx
         - Se agrega también variante '_0.xlsx' y '.pdf' como respaldo.
      2) Patrones legados:
         - (raíz y /paginas/) Haircut/Haircuts {MesCap} {Año}.xlsx|.xls
         - /paginas/ HAIRCUT_{MES_UP}_{AÑO}.pdf + variantes Excel
    Orden de prioridad: reciente, luego legados.
    """
    urls: list[str] = []
    mes_l = mes.lower()
    mes_cap = mes_capitalizado(mes_l)
    mes_up = mes_mayus(mes_l)

    # 1) Regla reciente (aplica probable 2024-mayo+)
    tipo_slug = "deuda-externa" if tipo == "haircuts-deuda-externa" else "repos"
    base_recent = f"{BASE_CLOUDFRONT}/dcv-haircuts-{tipo_slug}-{mes_l}-{anio}"
    urls += [
        f"{base_recent}.xlsx",
        f"{base_recent}_0.xlsx",   # algunos meses traen sufijo _0
        f"{base_recent}.pdf",
    ]

    # 2) Patrones legados en raíz (sin /paginas/)
    for prefix in ["Haircut", "Haircuts"]:
        for ext in ["xlsx", "xls"]:
            fname = f"{prefix} {mes_cap} {anio}.{ext}"
            urls.append(f"{BASE_CLOUDFRONT}/{quote(fname)}")

    # 3) Patrones legados en /paginas/
    for prefix in ["Haircut", "Haircuts"]:
        for ext in ["xlsx", "xls", "pdf"]:
            fname = f"{prefix} {mes_cap} {anio}.{ext}"
            urls.append(f"{BASE_CLOUDFRONT}/paginas/{quote(fname)}")

    # 4) HAIRCUT_{MES_UP}_{AÑO} (PDF y Excel) en /paginas/
    for ext in ["pdf", "xls", "xlsx"]:
        fname = f"HAIRCUT_{mes_up}_{anio}.{ext}"
        urls.append(f"{BASE_CLOUDFRONT}/paginas/{quote(fname)}")
        # Variante minúscula
        urls.append(f"{BASE_CLOUDFRONT}/paginas/{quote(f'haircut_{mes_up}_{anio}.{ext}')}")
    return urls

def construir_candidatos(tipo: str, anio: int, mes: str) -> list[str]:
    """Excepciones primero; si no hay, aplica reglas. Elimina duplicados preservando orden."""
    key = (tipo, anio, mes.lower())
    vistos = set()
    cand = []

    # 1) Excepciones explícitas
    if key in EXCEPCIONES:
        for u in EXCEPCIONES[key]:
            if u not in vistos:
                cand.append(u); vistos.add(u)

    # 2) Reglas generales
    for u in candidatos_reglas(tipo, anio, mes):
        if u not in vistos:
            cand.append(u); vistos.add(u)

    return cand

def resolver_url(tipo: str, anio: int, mes: str) -> tuple[str|None, list[str]]:
    """Devuelve (primera_url_existente, lista_candidatos_generados) usando HEAD."""
    cand = construir_candidatos(tipo, anio, mes)
    for u in cand:
        if validar_existencia(u):
            return u, cand
    return None, cand

# ------------------------------------------------------------------------------
# Interfaz
# ------------------------------------------------------------------------------
hoy = dt.date.today()
years = list(range(2019, hoy.year + 1))

tipo = st.radio("Tipo de haircuts", ["haircuts-repos", "haircuts-deuda-externa", "ambos"], horizontal=True)
col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("Año", years, index=len(years)-1)
with col2:
    mes = st.selectbox("Mes", listar_meses(), index=hoy.month - 1)

modo_batch = st.checkbox("Modo batch: listar todos los meses del año (según tipo seleccionado)")

# ------------------------------------------------------------------------------
# Funciones principales
# ------------------------------------------------------------------------------
def flujo_unico(tipo_sel: str, anio_sel: int, mes_sel: str):
    url, cand = resolver_url(tipo_sel, anio_sel, mes_sel)
    with st.expander("Diagnóstico: candidatos generados (en orden de validación)"):
        st.dataframe(pd.DataFrame({"URL candidata": cand}), use_container_width=True)

    if not url:
        st.error("No se encontró ningún archivo con los patrones disponibles.")
        return

    st.success(f"Archivo encontrado: {url}")
    data = descargar_binario(url)
    if not data:
        st.error("Fallo en la descarga (GET).")
        return

    ext = ext_from_url(url)
    nombre = f"{tipo_sel}-{mes_sel}-{anio_sel}.{ext}"
    st.download_button(
        f"Descargar {ext.upper()}",
        data=data,
        file_name=nombre,
        mime="application/octet-stream",
        key=f"dl-{tipo_sel}-{mes_sel}-{anio_sel}"
    )

    if ext in ["xlsx", "xls"]:
        try:
            with io.BytesIO(data) as bio:
                df_preview = pd.read_excel(bio, engine="openpyxl")
            st.subheader("Vista previa (primeras filas)")
            st.dataframe(df_preview.head(50), use_container_width=True)
        except Exception as e:
            st.warning(f"No fue posible mostrar vista previa del Excel: {e}")
    else:
        st.caption("Vista previa no disponible para archivos PDF u otros formatos.")

def flujo_batch(tipo_sel: str, anio_sel: int):
    meses = listar_meses()
    tipos = ["haircuts-repos", "haircuts-deuda-externa"] if tipo_sel == "ambos" else [tipo_sel]

    resultados = []
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for m in meses:
            for t in tipos:
                url, _ = resolver_url(t, anio_sel, m)
                if url:
                    data = descargar_binario(url)
                    if data:
                        ext = ext_from_url(url)
                        nombre = f"{t}-{m}-{anio_sel}.{ext}"
                        zf.writestr(nombre, data)
                        resultados.append({"Mes": m, "Tipo": t, "Estado": "Disponible", "URL": url})
                    else:
                        resultados.append({"Mes": m, "Tipo": t, "Estado": "Error de descarga", "URL": url})
                else:
                    resultados.append({"Mes": m, "Tipo": t, "Estado": "No disponible", "URL": None})

    st.subheader(f"Resultados – {anio_sel}")
    st.dataframe(pd.DataFrame(resultados), use_container_width=True)
    st.download_button(
        "Descargar ZIP con archivos disponibles",
        data=zip_buf.getvalue(),
        file_name=f"haircuts-{anio_sel}.zip",
        mime="application/zip",
        key=f"zip-{tipo_sel}-{anio_sel}"
    )

# ------------------------------------------------------------------------------
# Acción
# ------------------------------------------------------------------------------
if st.button("Buscar y descargar"):
    with st.spinner("Procesando…"):
        if modo_batch:
            flujo_batch(tipo, year)
        else:
            if tipo == "ambos":
                st.markdown("### Repos")
                flujo_unico("haircuts-repos", year, mes)
                st.markdown("---")
                st.markdown("### Deuda Externa")
                flujo_unico("haircuts-deuda-externa", year, mes)
            else:
                flujo_unico(tipo, year, mes)
