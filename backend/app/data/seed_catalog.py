"""
Catálogo oficial FORAGRO Honduras y referencias fitosanitarias para ChatAgro POP.
Carga los 38 productos oficiales desde docs/catalogo_foragro_honduras.csv y las
18 enfermedades/plagas prioritarias de Honduras con fotografías reales verificadas.
"""

import csv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
PRODUCTS_CSV = ROOT_DIR / "docs" / "catalogo_foragro_honduras.csv"

INITIAL_DISEASE_REFERENCES = [
    # ---- 1. CAFÉ ----
    {
        "cultivo": "Café",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Roya del Café",
        "nombre_cientifico": "Hemileia vastatrix",
        "descripcion_sintomas": "Polvillo amarillo-anaranjado (uredosporas) en el envés de las hojas. En el haz se observan manchas cloróticas amarillentas que luego se necrosan, provocando defoliación severa y paloteo.",
        "foto_url": "/shared/img/diseases/roya_cafe.jpg",
        "productos_recomendados_ids": "Iman Ultra 37.5 SC, Vertigo 32.5 SC, Halt 10 SC, Oxicloruro 50 WP",
    },
    {
        "cultivo": "Café",
        "problema": "Plagas",
        "nombre_enfermedad": "Broca del Café",
        "nombre_cientifico": "Hypothenemus hampei",
        "descripcion_sintomas": "Pequeño escarabajo negro que perfora un orificio circular de 1 mm en la corona o disco del fruto del café. Genera polvillo de aserrín en la entrada, pudrición interna y caída del grano.",
        "foto_url": "/shared/img/diseases/broca_cafe.jpg",
        "productos_recomendados_ids": "Forafos 48 EC",
    },
    {
        "cultivo": "Café",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Ojo de Gallo",
        "nombre_cientifico": "Mycena citricolor",
        "descripcion_sintomas": "Manchas circulares bien delimitadas color castaño claro a blanquecino en hojas y frutos, donde crecen pequeños filamentos amarillos con cabecita ('gemas'). Causa defoliación intensa en zonas altas y húmedas.",
        "foto_url": "/shared/img/diseases/ojo_de_gallo.jpg",
        "productos_recomendados_ids": "Halt 10 SC, Kalex Cu, Oxicloruro 50 WP",
    },
    {
        "cultivo": "Café",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Mancha de Hierro",
        "nombre_cientifico": "Cercospora coffeicola",
        "descripcion_sintomas": "Lesiones circulares necróticas café rojizo con centro grisáceo y un halo amarillo muy marcado en hojas, o manchas hundidas oscuras en cerezas que adhieren la pulpa al pergamino.",
        "foto_url": "/shared/img/diseases/mancha_hierro.jpg",
        "productos_recomendados_ids": "Mancozeb 80 WP, Pilarstin 50 WP, Iman Ultra 37.5 SC",
    },
    # ---- 2. MAÍZ ----
    {
        "cultivo": "Maíz",
        "problema": "Plagas",
        "nombre_enfermedad": "Gusano Cogollero",
        "nombre_cientifico": "Spodoptera frugiperda",
        "descripcion_sintomas": "Larva que raspa las hojas tiernas dejando 'ventanas' translúcidas y luego perfora el cogollo central dejando abundante excremento húmedo parecido al aserrín.",
        "foto_url": "/shared/img/diseases/gusano_cogollero.jpg",
        "productos_recomendados_ids": "Curagro 55 EC, Atrapa 44 EC, Kñon 40 SC, Brújula 5 WG",
    },
    {
        "cultivo": "Maíz",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Complejo Mancha de Asfalto",
        "nombre_cientifico": "Phyllachora maydis",
        "descripcion_sintomas": "Pequeños puntos negros brillantes y abultados (estromas similares a salpicaduras de brea o alquitrán) sobre las hojas verdes que se rodean de un halo necrótico pajizo ('ojo de pescado') y secan la planta.",
        "foto_url": "/shared/img/diseases/mancha_asfalto.jpg",
        "productos_recomendados_ids": "Vertigo 32.5 SC, Halt 10 SC, Urgente 50 WG",
    },
    {
        "cultivo": "Maíz",
        "problema": "Plagas",
        "nombre_enfermedad": "Gallina Ciega",
        "nombre_cientifico": "Phyllophaga spp.",
        "descripcion_sintomas": "Larvas blancas en forma de 'C' con cabeza café y tres pares de patas torácicas en el suelo. Devoran las raíces provocando amarillamiento, enanismo y acame (vuelco) de las plantas de maíz.",
        "foto_url": "/shared/img/diseases/gallina_ciega.jpg",
        "productos_recomendados_ids": "Forabufos 10 GR, Defiende Plus 54 FS, Forafos 48 EC",
    },
    # ---- 3. FRIJOL ----
    {
        "cultivo": "Frijol",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Antracnosis del Frijol",
        "nombre_cientifico": "Colletotrichum lindemuthianum",
        "descripcion_sintomas": "Lesiones necróticas oscuras a lo largo de las nervaduras en el envés de la hoja y cancros circulares hundidos color café rojizo con borde oscuro en las vainas.",
        "foto_url": "/shared/img/diseases/antracnosis_frijol.jpg",
        "productos_recomendados_ids": "Vertigo 32.5 SC, Pilarstin 50 WP, Mancozeb 80 WP, Oxicloruro 50 WP",
    },
    {
        "cultivo": "Frijol",
        "problema": "Plagas",
        "nombre_enfermedad": "Babosa del Frijol",
        "nombre_cientifico": "Sarasinula plebeia",
        "descripcion_sintomas": "Molusco terrestre café-grisáceo sin concha que ataca de noche, cortando hipocótilos y devorando cotiledones y hojas tiernas recién germinadas, dejando rastros brillantes de baba.",
        "foto_url": "/shared/img/diseases/babosa_frijol.jpg",
        "productos_recomendados_ids": "Molux 6 GB",
    },
    {
        "cultivo": "Frijol",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Mancha Angular del Frijol",
        "nombre_cientifico": "Pseudocercospora griseola",
        "descripcion_sintomas": "Manchas necróticas cafés de bordes rectos y forma angular delimitadas por las venas secundarias de la hoja, acompañadas de amarillamiento y caída prematura del follaje.",
        "foto_url": "/shared/img/diseases/mancha_angular_frijol.jpg",
        "productos_recomendados_ids": "Vertigo 32.5 SC, Urgente 50 WG, Mancozeb 80 WP",
    },
    # ---- 4. TOMATE, PAPA Y CHILE ----
    {
        "cultivo": "Tomate",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Tizón Tardío",
        "nombre_cientifico": "Phytophthora infestans",
        "descripcion_sintomas": "Manchas irregulares de aspecto acuoso ('escaldado') en bordes y puntas de hojas que rápidamente se tornan café oscuro a negro, con vellosidad blanquecina en el envés y pudrición firme en frutos.",
        "foto_url": "/shared/img/diseases/tizon_tardio.jpg",
        "productos_recomendados_ids": "Forzate 72 WP, Padrino 18.7 DC, Foraxil CT 48 SC, Foraxil 240 EC",
    },
    {
        "cultivo": "Tomate",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Tizón Temprano",
        "nombre_cientifico": "Alternaria solani",
        "descripcion_sintomas": "Manchas necróticas café oscuro en hojas bajeras con anillos concéntricos muy marcados (en forma de tiro al blanco o 'diana') rodeadas de un halo amarillo intenso.",
        "foto_url": "/shared/img/diseases/tizon_temprano.jpg",
        "productos_recomendados_ids": "Escofor 23 SC, Foraxil CT 48 SC, Urgente 50 WG, Mancozeb 80 WP",
    },
    {
        "cultivo": "Tomate",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Moho Gris",
        "nombre_cientifico": "Botrytis cinerea",
        "descripcion_sintomas": "Pudrición blanda cubierta por un denso micelio y esporulación aterciopelada color gris parduzco sobre flores, tallos, pecíolos y frutos en condiciones de alta humedad.",
        "foto_url": "/shared/img/diseases/moho_gris.jpg",
        "productos_recomendados_ids": "Escofor 23 SC, Pilarstin 50 WP",
    },
    {
        "cultivo": "Tomate",
        "problema": "Plagas",
        "nombre_enfermedad": "Mosca Blanca",
        "nombre_cientifico": "Bemisia tabaci",
        "descripcion_sintomas": "Colonias de diminutos insectos blancos alados y ninfas translúcidas en el envés de las hojas. Succionan savia, secretan mielecilla y transmiten geminivirus (encrespamiento y mosaico amarillo).",
        "foto_url": "/shared/img/diseases/mosca_blanca.jpg",
        "productos_recomendados_ids": "Bolido 24 SC, Ztafor 20 SP, Abafor 1.8 EC, Atrapa 44 EC",
    },
    {
        "cultivo": "Tomate",
        "problema": "Plagas",
        "nombre_enfermedad": "Picudo del Chile y Solanáceas",
        "nombre_cientifico": "Anthonomus eugenii",
        "descripcion_sintomas": "Escarabajo pequeño gris oscuro a negro con pico largo curvado (rostro). Las hembras perforan botones florales y frutos tiernos donde las larvas se alimentan, causando caída masiva de flores y frutos.",
        "foto_url": "/shared/img/diseases/picudo_chile.jpg",
        "productos_recomendados_ids": "Pikudo 20 SC, Foramil 90 SP",
    },
    # ---- 5. PLÁTANO Y BANANO ----
    {
        "cultivo": "Plátano",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Sigatoka Negra",
        "nombre_cientifico": "Pseudocercospora fijiensis",
        "descripcion_sintomas": "Pizcas y estrías café rojizas paralelas a las venas secundarias que evolucionan a manchas negras alargadas con halo amarillo brillante, secando prematuramente las hojas funcionales.",
        "foto_url": "/shared/img/diseases/sigatoka_negra.jpg",
        "productos_recomendados_ids": "Iman Ultra 37.5 SC, Mancozeb 80 WP, Alfan 45 EC, Kalex Cu",
    },
    {
        "cultivo": "Plátano",
        "problema": "Plagas",
        "nombre_enfermedad": "Picudo Negro del Plátano",
        "nombre_cientifico": "Cosmopolites sordidus",
        "descripcion_sintomas": "Gorgojo negro de rostro curvo cuyas larvas perforan galerías oscuras dentro del cormo (cepa), debilitando el anclaje radicular, amarilleando hojas y provocando la caída de la planta con racimo.",
        "foto_url": "/shared/img/diseases/picudo_platano.jpg",
        "productos_recomendados_ids": "Pikudo 20 SC, Forabufos 10 GR, Forafos 48 EC",
    },
    # ---- 6. PASTOS Y GANADERÍA ----
    {
        "cultivo": "Otro",
        "problema": "Plagas",
        "nombre_enfermedad": "Salivazo de los Pastos",
        "nombre_cientifico": "Aeneolamia spp.",
        "descripcion_sintomas": "Chinche negra con bandas rojas/anaranjadas cuyas ninfas se cubren de espuma blanca ('saliva') en la base de los tallos del pasto. Inyecta toxinas que secan y queman el potrero.",
        "foto_url": "/shared/img/diseases/salivazo_pastos.jpg",
        "productos_recomendados_ids": "Forafos 48 EC, Cintanegra 2.5 EC",
    },
]


def load_initial_products() -> list:
    """Lee los 38 productos oficiales desde docs/catalogo_foragro_honduras.csv."""
    if not PRODUCTS_CSV.exists():
        return []
    products = []
    with open(PRODUCTS_CSV, mode="r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            sku = (row.get("sku") or "").strip()
            nombre = (row.get("nombre") or "").strip()
            if not sku or not nombre:
                continue
            products.append({
                "sku": sku,
                "nombre": nombre,
                "categoria": (row.get("categoria") or "").strip(),
                "ingrediente_activo": (row.get("ingrediente_activo") or "").strip(),
                "cultivos": (row.get("cultivos") or "").strip(),
                "problemas": (row.get("problemas") or "").strip(),
                "dosis": (row.get("dosis") or "").strip(),
                "precio_hnl": float(str(row.get("precio_hnl") or "0").replace(",", "").strip() or 0),
                "stock": int(float(str(row.get("stock") or "0").strip() or 0)),
                "unidad": (row.get("unidad") or "Unidad").strip(),
                "imagen_url": (row.get("imagen_url") or "").strip(),
                "descripcion": (row.get("descripcion") or "").strip(),
            })
    return products


INITIAL_PRODUCTS = load_initial_products()


def seed_database_if_empty(conn):
    """Inserta productos y referencias de enfermedades si las tablas están vacías."""
    cur = conn.execute("SELECT COUNT(*) AS cnt FROM products")
    count_prod = (cur.fetchone() or {}).get("cnt", 0)
    if count_prod == 0:
        for p in load_initial_products():
            conn.execute(
                """
                INSERT INTO products (
                    sku, nombre, categoria, ingrediente_activo,
                    cultivos, problemas, dosis, precio_hnl, stock,
                    unidad, imagen_url, descripcion
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    p["sku"], p["nombre"], p["categoria"], p["ingrediente_activo"],
                    p["cultivos"], p["problemas"], p["dosis"], p["precio_hnl"], p["stock"],
                    p["unidad"], p.get("imagen_url", ""), p.get("descripcion", ""),
                ),
            )

    cur2 = conn.execute("SELECT COUNT(*) AS cnt FROM disease_references")
    count_diseases = (cur2.fetchone() or {}).get("cnt", 0)
    if count_diseases == 0:
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

    cur3 = conn.execute("SELECT COUNT(*) AS cnt FROM users")
    count_users = (cur3.fetchone() or {}).get("cnt", 0)
    if count_users == 0:
        from app.security import hash_password
        admin_hash = hash_password("admin1234")
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            ("admin", admin_hash),
        )

    conn.commit()
