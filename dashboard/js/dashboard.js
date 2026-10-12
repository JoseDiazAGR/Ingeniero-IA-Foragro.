/**
 * FORAGRO Dashboard & CRM Comercial v2.0 — Lógica de Interfaz
 */
(function () {
  "use strict";

  let currentEditingLeadId = null;
  let globalPdvId = null;

  const tagMap = {
    Radio: "tag-radio", TV: "tag-tv", Facebook: "tag-social",
    Amigo: "tag-friend", "Punto de venta": "tag-store", Otro: "tag-other",
  };

  const statusClassMap = {
    Nuevo: "status-nuevo", Contactado: "status-contactado",
    "Visita Técnica Agendada": "status-visita", "Venta Cerrada": "status-cerrada",
    "No Interesado": "status-no-interesado",
  };

  // ---- Navegación por Pestañas ----
  function initTabs() {
    const tabBtns = document.querySelectorAll(".tab-btn");
    const panes = document.querySelectorAll(".tab-pane");

    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        tabBtns.forEach((b) => b.classList.remove("active"));
        panes.forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        
        const targetId = btn.getAttribute("data-tab");
        const targetPane = document.getElementById(targetId);
        if (targetPane) targetPane.classList.add("active");

        if (targetId === "tabCRM") loadCRMLeads();
        if (targetId === "tabInventory") loadInventory();
        if (targetId === "tabAgronomos") loadAgronomos();
      });
    });
  }

  // =========================================================================
  // INIT PDV FILTER
  // =========================================================================
  async function loadPdvDropdown() {
      try {
          const res = await apiFetch('/api/pdv');
          const select = document.getElementById("globalPdvFilter");
          res.puntos_de_venta.forEach(pdv => {
              const opt = document.createElement("option");
              opt.value = pdv.id;
              opt.textContent = pdv.nombre + ` (${pdv.codigo})`;
              select.appendChild(opt);
          });
      } catch(e) { console.error("Error loading PDVs", e); }
  }

  document.getElementById("globalPdvFilter").addEventListener("change", (e) => {
      globalPdvId = e.target.value || null;
      loadMetrics();
      loadCRMLeads();
  });

  // =========================================================================
  // 1. CARGA DE MÉTRICAS Y REPORTES
  // =========================================================================
  async function loadMetrics() {
    try {
      const url = globalPdvId ? `/api/metrics?pdv_id=${globalPdvId}` : "/api/metrics";
      const data = await apiFetch(url);
      renderStats(data);
      renderCampaignChart(data.campaigns || {});
      renderCropsChart(data.cultivos || {});
      renderIssuesList(data.problemas || {});
      document.getElementById("tabLeadCount").textContent = data.leads || 0;
    } catch (err) {
      console.error("Error cargando métricas:", err);
    }
  }

  function renderStats(data) {
    document.getElementById("statLeads").textContent = data.leads || 0;
    document.getElementById("statManzanas").textContent = (data.total_manzanas || 0) + " mz";
    document.getElementById("statCoupons").textContent = data.coupons || 0;
    document.getElementById("statEscaladas").textContent = data.escaladas_pendientes || 0;
  }

  function renderCampaignChart(campaigns) {
    const total = Object.values(campaigns).reduce((a, b) => a + b, 0) || 1;
    const colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#6366f1", "#8b5cf6"];
    let chartHtml = "", tbody = "";

    Object.keys(campaigns).forEach((label, i) => {
      const val = campaigns[label];
      const pct = Math.round((val / total) * 100);
      const tag = tagMap[label] || "tag-other";

      chartHtml += `
        <div class="chart-bar">
          <div class="chart-label">${escapeHTML(label)}</div>
          <div class="chart-track"><div class="chart-fill" style="width:${pct}%;background:${colors[i % colors.length]}"></div></div>
          <div class="chart-value">${pct}%</div>
        </div>
      `;
      tbody += `<tr><td><span class="tag ${tag}">${escapeHTML(label)}</span></td><td><b>${val}</b></td><td>${pct}%</td><td>-</td></tr>`;
    });
    document.getElementById("campaignChart").innerHTML = chartHtml || '<div style="font-size:12px;">Sin datos</div>';
    document.getElementById("campaignBody").innerHTML = tbody || '<tr><td colspan="4">Sin datos</td></tr>';
  }

  function renderCropsChart(cultivos) {
    const total = Object.values(cultivos).reduce((a, b) => a + b, 0) || 1;
    const colors = ["#10b981", "#f59e0b", "#3b82f6", "#ef4444", "#8b5cf6", "#64748b"];
    let chartHtml = "";
    Object.keys(cultivos).forEach((crop, i) => {
      const pct = Math.round((cultivos[crop] / total) * 100);
      chartHtml += `
        <div class="chart-bar">
          <div class="chart-label">${escapeHTML(crop)}</div>
          <div class="chart-track"><div class="chart-fill" style="width:${pct}%;background:${colors[i % colors.length]}"></div></div>
          <div class="chart-value">${cultivos[crop]} (${pct}%)</div>
        </div>`;
    });
    document.getElementById("cropsChart").innerHTML = chartHtml || '<div style="font-size:12px;">Sin datos</div>';
  }

  function renderIssuesList(issues) {
    const container = document.getElementById("issuesList");
    let html = "";
    Object.keys(issues).forEach((iss) => html += `<span class="issue-chip">⚠️ ${escapeHTML(iss)} (${issues[iss]})</span>`);
    container.innerHTML = html || '<span>Sin incidencias</span>';
  }

  // =========================================================================
  // 2. CRM DE PRODUCTORES
  // =========================================================================
  async function loadCRMLeads() {
    const search = document.getElementById("crmSearchInput").value.trim();
    const cultivo = document.getElementById("crmFilterCultivo").value;
    const estado = document.getElementById("crmFilterEstado").value;

    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (cultivo) params.append("cultivo", cultivo);
    if (estado) params.append("estado", estado);
    if (globalPdvId) params.append("pdv_id", globalPdvId);

    try {
      const data = await apiFetch(`/api/leads?${params.toString()}`);
      renderCRMTable(data.leads || []);
    } catch (err) { console.error(err); }
  }

  function renderCRMTable(leads) {
    const tbody = document.getElementById("crmTableBody");
    if (!leads.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No se encontraron productores.</td></tr>';
      return;
    }

    let html = "";
    leads.forEach((l) => {
      const status = l.estado_seguimiento || "Nuevo";
      const statusClass = statusClassMap[status] || "status-nuevo";
      
      html += `
        <tr>
          <td>#${l.id}</td>
          <td><strong>${escapeHTML(l.pdv_nombre || "Global")}</strong><br><small>${l.pdv_codigo || ""}</small></td>
          <td><strong>${escapeHTML(l.nombre_productor || "Productor")}</strong><br><small>${l.zona || ""}</small></td>
          <td>${escapeHTML(l.cultivo || "-")}<br><small>${escapeHTML(l.problema || "General")}</small></td>
          <td><a href="https://wa.me/${(l.telefono||"").replace(/\D/g,"")}" target="_blank">${escapeHTML(l.telefono)}</a></td>
          <td><span class="status-badge ${statusClass}">${escapeHTML(status)}</span></td>
          <td><button class="btn btn-detail" data-lead-id="${l.id}">Abrir</button></td>
        </tr>`;
    });
    tbody.innerHTML = html;

    tbody.querySelectorAll(".btn-detail").forEach((btn) => {
      btn.addEventListener("click", () => openLeadModal(btn.getAttribute("data-lead-id")));
    });
  }

  // =========================================================================
  // 3. MODAL DE DETALLE (Kiosco + WhatsApp History)
  // =========================================================================
  async function openLeadModal(leadId) {
    currentEditingLeadId = leadId;
    const backdrop = document.getElementById("leadModalBackdrop");
    backdrop.classList.remove("hidden");

    try {
      const data = await apiFetch(`/api/leads/${leadId}`);
      const lead = data.lead;
      
      document.getElementById("modalLeadTitle").textContent = `${lead.nombre_productor || 'Productor'} #${lead.id}`;
      document.getElementById("modalLeadSub").textContent = `PDV: ${lead.pdv_nombre || 'N/D'} | ${new Date(lead.created_at).toLocaleString("es-HN")}`;
      
      document.getElementById("dCultivo").textContent = lead.cultivo || "-";
      document.getElementById("dZona").textContent = lead.zona || "-";
      document.getElementById("dManzanas").textContent = (lead.manzanas || "N/D") + " mz";
      document.getElementById("dProblema").textContent = lead.problema || "-";
      document.getElementById("dTelefono").textContent = lead.telefono || "-";
      document.getElementById("dCupon").textContent = lead.cupon || "-";

      document.getElementById("mEstadoSeguimiento").value = lead.estado_seguimiento || "Nuevo";
      document.getElementById("mAgronomoAsignado").value = lead.agronomo_asignado || "";
      document.getElementById("mNotasSeguimiento").value = lead.notas_seguimiento || "";

      // Historial Kiosco
      const kHist = document.getElementById("modalChatHistory");
      const convs = (data.conversations || []).filter(c => c.canal === 'kiosk' || !c.canal);
      kHist.innerHTML = convs.length ? convs.map(c => `
          <div class="wa-message ${c.role}"><strong>${c.role === 'user' ? '👤' : '🤖'}:</strong> ${escapeHTML(c.message)}</div>
      `).join('') : '<div style="color:#888;">Sin interacciones en Kiosco.</div>';

      // Historial WhatsApp
      const wHist = document.getElementById("modalWaHistory");
      wHist.innerHTML = data.whatsapp_history.length ? data.whatsapp_history.map(c => `
          <div class="wa-message ${c.role}"><strong>${c.role === 'user' ? '📞' : '📱'}:</strong> ${escapeHTML(c.message)}</div>
      `).join('') : '<div style="color:#888;">Sin historial en WhatsApp.</div>';
      wHist.scrollTop = wHist.scrollHeight;

    } catch (err) { console.error(err); }
  }

  function closeLeadModal() {
    document.getElementById("leadModalBackdrop").classList.add("hidden");
    currentEditingLeadId = null;
  }

  async function saveLeadFollowup() {
    if (!currentEditingLeadId) return;
    const payload = {
      estado_seguimiento: document.getElementById("mEstadoSeguimiento").value,
      agronomo_asignado: document.getElementById("mAgronomoAsignado").value,
      notas_seguimiento: document.getElementById("mNotasSeguimiento").value
    };
    try {
      await apiFetch(`/api/leads/${currentEditingLeadId}`, { method: "PUT", body: JSON.stringify(payload) });
      showToast("¡Actualizado!");
      closeLeadModal();
      loadCRMLeads();
    } catch (err) { console.error(err); }
  }

  // =========================================================================
  // 4. INVENTARIO DE BODEGA
  // =========================================================================
  async function loadInventory() {
    try {
      const data = await apiFetch("/api/inventory");
      const tbody = document.getElementById("inventoryTableBody");
      tbody.innerHTML = data.products.map(p => `
        <tr>
          <td><small>${p.sku}</small></td>
          <td><strong>${p.nombre}</strong></td>
          <td>${p.categoria}</td>
          <td>✅ Integrado</td>
          <td><small>${p.dosis || "Consultar"}</small></td>
          <td>L. ${p.precio_hnl}</td>
          <td style="color:${p.stock>10?'green':'red'}"><strong>${p.stock} uds</strong></td>
        </tr>
      `).join('');
    } catch (err) {}
  }

  // =========================================================================
  // 5. AGRÓNOMOS
  // =========================================================================
  async function loadAgronomos() {
      try {
          const res = await apiFetch('/api/agronomo-stats');
          const list = res.agronomos || res.agrónomos || [];
          grid.innerHTML = list.map(a => `
              <div class="agronomo-card">
                  <h3>👨‍🌾 ${a.nombre || a.username}</h3>
                  <p><small>${a.especialidad || 'Asesor Comercial'}</small></p>
                  <p>WhatsApp: <a href="https://wa.me/${(a.telefono_wa||"").replace(/\D/g,"")}" target="_blank">${a.telefono_wa || 'No configurado'}</a></p>
                  <hr style="margin:10px 0; border:0; border-top:1px solid #eee;">
                  <p><strong>Rendimiento:</strong></p>
                  <ul>
                      <li>Escaladas Pendientes: <strong style="color:red;">${a.escaladas_pendientes}</strong></li>
                      <li>Escaladas Resueltas: <strong style="color:green;">${a.escaladas_respondidas}</strong></li>
                      <li>Tiempo Promedio Respuesta: <strong>${a.tiempo_respuesta_horas || '-'} hrs</strong></li>
                  </ul>
                  <p><small>PDVs Asignados: ${a.pdvs.map(p=>p.nombre).join(', ')||'Ninguno'}</small></p>
              </div>
          `).join('');
      } catch(e) {}
  }

  // =========================================================================
  // EXPORTACIÓN A CSV & EVENTOS
  // =========================================================================
  function exportCSV() {
    let url = `/api/leads/export/csv`;
    if (globalPdvId) url += `?pdv_id=${globalPdvId}`;
    window.open((window.FORAGRO_CONFIG?.API_BASE || "") + url, "_blank");
  }

  initTabs();
  loadPdvDropdown();
  loadMetrics();
  loadCRMLeads();

  document.getElementById("refreshBtn").addEventListener("click", () => { loadMetrics(); loadCRMLeads(); });
  document.getElementById("exportCsvBtn").addEventListener("click", exportCSV);
  document.getElementById("logoutBtn").addEventListener("click", async () => {
      try { await apiFetch("/api/logout", { method: "POST" }); } catch(e){} window.location.href="login.html";
  });

  document.getElementById("crmSearchInput").addEventListener("input", debounce(loadCRMLeads, 400));
  document.getElementById("crmFilterCultivo").addEventListener("change", loadCRMLeads);
  document.getElementById("crmFilterEstado").addEventListener("change", loadCRMLeads);

  document.getElementById("modalCloseBtn").addEventListener("click", closeLeadModal);
  document.getElementById("btnSaveLeadCrm").addEventListener("click", saveLeadFollowup);
  document.getElementById("leadModalBackdrop").addEventListener("click", (e) => {
    if (e.target.id === "leadModalBackdrop") closeLeadModal();
  });

  function debounce(fn, ms) {
    let timer; return function (...args) { clearTimeout(timer); timer = setTimeout(() => fn.apply(this, args), ms); };
  }

})();
