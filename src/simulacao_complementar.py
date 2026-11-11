"""
Simulação complementar de Q1–Q3: efeitos negativos e α = 0,01.

Q2 e Q3 (simulacao_q2.py, simulacao_q3.py) varrem só d ≥ 0, ou seja, o bot mais lento
(T_bot = e^δ · T com δ ≥ 0). Mas nos dados reais o sinal é o contrário (δ = −0,42, bot mais
rápido), e o t de Welch não é simétrico em dados assimétricos. Este script repete a varredura com
os mesmos d positivos, na mesma ordem e com a mesma semente, e acrescenta os d negativos.
Por isso, as colunas de α = 5% para d ≥ 0 reproduzem exatamente data/simulacao_q3_poder.csv.

Também registra, na mesma varredura:
  - a proporção de rejeições com α = 1%, para responder o que muda quando α cai de 5% para 1%;
  - a parte das rejeições a α = 5% em que a estatística aponta o bot como mais rápido
    (t < 0 no Welch; U abaixo da média n_bot·n_humano/2 no Mann-Whitney).

Semente fixa: numpy.random.default_rng(42), um gerador por situação.

Saída: data/simulacao_complementar.csv (formato longo)
API reutilizável: simular_complementar()
"""

import os
import sys

import numpy as np
import pandas as pd

from simulacao import carregar_parametros, criar_rng, gerar
from simulacao_q3 import REPETICOES, SITUACOES, TAMANHOS_EFEITO
from testes import ALPHA, aplicar_testes

ALPHA_RIGOROSO = 0.01
# Primeiro os d de Q2/Q3, na mesma ordem (reproduz o fluxo aleatório); depois os negativos.
EFEITOS = TAMANHOS_EFEITO + tuple(-d for d in TAMANHOS_EFEITO if d > 0)
RAIZ = os.path.join(os.path.dirname(__file__), "..")
SAIDA = os.path.join(RAIZ, "data", "simulacao_complementar.csv")
TESTES = (("t de Welch", "welch"), ("Mann-Whitney U", "mann_whitney"))
COLUNAS = ["situacao", "rotulo_situacao", "d", "teste", "repeticoes",
           "rejeicoes_alfa05", "proporcao_alfa05", "rejeicoes_alfa01", "proporcao_alfa01",
           "rejeicoes_alfa05_bot_mais_rapido", "proporcao_alfa05_bot_mais_rapido"]


def _bot_mais_rapido(resultado) -> bool:
    """A estatística aponta o grupo bot como o de menor tempo."""
    if resultado.nome == "t de Welch":
        return resultado.estatistica < 0
    return resultado.estatistica < resultado.n_bot * resultado.n_humano / 2


def simular_complementar(
    parametros: dict,
    efeitos: tuple[float, ...] = EFEITOS,
    repeticoes: int = REPETICOES,
    situacoes: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Rejeições a α = 5% e 1% por situação, tamanho de efeito (com sinal) e teste."""
    situacoes = tuple(SITUACOES) if situacoes is None else situacoes
    if any(s not in SITUACOES for s in situacoes):
        raise ValueError(f"Situação deve ser uma de {tuple(SITUACOES)}")
    if repeticoes < 1:
        raise ValueError("O número de repetições deve ser positivo")
    if 0 not in efeitos:
        raise ValueError("Os tamanhos de efeito devem incluir zero (sem efeito)")

    linhas = []
    for situacao in situacoes:
        cfg = SITUACOES[situacao]
        rng = criar_rng()
        for d in efeitos:
            contagem = {chave: [0, 0, 0] for _, chave in TESTES}
            for _ in range(repeticoes):
                bot, humano = gerar(
                    parametros, h1=d != 0, d=d, n_bot=cfg["n_bot"], n_humano=cfg["n_humano"],
                    fator_sigma=cfg["fator_sigma"], rng=rng,
                )
                res = aplicar_testes(bot, humano)
                for _, chave in TESTES:
                    r = getattr(res, chave)
                    contagem[chave][0] += r.p_valor < ALPHA
                    contagem[chave][1] += r.p_valor < ALPHA_RIGOROSO
                    contagem[chave][2] += (r.p_valor < ALPHA) and _bot_mais_rapido(r)
            for teste, chave in TESTES:
                a05, a01, rapido = contagem[chave]
                linhas.append({
                    "situacao": situacao, "rotulo_situacao": cfg["rotulo"], "d": d,
                    "teste": teste, "repeticoes": repeticoes,
                    "rejeicoes_alfa05": int(a05), "proporcao_alfa05": a05 / repeticoes,
                    "rejeicoes_alfa01": int(a01), "proporcao_alfa01": a01 / repeticoes,
                    "rejeicoes_alfa05_bot_mais_rapido": int(rapido),
                    "proporcao_alfa05_bot_mais_rapido": rapido / repeticoes,
                })
    return pd.DataFrame(linhas, columns=COLUNAS)



def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    resultado = simular_complementar(carregar_parametros())
    resultado.round(6).to_csv(SAIDA, index=False)

    print(f"Complementar — {REPETICOES} repetições por d (semente 42), α = 5% e α = 1%")
    for alfa in ("alfa05", "alfa01"):
        print(f"\nProporção de rejeições, {alfa[-2:]}%:")
        tabela = resultado.pivot_table(index=["rotulo_situacao", "teste"], columns="d",
                                       values=f"proporcao_{alfa}")
        print(tabela.map(lambda v: f"{v:.1%}").to_string())
    print(f"\nSalvo em {SAIDA}")


if __name__ == "__main__":
    main()
