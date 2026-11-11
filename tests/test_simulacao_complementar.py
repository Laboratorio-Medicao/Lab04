import pandas as pd
import pytest

import simulacao as sim
import simulacao_complementar as comp
import simulacao_q3 as q3

PARAMETROS = sim.carregar_parametros()
D = (0.0, 0.5, -0.5)


def rodar(situacoes=("normal",), repeticoes=20, efeitos=D):
    return comp.simular_complementar(PARAMETROS, efeitos, repeticoes, situacoes)


def test_mesma_semente_gera_o_mesmo_resultado():
    pd.testing.assert_frame_equal(rodar(), rodar())


def test_formato_longo_tem_um_registro_por_situacao_d_e_teste():
    df = rodar(("normal", "amostras_pequenas"))
    assert list(df.columns) == comp.COLUNAS
    assert len(df) == 2 * len(D) * 2
    assert set(df["teste"]) == {"t de Welch", "Mann-Whitney U"}
    assert set(df["d"]) == set(D)


def test_efeitos_comecam_nos_de_q3_na_mesma_ordem_e_incluem_os_negativos():
    n = len(q3.TAMANHOS_EFEITO)
    assert comp.EFEITOS[:n] == q3.TAMANHOS_EFEITO
    assert comp.EFEITOS[n:] == tuple(-d for d in q3.TAMANHOS_EFEITO if d > 0)
    assert all(d < 0 for d in comp.EFEITOS[n:])


def test_alfa_1_por_cento_nunca_rejeita_mais_que_alfa_5_por_cento():
    df = rodar(repeticoes=60)
    assert (df["rejeicoes_alfa01"] <= df["rejeicoes_alfa05"]).all()
    assert (df["rejeicoes_alfa05_bot_mais_rapido"] <= df["rejeicoes_alfa05"]).all()
    assert df[["proporcao_alfa05", "proporcao_alfa01"]].stack().between(0, 1).all()


def test_d_positivo_reproduz_a_q3_com_a_mesma_semente():
    df = comp.simular_complementar(PARAMETROS, (0.0, 0.5), 30, ("amostras_pequenas",))
    q = q3.simular_situacao(PARAMETROS, "amostras_pequenas", (0.0, 0.5), 30, sim.criar_rng())
    pd.testing.assert_series_equal(df["proporcao_alfa05"], q["proporcao_rejeicoes"], check_names=False)


def test_efeito_negativo_faz_o_bot_parecer_mais_rapido():
    df = comp.simular_complementar(PARAMETROS, (0.0, -1.0, 1.0), 100, ("normal",))
    mw = df[df["teste"] == "Mann-Whitney U"].set_index("d")
    assert mw.loc[-1.0, "proporcao_alfa05_bot_mais_rapido"] == mw.loc[-1.0, "proporcao_alfa05"] > 0.5
    assert mw.loc[1.0, "proporcao_alfa05_bot_mais_rapido"] == 0


@pytest.mark.parametrize("kwargs", [
    {"situacoes": ("inexistente",)},
    {"repeticoes": 0},
    {"efeitos": (0.5, -0.5)},
])
def test_entradas_invalidas_sao_recusadas(kwargs):
    with pytest.raises(ValueError):
        comp.simular_complementar(PARAMETROS, **kwargs)


def test_csv_versionado_reproduz_o_poder_da_q3_para_d_positivo():
    completo = pd.read_csv(comp.SAIDA)
    q = pd.read_csv(q3.SAIDA_PODER)
    chave = ["situacao", "d", "teste"]
    junto = completo[completo["d"] >= 0].merge(q, on=chave)
    assert len(junto) == len(q)
    assert (junto["rejeicoes_alfa05"] == junto["rejeicoes"]).all()
