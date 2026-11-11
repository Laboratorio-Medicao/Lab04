"""
Executa o pipeline do LAB04 do início ao fim, com um único comando:

    python -m executar_tudo                # regenera parâmetros, simulações e CSVs de data/
    python -m executar_tudo --dashboard    # idem e abre o dashboard no fim
    python -m executar_tudo --coletar      # inclui a coleta dos dados reais (exige `gh auth login`)

Etapas, na ordem: estimar parâmetros → dados simulados → Q1 → Q2 → Q3 → complementar.
Todas usam a semente fixa numpy.random.default_rng(42), então duas execuções geram
exatamente os mesmos arquivos. A coleta fica de fora por padrão: precisa de token do
GitHub, e os dados reais já estão versionados em data/dados_reais.csv.
"""

import argparse
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))


def etapas(coletar: bool = False) -> list[tuple[str, str]]:
    """(descrição, módulo de src/ com função main) na ordem de execução."""
    lista = [
        ("Estimar parâmetros da simulação", "estimar_parametros"),
        ("Gerar dados simulados (H₀ e H₁)", "simulacao"),
        ("Q1: erro tipo I", "simulacao_q1"),
        ("Q2: poder", "simulacao_q2"),
        ("Q3: violação de pressuposto", "simulacao_q3"),
        ("Complementar: efeitos negativos e α = 1%", "simulacao_complementar"),
    ]
    if coletar:
        lista.insert(0, ("Coletar dados reais (API do GitHub)", "coletar_dados"))
    return lista


def executar(coletar: bool = False) -> None:
    import importlib

    plano = etapas(coletar)
    inicio = time.time()
    for i, (descricao, modulo) in enumerate(plano, start=1):
        print(f"\n[{i}/{len(plano)}] {descricao}", flush=True)
        t0 = time.time()
        importlib.import_module(modulo).main()
        print(f"      concluído em {time.time() - t0:.0f} s", flush=True)
    print(f"\nPipeline completo em {time.time() - inicio:.0f} s. Arquivos em data/.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Executa o pipeline do LAB04 do início ao fim")
    parser.add_argument("--coletar", action="store_true",
                        help="inclui a coleta dos dados reais (exige gh auth login)")
    parser.add_argument("--dashboard", action="store_true", help="abre o dashboard ao terminar")
    args = parser.parse_args(argv)

    executar(args.coletar)
    if args.dashboard:
        import dashboard
        dashboard.main()


if __name__ == "__main__":
    main()
