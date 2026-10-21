# API interna (`/api/v1`)

Documentação interativa gerada pelo FastAPI: `http://localhost:8000/docs` (OpenAPI em `/openapi.json`).

Convenções: datas ISO 8601 (`YYYY-MM-DD`); valores numéricos com a unidade explícita na resposta;
erros sempre no formato:

```json
{ "error": { "code": "invalid_range", "message": "start_date deve ser anterior ou igual a end_date.", "details": null } }
```

| Método e rota | Descrição |
|---|---|
| `GET /api/v1/health` | Estado da aplicação e do banco (`503 database_unavailable` se o banco cair) |
| `GET /api/v1/sources` | Fontes oficiais cadastradas |
| `GET /api/v1/geographies` | Unidades geográficas cadastradas |
| `GET /api/v1/indicators` | Catálogo com metadados, período armazenado e data da última coleta |
| `GET /api/v1/indicators/{code}` | Metadados de um indicador (`404 indicator_not_found`) |
| `GET /api/v1/indicators/{code}/observations` | Série histórica filtrada |

## `GET /api/v1/indicators/{code}/observations`

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `start_date` | — (início da série) | Data inicial inclusiva |
| `end_date` | — (última observação) | Data final inclusiva |
| `geography` | `BR` | Sigla ou código IBGE. Série nacional pedida para UF → `422 geography_not_available` |
| `frequency` | `original` | `original`, `daily` ou `monthly` (último valor do mês). Conversão para frequência mais alta → `422 frequency_not_supported` |

Resposta (resumida):

```json
{
  "indicator": { "code": "SELIC_TARGET", "unit": "% a.a.", "change_unit": "p.p.", "source_url": "…", "last_collected_at": "…" },
  "geography": { "ibge_code": "1", "acronym": "BR", "name": "Brasil", "geographic_level": "country" },
  "unit": "% a.a.",
  "original_frequency": "daily",
  "frequency": "monthly",
  "aggregation": { "method": "last_value_of_period", "description": "Valor mensal: último valor…" },
  "start_date": "2026-08-01",
  "end_date": "2026-10-21",
  "count": 3,
  "stats": { "first": {…}, "last": {…}, "change": -0.25, "change_unit": "p.p.", "min": {…}, "max": {…} },
  "observations": [
    { "date": "2026-10-21", "value": 13.75, "period_start": "2026-10-01", "period_end": "2026-10-31", "partial": true }
  ]
}
```

- `stats.change` é a diferença absoluta (último − primeiro) na unidade `change_unit`.
- Intervalo sem dados → `count: 0`, `observations: []`, `stats: null` (nunca zeros).
- Sem paginação: uma série diária completa tem ~10 mil pontos (~600 KB), adequado para o gráfico.
  Paginação será adicionada se surgirem séries maiores.
- `Cache-Control: public, max-age=300`.

### Planejados (fases futuras)

`/api/v1/dashboard/national` (quando houver os 3 indicadores), `/states/{uf}/…`, `/compare`, `/events`, `/relationships`.
