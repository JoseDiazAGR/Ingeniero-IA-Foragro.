/**
 * FORAGRO ChatAgro POP — Cliente Conversacional para Tablet (WebSockets)
 * ---------------------------------------------------------------------------
 * Agente en punto de venta con voz de ultra-baja latencia, Function Calling,
 * galería visual de patología fitosanitaria, captura por cámara,
 * consulta de inventario en bodega y registro CRM con WhatsApp.
 * ---------------------------------------------------------------------------
 */
(function () {
  "use strict";

  // ---- Estado de la sesión del agricultor ----
  let leadData = {
    cultivo: "",
    zona: "",
    manzanas: "",
    fecha_siembra: "",
    problema: "",
    historial: "",
    canal: "Punto de venta",
    telefono: "",
    cupon: "",
  };

  let currentLeadId = null;
  let isListening = false;
  let isSpeaking = false;
  let recognition = null;
  let currentAudio = null;
  let socket = null; // Canal permanente WebSockets
  let estadoConversacion = "inactivo";

  // ---- Referencias al DOM ----
  const kiosk = document.getElementById("kiosk");
  const startScreen = document.getElementById("startScreen");
  const chatArea = document.getElementById("chatArea");
  const extraContent = document.getElementById("extraContent");
  const optionsRow = document.getElementById("optionsRow");
  const controlsBar = document.getElementById("controlsBar");
  const inputRow = document.getElementById("inputRow");
  const avatarRing = document.getElementById("avatarRing");
  const voiceWaves = document.getElementById("voiceWaves");
  const micBtn = document.getElementById("micBtn");
  const restartBtn = document.getElementById("restartBtn");
  const talkBtn = document.getElementById("talkBtn");
  const talkBtnLabel = document.getElementById("talkBtnLabel");
  const cameraBtn = document.getElementById("cameraBtn");
  const cameraInput = document.getElementById("cameraInput");
  const keyboardBtn = document.getElementById("keyboardBtn");

  const config = window.FORAGRO_CONFIG || {};
  const apiBase = config.API_BASE || "http://localhost:8000";
  // Cambiar protocolo HTTP por WS
  const wsBase = apiBase.replace(/^http/, "ws"); 

  // ---- Inicializar Conexión WebSocket (Primer Toque) ----
  function iniciarKioscoAgrobot() {
    if (estadoConversacion !== "inactivo") return;

    estadoConversacion = "conectando";
    if (talkBtnLabel) talkBtnLabel.textContent = "Conectando...";

    socket = new WebSocket(`${wsBase}/api/chat-ws`);

    socket.onopen = function () {
      estadoConversacion = "activo";
      // Ocultar pantalla de inicio si aplica y activar interfaz
      if (startScreen) startScreen.classList.add("hidden");
      if (chatArea) chatArea.classList.remove("hidden");
      if (controlsBar) controlsBar.classList.remove("hidden");
      
      console.log("📱 Kiosco conectado mediante WebSocket.");
      solicitarEscuchaAutomatica();
    };

    socket.onmessage = function (event) {
      const data = JSON.parse(event.data);

      if (data.type === "status" && data.status === "pensando") {
        showTyping();
        return;
      }

      if (data.type === "response") {
        hideTyping();
        
        if (data.lead_id) {
          currentLeadId = data.lead_id;
        }

        // Pintar respuesta en pantalla y guardarla en el log de UI
        addMessageBubble(data.reply, false);

        // Disparar las tools/acciones visuales (carruseles, cupones, etc.)
        if (data.ui_actions && data.ui_actions.length > 0) {
          ejecutarAccionesDePantalla(data.ui_actions);
        }

        // Reproducir el audio Base64 que devolvió el backend de manera fluida
        if (data.audio) {
          reproducirAudioWS(data.audio);
        } else {
          // Si por algún motivo falló el audio de la IA, volver a escuchar tras 3 segundos
          setTimeout(solicitarEscuchaAutomatica, 3000);
        }
      }
    };

    socket.onclose = function () {
      estadoConversacion = "inactivo";
      avatarRing.classList.remove("listening", "speaking");
      if (talkBtnLabel) talkBtnLabel.textContent = "Iniciar";
      console.warn("🔌 Desconectado del servidor WebSocket de FORAGRO.");
    };

    socket.onerror = function (error) {
      console.error("Error en WebSocket:", error);
      hideTyping();
    };
  }

  // ---- Inicializar Reconocimiento de Voz del Navegador (STT) ----
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = "es-HN";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = function () {
      isListening = true;
      avatarRing.classList.add("listening");
      talkBtn.classList.add("listening");
      if (talkBtnLabel) talkBtnLabel.textContent = "Escuchando...";
    };

    recognition.onresult = function (event) {
      const transcript = event.results[0][0].transcript;
      if (transcript && transcript.trim()) {
        handleUserMessage(transcript.trim());
      }
    };

    recognition.onerror = function (event) {
      console.warn("Speech recognition notice:", event.error);
      stopListening();
      // Si el cliente no habló o se canceló, reabrir escucha automática
      if (event.error === 'no-speech') {
        solicitarEscuchaAutomatica();
      }
    };

    recognition.onend = function () {
      stopListening();
    };
  }

  function solicitarEscuchaAutomatica() {
    if (isSpeaking && currentAudio) {
      currentAudio.pause();
      isSpeaking = false;
      avatarRing.classList.remove("speaking");
    }
    if (window.speechSynthesis) window.speechSynthesis.cancel();

    if (recognition && estadoConversacion === "active" || estadoConversacion === "activo") {
      try {
        recognition.start();
      } catch (e) {
        console.warn("Speech recognition already active:", e);
      }
    }
  }

  function stopListening() {
    isListening = false;
    avatarRing.classList.remove("listening");
    talkBtn.classList.remove("listening");
    if (talkBtnLabel) talkBtnLabel.textContent = "Hablar";
    if (recognition) {
      try {
        recognition.stop();
      } catch (e) {}
    }
  }

  // ---- Reproductor de audio WebSocket + Manos Libres Continuo ----
  function reproducirAudioWS(audioB64) {
    if (currentAudio) currentAudio.pause();
    if (window.speechSynthesis) window.speechSynthesis.cancel();

    const audioUrl = "data:audio/mpeg;base64," + audioB64;
    currentAudio = new Audio(audioUrl);
    isSpeaking = true;
    avatarRing.classList.add("speaking");

    currentAudio.onended = function () {
      isSpeaking = false;
      avatarRing.classList.remove("speaking");
      console.log("El ingeniero terminó de hablar. Reabriendo micrófono automáticamente.");
      // 🔥 REAPERTURA AUTOMÁTICA DEL MICRÓFONO
      solicitarEscuchaAutomatica();
    };

    currentAudio.onerror = function () {
      isSpeaking = false;
      avatarRing.classList.remove("speaking");
      solicitarEscuchaAutomatica();
    };

    currentAudio.play().catch(err => {
      console.error("Error reproduciendo audio por WS:", err);
      fallbackSpeechSynthesis(document.getElementById("chat-box")?.innerText || "", solicitarEscuchaAutomatica);
    });
  }

  function fallbackSpeechSynthesis(text, callback) {
    if (!window.speechSynthesis) {
      if (callback) callback();
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "es-HN";
    utterance.rate = 1.05;

    const voices = window.speechSynthesis.getVoices();
    const esVoice = voices.find((v) => v.lang.startsWith("es") && (v.name.includes("Male") || v.name.includes("Jorge") || v.name.includes("Raul")));
    if (esVoice) utterance.voice = esVoice;

    isSpeaking = true;
    avatarRing.classList.add("speaking");

    utterance.onend = function () {
      isSpeaking = false;
      avatarRing.classList.remove("speaking");
      if (callback) callback();
    };
    utterance.onerror = function () {
      isSpeaking = false;
      avatarRing.classList.remove("speaking");
      if (callback) callback();
    };

    window.speechSynthesis.speak(utterance);
  }

  // ---- Despachador de mensajes hacia el WebSocket ----
  function handleUserMessage(text) {
    if (!text) return;
    
    // Imprimir mensaje del usuario en la tablet
    addMessageBubble(text, true);

    // Enviar el paquete estructurado al WebSocket
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(json.stringify({
        message: text,
        cultivo: leadData.cultivo,
        zona: leadData.zona,
        lead_id: currentLeadId
      }));
    } else {
      console.error("Error: WebSocket no está abierto. Estado:", socket ? socket.readyState : "nulo");
    }
  }

  // ---- Renderizado de Mensajes en Pantalla ----
  function addMessageBubble(text, isUser) {
    const div = document.createElement("div");
    div.className = "msg-bubble " + (isUser ? "user" : "agent");
    div.textContent = text;
    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
  }

  function showTyping() {
    if (document.getElementById("typingBubble")) return;
    const div = document.createElement("div");
    div.className = "msg-bubble agent typing";
    div.id = "typingBubble";
    div.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
  }

  function hideTyping() {
    const t = document.getElementById("typingBubble");
    if (t) t.remove();
  }

  function showQuickOptions(options, onSelect) {
    optionsRow.innerHTML = "";
    if (!options || !options.length) {
      optionsRow.classList.add("hidden");
      return;
    }
    optionsRow.classList.remove("hidden");
    options.forEach((opt) => {
      const btn = document.createElement("button");
      btn.type = "button";
