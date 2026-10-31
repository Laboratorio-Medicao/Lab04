# Cenário — LAB04

## Par de testes

**P1 — t de Welch × Mann-Whitney**

---

## Pergunta

> PRs abertos por bots de atualização automática de dependências são merged mais rapidamente do que PRs abertos por humanos no repositório `pallets/flask`?

---

## Hipóteses

| | |
|---|---|
| **H₀** | A distribuição do tempo até o merge é igual nos dois grupos (bot e humano). |
| **H₁** | O tempo até o merge é diferente entre os dois grupos (bicaudal). |

**Tipo:** bicaudal — não há razão a priori para assumir a direção do efeito, pois bots podem ser mergeados rapidamente (CI verde → merge automático) ou ficar esperando por janelas de manutenção.

---

## Fonte dos dados reais

- **Repositório:** [`pallets/flask`](https://github.com/pallets/flask)
- **API:** GitHub GraphQL API — campo `mergedAt` e `createdAt` de `PullRequest`
- **Data de coleta:** 2026-10-31
- **Critério de seleção:**
  - **com_bot:** PRs merged com `author:app/dependabot`
  - **sem_bot:** PRs merged excluindo `author:app/dependabot` e `author:app/renovate`
- **Script:** `src/coletar_dados.py`
- **Arquivo:** `data/dados_reais.csv`

### Estatísticas descritivas dos dados reais

| Grupo | n | Mínimo (h) | Mediana (h) | Média (h) | Máximo (h) |
|-------|---|-----------|------------|---------|-----------|
| com_bot | 35 | 0,04 | 0,4 | 31,2 | 295,5 |
| sem_bot | 35 | 0,01 | 0,3 | 487,5 | 3.369,9 |

### Observações sobre a distribuição

Os dados são **fortemente assimétricos à direita** (right-skewed) em ambos os grupos:
- A maioria dos PRs é merged em menos de 1 hora, mas existem outliers com centenas ou milhares de horas.
- A diferença entre mediana e média é enorme — especialmente no grupo `sem_bot` (0,3h vs 487,5h).
- Isso é típico de dados de tempo (duração) em engenharia de software e viola a suposição de normalidade do t de Welch.

---

## Parâmetros da simulação

Com base nos dados reais, vamos modelar cada grupo com uma **distribuição lognormal**,
que captura bem a assimetria observada.

| Parâmetro | com_bot | sem_bot |
|-----------|---------|---------|
| Distribuição | Lognormal | Lognormal |
| μ (log-espaço) | ln(mediana) ≈ −0,92 | ln(mediana) ≈ −1,20 |
| σ (log-espaço) | estimado dos dados ≈ 2,5 | estimado dos dados ≈ 3,5 |

> Os valores exatos de μ e σ serão ajustados via MLE nas funções de simulação (`src/simulacao.py`).

---

## Expectativa inicial (antes de simular)

Esperamos que o **Mann-Whitney se saia melhor** do que o t de Welch neste cenário, pelos seguintes motivos:

1. **Violação de normalidade:** Os dados são fortemente assimétricos (lognormal). O t de Welch assume normalidade (ou n grande pelo TCL), e com n=35 por grupo a aproximação pode ser insuficiente para caudas tão pesadas.
2. **Sensibilidade a outliers:** O t de Welch usa a média, que é inflada pelos valores extremos. O Mann-Whitney usa postos e é robusto a outliers.
3. **Diferença estrutural:** A diferença entre os grupos pode ser melhor capturada pela diferença de distribuições do que pela diferença de médias (que é dominada por poucos PRs muito antigos no grupo `sem_bot`).

> Essa expectativa será verificada nas simulações Q1, Q2 e Q3 da Sprint S02.
