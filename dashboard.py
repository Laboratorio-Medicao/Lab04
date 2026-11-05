"""
Dashboard do LAB04. Execute na raiz do repositório:

    python -m dashboard

O comando inicia o Streamlit com este mesmo arquivo. Cada seção tem a própria
função, e cada card preenche a sua.
"""

import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import runtime

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

from graficos import (  # noqa: E402
    PAINEIS_G4, amostras_g1, bordas_log, dados_g4, estatisticas_h0, exemplo_g2, figura_g1,
    figura_g2, figura_g4, tabela_g1, tabela_g4,
)
from simulacao import carregar_parametros  # noqa: E402


def em_construcao(card: str) -> None:
    st.info(f"Em construção: card {card}.")


def texto_g1(parametros: dict) -> str:
    bot = round(parametros["mistura"]["com_bot"]["p_rapido"] * 100)
    humano = round(parametros["mistura"]["sem_bot"]["p_rapido"] * 100)
    maximo = f"{parametros['descritivas']['sem_bot']['maximo']:,.0f}".replace(",", ".")
    return (
        f"Cerca de {bot}% dos PRs do Dependabot e {humano}% dos PRs humanos são mergeados em menos "
        "de 1 hora, e os demais levam de horas a dias no Dependabot e de horas a meses nos humanos. "
        f"Por isso, os dados são muito assimétricos, com outliers de até {maximo} horas. "
        "A simulação usa uma mistura de duas lognormais, com média e desvio de ln(T) calculados em "
        "cada regime, separados em 1 hora, porque uma lognormal única exagerava a média e o máximo "
        "do grupo humano. "
        "A mistura reproduz a forma geral dos dados reais, mas ainda gera uma cauda mais pesada que "
        "a observada, sobretudo no grupo humano."
    )


def texto_g2(exemplo: dict) -> str:
    def v(x: float) -> str:
        return f"{x:.2f}".replace(".", ",")

    w, mw = exemplo["welch"], exemplo["mann_whitney"]
    rejeita = [t for t in (w, mw) if t["p_valor"] < 0.05]
    conclusao = ("nenhum teste cai na região de rejeição, então H₀ não é rejeitada." if not rejeita
                 else "ao menos um teste cai na região de rejeição, o que seria um falso positivo.")
    return (
        "O t de Welch compara as médias dos dois grupos e o Mann-Whitney compara se um PR de um grupo "
        "tende a demorar mais que o do outro. Como o teste é bicaudal, a região de rejeição (cinza) fica "
        "nas duas caudas, onde a estatística seria rara sob H₀ (5% no total). "
        f"No exemplo, sorteado sob H₀, o t vale {v(w['estatistica'])} (p = {v(w['p_valor'])}) e o Z do "
        f"Mann-Whitney vale {v(mw['estatistica'])} (p = {v(mw['p_valor'])}). "
        "O p-valor é a área em vermelho: a chance de obter uma estatística tão extrema quanto a do exemplo "
        "se H₀ fosse verdadeira, e " + conclusao

    )


def texto_g4(dados: pd.DataFrame) -> str:
    def pct(situacao: str, teste: str, d: float) -> float:
        linha = dados[(dados["situacao"] == situacao) & (dados["teste"] == teste) & (dados["d"] == d)]
        return float(linha["proporcao_rejeicoes"].iloc[0])

    def p(x: float) -> str:
        return f"{x:.0%}".replace(".", ",")

    d_max = float(dados["d"].max())
    welch_ganha = [
        PAINEIS_G4[s].lower() for s in PAINEIS_G4
        if any(pct(s, "t de Welch", d) > pct(s, "Mann-Whitney U", d) for d in dados["d"].unique() if d > 0)
    ]
    vantagem = ("em todas as situações simuladas e em todo d > 0" if not welch_ganha
                else "na maior parte da curva, com exceção de " + "; ".join(welch_ganha))
    return (
        f"O Mann-Whitney tem mais poder que o t de Welch {vantagem}: na situação normal, com "
        f"d = {d_max:g}, ele rejeita {p(pct('normal', 'Mann-Whitney U', d_max))} das vezes e o Welch, "
        f"{p(pct('normal', 't de Welch', d_max))}. "
        "A violação de pressuposto derruba sobretudo o Welch: com amostras pequenas o Mann-Whitney "
        f"chega a {p(pct('amostras_pequenas', 'Mann-Whitney U', d_max))} e o Welch, a "
        f"{p(pct('amostras_pequenas', 't de Welch', d_max))}, e com outliers extremos o Welch fica em "
        f"{p(pct('outliers_extremos', 't de Welch', d_max))}. "
        "O valor em d = 0 não é poder, e sim o erro tipo I, que o Welch infla além de 5% na situação normal."
    )


@st.cache_data
def dados_g2() -> tuple[dict, dict]:
    parametros = carregar_parametros()
    return estatisticas_h0(parametros), exemplo_g2(parametros)


def secao_1() -> None:
    st.header("1. Cenário")
    em_construcao("#20")


def secao_2() -> None:
    st.header("2. Os dados")
    parametros = carregar_parametros()
    try:
        amostras = amostras_g1(pd.read_csv(RAIZ / "data" / "dados_reais.csv"), parametros)
    except (ValueError, OSError) as erro:
        st.error(f"Não foi possível montar o G1 com data/dados_reais.csv: {erro}")
        return
    st.plotly_chart(figura_g1(amostras), theme=None, width="stretch")
    st.caption("Cada grupo simulado tem 10.000 sorteios da mistura do próprio grupo, com semente fixa 42.")
    st.write(texto_g1(parametros))
    with st.expander("Ver dados do G1"):
        tabela = tabela_g1(amostras, bordas_log(amostras))
        st.dataframe(tabela.style.format(precision=1, decimal=","), hide_index=True)


def secao_3() -> None:
    st.header("3. Como os testes funcionam")
    estatisticas, exemplo = dados_g2()
    st.plotly_chart(figura_g2(estatisticas, exemplo), theme=None, width="stretch")
    st.caption("Histograma de 2.000 conjuntos sorteados sob H₀ (n = 60 e 320), com semente fixa 42. "
               "A curva é a distribuição teórica: t com graus de liberdade de Welch e normal padrão para o U padronizado.")
    st.write(texto_g2(exemplo))


def secao_4() -> None:
    st.header("4. Erro tipo I")
    em_construcao("#15")


def secao_5() -> None:
    st.header("5. Poder")
    try:
        dados = dados_g4(pd.read_csv(RAIZ / "data" / "simulacao_q2_poder.csv"),
                         pd.read_csv(RAIZ / "data" / "simulacao_q3_poder.csv"))
    except (ValueError, OSError) as erro:
        st.error(f"Não foi possível montar o G4 com os CSVs de poder da Q2 e da Q3: {erro}")
        return
    st.plotly_chart(figura_g4(dados), theme=None, width="stretch")
    st.caption("Cada ponto tem 10.000 repetições por teste, com semente fixa 42. A linha pontilhada é α = 5%.")
    st.write(texto_g4(dados))
    with st.expander("Ver dados do G4"):
        st.dataframe(tabela_g4(dados).style.format(precision=1, decimal=","), hide_index=True)


def secao_6() -> None:
    st.header("6. Dados reais")
    em_construcao("#22")


def secao_7() -> None:
    st.header("7. Conclusão")
    em_construcao("#22")


def renderizar() -> None:
    st.set_page_config(page_title="LAB04", layout="wide")
    st.title("LAB04: Testes de Hipótese por Dentro")
    st.caption("t de Welch × Mann-Whitney no tempo até o merge de PRs de pallets/flask")
    secao_1()
    secao_2()
    secao_3()
    secao_4()
    secao_5()
    secao_6()
    secao_7()


def main() -> None:
    if runtime.exists():
        renderizar()
        return
    try:
        resultado = subprocess.run([sys.executable, "-m", "streamlit", "run", str(RAIZ / "dashboard.py")])
    except KeyboardInterrupt:
        sys.exit(0)
    sys.exit(resultado.returncode)


if __name__ == "__main__":
    main()
