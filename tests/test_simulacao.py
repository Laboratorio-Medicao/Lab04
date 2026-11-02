import numpy as np
import pytest

import simulacao as sim

PARAMETROS = sim.carregar_parametros()


def test_mesma_semente_gera_os_mesmos_dados():
    a = sim.gerar(PARAMETROS, rng=sim.criar_rng())
    b = sim.gerar(PARAMETROS, rng=sim.criar_rng())
    np.testing.assert_array_equal(a[0], b[0])
    np.testing.assert_array_equal(a[1], b[1])


def test_semente_diferente_gera_dados_diferentes():
    a = sim.gerar(PARAMETROS, rng=sim.criar_rng(42))
    b = sim.gerar(PARAMETROS, rng=sim.criar_rng(7))
    assert not np.array_equal(a[0], b[0])


def test_tamanhos_padrao_vem_dos_parametros_e_sao_configuraveis():
    bot, humano = sim.gerar(PARAMETROS)
    assert (len(bot), len(humano)) == (60, 320)
    bot, humano = sim.gerar(PARAMETROS, n_bot=8, n_humano=9)
    assert (len(bot), len(humano)) == (8, 9)


def test_tempos_sao_positivos_e_finitos():
    for distribuicao in sim.DISTRIBUICOES:
        bot, humano = sim.gerar(PARAMETROS, distribuicao=distribuicao)
        assert (bot > 0).all() and (humano > 0).all()
        assert np.isfinite(bot).all() and np.isfinite(humano).all()


def test_h1_desloca_o_log_do_bot_em_delta():
    d = 0.3
    bot, humano = sim.gerar(PARAMETROS, h1=True, d=d, n_bot=50_000, n_humano=50_000)
    esperado = sim.delta_de_d(d, PARAMETROS)
    obtido = np.log(bot).mean() - np.log(humano).mean()
    assert obtido == pytest.approx(esperado, abs=0.1)


def test_h0_ignora_o_efeito():
    a = sim.gerar(PARAMETROS, h1=False, d=0.5, rng=sim.criar_rng())
    b = sim.gerar(PARAMETROS, rng=sim.criar_rng())
    np.testing.assert_array_equal(a[0], b[0])


def test_h1_com_d_zero_equivale_a_h0():
    a = sim.gerar(PARAMETROS, h1=True, d=0.0, rng=sim.criar_rng())
    b = sim.gerar(PARAMETROS, rng=sim.criar_rng())
    np.testing.assert_array_equal(a[0], b[0])


def test_sinal_de_d_inverte_o_deslocamento():
    mais = sim.gerar(PARAMETROS, h1=True, d=0.5, rng=sim.criar_rng())[0]
    menos = sim.gerar(PARAMETROS, h1=True, d=-0.5, rng=sim.criar_rng())[0]
    assert (mais > menos).all()


def test_fator_sigma_aumenta_a_dispersao_do_log():
    base = sim.gerar(PARAMETROS, n_bot=20_000, n_humano=1)[0]
    larga = sim.gerar(PARAMETROS, n_bot=20_000, n_humano=1, fator_sigma=2.0)[0]
    assert np.log(larga).std() > np.log(base).std()


def test_lognormal_tem_a_media_e_o_desvio_de_h0():
    bot = sim.gerar(PARAMETROS, distribuicao="lognormal", n_bot=100_000, n_humano=1)[0]
    assert np.log(bot).std() == pytest.approx(PARAMETROS["simulacao"]["sigma_log_h0"], rel=0.03)


@pytest.mark.parametrize("kwargs, msg", [
    ({"distribuicao": "normal"}, "Distribuição"),
    ({"n_bot": 0}, "tamanho"),
    ({"fator_sigma": 0}, "fator"),
])
def test_parametros_invalidos_sao_rejeitados(kwargs, msg):
    with pytest.raises(ValueError, match=msg):
        sim.gerar(PARAMETROS, **kwargs)
