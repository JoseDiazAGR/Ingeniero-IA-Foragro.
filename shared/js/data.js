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
      Plagas: "Fosetyl-Al + Beauveria bassiana. Monitorear broca.",
      Enfermedad: "Oxicloruro de cobre + mancozeb. Roya del café.",
      Clima: "Cobertura de sombra. Riego por goteo en sequía.",
      Suelo: "Cal dolomítica + materia orgánica. pH ácido.",
      "No sé": "Análisis de suelo + muestra foliar recomendado.",
    },
    Maíz: {
      Plagas: "Clorantraniliprole + Trichogramma. Gusano cogollero.",
      Enfermedad: "Metalaxil + mancozeb. Mancha foliar.",
      Clima: "Siembra temprana. Cobertura de rastrojo.",
      Suelo: "Urea + triple 17. Nivelar pH con cal.",
      "No sé": "Diagnóstico visual + laboratorio de suelo.",
    },
    Frijol: {
      Plagas: "Tiametoxam + aceite de nim. Trips y mosca blanca.",
      Enfermedad: "Benomyl + oxicloruro. Antracnosis.",
      Clima: "Evitar riego por aspersión. Drenaje correcto.",
      Suelo: "Inoculante de Rhizobium + P y K.",
      "No sé": "Evaluación de campo por técnico agrícola.",
    },
    Plátano: {
      Plagas: "Imidacloprid + control cultural. Picudo.",
      Enfermedad: "Fungicida sistémico + preventivo. Sigatoka.",
      Clima: "Protección contra vientos. Riego frecuente.",
      Suelo: "Abonamiento orgánico + micronutrientes.",
      "No sé": "Muestreo de raíces y diagnóstico foliar.",
    },
    Tomate: {
      Plagas: "Espinosad + feromonas. Minador y tuta.",
      Enfermedad: "Azoxystrobin + mancozeb. Tizón temprano.",
      Clima: "Invernadero o cobertura plástica. Control de humedad.",
      Suelo: "Enmienda con compost + calcio foliar.",
      "No sé": "Análisis completo: suelo, agua y tejido.",
    },
    Otro: {
      Plagas: "Consultar con técnico especializado.",
      Enfermedad: "Consultar con técnico especializado.",
      Clima: "Consultar con técnico especializado.",
      Suelo: "Consultar con técnico especializado.",
      "No sé": "Consultar con técnico especializado.",
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
