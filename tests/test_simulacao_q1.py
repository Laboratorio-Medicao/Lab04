import numpy as np
import pandas as pd
import pytest

import simulacao as sim
import simulacao_q1 as q1

PARAMETROS = sim.carregar_parametros()


def test_mesma_semente_gera_os_mesmos_pvalores():
    a = q1.simular_erro_tipo_i(PARAMETROS, repeticoes=30, rng=sim.criar_rng())
    b = q1.simular_erro_tipo_i(PARAMETROS, repeticoes=30, rng=sim.criar_rng())
    pd.testing.assert_frame_equal(a, b)


def test_pvalores_tem_uma_linha_por_repeticao_e_ficam_em_0_1():
    df = q1.simular_erro_tipo_i(PARAMETROS, repeticoes=25, rng=sim.criar_rng())
    assert list(df.columns) == ["repeticao", "p_welch", "p_mann_whitney"]
    assert len(df) == 25
    assert df[["p_welch", "p_mann_whitney"]].apply(lambda c: c.between(0, 1).all()).all()


def test_repeticoes_invalidas_sao_recusadas():
    with pytest.raises(ValueError):
        q1.simular_erro_tipo_i(PARAMETROS, repeticoes=0)


def test_resumo_calcula_proporcao_e_intervalo():
    pvalores = pd.DataFrame({
        "repeticao": range(1, 101),
        "p_welch": [0.01] * 5 + [0.5] * 95,
        "p_mann_whitney": [0.01] * 10 + [0.5] * 90,
    })
    resumo = q1.resumir(pvalores).set_index("teste")
    assert resumo.loc["t de Welch", "proporcao_rejeicoes"] == pytest.approx(0.05)
    assert resumo.loc["Mann-Whitney U", "rejeicoes"] == 10
    assert (resumo["situacao"] == "H₀ verdadeira").all()
    meia = 1.959964 * np.sqrt(0.05 * 0.95 / 100) * 100
    assert resumo.loc["t de Welch", "ic95_meia_largura_pp"] == pytest.approx(meia)
