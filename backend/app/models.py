"""
Modelos Pydantic para validación estricta de requests.
Cada módulo del sistema tiene sus modelos claramente separados.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat y voz (Kiosco POP)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    context: Optional[List[Dict]] = []
    cultivo: Optional[str] = None
    zona: Optional[str] = None
    lead_id: Optional[int] = None
    fecha_siembra: Optional[str] = None
    punto_venta_id: Optional[str] = None   # código del PDV que origina la consulta


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "onyx"


# ---------------------------------------------------------------------------
# Leads / CRM
# ---------------------------------------------------------------------------

class LeadRequest(BaseModel):
    cultivo: str
    zona: str
    manzanas: Optional[str] = None
    fecha_siembra: Optional[str] = None
    problema: Optional[str] = None
    historial: Optional[str] = None
    canal: Optional[str] = None
    telefono: str
    productos_sugeridos: Optional[str] = None
    punto_venta_id: Optional[str] = None   # código del PDV
    nombre_productor: Optional[str] = None


class LeadUpdateRequest(BaseModel):
    estado_seguimiento: Optional[str] = None
    notas_seguimiento: Optional[str] = None
    agronomo_asignado: Optional[str] = None


# ---------------------------------------------------------------------------
# WhatsApp
# ---------------------------------------------------------------------------

class WhatsAppRequest(BaseModel):
    lead_id: int


# ---------------------------------------------------------------------------
# Cupones y campañas
# ---------------------------------------------------------------------------

class CouponRequest(BaseModel):
    lead_id: int
    discount_percent: float = 5.0
    expires_days: int = 7


class CampaignRequest(BaseModel):
    name: str
    channel: str
    budget: float


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


# ---------------------------------------------------------------------------
# Puntos de Venta (PDV)
# ---------------------------------------------------------------------------

class PDVRequest(BaseModel):
    codigo: str = Field(..., min_length=3, max_length=30,
                        description="Código único del PDV, ej: SANTA_ROSA_01")
    nombre: str
    municipio: Optional[str] = ""
    departamento: Optional[str] = ""
    direccion: Optional[str] = ""
    telefono: Optional[str] = ""


class PDVUpdateRequest(BaseModel):
    nombre: Optional[str] = None
    municipio: Optional[str] = None
    departamento: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    activo: Optional[bool] = None


class PDVAgronomoRequest(BaseModel):
    user_id: int
    es_responsable: bool = False


# ---------------------------------------------------------------------------
# Perfil de Agrónomo (extiende usuario)
# ---------------------------------------------------------------------------

class AgronomoProfileRequest(BaseModel):
    nombre: Optional[str] = None
    telefono_wa: Optional[str] = None
    especialidad: Optional[str] = None
    rol: Optional[str] = None   # 'admin' | 'agronomo' | 'operador'


# ---------------------------------------------------------------------------
# Escaladas a agrónomo humano
# ---------------------------------------------------------------------------

class EscaladaResolveRequest(BaseModel):
    respuesta: str
    estado: str = "respondida"   # 'respondida' | 'ignorada'


# ---------------------------------------------------------------------------
# Panel Admin sin código
# ---------------------------------------------------------------------------

class AdminMetricRequest(BaseModel):
    nombre: str
    descripcion: Optional[str] = ""
    tipo_grafico: str = "bar"      # 'bar' | 'pie' | 'line' | 'table' | 'number'
    dimension: str = "cultivo"     # columna por la que agrupar
    metrica: str = "leads"         # qué contar / sumar
    filtro_fecha: str = "30d"      # '7d' | '30d' | '90d' | 'all'
    orden: int = 0


class ProductCreateRequest(BaseModel):
    sku: str
    nombre: str
    categoria: str
    ingrediente_activo: Optional[str] = ""
    cultivos: Optional[str] = ""
    problemas: Optional[str] = ""
    dosis: Optional[str] = ""
    precio_hnl: float = 0.0
    stock: int = 0
    unidad: str = "Unidad"
    imagen_url: Optional[str] = ""
    descripcion: Optional[str] = ""


class ProductUpdateRequest(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    ingrediente_activo: Optional[str] = None
    cultivos: Optional[str] = None
    problemas: Optional[str] = None
    dosis: Optional[str] = None
    precio_hnl: Optional[float] = None
    stock: Optional[int] = None
    unidad: Optional[str] = None
    imagen_url: Optional[str] = None
    descripcion: Optional[str] = None


class DiseaseReferenceRequest(BaseModel):
    cultivo: str
    problema: str
    nombre_enfermedad: str
    nombre_cientifico: Optional[str] = ""
    descripcion_sintomas: Optional[str] = ""
    foto_url: Optional[str] = ""
    productos_recomendados_ids: Optional[str] = ""