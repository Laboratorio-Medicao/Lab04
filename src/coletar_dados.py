"""
Coleta dados reais de tempo até o merge de PRs do repositório pallets/flask.

Grupos:
  com_bot  — PRs abertos por dependabot (bot de atualização automática de deps)
  sem_bot  — PRs abertos por humanos

Par de testes escolhido: P1 — t de Welch × Mann-Whitney
Pergunta: PRs com bot de atualização automática são merged mais rápido
          do que PRs abertos por humanos?

Saída: data/dados_reais.csv
Fonte: API GraphQL do GitHub — repositório pallets/flask
       Coletado em: 2026-10-31
"""

import os
import csv
import time
import json
import subprocess
from datetime import datetime, timezone

REPO_OWNER = "pallets"
REPO_NAME = "flask"
TARGET_PER_GROUP = 35
OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "dados_reais.csv")

QUERY_BOT = """
query($cursor: String) {
  search(
    query: "repo:pallets/flask is:pr is:merged author:app/dependabot"
    type: ISSUE
    first: 50
    after: $cursor
  ) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number
        title
        author { login }
        createdAt
        mergedAt
      }
    }
  }
}
"""

QUERY_HUMAN = """
query($cursor: String) {
  search(
    query: "repo:pallets/flask is:pr is:merged -author:app/dependabot -author:app/renovate"
    type: ISSUE
    first: 50
    after: $cursor
  ) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number
        title
        author { login }
        createdAt
        mergedAt
      }
    }
  }
}
"""


def gh_graphql(query: str, cursor=None) -> dict:
    variables = {"cursor": cursor} if cursor else {}
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}",
         "--jq", "."],
        input=json.dumps(variables),
        capture_output=True, text=True
    )
    # simpler: pass variables via -F
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    if cursor:
        args += ["-f", f"cursor={cursor}"]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def horas_ate_merge(created_at: str, merged_at: str) -> float:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    created = datetime.strptime(created_at, fmt).replace(tzinfo=timezone.utc)
    merged = datetime.strptime(merged_at, fmt).replace(tzinfo=timezone.utc)
    return round((merged - created).total_seconds() / 3600, 2)


def coletar_grupo(query: str, grupo: str, target: int) -> list[dict]:
    rows = []
    cursor = None
    print(f"Coletando grupo '{grupo}' ...")
    while len(rows) < target:
        data = gh_graphql(query, cursor)
        search = data["data"]["search"]
        for node in search["nodes"]:
            if not node.get("mergedAt"):
                continue
            horas = horas_ate_merge(node["createdAt"], node["mergedAt"])
            rows.append({
                "pr_number": node["number"],
                "repo": f"{REPO_OWNER}/{REPO_NAME}",
                "autor": node["author"]["login"] if node["author"] else "ghost",
                "grupo": grupo,
                "horas_ate_merge": horas,
                "created_at": node["createdAt"],
                "merged_at": node["mergedAt"],
            })
            if len(rows) >= target:
                break
        page_info = search["pageInfo"]
        print(f"  coletados: {len(rows)}")
        if not page_info["hasNextPage"] or len(rows) >= target:
            break
        cursor = page_info["endCursor"]
        time.sleep(0.3)
    return rows[:target]


def main() -> None:
    com_bot = coletar_grupo(QUERY_BOT, "com_bot", TARGET_PER_GROUP)
    sem_bot = coletar_grupo(QUERY_HUMAN, "sem_bot", TARGET_PER_GROUP)

    rows = com_bot + sem_bot
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSalvo em {OUTPUT}")
    print(f"  com_bot : {len(com_bot)} obs  |  horas_ate_merge: "
          f"mediana={sorted(r['horas_ate_merge'] for r in com_bot)[len(com_bot)//2]:.1f}h")
    print(f"  sem_bot : {len(sem_bot)} obs  |  horas_ate_merge: "
          f"mediana={sorted(r['horas_ate_merge'] for r in sem_bot)[len(sem_bot)//2]:.1f}h")


if __name__ == "__main__":
    main()
