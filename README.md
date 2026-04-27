# Football Predictor — Match Data Explorer

## 1. Propósito del Sistema

El Football Predictor es una herramienta de **exploración de datos y visualización** diseñada para identificar y filtrar partidos de fútbol de las principales ligas europeas. El sistema detecta escenarios "Goliath vs David" (equipos Top 4 contra equipos en la parte baja de la tabla), mostrando estadísticas de goles reales calculadas desde historial de partidos.

## 2. Arquitectura y Flujo de Datos

```
Scraper → matches.json → Engine → matches.json → API (FastAPI) → Frontend (nginx)
```

1. **Scraper**: Obtiene partidos programados, standings y historial desde [football-data.org](https://api.football-data.org/v4/). Calcula promedios de goles por equipo (home/away).
2. **Engine**: Añade flags `is_goliath_vs_david` y `goliath_team` basándose en rankings.
3. **API**: Expone `matches.json` en `http://localhost:8880/matches` con filtros por liga, goliath, y localía.
4. **Frontend**: Dashboard visual servido por nginx en `http://localhost:3330`.

## 3. Fuente de Datos

| Atributo | Valor |
|----------|-------|
| API | [football-data.org v4](https://api.football-data.org/v4/) |
| Autenticación | Header `X-Auth-Token` |
| Variable de entorno | `API_FOOTBALL_TOKEN` |
| Rate limit (free tier) | 10 requests/minuto |

### Ligas disponibles

| Código | Liga |
|--------|------|
| `PL` | Premier League |
| `PD` | La Liga |
| `SA` | Serie A |
| `BL1` | Bundesliga |
| `FL1` | Ligue 1 |

### Endpoints utilizados

| Endpoint | Propósito |
|----------|-----------|
| `GET /v4/matches?status=SCHEDULED` | Partidos programados |
| `GET /v4/competitions/{code}/standings` | Tabla de posiciones |
| `GET /v4/competitions/{code}/matches?status=FINISHED` | Historial para estadísticas |

## 4. Configuración (.env)

```env
API_FOOTBALL_TOKEN=tu_token_de_football_data_org
HOME_ADVANTAGE_FACTOR=1.15
API_PORT=8880
FRONTEND_PORT=3330
```

## 5. Guía de Inicio Rápido

### Paso 1: Configurar `.env`
Crear archivo `.env` en la raíz con tu token de [football-data.org](https://www.football-data.org/client/register).

### Paso 2: Levantar el sistema
```bash
docker compose up --build
```

Los servicios se ejecutan en orden automático:
1. **Scraper** → descarga datos reales (~1 minuto)
2. **Engine** → procesa flags Goliath vs David
3. **API** → disponible en `http://localhost:8880/matches`
4. **Frontend** → disponible en `http://localhost:3330`

### Paso 3: Verificar
```bash
curl http://localhost:8880/matches | python3 -m json.tool
```

## 6. Estructura de Datos (matches.json)

```json
{
    "fixture_id": 537147,
    "date": "2026-04-27T16:30:00Z",
    "league_id": "SA",
    "league_name": "Serie A",
    "home_team": "Cagliari Calcio",
    "away_team": "Atalanta BC",
    "rank_home": 16,
    "rank_away": 7,
    "home_avg_goals_for": 1.06,
    "home_avg_goals_against": 1.12,
    "away_avg_goals_for": 1.25,
    "away_avg_goals_against": 0.94,
    "matchday": 34,
    "status": "TIMED",
    "is_goliath_vs_david": false,
    "goliath_team": null
}
```

## 7. Criterios Goliath vs David

Un partido es clasificado como "Goliath vs David" cuando:
- `rank_home ≤ 4` AND `rank_away ≥ 14`, ó
- `rank_away ≤ 4` AND `rank_home ≥ 14`

## 8. Reglas del Sistema

- ❌ Prohibido mock data
- ❌ Prohibido inventar valores
- ✅ Si falta información crítica → el partido se descarta
- ✅ Logging en cada request a la API
- ✅ Rate limiting: 7s entre requests

---
**Fuente exclusiva: football-data.org v4**

docker compose down && rm -f shared/data/*.json && docker compose up --build -d scraper && docker compose up --build -d api engine frontend