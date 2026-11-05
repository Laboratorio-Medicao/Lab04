"""
Q1 — Erro tipo I: 10.000 repetições sob H₀ verdadeira.

Para cada repetição gera (bot, humano) da mesma distribuição (sem efeito), aplica
t de Welch e Mann-Whitney e registra o p-valor. A taxa de erro tipo I de cada teste
é a proporção de p < α (esperado: próximo de 5%).

Semente fixa: numpy.random.default_rng(42), um único gerador para todas as repetições.

Saídas (insumo para o G3, #15):
  data/simulacao_q1_pvalores.csv   um p-valor por repetição e teste (formato largo)
  data/simulacao_q1_resumo.csv     teste, situação, proporção de rejeições, IC

API reutilizável: simular_erro_tipo_i() → DataFrame de p-valores,
                  resumir(pvalores)     → DataFrame resumo.
"""

import os
import sys

import numpy as np
import pandas as pd

from simulacao import carregar_parametros, criar_rng, gerar
from testes import ALPHA, aplicar_testes

REPETICOES = 10_000
Z_95 = 1.959964
RAIZ = os.path.join(os.path.dirname(__file__), "..")
SAIDA_PVALORES = os.path.join(RAIZ, "data", "simulacao_q1_pvalores.csv")
SAIDA_RESUMO = os.path.join(RAIZ, "data", "simulacao_q1_resumo.csv")
SITUACAO = "H₀ verdadeira"


def simular_erro_tipo_i(
    parametros: dict,
    repeticoes: int = REPETICOES,
    rng: np.random.Generator | None = None,
    distribuicao: str = "mistura",
) -> pd.DataFrame:
    """Gera `repeticoes` conjuntos sob H₀ e devolve os p-valores dos dois testes."""
    if repeticoes < 1:
        raise ValueError("O número de repetições deve ser positivo")
    rng = criar_rng() if rng is None else rng

    welch = np.empty(repeticoes)
    mann_whitney = np.empty(repeticoes)
    for i in range(repeticoes):
        bot, humano = gerar(parametros, h1=False, distribuicao=distribuicao, rng=rng)
        res = aplicar_testes(bot, humano, cenario="h0")
        welch[i] = res.welch.p_valor
        mann_whitney[i] = res.mann_whitney.p_valor

    return pd.DataFrame({
        "repeticao": np.arange(1, repeticoes + 1),
        "p_welch": welch,
        "p_mann_whitney": mann_whitney,
    })


def resumir(pvalores: pd.DataFrame, alpha: float = ALPHA) -> pd.DataFrame:
    """Proporção de p < α por teste, com IC de 95% (aproximação normal, em pp)."""
    linhas = []
    for teste, coluna in (("t de Welch", "p_welch"), ("Mann-Whitney U", "p_mann_whitney")):
        n = len(pvalores)
        rejeicoes = int((pvalores[coluna] < alpha).sum())
        proporcao = rejeicoes / n
        meia_largura = Z_95 * np.sqrt(proporcao * (1 - proporcao) / n)
        linhas.append({
            "teste": teste,
            "situacao": SITUACAO,
            "repeticoes": n,
            "rejeicoes": rejeicoes,
            "proporcao_rejeicoes": proporcao,
            "ic95_inferior": max(0.0, proporcao - meia_largura),
            "ic95_superior": min(1.0, proporcao + meia_largura),
            "ic95_meia_largura_pp": meia_largura * 100,
        })
    return pd.DataFrame(linhas)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parametros = carregar_parametros()
    pvalores = simular_erro_tipo_i(parametros)
    resumo = resumir(pvalores)

    pvalores.to_csv(SAIDA_PVALORES, index=False)
    resumo.round(6).to_csv(SAIDA_RESUMO, index=False)

    print(f"Q1 — erro tipo I, {len(pvalores)} repetições sob H₀ (semente 42, α = {ALPHA})")
    for r in resumo.itertuples():
        print(f"  {r.teste:<15} rejeita {r.proporcao_rejeicoes:.2%} "
              f"(IC95% {r.ic95_inferior:.2%}–{r.ic95_superior:.2%}, ±{r.ic95_meia_largura_pp:.2f} pp)")
    print(f"Salvo em {SAIDA_PVALORES}\n      e {SAIDA_RESUMO}")


if __name__ == "__main__":
    main()
