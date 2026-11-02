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

O dashboard abre em `http://localhost:8501` (Streamlit) ou gera `dashboard.html` (Plotly),
conforme a implementação final.

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
dashboard.py    dashboard interativo (entrega final)
requirements.txt
```

---

## Links

- **Repositório:** https://github.com/Laboratorio-Medicao/Lab04  
- **GitHub Projects (Kanban):** https://github.com/orgs/Laboratorio-Medicao/projects/1
