# AGROBOT POP

## Objetivo

Crear un asesor agrícola inteligente para puntos de venta.

## Usuarios

- Agricultor
- Vendedor
- Gerente de marketing

## Componentes

- Frontend
- Backend
- OpenAI
- Base de datos
- WhatsApp

Con el servidor corriendo en http://localhost:8000:

Módulo	URL de Acceso	Descripción
Kiosco POP (Tablet)	http://localhost:8000/kiosk/?pdv=COP-01	Interfaz manos libres para la tablet en tienda
Panel de Administración (No-Code)	http://localhost:8000/admin-panel/	Gestión de inventario, métricas, reportes y escaladas
Dashboard CRM	http://localhost:8000/dashboard/	Historial de productores (Kiosco + WhatsApp), métricas y agrónomos
Documentación Interactiva (API)	http://localhost:8000/docs	Swagger para probar todos los endpoints
