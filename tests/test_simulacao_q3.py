import pandas as pd
import pytest

import simulacao as sim
import simulacao_q1 as q1
import simulacao_q3 as q3

PARAMETROS = sim.carregar_parametros()
D = (0.0, 0.5)


def rodar(situacao, repeticoes=20):
    return q3.simular_situacao(PARAMETROS, situacao, D, repeticoes, sim.criar_rng())


def test_mesma_semente_gera_o_mesmo_resultado():
    pd.testing.assert_frame_equal(rodar("amostras_pequenas"), rodar("amostras_pequenas"))


def test_formato_longo_tem_um_registro_por_d_e_teste():
    df = rodar("outliers_extremos")
    assert len(df) == len(D) * 2
    assert set(df["teste"]) == {"t de Welch", "Mann-Whitney U"}
    assert df["proporcao_rejeicoes"].between(0, 1).all()


def test_d_zero_na_situacao_normal_reproduz_a_q1():
    df = q3.simular_situacao(PARAMETROS, "normal", (0.0,), 60, sim.criar_rng())
    p = q1.simular_erro_tipo_i(PARAMETROS, repeticoes=60, rng=sim.criar_rng())
    esperado = {"t de Welch": (p["p_welch"] < 0.05).sum(), "Mann-Whitney U": (p["p_mann_whitney"] < 0.05).sum()}
    obtido = df.set_index("teste")["rejeicoes"].to_dict()
    assert obtido == esperado


def test_poder_cresce_com_o_efeito_em_amostra_grande():
    df = q3.simular_situacao(PARAMETROS, "normal", (0.0, 1.0), 200, sim.criar_rng())
    welch = df[df["teste"] == "Mann-Whitney U"].set_index("d")["proporcao_rejeicoes"]
    assert welch[1.0] > welch[0.0]


@pytest.mark.parametrize("kwargs", [
    {"situacao": "inexistente"},
    {"situacao": "normal", "repeticoes": 0},
    {"situacao": "normal", "tamanhos_efeito": ()},
    {"situacao": "normal", "tamanhos_efeito": (-0.1,)},
])
def test_entradas_invalidas_sao_recusadas(kwargs):
    with pytest.raises(ValueError):
        q3.simular_situacao(PARAMETROS, **kwargs)


def test_comparacao_calcula_diferenca_para_a_situacao_normal():
    poder = pd.concat([
        pd.DataFrame({"situacao": "normal", "rotulo_situacao": "N", "d": [0.0, 0.5],
                      "teste": "t de Welch", "proporcao_rejeicoes": [0.10, 0.40]}),
        pd.DataFrame({"situacao": "amostras_pequenas", "rotulo_situacao": "P", "d": [0.0, 0.5],
                      "teste": "t de Welch", "proporcao_rejeicoes": [0.03, 0.10]}),
    ])
    comp = q3.comparar(poder)
    assert list(comp["situacao"].unique()) == ["amostras_pequenas"]
    assert list(comp["metrica"]) == ["erro tipo I (Q1)", "poder (Q2)"]
    assert comp["diferenca_pp"].round(6).tolist() == [-7.0, -30.0]
