# LAB04 — Testes de Hipótese por Dentro

**Disciplina:** Laboratório de Experimentação de Software · PUC Minas  
**Turno:** Noite · 6º Período  
**Professor:** Danilo Maia  
**Grupo:** Guilherme Vieira · Arthur Luiz · Marcos

---

## Par de testes escolhido

**P1 — t de Welch × Mann-Whitney**

**Cenário:** Tempo até o merge de PRs no repositório `pallets/flask` —  
PRs abertos por dependabot (bot) versus PRs abertos por humanos.

---

## Como executar

### Pré-requisitos

- Python 3.11 ou superior
- `pip`

### Instalação

Recomendado, em ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Os CSVs e o JSON em `data/` já estão versionados: o dashboard roda sem token do GitHub.

A autenticação no GitHub só é necessária para recoletar os dados reais:

```bash
gh auth login   # ou exporte GITHUB_TOKEN
```

### Comando único — dashboard completo

```bash
python -m dashboard
```

Execute na raiz do repositório. O dashboard fica disponível em `http://localhost:8501`. A URL
também aparece no terminal, e o navegador não abre sozinho. Para encerrar, use `Ctrl+C`.

---

## Coleta de dados reais

```bash
python src/coletar_dados.py
```

Dados salvos em `data/dados_reais.csv` (380 observações: 60 `com_bot` e 320 `sem_bot`).  
Veja [`docs/cenario.md`](docs/cenario.md) para detalhes da fonte e parâmetros da simulação.

---

## Parâmetros da simulação

```bash
python src/estimar_parametros.py
```

Parâmetros salvos em `data/parametros_simulacao.json`, derivados de `data/dados_reais.csv`.

---

## Dados simulados

```bash
python src/simulacao.py
```

Gera `data/dados_simulados.csv` com um conjunto sob H₀ e outro sob H₁, com semente fixa
`numpy.random.default_rng(42)`: duas execuções produzem exatamente o mesmo arquivo.

Nos scripts de análise e no dashboard, importe `gerar` de `src/simulacao.py`:

```python
from simulacao import carregar_parametros, criar_rng, gerar

parametros = carregar_parametros()
bot, humano = gerar(parametros, h1=True, d=0.3, n_bot=60, n_humano=320, rng=criar_rng())
```

| Parâmetro | Efeito |
|---|---|
| `h1`, `d` | `h1=False` sorteia sob H₀. Com `h1=True`, `T_bot = e^δ · T` e `δ = d · σ_log_h0` (d negativo inverte o sinal) |
| `n_bot`, `n_humano` | tamanho de cada grupo (padrão: 60 e 320, de `parametros_simulacao.json`) |
| `distribuicao` | `"mistura"` (padrão, duas lognormais) ou `"lognormal"` (única) |
| `fator_sigma` | multiplica o desvio de ln(T): maior deixa a cauda mais pesada |
| `rng` | gerador; por omissão, `default_rng(42)` |

O G1 é a exceção: ele compara cada grupo real com a mistura do próprio grupo, em `graficos.amostras_g1`.

---

## Testes

```bash
python -m pytest
```

---

## Estrutura do repositório

```
data/                   dados reais (CSV), parâmetros da simulação (JSON) e saídas das simulações Q1–Q3
data/kanban-snapshots/  snapshots do GitHub Projects (Kanban)
docs/                   cenário (cenario.md)
kanban/                 código que exporta os snapshots do Kanban (`python -m kanban.snapshot`)
src/                    código de coleta, simulação, testes estatísticos e gráficos
tests/                  testes automatizados (pytest)
.github/workflows/      CI (pytest em push no main e em PRs)
.streamlit/             configuração do dashboard
dashboard.py            dashboard interativo (entrega final)
requirements.txt
```

---

## Links

- **Repositório:** https://github.com/Laboratorio-Medicao/Lab04  
- **GitHub Projects (Kanban):** https://github.com/orgs/Laboratorio-Medicao/projects/1

---

## Q1 — Erro tipo I

```bash
python src/simulacao_q1.py
```

Aplica o t de Welch e o Mann-Whitney a 10.000 conjuntos sorteados sob H₀ verdadeira (semente 42) e
registra a proporção de p < 5%. Saídas para o G3: `data/simulacao_q1_pvalores.csv` e
`data/simulacao_q1_resumo.csv`.

## Q2 — Poder (efeitos crescentes)

```bash
python src/simulacao_q2.py
```

Curva de poder do t de Welch e do Mann-Whitney para d ∈ {0; 0,1; 0,2; 0,3; 0,5; 0,8; 1,0} (7 tamanhos,
começando em zero), com 10.000 repetições por d e semente 42. Em d = 0 a proporção é o erro tipo I (Q1).
Inclui uma sensibilidade com os tempos truncados no máximo dos dados reais. Saídas para o G4:
`data/simulacao_q2_poder.csv` e `data/simulacao_q2_sensibilidade.csv`.

## Q3 — Violação de pressuposto (erro tipo I e poder)

```bash
python src/simulacao_q3.py
```

Repete Q1 e Q2 em duas situações adversas ao t de Welch (amostras pequenas, n = 10 por grupo; e
outliers extremos, σ de ln T × 1,5) e compara com a situação normal. Semente 42, 10.000 repetições
por tamanho de efeito d ∈ {0; 0,1; 0,2; 0,3; 0,5; 0,8; 1,0}. Saídas para G3 e G4:
`data/simulacao_q3_poder.csv` e `data/simulacao_q3_comparacao.csv`.
