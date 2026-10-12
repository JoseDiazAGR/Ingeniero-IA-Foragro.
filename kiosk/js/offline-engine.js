/**
 * Motor offline para la tablet.
 * Se encarga de procesar las consultas cuando no hay conexión a internet o a la API,
 * basándose en el offline-cache de IndexedDB/CacheStorage.
 */
class OfflineEngine {
    constructor() {
        this.data = null;
        this.loadOfflineData();
    }

    async loadOfflineData() {
        try {
            const cache = await caches.open('foragro-kiosk-v2');
            const res = await cache.match('/api/offline-cache');
            if (res) {
                this.data = await res.json();
                console.log("🟢 Datos agronómicos offline cargados:", this.data.version);
            }
        } catch (e) {
            console.warn("No se pudo cargar datos offline:", e);
        }
    }

    processMessage(message, currentCultivo) {
        if (!this.data) {
            return {
                reply: "La conexión a internet se ha perdido y aún no tengo mi base de datos offline lista. Por favor intenta en unos minutos.",
                ui_actions: []
            };
        }

        const msgLower = message.toLowerCase();
        
        // 1. Detectar cultivo
        let detectedCultivo = currentCultivo;
        for (const c of this.data.cultivos) {
            if (msgLower.includes(c.toLowerCase())) {
                detectedCultivo = c;
                break;
            }
        }
        if (!detectedCultivo) detectedCultivo = "Café"; // Fallback default

        // 2. Detectar problema
        let detectedProblema = null;
        const keywords = {
            "roya": "Roya", "broca": "Broca", "cogollero": "Cogollero",
            "antracnosis": "Antracnosis", "sigatoka": "Sigatoka",
            "tizón": "Tizón", "plaga": "Plagas", "enfermedad": "Enfermedad"
        };
        for (const [kw, prob] of Object.entries(keywords)) {
            if (msgLower.includes(kw)) {
                detectedProblema = prob;
                break;
            }
        }

        const ui_actions = [];

        // 3. Buscar fotos de referencia
        let referencias = this.data.disease_references.filter(r => r.cultivo === detectedCultivo);
        if (detectedProblema) {
            const filtered = referencias.filter(r => r.problema === detectedProblema);
            if (filtered.length > 0) referencias = filtered;
        }
        if (referencias.length > 0) {
            ui_actions.push({ type: "show_disease_photos", data: referencias });
        }

        // 4. Buscar productos
        let productos = this.data.products.filter(p => p.cultivos && p.cultivos.includes(detectedCultivo));
        if (detectedProblema) {
            const filtered = productos.filter(p => p.problemas && p.problemas.includes(detectedProblema));
            if (filtered.length > 0) productos = filtered;
        }
        if (productos.length > 0) {
            ui_actions.push({ type: "show_products", data: productos.slice(0, 3) });
        }

        // 5. Generar respuesta
        const recomendacionBase = (this.data.recomendaciones[detectedCultivo] && this.data.recomendaciones[detectedCultivo][detectedProblema]) 
            ? this.data.recomendaciones[detectedCultivo][detectedProblema] 
            : "revisión técnica para identificar el tratamiento correcto";

        let productStr = "";
        if (productos.length > 0) {
            productStr = ` En la tienda contamos con ${productos[0].nombre} para tratar este problema.`;
        }

        let reply = `[Modo Offline] Para tu cultivo de ${detectedCultivo}, la recomendación general es ${recomendacionBase}.${productStr} Compara tus síntomas con las fotos de referencia.`;

        return {
            reply,
            ui_actions,
            lead_id: null,
            model: "local_offline"
        };
    }
}

window.offlineEngine = new OfflineEngine();
