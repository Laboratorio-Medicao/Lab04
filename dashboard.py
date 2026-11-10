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
URL_REPOSITORIO = "https://github.com/Laboratorio-Medicao/Lab04"
URL_PROJECTS = "https://github.com/orgs/Laboratorio-Medicao/projects/1"
sys.path.insert(0, str(RAIZ / "src"))

from graficos import (  # noqa: E402
    PAINEIS_G4, amostras_g1, bordas_log, dados_g3, dados_g4, estatisticas_h0, exemplo_g2,
    figura_g1, figura_g2, figura_g3, figura_g4, tabela_g1, tabela_g3, tabela_g4,
)
from graficos import resultado_g5, tabela_g5  # noqa: E402
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
    parametros = carregar_parametros()
    n_bot = parametros["n"]["com_bot"]
    n_humano = parametros["n"]["sem_bot"]
    n_total = n_bot + n_humano
    st.markdown(
        "**Pergunta:** o tempo até o merge de PRs abertos pelo Dependabot difere do tempo "
        "até o merge de PRs abertos por humanos no repositório "
        "[pallets/flask](https://github.com/pallets/flask)?"
    )
    st.markdown(
        "**Fonte dos dados:** GitHub GraphQL API — PRs merged criados entre 2021-04-28 e 2024-08-01 "
        f"(janela comum aos dois grupos). Total: **{n_total} PRs** — "
        f"**{n_bot}** abertos pelo Dependabot e **{n_humano}** por humanos."
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**H₀ (hipótese nula)**")
        st.markdown(
            "Os dois grupos têm a mesma distribuição de tempo até o merge: "
            "não há diferença sistemática entre PRs do bot e de humanos."
        )
        st.markdown("| Teste | H₀ |\n|---|---|\n"
                    "| t de Welch | μ_bot = μ_humano |\n"
                    "| Mann-Whitney | P(T_bot > T_humano) = P(T_bot < T_humano) |")
    with col2:
        st.markdown("**H₁ (hipótese alternativa) — bicaudal**")
        st.markdown(
            "Os grupos têm distribuições diferentes: um tende a ser mergeado "
            "mais rápido (ou mais devagar) que o outro. "
            "Bicaudal porque não há razão a priori para assumir a direção do efeito."
        )
        st.markdown("| Teste | H₁ |\n|---|---|\n"
                    "| t de Welch | μ_bot ≠ μ_humano |\n"
                    "| Mann-Whitney | P(T_bot > T_humano) ≠ P(T_bot < T_humano) |")
    st.caption(
        "Par de testes: P1 — t de Welch × Mann-Whitney U. "
        "Nível de significância: α = 5%. Testes aplicados ao tempo em horas, sem transformação."
    )



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


def texto_g3(dados: pd.DataFrame) -> str:
    def v(situacao: str, teste: str) -> float:
        return float(dados[(dados["situacao"] == situacao) & (dados["teste"] == teste)]["proporcao_rejeicoes"].iloc[0])

    def p(x: float) -> str:
        return f"{x:.1%}".replace(".", ",")

    def classe(x: float) -> str:
        return "liberal" if x > 0.06 else "conservador" if x < 0.04 else "perto de 5%"

    w = {s: v(s, "t de Welch") for s in ("H₀ verdadeira", "amostras_pequenas", "outliers_extremos")}
    mw = {s: v(s, "Mann-Whitney U") for s in w}
    return (
        f"O Mann-Whitney ficou perto de 5% nas três situações, entre {p(min(mw.values()))} e {p(max(mw.values()))}. "
        f"O t de Welch foi o que se desviou: {classe(w['H₀ verdadeira'])} na situação normal ({p(w['H₀ verdadeira'])}), "
        f"{classe(w['amostras_pequenas'])} com amostras pequenas ({p(w['amostras_pequenas'])}) e "
        f"{classe(w['outliers_extremos'])} com outliers extremos ({p(w['outliers_extremos'])}). "
        "O excesso de rejeições do Welch vem da forte assimetria dos dados, que prejudica a aproximação normal da "
        "estatística t. "
        "Com n = 10 essa aproximação piora ainda mais, e o teste quase nunca rejeita."
    )


def secao_4() -> None:
    st.header("4. Erro tipo I")
    try:
        dados = dados_g3(
            pd.read_csv(RAIZ / "data" / "simulacao_q1_resumo.csv"),
            pd.read_csv(RAIZ / "data" / "simulacao_q3_comparacao.csv"),
        )
    except (ValueError, OSError) as erro:
        st.error(f"Não foi possível montar o G3: {erro}")
        return
    st.plotly_chart(figura_g3(dados), theme=None, width="stretch")
    st.caption("10.000 repetições por situação e por teste, com semente fixa 42. A linha pontilhada é α = 5%.")
    st.write(texto_g3(dados))
    with st.expander("Ver dados do G3"):
        st.dataframe(tabela_g3(dados).style.format(precision=1, decimal=","), hide_index=True)


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


def formatar_p(p: float) -> str:
    return "< 0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")


def p_igual(p: float) -> str:
    """'p < 0,001' ou 'p = 0,983'."""
    return f"p {formatar_p(p)}" if p < 0.001 else f"p = {formatar_p(p)}"


def _num(x: float, casas: int = 2) -> str:
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _magnitude(valor: float, limites: tuple[float, float, float]) -> str:
    a = abs(valor)
    return ("desprezível" if a < limites[0] else "pequeno" if a < limites[1]
            else "médio" if a < limites[2] else "grande")


def texto_secao_6(res) -> str:
    w, mw = res.welch, res.mann_whitney
    if w.rejeita_h0 and mw.rejeita_h0:
        acordo = "Os dois testes rejeitam H₀ a α = 5%, então chegam à mesma conclusão."
    elif not w.rejeita_h0 and not mw.rejeita_h0:
        acordo = "Como nenhum dos dois testes rejeita H₀ a α = 5%, eles chegam à mesma conclusão."
    else:
        sim, nao = (w, mw) if w.rejeita_h0 else (mw, w)
        acordo = f"As conclusões divergem: a α = 5%, o {sim.nome} rejeita H₀ e o {nao.nome} não rejeita."
    return (
        f"Com {w.n_bot} PRs do Dependabot e {w.n_humano} PRs humanos, o t de Welch vale {_num(w.estatistica)} "
        f"({p_igual(w.p_valor)}) e o U do Mann-Whitney vale {_num(mw.estatistica, 1)} ({p_igual(mw.p_valor)}). "
        f"{acordo} "
        f"O Cohen's d de {_num(w.tamanho_efeito)} indica um efeito {_magnitude(w.tamanho_efeito, (0.2, 0.5, 0.8))} "
        f"na diferença de médias, e o r de {_num(mw.tamanho_efeito, 3)} indica um efeito "
        f"{_magnitude(mw.tamanho_efeito, (0.1, 0.3, 0.5))} na tendência de um PR de um grupo demorar mais que o "
        "do outro. O Welch reage às médias, que poucos PRs muito lentos puxam para cima, enquanto o Mann-Whitney "
        "compara posições e quase não é afetado por esses outliers."
    )


def _taxa(dados: pd.DataFrame, situacao: str, teste: str, d: float | None = None) -> float:
    filtro = (dados["situacao"] == situacao) & (dados["teste"] == teste)
    if d is not None:
        filtro &= dados["d"] == d
    return float(dados.loc[filtro, "proporcao_rejeicoes"].iloc[0])


TESTES = ("t de Welch", "Mann-Whitney U")
NOMES = {"t de Welch": "t de Welch", "Mann-Whitney U": "Mann-Whitney"}


def recomendado(g3: pd.DataFrame, g4: pd.DataFrame) -> str:
    """Teste com erro tipo I mais perto de 5% em média nas situações simuladas; no empate, o de mais poder."""
    desvio = {t: (g3.loc[g3["teste"] == t, "proporcao_rejeicoes"] - 0.05).abs().mean() for t in TESTES}
    poder = {t: g4.loc[(g4["teste"] == t) & (g4["d"] > 0), "proporcao_rejeicoes"].mean() for t in TESTES}
    return min(TESTES, key=lambda t: (round(desvio[t], 3), -poder[t]))


def texto_secao_7(res, g3: pd.DataFrame, g4: pd.DataFrame) -> list[str]:
    def p(x: float) -> str:
        return f"{x:.1%}".replace(".", ",")

    escolhido = recomendado(g3, g4)
    outro = next(t for t in TESTES if t != escolhido)
    erros = {t: [_taxa(g3, s, t) for s in g3["situacao"].unique()] for t in TESTES}
    d_ref = 0.5
    poder = {t: _taxa(g4, "normal", t, d_ref) for t in TESTES}
    def classe(x: float) -> str:
        return "liberal" if x > 0.06 else "conservador" if x < 0.04 else "perto de 5%"

    def welch_poder(situacao: str, d: float) -> float:
        return _taxa(g4, situacao, "t de Welch", d)

    w_normal = _taxa(g3, "H₀ verdadeira", "t de Welch")
    w_outliers = _taxa(g3, "outliers_extremos", "t de Welch")
    w_pequenas = _taxa(g3, "amostras_pequenas", "t de Welch")
    ds = sorted(float(d) for d in g4["d"].unique() if d > 0)
    d_min, d_seg, d_max = ds[0], ds[1], ds[-1]
    d_min_out = min(ds, key=lambda d: welch_poder("outliers_extremos", d))
    min_out = welch_poder("outliers_extremos", d_min_out)
    real = {"t de Welch": res.welch, "Mann-Whitney U": res.mann_whitney}
    achado = ("A simulação confirmou a expectativa" if escolhido == "Mann-Whitney U"
              else "A simulação não confirmou a expectativa")
    evidencia = "há evidência" if real[escolhido].rejeita_h0 else "não há evidência"
    return [
        "**Expectativa.** Antes de simular, esperávamos que o Mann-Whitney fosse mais confiável nestes dados, "
        "porque o tempo até o merge é muito assimétrico e tem outliers. Também esperávamos que o t de Welch "
        "tivesse erro tipo I fora de 5%, já que a aproximação normal da estatística t sofre com essa assimetria.",
        f"**Achados.** {achado}: sob H₀, o Mann-Whitney rejeitou entre {p(min(erros['Mann-Whitney U']))} e "
        f"{p(max(erros['Mann-Whitney U']))} das vezes nas situações simuladas, enquanto o t de Welch foi "
        f"{classe(w_normal)} na situação normal ({p(w_normal)}), {classe(w_outliers)} com outliers extremos "
        f"({p(w_outliers)}) e {classe(w_pequenas)} com amostras pequenas ({p(w_pequenas)}). "
        f"Com d = {_num(d_ref, 1)} na situação normal, o poder foi de {p(poder['Mann-Whitney U'])} no Mann-Whitney "
        f"e de {p(poder['t de Welch'])} no t de Welch, cujo poder nem cresce sempre com o efeito: na situação "
        f"normal cai de {p(welch_poder('normal', d_min))} em d = {_num(d_min, 1)} para "
        f"{p(welch_poder('normal', d_seg))} em d = {_num(d_seg, 1)}, e com outliers extremos desce a "
        f"{p(min_out)} em d = {_num(d_min_out, 1)} e só chega a {p(welch_poder('outliers_extremos', d_max))} em "
        f"d = {_num(d_max, 1)}. "
        f"Nos dados reais, o {NOMES[escolhido]} deu {p_igual(real[escolhido].p_valor)} e o {NOMES[outro]}, "
        f"{p_igual(real[outro].p_valor)}.",
        f"**Recomendação.** Recomendamos o {NOMES[escolhido]} para comparar o tempo até o merge de PRs do "
        "Dependabot e de humanos, porque nas situações simuladas ele manteve o erro tipo I mais perto de 5% e "
        f"teve mais poder, enquanto o {NOMES[outro]} se desviou de 5% para os dois lados e teve poder baixo e instável "
        f"nas situações simuladas. Por ele, {evidencia} a α = 5% de que um grupo tende a ser mergeado mais rápido que "
        "o outro.",
        "**Quando mudaria.** Se a pergunta fosse sobre a média, por exemplo o tempo total de espera somado de "
        "todos os PRs, o t de Welch seria o teste adequado, porque o Mann-Whitney não compara médias. "
        "O Welch também ficaria mais atraente com amostras grandes e pouco assimétricas, em que a aproximação "
        "normal da estatística t funciona bem.",
        "**Limitação.** Os dados vêm de um único repositório (pallets/flask), e a simulação usa uma mistura de "
        "lognormais estimada desses mesmos dados, então os resultados podem não valer para outros projetos. "
        "Além disso, o Mann-Whitney testa se um grupo tende a ter valores maiores que o outro, e não a "
        "diferença de médias, o que limita o que se conclui sobre o tempo médio.",
    ]


def secao_6() -> None:
    st.header("6. Dados reais")
    try:
        res = resultado_g5(pd.read_csv(RAIZ / "data" / "dados_reais.csv"))
    except (ValueError, OSError) as erro:
        st.error(f"Não foi possível aplicar os testes a data/dados_reais.csv: {erro}")
        return
    st.dataframe(
        tabela_g5(res).style.format({"Estatística": _num, "p-valor": formatar_p,
                                     "Tamanho do efeito": lambda x: _num(x, 3)}),
        hide_index=True,
    )
    st.caption("Testes bicaudais, aplicados com a mesma função usada na simulação.")
    st.write(texto_secao_6(res))


def secao_7() -> None:
    st.header("7. Conclusão")
    try:
        res = resultado_g5(pd.read_csv(RAIZ / "data" / "dados_reais.csv"))
        g3 = dados_g3(pd.read_csv(RAIZ / "data" / "simulacao_q1_resumo.csv"),
                      pd.read_csv(RAIZ / "data" / "simulacao_q3_comparacao.csv"))
        g4 = dados_g4(pd.read_csv(RAIZ / "data" / "simulacao_q2_poder.csv"),
                      pd.read_csv(RAIZ / "data" / "simulacao_q3_poder.csv"))
    except (ValueError, OSError) as erro:
        st.error(f"Não foi possível montar a conclusão com os CSVs de data/: {erro}")
        return
    for bloco in texto_secao_7(res, g3, g4):
        st.markdown(bloco)


def renderizar() -> None:
    st.set_page_config(page_title="LAB04", layout="wide")
    st.title("LAB04: Testes de Hipótese por Dentro")
    st.caption("t de Welch × Mann-Whitney no tempo até o merge de PRs de pallets/flask")
    st.markdown(f"[Repositório]({URL_REPOSITORIO}) · [GitHub Projects (Kanban)]({URL_PROJECTS})")
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
