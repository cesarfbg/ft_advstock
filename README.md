# Inventario Avanzado (Feral Tech)

**Versión:** 16.0.2.0.0
**Compatibilidad:** Odoo 16 Community & Enterprise
**Autor:** [Feral Tech](https://feraltech.co)

---

## Descripción

**Inventario Avanzado** es un módulo de reportes que proporciona herramientas de análisis para la gestión de inventarios. Permite evaluar la rotación de productos, identificar stock de baja o alta rotación mediante un sistema de semáforo visual, y tomar decisiones informadas sobre reabastecimiento.

---

## Funcionalidades

### Reporte de Rotación de Inventarios

Accesible desde **Inventario > Reportes > Inventario Avanzado > Rotación de Inventarios**.

Este reporte analiza el movimiento de tus productos dentro de un rango de fechas seleccionado y muestra:

| Indicador | Descripción |
|-----------|-------------|
| **Flag** | Semáforo visual (🟢🟡🔴) con flecha de tendencia (↑↓) |
| **Producto** | Nombre del producto (clic para abrir la ficha del producto) |
| **Saliente Total** | Cantidad total vendida/despachada en el periodo |
| **Saliente Prom./Mes** | Promedio mensual basado en días exactos del rango |
| **Entrante Pendiente** | Cantidad en órdenes pendientes por recibir |
| **Stock a la Mano** | Inventario actual disponible |
| **Rotación (Meses)** | Cuántos meses de inventario tienes considerando stock + entrante |
| **Rotación (Días)** | Equivalente en días (9999 cuando no hay ventas) |

Todas las columnas numéricas son ordenables de mayor a menor y viceversa.

#### Cálculo del promedio mensual

El promedio mensual se calcula con precisión basada en los **días exactos** del rango seleccionado:

```
promedio_mensual = saliente_total / días_en_rango × 30
```

Esto asegura que un rango de 45 días con 22 ventas dé un promedio de 14.67/mes, no 11/mes como daría al dividir por 2 meses calendario.

#### Fórmula de rotación

La rotación se calcula incluyendo tanto el stock actual como el inventario entrante pendiente:

```
rotación_meses = (stock_a_la_mano + entrante_pendiente) / promedio_mensual
rotación_días = rotación_meses × 30
```

Cuando un producto tiene stock pero cero ventas en el período, la rotación se muestra como 9999 (tanto en días como en meses) para indicar rotación nula y permitir el ordenamiento correcto.

#### Entrante futuro

El wizard permite opcionalmente **extender la ventana de búsqueda del inventario entrante** más allá del período de análisis de ventas. Esto es útil para incluir órdenes de compra que llegarán en un futuro cercano:

1. Marca la opción **"Incluir Entrante Futuro"**.
2. Indica la **Fecha Tope Entrante** (debe ser igual o posterior a la fecha fin del período).
3. Las ventas se calculan usando el rango original, pero el entrante incluye movimientos pendientes hasta la fecha tope.

#### Mostrar decimales

En los ajustes del módulo se puede activar o desactivar la opción **"Mostrar Decimales"**:

- **Activado**: todas las columnas numéricas del reporte muestran **2 decimales**.
- **Desactivado** (por defecto): los números se redondean a **enteros** sin mostrar `,00`.

En ambos modos las columnas permanecen ordenables.

### Sistema de Semáforo (Flags)

Cada producto en el reporte muestra un indicador visual basado en sus días de rotación:

| Flag | Significado |
|------|-------------|
| 🟢 | Rotación saludable (dentro del rango verde) |
| 🟡 ↓ | Alerta por déficit de stock (rotación baja, entre amarillo min y verde min) |
| 🟡 ↑ | Alerta por exceso de stock (rotación alta, entre verde max y amarillo max) |
| 🔴 ↓ | Crítico por déficit (rotación por debajo del amarillo min) |
| 🔴 ↑ | Crítico por exceso (rotación por encima del amarillo max) |

Las filas del reporte se decoran con colores de fondo según el semáforo y se pueden filtrar y agrupar por color.

#### Configuración de rangos predeterminados

En **Ajustes > Feral Tech > Inventario Avanzado** (sección derecha), configura los 4 límites:

| Campo | Default | Descripción |
|-------|---------|-------------|
| Amarillo Min | 25 días | Por debajo → rojo ↓ |
| Verde Min | 30 días | Inicio del rango saludable |
| Verde Max | 60 días | Fin del rango saludable |
| Amarillo Max | 65 días | Por encima → rojo ↑ |

Validaciones automáticas aseguran que: Amarillo Min < Verde Min < Verde Max < Amarillo Max.

#### Flags personalizadas por producto

Es posible configurar rangos de rotación específicos para productos individuales que tienen comportamientos diferentes al estándar. Accesible desde:

- **Inventario > Configuración > Inventario Avanzado > Flags de Rotación** (gestión masiva en lista editable).
- **Botón "Configurar Flags por Producto"** en los ajustes de Inventario Avanzado.
- **Pestaña "Inventario"** dentro de la ficha de cada producto (checkbox "Usar Flags de Rotación Personalizadas" + 4 campos de rangos).

Los tres puntos de acceso operan sobre el mismo modelo, por lo que los cambios se sincronizan automáticamente. Los productos con configuración personalizada usan sus propios rangos; el resto usa los valores predeterminados de la compañía. En entornos multi-compañía, cada compañía gestiona su propia configuración de flags por producto.

### Filtros y agrupaciones

- **Con Salidas**: Muestra solo productos que tuvieron movimiento.
- **Con Stock**: Muestra solo productos con inventario positivo.
- **Por color de semáforo**: Filtra por rojo, amarillo o verde.
- **Agrupación**: Por producto, categoría o semáforo.

### Presets de ubicación

Puedes guardar combinaciones de ubicaciones que usas frecuentemente con un nombre personalizado y cargarlas rápidamente en futuros reportes. Ideal si manejas múltiples bodegas y necesitas analizarlas por grupos.

### Planeación de Reorden (Próximamente)

Funcionalidad en desarrollo que permitirá planificar compras basándose en los datos de rotación de inventario.

---

## Cómo usar

1. Ve a **Inventario > Reportes > Inventario Avanzado > Rotación de Inventarios**.
2. Selecciona el **rango de fechas** que deseas analizar.
3. (Opcional) Marca **Incluir Entrante Futuro** e indica una fecha tope.
4. (Opcional) Filtra por **ubicaciones** o carga un preset guardado.
5. Haz clic en **Generar Reporte**.
6. Analiza los resultados en la vista de lista. Los colores del semáforo te indican rápidamente qué productos necesitan atención.
7. Haz clic en el nombre de un producto para abrir su ficha directamente.
8. Ordena por cualquier columna numérica haciendo clic en el encabezado.

---

## Configuración

1. Navega a **Ajustes > Feral Tech > Inventario Avanzado**.
2. Ingresa el **token de licencia** proporcionado por Feral Tech.
3. (Opcional) Activa **Mostrar Decimales** para ver 2 decimales en los reportes.
4. Configura los **rangos del semáforo** (Amarillo Min, Verde Min, Verde Max, Amarillo Max).
5. (Opcional) Configura **flags por producto** desde el botón en ajustes, desde **Inventario > Configuración > Inventario Avanzado > Flags de Rotación**, o directamente en la ficha de cada producto.

---

## Requisitos

- Odoo 16 (Community o Enterprise).
- Módulos de Odoo: **Inventario**, **Compras**, **Contabilidad**.
- Módulo base: **feral_tech_base**.
- Licencia activa de Feral Tech.

---

## Soporte

- Web: [https://feraltech.co](https://feraltech.co)
- Email: soporte@feraltech.co
