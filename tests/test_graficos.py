from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import graficos as gr
from simulacao import carregar_parametros

RAIZ = Path(__file__).resolve().parent.parent


def mistura(mu):
    return {"p_rapido": 0.5, "mu_rapido": mu, "sigma_rapido": 0.1, "mu_lento": mu + 1, "sigma_lento": 0.1}


PARAMETROS = {"mistura": {"com_bot": mistura(0.0), "sem_bot": mistura(5.0)}}
DADOS = pd.DataFrame({"grupo": ["com_bot"] * 4 + ["sem_bot"] * 6,
                      "horas_ate_merge": [0.1, 1.0, 2.0, 3.0, 0.2, 1.0, 5.0, 9.0, 20.0, 40.0]})
AMOSTRAS = {
    "com_bot": {"real": np.array([0.5, 2.0]), "simulado": np.array([0.4, 3.0])},
    "sem_bot": {"real": np.array([0.01, 300.0]), "simulado": np.array([0.02, 20000.0])},
}


def test_amostras_g1_usam_a_mistura_de_cada_grupo():
    a = gr.amostras_g1(DADOS, PARAMETROS)
    assert a["com_bot"]["simulado"].max() < np.exp(2)
    assert a["sem_bot"]["simulado"].min() > np.exp(4)


def test_amostras_g1_mantem_o_real_e_sorteiam_n_simulado():
    a = gr.amostras_g1(DADOS, PARAMETROS, n_simulado=100)
    assert len(a["com_bot"]["real"]) == 4 and len(a["sem_bot"]["real"]) == 6
    assert len(a["com_bot"]["simulado"]) == len(a["sem_bot"]["simulado"]) == 100


def test_n_simulado_padrao_e_dez_mil():
    assert len(gr.amostras_g1(DADOS, PARAMETROS)["com_bot"]["simulado"]) == 10_000


def test_amostras_g1_reproduzem_com_a_mesma_semente():
    a, b = gr.amostras_g1(DADOS, PARAMETROS), gr.amostras_g1(DADOS, PARAMETROS)
    assert np.array_equal(a["sem_bot"]["simulado"], b["sem_bot"]["simulado"])


def test_bordas_cobrem_a_cauda_simulada():
    bordas = gr.bordas_log(AMOSTRAS)
    assert bordas[0] == -2 and bordas[-1] == 5 and len(bordas) == 15
    for grupo in AMOSTRAS.values():
        for horas in grupo.values():
            assert gr.percentuais(horas, bordas).sum() == pytest.approx(100)


def test_bordas_rejeitam_tempo_invalido():
    for valor in (0.0, np.nan):
        amostras = {"com_bot": {"real": np.array([valor, 1.0]), "simulado": np.array([1.0, 2.0])}}
        with pytest.raises(ValueError, match="positiv"):
            gr.bordas_log(amostras)


def test_percentuais_contam_a_faixa_certa():
    bordas = np.array([-1.0, 0.0, 1.0])
    assert gr.percentuais(np.array([0.5, 2.0, 3.0, 4.0]), bordas).tolist() == [25.0, 75.0]


def test_formatar_horas_usa_dois_algarismos_e_padrao_brasileiro():
    assert [gr.formatar_horas(h) for h in (0.001, 0.1, 1.0, 10.0, 1000.0, 100000.0)] == [
        "0,001", "0,1", "1", "10", "1.000", "100.000"]
    assert gr.formatar_horas(10 ** -2.5) == "0,0032"
    assert gr.formatar_horas(10 ** 3.5) == "3.200"


def test_rotulo_faixa_recebe_bordas_em_log():
    assert gr.rotulo_faixa(-2.5, -2.0) == "0,0032 a 0,01"
    assert gr.rotulo_faixa(3.5, 4.0) == "3.200 a 10.000"


def test_cores_cobrem_grupos_e_testes():
    assert set(gr.CORES) == {"com_bot", "sem_bot", "welch", "mann_whitney"}


def test_tabela_g1_tem_uma_linha_por_faixa():
    bordas = gr.bordas_log(AMOSTRAS)
    t = gr.tabela_g1(AMOSTRAS, bordas)
    assert len(t) == len(bordas) - 1
    assert list(t.columns) == ["Faixa (h)", "Dependabot real (%)", "Dependabot simulado (%)",
                               "Humanos real (%)", "Humanos simulado (%)"]
    assert t["Humanos simulado (%)"].sum() == pytest.approx(100)


def test_figura_g1_tem_real_e_simulado_em_cada_painel():
    f = gr.figura_g1(AMOSTRAS)
    assert [t.name for t in f.data] == ["Dependabot: real", "Dependabot: simulado (modelo)",
                                        "Humanos: real", "Humanos: simulado (modelo)"]
    assert [t.xaxis for t in f.data] == ["x", "x", "x2", "x2"]
    assert all(sum(t.y) == pytest.approx(100) for t in f.data)


def test_figura_g1_tem_titulo_eixos_e_legenda():
    f = gr.figura_g1(AMOSTRAS)
    assert "G1" in f.layout.title.text
    assert "horas" in f.layout.xaxis.title.text and "escala log" in f.layout.xaxis.title.text
    assert "%" in f.layout.yaxis.title.text
    assert f.layout.showlegend is True


def test_figura_g1_usa_a_cor_de_cada_grupo():
    f = gr.figura_g1(AMOSTRAS)
    assert f.data[0].marker.color == gr.CORES["com_bot"]
    assert f.data[1].marker.line.color == gr.CORES["com_bot"]
    assert f.data[2].marker.color == gr.CORES["sem_bot"]
    assert f.data[3].marker.line.color == gr.CORES["sem_bot"]


def test_figura_g1_compartilha_as_escalas_entre_paineis():
    f = gr.figura_g1(AMOSTRAS)
    assert f.layout.xaxis.range == f.layout.xaxis2.range
    assert f.layout.yaxis2.matches == "y"


def test_figura_g1_marca_rotulos_em_horas():
    f = gr.figura_g1(AMOSTRAS)
    assert "1" in f.layout.xaxis.ticktext and "100" in f.layout.xaxis.ticktext


def test_figura_g1_mantem_rotulos_na_horizontal_sem_colisao():
    eixo = gr.figura_g1(AMOSTRAS).layout.xaxis
    assert eixo.tickangle == 0
    assert eixo.ticktext[list(eixo.tickvals).index(3)] == ""
    assert eixo.ticktext[list(eixo.tickvals).index(4)] == "10.000"


def test_figura_g1_com_dados_do_projeto():
    dados = pd.read_csv(RAIZ / "data/dados_reais.csv")
    amostras = gr.amostras_g1(dados, carregar_parametros())
    f = gr.figura_g1(amostras)
    assert "n=60 reais" in f.layout.annotations[0].text and "n=320 reais" in f.layout.annotations[1].text
    assert (amostras["sem_bot"]["simulado"] > 0).all()


def test_figura_g1_rotula_o_limiar_so_no_primeiro_painel():
    textos = [a.text for a in gr.figura_g1(AMOSTRAS).layout.annotations]
    assert textos.count("1 h") == 1
    assert all(textos)


def test_figura_g1_nao_desenha_contorno_em_faixa_vazia():
    simulado = gr.figura_g1(AMOSTRAS).data[1]
    larguras = dict(zip(simulado.x, simulado.marker.line.width))
    assert all((larguras[x] == 0) == (y == 0) for x, y in zip(simulado.x, simulado.y))


def test_figura_g1_separa_os_rotulos_dos_paineis():
    f = gr.figura_g1(AMOSTRAS)
    assert f.layout.xaxis2.domain[0] - f.layout.xaxis.domain[1] >= 0.08


def test_amostras_g1_rejeitam_grupo_sem_observacoes():
    with pytest.raises(ValueError, match="sem_bot"):
        gr.amostras_g1(DADOS[DADOS["grupo"] == "com_bot"], PARAMETROS)


def test_amostras_g1_rejeitam_tempo_nao_numerico():
    dados = DADOS.astype({"horas_ate_merge": object})
    dados.loc[0, "horas_ate_merge"] = "abc"
    with pytest.raises(ValueError, match="positiv"):
        gr.amostras_g1(dados, PARAMETROS)


def test_amostras_g1_rejeitam_coluna_ausente():
    with pytest.raises(ValueError, match="horas_ate_merge"):
        gr.amostras_g1(DADOS.drop(columns="horas_ate_merge"), PARAMETROS)


PARAMETROS_G2 = {"n": {"com_bot": 20, "sem_bot": 40}, "mistura": {"h0": mistura(1.0)}}


def test_estatisticas_h0_reproduzem_e_tem_um_valor_por_repeticao():
    a = gr.estatisticas_h0(PARAMETROS_G2, n_repeticoes=50)
    b = gr.estatisticas_h0(PARAMETROS_G2, n_repeticoes=50)
    assert set(a) == {"welch", "mann_whitney"}
    assert all(len(v) == 50 for v in a.values())
    assert all(np.array_equal(a[k], b[k]) for k in a)


def test_u_padronizado_sob_h0_tem_media_zero_e_desvio_um():
    z = gr.estatisticas_h0(PARAMETROS_G2, n_repeticoes=2000)["mann_whitney"]
    assert abs(z.mean()) < 0.1 and abs(z.std() - 1) < 0.1


def test_exemplo_g2_bate_com_aplicar_testes():
    exemplo = gr.exemplo_g2(carregar_parametros())
    assert 0 < exemplo["welch"]["p_valor"] < 1 and exemplo["welch"]["gl"] > 0
    assert 0 < exemplo["mann_whitney"]["p_valor"] < 1


def test_figura_g2_tem_regiao_pvalor_titulo_eixos_e_legenda():
    parametros = carregar_parametros()
    fig = gr.figura_g2(gr.estatisticas_h0(parametros, n_repeticoes=200), gr.exemplo_g2(parametros))
    # Cada região tem duas séries por painel (uma por cauda); a legenda mostra uma só.
    regioes = [t for t in fig.data if t.name.startswith("Região de rejeição")]
    areas_p = [t for t in fig.data if t.name == "Área do p-valor do exemplo"]
    assert len(regioes) == len(areas_p) == 4
    assert sum(bool(t.showlegend) for t in regioes) == sum(bool(t.showlegend) for t in areas_p) == 1
    assert sum(t.type == "histogram" for t in fig.data) == 2
    assert fig.layout.title.text.startswith("G2") and fig.layout.showlegend
    assert all(fig.layout[e].title.text for e in ("xaxis", "xaxis2", "yaxis", "yaxis2"))
    for chave in gr.TESTES_G2:
        nome = gr.TESTES_G2[chave]
        histograma = next(t for t in fig.data if t.type == "histogram" and t.name.startswith(nome))
        curva = next(t for t in fig.data if t.name == f"{nome}: curva teórica")
        assert histograma.marker.line.color == curva.line.color == gr.CORES[chave]


def poder_g4(valores):
    linhas = []
    for d, (welch, mw) in valores.items():
        for teste, p in (("t de Welch", welch), ("Mann-Whitney U", mw)):
            linhas.append({"d": d, "teste": teste, "proporcao_rejeicoes": p,
                           "ic95_inferior": max(0, p - 0.01), "ic95_superior": min(1, p + 0.01)})
    return pd.DataFrame(linhas)


Q2_G4 = poder_g4({0.0: (0.11, 0.05), 0.5: (0.2, 0.9), 1.0: (0.5, 1.0)})
Q3_G4 = pd.concat([
    poder_g4({0.0: (0.01, 0.04), 0.5: (0.02, 0.2), 1.0: (0.03, 0.5)}).assign(situacao="amostras_pequenas"),
    poder_g4({0.0: (0.08, 0.05), 0.5: (0.02, 0.9), 1.0: (0.09, 1.0)}).assign(situacao="outliers_extremos"),
    Q2_G4.assign(situacao="normal"),
], ignore_index=True)


def test_dados_g4_junta_normal_da_q2_e_violacoes_da_q3():
    dados = gr.dados_g4(Q2_G4, Q3_G4)
    assert set(dados["situacao"]) == set(gr.PAINEIS_G4)
    assert len(dados) == 3 * 3 * 2


def test_dados_g4_rejeita_csv_incompleto():
    with pytest.raises(ValueError, match="colunas"):
        gr.dados_g4(Q2_G4.drop(columns="ic95_inferior"), Q3_G4)
    with pytest.raises(ValueError, match="situações"):
        gr.dados_g4(Q2_G4, Q3_G4[Q3_G4["situacao"] == "normal"])


def test_figura_g4_tem_titulo_eixos_legenda_e_linha_de_alfa():
    fig = gr.figura_g4(gr.dados_g4(Q2_G4, Q3_G4))
    assert fig.layout.title.text.startswith("G4") and fig.layout.showlegend
    assert all(fig.layout[e].title.text for e in ("xaxis", "xaxis2", "xaxis3", "yaxis"))
    assert tuple(fig.layout.yaxis.range) == (0, 1)
    assert len([s for s in fig.layout.shapes if s.y0 == 0.05]) == 3
    assert len(fig.data) == 3 * 2 + 1
    assert sum(bool(t.showlegend) for t in fig.data) == 3
    assert not fig.layout.annotations or all(a.text != "new text" for a in fig.layout.annotations)
    assert all(a.text in gr.PAINEIS_G4.values() for a in fig.layout.annotations)


def test_figura_g4_usa_a_cor_de_cada_teste_em_todos_os_paineis():
    fig = gr.figura_g4(gr.dados_g4(Q2_G4, Q3_G4))
    for t in fig.data:
        if t.name in gr.TESTES_G4:
            assert t.line.color == gr.CORES[gr.TESTES_G4[t.name]]


def test_tabela_g4_tem_uma_linha_por_situacao_e_d():
    tabela = gr.tabela_g4(gr.dados_g4(Q2_G4, Q3_G4))
    assert len(tabela) == 3 * 3
    assert {"t de Welch (%)", "Mann-Whitney U (%)"} <= set(tabela.columns)
