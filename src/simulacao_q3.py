"""
Q3 — Violação de pressuposto: repete Q1 (erro tipo I) e Q2 (curva de poder) em
situações adversas ao t de Welch, e compara com a situação normal.

Situações (cada uma com sua própria semente 42, um único gerador por situação):
  normal             cenário base (n = 60 × 320), que já é muito assimétrico: referência de
                     Q1 e Q2. O id "normal" é histórico; não é uma situação com dados normais
  amostras_pequenas  n = 10 por grupo (n ≤ 10): o TCL deixa de proteger o t de Welch
  outliers_extremos  cauda muito mais pesada (σ de ln T × 1,5) com n do cenário:
                     a média passa a ser dominada por poucos valores extremos

Em cada situação varre o tamanho de efeito d (padronizado em ln T, como em
simulacao.delta_de_d), com 10.000 repetições por d. d = 0 é H₀ verdadeira, logo a
proporção de p < α em d = 0 é a Q1 e as demais são a curva de poder (Q2).
Na situação normal, d = 0 reproduz exatamente data/simulacao_q1_*.csv.

Saídas (insumo para G3, #15, e G4, #16):
  data/simulacao_q3_poder.csv        situação, d, teste, repetições, rejeições,
                                     proporção, IC95%  (formato longo)
  data/simulacao_q3_comparacao.csv   erro tipo I e poder em cada situação × normal

API reutilizável: simular_situacao(), simular_todas(), comparar().
"""

import os
import sys

import numpy as np
import pandas as pd

from simulacao import carregar_parametros, criar_rng, gerar
from testes import ALPHA, aplicar_testes

REPETICOES = 10_000
TAMANHOS_EFEITO = (0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0)
Z_95 = 1.959964
RAIZ = os.path.join(os.path.dirname(__file__), "..")
SAIDA_PODER = os.path.join(RAIZ, "data", "simulacao_q3_poder.csv")
SAIDA_COMPARACAO = os.path.join(RAIZ, "data", "simulacao_q3_comparacao.csv")

# n=None mantém o n do cenário (60 com bot × 320 sem bot)
SITUACOES = {
    "normal": {"rotulo": "Cenário base (já assimétrico)", "n_bot": None, "n_humano": None, "fator_sigma": 1.0},
    "amostras_pequenas": {"rotulo": "Amostras pequenas (n = 10)", "n_bot": 10, "n_humano": 10, "fator_sigma": 1.0},
    "outliers_extremos": {"rotulo": "Outliers extremos (σ × 1,5)", "n_bot": None, "n_humano": None, "fator_sigma": 1.5},
}
SITUACAO_REFERENCIA = "normal"
TESTES = (("t de Welch", "welch"), ("Mann-Whitney U", "mann_whitney"))


def simular_situacao(
    parametros: dict,
    situacao: str,
    tamanhos_efeito: tuple[float, ...] = TAMANHOS_EFEITO,
    repeticoes: int = REPETICOES,
    rng: np.random.Generator | None = None,
) -> pd.DataFrame:
    """Rejeições de cada teste por tamanho de efeito, numa situação (formato longo)."""
    if situacao not in SITUACOES:
        raise ValueError(f"Situação deve ser uma de {tuple(SITUACOES)}")
    if repeticoes < 1:
        raise ValueError("O número de repetições deve ser positivo")
    if not tamanhos_efeito or any(d < 0 for d in tamanhos_efeito):
        raise ValueError("Os tamanhos de efeito devem ser não negativos")
    cfg = SITUACOES[situacao]
    rng = criar_rng() if rng is None else rng

    linhas = []
    for d in tamanhos_efeito:
        rejeicoes = {chave: 0 for _, chave in TESTES}
        for _ in range(repeticoes):
            bot, humano = gerar(
                parametros, h1=d > 0, d=d, n_bot=cfg["n_bot"], n_humano=cfg["n_humano"],
                fator_sigma=cfg["fator_sigma"], rng=rng,
            )
            res = aplicar_testes(bot, humano)
            for _, chave in TESTES:
                rejeicoes[chave] += getattr(res, chave).p_valor < ALPHA
        for teste, chave in TESTES:
            proporcao = rejeicoes[chave] / repeticoes
            meia = Z_95 * np.sqrt(proporcao * (1 - proporcao) / repeticoes)
            linhas.append({
                "situacao": situacao,
                "rotulo_situacao": cfg["rotulo"],
                "d": d,
                "teste": teste,
                "repeticoes": repeticoes,
                "rejeicoes": int(rejeicoes[chave]),
                "proporcao_rejeicoes": proporcao,
                "ic95_inferior": max(0.0, proporcao - meia),
                "ic95_superior": min(1.0, proporcao + meia),
            })
    return pd.DataFrame(linhas)


def simular_todas(
    parametros: dict,
    tamanhos_efeito: tuple[float, ...] = TAMANHOS_EFEITO,
    repeticoes: int = REPETICOES,
) -> pd.DataFrame:
    """Roda todas as situações, cada uma com a semente fixa."""
    return pd.concat(
        [simular_situacao(parametros, s, tamanhos_efeito, repeticoes, criar_rng()) for s in SITUACOES],
        ignore_index=True,
    )


def comparar(poder: pd.DataFrame) -> pd.DataFrame:
    """Para cada situação adversa, d e teste: proporção, e diferença para a situação normal.

    Em d = 0 a proporção é o erro tipo I (Q1); em d > 0 é o poder (Q2).
    """
    chave = ["d", "teste"]
    ref = poder[poder["situacao"] == SITUACAO_REFERENCIA][chave + ["proporcao_rejeicoes"]]
    ref = ref.rename(columns={"proporcao_rejeicoes": "proporcao_normal"})
    adversas = poder[poder["situacao"] != SITUACAO_REFERENCIA]
    comp = adversas.merge(ref, on=chave, how="left")
    comp["metrica"] = np.where(comp["d"] == 0, "erro tipo I (Q1)", "poder (Q2)")
    comp["diferenca_pp"] = (comp["proporcao_rejeicoes"] - comp["proporcao_normal"]) * 100
    return comp[["situacao", "rotulo_situacao", "metrica", "d", "teste",
                 "proporcao_rejeicoes", "proporcao_normal", "diferenca_pp"]]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parametros = carregar_parametros()
    poder = simular_todas(parametros)
    comparacao = comparar(poder)

    poder.round(6).to_csv(SAIDA_PODER, index=False)
    comparacao.round(6).to_csv(SAIDA_COMPARACAO, index=False)

    print(f"Q3 — violação de pressuposto, {REPETICOES} repetições por d (semente 42, α = {ALPHA})")
    print("\nErro tipo I (d = 0):")
    for r in poder[poder["d"] == 0].itertuples():
        print(f"  {r.rotulo_situacao:<30} {r.teste:<15} {r.proporcao_rejeicoes:.2%}")
    print("\nPoder:")
    tabela = poder[poder["d"] > 0].pivot_table(
        index=["rotulo_situacao", "teste"], columns="d", values="proporcao_rejeicoes")
    print(tabela.map(lambda v: f"{v:.1%}").to_string())
    print(f"\nSalvo em {SAIDA_PODER}\n      e {SAIDA_COMPARACAO}")


if __name__ == "__main__":
    main()
