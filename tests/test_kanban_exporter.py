"""Testes para kanban/exporter.py."""

import csv
from datetime import date

from kanban.exporter import CsvExporter
from kanban.models import KanbanItem

ITENS = [KanbanItem(17, "[S6] Sprint S02 — Snapshot do Kanban", "Done", ("ALuiz19",), ("lab04", "sprint-s02"))]
DIA = date(2026, 11, 5)


def test_nome_padrao_usa_so_a_data(tmp_path):
    caminho = CsvExporter(tmp_path).export(ITENS, snapshot_date=DIA)
    assert caminho.name == "kanban-snapshot-2026-11-05.csv"


def test_sufixo_separa_snapshots_do_mesmo_dia(tmp_path):
    exportador = CsvExporter(tmp_path)
    s01 = exportador.export(ITENS, snapshot_date=DIA)
    s02 = exportador.export(ITENS, snapshot_date=DIA, suffix="s02")
    assert s02.name == "kanban-snapshot-2026-11-05-s02.csv"
    assert s01.exists() and s02.exists()


def test_csv_tem_uma_linha_por_card(tmp_path):
    caminho = CsvExporter(tmp_path).export(ITENS, snapshot_date=DIA, suffix="s02")
    with caminho.open(encoding="utf-8") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    assert linhas == [{"number": "17", "title": "[S6] Sprint S02 — Snapshot do Kanban", "status": "Done",
                       "assignees": "ALuiz19", "labels": "lab04|sprint-s02"}]
