/**
 * Panel de Administración - Lógica Frontend
 */

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadProducts();
    loadEscaladas();
    
    // Bindings
    document.getElementById('btn-new-product').addEventListener('click', openProductModal);
    document.getElementById('btn-new-metric').addEventListener('click', openMetricModal);
    document.getElementById('btn-modal-close').addEventListener('click', closeModal);
    
    document.getElementById('export-form').addEventListener('submit', handleExport);
});

function initTabs() {
    const tabs = document.querySelectorAll('.nav-item[data-tab]');
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            
            tab.classList.add('active');
            const target = tab.getAttribute('data-tab');
            document.getElementById(`tab-${target}`).classList.add('active');
            
            if (target === 'products') loadProducts();
            if (target === 'metrics') loadMetricsInfo();
            if (target === 'escaladas') loadEscaladas();
        });
    });
}

// --- PRODUCTOS ---
async function loadProducts() {
    try {
        const res = await fetch('/api/products');
        const data = await res.json();
        const tbody = document.querySelector('#products-table tbody');
        tbody.innerHTML = '';
        
        data.products.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${p.sku}</td>
                <td>${p.nombre}</td>
                <td>${p.categoria}</td>
                <td>L. ${p.precio_hnl}</td>
                <td>${p.stock}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="editProduct(${p.id})"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-danger btn-sm" onclick="deleteProduct(${p.id})"><i class="fas fa-trash"></i></button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading products", e);
    }
}

function openProductModal() {
    document.getElementById('modal-title').innerText = "Nuevo Producto";
    document.getElementById('modal-body').innerHTML = `
        <form id="product-form">
            <div class="form-group"><label>SKU</label><input type="text" id="p-sku" required></div>
            <div class="form-group"><label>Nombre</label><input type="text" id="p-nombre" required></div>
            <div class="form-group"><label>Categoría</label><input type="text" id="p-cat" required></div>
            <div class="form-group"><label>Precio HNL</label><input type="number" id="p-precio" required></div>
            <div class="form-group"><label>Stock Inicial</label><input type="number" id="p-stock" value="100" required></div>
        </form>
    `;
    const btnSave = document.getElementById('btn-modal-save');
    btnSave.onclick = saveProduct;
    document.getElementById('modal-overlay').classList.remove('hidden');
}

async function saveProduct() {
    const payload = {
        sku: document.getElementById('p-sku').value,
        nombre: document.getElementById('p-nombre').value,
        categoria: document.getElementById('p-cat').value,
        precio_hnl: parseFloat(document.getElementById('p-precio').value),
        stock: parseInt(document.getElementById('p-stock').value),
        unidad: "unidad"
    };
    
    try {
        await fetch('/api/admin/products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        closeModal();
        loadProducts();
    } catch (e) {
        alert("Error guardando producto");
    }
}

// Mock placeholders para funciones que se llaman en onClick
window.editProduct = (id) => alert("Editar producto " + id);
window.deleteProduct = async (id) => {
    if(!confirm("¿Seguro de eliminar este producto?")) return;
    await fetch('/api/admin/products/' + id, { method: 'DELETE' });
    loadProducts();
};

// --- MÉTRICAS ---
async function loadMetricsInfo() {
    try {
        const res = await fetch('/api/admin/schema-info');
        window.schemaInfo = await res.json();
        const metricsRes = await fetch('/api/admin/metrics-custom');
        const data = await metricsRes.json();
        
        const grid = document.getElementById('metrics-grid');
        grid.innerHTML = '';
        data.metrics.forEach(m => {
            const div = document.createElement('div');
            div.className = 'metric-card';
            div.innerHTML = `
                <h3>${m.nombre}</h3>
                <p class="tag">${m.metrica} x ${m.dimension}</p>
                <button class="btn btn-secondary" style="margin-top:10px" onclick="deleteMetric(${m.id})">Eliminar</button>
            `;
            grid.appendChild(div);
        });
    } catch(e) {}
}

function openMetricModal() {
    document.getElementById('modal-title').innerText = "Nueva Métrica Personalizada";
    
    let html = `<form id="metric-form">
        <div class="form-group"><label>Nombre del Gráfico</label><input type="text" id="m-nombre" required></div>
        <div class="form-group"><label>Métrica</label><select id="m-metrica">`;
    window.schemaInfo.metricas.forEach(m => html += `<option value="${m.key}">${m.label}</option>`);
    html += `</select></div><div class="form-group"><label>Dimensión (Agrupar por)</label><select id="m-dim">`;
    window.schemaInfo.dimensiones.forEach(d => html += `<option value="${d.key}">${d.label}</option>`);
    html += `</select></div><div class="form-group"><label>Periodo</label><select id="m-fecha">`;
    window.schemaInfo.filtros_fecha.forEach(f => html += `<option value="${f.key}">${f.label}</option>`);
    html += `</select></div></form>`;
    
    document.getElementById('modal-body').innerHTML = html;
    document.getElementById('btn-modal-save').onclick = saveMetric;
    document.getElementById('modal-overlay').classList.remove('hidden');
}

async function saveMetric() {
    const payload = {
        nombre: document.getElementById('m-nombre').value,
        metrica: document.getElementById('m-metrica').value,
        dimension: document.getElementById('m-dim').value,
        filtro_fecha: document.getElementById('m-fecha').value,
        tipo_grafico: 'bar',
        descripcion: ''
    };
    try {
        const res = await fetch('/api/admin/metrics-custom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if(res.ok) { closeModal(); loadMetricsInfo(); }
        else { alert("Combinación no soportada"); }
    } catch(e) { console.error(e); }
}
window.deleteMetric = async (id) => {
    if(!confirm("¿Eliminar?")) return;
    await fetch('/api/admin/metrics-custom/' + id, { method: 'DELETE' });
    loadMetricsInfo();
}

// --- REPORTES ---
function handleExport(e) {
    e.preventDefault();
    const tipo = document.getElementById('export-type').value;
    const dias = document.getElementById('export-days').value;
    window.location.href = `/api/admin/report?tipo=${tipo}&dias=${dias}&formato=csv`;
}

// --- ESCALADAS ---
async function loadEscaladas() {
    try {
        const res = await fetch('/api/admin/escaladas');
        const data = await res.json();
        const tbody = document.querySelector('#escaladas-table tbody');
        tbody.innerHTML = '';
        
        data.escaladas.forEach(e => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${e.created_at.split('T')[0]}</td>
                <td>${e.pdv_nombre || 'General'}</td>
                <td>${e.nombre_productor || e.telefono}</td>
                <td><small>${e.pregunta}</small></td>
                <td><strong>${e.estado.toUpperCase()}</strong></td>
                <td>${e.agronomo_nombre || 'N/A'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {}
}

function closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
}
