import pandas as pd
import pytest

import simulacao as sim
import simulacao_q1 as q1
import simulacao_q2 as q2
import simulacao_q3 as q3

PARAMETROS = sim.carregar_parametros()
D = (0.0, 0.2, 0.4, 0.6, 1.0)


def rodar(repeticoes=20, d=D):
    return q2.simular_poder(PARAMETROS, d, repeticoes, sim.criar_rng())


def test_mesma_semente_gera_o_mesmo_resultado():
    pd.testing.assert_frame_equal(rodar(), rodar())


def test_formato_longo_tem_um_registro_por_d_e_teste():
    df = rodar()
    assert list(df.columns) == q2.COLUNAS
    assert len(df) == len(D) * 2
    assert set(df["teste"]) == {"t de Welch", "Mann-Whitney U"}
    assert df["proporcao_rejeicoes"].between(0, 1).all()


def test_padrao_tem_ao_menos_5_tamanhos_comecando_em_zero():
    assert len(q3.TAMANHOS_EFEITO) >= 5 and q3.TAMANHOS_EFEITO[0] == 0


def test_d_zero_reproduz_a_q1():
    df = q2.simular_poder(PARAMETROS, D, 60, sim.criar_rng())
    p = q1.simular_erro_tipo_i(PARAMETROS, repeticoes=60, rng=sim.criar_rng())
    esperado = {"t de Welch": (p["p_welch"] < 0.05).sum(), "Mann-Whitney U": (p["p_mann_whitney"] < 0.05).sum()}
    assert df[df["d"] == 0].set_index("teste")["rejeicoes"].to_dict() == esperado


def test_poder_cresce_com_o_efeito():
    df = q2.simular_poder(PARAMETROS, D, 200, sim.criar_rng())
    for teste, g in df.groupby("teste"):
        assert g.set_index("d")["proporcao_rejeicoes"][1.0] > g.set_index("d")["proporcao_rejeicoes"][0.0], teste


@pytest.mark.parametrize("kwargs", [
    {"tamanhos_efeito": (0.0, 0.5)},
    {"tamanhos_efeito": (0.1, 0.2, 0.3, 0.4, 0.5)},
    {"repeticoes": 0},
])
def test_entradas_invalidas_sao_recusadas(kwargs):
    with pytest.raises(ValueError):
        q2.simular_poder(PARAMETROS, **kwargs)


def test_sensibilidade_tem_o_mesmo_formato_e_e_reprodutivel():
    a = q2.simular_sensibilidade(PARAMETROS, 1000.0, D, 20, sim.criar_rng())
    b = q2.simular_sensibilidade(PARAMETROS, 1000.0, D, 20, sim.criar_rng())
    pd.testing.assert_frame_equal(a, b)
    assert list(a.columns) == q2.COLUNAS
    assert len(a) == len(D) * 2


def test_teto_muito_alto_nao_altera_a_curva():
    a = q2.simular_sensibilidade(PARAMETROS, 1e12, D, 20, sim.criar_rng())
    assert a.equals(rodar())


def test_teto_real_e_o_maximo_dos_dados():
    assert q2.teto_real() == pd.read_csv(q2.DADOS_REAIS)["horas_ate_merge"].max()


@pytest.mark.parametrize("kwargs", [{"teto": 0}, {"teto": -1.0}, {"teto": 100.0, "repeticoes": 0}])
def test_sensibilidade_recusa_entradas_invalidas(kwargs):
    with pytest.raises(ValueError):
        q2.simular_sensibilidade(PARAMETROS, **kwargs)
