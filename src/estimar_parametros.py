"""
Estima os parâmetros da simulação a partir de data/dados_reais.csv.

Modelo: mistura de duas lognormais, com os PRs separados em regime rápido
(menos de 1 hora) e regime lento. μ e σ são MLE condicional ao regime, ou seja,
média e desvio de ln(horas) dentro de cada regime.

Saída: data/parametros_simulacao.json, fonte única dos parâmetros para os
       scripts de simulação e para os gráficos do dashboard.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

LIMIAR_RAPIDO_H = 1.0
SEMENTE = 42
FONTE = "data/dados_reais.csv"
RAIZ = os.path.join(os.path.dirname(__file__), "..")
OUTPUT = os.path.join(RAIZ, "data", "parametros_simulacao.json")
QUANTIS = {"q25": 0.25, "mediana": 0.5, "q75": 0.75, "q90": 0.9}


def log_positivo(horas: np.ndarray) -> np.ndarray:
    if (horas <= 0).any():
        raise ValueError("Os tempos até o merge devem ser positivos")
    return np.log(horas)


def ajustar_mistura(horas: np.ndarray, limiar: float = LIMIAR_RAPIDO_H) -> dict:
    logs = log_positivo(horas)
    rapido = horas < limiar
    if rapido.sum() < 2 or (~rapido).sum() < 2:
        raise ValueError("Cada regime precisa de pelo menos duas observações")
    return {
        "p_rapido": float(rapido.mean()),
        "mu_rapido": float(logs[rapido].mean()),
        "sigma_rapido": float(logs[rapido].std()),
        "mu_lento": float(logs[~rapido].mean()),
        "sigma_lento": float(logs[~rapido].std()),
    }


def ajustar_lognormal(horas: np.ndarray) -> dict:
    logs = log_positivo(horas)
    return {"mu": float(logs.mean()), "sigma": float(logs.std())}


def amostrar_mistura(params: dict, tamanho: tuple[int, int], rng: np.random.Generator) -> np.ndarray:
    rapido = rng.random(tamanho) < params["p_rapido"]
    mu = np.where(rapido, params["mu_rapido"], params["mu_lento"])
    sigma = np.where(rapido, params["sigma_rapido"], params["sigma_lento"])
    return np.exp(rng.normal(mu, sigma))


def resumir(amostras: np.ndarray) -> dict:
    """Resume cada réplica (linha) e devolve a mediana entre as réplicas."""
    resumo = {nome: np.quantile(amostras, q, axis=1) for nome, q in QUANTIS.items()}
    resumo["media"] = amostras.mean(axis=1)
    resumo["maximo"] = amostras.max(axis=1)
    return {nome: float(np.median(valores)) for nome, valores in resumo.items()}


def comparar_modelos(horas: np.ndarray, rng: np.random.Generator, n_rep: int = 5000) -> dict:
    lognormal = ajustar_lognormal(horas)
    tamanho = (n_rep, len(horas))
    return {
        "real": resumir(horas[np.newaxis, :]),
        "lognormal": resumir(rng.lognormal(lognormal["mu"], lognormal["sigma"], tamanho)),
        "mistura": resumir(amostrar_mistura(ajustar_mistura(horas), tamanho, rng)),
    }


def descrever(horas: np.ndarray) -> dict:
    return {
        "minimo": float(horas.min()),
        "mediana": float(np.median(horas)),
        "media": float(horas.mean()),
        "maximo": float(horas.max()),
        "desvio": float(horas.std(ddof=1)),
        "assimetria": float(stats.skew(horas)),
    }


def estimar(caminho_csv: str, semente: int = SEMENTE) -> dict:
    dados = pd.read_csv(caminho_csv)
    bot = dados.loc[dados["grupo"] == "com_bot", "horas_ate_merge"].to_numpy()
    humano = dados.loc[dados["grupo"] == "sem_bot", "horas_ate_merge"].to_numpy()
    combinado = np.concatenate([bot, humano])

    rng = np.random.default_rng(semente)
    n = {"com_bot": len(bot), "sem_bot": len(humano)}
    delta = float(log_positivo(bot).mean() - log_positivo(humano).mean())
    sigma_log_h0 = ajustar_lognormal(combinado)["sigma"]

    return {
        "fonte": FONTE,
        "limiar_rapido_h": LIMIAR_RAPIDO_H,
        "semente": semente,
        "n": n,
        "descritivas": {"com_bot": descrever(bot), "sem_bot": descrever(humano)},
        "mistura": {
            "com_bot": ajustar_mistura(bot),
            "sem_bot": ajustar_mistura(humano),
            "h0": ajustar_mistura(combinado),
        },
        "comparacao": {
            "com_bot": comparar_modelos(bot, rng),
            "sem_bot": comparar_modelos(humano, rng),
        },
        "simulacao": {
            "base": "mistura.h0",
            "n": n,
            "sinais_delta": [-1, 1],
            "sigma_log_h0": sigma_log_h0,
        },
        "delta_log_observado": delta,
        "delta_padronizado": delta / sigma_log_h0,
    }


def arredondar(valor):
    if isinstance(valor, dict):
        return {chave: arredondar(item) for chave, item in valor.items()}
    return round(valor, 4) if isinstance(valor, float) else valor


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parametros = arredondar(estimar(os.path.join(RAIZ, FONTE)))
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(parametros, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Salvo em {OUTPUT}")
    for grupo, params in parametros["mistura"].items():
        print(f"  {grupo}: {params}")
    print(f"  δ observado: {parametros['delta_log_observado']}"
          f"  |  δ padronizado: {parametros['delta_padronizado']}")


if __name__ == "__main__":
    main()
