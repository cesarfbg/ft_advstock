# Inventario Avanzado (Feral Tech)

**Versión:** 16.0.1.0.0
**Compatibilidad:** Odoo 16 Community & Enterprise
**Autor:** [Feral Tech](https://feraltech.co)

---

## Descripción

**Inventario Avanzado** es un módulo de reportes que proporciona herramientas de análisis para la gestión de inventarios. Permite evaluar la rotación de productos, identificar stock de baja rotación y tomar decisiones informadas sobre reabastecimiento.

---

## Funcionalidades

### Reporte de Rotación de Inventarios

Accesible desde **Inventario > Reportes > Inventario Avanzado > Rotación de Inventarios**.

Este reporte analiza el movimiento de tus productos dentro de un rango de fechas seleccionado y muestra:

| Indicador | Descripción |
|-----------|-------------|
| **Saliente Total** | Cantidad total vendida/despachada en el periodo |
| **Saliente Prom./Mes** | Promedio mensual de salidas (consumo promedio) |
| **Entrante Pendiente** | Cantidad en órdenes pendientes por recibir |
| **Stock a la Mano** | Inventario actual disponible |
| **Rotación (Meses)** | Cuántos meses de inventario tienes disponible |
| **Rotación (Días)** | Equivalente en días |

#### Filtros disponibles

- **Rango de fechas**: Define el periodo de análisis (ej: últimos 6 meses).
- **Ubicaciones**: Filtra por bodegas o ubicaciones específicas.
- **Con Salidas**: Muestra solo productos que tuvieron movimiento.
- **Con Stock**: Muestra solo productos con inventario positivo.
- **Agrupación**: Agrupa resultados por producto o categoría.

#### Presets de ubicación

Puedes guardar combinaciones de ubicaciones que usas frecuentemente con un nombre personalizado y cargarlas rápidamente en futuros reportes. Ideal si manejas múltiples bodegas y necesitas analizarlas por grupos.

### Planeación de Reorden (Proximamente)

Funcionalidad en desarrollo que permitirá planificar compras basándose en los datos de rotación de inventario.

---

## Cómo usar

1. Ve a **Inventario > Reportes > Inventario Avanzado > Rotación de Inventarios**.
2. Selecciona el **rango de fechas** que deseas analizar.
3. (Opcional) Filtra por **ubicaciones** o carga un preset guardado.
4. Haz clic en **Generar Reporte**.
5. Analiza los resultados en la vista de lista. Usa los filtros y agrupaciones para enfocarte en lo que necesitas.

---

## Configuración

1. Navega a **Ajustes > Feral Tech > Inventario Avanzado**.
2. Ingresa el **token de licencia** proporcionado por Feral Tech.

---

## Requisitos

- Odoo 16 (Community o Enterprise).
- Módulos de Odoo: **Inventario**, **Compras**, **Contabilidad**.
- Licencia activa de Feral Tech.

---

## Soporte

- Web: [https://feraltech.co](https://feraltech.co)
- Email: soporte@feraltech.co
