/**
 * FORAGRO — Static domain data
 * ---------------------------------------------------------------------------
 * Pulled out of the conversation logic so agronomy content can be updated
 * (or eventually loaded from a CMS/API) without touching app behavior.
 *
 * NOTE: these are placeholder/demo values (soil type, weather snapshot,
 * treatment) and should be replaced by a real agronomy database and a live
 * weather API call keyed by GPS/municipality rather than a hardcoded map.
 * ---------------------------------------------------------------------------
 */
window.FORAGRO_DATA = Object.freeze({
  suelos: {
    Copán: "Franco-arcilloso, pH 5.8, buen drenaje",
    Ocotepeque: "Franco-limoso, pH 6.2, moderado drenaje",
    Lempira: "Arcilloso, pH 5.5, drenaje lento",
    "Santa Bárbara": "Franco-arenoso, pH 6.5, excelente drenaje",
    Olancho: "Limoso, pH 6.0, drenaje moderado",
    Otro: "Suelo variable, requiere análisis",
  },
  climas: {
    Copán: "24°C, parcialmente nublado, 78% humedad",
    Ocotepeque: "22°C, soleado, 65% humedad",
    Lempira: "20°C, nublado, 82% humedad",
    "Santa Bárbara": "26°C, soleado, 70% humedad",
    Olancho: "28°C, parcialmente nublado, 75% humedad",
    Otro: "Clima variable, consultar zona específica",
  },
  recomendaciones: {
    Café: {
      Plagas: "Forafos 48 EC para control de Broca del Café.",
      Enfermedad: "Iman Ultra 37.5 SC, Vertigo 32.5 SC, Halt 10 SC y Oxicloruro 50 WP.",
      Clima: "Proliforte Foliar y Kalex Fosfito K para estrés hídrico.",
      Suelo: "Kalex Fosfito K y manejo integrado de nutrición radicular.",
      "No sé": "Revisión foliar con Kalex Cu y Proliforte Foliar.",
    },
    Maíz: {
      Plagas: "Curagro 55 EC, Atrapa 44 EC o Kñon 40 SC para Gusano Cogollero; Forabufos 10 GR para Gallina Ciega.",
      Enfermedad: "Vertigo 32.5 SC y Halt 10 SC para Complejo Mancha de Asfalto.",
      Clima: "Proliforte Foliar para recuperar el cultivo tras sequía.",
      Suelo: "Defiende Plus 54 FS y Tratasem 35 SC en tratamiento de semilla.",
      "No sé": "Diagnóstico visual y bioestimulación con Proliforte Foliar.",
    },
    Frijol: {
      Plagas: "Molux 6 GB para Babosa del Frijol; Bolido 24 SC y Ztafor 20 SP para Mosca Blanca.",
      Enfermedad: "Vertigo 32.5 SC, Pilarstin 50 WP y Oxicloruro 50 WP para Antracnosis.",
      Clima: "Proliforte Foliar para floración y llenado de vaina.",
      Suelo: "Tratasem 35 SC y Defiende Plus 54 FS contra pudrición radicular.",
      "No sé": "Evaluación técnica de campo por agrónomo FORAGRO.",
    },
    Plátano: {
      Plagas: "Pikudo 20 SC y Forabufos 10 GR para Picudo Negro del Plátano.",
      Enfermedad: "Iman Ultra 37.5 SC, Mancozeb 80 WP y Alfan 45 EC para Sigatoka Negra.",
      Clima: "Kalex Fosfito K y Proliforte Foliar para vigor foliar.",
      Suelo: "Forabufos 10 GR para control de nemátodos y plagas de cepa.",
      "No sé": "Muestreo de cormo y diagnóstico foliar.",
    },
    Tomate: {
      Plagas: "Bolido 24 SC, Ztafor 20 SP y Abafor 1.8 EC para Mosca Blanca; Pikudo 20 SC para Picudo.",
      Enfermedad: "Forzate 72 WP, Padrino 18.7 DC y Escofor 23 SC para Tizones y Moho Gris.",
      Clima: "Kalex Fosfito K y Proliforte Foliar contra estrés ambiental.",
      Suelo: "Foraxil 240 EC y Padrino 18.7 DC en drench contra Damping-off.",
      "No sé": "Análisis fitosanitario integral de follaje y raíz.",
    },
    Otro: {
      Plagas: "Forafos 48 EC y Cintanegra 2.5 EC para Salivazo en pastos.",
      Enfermedad: "Mancozeb 80 WP y Kalex Fosfito K de amplio espectro.",
      Clima: "Proliforte Foliar para recuperación metabólica.",
      Suelo: "Pastura 7.5 SL, Tejano 30.4 SL y Tokon 24.4 SL para limpieza de potreros.",
      "No sé": "Consultar con agrónomo especializado FORAGRO.",
    },
  },
  crossSell: {
    Café: "Fertilizante especial café + Herbicida selectivo",
    Maíz: "Semilla híbrida certificada + Fungicida preventivo",
    Frijol: "Inoculante biológico + Malla sombra",
    Plátano: "Bioestimulante radicular + Bolsa protectora",
    Tomate: "Semilla mejorada + Sistema de riego por goteo",
    Otro: "Kit de diagnóstico + Asesoría técnica",
  },
});
