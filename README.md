# FORAGRO — ChatAgro POP (Kiosco Inteligente) + CRM & Dashboard

Sistema integral de asesoría agrícola y punto de venta (POP) para **tiendas y agroveterinarias FORAGRO**. 
Diseñado para operar en una **tablet montada sobre un agrónomo de tamaño real de PVC o cartón** ("Inge. Agro IA"), brindando atención conversacional por voz fluida a productores agrícolas, diagnóstico visual de enfermedades con fotos de referencia o cámara, prescripción fundamentada en inventario real de bodega y sincronización con el CRM comercial y WhatsApp.

---

## 🚀 Inicio Rápido (Local)

Para mayor facilidad, se han incluido ejecutables directos `.bat`:

1. **Iniciar el Backend (FastAPI + SQLite + IA):**
   Haz doble clic en `iniciar_backend.bat` (o ejecuta `uvicorn app.main:app --reload --port 8000` en la carpeta `backend`).
   - Servidor API: `http://localhost:8000`
   - Documentación interactiva Swagger: `http://localhost:8000/docs`

2. **Iniciar el Frontend (Kiosco POP y Dashboard CRM):**
   Haz doble clic en `iniciar_frontend.bat` (o ejecuta `python -m http.server 8080` en la raíz).
   - **Kiosco en Tablet POP:** [http://localhost:8080/kiosk/](http://localhost:8080/kiosk/)
   - **Dashboard & CRM Comercial:** [http://localhost:8080/dashboard/](http://localhost:8080/dashboard/)
     - **Usuario administrador por defecto:** `admin`
     - **Contraseña:** `admin1234`

---

## 🌾 Funcionalidades de ChatAgro POP (Tablet de Punto de Venta)

1. **Voz de Ultra-Baja Latencia y Alta Fidelidad:**
   - Síntesis de voz ultra-natural con modelo `tts-1` de OpenAI (`voice: onyx`), con tono cálido, profesional y empático.
   - **Caché local de audio en disco/memoria:** Frases recurrentes se despachan en menos de 50 ms.
   - **Fallback automático y transparente:** Si la conexión a la nube o el saldo de la API se interrumpe, conmuta al sintetizador de voz local del navegador sin congelar la pantalla.
   - **Reconocimiento por voz (STT):** Micrófono interactivo con Web Speech API para interacción fluida de cero latencia.

2. **Function Calling (Herramientas de IA) — Cero Alucinaciones y Ahorro de Tokens:**
   El agente no inventa datos; consulta herramientas conectadas a la base de datos:
   - `consultar_inventario`: Consulta en tiempo real las existencias en bodega, dosis recomendada, ingrediente activo y precios en Lempiras (HNL) de productos oficiales FORAGRO (*Oxicloruro 50 WP, Mancozeb 80 WP, Fosetyl-Al 80 WG, Clorantraniliprole 20 SC, Beauveria Bassiana, FertiPlus, RaizMax, etc.*).
   - `mostrar_fotos_referencia`: Despliega tarjetas con fotografías de patología vegetal (Roya del Café, Broca, Cogollero, Sigatoka, Antracnosis, etc.) para que el agricultor toque la foto que coincide con su cultivo.
   - `solicitar_foto_camara`: Activa la cámara de la tablet para que el cliente tome una foto en vivo de la hoja enferma para diagnóstico por visión IA.
   - `obtener_datos_agronomicos`: Consulta el tipo de suelo, pH y clima según el departamento de Honduras.
   - `guardar_datos_productor`: Registra cultivo, zona, manzanas, fecha de siembra, teléfono y genera el cupón del 5%.
   - `enviar_resumen_whatsapp`: Despacha el diagnóstico y cupón a WhatsApp.

3. **Captura Completa de Datos del Productor:**
   - Tipo de cultivo
   - Zona / Departamento
   - Manzanas cultivadas
   - **Fecha de siembra / Etapa agronómica** (floración, llenado, etc.)
   - Si el problema es recurrente
   - Teléfono para WhatsApp

---

## 👥 CRM y Dashboard Comercial

1. **Métricas y Atribución:**
   - KPIs en tiempo real: Productores registrados, área total atendida (manzanas), cupones emitidos vs canjeados, tasa de conversión comercial.
   - Gráfico de atribución publicitaria (Radio, TV, Redes sociales, Amigo, Punto de venta).
   - Gráfico de foco de atención por cultivo y lista de patologías más consultadas.

2. **CRM de Productores y Seguimiento Agronómico:**
   - Búsqueda en tiempo real por teléfono, cultivo, zona o patología.
   - Filtros dinámicos por Cultivo, Departamento y Estado de seguimiento.
   - **Modal de Detalle del Productor:**
     - Datos agronómicos completos (incluyendo fecha de siembra y área).
     - Bitácora de seguimiento editable para el agrónomo asignado.
     - Actualización de estados: `Nuevo`, `Contactado`, `Visita Técnica Agendada`, `Venta Cerrada`, `No Interesado`.
     - **Botón directo de WhatsApp:** Abre chat con el productor con mensaje personalizado prellenado.
     - **Transcripción de la charla:** Muestra lo que el productor conversó con el kiosco.

3. **Inventario de Bodega:**
   - Monitoreo de existencias de productos FORAGRO y precios.
   - Ajuste rápido de stock en bodega desde la propia interfaz.

4. **Exportación a CSV / Excel:**
   - Descarga directa de la base de datos de leads en formato CSV con codificación UTF-8 BOM compatible con Microsoft Excel.

---

## 🔒 Arquitectura y Buenas Prácticas de Seguridad

- **Separación total de entornos:** El Kiosco público (`kiosk/`) y el CRM privado (`dashboard/`) están desacoplados.
- **Autenticación robusta:** Sesiones HTTP-only con tokens hasheados con SHA-256 y contraseñas cifradas con `bcrypt`.
- **Mitigación XSS:** Todo dato renderizado en DOM dinámico pasa por saneamiento estricto (`escapeHTML`).
- **Content Security Policy (CSP):** Políticas restrictivas para carga de scripts, fuentes y recursos multimedia.
- **Rate Limiting:** Protección contra ataques de denegación de servicio o fuerza bruta.
