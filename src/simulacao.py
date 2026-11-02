"""
Gera dados simulados de tempo até o merge (horas) para os dois grupos.

Parâmetros: data/parametros_simulacao.json (fonte única, gerada por
estimar_parametros.py). Semente fixa: numpy.random.default_rng(42).

Cenários:
  H₀ verdadeira: os dois grupos saem de forma independente da mesma distribuição.
  H₁ verdadeira: T_humano ~ distribuição base e T_bot = e^δ · T, com δ = d · σ_log_h0.
                 O deslocamento torna falsas as duas H₀ (Welch e Mann-Whitney).

Distribuições: "mistura" (duas lognormais, padrão do cenário) ou "lognormal" (única).

Saída: data/dados_simulados.csv, com um conjunto H₀ e um H₁ para conferência
       e uso nos scripts de análise e no dashboard.
"""

import json
import os
import sys

import numpy as np
import pandas as pd

from estimar_parametros import amostrar_mistura

SEMENTE = 42
RAIZ = os.path.join(os.path.dirname(__file__), "..")
PARAMETROS = os.path.join(RAIZ, "data", "parametros_simulacao.json")
OUTPUT = os.path.join(RAIZ, "data", "dados_simulados.csv")
DISTRIBUICOES = ("mistura", "lognormal")


def carregar_parametros(caminho: str = PARAMETROS) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def criar_rng(semente: int = SEMENTE) -> np.random.Generator:
    return np.random.default_rng(semente)


def delta_de_d(d: float, parametros: dict) -> float:
    """Converte o tamanho de efeito padronizado d no deslocamento δ de ln(T)."""
    return d * parametros["simulacao"]["sigma_log_h0"]


def amostrar(
    parametros: dict,
    tamanho: int,
    rng: np.random.Generator,
    distribuicao: str = "mistura",
    fator_sigma: float = 1.0,
) -> np.ndarray:
    """Sorteia `tamanho` tempos (h) da distribuição base (mistura.h0).

    `fator_sigma` multiplica o desvio de ln(T): 1 mantém os dados reais, valores
    maiores deixam a cauda mais pesada e menores deixam a amostra mais comportada.
    """
    if distribuicao not in DISTRIBUICOES:
        raise ValueError(f"Distribuição deve ser uma de {DISTRIBUICOES}")
    if tamanho < 1:
        raise ValueError("O tamanho da amostra deve ser positivo")
    if fator_sigma <= 0:
        raise ValueError("O fator de desvio deve ser positivo")

    base = parametros["mistura"]["h0"]
    if distribuicao == "mistura":
        escalada = dict(base)
        escalada["sigma_rapido"] *= fator_sigma
        escalada["sigma_lento"] *= fator_sigma
        return amostrar_mistura(escalada, (tamanho,), rng)
    mu = base["p_rapido"] * base["mu_rapido"] + (1 - base["p_rapido"]) * base["mu_lento"]
    sigma = parametros["simulacao"]["sigma_log_h0"] * fator_sigma
    return rng.lognormal(mu, sigma, tamanho)


def gerar(
    parametros: dict,
    h1: bool = False,
    d: float = 0.0,
    n_bot: int | None = None,
    n_humano: int | None = None,
    distribuicao: str = "mistura",
    fator_sigma: float = 1.0,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Gera (bot, humano) em horas. Com h1=False o efeito d é ignorado (H₀)."""
    n = parametros["simulacao"]["n"]
    n_bot = n["com_bot"] if n_bot is None else n_bot
    n_humano = n["sem_bot"] if n_humano is None else n_humano
    rng = criar_rng() if rng is None else rng

    humano = amostrar(parametros, n_humano, rng, distribuicao, fator_sigma)
    bot = amostrar(parametros, n_bot, rng, distribuicao, fator_sigma)
    if h1:
        bot = bot * np.exp(delta_de_d(d, parametros))
    return bot, humano


def montar_tabela(cenario: str, bot: np.ndarray, humano: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({
        "cenario": cenario,
        "grupo": ["com_bot"] * len(bot) + ["sem_bot"] * len(humano),
        "horas_ate_merge": np.concatenate([bot, humano]),
    })


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parametros = carregar_parametros()
    d = abs(parametros["delta_padronizado"])

    rng = criar_rng()
    h0 = gerar(parametros, rng=rng)
    h1 = gerar(parametros, h1=True, d=d, rng=rng)

    tabela = pd.concat([montar_tabela("h0", *h0), montar_tabela("h1", *h1)], ignore_index=True)
    tabela["horas_ate_merge"] = tabela["horas_ate_merge"].round(4)
    tabela.to_csv(OUTPUT, index=False)

    print(f"Salvo em {OUTPUT} (semente {SEMENTE}, d da H₁ = {d})")
    print(tabela.groupby(["cenario", "grupo"])["horas_ate_merge"]
          .agg(["count", "median", "mean", "max"]).round(2))


if __name__ == "__main__":
    main()
