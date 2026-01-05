# -*- coding: utf-8 -*-
import re
import requests
from bs4 import BeautifulSoup

LISTADO_URL = "https://www.banrep.gov.co/es/sistemas-pago/dcv/haircuts-repos-deuda-externa"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (haircuts-app; +https://github.com/tu-usuario/haircuts-app)"
}

def listar_meses():
    """Devuelve lista de dicts con nombres de meses en español."""
    meses = [
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
    return meses

def construir_slug_detalle(tipo: str, mes_largo: str, year: int) -> str:
    """
    Construye el slug esperado del detalle mensual en BanRep.
    Ej.: /es/sistemas-pago/dcv/haircuts-deuda-externa-enero-2026
    """
    return f"/es/sistemas-pago/dcv/{tipo}-{mes_largo}-{year}"

def _get_soup(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None

def encontrar_url_detalle_mensual(slug_detalle: str) -> str | None:
    """
    Desde la página de listado general, busca el <a> cuyo href contiene el slug.
    Devuelve la URL absoluta al detalle, si existe.
    """
    soup = _get_soup(LISTADO_URL)
    if not soup:
        return None
    # La tabla lista por año/mes las URLs a cada detalle (Repos/Deuda)  [1](https://www.banrep.gov.co/es/sistemas-pago/dcv/haircuts-repos-deuda-externa)
    anclas = soup.select("a[href]")
    for a in anclas:
        href = a.get("href", "")
        if slug_detalle in href:
            if href.startswith("http"):
                return href
            else:
                return "https://www.banrep.gov.co" + href
    # Fallback: intentar patrón sin guiones (por si el portal cambia el path)
    # (no estricto; sirve como red de seguridad)
    return None

def encontrar_enlace_xlsx(url_detalle: str) -> str | None:
    """
    En la página de detalle, encontrar <a> que apunte a /sites/default/files/... .xlsx
    Según documento de estructura, los adjuntos públicos se sirven bajo ese path.  [2](https://www.banrep.gov.co/es/sistemas-pago/dcv/estructura-archivo-emisiones-vigentes-haircuts)
    """
    soup = _get_soup(url_detalle)
    if not soup:
        return None

    # Regla primaria: .xlsx bajo /sites/default/files/
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "/sites/default/files/" in href and href.lower().endswith(".xlsx"):
            if href.startswith("http"):
                return href
            else:
                return "https://www.banrep.gov.co" + href

    # Fallback: admitir .xls o .csv si alguna publicación particular lo usa
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "/sites/default/files/" in href and re.search(r"\.(xls|csv)$", href, flags=re.I):
            return "https://www.banrep.gov.co" + href if not href.startswith("http") else href

    return None

def descargar_binario(url_archivo: str) -> bytes | None:
    try:
        r = requests.get(url_archivo, headers=HEADERS, timeout=60, stream=True)
        r.raise_for_status()
        return r.content
    except Exception:
        return None
