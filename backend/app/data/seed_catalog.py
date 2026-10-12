"""
Catálogo oficial FORAGRO Honduras y referencias de enfermedades para ChatAgro POP.
Datos iniciales para SQLite con productos, stock en bodega, precios en HNL (Lempiras),
dosis de aplicación e imágenes de referencia de enfermedades comunes.
"""

INITIAL_PRODUCTS = [
    # ---- Fungicidas ----
    {
        "sku": "FOR-FUN-001",
        "nombre": "Oxicloruro FORAGRO 50 WP",
        "categoria": "Fungicida",
        "ingrediente_activo": "Oxicloruro de Cobre 50%",
        "cultivos": "Café, Tomate, Frijol, Plátano",
        "problemas": "Roya, Antracnosis, Mancha Foliar, Tizón Temprano",
        "dosis": "1.5 a 2.0 kg/manzana (30-40 g por bomba de 16L)",
        "precio_hnl": 320.00,
        "stock": 45,
        "unidad": "Bolsa 1 Kg",
        "imagen_url": "oxicloruro_50wp.png",
        "descripcion": "Fungicida cúprico preventivo de amplio espectro. Excelente adherencia y resistencia al lavado por lluvia en zonas de alta humedad.",
    },
    {
        "sku": "FOR-FUN-002",
        "nombre": "Mancozeb FORAGRO 80 WP",
        "categoria": "Fungicida",
        "ingrediente_activo": "Mancozeb 80%",
        "cultivos": "Café, Maíz, Tomate, Frijol, Plátano",
        "problemas": "Roya, Tizón Tardío, Mancha Foliar, Sigatoka",
        "dosis": "1.5 a 2.5 kg/manzana (50 g por bomba de 16L)",
        "precio_hnl": 285.00,
        "stock": 60,
        "unidad": "Bolsa 1 Kg",
        "imagen_url": "mancozeb_80wp.png",
        "descripcion": "Fungicida multisitio protector. Aporta micronutrientes zinc y manganeso que vigorizan el follaje y previenen resistencia.",
    },
    {
        "sku": "FOR-FUN-003",
        "nombre": "Fosetyl-Al FORAGRO 80 WG",
        "categoria": "Fungicida",
        "ingrediente_activo": "Fosetil Aluminio 80%",
        "cultivos": "Café, Cacao, Tomate, Plátano",
        "problemas": "Phytophthora, Mal de hilachas, Pudrición radicular",
        "dosis": "1.0 a 1.5 kg/manzana en drench o foliar",
        "precio_hnl": 490.00,
        "stock": 28,
        "unidad": "Bolsa 1 Kg",
        "imagen_url": "fosetyl_80wg.png",
        "descripcion": "Fungicida sistémico completo con movimiento ascendente y descendente (acrópeto y basípeto). Estimula las defensas naturales (fitoalexinas).",
    },
    {
        "sku": "FOR-FUN-004",
        "nombre": "Benomyl FORAGRO 50 WP",
        "categoria": "Fungicida",
        "ingrediente_activo": "Benomilo 50%",
        "cultivos": "Frijol, Tomate, Plátano, Café",
        "problemas": "Antracnosis, Sigatoka, Ojo de Gallo, Moho blanco",
        "dosis": "0.5 a 0.8 kg/manzana",
        "precio_hnl": 395.00,
        "stock": 35,
        "unidad": "Bolsa 500 g",
        "imagen_url": "benomyl_50wp.png",
        "descripcion": "Fungicida curativo y preventivo con acción sistémica. Control rápido de hongos ascomicetos y deuteromicetos.",
    },
    {
        "sku": "FOR-FUN-005",
        "nombre": "Azoxystrobin FORAGRO 25 SC",
        "categoria": "Fungicida",
        "ingrediente_activo": "Azoxistrobina 250 g/L",
        "cultivos": "Café, Maíz, Tomate, Frijol",
        "problemas": "Roya, Mancha de asfalto, Tizón temprano",
        "dosis": "250 a 350 cc/manzana",
        "precio_hnl": 580.00,
        "stock": 20,
        "unidad": "Frasco 1 Litro",
        "imagen_url": "azoxy_25sc.png",
        "descripcion": "Estrobirulina sistémica de última generación con potente efecto reverdeciente (efecto greening) y alta persistencia foliar.",
    },

    # ---- Insecticidas ----
    {
        "sku": "FOR-INS-001",
        "nombre": "Clorantraniliprole 20 SC",
        "categoria": "Insecticida",
        "ingrediente_activo": "Clorantraniliprol 200 g/L",
        "cultivos": "Maíz, Tomate, Frijol",
        "problemas": "Gusano Cogollero, Barrenador, Tuta absoluta, Cogollero",
        "dosis": "75 a 100 cc/manzana (15-20 cc por bomba)",
        "precio_hnl": 620.00,
        "stock": 50,
        "unidad": "Frasco 250 cc",
        "imagen_url": "clorantra_20sc.png",
        "descripcion": "Insecticida modulador de receptores de rianodina. Máxima eficacia contra cogollero del maíz, seguro para fauna benéfica y bajo período de reingreso.",
    },
    {
        "sku": "FOR-INS-002",
        "nombre": "Imidacloprid FORAGRO 35 SC",
        "categoria": "Insecticida",
        "ingrediente_activo": "Imidacloprid 350 g/L",
        "cultivos": "Café, Tomate, Frijol, Plátano",
        "problemas": "Broca del café, Mosca Blanca, Pulgones, Picudo, Trips",
        "dosis": "200 a 300 cc/manzana",
        "precio_hnl": 440.00,
        "stock": 40,
        "unidad": "Frasco 500 cc",
        "imagen_url": "imida_35sc.png",
        "descripcion": "Neonicotinoide sistémico de alta absorción radicular y foliar. Protección prolongada contra insectos chupadores y raspadores.",
    },
    {
        "sku": "FOR-INS-003",
        "nombre": "Tiametoxam + Lambda 30 WG",
        "categoria": "Insecticida",
        "ingrediente_activo": "Tiametoxam 141 g/kg + Lambda Cihalotrina 106 g/kg",
        "cultivos": "Maíz, Frijol, Tomate",
        "problemas": "Gusano cogollero, Trips, Mosca blanca, Tortuguilla",
        "dosis": "100 a 150 g/manzana",
        "precio_hnl": 380.00,
        "stock": 30,
        "unidad": "Bolsa 250 g",
        "imagen_url": "tiametoxam_lambda.png",
        "descripcion": "Doble modo de acción: choque inmediato (knock-down) y residualidad sistémica en el tejido nuevo de la planta.",
    },
    {
        "sku": "FOR-INS-004",
        "nombre": "Beauveria Bassiana Bio-Agro",
        "categoria": "Bio-Insecticida",
        "ingrediente_activo": "Beauveria bassiana cepa BB-01 (1x10^9 conidios/g)",
        "cultivos": "Café, Maíz, Plátano",
        "problemas": "Broca del café, Picudo negro, Mosca blanca",
        "dosis": "1.0 kg/manzana en horas de baja radiación solar",
        "precio_hnl": 310.00,
        "stock": 25,
        "unidad": "Bolsa 1 Kg",
        "imagen_url": "beauveria_bio.png",
        "descripcion": "Control biológico entomopatógeno certificado. Ideal para manejo integrado de plagas (MIP) y fincas con certificación orgánica o Rainforest.",
    },

    # ---- Fertilizantes y Bioestimulantes ----
    {
        "sku": "FOR-FER-001",
        "nombre": "FertiPlus Foliar 20-20-20 + ME",
        "categoria": "Fertilizante Foliar",
        "ingrediente_activo": "N 20%, P2O5 20%, K2O 20% + Microelementos Quelatados",
        "cultivos": "Café, Maíz, Frijol, Tomate, Plátano",
        "problemas": "Nutrición general, Clorosis, Estimulación vegetativa",
        "dosis": "1.0 a 1.5 kg/manzana",
        "precio_hnl": 190.00,
        "stock": 70,
        "unidad": "Bolsa 1 Kg",
        "imagen_url": "fertiplus_202020.png",
        "descripcion": "Nutrición balanceada 100% soluble con magnesio, boro, zinc y hierro. Rápida recuperación post-cosecha o estrés hídrico.",
    },
    {
        "sku": "FOR-BIO-001",
        "nombre": "RaizMax Bioestimulante Radicular",
        "categoria": "Bioestimulante",
        "ingrediente_activo": "Extracto de algas Ascophyllum nodosum + Ácidos Húmicos 15%",
        "cultivos": "Café, Maíz, Tomate, Frijol, Plátano",
        "problemas": "Suelo pobre, Enraizamiento lento, Estrés post-trasplante",
        "dosis": "1.0 Litro/manzana en drench o primera fertilización",
        "precio_hnl": 360.00,
        "stock": 38,
        "unidad": "Frasco 1 Litro",
        "imagen_url": "raizmax_1l.png",
        "descripcion": "Potenciador del sistema radicular. Aumenta la masa de raíces secundarias y pelos absorbentes para maximizar absorción de fertilizantes.",
    },
    {
        "sku": "FOR-ENM-001",
        "nombre": "Cal Dolomítica Mejorada FORAGRO",
        "categoria": "Enmienda de Suelo",
        "ingrediente_activo": "Carbonato de Calcio 55% + Carbonato de Magnesio 35%",
        "cultivos": "Café, Maíz, Frijol, Plátano",
        "problemas": "Acidez de suelo, Bloqueo de fósforo, Deficiencia de magnesio",
        "dosis": "10 a 20 quintales/manzana según análisis de suelo",
        "precio_hnl": 130.00,
        "stock": 120,
        "unidad": "Saco 100 Lbs",
        "imagen_url": "cal_dolomitica.png",
        "descripcion": "Corrector de pH ácido para suelos cafetaleros y de ladera en Honduras. Desbloquea nutrientes fijados en el suelo.",
    },
    {
        "sku": "FOR-SEM-001",
        "nombre": "Semilla Maíz Híbrido H-27 Certificada",
        "categoria": "Semillas",
        "ingrediente_activo": "Zea mays híbrido blanco de alto rendimiento",
        "cultivos": "Maíz",
        "problemas": "Bajo rendimiento, Vuelco por viento, Susceptibilidad a sequía",
        "dosis": "1 bolsa (60,000 semillas) por manzana",
        "precio_hnl": 1450.00,
        "stock": 18,
        "unidad": "Bolsa 60k semillas",
        "imagen_url": "semilla_h27.png",
        "descripcion": "Semilla adaptada al corredor seco y valles de Honduras. Gran mazorca con excelente cobertura de tusa y tolerancia a sequía.",
    }
]

INITIAL_DISEASE_REFERENCES = [
    {
        "cultivo": "Café",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Roya del Café",
        "nombre_cientifico": "Hemileia vastatrix",
        "descripcion_sintomas": "Polvillo amarillo o anaranjado en el envés de las hojas adultas. En el haz se observan manchas amarillentas cloróticas que luego se necrosan, provocando defoliación severa.",
        "foto_url": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&auto=format&fit=crop&q=80",
        "productos_recomendados_ids": "Oxicloruro FORAGRO 50 WP, Mancozeb FORAGRO 80 WP, Azoxystrobin FORAGRO 25 SC"
    },
    {
        "cultivo": "Café",
        "problema": "Plagas",
        "nombre_enfermedad": "Broca del Café",
        "nombre_cientifico": "Hypothenemus hampei",
        "descripcion_sintomas": "Pequeño orificio redondo (1 mm) en la corona o disco del fruto maduro o verde. Presencia de aserrín oscuro en la entrada del fruto. Causa caída y pérdida de peso del grano.",
        "foto_url": "https://images.unsplash.com/photo-1611080626919-7cf5a9dbab5b?w=600&auto=format&fit=crop&q=80",
        "productos_recomendados_ids": "Beauveria Bassiana Bio-Agro, Imidacloprid FORAGRO 35 SC"
    },
    {
        "cultivo": "Café",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Ojo de Gallo",
        "nombre_cientifico": "Mycena citricolor",
        "descripcion_sintomas": "Manchas circulares castaño claro a blanquecinas en hojas y frutos verdes, delimitadas por un anillo más oscuro. Causa intensa caída de hojas en zonas nubosas de altura.",
        "foto_url": "https://images.unsplash.com/photo-1509785307050-d4066910ec1e?w=600&auto=format&fit=crop&q=80",
        "productos_recomendados_ids": "Benomyl FORAGRO 50 WP, Oxicloruro FORAGRO 50 WP"
    },
    {
        "cultivo": "Maíz",
        "problema": "Plagas",
        "nombre_enfermedad": "Gusano Cogollero",
        "nombre_cientifico": "Spodoptera frugiperda",
        "descripcion_sintomas": "Hojas tiernas perforadas y rasgadas en el verticilo central (cogollo) con presencia abundante de excremento húmedo similar a aserrín. La larva tiene una Y invertida visible en la cabeza.",
        "foto_url": "https://images.unsplash.com/photo-1551754655-cd27e38d2076?w=600&auto=format&fit=crop&q=80",
        "productos_recomendados_ids": "Clorantraniliprole 20 SC, Tiametoxam + Lambda 30 WG"
    },
    {
        "cultivo": "Maíz",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Complejo Mancha de Asfalto",
        "nombre_cientifico": "Phyllachora maydis + Monographella maydis",
        "descripcion_sintomas": "Pequeñas manchas negras brillantes y abultadas (puntos de brea o alquitrán) en las hojas que coalescen rápidamente con un halo necrótico café, secando el follaje en pocos días.",
        "foto_url": "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?w=600&auto=format&fit=crop&q=80",
        "productos_recomendados_ids": "Azoxystrobin FORAGRO 25 SC, Mancozeb FORAGRO 80 WP"
    },
    {
        "cultivo": "Frijol",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Antracnosis del Frijol",
        "nombre_cientifico": "Colletotrichum lindemuthianum",
        "descripcion_sintomas": "Lesiones oscuras rojo-ladrillo o púrpuras a lo largo de las nervaduras principales en el envés de la hoja. En vainas produce cancros redondeados y hundidos con borde café.",
        "foto_url": "https://images.unsplash.com/photo-1592417817098-8f3d6910985b?w=600&auto=format&fit=crop&q=80",
        "productos_recomendados_ids": "Benomyl FORAGRO 50 WP, Mancozeb FORAGRO 80 WP, Oxicloruro FORAGRO 50 WP"
    },
    {
        "cultivo": "Plátano",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Sigatoka Negra",
        "nombre_cientifico": "Mycosphaerella fijiensis",
        "descripcion_sintomas": "Pizcas y estrías rojizas o café oscuro en el envés de las hojas 3 a 5, que crecen y se convierten en manchas elípticas con centro gris hundido y halo amarillo brillante.",
        "foto_url": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=600&auto=format&fit=crop&q=80",
        "productos_recomendados_ids": "Mancozeb FORAGRO 80 WP, Benomyl FORAGRO 50 WP"
    },
    {
        "cultivo": "Tomate",
        "problema": "Enfermedad",
        "nombre_enfermedad": "Tizón Temprano",
        "nombre_cientifico": "Alternaria solani",
        "descripcion_sintomas": "Manchas circulares oscuras en hojas bajeras con anillos concéntricos característicos en forma de tiro al blanco ('diana'). Rodeadas de un halo clorótico amarillo.",
        "foto_url": "https://images.unsplash.com/photo-1592841200221-a6898f307baa?w=600&auto=format&fit=crop&q=80",
        "productos_recomendados_ids": "Oxicloruro FORAGRO 50 WP, Mancozeb FORAGRO 80 WP, Azoxystrobin FORAGRO 25 SC"
    }
]


def seed_database_if_empty(conn):
    """Inserta productos y referencias de enfermedades si las tablas están vacías."""
    cur = conn.execute("SELECT COUNT(*) AS cnt FROM products")
    count_prod = (cur.fetchone() or {}).get("cnt", 0)
    if count_prod == 0:
        for p in INITIAL_PRODUCTS:
            conn.execute("""
                INSERT INTO products (
                    sku, nombre, categoria, ingrediente_activo,
                    cultivos, problemas, dosis, precio_hnl, stock,
                    unidad, imagen_url, descripcion
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                p["sku"], p["nombre"], p["categoria"], p["ingrediente_activo"],
                p["cultivos"], p["problemas"], p["dosis"], p["precio_hnl"], p["stock"],
                p["unidad"], p.get("imagen_url", ""), p.get("descripcion", "")
            ))

    cur2 = conn.execute("SELECT COUNT(*) AS cnt FROM disease_references")
    count_diseases = (cur2.fetchone() or {}).get("cnt", 0)
    if count_diseases == 0:
        for d in INITIAL_DISEASE_REFERENCES:
            conn.execute("""
                INSERT INTO disease_references (
                    cultivo, problema, nombre_enfermedad, nombre_cientifico,
                    descripcion_sintomas, foto_url, productos_recomendados_ids
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                d["cultivo"], d["problema"], d["nombre_enfermedad"], d["nombre_cientifico"],
                d["descripcion_sintomas"], d["foto_url"], d["productos_recomendados_ids"]
            ))

    cur3 = conn.execute("SELECT COUNT(*) AS cnt FROM users")
    count_users = (cur3.fetchone() or {}).get("cnt", 0)
    if count_users == 0:
        from app.security import hash_password
        admin_hash = hash_password("admin1234")
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            ("admin", admin_hash)
        )

    conn.commit()
