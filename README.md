# Inventario Avanzado (Feral Tech)

**Version:** 16.0.4.0.0
**Compatibilidad:** Odoo 16 Community & Enterprise
**Autor:** [Feral Tech](https://feraltech.co)

---

## Descripcion

**Inventario Avanzado** es una suite de herramientas de analisis y planeacion para la gestion de inventarios. Permite evaluar la rotacion de productos, planificar compras con proyecciones mensuales, consultar el inventario historico a cualquier fecha, y tomar decisiones informadas sobre reabastecimiento con un sistema visual de alertas por colores.

---

## Funcionalidades

### 1. Rotacion de Inventarios

Accesible desde **Inventario > Reportes > Inventario Avanzado > Rotacion de Inventarios**.

Analiza el movimiento de tus productos dentro de un rango de fechas y muestra indicadores clave:

| Columna | Descripcion |
|---------|-------------|
| **Flag** | Indicador visual con color y tendencia (ver seccion Flags) |
| **Producto** | Nombre del producto (clic para abrir la ficha) |
| **Categoria** | Categoria del producto (columna opcional) |
| **Saliente Total** | Cantidad total despachada en el periodo |
| **Saliente Prom./Mes** | Promedio mensual basado en dias exactos del rango |
| **Entrante Pendiente** | Cantidad en ordenes pendientes por recibir |
| **Stock a la Mano** | Inventario actual disponible |
| **Rotacion (Meses)** | Meses de inventario disponibles al ritmo actual |
| **Rotacion (Dias)** | Equivalente en dias (9999 indica rotacion nula) |

Todas las columnas numericas son ordenables.

#### Calculo del promedio mensual

```
promedio_mensual = saliente_total / dias_en_rango x 30
```

Esto asegura precision con cualquier rango de fechas, ya que se basa en los dias exactos del periodo seleccionado.

#### Formula de rotacion

```
rotacion_meses = (stock_a_la_mano + entrante_pendiente) / promedio_mensual
rotacion_dias = rotacion_meses x 30
```

Cuando un producto tiene stock pero cero ventas, la rotacion se muestra como **9999** para indicar rotacion nula y permitir el ordenamiento correcto.

#### Entrante futuro

El wizard permite extender la ventana de busqueda del inventario entrante mas alla del periodo de analisis:

1. Marca la opcion **"Incluir Entrante Futuro"**.
2. Indica la **Fecha Tope Entrante** (debe ser igual o posterior a la fecha fin).
3. Las ventas se calculan con el rango original, pero el entrante incluye movimientos pendientes hasta la fecha tope.

### 2. Sistema de Flags

Cada producto muestra un indicador visual basado en sus dias de rotacion:

| Flag | Significado |
|------|-------------|
| 🟢 | Rotacion saludable (dentro del rango verde) |
| 🟡 ↓ | Alerta por deficit de stock |
| 🟡 ↑ | Alerta por exceso de stock |
| 🔴 ↓ | Critico por deficit |
| 🔴 ↑ | Critico por exceso |

Las filas del reporte se decoran con colores de fondo segun el flag. Se pueden filtrar y agrupar por color.

#### Configuracion de rangos

En **Ajustes > Feral Tech > Inventario Avanzado**, configura los 4 limites:

| Campo | Default | Descripcion |
|-------|---------|-------------|
| Amarillo Min | 25 dias | Por debajo -> rojo ↓ |
| Verde Min | 30 dias | Inicio del rango saludable |
| Verde Max | 60 dias | Fin del rango saludable |
| Amarillo Max | 65 dias | Por encima -> rojo ↑ |

Validaciones automaticas aseguran que: Amarillo Min < Verde Min < Verde Max < Amarillo Max.

#### Flags personalizadas por producto

Configura rangos especificos para productos con comportamiento diferente al estandar:

- **Inventario > Configuracion > Inventario Avanzado > Flags de Rotacion** (lista editable).
- **Boton "Configurar Flags por Producto"** en los ajustes.
- **Pestana "Inventario"** en la ficha de cada producto.

Los tres accesos operan sobre el mismo modelo y se sincronizan automaticamente.

### 3. Planeacion de Compras

Accesible desde **Inventario > Reportes > Inventario Avanzado > Planeacion de Compras**.

Herramienta de planificacion que muestra una grilla de 11 meses (5 anteriores + actual + 5 futuros) por producto con las siguientes metricas:

| Fila | Descripcion | Editable |
|------|-------------|----------|
| **Inv. Inicial** | Stock al inicio de cada mes | No |
| **Transito** | Recepciones de compras confirmadas/realizadas | No |
| **Pronostico de Compras** | Cantidad que planeas comprar | Si |
| **Inv. Total** | Inv. Inicial + Transito + Pronostico de Compras | No |
| **Pronostico de Ventas** | Cantidad que esperas vender | Si |
| **Venta Real** | Ventas efectivamente realizadas (meses pasados) | No |
| **Inv. Final** | Inv. Total - Pronostico de Ventas | No |
| **Dias de Inventario** | Dias de cobertura con flag de color | No |

#### Caracteristicas de la planeacion

- **Navegacion mensual** con botones para desplazar la ventana temporal.
- **Pronosticos editables** directamente en la grilla.
- **Exportacion a Excel** con formato y colores.
- **Exclusion de ubicaciones** configurable en ajustes (ej: excluir bodega de vencidos).
- **Tipos de picking configurables** para el calculo de transito.
- **Multi-empresa** con agregacion de datos por todas las empresas seleccionadas.

### 4. Inventario a la Fecha

Accesible desde **Inventario > Reportes > Inventario Avanzado > Inventario a la Fecha**.

Reconstruye el inventario historico a cualquier fecha seleccionada, discriminado por ubicacion, producto y lote.

| Columna | Descripcion |
|---------|-------------|
| **Almacen** | Almacen padre de la ubicacion |
| **Ubicacion** | Ubicacion interna especifica |
| **Producto** | Nombre del producto |
| **Categoria** | Categoria del producto (columna opcional) |
| **Lote/Serie** | Numero de lote o serie |
| **Cantidad** | Stock a la fecha seleccionada |
| **UdM** | Unidad de medida |
| **Fecha de Corte** | Fecha seleccionada para el calculo (columna opcional) |

#### Como funciona

1. Un wizard solicita la fecha de corte.
2. El sistema reconstruye el inventario partiendo del stock actual y deshaciendo los movimientos posteriores a la fecha seleccionada.
3. Los resultados se muestran en una vista de lista con filtros y agrupaciones:
   - **Filtro:** Con Existencia (cantidad > 0)
   - **Agrupar por:** Almacen, Ubicacion, Categoria, Producto, Lote

---

## Como usar

### Rotacion de Inventarios

1. Ve a **Inventario > Reportes > Inventario Avanzado > Rotacion de Inventarios**.
2. Selecciona el **rango de fechas**.
3. (Opcional) Marca **Incluir Entrante Futuro** con una fecha tope.
4. (Opcional) Filtra por **ubicaciones** o carga un preset guardado.
5. Haz clic en **Generar Reporte**.

### Planeacion de Compras

1. Ve a **Inventario > Reportes > Inventario Avanzado > Planeacion de Compras**.
2. Selecciona un **producto**.
3. Edita las celdas de **Pronostico de Ventas** y **Pronostico de Compras** segun tus proyecciones.
4. Observa como cambian los dias de inventario y los flags de rotacion.
5. Usa las flechas para navegar entre meses.

### Inventario a la Fecha

1. Ve a **Inventario > Reportes > Inventario Avanzado > Inventario a la Fecha**.
2. Selecciona la **fecha de corte** deseada.
3. Haz clic en **Calcular**.
4. Usa los filtros y agrupaciones para analizar los resultados.

---

## Configuracion

1. Navega a **Ajustes > Feral Tech > Inventario Avanzado**.
2. Ingresa el **token de licencia** proporcionado por Feral Tech.
3. (Opcional) Activa **Mostrar Decimales** para ver 2 decimales en los reportes.
4. Configura los **rangos del flag** (Amarillo Min, Verde Min, Verde Max, Amarillo Max).
5. (Opcional) Selecciona las **ubicaciones a excluir** del calculo de planeacion.
6. (Opcional) Configura los **tipos de picking** para el calculo de transito.
7. (Opcional) Configura **flags por producto** para productos con rotacion especial.

### Presets de ubicacion

Puedes guardar combinaciones de ubicaciones frecuentes con un nombre personalizado y cargarlas rapidamente en futuros reportes de rotacion.

---

## Requisitos

- Odoo 16 (Community o Enterprise).
- Modulos de Odoo: **Inventario**, **Compras**, **Contabilidad**.
- Modulo base: **Feral Tech Base** (`feral_tech_base`).
- Licencia activa con Feral Tech.

Para adquirir una licencia o solicitar soporte, contactanos en **contacto@feraltech.co**

---

## Soporte

- Web: [https://feraltech.co](https://feraltech.co)
- Email: contacto@feraltech.co
