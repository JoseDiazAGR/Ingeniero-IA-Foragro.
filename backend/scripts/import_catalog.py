"""
Script para importar, limpiar y sincronizar el catálogo oficial de productos y
enfermedades de FORAGRO en PostgreSQL / Supabase.
Uso:
    python scripts/import_catalog.py [ruta_al_csv]
"""

import csv
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import get_db, init_db
from app.data.seed_catalog import INITIAL_DISEASE_REFERENCES

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def import_catalog(csv_path: Path):
    if not csv_path.exists():
        print(f"❌ Error: Archivo no encontrado en: {csv_path}")
        return False

    print(f"📖 Leyendo catálogo desde: {csv_path.name}...")

    products = []
    valid_skus = []
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            sku = (row.get("sku") or "").strip()
            nombre = (row.get("nombre") or "").strip()
            categoria = (row.get("categoria") or "").strip()
            if not sku or not nombre:
                continue

            try:
                precio = float(str(row.get("precio_hnl") or "0").replace(",", "").strip())
            except ValueError:
                precio = 0.0

            try:
                stock = int(float(str(row.get("stock") or "0").strip()))
            except ValueError:
                stock = 0

            imagen_url = (row.get("imagen_url") or "").strip()
            if imagen_url.startswith("https://www.foragro.com/images/productos/"):
                imagen_url = ""

            valid_skus.append(sku)
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
                "imagen_url": imagen_url,
            })

    print(f"📦 Total de productos oficiales procesados: {len(products)}")

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

    print("🚀 Sincronizando con PostgreSQL y limpiando registros obsoletos...")
    with get_db() as conn:
        # 1. Eliminar productos de prueba/obsoletos que no pertenecen al catálogo oficial
        if valid_skus:
            placeholders = ", ".join(["%s"] * len(valid_skus))
            cur_del = conn.execute(
                f"DELETE FROM products WHERE sku NOT IN ({placeholders})",
                tuple(valid_skus),
            )
            print(f"🧹 Productos obsoletos eliminados de BD: {cur_del.rowcount}")

        # 2. Upsert de los 38 productos oficiales
        for p in products:
            conn.execute(upsert_sql, p)

        # 3. Reemplazar referencias de enfermedades con las 18 verificadas
        conn.execute("DELETE FROM disease_references")
        for d in INITIAL_DISEASE_REFERENCES:
            conn.execute(
                """
                INSERT INTO disease_references (
                    cultivo, problema, nombre_enfermedad, nombre_cientifico,
                    descripcion_sintomas, foto_url, productos_recomendados_ids
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    d["cultivo"], d["problema"], d["nombre_enfermedad"], d["nombre_cientifico"],
                    d["descripcion_sintomas"], d["foto_url"], d["productos_recomendados_ids"],
                ),
            )

        conn.commit()

    print(f"✅ Sincronización exitosa: {len(products)} productos y {len(INITIAL_DISEASE_REFERENCES)} enfermedades verificadas.")
    return True


if __name__ == "__main__":
    default_csv = ROOT_DIR / "docs" / "catalogo_foragro_honduras.csv"
    target_csv = Path(sys.argv[1]) if len(sys.argv) > 1 else default_csv
    success = import_catalog(target_csv)
    sys.exit(0 if success else 1)
