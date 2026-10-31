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

Dados salvos em `data/dados_reais.csv` (70 observações: 35 por grupo).  
Veja [`docs/cenario.md`](docs/cenario.md) para detalhes da fonte e parâmetros da simulação.

---

## Estrutura do repositório

```
data/           dados reais coletados (CSV)
docs/           cenário, kanban snapshots e apresentação
src/            código de coleta, simulação e testes
dashboard.py    dashboard interativo (entrega final)
requirements.txt
```

---

## Links

- **Repositório:** https://github.com/Laboratorio-Medicao/Lab04  
- **GitHub Projects (Kanban):** https://github.com/orgs/Laboratorio-Medicao/projects/1
