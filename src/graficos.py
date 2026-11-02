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
