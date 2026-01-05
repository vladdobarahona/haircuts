
# Haircuts DCV – Streamlit

App en Streamlit para consultar y descargar los Haircuts mensuales del DCV (Repos BR y Deuda Externa) publicados por el Banco de la República.

- Listado oficial: https://www.banrep.gov.co/es/sistemas-pago/dcv/haircuts-repos-deuda-externa
- Cambios en estructura/nombres de archivo (v1.03 2024-01-09): https://www.banrep.gov.co/es/sistemas-pago/dcv/estructura-archivo-emisiones-vigentes-haircuts

## Ejecutar local
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
