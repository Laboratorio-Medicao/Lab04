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
    assert "1" in f.layout.xaxis.ticktext and "1.000" in f.layout.xaxis.ticktext


def test_figura_g1_com_dados_do_projeto():
    dados = pd.read_csv(RAIZ / "data/dados_reais.csv")
    amostras = gr.amostras_g1(dados, carregar_parametros())
    f = gr.figura_g1(amostras)
    assert "n=60 reais" in f.layout.annotations[0].text and "n=320 reais" in f.layout.annotations[1].text
    assert (amostras["sem_bot"]["simulado"] > 0).all()
