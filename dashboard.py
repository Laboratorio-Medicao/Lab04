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
# Link público do dashboard (Streamlit Community Cloud). Preencher após a publicação.
URL_DASHBOARD = ""
sys.path.insert(0, str(RAIZ / "src"))

from graficos import (  # noqa: E402
    PAINEIS_G4, amostras_g1, bordas_log, dados_g3, dados_g4, estatisticas_h0, exemplo_g2,
    figura_g1, figura_g2, figura_g3, figura_g4, tabela_g1, tabela_g3, tabela_g4,
)
from graficos import resultado_g5, tabela_g5  # noqa: E402
from graficos import (  # noqa: E402
    ROTULOS_SITUACAO, fracao_na_regiao, tabela_alfa, tabela_efeito_com_sinal, tabela_sensibilidade,
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


def texto_g2(exemplo: dict, fracoes: dict | None = None) -> str:
    def v(x: float) -> str:
        return f"{x:.2f}".replace(".", ",")

    regiao = "onde a estatística seria rara sob H₀ (5% no total)"
    if fracoes:
        pct = lambda x: f"{x:.1%}".replace(".", ",")  # noqa: E731
        regiao = (
            "onde a estatística seria rara sob H₀ (5% na curva teórica), mas nas simulações "
            f"{pct(fracoes['mann_whitney'])} dos Z do Mann-Whitney (o U padronizado) e {pct(fracoes['welch'])} dos t de Welch "
            "caem nela, porque a assimetria dos dados deixa o t mais disperso que a curva teórica, "
            "o mesmo erro tipo I inflado do G3"
        )

    w, mw = exemplo["welch"], exemplo["mann_whitney"]
    rejeita = [t for t in (w, mw) if t["p_valor"] < 0.05]
    conclusao = ("nenhum teste cai na região de rejeição, então H₀ não é rejeitada." if not rejeita
                 else "ao menos um teste cai na região de rejeição, o que seria um falso positivo.")
    return (
        "O t de Welch compara as médias dos dois grupos e o Mann-Whitney compara se um PR de um grupo "
        "tende a demorar mais que o do outro. Como o teste é bicaudal, a região de rejeição (cinza) fica "
        f"nas duas caudas, {regiao}. "
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
        f"O Mann-Whitney tem mais poder que o t de Welch {vantagem}: no cenário base, com "
        f"d = {d_max:g}, ele rejeita {p(pct('normal', 'Mann-Whitney U', d_max))} das vezes e o Welch, "
        f"{p(pct('normal', 't de Welch', d_max))}. "
        "A violação de pressuposto derruba sobretudo o Welch: com amostras pequenas o Mann-Whitney "
        f"chega a {p(pct('amostras_pequenas', 'Mann-Whitney U', d_max))} e o Welch, a "
        f"{p(pct('amostras_pequenas', 't de Welch', d_max))}, e com outliers extremos o Welch fica em "
        f"{p(pct('outliers_extremos', 't de Welch', d_max))}. "
        "O valor em d = 0 não é poder, e sim o erro tipo I, que o Welch infla além de 5% "
        + " e ".join(nome for s, nome in (("normal", "no cenário base"), ("amostras_pequenas", "com amostras pequenas"),
                                           ("outliers_extremos", "com outliers extremos"))
                     if pct(s, "t de Welch", 0.0) > 0.06) + "."
    )


def _pct(x: float, casas: int = 1) -> str:
    return f"{x:.{casas}%}".replace(".", ",")


def _prop(df: pd.DataFrame, situacao: str, teste: str, d: float, coluna: str = "proporcao_alfa05") -> float:
    filtro = (df["situacao"] == situacao) & (df["teste"] == teste) & (df["d"] == d)
    return float(df.loc[filtro, coluna].iloc[0])


def carregar_complementar() -> pd.DataFrame:
    return pd.read_csv(RAIZ / "data" / "simulacao_complementar.csv")


def texto_pvalor_nao_significa() -> str:
    return (
        "- **Não é a probabilidade de H₀ ser verdadeira.** O p-valor já supõe H₀ verdadeira e mede quão rara "
        "seria uma estatística tão extrema quanto a observada.\n"
        "- **Não é a chance de a conclusão estar certa**, nem a probabilidade de repetir o resultado.\n"
        "- **Não mede o tamanho do efeito.** Com amostras grandes, uma diferença minúscula dá p pequeno; por isso "
        "a seção 6 traz também o Cohen's d e o r.\n"
        "- **Não garante relevância prática**, e um p-valor alto não prova que não há efeito: pode ser só falta de poder."
    )


def texto_situacoes(parametros: dict) -> str:
    d = parametros["descritivas"]
    return (
        "**Como ler as três situações.** O **cenário base já é muito assimétrico**: os dados reais têm assimetria "
        f"de {_num(d['com_bot']['assimetria'], 1)} (Dependabot) e {_num(d['sem_bot']['assimetria'], 1)} (humanos), "
        "e a simulação reproduz essa forma. Por isso o G3 e o G4 **não** comparam dados normais com dados não normais: "
        "comparam um cenário que já é difícil para o t de Welch com duas situações que o pioram.\n\n"
        "- **Amostras pequenas (n = 10 por grupo):** com apenas 10 observações por grupo, a aproximação normal "
        "usada pelo teste fica menos confiável, e poucos valores grandes decidem a média e o erro-padrão.\n"
        "- **Outliers extremos (desvio de ln T × 1,5):** valores muito elevados influenciam fortemente a média e "
        "a variância, então o t oscila muito de uma amostra para outra. O Mann-Whitney usa só a ordem dos valores "
        "e quase não sente isso."
    )


def texto_erros_tipo_i_ii() -> str:
    return (
        "- **Erro tipo I:** concluir que os PRs do Dependabot são mergeados mais rápido (ou mais devagar) que os "
        "de humanos quando, na realidade, não existe diferença. É o que o G3 mede, com H₀ verdadeira.\n"
        "- **Erro tipo II:** não identificar uma diferença que existe entre os grupos. É o complemento do poder do "
        "G4: erro tipo II = 1 − poder.\n"
        "- **Qual é mais grave:** neste cenário, o tipo I. Um falso positivo levaria a mudar a política de revisão "
        "ou de automação por uma diferença que não existe, enquanto o tipo II só mantém o processo atual. Por isso "
        "o erro tipo I inflado do t de Welch pesa na recomendação."
    )


def texto_alfa(comp: pd.DataFrame) -> str:
    situacoes = list(ROTULOS_SITUACAO)
    a01 = lambda s, t, d: _prop(comp, s, t, d, "proporcao_alfa01")  # noqa: E731
    a05 = lambda s, t, d: _prop(comp, s, t, d)  # noqa: E731
    mw = [a01(s, "Mann-Whitney U", 0.0) for s in situacoes]
    positivos = sorted(float(d) for d in comp["d"].unique() if d > 0)
    d_ref = 0.5
    ordem = all(a01(s, "Mann-Whitney U", d) >= a01(s, "t de Welch", d) for s in situacoes for d in positivos)
    return (
        f"Com α = 1%, a linha de referência do G3 desce para 1%. O Mann-Whitney fica perto dela nas três situações "
        f"({_pct(min(mw))} a {_pct(max(mw))}), e o Welch continua fora: {_pct(a01('normal', 't de Welch', 0.0))} no "
        f"cenário base, {_pct(a01('amostras_pequenas', 't de Welch', 0.0))} com amostras pequenas e "
        f"{_pct(a01('outliers_extremos', 't de Welch', 0.0))} com outliers extremos. "
        "No G4 todas as curvas descem, porque o critério fica mais rígido e exige efeitos maiores para o mesmo poder: "
        f"no cenário base, em d = {_num(d_ref, 1)}, o Mann-Whitney passa de {_pct(a05('normal', 'Mann-Whitney U', d_ref))} "
        f"para {_pct(a01('normal', 'Mann-Whitney U', d_ref))} e o Welch de {_pct(a05('normal', 't de Welch', d_ref))} "
        f"para {_pct(a01('normal', 't de Welch', d_ref))}. "
        + ("A ordem entre os testes não muda para nenhum d > 0." if ordem
           else "A ordem entre os testes muda em alguns pontos; veja a tabela.")
    )


def texto_queda_welch(comp: pd.DataFrame) -> str:
    tot = lambda d: _prop(comp, "normal", "t de Welch", d)  # noqa: E731
    rapido = lambda d: _prop(comp, "normal", "t de Welch", d, "proporcao_alfa05_bot_mais_rapido")  # noqa: E731
    positivos = sorted(float(d) for d in comp["d"].unique() if d > 0)
    d_vale = min(positivos, key=tot)
    proximos = [d for d in positivos if d > d_vale][:2]
    cresce = " e ".join(f"{_pct(tot(d) - rapido(d))} em d = {_num(d, 1)}" for d in proximos)
    return (
        f"**Por que o poder do Welch cai até d = {_num(d_vale, 1)}?** Sem efeito, o Welch rejeita {_pct(tot(0.0))} das "
        f"vezes no cenário base, e em {_pct(rapido(0.0))} das repetições a rejeição vem com t negativo (o Dependabot parece mais "
        "rápido), porque, com dados assimétricos, a estatística t também é assimétrica. Um efeito positivo (Dependabot "
        "mais lento) puxa o t de volta para o centro e tira essas rejeições "
        f"({_pct(rapido(positivos[0]))} em d = {_num(positivos[0], 1)}; {_pct(rapido(d_vale))} em d = {_num(d_vale, 1)}) "
        f"antes que a cauda positiva cresça (rejeições com t positivo: {cresce}). "
        "Parte do \"poder\" do Welch em efeitos pequenos é, portanto, erro tipo I, e não detecção do efeito."
    )


def texto_efeito_negativo(comp: pd.DataFrame, parametros: dict) -> str:
    negativos = sorted(float(d) for d in comp["d"].unique() if d < 0)
    w = lambda s, d: _prop(comp, s, "t de Welch", d)  # noqa: E731
    m = lambda s, d: _prop(comp, s, "Mann-Whitney U", d)  # noqa: E731
    inicio = (
        "O G4 mostra efeitos positivos (Dependabot mais lento), como a Q2 e a Q3 pedem a partir de zero, mas nos "
        f"dados reais o Dependabot é mais rápido (d = {_num(parametros['delta_padronizado'], 2)} na escala da simulação). "
    )
    ganha = [d for d in negativos if w("normal", d) > m("normal", d)]
    if not ganha:
        return inicio + ("Com efeitos negativos o Mann-Whitney também tem mais poder que o Welch em todos os d "
                         "simulados no cenário base.")
    d_ini = ganha[-1]
    d_volta = next(d for d in reversed(negativos) if d < d_ini)
    d_ext = negativos[0]
    return (
        inicio
        + f"Nesse sentido a vantagem muda de lado em efeitos muito pequenos: no cenário base, em d = {_num(d_ini, 1)}, "
        f"o Welch rejeita {_pct(w('normal', d_ini))} e o Mann-Whitney {_pct(m('normal', d_ini))}. "
        f"Isso vem em boa parte do erro tipo I do Welch, que já rejeita {_pct(_prop(comp, 'normal', 't de Welch', 0.0, 'proporcao_alfa05_bot_mais_rapido'))} "
        "sem efeito algum nesse sentido. "
        f"A partir de d = {_num(d_volta, 1)} o Mann-Whitney volta à frente ({_pct(m('normal', d_volta))} contra "
        f"{_pct(w('normal', d_volta))}) e chega a {_pct(m('normal', d_ext))} contra {_pct(w('normal', d_ext))} em "
        f"d = {_num(d_ext, 1)}."
    )


def texto_limitacao_poder(sens: pd.DataFrame) -> str:
    """Duas frases para a limitação da seção 7: cauda simulada e sentido do efeito."""
    tabela = sens.pivot_table(index="d", columns=["teste", "variante"], values="proporcao_rejeicoes")
    welch = tabela["t de Welch"]
    d_max = max(float(d) for d in tabela.index)
    return (
        "A cauda simulada é mais pesada que a real: truncando os tempos no máximo observado, o poder do Welch em "
        f"d = {_num(d_max, 1)} passa de {_pct(welch['sem truncamento'][d_max])} para "
        f"{_pct(welch['truncada no máximo real'][d_max])} (seção 5), então o tamanho da vantagem de poder do "
        "Mann-Whitney depende da cauda assumida. Essa vantagem vale para efeitos positivos; com efeito "
        "negativo, o sentido observado nos dados reais, o Welch tem mais poder em efeitos muito pequenos, em parte "
        "por causa do erro tipo I."
    )


def texto_sensibilidade(sens: pd.DataFrame, teto: float) -> str:
    tabela = sens.pivot_table(index="d", columns=["teste", "variante"], values="proporcao_rejeicoes")
    sem, com = "sem truncamento", "truncada no máximo real"
    w_sem, w_com = tabela[("t de Welch", sem)], tabela[("t de Welch", com)]
    m_com = tabela[("Mann-Whitney U", com)]
    ds = [float(d) for d in tabela.index if d > 0]
    d_max = max(ds)
    a_frente = all(m_com[d] > w_com[d] for d in ds)
    return (
        "A cauda simulada é mais pesada que a real: a média teórica da mistura é cerca de 200 h, contra 132 h nos "
        f"dados combinados (veja `docs/cenario.md`). Ao truncar os tempos em {_num(teto, 0)} h, o máximo observado, "
        f"o erro tipo I do Welch vai de {_pct(w_sem[0.0])} para {_pct(w_com[0.0])} e o poder dele em d = {_num(d_max, 1)} "
        f"de {_pct(w_sem[d_max])} para {_pct(w_com[d_max])}, enquanto o Mann-Whitney fica em {_pct(m_com[d_max])}. "
        + ("O Mann-Whitney continua à frente em todos os d, mas a distância depende de quão pesada é a cauda. "
           if a_frente else "A ordem entre os testes muda em alguns d; veja a tabela. ")
        + "Isso é uma limitação: o tamanho da vantagem de poder do Mann-Whitney depende da cauda assumida na simulação."
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
    st.write(texto_g2(exemplo, fracao_na_regiao(estatisticas, exemplo)))
    with st.expander("O que o p-valor não significa"):
        st.markdown(texto_pvalor_nao_significa())


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
        f"O t de Welch foi o que se desviou: {classe(w['H₀ verdadeira'])} no cenário base ({p(w['H₀ verdadeira'])}), "
        f"{classe(w['amostras_pequenas'])} com amostras pequenas ({p(w['amostras_pequenas'])}) e "
        f"{classe(w['outliers_extremos'])} com outliers extremos ({p(w['outliers_extremos'])}). "
        "O excesso de rejeições do Welch vem da forte assimetria dos dados, que prejudica a aproximação normal da "
        "estatística t, e o cenário base já tem essa assimetria. "
        "Com n = 10 o desvio vai para o outro lado: poucos valores grandes inflam o erro-padrão junto com a "
        "média, o t fica pequeno e o Welch quase nunca rejeita, abaixo de 5%."
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
    st.markdown(texto_situacoes(carregar_parametros()))
    with st.expander("Ver dados do G3"):
        st.dataframe(tabela_g3(dados).style.format(precision=1, decimal=","), hide_index=True)
    with st.expander("Erro tipo I e erro tipo II no nosso cenário"):
        st.markdown(texto_erros_tipo_i_ii())
    try:
        comp = carregar_complementar()
        tabela = tabela_alfa(comp)
        explicacao = texto_alfa(comp)
    except (ValueError, OSError, KeyError) as erro:
        st.error(f"Não foi possível montar a análise com α = 1%: {erro}")
        return
    with st.expander("E se α fosse 1% em vez de 5%?"):
        st.write(explicacao)
        st.dataframe(tabela.style.format(precision=1, decimal=","), hide_index=True)


def _poder_em_d(dados: pd.DataFrame, d_val: float) -> dict[str, float]:
    """Retorna proporção de rejeições no cenário base para cada teste no d_val mais próximo."""
    ds_disponiveis = sorted(dados["d"].unique())
    d_mais_proximo = min(ds_disponiveis, key=lambda x: abs(x - d_val))
    base = dados[(dados["situacao"] == "normal") & (dados["d"] == d_mais_proximo)]
    resultado = {}
    for nome_teste in base["teste"].unique():
        linha = base[base["teste"] == nome_teste]
        if not linha.empty:
            resultado[nome_teste] = float(linha["proporcao_rejeicoes"].iloc[0])
    return resultado


def secao_5() -> None:
    st.header("5. Poder")
    try:
        dados = dados_g4(pd.read_csv(RAIZ / "data" / "simulacao_q2_poder.csv"),
                         pd.read_csv(RAIZ / "data" / "simulacao_q3_poder.csv"))
    except (ValueError, OSError) as erro:
        st.error(f"Não foi possível montar o G4 com os CSVs de poder da Q2 e da Q3: {erro}")
        return

    ds_disponiveis = sorted(float(d) for d in dados["d"].unique())
    d_inicial = ds_disponiveis[len(ds_disponiveis) // 2]
    d_selecionado = st.select_slider(
        "Tamanho do efeito d — arraste para ver o poder em cada ponto da curva",
        options=ds_disponiveis,
        value=d_inicial,
        format_func=lambda x: f"d = {x:.1f}",
    )

    poder_atual = _poder_em_d(dados, d_selecionado)
    if d_selecionado > 0:
        col1, col2 = st.columns(2)
        welch_val = poder_atual.get("t de Welch", 0.0)
        mw_val = poder_atual.get("Mann-Whitney U", 0.0)
        col1.metric("Mann-Whitney U — poder no cenário base", f"{mw_val:.1%}".replace(".", ","))
        col2.metric("t de Welch — poder no cenário base", f"{welch_val:.1%}".replace(".", ","),
                    delta=f"{welch_val - mw_val:.1%}".replace(".", ","),
                    delta_color="inverse")

    fig = figura_g4(dados)
    fig.add_vline(
        x=d_selecionado, line_dash="dash", line_color="#a0b4ff", line_width=1.5,
    )
    st.plotly_chart(fig, theme=None, width="stretch")
    st.caption("Cada ponto tem 10.000 repetições por teste, com semente fixa 42. A linha pontilhada é α = 5%.")
    st.write(texto_g4(dados))
    with st.expander("Ver dados do G4"):
        st.dataframe(tabela_g4(dados).style.format(precision=1, decimal=","), hide_index=True)
    try:
        comp = carregar_complementar()
        sens = pd.read_csv(RAIZ / "data" / "simulacao_q2_sensibilidade.csv")
        teto = float(pd.read_csv(RAIZ / "data" / "dados_reais.csv")["horas_ate_merge"].max())
        tabela_comp, tabela_sens = tabela_efeito_com_sinal(comp), tabela_sensibilidade(sens)
        explicacoes = (texto_queda_welch(comp), texto_efeito_negativo(comp, carregar_parametros()),
                       texto_sensibilidade(sens, teto))
    except (ValueError, OSError, KeyError) as erro:
        st.error(f"Não foi possível montar as análises complementares de poder: {erro}")
        return
    st.markdown(explicacoes[0])
    st.markdown(explicacoes[1])
    with st.expander("Ver o poder com efeitos negativos (Dependabot mais rápido)"):
        st.dataframe(tabela_comp.style.format(precision=1, decimal=","), hide_index=True)
    with st.expander("Sensibilidade: e se a cauda simulada fosse mais leve?"):
        st.write(explicacoes[2])
        st.dataframe(tabela_sens.style.format(precision=1, decimal=","), hide_index=True)


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


def texto_secao_7(res, g3: pd.DataFrame, g4: pd.DataFrame, extra: str = "") -> list[str]:
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
        f"{classe(w_normal)} no cenário base ({p(w_normal)}), {classe(w_outliers)} com outliers extremos "
        f"({p(w_outliers)}) e {classe(w_pequenas)} com amostras pequenas ({p(w_pequenas)}). "
        f"Com d = {_num(d_ref, 1)} no cenário base, o poder foi de {p(poder['Mann-Whitney U'])} no Mann-Whitney "
        f"e de {p(poder['t de Welch'])} no t de Welch, cujo poder nem cresce sempre com o efeito: no "
        f"cenário base cai de {p(welch_poder('normal', d_min))} em d = {_num(d_min, 1)} para "
        f"{p(welch_poder('normal', d_seg))} em d = {_num(d_seg, 1)}, e com outliers extremos desce a "
        f"{p(min_out)} em d = {_num(d_min_out, 1)} e só chega a {p(welch_poder('outliers_extremos', d_max))} em "
        f"d = {_num(d_max, 1)}. "
        f"Nos dados reais, o {NOMES[escolhido]} deu {p_igual(real[escolhido].p_valor)} e o {NOMES[outro]}, "
        f"{p_igual(real[outro].p_valor)}.",
        f"**Recomendação.** Recomendamos o {NOMES[escolhido]} para comparar o tempo até o merge de PRs do "
        "Dependabot e de humanos, porque nas situações simuladas ele manteve o erro tipo I mais perto de 5% e "
        f"teve mais poder nos efeitos positivos simulados, enquanto o {NOMES[outro]} se desviou de 5% para os dois lados e teve poder baixo e instável "
        f"nas situações simuladas. Por ele, {evidencia} a α = 5% de que um grupo tende a ser mergeado mais rápido que "
        "o outro.",
        "**Quando mudaria.** Se a pergunta fosse sobre a média, por exemplo o tempo total de espera somado de "
        "todos os PRs, o t de Welch seria o teste adequado, porque o Mann-Whitney não compara médias. "
        "O Welch também ficaria mais atraente com amostras grandes e pouco assimétricas, em que a aproximação "
        "normal da estatística t funciona bem.",
        "**Limitação.** Os dados vêm de um único repositório (pallets/flask), e a simulação usa uma mistura de "
        "lognormais estimada desses mesmos dados, então os resultados podem não valer para outros projetos. "
        "Além disso, o Mann-Whitney testa se um grupo tende a ter valores maiores que o outro, e não a "
        "diferença de médias, o que limita o que se conclui sobre o tempo médio." + extra,
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
    extra = ""
    try:
        sens = pd.read_csv(RAIZ / "data" / "simulacao_q2_sensibilidade.csv")
        carregar_complementar()
        extra = " " + texto_limitacao_poder(sens)
    except (ValueError, OSError, KeyError):
        pass
    for bloco in texto_secao_7(res, g3, g4, extra):
        st.markdown(bloco)


def renderizar() -> None:
    st.set_page_config(page_title="LAB04", layout="wide")
    _links = [("Repositório", URL_REPOSITORIO), ("GitHub Projects", URL_PROJECTS)]
    if URL_DASHBOARD:
        _links.insert(0, ("Dashboard", URL_DASHBOARD))
    _links_html = " &nbsp;·&nbsp; ".join(f'<a href="{u}" target="_blank">{t}</a>' for t, u in _links)
    st.markdown(
        f"<h3 style='margin:0 0 4px 0'>LAB04 &nbsp;·&nbsp; "
        f"t de Welch × Mann-Whitney &nbsp;·&nbsp; pallets/flask"
        f"&emsp;<span style='font-size:0.6em;font-weight:400'>{_links_html}</span></h3>",
        unsafe_allow_html=True,
    )
    st.divider()

    aba_visual, aba_relatorio = st.tabs(["Visão geral", "Relatório"])

    with aba_visual:
        # --- G1: legenda à direita, automargin nos eixos ---
        try:
            parametros = carregar_parametros()
            amostras = amostras_g1(pd.read_csv(RAIZ / "data" / "dados_reais.csv"), parametros)
            fig = figura_g1(amostras)
            fig.update_layout(
                height=400,
                margin={"t": 55, "b": 55, "l": 60, "r": 210},
                legend={"orientation": "v", "x": 1.01, "xanchor": "left",
                        "y": 0.5, "yanchor": "middle"},
            )
            fig.update_xaxes(automargin=True)
            fig.update_yaxes(automargin=True)
            st.plotly_chart(fig, theme=None, width="stretch")
        except (ValueError, OSError) as erro:
            st.error(f"G1: {erro}")

        # --- G3 | métricas G5 ---
        c_g3, c_metricas = st.columns([3, 2])
        with c_g3:
            try:
                g3 = dados_g3(pd.read_csv(RAIZ / "data" / "simulacao_q1_resumo.csv"),
                              pd.read_csv(RAIZ / "data" / "simulacao_q3_comparacao.csv"))
                fig = figura_g3(g3)
                _rotulos_g3 = {
                    "Cenário base, já assimétrico (Q1)": "Cenário base",
                    "Violação: amostras pequenas (Q3)": "Amostras pequenas",
                    "Violação: outliers extremos (Q3)": "Outliers extremos",
                }
                fig.update_xaxes(
                    ticktext=list(_rotulos_g3.values()),
                    tickvals=list(_rotulos_g3.keys()),
                    tickangle=0,
                    title_text="",
                    automargin=True,
                )
                fig.update_yaxes(title_text="Rejeições sob H₀", automargin=True)
                fig.update_layout(
                    height=380,
                    margin={"t": 55, "b": 100, "l": 60, "r": 20},
                    legend={"orientation": "h", "y": -0.22},
                )
                st.plotly_chart(fig, theme=None, width="stretch")
            except (ValueError, OSError) as erro:
                st.error(f"G3: {erro}")
        with c_metricas:
            try:
                res = resultado_g5(pd.read_csv(RAIZ / "data" / "dados_reais.csv"))
                st.markdown("**Dados reais** · pallets/flask")
                mc1, mc2 = st.columns(2)
                mc1.metric("t de Welch", f"t = {_num(res.welch.estatistica)}",
                           delta=f"p {formatar_p(res.welch.p_valor)}", delta_color="off")
                mc2.metric("Mann-Whitney U", f"U = {_num(res.mann_whitney.estatistica, 0)}",
                           delta=f"p = {formatar_p(res.mann_whitney.p_valor)}", delta_color="off")
                mc1.metric("Cohen's d", _num(res.welch.tamanho_efeito),
                           delta=_magnitude(res.welch.tamanho_efeito, (0.2, 0.5, 0.8)), delta_color="off")
                mc2.metric("r (Mann-Whitney)", _num(res.mann_whitney.tamanho_efeito, 3),
                           delta=_magnitude(res.mann_whitney.tamanho_efeito, (0.1, 0.3, 0.5)), delta_color="off")
            except (ValueError, OSError) as erro:
                st.error(f"G5: {erro}")

        # --- G2: remove subtítulo longo dos painéis, legenda embaixo ---
        try:
            estatisticas, exemplo = dados_g2()
            fig = figura_g2(estatisticas, exemplo)
            for ann in fig.layout.annotations:
                if "<br><sup>" in ann.text:
                    ann.text = ann.text.split("<br><sup>")[0]
            fig.update_xaxes(automargin=True)
            fig.update_layout(
                height=460,
                margin={"t": 80, "b": 130, "l": 60, "r": 20},
                legend={"orientation": "h", "y": -0.26},
            )
            st.plotly_chart(fig, theme=None, width="stretch")
        except Exception as erro:
            st.error(f"G2: {erro}")

        # --- G4: títulos curtos, eixo X só no painel 1, legenda embaixo ---
        try:
            dados_poder = dados_g4(pd.read_csv(RAIZ / "data" / "simulacao_q2_poder.csv"),
                                   pd.read_csv(RAIZ / "data" / "simulacao_q3_poder.csv"))
            ds = sorted(float(d) for d in dados_poder["d"].unique())
            col_slider, _ = st.columns([2, 5])
            d_sel = col_slider.select_slider(
                "d (tamanho do efeito)",
                options=ds, value=ds[len(ds) // 2],
                format_func=lambda x: f"d = {x:.1f}",
            )
            fig = figura_g4(dados_poder)
            _titulos_g4 = {
                "Cenário base, já assimétrico (Q2)": "Cenário base (Q2)",
                "Violação: amostras pequenas (Q3)": "Amostras pequenas (Q3)",
                "Violação: outliers extremos (Q3)": "Outliers extremos (Q3)",
            }
            for ann in fig.layout.annotations:
                ann.text = _titulos_g4.get(ann.text, ann.text)
            fig.update_xaxes(title_text="", row=1, col=2)
            fig.update_xaxes(title_text="", row=1, col=3)
            fig.update_xaxes(automargin=True)
            fig.update_yaxes(automargin=True)
            fig.update_layout(
                height=380,
                margin={"t": 70, "b": 90, "l": 60, "r": 20},
                legend={"orientation": "h", "y": -0.22},
            )
            fig.add_vline(x=d_sel, line_dash="dash", line_color="#a0b4ff", line_width=1.5)
            st.plotly_chart(fig, theme=None, width="stretch")
        except (ValueError, OSError) as erro:
            st.error(f"G4: {erro}")

    with aba_relatorio:
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
