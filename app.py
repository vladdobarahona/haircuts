# Autor: Vladimir Alonso B. P. (para uso empresarial)

# -*- coding: utf-8 -*-
"""
Haircuts DCV – Repos y Deuda Externa (BanRep) • Streamlit
Descarga directa desde CloudFront con catálogo por mes/año (sin huecos) y reglas recientes.
Autor: vbarahona (refactor M365 Copilot)
Fecha: 2026-01-06

Cambios clave según tu listado:
- Catálogo completo por (tipo, año, mes) para evitar "excepciones" como huecos.
- Deuda Externa reciente:
  - 2024-enero..abril  → dcv-haircuts-deuda-externa-{mes}-{año}.pdf (con excepciones para enero y marzo).
  - 2024-mayo          → dcv-haircuts-deuda-externa-mayo-2024_0.xlsx (único con _0).
  - 2024-junio..diciembre → dcv-haircuts-deuda-externa-{mes}-{año}.xlsx.
  - 2025+ → haircuts-deuda-externa-{mes}-{año}.xlsx (base sin dcv-).
- Repos reciente:
  - 2024-mayo..diciembre → dcv-haircuts-repos-{mes}-{año}.xlsx.
  - 2025+ → haircuts-repos-{mes}-{año}.xlsx (base sin dcv-).
- Excepciones reales únicas (según tu listado).

Requisitos:
    pip install streamlit requests pandas openpyxl xlrd

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
    "<span style='color:#F59B1D; font-size:0.9em; font-family:\"Century Gothic\", sans-serif;'>"
    "Idea de web scrapping en selenium originada por Vladimir Barahona."
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
    """HEAD -> True si 200. En 405/403 intenta GET con stream para validar existencia."""
    try:
        r = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            return True
        # Algunos endpoints no soportan HEAD correctamente
        if r.status_code in (403, 404, 405):
            rg = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
            return rg.status_code == 200
        return False
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
# Construcción de catálogo por (tipo, año, mes)
# ------------------------------------------------------------------------------
def _dedup(seq):
    """Elimina duplicados preservando orden."""
    vistos = set()
    out = []
    for x in seq:
        if x not in vistos:
            out.append(x); vistos.add(x)
    return out

def _urls_legado_por_mes(tipo: str, anio: int, mes: str) -> list[str]:
    """
    Variantes 'legadas' preferidas por año:
    - Raíz y /paginas/ con 'Haircut' y 'Haircuts' en xlsx/xls.
    - Para deuda externa, también PDF en raíz y /paginas/ con HAIRCUT_{MES_UP}_{AÑO}.
    - Variantes con guion bajo: Haircut_{mes}_{año}.pdf y Haircuts_{mes} {año}.pdf.
    - Variante hispana: "Haircuts {MesCap} de {Año}.pdf" (raíz).
    """
    mes_l = mes.lower()
    mes_cap = mes_capitalizado(mes_l)
    mes_up = mes_mayus(mes_l)

    # Preferencias de extensión legada por año
    if anio in (2019, 2020):
        exts = ["xls"]
    elif anio in (2021, 2022, 2023, 2024):
        exts = ["xlsx", "xls"]
    else:
        exts = ["xlsx"]

    urls = []

    # PDFs y variantes específicas para deuda externa (prioridad primero)
    if tipo == "haircuts-deuda-externa":
        # HAIRCUT_{MES_UP}_{AÑO} en raíz y /paginas/
        for base_dir in [BASE_CLOUDFRONT, f"{BASE_CLOUDFRONT}/paginas"]:
            urls.append(f"{base_dir}/HAIRCUT_{mes_up}_{anio}.pdf")
            urls.append(f"{base_dir}/HAIRCUT_{mes_up}_{anio}.xls")
            urls.append(f"{base_dir}/HAIRCUT_{mes_up}_{anio}.xlsx")
        # Variantes con guion bajo y minúsculas + forma hispana
        urls.append(f"{BASE_CLOUDFRONT}/paginas/{quote(f'haircut_{mes_up}_{anio}.pdf')}")
        urls.append(f"{BASE_CLOUDFRONT}/{quote(f'Haircut_{mes_l}_{anio}.pdf')}")
        urls.append(f"{BASE_CLOUDFRONT}/{quote(f'Haircuts_{mes_l} {anio}.pdf')}")
        urls.append(f"{BASE_CLOUDFRONT}/{quote(f'Haircuts {mes_cap} de {anio}.pdf')}")

    # 'Haircut' / 'Haircuts' en raíz y /paginas/
    for prefix in ["Haircut", "Haircuts"]:
        for ext in exts:
            fname = f"{prefix} {mes_cap} {anio}.{ext}"
            urls.append(f"{BASE_CLOUDFRONT}/{quote(fname)}")
            urls.append(f"{BASE_CLOUDFRONT}/paginas/{quote(fname)}")

    return _dedup(urls)

def _urls_recientes_por_mes(tipo: str, anio: int, mes: str) -> list[str]:
    """
    Estructura 'reciente' (haircuts/dcv-haircuts) con reglas específicas:
      - DEUDA EXTERNA:
        * 2024-enero..abril  → solo .pdf (salvo excepciones explícitas listadas).
        * 2024-mayo          → solo _0.xlsx (exclusivo).
        * 2024-junio..diciembre → solo .xlsx (sin _0).
        * 2025+ → base 'haircuts-deuda-externa-{mes}-{año}.xlsx' (sin dcv-).
      - REPOS:
        * 2024-mayo..diciembre → base 'dcv-haircuts-repos-{mes}-{año}.xlsx'.
        * 2025+ → base 'haircuts-repos-{mes}-{año}.xlsx' (sin dcv-).
    """
    mes_l = mes.lower()
    tipo_slug = "deuda-externa" if tipo == "haircuts-deuda-externa" else "repos"

    if tipo == "haircuts-deuda-externa":
        if anio == 2024:
            base = f"{BASE_CLOUDFRONT}/dcv-haircuts-{tipo_slug}-{mes_l}-{anio}"
            if mes_l in {"enero", "febrero", "marzo", "abril"}:
                return [f"{base}.pdf"]
            if mes_l == "mayo":
                return [f"{base}_0.xlsx"]
            return [f"{base}.xlsx"]
        else:  # 2025+
            base = f"{BASE_CLOUDFRONT}/haircuts-{tipo_slug}-{mes_l}-{anio}"
            return [f"{base}.xlsx"]
    else:  # repos
        if anio == 2024:
            base = f"{BASE_CLOUDFRONT}/dcv-haircuts-{tipo_slug}-{mes_l}-{anio}"
            return [f"{base}.xlsx"]
        else:  # 2025+
            base = f"{BASE_CLOUDFRONT}/haircuts-{tipo_slug}-{mes_l}-{anio}"
            return [f"{base}.xlsx"]

# Excepciones verdaderamente únicas (siguen tu listado)
EXCEPCIONES_UNICAS: dict[tuple[str, int, str], list[str]] = {
    # --- Repos marzo 2024 (única estructura)
    ("haircuts-repos", 2024, "marzo"): [
        f"{BASE_CLOUDFRONT}/{quote('haircut2024-03-27.xls')}"
    ],
    # --- Deuda enero 2024 (xlsx en raíz)
    ("haircuts-deuda-externa", 2024, "enero"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut Enero 2024.xlsx')}"
    ],
    # --- Deuda marzo 2024 (pdf en raíz sin dcv)
    ("haircuts-deuda-externa", 2024, "marzo"): [
        f"{BASE_CLOUDFRONT}/haircuts-deuda-externa-marzo-2024.pdf"
    ],
    # --- Deuda agosto 2024 (xlsx con nombre de repos)
    ("haircuts-deuda-externa", 2024, "agosto"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircut-Repos-Agosto-2024.xlsx')}"
    ],
    # --- Deuda agosto 2021 (formato 'Mes de Año')
    ("haircuts-deuda-externa", 2021, "agosto"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircuts Agosto de 2021.pdf')}"
    ],
    # --- Deuda septiembre 2021 (formato 'Mes de Año')
    ("haircuts-deuda-externa", 2021, "septiembre"): [
        f"{BASE_CLOUDFRONT}/{quote('Haircuts Septiembre de 2021.pdf')}"
    ],
    # --- Deuda marzo 2022 (formato 'Marzo 2022-Haircuts Deuda Externa.pdf')
    ("haircuts-deuda-externa", 2022, "marzo"): [
        f"{BASE_CLOUDFRONT}/{quote('Marzo 2022-Haircuts Deuda Externa.pdf')}"
    ],
}

def _estructura_deseada(tipo: str, anio: int, mes: str) -> list[str]:
    """
    Devuelve la(s) estructura(s) deseada(s) por período:
    - Excepción única → solo esa.
    - 2025+ → reciente 'haircuts-...'.
    - 2024 mayo..dic → 'dcv-haircuts-...' según reglas arriba.
    - Resto → legados (para deuda, PDF primero).
    """
    key = (tipo, anio, mes.lower())
    if key in EXCEPCIONES_UNICAS:
        return EXCEPCIONES_UNICAS[key][:]

    # 2025 en adelante: nueva estructura para ambos tipos (base 'haircuts-')
    if anio >= 2025:
        return _urls_recientes_por_mes(tipo, anio, mes)

    # 2024: a partir de mayo predominan 'dcv-haircuts-...'
    if anio == 2024 and mes.lower() in {
        "mayo", "junio", "julio", "septiembre", "octubre", "noviembre", "diciembre"
    }:
        return _urls_recientes_por_mes(tipo, anio, mes)

    # Resto: patrones legados
    return _urls_legado_por_mes(tipo, anio, mes)

def construir_diccionario_completo(anio_min: int = 2019, anio_max: int | None = None) -> dict[tuple[str, int, str], list[str]]:
    """Construye el catálogo explicitando la(s) estructura(s) por cada (tipo, año, mes)."""
    if anio_max is None:
        anio_max = dt.date.today().year

    salida: dict[tuple[str, int, str], list[str]] = {}
    for anio in range(anio_min, anio_max + 1):
        for mes in MESES:
            for tipo in ["haircuts-repos", "haircuts-deuda-externa"]:
                salida[(tipo, anio, mes)] = _estructura_deseada(tipo, anio, mes)
    return salida

# Construcción del catálogo completo
EXCEPCIONES: dict[tuple[str, int, str], list[str]] = construir_diccionario_completo()
PREFILL_COMPLETO = True  # el catálogo está completo para (2019..hoy)

# ------------------------------------------------------------------------------
# Reglas (respaldo; se aplican solo si una clave no está prellenada o si se desea ampliar)
# ------------------------------------------------------------------------------
def candidatos_reglas(tipo: str, anio: int, mes: str) -> list[str]:
    """
    Reglas generales (solo respaldo). En este refactor, el catálogo está completo,
    por lo que raramente se usan.
    """
    urls: list[str] = []
    mes_l = mes.lower()
    mes_cap = mes_capitalizado(mes_l)
    mes_up = mes_mayus(mes_l)

    # 1) Regla reciente (alineada a _urls_recientes_por_mes)
    tipo_slug = "deuda-externa" if tipo == "haircuts-deuda-externa" else "repos"
    if tipo == "haircuts-deuda-externa":
        if anio == 2024:
            base_recent = f"{BASE_CLOUDFRONT}/dcv-haircuts-{tipo_slug}-{mes_l}-{anio}"
            if mes_l in {"enero", "febrero", "marzo", "abril"}:
                urls.append(f"{base_recent}.pdf")
            elif mes_l == "mayo":
                urls.append(f"{base_recent}_0.xlsx")
            else:
                urls.append(f"{base_recent}.xlsx")
        else:
            base_recent = f"{BASE_CLOUDFRONT}/haircuts-{tipo_slug}-{mes_l}-{anio}"
            urls.append(f"{base_recent}.xlsx")
    else:
        if anio == 2024:
            base_recent = f"{BASE_CLOUDFRONT}/dcv-haircuts-{tipo_slug}-{mes_l}-{anio}"
            urls.append(f"{base_recent}.xlsx")
        else:
            base_recent = f"{BASE_CLOUDFRONT}/haircuts-{tipo_slug}-{mes_l}-{anio}"
            urls.append(f"{base_recent}.xlsx")

    # 2) Patrones legados en raíz (sin /paginas/)
    for prefix in ["Haircut", "Haircuts"]:
        for ext in ["xlsx", "xls"]:
            fname = f"{prefix} {mes_cap} {anio}.{ext}"
            urls.append(f"{BASE_CLOUDFRONT}/{quote(fname)}")
    # Legados tipo HAIRCUT_ en raíz
    for ext in ["pdf", "xls", "xlsx"]:
        urls.append(f"{BASE_CLOUDFRONT}/HAIRCUT_{mes_up}_{anio}.{ext}")
    # Guion bajo / minúsculas en raíz
    urls.append(f"{BASE_CLOUDFRONT}/{quote(f'Haircut_{mes_l}_{anio}.pdf')}")
    urls.append(f"{BASE_CLOUDFRONT}/{quote(f'Haircuts_{mes_l} {anio}.pdf')}")
    urls.append(f"{BASE_CLOUDFRONT}/{quote(f'Haircuts {mes_cap} de {anio}.pdf')}")

    # 3) Patrones legados en /paginas/
    for prefix in ["Haircut", "Haircuts"]:
        for ext in ["xlsx", "xls", "pdf"]:
            fname = f"{prefix} {mes_cap} {anio}.{ext}"
            urls.append(f"{BASE_CLOUDFRONT}/paginas/{quote(fname)}")
    for ext in ["pdf", "xls", "xlsx"]:
        urls.append(f"{BASE_CLOUDFRONT}/paginas/HAIRCUT_{mes_up}_{anio}.{ext}")
        urls.append(f"{BASE_CLOUDFRONT}/paginas/{quote(f'haircut_{mes_up}_{anio}.{ext}')}")

    return _dedup(urls)

def construir_candidatos(tipo: str, anio: int, mes: str) -> list[str]:
    """Catálogo explícito primero; si no hay (o se desactiva prefill), reglas de respaldo."""
    key = (tipo, anio, mes.lower())
    vistos = set()
    cand = []

    if key in EXCEPCIONES:
        for u in EXCEPCIONES[key]:
            if u not in vistos:
                cand.append(u); vistos.add(u)
        if PREFILL_COMPLETO:
            return cand

    for u in candidatos_reglas(tipo, anio, mes):
        if u not in vistos:
            cand.append(u); vistos.add(u)

    return cand

def resolver_url(tipo: str, anio: int, mes: str) -> tuple[str | None, list[str]]:
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
    year = st.selectbox("Año", years, index=len(years) - 1)
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
                engine = "openpyxl" if ext == "xlsx" else "xlrd"
                df_preview = pd.read_excel(bio, engine=engine)
            st.subheader("Vista previa (primeras filas)")
            st.dataframe(df_preview.head(50), use_container_width=True)
        except Exception as e:
            st.warning(f"No fue posible mostrar vista previa del Excel: {e}")
    else:
        st.caption("Vista previa no disponible para archivos PDF u otros formatos.")

def flujo_batch(tipo_sel: str, anio_sel: int):
    meses_l = listar_meses()
    tipos = ["haircuts-repos", "haircuts-deuda-externa"] if tipo_sel == "ambos" else [tipo_sel]

    resultados = []
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for m in meses_l:
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
