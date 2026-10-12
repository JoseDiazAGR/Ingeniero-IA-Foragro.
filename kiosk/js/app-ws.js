/**
 * Controlador de WebSocket (Manos libres) para FORAGRO Kiosco v2.0
 * UX Simplificado: Pantalla de inicio limpia con botón de inicio y chat minimalista.
 */

class KioskController {
    constructor() {
        this.pdvCodigo = new URLSearchParams(window.location.search).get('pdv') || 'DEMO_01';
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnect = 15;
        this.context = { cultivo: null, zona: null };
        this.isOnline = navigator.onLine;
        this.heartbeatTimer = null;
        this.isConsultationActive = false;

        // Control de habla y anti-eco (Barge-in / Interrupción)
        this.isSpeaking = false;
        this.currentAudio = null;
        this.currentSpeakingText = "";
        
        // DOM Elements
        this.idleScreen = document.getElementById('idle-screen');
        this.activeScreen = document.getElementById('active-screen');
        this.btnStart = document.getElementById('btn-start');
        this.btnReset = document.getElementById('btn-reset');
        this.btnMic = document.getElementById('btn-mic');
        this.micHint = document.getElementById('mic-hint');
        this.statusText = document.getElementById('status-text');
        this.chatLog = document.getElementById('chat-log');
        this.pdvBadge = document.getElementById('pdv-badge');
        
        if (this.pdvBadge) {
            this.pdvBadge.textContent = 'PDV: ' + this.pdvCodigo;
        }

        this.initEventListeners();
        this.initNetworkListeners();
        this.connectWebSocket();
        this.initMicrophone();
    }

    initEventListeners() {
        if (this.btnStart) {
            this.btnStart.addEventListener('click', () => this.startConsultation());
        }
        if (this.btnReset) {
            this.btnReset.addEventListener('click', () => this.resetToIdle());
        }
        // Permitir interrumpir la voz del bot tocando la pantalla
        if (this.activeScreen) {
            this.activeScreen.addEventListener('click', (e) => {
                if (this.isSpeaking && e.target !== this.btnReset && !this.btnReset?.contains(e.target)) {
                    console.log("🛑 Cliente interrumpió al Agrobot tocando la pantalla.");
                    this.stopAudioPlayback();
                    this.updateStatus("Listo para hablar");
                }
            });
        }
    }

    startConsultation() {
        this.isConsultationActive = true;
        if (this.idleScreen) this.idleScreen.classList.add('hidden');
        if (this.activeScreen) this.activeScreen.classList.remove('hidden');

        // Mensaje inicial de bienvenida si está vacío
        if (this.chatLog && this.chatLog.children.length === 0) {
            const welcomeText = "¡Hola amigo productor! 👋 Soy el Ingeniero Agrónomo de FORAGRO. Cuéntame, ¿qué cultivo tienes y qué plaga o problema estás viendo en tu finca?";
            this.appendMessage('assistant', welcomeText);
            this.speakNative(welcomeText);
        }

        // Iniciar escucha del micrófono
        if (this.recognition) {
            try {
                this.recognition.start();
                this.updateMicState(true);
            } catch (e) {
                console.log("Mic ya estaba activo o requiere permiso", e);
            }
        }
    }

    resetToIdle() {
        this.isConsultationActive = false;
        if (this.activeScreen) this.activeScreen.classList.add('hidden');
        if (this.idleScreen) this.idleScreen.classList.remove('hidden');
        
        // Limpiar chat log para la siguiente persona
        if (this.chatLog) this.chatLog.innerHTML = '';
        this.context = { cultivo: null, zona: null };

        // Ocultar overlay si estaba abierto
        const overlay = document.getElementById('ui-overlay');
        if (overlay) overlay.classList.add('hidden');

        // Detener micrófono y audio
        this.stopAudioPlayback();
        if (this.recognition) {
            try { this.recognition.stop(); } catch(e){}
        }
        this.updateMicState(false);
    }

    initNetworkListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateStatus("En línea");
            this.connectWebSocket();
        });
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateStatus("Modo Offline");
            this.stopHeartbeat();
        });
    }

    updateStatus(text) {
        if (this.statusText) this.statusText.innerText = text;
    }

    updateMicState(isActive) {
        if (!this.btnMic) return;
        if (isActive) {
            this.btnMic.classList.add('active');
            if (this.micHint) this.micHint.innerHTML = "🎙️ <strong>Manos libres activo</strong> (habla con confianza)";
            this.updateStatus("Escuchando...");
        } else {
            this.btnMic.classList.remove('active');
            if (this.micHint) this.micHint.innerHTML = "Micrófono en pausa (toca para hablar)";
            this.updateStatus("En pausa");
        }
    }

    appendMessage(role, text) {
        if (!this.chatLog) return;
        const div = document.createElement('div');
        div.className = `message ${role}`;
        div.innerText = text;
        this.chatLog.appendChild(div);
        this.chatLog.scrollTop = this.chatLog.scrollHeight;
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

    connectWebSocket() {
        if (!this.isOnline) return;
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/api/chat-ws`);

        this.ws.onopen = () => {
            console.log("✅ WebSocket conectado.");
            this.reconnectAttempts = 0;
            this.ws.send(JSON.stringify({ type: 'init', pdv: this.pdvCodigo }));
            this.startHeartbeat();
            
            fetch('/api/offline-cache').catch(e => console.log('Offline cache fetch', e));
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'ready') {
                if (this.pdvBadge) this.pdvBadge.textContent = 'PDV: ' + (data.pdv || this.pdvCodigo);
            } else if (data.type === 'status') {
                this.updateStatus(data.status === 'pensando' ? 'Inge está pensando...' : 'Escuchando...');
            } else if (data.type === 'response') {
                this.updateStatus("Listo para hablar");
                this.appendMessage('assistant', data.reply);
                this.handleUiActions(data.ui_actions);
                
                if (data.audio) {
                    this.playAudio(data.audio, data.reply);
                } else {
                    this.speakNative(data.reply);
                }
            } else if (data.type === 'error') {
                this.updateStatus("Reintentando...");
                this.appendMessage('system', data.message);
            }
        };

        this.ws.onclose = () => {
            this.stopHeartbeat();
            if (this.isOnline && this.reconnectAttempts < this.maxReconnect) {
                this.reconnectAttempts++;
                setTimeout(() => this.connectWebSocket(), 2000 * Math.min(this.reconnectAttempts, 5));
            }
        };

        this.ws.onerror = (err) => {
            console.error("WebSocket error:", err);
        };
    }

    handleUiActions(actions) {
        if (!actions || !Array.isArray(actions)) return;
        for (const action of actions) {
            const event = new CustomEvent('kioskAction', { detail: action });
            window.dispatchEvent(event);
        }
    }

    stopAudioPlayback() {
        if (this.currentAudio) {
            try {
                this.currentAudio.pause();
                this.currentAudio.currentTime = 0;
            } catch (e) {}
            this.currentAudio = null;
        }
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
        this.isSpeaking = false;
        this.currentSpeakingText = "";
    }

    isEchoOfBot(transcript) {
        if (!this.currentSpeakingText) return false;

        const clean = (s) => (s || '')
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^a-z0-9\s]/g, " ")
            .replace(/\s+/g, " ")
            .trim();

        const cleanTranscript = clean(transcript);
        const cleanBot = clean(this.currentSpeakingText);

        if (!cleanTranscript) return true;

        // 1. Coincidencia directa por subcadena
        if (cleanBot.includes(cleanTranscript)) {
            return true;
        }

        // 2. Coincidencia por conjunto de palabras (si >50% de las palabras provienen de lo que el bot está diciendo)
        const transcriptWords = cleanTranscript.split(" ").filter(w => w.length > 2);
        if (transcriptWords.length === 0) return true;

        const botWords = new Set(cleanBot.split(" ").filter(w => w.length > 2));
        let matchCount = 0;
        for (const w of transcriptWords) {
            if (botWords.has(w)) matchCount++;
        }

        return (matchCount / transcriptWords.length) >= 0.5;
    }

    playAudio(base64Audio, replyText = "") {
        this.stopAudioPlayback();
        this.isSpeaking = true;
        this.currentSpeakingText = replyText;

        try {
            const audio = new Audio("data:audio/mpeg;base64," + base64Audio);
            this.currentAudio = audio;

            audio.onplay = () => {
                this.isSpeaking = true;
            };

            audio.onended = () => {
                this.currentAudio = null;
                // Margen de 400ms para disipar cualquier reverberación acústica en el micrófono
                setTimeout(() => {
                    this.isSpeaking = false;
                    this.currentSpeakingText = "";
                }, 400);
            };

            audio.onerror = () => {
                this.isSpeaking = false;
                this.currentSpeakingText = "";
            };

            audio.play().catch(e => {
                console.warn("Autoplay bloqueado:", e);
                this.isSpeaking = false;
            });
        } catch (e) {
            console.error("Error reproduciendo audio:", e);
            this.isSpeaking = false;
        }
    }

    speakNative(text) {
        this.stopAudioPlayback();
        if ('speechSynthesis' in window) {
            this.isSpeaking = true;
            this.currentSpeakingText = text;

            const cleanText = text.replace(/[*_#]/g, '');
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.lang = 'es-HN';
            utterance.rate = 1.0;

            utterance.onstart = () => {
                this.isSpeaking = true;
            };

            utterance.onend = () => {
                setTimeout(() => {
                    this.isSpeaking = false;
                    this.currentSpeakingText = "";
                }, 400);
            };

            utterance.onerror = () => {
                this.isSpeaking = false;
                this.currentSpeakingText = "";
            };

            window.speechSynthesis.speak(utterance);
        }
    }

    initMicrophone() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.warn("Speech Recognition no disponible.");
            if (this.micHint) this.micHint.innerText = "Utiliza el teclado en pantalla";
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'es-HN';
        this.recognition.continuous = true;
        this.recognition.interimResults = false;

        this.recognition.onresult = (event) => {
            const transcript = event.results[event.results.length - 1][0].transcript.trim();
            if (!transcript) return;

            // --- FILTRO ANTI-ECO Y BARGE-IN (INTERRUPCIÓN) ---
            if (this.isSpeaking) {
                if (this.isEchoOfBot(transcript)) {
                    console.log("🔇 Eco del Agrobot descartado (no procesar):", transcript);
                    return;
                }
                // Si el cliente dijo algo diferente, se detiene el habla inmediatamente
                console.log("🛑 Interrupción por voz detectada del cliente:", transcript);
                this.stopAudioPlayback();
                this.updateStatus("Interrumpido - Procesando...");
            }

            console.log("🎤 Reconocido:", transcript);
            this.appendMessage('user', transcript);
            this.sendMessage(transcript);
        };

        this.recognition.onend = () => {
            if (this.isConsultationActive && this.btnMic && this.btnMic.classList.contains('active')) {
                try { this.recognition.start(); } catch(e){}
            }
        };

        if (this.btnMic) {
            this.btnMic.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.isSpeaking) {
                    this.stopAudioPlayback();
                }
                if (this.btnMic.classList.contains('active')) {
                    this.updateMicState(false);
                    this.recognition.stop();
                } else {
                    this.updateMicState(true);
                    try { this.recognition.start(); } catch(e){}
                }
            });
        }
    }

    sendMessage(text) {
        if (this.isOnline && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'message',
                message: text,
                cultivo: this.context.cultivo,
                zona: this.context.zona
            }));
        } else {
            this.updateStatus("Procesando en modo offline...");
            const offlineResponse = window.offlineEngine.processMessage(text, this.context.cultivo);
            setTimeout(() => {
                this.updateStatus("Listo para hablar");
                this.appendMessage('assistant', offlineResponse.reply);
                this.speakNative(offlineResponse.reply);
                this.handleUiActions(offlineResponse.ui_actions);
            }, 300);
        }
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.kioskApp = new KioskController();
});
