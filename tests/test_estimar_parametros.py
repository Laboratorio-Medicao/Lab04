import numpy as np
import pandas as pd
import pytest

import estimar_parametros as ep

HORAS = np.exp(np.array([-2.0, -1.0, -3.0, 2.0, 4.0, 3.0]))


def test_ajustar_mistura_separa_regimes_no_limiar():
    p = ep.ajustar_mistura(HORAS)
    assert p["p_rapido"] == pytest.approx(0.5)
    assert p["mu_rapido"] == pytest.approx(-2.0)
    assert p["sigma_rapido"] == pytest.approx(np.std([-2, -1, -3]))
    assert p["mu_lento"] == pytest.approx(3.0)
    assert p["sigma_lento"] == pytest.approx(np.std([2, 4, 3]))


def test_ajustar_mistura_rejeita_tempo_nao_positivo():
    with pytest.raises(ValueError, match="positiv"):
        ep.ajustar_mistura(np.array([0.0, 0.5, 0.2, 3.0, 4.0]))


def test_ajustar_mistura_rejeita_regime_com_menos_de_duas_observacoes():
    with pytest.raises(ValueError, match="regime"):
        ep.ajustar_mistura(np.array([0.5, 0.2, 0.3, 4.0]))


def test_ajustar_lognormal_usa_media_e_desvio_do_log():
    p = ep.ajustar_lognormal(HORAS)
    assert p["mu"] == pytest.approx(np.log(HORAS).mean())
    assert p["sigma"] == pytest.approx(np.log(HORAS).std())


def test_amostrar_mistura_reproduz_com_a_mesma_semente():
    p = ep.ajustar_mistura(HORAS)
    a = ep.amostrar_mistura(p, (10, 5), np.random.default_rng(42))
    b = ep.amostrar_mistura(p, (10, 5), np.random.default_rng(42))
    assert a.shape == (10, 5) and np.array_equal(a, b) and (a > 0).all()


def test_amostrar_mistura_respeita_proporcao_de_rapidos():
    p = {"p_rapido": 0.3, "mu_rapido": -5.0, "sigma_rapido": 0.1, "mu_lento": 5.0, "sigma_lento": 0.1}
    a = ep.amostrar_mistura(p, (100_000, 1), np.random.default_rng(42))
    assert (a < 1).mean() == pytest.approx(0.3, abs=0.01)


def test_estimar_gera_h0_com_dados_combinados_e_delta(tmp_path):
    csv = tmp_path / "d.csv"
    pd.DataFrame({"grupo": ["com_bot"] * 6 + ["sem_bot"] * 6,
                  "horas_ate_merge": list(HORAS) + list(HORAS * 2)}).to_csv(csv, index=False)
    r = ep.estimar(str(csv))
    assert r["n"] == {"com_bot": 6, "sem_bot": 6}
    assert set(r["mistura"]) == {"com_bot", "sem_bot", "h0"}
    assert r["delta_log_observado"] == pytest.approx(-np.log(2))
    combinado = np.concatenate([HORAS, HORAS * 2])
    assert r["mistura"]["h0"]["p_rapido"] == pytest.approx((combinado < 1).mean())
    assert r["fonte"] == "data/dados_reais.csv"
    sigma = np.log(combinado).std()
    assert r["simulacao"]["base"] == "mistura.h0"
    assert r["simulacao"]["sinais_delta"] == [-1, 1]
    assert r["simulacao"]["sigma_log_h0"] == pytest.approx(sigma)
    assert r["delta_padronizado"] == pytest.approx(-np.log(2) / sigma)


def test_estimar_define_descritivas_e_comparacao(tmp_path):
    csv = tmp_path / "d.csv"
    pd.DataFrame({"grupo": ["com_bot"] * 6 + ["sem_bot"] * 6,
                  "horas_ate_merge": list(HORAS) + list(HORAS * 2)}).to_csv(csv, index=False)
    r = ep.estimar(str(csv))
    assert set(r["descritivas"]["com_bot"]) == {"minimo", "mediana", "media", "maximo", "desvio", "assimetria"}
    assert set(r["comparacao"]["sem_bot"]) == {"real", "lognormal", "mistura"}
    assert set(r["comparacao"]["sem_bot"]["real"]) == {"q25", "mediana", "q75", "q90", "media", "maximo"}
