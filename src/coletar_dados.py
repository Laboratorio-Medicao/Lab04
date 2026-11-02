"""
Coleta dados reais de tempo até o merge de PRs do repositório pallets/flask.

Grupos:
  com_bot  — PRs abertos pelo Dependabot (bot de atualização automática de deps)
  sem_bot  — PRs abertos por humanos (autor do tipo User na API do GitHub)

Janela: 2021-04-28 a 2024-08-01, todo o período de atividade do Dependabot no
        repositório, aplicada aos dois grupos.

Par de testes escolhido: P1 — t de Welch × Mann-Whitney
Pergunta: O tempo até o merge de PRs abertos pelo Dependabot difere do tempo
          até o merge de PRs abertos por humanos em pallets/flask?

Saída: data/dados_reais.csv
Fonte: API GraphQL do GitHub — repositório pallets/flask
       Coletado em: 2026-11-02
"""

import os
import csv
import time
import json
import statistics
import subprocess
from datetime import datetime, timezone

REPO_OWNER = "pallets"
REPO_NAME = "flask"
JANELA = "2021-04-28..2024-08-01"
LIMITE_BUSCA = 1000
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "dados_reais.csv")

QUERY = """
query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 100, after: $cursor) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number
        title
        author { __typename login }
        createdAt
        mergedAt
      }
    }
  }
}
"""


def termos_busca(grupo: str) -> str:
    autor = "author:app/dependabot" if grupo == "com_bot" else "-author:app/dependabot"
    return f"repo:{REPO_OWNER}/{REPO_NAME} is:pr is:merged created:{JANELA} {autor}"


def eh_humano(node: dict) -> bool:
    return node["author"] is not None and node["author"]["__typename"] == "User"


def gh_graphql(termos: str, cursor: str | None = None) -> dict:
    args = ["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"q={termos}"]
    if cursor:
        args += ["-f", f"cursor={cursor}"]
    r = subprocess.run(args, capture_output=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def horas_ate_merge(created_at: str, merged_at: str) -> float:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    created = datetime.strptime(created_at, fmt).replace(tzinfo=timezone.utc)
    merged = datetime.strptime(merged_at, fmt).replace(tzinfo=timezone.utc)
    return round((merged - created).total_seconds() / 3600, 4)


def coletar_grupo(grupo: str) -> list[dict]:
    termos = termos_busca(grupo)
    rows = []
    recebidos = 0
    cursor = None
    print(f"Coletando grupo '{grupo}' ...")
    while True:
        search = gh_graphql(termos, cursor)["data"]["search"]
        if search["issueCount"] > LIMITE_BUSCA:
            raise RuntimeError(f"Busca '{grupo}' passa do limite de {LIMITE_BUSCA} resultados")
        recebidos += len(search["nodes"])
        for node in search["nodes"]:
            if grupo == "sem_bot" and not eh_humano(node):
                continue
            rows.append({
                "pr_number": node["number"],
                "repo": f"{REPO_OWNER}/{REPO_NAME}",
                "autor": node["author"]["login"],
                "grupo": grupo,
                "horas_ate_merge": horas_ate_merge(node["createdAt"], node["mergedAt"]),
                "created_at": node["createdAt"],
                "merged_at": node["mergedAt"],
            })
        page_info = search["pageInfo"]
        print(f"  coletados: {len(rows)}")
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]
        time.sleep(0.3)
    if recebidos != search["issueCount"]:
        raise RuntimeError(f"Coleta incompleta em '{grupo}': {recebidos} de {search['issueCount']}")
    return sorted(rows, key=lambda r: r["pr_number"])


def main() -> None:
    com_bot = coletar_grupo("com_bot")
    sem_bot = coletar_grupo("sem_bot")

    rows = com_bot + sem_bot
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSalvo em {OUTPUT}")
    print(f"  com_bot : {len(com_bot)} obs  |  horas_ate_merge: "
          f"mediana={statistics.median(r['horas_ate_merge'] for r in com_bot):.2f}h")
    print(f"  sem_bot : {len(sem_bot)} obs  |  horas_ate_merge: "
          f"mediana={statistics.median(r['horas_ate_merge'] for r in sem_bot):.2f}h")


if __name__ == "__main__":
    main()
