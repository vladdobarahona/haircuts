# -*- coding: utf-8 -*-
import io
import datetime as dt
import pandas as pd
import streamlit as st
from src.scraper import (
    listar_meses,
    construir_slug_detalle,
    encontrar_url_detalle_mensual,
    encontrar_enlace_xlsx,
    descargar_binario
)

st.set_page_config(page_title="Haircuts DCV (Repos & Deuda Externa)", page_icon="💼", layout="centered")
st.title("Haircuts DCV – Repos y Deuda Externa (BanRep)")

st.caption(
    "Fuente oficial: Banco de la República – Página que lista los haircuts mensuales "
    "(Repos BR y Deuda Externa)."
)
st.markdown(
    "[Ver página de listado](https://www.banrep.gov.co/es/sistemas-pago/dcv/haircuts-repos-deuda-externa)"
)

# Parámetros iniciales
hoy = dt.date.today()
meses = listar_meses()
years = list(range(2019, hoy.year + 1))  # según disponibilidad pública desde 2019
tipo = st.radio("Tipo de haircuts", ["haircuts-repos", "haircuts-deuda-externa"], horizontal=True)
col1, col2 = st.columns(2)
with col1:
    year = st.selectbox("Año", years, index=len(years) - 1)
with col2:
    mes_texto = st.selectbox("Mes (español)", [m["nombre_largo"] for m in meses],
                             index=hoy.month - 1)

# Acción
if st.button("Buscar y descargar"):
    with st.spinner("Consultando el portal de BanRep…"):
        # 1) Construir la ruta esperada (slug) del detalle mensual
        slug = construir_slug_detalle(tipo, mes_texto, year)

        # 2) Encontrar la URL de detalle desde la página de listado
        url_detalle = encontrar_url_detalle_mensual(slug)

        if not url_detalle:
            st.error("No se encontró la página de detalle para esos parámetros. "
                     "Prueba otro mes/año o verifica si hay cambios de publicación.")
        else:
            st.success(f"Detalle localizado: {url_detalle}")

            # 3) Dentro del detalle, localizar el enlace al .xlsx (o variantes)
            url_xlsx = encontrar_enlace_xlsx(url_detalle)
            if not url_xlsx:
                st.warning("No se encontró un archivo .xlsx en el detalle. "
                           "Es posible que la publicación sea PDF u otro formato.")
            else:
                st.info(f"Archivo a descargar: {url_xlsx}")
                binario = descargar_binario(url_xlsx)
                if not binario:
                    st.error("Fallo al descargar el archivo.")
                else:
                    nombre_sugerido = f"{tipo}-{mes_texto}-{year}.xlsx"
                    st.download_button(
                        "Descargar Excel",
                        data=binario,
                        file_name=nombre_sugerido,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    # Vista previa (si es un Excel legible)
                    try:
                        with io.BytesIO(binario) as bio:
                            df_preview = pd.read_excel(bio, engine="openpyxl")
                        st.subheader("Vista previa (primeras filas)")
                        st.dataframe(df_preview.head(50), use_container_width=True)
                    except Exception as e:
                        st.warning(f"No fue posible mostrar vista previa del Excel: {e}")
