# Cenário — LAB04

## Par de testes

**P1 — t de Welch × Mann-Whitney**

---

## Pergunta

> O tempo até o merge de PRs abertos pelo Dependabot difere do tempo até o merge de PRs abertos por humanos no repositório `pallets/flask`?

---

## Hipóteses

Seja `T` o tempo até o merge, em horas, e `F` sua distribuição em cada grupo.

**H₀ comum:** `F_bot = F_humano`. Em palavras: os dois grupos têm a mesma distribuição de tempo até o merge. É essa a H₀ usada na simulação.

Cada teste avalia uma consequência diferente dessa H₀:

| Teste | H₀ | H₁ | Em palavras |
|---|---|---|---|
| t de Welch | `μ_bot = μ_humano` | `μ_bot ≠ μ_humano` | O tempo médio em horas é igual / é diferente entre os grupos |
| Mann-Whitney | `P(T_bot > T_humano) = P(T_bot < T_humano)` | `P(T_bot > T_humano) ≠ P(T_bot < T_humano)` | Um PR de bot sorteado não tende a demorar mais nem menos que um humano / tende a demorar mais ou menos |

**Tipo:** bicaudal — não há razão a priori para assumir a direção do efeito, pois bots podem ser mergeados rapidamente (CI verde → merge automático) ou ficar esperando por janelas de manutenção. A direção não foi escolhida depois de olhar os dados.

Os dois testes são aplicados ao tempo em horas, sem transformação em log.

---

## Fonte dos dados reais

- **Repositório:** [`pallets/flask`](https://github.com/pallets/flask)
- **API:** GitHub GraphQL API — campos `mergedAt`, `createdAt` e `author` de `PullRequest`
- **Data de coleta:** 2026-11-02
- **Janela:** PRs criados de 2021-04-28 a 2024-08-01 nos dois grupos. É todo o período de atividade do Dependabot no repositório, o que evita comparar grupos de épocas diferentes.
- **Critério de seleção:** todos os PRs merged da janela, sem subamostragem.
  - **com_bot:** PRs com `author:app/dependabot`.
  - **sem_bot:** PRs com autor do tipo `User` na API. Ficam de fora 25 PRs de `pre-commit-ci`, 1 de `dependabot-preview` e 1 sem autor.
- **Scripts:** `src/coletar_dados.py` e `src/estimar_parametros.py`
- **Arquivos:** `data/dados_reais.csv` e `data/parametros_simulacao.json`

### Estatísticas descritivas dos dados reais

| Grupo | n | Mínimo (h) | Mediana (h) | Média (h) | Máximo (h) | Desvio (h) | Assimetria |
|-------|---|-----------|------------|---------|-----------|-----------|-----------|
| com_bot | n=60 | 0,0433 | 0,77 | 19,52 | 295,48 | 47,10 | 3,88 |
| sem_bot | n=320 | 0,0019 | 1,07 | 153,06 | 5234,09 | 530,11 | 6,32 |

### Observações sobre a distribuição

Os dados são **fortemente assimétricos à direita** (right-skewed) em ambos os grupos, e a observação mais importante é que eles se dividem em **dois regimes**:
- **Regime rápido:** 58% dos PRs do Dependabot e 49% dos PRs humanos são merged em menos de 1 hora.
- **Regime lento:** os demais se espalham por dias ou meses, com valores extremos de centenas ou milhares de horas.
- A diferença entre mediana e média é enorme, especialmente no grupo `sem_bot` (1,07 h de mediana e 153,06 h de média).
- Isso é típico de dados de tempo (duração) em engenharia de software e viola a suposição de normalidade do t de Welch.

---

## Parâmetros da simulação

O arquivo `data/parametros_simulacao.json` é a **fonte única** dos parâmetros para os cards #5 e #7. Ele é gerado por `python src/estimar_parametros.py`, com semente fixa `numpy.random.default_rng(42)`.

### Modelo

Cada grupo é modelado como uma **mistura de duas lognormais**, com os PRs separados em 1 hora. Um PR cai no regime rápido com probabilidade `p_rápido` e, nesse caso, `ln(T) ~ N(μ_rápido, σ_rápido²)`. Caso contrário, `ln(T) ~ N(μ_lento, σ_lento²)`. Os valores são MLE condicional ao regime: média e desvio de `ln(T)` dentro de cada regime.

| Parâmetro | com_bot | sem_bot | h0 (dados combinados) |
|-----------|---------|---------|-----------------------|
| p_rápido | 0,58 | 0,49 | 0,51 |
| μ_rápido | −1,46 | −2,46 | −2,28 |
| σ_rápido | 1,00 | 1,06 | 1,12 |
| μ_lento | 2,71 | 3,79 | 3,64 |
| σ_lento | 1,70 | 2,20 | 2,17 |

### Por que a mistura

A tabela compara os dados reais com amostras simuladas de mesmo tamanho. Cada valor simulado é a mediana entre 5.000 réplicas.

| Grupo | Fonte | Q1 (h) | Mediana (h) | Q3 (h) | P90 (h) | Média (h) | Máximo (h) |
|-------|-------|--------|-------------|--------|---------|-----------|------------|
| com_bot | Real | 0,15 | 0,77 | 4,45 | 51,12 | 19,52 | 295,48 |
| com_bot | Lognormal única | 0,27 | 1,32 | 6,64 | 27,21 | 16,93 | 354,80 |
| com_bot | Mistura | 0,20 | 0,62 | 9,28 | 44,37 | 21,46 | 390,92 |
| sem_bot | Real | 0,07 | 1,07 | 52,52 | 336,76 | 153,06 | 5234,09 |
| sem_bot | Lognormal única | 0,18 | 2,02 | 22,32 | 191,33 | 439,71 | 52700,24 |
| sem_bot | Mistura | 0,09 | 0,75 | 44,73 | 280,68 | 211,48 | 14744,16 |

Em `com_bot`, os dois modelos ficam próximos. Em `sem_bot`, a lognormal única exagera a média e o máximo e erra o quartil superior, enquanto a mistura se aproxima melhor dos dados reais.

### Configuração da simulação

Esta é a **situação base**, não uma "situação normal": os dados simulados já são muito assimétricos. Por isso, a violação de pressuposto do Q3 (#14) deve usar n ≤ 10 ou outliers extremos.

- **Tamanhos:** n=60 para `com_bot` e n=320 para `sem_bot`.
- **H₀ verdadeira:** os dois grupos são sorteados de forma independente de `mistura.h0`.
- **H₁ verdadeira:** `T_humano ~ mistura.h0` e `T_bot = e^δ · T`, com `T ~ mistura.h0` sorteado de forma independente. Esse deslocamento torna falsas as duas H₀ ao mesmo tempo.
- **Sinais de δ:** avaliar +δ e −δ, coerente com o teste bicaudal.
- **Tamanho de efeito padronizado:** `d = δ / σ_log_h0`, com `σ_log_h0` = 3,42 (desvio de `ln(T)` nos dados combinados).
- **Referência de escala:** nos dados reais, δ observado = −0,42 e d observado = −0,12. Esses valores servem só como referência de escala, porque o deslocamento é uma simplificação: a diferença real entre os grupos não é um deslocamento puro.
- **Papel de cada bloco do JSON:** `mistura.com_bot` e `mistura.sem_bot` servem ao G1 (#7), que compara cada grupo real com a mistura do próprio grupo. Q1, Q2 e Q3 usam `mistura.h0` como configuração principal.

### Orientação para Q2, Q3 e G4 (#13, #14 e #16)

Mostrar o tamanho empírico em δ = 0 ao lado do poder, e comparar os testes pelo poder ajustado, porque um teste fora de 5% não tem poder bruto comparável.

O valor crítico é um par por teste, com os quantis 2,5% e 97,5% da estatística sob H₀ (δ = 0). Rejeita-se fora desse intervalo. Não usar corte em |estatística|. O par é recalculado para cada situação e cada n.

A estatística é, sempre na ordem bot × humano, o `t` com sinal no Welch e o `U` do grupo bot no Mann-Whitney. Não usar `min(U)`, porque o par de quantis perderia o sentido.

Informar também o tamanho alcançado ao lado do poder ajustado, porque a estatística do Mann-Whitney é discreta e, com n pequeno, fica abaixo de 5%.

---

## Expectativa inicial (antes de simular)

Esperamos que o **Mann-Whitney se saia melhor** do que o t de Welch neste cenário, pelos seguintes motivos:

1. **Violação de normalidade:** Os dados são fortemente assimétricos (lognormal). O t de Welch assume normalidade (ou n grande pelo TCL), e com n=35 por grupo a aproximação pode ser insuficiente para caudas tão pesadas.
2. **Sensibilidade a outliers:** O t de Welch usa a média, que é inflada pelos valores extremos. O Mann-Whitney usa postos e é robusto a outliers.
3. **Diferença estrutural:** A diferença entre os grupos pode ser melhor capturada pela diferença de distribuições do que pela diferença de médias (que é dominada por poucos PRs muito antigos no grupo `sem_bot`).

> Essa expectativa será verificada nas simulações Q1, Q2 e Q3 da Sprint S02.

Nota de 2026-11-02: texto escrito antes da recoleta. A amostra passou a n=60 e n=320, e o modelo passou a ser uma mistura de duas lognormais.

---

## Limitações

- **Concentração em um autor:** 135 dos 320 PRs humanos são de `davidism`, e 93% dos PRs dessa pessoa ficam abaixo de 1 hora, contra 17% dos outros humanos. O regime rápido está ligado ao autor.
- **Observações não totalmente independentes:** PRs do Dependabot chegam em lotes, e 14 dos 60 foram mergeados no mesmo minuto de outro PR do grupo.
- **Seleção por PRs merged:** a amostra ignora os PRs fechados sem merge, que são 47 de 107 no Dependabot e 243 de 590 nos demais.
- **Períodos ainda misturados:** mesmo com a janela comum, 65% dos PRs `com_bot` são de 2023–2024, contra 31% dos `sem_bot`.
- **Limiar de 1 hora:** é uma escolha do grupo.
- **Cauda simulada mais pesada que a real:** o máximo simulado de `sem_bot` passa do real, o que tende a prejudicar o t de Welch, justamente o teste que a expectativa inicial aponta como pior. Por isso, #13 e #14 devem incluir uma sensibilidade com reamostragem ou truncamento.
