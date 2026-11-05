"""
Paleta do projeto e gráficos do dashboard.

G1: histogramas do tempo até o merge, dados reais × simulados, um painel por
grupo. Cada grupo real é comparado com a mistura do próprio grupo, portanto o
G1 não usa `simulacao.gerar`, que sorteia de mistura.h0 nos dois grupos.
"""

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from estimar_parametros import amostrar_mistura, log_positivo

# Mesma cor para cada grupo e teste em todos os gráficos do projeto.
# Validada com validate_palette.js em superfície clara, para pares adjacentes:
# - grupos e testes nunca aparecem no mesmo gráfico, porque mann_whitney × sem_bot
#   fica abaixo do piso de separação;
# - welch e mann_whitney têm contraste abaixo de 3:1, então G2 a G4 precisam de
#   legenda visível e tabela.
CORES = {
    "com_bot": "#2a78d6",
    "sem_bot": "#eb6834",
    "welch": "#1baf7a",
    "mann_whitney": "#eda100",
}
SUPERFICIE = "#fcfcfb"
TINTA = "#52514e"
GRADE = "#e1e0d9"

GRUPOS = {"com_bot": "Dependabot", "sem_bot": "Humanos"}
SEMENTE = 42
N_SIMULADO_G1 = 10_000
OPACIDADE_SIMULADO = 0.3


def horas_do_grupo(dados: pd.DataFrame, grupo: str) -> np.ndarray:
    if "horas_ate_merge" not in dados.columns:
        raise ValueError("O CSV precisa da coluna horas_ate_merge")
    horas = pd.to_numeric(dados.loc[dados["grupo"] == grupo, "horas_ate_merge"], errors="coerce")
    if horas.empty:
        raise ValueError(f"O grupo {grupo} não tem observações no CSV")
    log_positivo(horas.to_numpy(dtype=float))
    return horas.to_numpy(dtype=float)


def amostras_g1(
    dados: pd.DataFrame,
    parametros: dict,
    semente: int = SEMENTE,
    n_simulado: int = N_SIMULADO_G1,
) -> dict[str, dict[str, np.ndarray]]:
    rng = np.random.default_rng(semente)
    amostras = {}
    for grupo in GRUPOS:
        amostras[grupo] = {
            "real": horas_do_grupo(dados, grupo),
            "simulado": amostrar_mistura(parametros["mistura"][grupo], (n_simulado,), rng),
        }
    return amostras


def bordas_log(amostras: dict, por_decada: int = 2) -> np.ndarray:
    """Bordas das faixas em log10(horas), comuns a todos os painéis."""
    horas = np.concatenate([valores for grupo in amostras.values() for valores in grupo.values()])
    log_positivo(horas)
    inferior = math.floor(np.log10(horas.min()))
    superior = math.ceil(np.log10(horas.max()))
    return np.linspace(inferior, superior, por_decada * (superior - inferior) + 1)


def percentuais(horas: np.ndarray, bordas: np.ndarray) -> np.ndarray:
    contagem, _ = np.histogram(np.log10(horas), bordas)
    return 100 * contagem / len(horas)


def formatar_horas(horas: float) -> str:
    """Formata com dois algarismos significativos, no padrão brasileiro."""
    casas = 1 - math.floor(math.log10(horas))
    texto = f"{round(horas, casas):,.{max(casas, 0)}f}"
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def rotulo_faixa(inferior: float, superior: float) -> str:
    return f"{formatar_horas(10.0 ** inferior)} a {formatar_horas(10.0 ** superior)}"


def tabela_g1(amostras: dict, bordas: np.ndarray) -> pd.DataFrame:
    tabela = {"Faixa (h)": [rotulo_faixa(a, b) for a, b in zip(bordas[:-1], bordas[1:])]}
    for grupo, nome in GRUPOS.items():
        tabela[f"{nome} real (%)"] = percentuais(amostras[grupo]["real"], bordas)
        tabela[f"{nome} simulado (%)"] = percentuais(amostras[grupo]["simulado"], bordas)
    return pd.DataFrame(tabela)


def com_opacidade(cor: str, alfa: float) -> str:
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {alfa})"


def figura_g1(amostras: dict) -> go.Figure:
    bordas = bordas_log(amostras)
    centros = (bordas[:-1] + bordas[1:]) / 2
    faixas = [rotulo_faixa(a, b) for a, b in zip(bordas[:-1], bordas[1:])]
    decadas = list(range(math.ceil(bordas[0]), math.floor(bordas[-1]) + 1))

    figura = make_subplots(
        rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.08,
        subplot_titles=[f"{nome} (n={len(amostras[grupo]['real'])} reais)" for grupo, nome in GRUPOS.items()],
    )
    for coluna, (grupo, nome) in enumerate(GRUPOS.items(), start=1):
        cor = CORES[grupo]
        real = percentuais(amostras[grupo]["real"], bordas)
        simulado = percentuais(amostras[grupo]["simulado"], bordas)
        series = [
            (f"{nome}: real", real, {"color": cor}),
            (f"{nome}: simulado (modelo)", simulado, {
                "color": com_opacidade(cor, OPACIDADE_SIMULADO),
                "line": {"color": cor, "width": np.where(simulado > 0, 1.5, 0)},
            }),
        ]
        for rotulo, valores, marcador in series:
            figura.add_trace(go.Bar(
                x=centros, y=valores, name=rotulo, marker=marcador, customdata=faixas,
                hovertemplate="%{customdata} h<br>%{y:.1f}% dos PRs<extra>%{fullData.name}</extra>",
            ), row=1, col=coluna)

    figura.update_layout(
        title="G1: tempo até o merge, dados reais × simulados",
        showlegend=True, barmode="group", bargap=0.15, separators=",.", height=460,
        paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE, font={"color": TINTA},
        legend={"orientation": "h", "y": -0.22},
    )
    figura.update_xaxes(
        title_text="Tempo até o merge (horas, escala log)",
        tickmode="array", tickvals=decadas, tickangle=0, ticks="outside",
        ticktext=[formatar_horas(10.0 ** d) if d % 2 == 0 else "" for d in decadas],
        range=[bordas[0], bordas[-1]], showgrid=False,
    )
    figura.update_yaxes(gridcolor=GRADE, zeroline=False)
    figura.update_yaxes(title_text="PRs do grupo (%)", row=1, col=1)
    limiar = {"x": 0, "line_dash": "dot", "line_color": TINTA, "line_width": 1, "row": 1}
    figura.add_vline(col=1, annotation_text="1 h", **limiar)
    figura.add_vline(col=2, **limiar)
    return figura


# ---------------------------------------------------------------------------
# G2: distribuição da estatística de teste sob H₀
# ---------------------------------------------------------------------------

N_REPETICOES_G2 = 2_000
TESTES_G2 = {"welch": "t de Welch", "mann_whitney": "Mann-Whitney U (padronizado)"}


def _graus_welch(a: np.ndarray, b: np.ndarray) -> float:
    va, vb = np.var(a, ddof=1) / len(a), np.var(b, ddof=1) / len(b)
    return float((va + vb) ** 2 / (va**2 / (len(a) - 1) + vb**2 / (len(b) - 1)))


def padronizar_u(u: np.ndarray | float, n_bot: int, n_humano: int) -> np.ndarray | float:
    """Z = (U − μ_U) / σ_U, a aproximação normal do U sob H₀ (sem correção de empates)."""
    media = n_bot * n_humano / 2
    desvio = math.sqrt(n_bot * n_humano * (n_bot + n_humano + 1) / 12)
    return (u - media) / desvio


def estatisticas_h0(
    parametros: dict,
    n_repeticoes: int = N_REPETICOES_G2,
    semente: int = SEMENTE,
) -> dict[str, np.ndarray]:
    """Monte Carlo: t de Welch e Z do Mann-Whitney em amostras sorteadas sob H₀."""
    from scipy import stats

    rng = np.random.default_rng(semente)
    n_bot, n_humano = parametros["n"]["com_bot"], parametros["n"]["sem_bot"]
    h0 = parametros["mistura"]["h0"]
    bot = amostrar_mistura(h0, (n_repeticoes, n_bot), rng)
    humano = amostrar_mistura(h0, (n_repeticoes, n_humano), rng)
    t = stats.ttest_ind(bot, humano, axis=1, equal_var=False).statistic
    postos = stats.rankdata(np.concatenate([bot, humano], axis=1), axis=1)
    u = postos[:, :n_bot].sum(axis=1) - n_bot * (n_bot + 1) / 2
    return {"welch": np.asarray(t), "mann_whitney": padronizar_u(u, n_bot, n_humano)}


def exemplo_g2(parametros: dict, semente: int = SEMENTE) -> dict:
    """Um conjunto sorteado sob H₀ (mesma semente do README) e o resultado dos dois testes."""
    from simulacao import criar_rng, gerar
    from testes import aplicar_testes

    bot, humano = gerar(parametros, h1=False, rng=criar_rng(semente))
    res = aplicar_testes(bot, humano, cenario="H₀ verdadeira")
    n_bot, n_humano = len(bot), len(humano)
    return {
        "welch": {"estatistica": res.welch.estatistica, "p_valor": res.welch.p_valor,
                  "gl": _graus_welch(bot, humano)},
        "mann_whitney": {"estatistica": float(padronizar_u(res.mann_whitney.estatistica, n_bot, n_humano)),
                         "p_valor": res.mann_whitney.p_valor},
    }


def figura_g2(estatisticas: dict, exemplo: dict, alpha: float = 0.05) -> go.Figure:
    """Um painel por teste: histograma Monte Carlo sob H₀, curva teórica, região de rejeição e p-valor."""
    from scipy import stats

    def distribuicao(chave: str):
        if chave == "welch":
            return stats.t(exemplo["welch"]["gl"])
        return stats.norm()

    figura = make_subplots(rows=1, cols=2, horizontal_spacing=0.1,
                           subplot_titles=[nome for nome in TESTES_G2.values()])
    for coluna, (chave, nome) in enumerate(TESTES_G2.items(), start=1):
        cor, dist = CORES[chave], distribuicao(chave)
        obs, p = exemplo[chave]["estatistica"], exemplo[chave]["p_valor"]
        crit = float(dist.ppf(1 - alpha / 2))
        limite = max(5.0, abs(obs) + 1, crit + 1)
        x = np.linspace(-limite, limite, 600)
        dens = dist.pdf(x)

        def area(mascara, rotulo, cor_area, grupo, mostrar_legenda):
            # Uma região por cauda: um único polígono ligaria as caudas pelo centro.
            esquerda = mascara & (x < 0)
            direita = mascara & (x > 0)
            for i, cauda in enumerate((esquerda, direita)):
                xs, ys = x[cauda], dens[cauda]
                figura.add_trace(go.Scatter(
                    x=np.concatenate([xs, xs[::-1]]), y=np.concatenate([ys, np.zeros_like(ys)]),
                    fill="toself", mode="lines", line={"width": 0}, fillcolor=cor_area,
                    name=rotulo, legendgroup=grupo, showlegend=mostrar_legenda and i == 0,
                    hoverinfo="skip",
                ), row=1, col=coluna)

        contagem_x = np.clip(estatisticas[chave], -limite, limite)
        figura.add_trace(go.Histogram(
            x=contagem_x, histnorm="probability density", nbinsx=50,
            marker={"color": com_opacidade(cor, 0.35), "line": {"color": cor, "width": 0.5}},
            name=f"{nome}: Monte Carlo sob H₀", legendgroup=chave,
            hovertemplate="estatística %{x:.2f}<br>densidade %{y:.3f}<extra></extra>",
        ), row=1, col=coluna)
        figura.add_trace(go.Scatter(
            x=x, y=dens, mode="lines", line={"color": cor, "width": 2.5},
            name=f"{nome}: curva teórica", legendgroup=chave, hoverinfo="skip",
        ), row=1, col=coluna)
        area(np.abs(x) >= crit, f"Região de rejeição (α = {alpha:g})".replace(".", ","), com_opacidade(TINTA, 0.35),
             f"rej{chave}", coluna == 1)
        area(np.abs(x) >= abs(obs), "Área do p-valor do exemplo", com_opacidade("#c0392b", 0.55),
             f"p{chave}", coluna == 1)
        topo = max(dens.max(), np.histogram(contagem_x, bins=50, density=True)[0].max()) * 1.3
        figura.add_vline(x=obs, line_color="#c0392b", line_width=2, row=1, col=coluna)
        figura.add_annotation(
            x=obs, y=topo, xanchor="right" if obs < 0 else "left", yanchor="top", showarrow=False,
            text=f"exemplo: {obs:.2f}<br>p = {p:.3f}".replace(".", ","), font={"color": "#c0392b"},
            xshift=-6 if obs < 0 else 6, row=1, col=coluna,
        )
        figura.update_yaxes(range=[0, topo], row=1, col=coluna)
        figura.update_xaxes(title_text=f"Estatística de teste ({'t' if chave == 'welch' else 'Z'})",
                            range=[-limite, limite], row=1, col=coluna)

    figura.update_layout(
        title="G2: distribuição da estatística sob H₀ (bicaudal)",
        showlegend=True, barmode="overlay", separators=",.", height=480,
        paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE, font={"color": TINTA},
        legend={"orientation": "h", "y": -0.28},
    )
    figura.update_xaxes(showgrid=False, zeroline=False)
    figura.update_yaxes(gridcolor=GRADE, zeroline=False)
    figura.update_yaxes(title_text="Densidade", row=1, col=1)
    figura.update_yaxes(title_text="Densidade", row=1, col=2)
    return figura


# ---------------------------------------------------------------------------
# G4: curvas de poder dos dois testes
# ---------------------------------------------------------------------------

TESTES_G4 = {"t de Welch": "welch", "Mann-Whitney U": "mann_whitney"}
# Painéis do G4: a situação normal vem da Q2 e as de violação de pressuposto, da Q3.
PAINEIS_G4 = {
    "normal": "Situação normal (Q2)",
    "amostras_pequenas": "Violação: amostras pequenas (Q3)",
    "outliers_extremos": "Violação: outliers extremos (Q3)",
}
COLUNAS_G4 = ["d", "teste", "proporcao_rejeicoes", "ic95_inferior", "ic95_superior"]


def dados_g4(q2_poder: pd.DataFrame, q3_poder: pd.DataFrame) -> pd.DataFrame:
    """Junta a curva da Q2 (normal) e as da Q3 (violações) em um formato longo, por situação."""
    faltam = [c for c in COLUNAS_G4 if c not in q2_poder.columns or c not in q3_poder.columns]
    if faltam:
        raise ValueError(f"Faltam colunas nos CSVs de poder: {', '.join(faltam)}")
    adversas = [s for s in PAINEIS_G4 if s != "normal"]
    if "situacao" not in q3_poder.columns or not set(adversas) <= set(q3_poder["situacao"]):
        raise ValueError(f"O CSV da Q3 precisa das situações {', '.join(adversas)}")
    partes = [q2_poder[COLUNAS_G4].assign(situacao="normal")]
    for situacao in adversas:
        partes.append(q3_poder.loc[q3_poder["situacao"] == situacao, COLUNAS_G4].assign(situacao=situacao))
    dados = pd.concat(partes, ignore_index=True)
    if not set(TESTES_G4) <= set(dados["teste"]):
        raise ValueError("Os CSVs de poder precisam dos dois testes")
    return dados


def tabela_g4(dados: pd.DataFrame) -> pd.DataFrame:
    """Poder (%) por situação e d, uma coluna por teste."""
    tabela = dados.pivot_table(index=["situacao", "d"], columns="teste", values="proporcao_rejeicoes")
    tabela = (tabela * 100).reset_index()
    tabela["situacao"] = tabela["situacao"].map(PAINEIS_G4)
    return tabela.rename(columns={"situacao": "Situação", "d": "d",
                                  **{t: f"{t} (%)" for t in TESTES_G4}})


def figura_g4(dados: pd.DataFrame, alpha: float = 0.05) -> go.Figure:
    """Um painel por situação: proporção de rejeições × tamanho do efeito, os dois testes juntos."""
    figura = make_subplots(
        rows=1, cols=len(PAINEIS_G4), shared_yaxes=True, horizontal_spacing=0.05,
        subplot_titles=list(PAINEIS_G4.values()),
    )
    for coluna, situacao in enumerate(PAINEIS_G4, start=1):
        for teste, chave in TESTES_G4.items():
            serie = dados[(dados["situacao"] == situacao) & (dados["teste"] == teste)].sort_values("d")
            cor = CORES[chave]
            figura.add_trace(go.Scatter(
                x=serie["d"], y=serie["proporcao_rejeicoes"], mode="lines+markers", name=teste,
                legendgroup=chave, showlegend=coluna == 1,
                line={"color": cor, "width": 2.5, "dash": "solid" if chave == "mann_whitney" else "dash"},
                marker={"color": cor, "size": 7},
                customdata=np.stack([serie["ic95_inferior"], serie["ic95_superior"]], axis=-1),
                hovertemplate=("d = %{x}<br>rejeita %{y:.1%} (IC95% %{customdata[0]:.1%} a "
                               "%{customdata[1]:.1%})<extra>%{fullData.name}</extra>"),
            ), row=1, col=coluna)
        figura.add_hline(y=alpha, line_dash="dot", line_color=TINTA, line_width=1, row=1, col=coluna)
    # Entrada só de legenda para a linha de α, sem rótulo em cima dos pontos.
    figura.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines", name=f"α = {alpha:.0%}".replace(".", ","),
        line={"color": TINTA, "width": 1, "dash": "dot"}, hoverinfo="skip", showlegend=True,
    ))

    figura.update_layout(
        title="G4: curvas de poder do t de Welch e do Mann-Whitney",
        showlegend=True, separators=",.", height=460,
        paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE, font={"color": TINTA},
        legend={"orientation": "h", "y": -0.22},
    )
    figura.update_xaxes(title_text="Tamanho do efeito d (padronizado em ln T)", showgrid=False, zeroline=False)
    figura.update_yaxes(gridcolor=GRADE, zeroline=False, range=[0, 1], tickformat=".0%")
    figura.update_yaxes(title_text="Proporção de rejeições (poder)", row=1, col=1)
    return figura
