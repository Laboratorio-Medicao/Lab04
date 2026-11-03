"""
Aplica t de Welch e Mann-Whitney U a dados simulados e interpreta os resultados.

API principal:
    aplicar_testes(bot, humano)      → ResultadoTestes
    verificar_pressupostos(bot, humano) → PressupostosWelch
    interpretar(res, ctx)            → str

Uso como script:
    python src/testes.py             # exibe resultados para H₀ e H₁ com d observado
    python src/testes.py --d 0.5     # usa d = 0,5
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass

import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# Tipos de resultado
# ---------------------------------------------------------------------------


@dataclass
class ResultadoTeste:
    nome: str                # "t de Welch" ou "Mann-Whitney U"
    estatistica: float       # t com sinal (Welch) ou U do grupo bot (Mann-Whitney)
    p_valor: float           # bicaudal em ambos
    rejeita_h0: bool         # p_valor < ALPHA
    tamanho_efeito: float    # Cohen's d (Welch) ou r = Z/√N (Mann-Whitney)
    nome_efeito: str         # nome da métrica de tamanho de efeito
    n_bot: int
    n_humano: int


@dataclass
class ResultadoTestes:
    welch: ResultadoTeste
    mann_whitney: ResultadoTeste
    cenario: str             # "h0" ou "h1"


@dataclass
class PressupostosWelch:
    shapiro_bot_stat: float
    shapiro_bot_p: float
    shapiro_humano_stat: float
    shapiro_humano_p: float
    normalidade_ok: bool     # ambos p > 0.05
    levene_stat: float
    levene_p: float
    variancia_igual: bool    # p > 0.05 (Welch ignora, mas registramos)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

ALPHA = 0.05


# ---------------------------------------------------------------------------
# Funções de cálculo
# ---------------------------------------------------------------------------


def _cohen_d(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's d com desvio agrupado (pooled SD), sinal: média(a) − média(b)."""
    n_a, n_b = len(a), len(b)
    var_a = np.var(a, ddof=1)
    var_b = np.var(b, ddof=1)
    pooled = math.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
    if pooled == 0:
        return 0.0
    return float((np.mean(a) - np.mean(b)) / pooled)


def _r_mann_whitney(u_stat: float, n_bot: int, n_humano: int) -> float:
    """r = Z / sqrt(N), onde Z é a aproximação normal de U."""
    n_total = n_bot + n_humano
    mu_u = n_bot * n_humano / 2
    sigma_u = math.sqrt(n_bot * n_humano * (n_total + 1) / 12)
    if sigma_u == 0:
        return 0.0
    z = (u_stat - mu_u) / sigma_u
    return float(z / math.sqrt(n_total))


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def verificar_pressupostos(bot: np.ndarray, humano: np.ndarray) -> PressupostosWelch:
    """Testa normalidade (Shapiro-Wilk) e igualdade de variâncias (Levene)."""
    # Shapiro-Wilk requer n ≤ 5000; usa amostra se necessário
    MAX_SW = 5000
    bot_sw = bot[:MAX_SW]
    hum_sw = humano[:MAX_SW]

    sw_bot = stats.shapiro(bot_sw)
    sw_hum = stats.shapiro(hum_sw)
    lev = stats.levene(bot, humano)

    return PressupostosWelch(
        shapiro_bot_stat=float(sw_bot.statistic),
        shapiro_bot_p=float(sw_bot.pvalue),
        shapiro_humano_stat=float(sw_hum.statistic),
        shapiro_humano_p=float(sw_hum.pvalue),
        normalidade_ok=(sw_bot.pvalue > ALPHA and sw_hum.pvalue > ALPHA),
        levene_stat=float(lev.statistic),
        levene_p=float(lev.pvalue),
        variancia_igual=(lev.pvalue > ALPHA),
    )


def aplicar_testes(
    bot: np.ndarray,
    humano: np.ndarray,
    cenario: str = "?",
) -> ResultadoTestes:
    """Aplica t de Welch e Mann-Whitney U (ambos bicaudais) a bot × humano."""
    bot = np.asarray(bot, dtype=float)
    humano = np.asarray(humano, dtype=float)

    # t de Welch (equal_var=False é o padrão, mas tornamos explícito)
    t_res = stats.ttest_ind(bot, humano, equal_var=False, alternative="two-sided")
    d = _cohen_d(bot, humano)

    welch = ResultadoTeste(
        nome="t de Welch",
        estatistica=float(t_res.statistic),
        p_valor=float(t_res.pvalue),
        rejeita_h0=bool(t_res.pvalue < ALPHA),
        tamanho_efeito=d,
        nome_efeito="Cohen's d",
        n_bot=len(bot),
        n_humano=len(humano),
    )

    # Mann-Whitney U — U do grupo bot, bicaudal
    u_res = stats.mannwhitneyu(bot, humano, alternative="two-sided")
    r = _r_mann_whitney(float(u_res.statistic), len(bot), len(humano))

    mw = ResultadoTeste(
        nome="Mann-Whitney U",
        estatistica=float(u_res.statistic),
        p_valor=float(u_res.pvalue),
        rejeita_h0=bool(u_res.pvalue < ALPHA),
        tamanho_efeito=r,
        nome_efeito="r (Z/√N)",
        n_bot=len(bot),
        n_humano=len(humano),
    )

    return ResultadoTestes(welch=welch, mann_whitney=mw, cenario=cenario)


def interpretar(res: ResultadoTestes, verbose: bool = True) -> str:
    """Retorna interpretação em português para o par de resultados."""
    linhas: list[str] = []
    alpha_pct = int(ALPHA * 100)

    for r in (res.welch, res.mann_whitney):
        veredicto = (
            f"REJEITA H₀ (p = {r.p_valor:.4f} < {ALPHA})"
            if r.rejeita_h0
            else f"NÃO rejeita H₀ (p = {r.p_valor:.4f} ≥ {ALPHA})"
        )
        linhas.append(f"[{r.nome}]  {veredicto}")
        linhas.append(
            f"  Estatística: {r.estatistica:.4f}  |  "
            f"{r.nome_efeito}: {r.tamanho_efeito:.4f}  |  "
            f"n_bot={r.n_bot}, n_humano={r.n_humano}"
        )

        if verbose:
            # O que o p-valor significa
            if r.rejeita_h0:
                linhas.append(
                    f"  Interpretação: se os dois grupos tivessem a mesma distribuição "
                    f"de tempo até o merge (H₀), obteríamos uma diferença tão grande "
                    f"quanto a observada em menos de {r.p_valor * 100:.1f}% das amostras "
                    f"desse tamanho, só por acaso. Com α = {ALPHA}, os dados são "
                    f"incompatíveis com H₀."
                )
            else:
                linhas.append(
                    f"  Interpretação: se os dois grupos tivessem a mesma distribuição "
                    f"(H₀), obteríamos uma diferença tão grande em {r.p_valor * 100:.1f}% "
                    f"das amostras — não é evidência suficiente para descartar H₀ "
                    f"com α = {ALPHA}."
                )
            # O que o p-valor NÃO significa
            linhas.append(
                "  O p-valor NÃO é a probabilidade de H₀ ser verdadeira, "
                "NÃO mede o tamanho do efeito e NÃO garante relevância prática."
            )
        linhas.append("")

    return "\n".join(linhas).rstrip()


# ---------------------------------------------------------------------------
# Script
# ---------------------------------------------------------------------------


def _cabecalho(cenario: str) -> str:
    return f"{'='*60}\nCenário: {cenario}\n{'='*60}"


def main(argv: list[str] | None = None) -> None:
    sys.path.insert(0, str(__file__).replace("testes.py", ""))

    parser = argparse.ArgumentParser(description="Aplica t de Welch e Mann-Whitney a dados simulados")
    parser.add_argument("--d", type=float, default=None, help="Tamanho de efeito d para H₁ (padrão: d observado nos dados reais)")
    args = parser.parse_args(argv)

    from simulacao import carregar_parametros, criar_rng, gerar  # noqa: PLC0415

    parametros = carregar_parametros()
    d_obs = abs(parametros["delta_padronizado"])
    d_h1 = args.d if args.d is not None else d_obs

    rng = criar_rng()

    # --- H₀ verdadeira ---
    bot_h0, hum_h0 = gerar(parametros, h1=False, rng=rng)
    res_h0 = aplicar_testes(bot_h0, hum_h0, cenario="H₀ verdadeira (sem efeito)")
    pre_h0 = verificar_pressupostos(bot_h0, hum_h0)

    print(_cabecalho(res_h0.cenario))
    print()
    print("Pressupostos do t de Welch:")
    print(f"  Shapiro-Wilk bot:    W={pre_h0.shapiro_bot_stat:.4f}, p={pre_h0.shapiro_bot_p:.2e}  → normalidade {'OK' if pre_h0.normalidade_ok else 'VIOLADA'}")
    print(f"  Shapiro-Wilk humano: W={pre_h0.shapiro_humano_stat:.4f}, p={pre_h0.shapiro_humano_p:.2e}")
    print(f"  Levene (var. igual): F={pre_h0.levene_stat:.4f}, p={pre_h0.levene_p:.2e}  → {'iguais' if pre_h0.variancia_igual else 'diferentes'}")
    print()
    print(interpretar(res_h0))

    # --- H₁ verdadeira ---
    bot_h1, hum_h1 = gerar(parametros, h1=True, d=d_h1, rng=rng)
    res_h1 = aplicar_testes(bot_h1, hum_h1, cenario=f"H₁ verdadeira (d = {d_h1:.4f})")
    pre_h1 = verificar_pressupostos(bot_h1, hum_h1)

    print()
    print(_cabecalho(res_h1.cenario))
    print()
    print("Pressupostos do t de Welch:")
    print(f"  Shapiro-Wilk bot:    W={pre_h1.shapiro_bot_stat:.4f}, p={pre_h1.shapiro_bot_p:.2e}  → normalidade {'OK' if pre_h1.normalidade_ok else 'VIOLADA'}")
    print(f"  Shapiro-Wilk humano: W={pre_h1.shapiro_humano_stat:.4f}, p={pre_h1.shapiro_humano_p:.2e}")
    print(f"  Levene (var. igual): F={pre_h1.levene_stat:.4f}, p={pre_h1.levene_p:.2e}  → {'iguais' if pre_h1.variancia_igual else 'diferentes'}")
    print()
    print(interpretar(res_h1))


if __name__ == "__main__":
    main()
