# Football Predictor — Match Data Explorer

## 1. Propósito del Sistema
El Football Predictor es una herramienta de **exploración de datos y visualización** diseñada para identificar y filtrar partidos de fútbol de las principales ligas europeas. El sistema se enfoca en detectar escenarios específicos, como enfrentamientos entre "Goliath vs David" (equipos en el Top 4 contra equipos en la parte baja de la tabla), permitiendo una análisis rápido de estadísticas clave sin depender exclusivamente de modelos de predicción complejos.

## 2. Arquitectura y Flujo de Datos
1.  **Scraper**: Obtiene estadísticas de equipos (promedio de goles a favor/en contra) y cuotas de múltiples casas de apuestas.
2.  **AI Market Engine**: 
    *   Calcula Lambdas ($\lambda$) por partido.
    *   Genera matriz de probabilidad Poisson.
    *   Normaliza cuotas de mercado (mediana) para obtener la probabilidad implícita.
    *   Calcula el **Edge** (ventaja absoluta) y **Edge Ratio** (ventaja relativa).
3.  **API**: Expone los resultados procesados en formato JSON.
4.  **Frontend**: Interfaz visual para visualizar las recomendaciones.

## 3. Parámetros de Configuración (.env)
*   `API_FOOTBALL_KEY`: Tu clave de API de [api-football.com](https://www.api-football.com/).
*   `HOME_ADVANTAGE_FACTOR`: (Default: `1.0`). Factor multiplicador para la ventaja de localía. Recomendado: `1.10` a `1.15` si deseas sesgar hacia el local.
*   `API_PORT`: Puerto para la API (Default: `8880`).
*   `FRONTEND_PORT`: Puerto para la web (Default: `3330`).

## 4. Gestión del Bankroll Inicial
El sistema no gestiona el dinero directamente, pero recomienda una estrategia de **Unit Betting** o **Kelly Criterion** basada en el `edge_ratio`.
*   **Bankroll Sugerido**: 100 Unidades.
*   **Stake por apuesta**:
    *   `low_edge`: 0.5 Unidades.
    *   `medium_edge`: 1.0 Unidades.
    *   `high_edge`: 2.0 Unidades.

## 5. Guía de Inicio Rápido (Paso a Paso)

### Paso 1: Configurar Entorno
Crea un archivo `.env` en la raíz del proyecto con tu clave:
```env
API_FOOTBALL_KEY=tu_clave_aqui
HOME_ADVANTAGE_FACTOR=1.0
```

### Paso 2: Levantar el Sistema
Ejecuta el siguiente comando en la terminal:
```bash
docker-compose up --build
```
Este comando construirá las imágenes y ejecutará los servicios en orden: Scraper -> Engine -> API -> Frontend.

### Paso 3: Monitorear el Proceso
1.  El **Scraper** descargará los partidos de hoy (esto puede tardar 1-2 minutos debido al rate limiting).
2.  El **Engine** procesará los datos y generará `predictions_latest.json`.
3.  La **API** estará disponible en `http://localhost:8880/predictions`.

### Paso 4: Visualizar Recomendaciones
Accede a `http://localhost:3330` para ver el dashboard de recomendaciones. Prioriza aquellas con `is_recommendation: true` y `high_edge`.

## 6. Criterios de Selección Estrictos
Para que un partido sea recomendado, debe cumplir:
1.  **Datos completos**: Estadísticas de goles reales disponibles.
2.  **Calidad de Mercado**: Mínimo de **3 bookmakers** diferentes para calcular la mediana.
3.  **Ventaja Matemática**: 
    *   `Edge > 0.05` ($5\%$)
    *   `Edge Ratio > 0.10` ($10\%$)

---
**El sistema está configurado y listo para pruebas iniciales.**