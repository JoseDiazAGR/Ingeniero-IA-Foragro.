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
        if (this.recognition) {
            try { this.recognition.stop(); } catch(e){}
        }
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
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
                    this.playAudio(data.audio);
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

    playAudio(base64Audio) {
        try {
            const audio = new Audio("data:audio/mpeg;base64," + base64Audio);
            audio.play().catch(e => {
                console.warn("Autoplay bloqueado:", e);
            });
        } catch (e) {
            console.error("Error reproduciendo audio:", e);
        }
    }

    speakNative(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const cleanText = text.replace(/[*_#]/g, '');
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.lang = 'es-HN';
            utterance.rate = 1.0;
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
            this.btnMic.addEventListener('click', () => {
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
