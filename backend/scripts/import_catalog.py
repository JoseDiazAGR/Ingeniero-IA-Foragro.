"""
Script para importar y sincronizar el catálogo oficial de FORAGRO desde CSV a PostgreSQL / Supabase.
Uso:
    python scripts/import_catalog.py [ruta_al_csv]
Por defecto busca: ../docs/catalogo_foragro_honduras.csv
"""

import csv
import os
import sys
from pathlib import Path

# Agregar directorio backend al sys.path para importar app
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import get_db, init_db
from app.config import logger


def import_catalog(csv_path: Path):
    if not csv_path.exists():
        print(f"❌ Error: Archivo no encontrado en: {csv_path}")
        return False

    print(f"📖 Leyendo catálogo desde: {csv_path.name}...")

    # Leer CSV con soporte utf-8 / utf-8-sig
    products = []
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            sku = (row.get("sku") or "").strip()
            nombre = (row.get("nombre") or "").strip()
            categoria = (row.get("categoria") or "").strip()
            if not sku or not nombre:
                print(f"⚠️ Fila {idx}: SKU o Nombre vacío. Omitiendo.")
                continue

            try:
                precio = float(str(row.get("precio_hnl") or "0").replace(",", "").strip())
            except ValueError:
                precio = 0.0

            try:
                stock = int(float(str(row.get("stock") or "0").strip()))
            except ValueError:
                stock = 0

            products.append({
                "sku": sku,
                "nombre": nombre,
                "categoria": categoria,
                "ingrediente_activo": (row.get("ingrediente_activo") or "").strip(),
                "cultivos": (row.get("cultivos") or "").strip(),
                "problemas": (row.get("problemas") or "").strip(),
                "dosis": (row.get("dosis") or "").strip(),
                "precio_hnl": precio,
                "stock": stock,
                "unidad": (row.get("unidad") or "Unidad").strip(),
                "descripcion": (row.get("descripcion") or "").strip(),
                "imagen_url": (row.get("imagen_url") or "").strip(),
            })

    print(f"📦 Total de productos procesados: {len(products)}")

    # Asegurar pool inicializado
    init_db()

    upsert_sql = """
    INSERT INTO products (
        sku, nombre, categoria, ingrediente_activo, cultivos, problemas,
        dosis, precio_hnl, stock, unidad, descripcion, imagen_url
    ) VALUES (
        %(sku)s, %(nombre)s, %(categoria)s, %(ingrediente_activo)s, %(cultivos)s, %(problemas)s,
        %(dosis)s, %(precio_hnl)s, %(stock)s, %(unidad)s, %(descripcion)s, %(imagen_url)s
    )
    ON CONFLICT (sku) DO UPDATE SET
        nombre = EXCLUDED.nombre,
        categoria = EXCLUDED.categoria,
        ingrediente_activo = EXCLUDED.ingrediente_activo,
        cultivos = EXCLUDED.cultivos,
        problemas = EXCLUDED.problemas,
        dosis = EXCLUDED.dosis,
        precio_hnl = EXCLUDED.precio_hnl,
        stock = EXCLUDED.stock,
        unidad = EXCLUDED.unidad,
        descripcion = EXCLUDED.descripcion,
        imagen_url = EXCLUDED.imagen_url;
    """

    print("🚀 Sincronizando con Supabase PostgreSQL...")
    inserted_count = 0
    with get_db() as conn:
        for p in products:
            conn.execute(upsert_sql, p)
            inserted_count += 1
        conn.commit()

    with get_db() as conn:
        total = conn.execute("SELECT count(*) as cnt FROM products").fetchone()["cnt"]

    print(f"✅ ¡Éxito! Sincronizados {inserted_count} productos.")
    print(f"📊 Total actual de productos en la base de datos: {total}")
    return True


if __name__ == "__main__":
    default_csv = ROOT_DIR / "docs" / "catalogo_foragro_honduras.csv"
    target_csv = Path(sys.argv[1]) if len(sys.argv) > 1 else default_csv
    import_catalog(target_csv)
