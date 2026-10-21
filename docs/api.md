# API interna (`/api/v1`)

Documentação interativa gerada pelo FastAPI: `http://localhost:8000/docs` (OpenAPI em `/openapi.json`).

Convenções: datas ISO 8601 (`YYYY-MM-DD`); valores numéricos com a unidade explícita na resposta;
parâmetros de consulta **não declarados pela rota são rejeitados** com `422 unknown_parameter`
(ex.: `?start=` em vez de `start_date`), com `details.unknown` e `details.allowed`, e parâmetros
escalares repetidos com `422 repeated_parameter`. Essa validação ocorre antes da rota: um indicador
inexistente com parâmetro desconhecido responde 422. Erros sempre no formato:

```json
{ "error": { "code": "invalid_range", "message": "start_date deve ser anterior ou igual a end_date.", "details": null } }
```

| Método e rota | Descrição |
|---|---|
| `GET /api/v1/health` | Estado da aplicação e do banco (`503 database_unavailable` se o banco cair) |
| `GET /api/v1/sources` | Fontes oficiais cadastradas |
| `GET /api/v1/geographies` | Unidades geográficas cadastradas (ver abaixo); filtro opcional `level` |
| `GET /api/v1/geographies/states/boundaries` | Geometrias oficiais das 27 UFs (GeoJSON, malha do IBGE); filtro opcional `mesh_year` |
| `GET /api/v1/indicators` | Catálogo com metadados, período armazenado e data da última coleta |
| `GET /api/v1/indicators/{code}` | Metadados de um indicador (`404 indicator_not_found`) |
| `GET /api/v1/indicators/{code}/observations` | Série histórica filtrada |
| `GET /api/v1/dashboard/national` | Resumo do dashboard nacional: último valor e variação em 12 meses de cada indicador |

Indicadores estaduais (`geographic_level = "state"`, códigos `STATE_*`, S4): no catálogo,
`first_stored_date`/`last_stored_date` consideram todas as UFs; a série de cada UF vem de
`/indicators/{code}/observations?geography=SP` (sem `geography`, a resposta é
`422 geography_not_available`, pois o padrão é `BR`). `frequency` (do indicador) pode ser `daily`,
`monthly`, `bimonthly` (bimestre do RREO), `quarterly`, `four_monthly` (quadrimestre do RGF) ou
`annual`; o parâmetro `frequency=monthly` sobre série bimestral ou quadrimestral responde
`422 frequency_not_supported`. Nos fluxos acumulados no ano (`STATE_PRIMARY_RESULT`,
`STATE_NOMINAL_RESULT`, `STATE_INVESTMENTS`), `stats` vem `null`: variação, mínimo e máximo
comparariam bimestres não comparáveis (ADR 0010). Nos indicadores derivados do SICONFI,
`last_collected_at` é a data da coleta dos anexos que originaram as observações (da UF pedida ou,
no catálogo, de todas), não a da derivação.

### Estado da coleta (`last_run`)

Cada indicador (em `/indicators`, `/indicators/{code}`, nas observações e no dashboard) traz:

- `last_collected_at`: fim da última coleta **bem-sucedida** (`null` se nunca houve uma);
- `last_run`: a **última tentativa**, qualquer que seja o resultado (`null` se nunca houve uma):

```json
{ "status": "failed", "started_at": "2026-10-21T09:00:00Z", "finished_at": "2026-10-21T09:00:31Z", "error_type": "SGSUnavailableError" }
```

`status` é `running`, `success` ou `failed`. Só o tipo do erro é público (`error_type`); a mensagem
completa fica em `ingestion_runs.error_message` e nos logs. Quando `last_run.status` é `failed`, os
dados servidos são os da última coleta bem-sucedida.

## `GET /api/v1/geographies`

Brasil, as 5 grandes regiões e as 27 UFs (26 estados e o DF), com os códigos oficiais da API de
localidades do IBGE (ex.: MG = `31`, SP = `35`, DF = `53`) e o pai na hierarquia país → região → UF.
Ordem: país, UFs e regiões, cada nível pelo código IBGE. `level` (`country`, `region`, `state`,
`municipality`) filtra por nível; valor desconhecido → `422 validation_error`.

```json
{ "ibge_code": "31", "acronym": "MG", "name": "Minas Gerais", "geographic_level": "state",
  "parent": { "ibge_code": "3", "acronym": "SE", "name": "Sudeste", "geographic_level": "region" } }
```

Códigos e siglas do IBGE só são únicos **dentro de um nível**: `1` é o Brasil e a Região Norte; `SE` é
Sergipe e a Região Sudeste. No parâmetro `geography` das observações, a busca ocorre primeiro no nível
do indicador; fora dele, a ordem é país, UF, região (`SE` → Sergipe, `1` → Brasil).

## `GET /api/v1/geographies/states/boundaries`

GeoJSON `FeatureCollection` (`Content-Type: application/geo+json`) com as 27 UFs da malha oficial do
IBGE coletada por `ingest-boundaries` (ver [pipeline](data-pipeline.md)). Cada feição tem `id` e
`properties.ibge_code` iguais ao código IBGE de `/geographies`, mais `acronym` e `name`; a geometria é
`Polygon` ou `MultiPolygon` em (longitude, latitude). O frontend usa só este endpoint, nunca o IBGE.

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `mesh_year` | edição mais recente armazenada | Edição da malha (≥ 2000) |

```json
{ "type": "FeatureCollection",
  "metadata": { "source": { "acronym": "IBGE", "name": "API de malhas geográficas do IBGE (v3)", … },
    "source_url": "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application%2Fvnd.geo%2Bjson&intrarregiao=UF&qualidade=minima&periodo=2022",
    "mesh_year": 2022, "quality": "minima", "coordinate_decimals": 4,
    "simplification": "Malha generalizada pelo próprio IBGE (qualidade=minima), …",
    "collected_at": "2026-10-21T07:53:04Z" },
  "features": [ { "type": "Feature", "id": "53",
    "properties": { "ibge_code": "53", "acronym": "DF", "name": "Distrito Federal" },
    "geometry": { "type": "Polygon", "coordinates": [[[-48.016, -16.0497], …]] } }, … ] }
```

- Malha não coletada (ou edição pedida ausente) → `404 boundaries_not_found`.
- Cache: `Cache-Control: public, max-age=86400`, `Vary: Accept-Encoding` e `ETag` fraco (`W/"…"`),
  calculado sobre a edição, os códigos, os nomes e as geometrias: recoletar uma malha idêntica não o
  muda; uma geometria alterada, sim. `If-None-Match` com o mesmo ETag (com ou sem `W/`) ou `*` → `304`
  sem corpo.
- `mesh_year` fora de 2000–2100 → `422 validation_error`.
- Respostas da API acima de 1 KB são comprimidas com gzip quando o cliente aceita (~100 KB → ~28 KB aqui).

## `GET /api/v1/indicators/{code}/observations`

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `start_date` | — (início da série) | Data inicial inclusiva |
| `end_date` | — (última observação) | Data final inclusiva. Entra toda observação cujo **período de referência termina** no intervalo (`start_date <= period_end <= end_date`; ADR 0005). Com `frequency=monthly` sobre série diária, o filtro age sobre os dados diários **antes** da agregação: o último mês pode vir com `partial: true` e `period_end` após `end_date` |
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

- `start_date`/`end_date` descrevem o intervalo coberto pelos períodos devolvidos, recortado ao pedido.
- `stats.change` é a diferença absoluta (último − primeiro) na unidade `change_unit`.
- Intervalo sem dados → `count: 0`, `observations: []`, `stats: null` (nunca zeros).
- Sem paginação: uma série diária completa tem ~10 mil pontos (~600 KB), adequado para o gráfico.
  Paginação será adicionada se surgirem séries maiores.
- `Cache-Control: public, max-age=300`.

## `GET /api/v1/dashboard/national`

Sem parâmetros. Devolve, numa só chamada, os indicadores do dashboard nacional na ordem de exibição
(`SELIC_TARGET`, `DBGG_GDP`, `IPCA_12M`), cada um com os metadados completos do catálogo (fonte,
série, unidade, metodologia, link oficial, data da última coleta), o último valor e a variação em
12 meses.

```json
{
  "geography": { "ibge_code": "1", "acronym": "BR", "name": "Brasil", "geographic_level": "country" },
  "indicators": [
    {
      "indicator": { "code": "SELIC_TARGET", "unit": "% a.a.", "change_unit": "p.p.", "last_collected_at": "…" },
      "status": "available",
      "aggregation": { "method": "last_value_of_period", "description": "Valor mensal: último valor…" },
      "latest": { "date": "2026-10-21", "value": 13.75, "period_start": "2026-10-01", "period_end": "2026-10-31", "partial": true },
      "change_12m": { "value": -1.25, "change_unit": "p.p.", "reference_date": "2025-10-31", "reference_value": 15.0 }
    }
  ]
}
```

- **Último valor**: a observação oficial mais recente (`date` = data de referência; `period_start`/
  `period_end` = período de referência; para série diária, o mês corrente, com `partial: true`
  enquanto o mês não termina).
- **Variação em 12 meses** (`change_12m.value`): diferença absoluta, na unidade `change_unit` (p.p.
  para taxas e razões), entre o último valor e o valor do **mesmo mês do ano anterior**. Séries diárias
  são lidas na visão mensal (último valor de cada mês, declarado em `aggregation`); séries mensais, como
  publicadas. É o mesmo cálculo que o cartão fazia sobre a visão mensal de `/observations`.
  Consequência para séries diárias: o último valor (ex.: 21/10/2026) é comparado com o **fechamento** do
  mesmo mês do ano anterior (31/10/2025), e não com a mesma data; a distância entre as datas pode ser
  um pouco menor que 12 meses. As datas comparadas vêm sempre na resposta (`latest.date` e
  `change_12m.reference_date`).
- Sem valor no mês de comparação → `change_12m: null` (nunca se usa um mês vizinho nem se interpola).
- Indicador sem dados armazenados → `status: "no_data"`, `latest: null`, `change_12m: null` (nunca zeros).
- Indicador ausente do catálogo (seed incompleto) → `500 catalog_not_seeded`.
- `Cache-Control: public, max-age=300`, como em `/observations`.

### Planejados (fases futuras)

`/states/{uf}/…`, `/compare`, `/events`, `/relationships`.
