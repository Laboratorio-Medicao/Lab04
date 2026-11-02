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

```bash
pip install -r requirements.txt
```

Autenticação GitHub necessária para coletar dados reais:

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
data/           dados reais coletados (CSV) e parâmetros da simulação (JSON)
docs/           cenário, kanban snapshots e apresentação
src/            código de coleta, simulação e testes
tests/          testes automatizados (pytest)
.streamlit/     configuração do dashboard
dashboard.py    dashboard interativo (entrega final)
requirements.txt
```

---

## Links

- **Repositório:** https://github.com/Laboratorio-Medicao/Lab04  
- **GitHub Projects (Kanban):** https://github.com/orgs/Laboratorio-Medicao/projects/1
