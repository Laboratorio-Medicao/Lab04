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

from graficos import amostras_g1, bordas_log, figura_g1, tabela_g1  # noqa: E402
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
    em_construcao("#6 e #8")


def secao_4() -> None:
    st.header("4. Erro tipo I")
    em_construcao("#15")


def secao_5() -> None:
    st.header("5. Poder")
    em_construcao("#16")


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
