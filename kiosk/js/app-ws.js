/**
 * Controlador de WebSocket (Manos libres) para FORAGRO Kiosco v2.1
 * UX Simplificado: Pantalla de inicio limpia con botón de inicio y chat minimalista.
 *
 * Arquitectura de voz (half-duplex, anti auto-escucha):
 *  1. El micrófono (SpeechRecognition) se APAGA con abort() ANTES de que el
 *     Ingeniero emita sonido y mientras la IA está pensando. abort() descarta
 *     cualquier audio ya capturado, así que la voz del bot nunca llega a transcribirse.
 *     (La Web Speech API no aplica cancelación de eco al audio que reproduce la
 *     propia página, por eso filtrar solo por texto no es suficiente.)
 *  2. Se reactiva tras un margen acústico (postSpeechDelayMs) para que la
 *     reverberación del parlante se disipe.
 *  3. Cualquier resultado que llegue mientras el micrófono "no debe" escuchar se descarta.
 *  4. Defensa secundaria: filtro de eco por similitud textual en la ventana
 *     inmediatamente posterior a que el bot termina de hablar.
 *  5. Voz: se usa la voz de la IA (OpenAI TTS vía backend) en TODOS los mensajes,
 *     incluida la bienvenida. La voz del navegador es solo respaldo (offline / error).
 *  6. Interrupción (barge-in): tocando la pantalla o el botón del micrófono.
 */

'use strict';

// ---------------------------------------------------------------------------
// Configuración de voz
// Sobrescribible con `window.KIOSK_VOICE_CONFIG = {...}` antes de cargar este
// script, o con el parámetro de URL `?voice=nova`.
// ---------------------------------------------------------------------------
const KIOSK_VOICE_CONFIG = (() => {
    const overrides = window.KIOSK_VOICE_CONFIG || {};
    const urlVoice = new URLSearchParams(window.location.search).get('voice');
    return Object.freeze({
        lang: 'es-HN',
        aiVoice: 'onyx',               // Voz de OpenAI TTS (onyx = masculina, cálida, profesional)
        preferAiVoice: true,           // Usar la voz de la IA siempre que haya conexión
        ttsEndpoint: '/api/tts',
        ttsTimeoutMs: 8000,
        postSpeechDelayMs: 700,        // Margen anti-reverberación antes de reabrir el micrófono
        echoGuardWindowMs: 2500,       // Ventana en la que se aplica el filtro de eco textual
        thinkingTimeoutMs: 45000,      // Si la IA no responde, se vuelve a escuchar
        nativeRate: 1.0,
        nativePitch: 1.0,
        nativeVoiceLangs: ['es-HN', 'es-MX', 'es-US', 'es-419', 'es-ES', 'es'],
        ...overrides,
        ...(urlVoice ? { aiVoice: urlVoice } : {}),
    });
})();

const WELCOME_TEXT = '¡Hola amigo productor! 👋 Soy el Ingeniero Agrónomo de FORAGRO. ' +
    'Cuéntame, ¿qué cultivo tienes y qué plaga o problema estás viendo en tu finca?';

const State = Object.freeze({
    IDLE: 'idle',
    LISTENING: 'listening',
    THINKING: 'thinking',
    SPEAKING: 'speaking',
});

// WAV vacío para "desbloquear" el elemento de audio dentro de un gesto del usuario (iOS/Android).
const SILENT_WAV = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function normalizeText(text) {
    return (text || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9\s]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

/** Limpia markdown y emojis para que no se pronuncien. */
function stripForSpeech(text) {
    return (text || '')
        .replace(/\p{Extended_Pictographic}/gu, '')
        .replace(/[*_#`>~]/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

/**
 * ¿La transcripción parece ser el propio bot escuchado por el micrófono?
 * Las respuestas cortas ("sí", "no", "maíz") nunca se consideran eco.
 */
function isLikelyEcho(transcript, reference) {
    const heard = normalizeText(transcript);
    const said = normalizeText(reference);
    if (!heard || !said) return false;

    const heardWords = heard.split(' ');
    if (heardWords.length < 3) return false;
    if (said.includes(heard)) return true;

    const saidWords = new Set(said.split(' '));
    const matches = heardWords.filter((w) => saidWords.has(w)).length;
    return matches / heardWords.length >= 0.6;
}

function base64ToBlob(base64, mimeType) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new Blob([bytes], { type: mimeType });
}

/** Divide el texto en frases cortas (evita el corte de ~15 s de speechSynthesis en Chrome). */
function splitIntoChunks(text, maxLength = 180) {
    const sentences = text.match(/[^.!?;:]+[.!?;:]*\s*/g) || [text];
    const chunks = [];
    let current = '';
    for (const sentence of sentences) {
        if (current && (current + sentence).length > maxLength) {
            chunks.push(current.trim());
            current = '';
        }
        current += sentence;
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks;
}

// ---------------------------------------------------------------------------
// VoicePlayer: salida de voz (voz de la IA con respaldo del navegador)
// ---------------------------------------------------------------------------
class VoicePlayer {
    constructor(config) {
        this.config = config;
        this.audioEl = new Audio();
        this.audioEl.preload = 'auto';
        this.ttsCache = new Map();
        this.nativeVoice = null;

        this._token = 0;          // Identifica la reproducción vigente (invalida callbacks viejos)
        this._finish = null;      // Resolver de la promesa de la reproducción en curso
        this._objectUrl = null;

        this._loadNativeVoice();
    }

    /** Debe llamarse dentro de un gesto del usuario (click) para permitir autoplay. */
    unlock() {
        const el = this.audioEl;
        el.muted = true;
        el.src = SILENT_WAV;
        el.play()
            .then(() => { if (el.src === SILENT_WAV) el.pause(); })
            .catch(() => {})
            .finally(() => { el.muted = false; });
    }

    /** Pre-genera audio de la IA (ej. bienvenida) para que suene sin latencia. */
    preload(text) {
        if (!this.config.preferAiVoice || !navigator.onLine) return;
        this._fetchTts(stripForSpeech(text)).catch(() => {});
    }

    /**
     * Reproduce el texto. Resuelve `true` si terminó normalmente
     * o `false` si fue interrumpido.
     */
    async speak(text, { audioBase64 = null } = {}) {
        this.stop();
        const token = ++this._token;
        const spoken = stripForSpeech(text);
        if (!spoken) return true;

        let blob = null;
        if (audioBase64) {
            try {
                blob = base64ToBlob(audioBase64, 'audio/mpeg');
            } catch (e) {
                console.warn('Audio de la IA corrupto, usando voz del navegador.', e);
            }
        } else if (this.config.preferAiVoice && navigator.onLine) {
            try {
                blob = await this._fetchTts(spoken);
            } catch (e) {
                console.warn('Voz de la IA no disponible, usando voz del navegador:', e.message);
            }
        }

        if (token !== this._token) return false; // Interrumpido durante la descarga

        if (blob) {
            const result = await this._playBlob(blob, token);
            if (result !== 'error') return result;
            if (token !== this._token) return false;
        }
        return this._speakNative(spoken, token);
    }

    /** Detiene inmediatamente cualquier voz (IA o navegador). */
    stop() {
        this._token++;
        this._teardownAudio();
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
        this._settle(false);
    }

    // -- Internos ------------------------------------------------------------

    _settle(value) {
        if (!this._finish) return;
        const finish = this._finish;
        this._finish = null;
        finish(value);
    }

    _teardownAudio() {
        const el = this.audioEl;
        el.onended = null;
        el.onerror = null;
        try { el.pause(); } catch (_) { /* noop */ }
        if (this._objectUrl) {
            el.removeAttribute('src');
            el.load();
            URL.revokeObjectURL(this._objectUrl);
            this._objectUrl = null;
        }
    }

    _playBlob(blob, token) {
        return new Promise((resolve) => {
            this._finish = resolve;
            const el = this.audioEl;
            const fail = (reason) => {
                if (token !== this._token) return;
                console.warn('No se pudo reproducir la voz de la IA:', reason);
                this._teardownAudio();
                this._settle('error');
            };

            this._objectUrl = URL.createObjectURL(blob);
            el.muted = false;
            el.onended = () => {
                if (token !== this._token) return;
                this._teardownAudio();
                this._settle(true);
            };
            el.onerror = () => fail(el.error?.message || 'error de decodificación');
            el.src = this._objectUrl;
            el.play().catch((e) => fail(e.name));
        });
    }

    async _fetchTts(text) {
        const key = `${this.config.aiVoice}|${text}`;
        if (this.ttsCache.has(key)) return this.ttsCache.get(key);

        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), this.config.ttsTimeoutMs);
        try {
            const res = await fetch(this.config.ttsEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, voice: this.config.aiVoice }),
                signal: controller.signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const blob = await res.blob();

            if (this.ttsCache.size >= 20) {
                this.ttsCache.delete(this.ttsCache.keys().next().value);
            }
            this.ttsCache.set(key, blob);
            return blob;
        } finally {
            clearTimeout(timer);
        }
    }

    _loadNativeVoice() {
        if (!('speechSynthesis' in window)) return;
        const pick = () => {
            const voices = window.speechSynthesis.getVoices();
            for (const lang of this.config.nativeVoiceLangs) {
                const match = voices.find((v) =>
                    v.lang.replace('_', '-').toLowerCase().startsWith(lang.toLowerCase()));
                if (match) {
                    this.nativeVoice = match;
                    return;
                }
            }
        };
        pick();
        window.speechSynthesis.addEventListener?.('voiceschanged', pick);
    }

    _speakNative(text, token) {
        if (!('speechSynthesis' in window)) return Promise.resolve(true);

        return new Promise((resolve) => {
            this._finish = resolve;
            const synth = window.speechSynthesis;
            const chunks = splitIntoChunks(text);
            const rate = this.config.nativeRate;

            synth.cancel();
            chunks.forEach((chunk, index) => {
                const utterance = new SpeechSynthesisUtterance(chunk);
                utterance.lang = this.nativeVoice?.lang || this.config.lang;
                if (this.nativeVoice) utterance.voice = this.nativeVoice;
                utterance.rate = rate;
                utterance.pitch = this.config.nativePitch;

                if (index === chunks.length - 1) {
                    utterance.onend = () => { if (token === this._token) this._settle(true); };
                }
                utterance.onerror = (e) => {
                    if (token !== this._token) return;
                    if (e.error === 'interrupted' || e.error === 'canceled') return;
                    this._settle(true);
                };
                synth.speak(utterance);
            });

            // Watchdog: algunos navegadores no disparan `onend`.
            const estimatedMs = (text.length * 85) / rate + 4000;
            setTimeout(() => {
                if (token !== this._token || !this._finish) return;
                synth.cancel();
                this._settle(true);
            }, estimatedMs);
        });
    }
}

// ---------------------------------------------------------------------------
// VoiceListener: entrada de voz con control half-duplex
// ---------------------------------------------------------------------------
class VoiceListener {
    constructor({ lang, onTranscript, onFatalError }) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.supported = Boolean(SpeechRecognition);
        this.onTranscript = onTranscript;
        this.onFatalError = onFatalError;

        this._wanted = false;       // ¿El controlador quiere que escuchemos?
        this._running = false;      // ¿Hay una sesión de reconocimiento abierta (o abriéndose)?
        this._restartTimer = null;
        this._failures = 0;

        if (!this.supported) {
            console.warn('Speech Recognition no disponible en este navegador.');
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = lang;
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onresult = (event) => this._handleResult(event);
        recognition.onerror = (event) => this._handleError(event);
        recognition.onend = () => {
            this._running = false;
            this._scheduleStart();
        };

        this._recognition = recognition;
    }

    /** Abre o cierra el micrófono. Cerrar usa abort() para descartar audio pendiente. */
    setActive(active) {
        if (!this.supported) return;
        this._wanted = active;

        if (active) {
            this._scheduleStart(0);
            return;
        }

        clearTimeout(this._restartTimer);
        if (this._running) {
            try { this._recognition.abort(); } catch (_) { /* noop */ }
        }
    }

    _scheduleStart(delay) {
        clearTimeout(this._restartTimer);
        if (!this._wanted || this._running) return;
        const wait = delay ?? Math.min(250 * 2 ** this._failures, 5000);
        this._restartTimer = setTimeout(() => this._start(), wait);
    }

    _start() {
        if (!this._wanted || this._running) return;
        try {
            this._running = true;
            this._recognition.start();
        } catch (e) {
            this._running = false;
            this._failures++;
            this._scheduleStart();
        }
    }

    _handleResult(event) {
        // Resultado tardío de una sesión que debía estar cerrada (ej. el bot empezó a hablar).
        if (!this._wanted) return;
        this._failures = 0;

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            if (!result.isFinal) continue;
            const transcript = result[0].transcript.trim();
            if (transcript) this.onTranscript(transcript);
        }
    }

    _handleError(event) {
        switch (event.error) {
            case 'no-speech':
            case 'aborted':
                return; // Normales: silencio o abort() intencional
            case 'not-allowed':
            case 'service-not-allowed':
            case 'audio-capture':
                this._wanted = false;
                this.onFatalError?.(event.error);
                return;
            default:
                this._failures++;
                console.warn('Error de reconocimiento de voz:', event.error);
        }
    }
}

// ---------------------------------------------------------------------------
// KioskController: orquesta UI, WebSocket, voz y turnos de conversación
// ---------------------------------------------------------------------------
class KioskController {
    constructor() {
        this.config = KIOSK_VOICE_CONFIG;
        this.pdvCodigo = new URLSearchParams(window.location.search).get('pdv') || 'DEMO_01';

        // Conexión
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnect = 15;
        this.isOnline = navigator.onLine;
        this.heartbeatTimer = null;

        // Conversación
        this.context = { cultivo: null, zona: null };
        this.isConsultationActive = false;
        this.micEnabled = true;          // Preferencia del usuario (botón de micrófono)
        this.state = State.IDLE;
        this.lastBotText = '';
        this.listeningSince = 0;
        this.speechTurn = 0;             // Invalida turnos de habla interrumpidos
        this.thinkingTimer = null;

        // DOM
        this.el = {
            idleScreen: document.getElementById('idle-screen'),
            activeScreen: document.getElementById('active-screen'),
            btnStart: document.getElementById('btn-start'),
            btnReset: document.getElementById('btn-reset'),
            btnMic: document.getElementById('btn-mic'),
            micHint: document.getElementById('mic-hint'),
            statusText: document.getElementById('status-text'),
            chatLog: document.getElementById('chat-log'),
            pdvBadge: document.getElementById('pdv-badge'),
        };
        if (this.el.pdvBadge) this.el.pdvBadge.textContent = 'PDV: ' + this.pdvCodigo;

        // Voz
        this.voice = new VoicePlayer(this.config);
        this.listener = new VoiceListener({
            lang: this.config.lang,
            onTranscript: (text) => this.handleUserSpeech(text),
            onFatalError: (error) => this.handleMicError(error),
        });

        this.initEventListeners();
        this.initNetworkListeners();
        this.connectWebSocket();
        this.voice.preload(WELCOME_TEXT);
        this.renderState();
    }

    // -- Eventos de UI -------------------------------------------------------

    initEventListeners() {
        const { btnStart, btnReset, btnMic, activeScreen } = this.el;

        btnStart?.addEventListener('click', () => this.startConsultation());
        btnReset?.addEventListener('click', () => this.resetToIdle());

        btnMic?.addEventListener('click', (e) => {
            e.stopPropagation();
            if (this.state === State.SPEAKING) {
                // Tocar el micrófono mientras habla = interrumpir y escuchar
                this.micEnabled = true;
                this.interruptSpeech();
                return;
            }
            this.micEnabled = !this.micEnabled;
            this.setState(this.state);
        });

        // Permitir interrumpir la voz del bot tocando la pantalla
        activeScreen?.addEventListener('click', (e) => {
            if (this.state !== State.SPEAKING) return;
            if (btnReset && btnReset.contains(e.target)) return;
            console.log('🛑 Cliente interrumpió al Agrobot tocando la pantalla.');
            this.interruptSpeech();
        });
    }

    initNetworkListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.reconnectAttempts = 0;
            this.connectWebSocket();
        });
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.stopHeartbeat();
            this.updateStatus('Modo Offline');
        });
    }

    // -- Ciclo de la consulta ------------------------------------------------

    startConsultation() {
        if (this.isConsultationActive) return;
        this.isConsultationActive = true;
        this.micEnabled = true;

        this.el.idleScreen?.classList.add('hidden');
        this.el.activeScreen?.classList.remove('hidden');

        // Estamos dentro del click: desbloquear audio para evitar bloqueo de autoplay.
        this.voice.unlock();

        if (this.el.chatLog && this.el.chatLog.children.length === 0) {
            this.appendMessage('assistant', WELCOME_TEXT);
            this.say(WELCOME_TEXT);
        } else {
            this.setState(State.LISTENING);
        }
    }

    resetToIdle() {
        this.isConsultationActive = false;
        this.clearThinkingTimer();
        this.speechTurn++;
        this.voice.stop();
        this.setState(State.IDLE);

        this.el.activeScreen?.classList.add('hidden');
        this.el.idleScreen?.classList.remove('hidden');

        // Limpiar para la siguiente persona
        if (this.el.chatLog) this.el.chatLog.innerHTML = '';
        this.context = { cultivo: null, zona: null };
        this.lastBotText = '';

        document.getElementById('ui-overlay')?.classList.add('hidden');
    }

    // -- Máquina de estados de turnos ---------------------------------------

    /**
     * Único punto donde se decide si el micrófono escucha.
     * Solo se escucha en LISTENING: nunca mientras la IA piensa o habla.
     */
    setState(next) {
        this.state = next;
        const shouldListen = this.isConsultationActive && this.micEnabled && next === State.LISTENING;
        if (shouldListen) this.listeningSince = Date.now();
        this.listener.setActive(shouldListen);
        this.renderState();
    }

    renderState() {
        const { btnMic, micHint } = this.el;
        const listening = this.state === State.LISTENING && this.micEnabled && this.listener.supported;

        btnMic?.classList.toggle('active', listening);
        btnMic?.classList.toggle('muted', !this.micEnabled);

        let status;
        let hint;
        switch (this.state) {
            case State.THINKING:
                status = 'Inge está pensando...';
                hint = 'Un momento, estoy revisando tu caso...';
                break;
            case State.SPEAKING:
                status = 'Inge está hablando...';
                hint = '🔈 Toca la pantalla para interrumpir';
                break;
            case State.LISTENING:
                if (!this.listener.supported) {
                    status = 'Listo';
                    hint = 'Utiliza el teclado en pantalla';
                } else if (this.micEnabled) {
                    status = 'Escuchando...';
                    hint = '🎙️ <strong>Manos libres activo</strong> (habla con confianza)';
                } else {
                    status = 'En pausa';
                    hint = 'Micrófono en pausa (toca para hablar)';
                }
                break;
            default:
                status = 'Sistema listo';
                hint = '';
        }

        this.updateStatus(status);
        if (micHint) micHint.innerHTML = hint;
    }

    updateStatus(text) {
        if (this.el.statusText) this.el.statusText.innerText = text;
    }

    // -- Habla del Ingeniero -------------------------------------------------

    async say(text, audioBase64 = null) {
        const turn = ++this.speechTurn;
        this.lastBotText = text;

        // Cerrar el micrófono ANTES de emitir cualquier sonido.
        this.setState(State.SPEAKING);
        const finished = await this.voice.speak(text, { audioBase64 });
        if (turn !== this.speechTurn || !this.isConsultationActive) return;

        // Margen para que la reverberación del parlante no entre al micrófono.
        if (finished) await sleep(this.config.postSpeechDelayMs);
        if (turn !== this.speechTurn || !this.isConsultationActive) return;

        this.setState(State.LISTENING);
    }

    interruptSpeech() {
        if (this.state !== State.SPEAKING) return;
        this.speechTurn++;
        this.voice.stop();
        this.setState(State.LISTENING);
    }

    // -- Entrada del productor ----------------------------------------------

    handleUserSpeech(transcript) {
        if (!this.isConsultationActive || this.state !== State.LISTENING) return;

        const justResumed = Date.now() - this.listeningSince < this.config.echoGuardWindowMs;
        if (justResumed && isLikelyEcho(transcript, this.lastBotText)) {
            console.log('🔇 Eco del Agrobot descartado:', transcript);
            return;
        }

        console.log('🎤 Reconocido:', transcript);
        this.appendMessage('user', transcript);
        this.sendMessage(transcript);
    }

    handleMicError(error) {
        this.micEnabled = false;
        this.renderState();
        if (error === 'not-allowed' || error === 'service-not-allowed') {
            this.appendMessage('system', 'No tengo permiso para usar el micrófono. Revisa los permisos del navegador.');
        } else {
            this.appendMessage('system', 'No se detecta el micrófono. Verifica que esté conectado.');
        }
    }

    sendMessage(text) {
        this.setState(State.THINKING);
        this.startThinkingTimer();

        if (this.isOnline && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'message',
                message: text,
                cultivo: this.context.cultivo,
                zona: this.context.zona,
                voice: this.config.aiVoice,
            }));
            return;
        }

        // Modo offline: motor local
        if (!window.offlineEngine) {
            this.handleAssistantError('Sin conexión en este momento. Intenta de nuevo en unos segundos.');
            return;
        }
        this.updateStatus('Procesando en modo offline...');
        const offline = window.offlineEngine.processMessage(text, this.context.cultivo);
        this.handleAssistantReply({ reply: offline.reply, ui_actions: offline.ui_actions, audio: null });
    }

    // -- Respuestas de la IA -------------------------------------------------

    handleAssistantReply(data) {
        this.clearThinkingTimer();
        if (!this.isConsultationActive) return;

        const reply = data.reply || '';
        if (reply) this.appendMessage('assistant', reply);
        this.handleUiActions(data.ui_actions);

        if (reply) {
            this.say(reply, data.audio || null);
        } else {
            this.setState(State.LISTENING);
        }
    }

    handleAssistantError(message) {
        this.clearThinkingTimer();
        if (!this.isConsultationActive) return;
        if (message) this.appendMessage('system', message);
        this.setState(State.LISTENING);
    }

    startThinkingTimer() {
        this.clearThinkingTimer();
        this.thinkingTimer = setTimeout(() => {
            if (this.state === State.THINKING) {
                this.handleAssistantError('No recibí respuesta. ¿Me lo puedes repetir?');
            }
        }, this.config.thinkingTimeoutMs);
    }

    clearThinkingTimer() {
        if (this.thinkingTimer) {
            clearTimeout(this.thinkingTimer);
            this.thinkingTimer = null;
        }
    }

    handleUiActions(actions) {
        if (!Array.isArray(actions)) return;
        for (const action of actions) {
            window.dispatchEvent(new CustomEvent('kioskAction', { detail: action }));
        }
    }

    appendMessage(role, text) {
        const { chatLog } = this.el;
        if (!chatLog) return;
        const div = document.createElement('div');
        div.className = `message ${role}`;
        div.innerText = text;
        chatLog.appendChild(div);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    // -- WebSocket -----------------------------------------------------------

    connectWebSocket() {
        if (!this.isOnline) return;
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/api/chat-ws`);

        this.ws.onopen = () => {
            console.log('✅ WebSocket conectado.');
            this.reconnectAttempts = 0;
            this.ws.send(JSON.stringify({ type: 'init', pdv: this.pdvCodigo, voice: this.config.aiVoice }));
            this.startHeartbeat();
            fetch('/api/offline-cache').catch((e) => console.log('Offline cache fetch', e));
        };

        this.ws.onmessage = (event) => {
            let data;
            try {
                data = JSON.parse(event.data);
            } catch (e) {
                console.warn('Mensaje WS inválido:', event.data);
                return;
            }

            switch (data.type) {
                case 'ready':
                    if (this.el.pdvBadge) this.el.pdvBadge.textContent = 'PDV: ' + (data.pdv || this.pdvCodigo);
                    break;
                case 'response':
                    this.handleAssistantReply(data);
                    break;
                case 'error':
                    this.handleAssistantError(data.message);
                    break;
                case 'status':
                case 'pong':
                default:
                    break; // El estado visual lo maneja la máquina de estados local
            }
        };

        this.ws.onclose = () => {
            this.stopHeartbeat();
            if (this.state === State.THINKING) {
                this.handleAssistantError('Se perdió la conexión. ¿Me repites tu pregunta?');
            }
            if (this.isOnline && this.reconnectAttempts < this.maxReconnect) {
                this.reconnectAttempts++;
                setTimeout(() => this.connectWebSocket(), 2000 * Math.min(this.reconnectAttempts, 5));
            }
        };

        this.ws.onerror = (err) => {
            console.error('WebSocket error:', err);
        };
    }

    startHeartbeat() {
        this.stopHeartbeat();
        this.heartbeatTimer = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 25000);
    }

    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.kioskApp = new KioskController();
});
