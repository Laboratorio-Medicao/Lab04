"""
Gera snapshot do Kanban GitHub Projects v2 para o Lab04.

Uso:
    python -m kanban.snapshot
    python -m kanban.snapshot --label lab04
    python -m kanban.snapshot --suffix s02
    python -m kanban.snapshot --org Laboratorio-Medicao --project 1 --label lab04

O token é lido de GITHUB_TOKEN ou obtido via `gh auth token`.
"""

import argparse
import logging
import os
import subprocess
from pathlib import Path

from kanban.client import GitHubGraphQLClient
from kanban.exporter import CsvExporter
from kanban.fetcher import KanbanFetcher

logger = logging.getLogger(__name__)

DEFAULT_ORG = "Laboratorio-Medicao"
DEFAULT_PROJECT_NUMBER = 1
DEFAULT_LABEL_FILTER = "lab04"
SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent / "data" / "kanban-snapshots"


def _get_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("Não foi possível obter o token GitHub. Configure GITHUB_TOKEN ou faça `gh auth login`.")
    return result.stdout.strip()


def _parse_args():
    parser = argparse.ArgumentParser(description="Gera snapshot do Kanban GitHub Projects v2")
    parser.add_argument("--org", default=DEFAULT_ORG, help="organização GitHub")
    parser.add_argument("--project", type=int, default=DEFAULT_PROJECT_NUMBER, help="número do projeto")
    parser.add_argument("--label", default=DEFAULT_LABEL_FILTER, help="filtrar por label (padrão: lab04)")
    parser.add_argument("--suffix", help="sufixo do arquivo, para separar snapshots do mesmo dia (ex.: s02)")
    return parser.parse_args()


def run(token, org=DEFAULT_ORG, project_number=DEFAULT_PROJECT_NUMBER,
        label_filter=DEFAULT_LABEL_FILTER, output_dir=SNAPSHOTS_DIR, suffix=None):
    client = GitHubGraphQLClient(token=token)
    fetcher = KanbanFetcher(client, org=org, project_number=project_number, label_filter=label_filter)
    items = fetcher.fetch_all()

    exporter = CsvExporter(output_dir)
    output_path = exporter.export(items, suffix=suffix)

    logger.info("snapshot salvo: %s (%s itens)", output_path, len(items))
    return output_path


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()
    token = _get_token()
    path = run(token=token, org=args.org, project_number=args.project, label_filter=args.label,
               suffix=args.suffix)
    print(f"Snapshot salvo em: {path}")


if __name__ == "__main__":
    main()
