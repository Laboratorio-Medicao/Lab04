"""
Q2 — Poder: curva de poder dos dois testes para efeitos de tamanhos crescentes.

Para cada tamanho de efeito d (padronizado em ln T, como em simulacao.delta_de_d)
gera 10.000 conjuntos com H₁ verdadeira (T_bot = e^δ · T_humano), aplica t de Welch e
Mann-Whitney e registra a proporção de p < α. Isso é o poder de cada teste em d.
d = 0 é H₀ verdadeira, então a proporção em d = 0 é o erro tipo I (Q1).

Tamanhos de efeito: 7 valores (≥ 5), começando em zero; d é o mesmo da Q3.
Semente fixa: numpy.random.default_rng(42), um único gerador para toda a curva.

A varredura é a mesma de simulacao_q3.simular_situacao na situação "normal"
(dados do cenário, n = 60 × 320); aqui só é exportada como Q2.

Sensibilidade (docs/cenario.md, Limitações): a cauda simulada é mais pesada que a real
(média teórica ~200 h contra 132 h), o que prejudica o t de Welch. Por isso a curva é
repetida com os tempos truncados no máximo observado nos dados reais (teto em horas),
com a mesma semente e os mesmos d.

Saídas (insumo para o G4, #16):
  data/simulacao_q2_poder.csv             curva principal: d, teste, repetições,
                                          rejeições, proporção de rejeições (poder), IC95%
  data/simulacao_q2_sensibilidade.csv     o mesmo formato, com a coluna `variante`
                                          ("sem truncamento" e "truncada no máximo real")

API reutilizável: simular_poder(), simular_sensibilidade(), teto_real().
"""

import os
import sys

import numpy as np
import pandas as pd

from simulacao import carregar_parametros, criar_rng, gerar
from simulacao_q3 import REPETICOES, TAMANHOS_EFEITO, TESTES, Z_95, simular_situacao
from testes import ALPHA, aplicar_testes

RAIZ = os.path.join(os.path.dirname(__file__), "..")
SAIDA_PODER = os.path.join(RAIZ, "data", "simulacao_q2_poder.csv")
SAIDA_SENSIBILIDADE = os.path.join(RAIZ, "data", "simulacao_q2_sensibilidade.csv")
DADOS_REAIS = os.path.join(RAIZ, "data", "dados_reais.csv")
SITUACAO = "normal"
COLUNAS = ["d", "teste", "repeticoes", "rejeicoes", "proporcao_rejeicoes",
           "ic95_inferior", "ic95_superior"]


def simular_poder(
    parametros: dict,
    tamanhos_efeito: tuple[float, ...] = TAMANHOS_EFEITO,
    repeticoes: int = REPETICOES,
    rng: np.random.Generator | None = None,
) -> pd.DataFrame:
    """Poder de cada teste por tamanho de efeito d (formato longo)."""
    _validar(tamanhos_efeito, repeticoes)
    rng = criar_rng() if rng is None else rng
    return simular_situacao(parametros, SITUACAO, tamanhos_efeito, repeticoes, rng)[COLUNAS]


def _validar(tamanhos_efeito: tuple[float, ...], repeticoes: int) -> None:
    if len(set(tamanhos_efeito)) < 5:
        raise ValueError("Q2 exige ao menos 5 tamanhos de efeito distintos")
    if 0 not in tamanhos_efeito:
        raise ValueError("Os tamanhos de efeito devem incluir zero (sem efeito)")
    if repeticoes < 1:
        raise ValueError("O número de repetições deve ser positivo")


def teto_real(caminho: str = DADOS_REAIS) -> float:
    """Maior tempo até o merge (h) observado nos dados reais, nos dois grupos."""
    return float(pd.read_csv(caminho)["horas_ate_merge"].max())


def simular_sensibilidade(
    parametros: dict,
    teto: float,
    tamanhos_efeito: tuple[float, ...] = TAMANHOS_EFEITO,
    repeticoes: int = REPETICOES,
    rng: np.random.Generator | None = None,
) -> pd.DataFrame:
    """Curva de poder com os tempos simulados truncados em `teto` horas (formato longo).

    O truncamento é aplicado antes do efeito: o deslocamento e^δ continua valendo sobre
    a distribuição base, e só depois o tempo é limitado a `teto`, como um tempo real
    nunca passa do máximo observado.
    """
    _validar(tamanhos_efeito, repeticoes)
    if teto <= 0:
        raise ValueError("O teto deve ser positivo")
    rng = criar_rng() if rng is None else rng

    linhas = []
    for d in tamanhos_efeito:
        rejeicoes = {chave: 0 for _, chave in TESTES}
        for _ in range(repeticoes):
            bot, humano = gerar(parametros, h1=d > 0, d=d, rng=rng)
            res = aplicar_testes(np.minimum(bot, teto), np.minimum(humano, teto))
            for _, chave in TESTES:
                rejeicoes[chave] += getattr(res, chave).p_valor < ALPHA
        for teste, chave in TESTES:
            proporcao = rejeicoes[chave] / repeticoes
            meia = Z_95 * np.sqrt(proporcao * (1 - proporcao) / repeticoes)
            linhas.append({
                "d": d, "teste": teste, "repeticoes": repeticoes,
                "rejeicoes": int(rejeicoes[chave]), "proporcao_rejeicoes": proporcao,
                "ic95_inferior": max(0.0, proporcao - meia),
                "ic95_superior": min(1.0, proporcao + meia),
            })
    return pd.DataFrame(linhas)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parametros = carregar_parametros()
    poder = simular_poder(parametros)
    teto = teto_real()
    truncada = simular_sensibilidade(parametros, teto)
    sensibilidade = pd.concat([
        poder.assign(variante="sem truncamento"),
        truncada.assign(variante="truncada no máximo real"),
    ], ignore_index=True)
    poder.round(6).to_csv(SAIDA_PODER, index=False)
    sensibilidade.round(6).to_csv(SAIDA_SENSIBILIDADE, index=False)

    print(f"Q2 — poder, {REPETICOES} repetições por d (semente 42, α = {ALPHA})")
    tabela = poder.pivot_table(index="teste", columns="d", values="proporcao_rejeicoes")
    print(tabela.map(lambda v: f"{v:.1%}").to_string())
    print(f"\nSensibilidade: tempos truncados em {teto:.0f} h (máximo dos dados reais)")
    tabela = truncada.pivot_table(index="teste", columns="d", values="proporcao_rejeicoes")
    print(tabela.map(lambda v: f"{v:.1%}").to_string())
    print(f"\nSalvo em {SAIDA_PODER}\n      e {SAIDA_SENSIBILIDADE}")


if __name__ == "__main__":
    main()
