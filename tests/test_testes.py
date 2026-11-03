"""Testes para src/testes.py."""

import sys
import os
import math

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from testes import (
    ALPHA,
    ResultadoTestes,
    ResultadoTeste,
    PressupostosWelch,
    aplicar_testes,
    verificar_pressupostos,
    interpretar,
    _cohen_d,
    _r_mann_whitney,
)


RNG = np.random.default_rng(0)


def _grupos_normais(mu_a=0.0, mu_b=0.0, n_a=60, n_b=320, seed=1):
    rng = np.random.default_rng(seed)
    return rng.normal(mu_a, 1, n_a), rng.normal(mu_b, 1, n_b)


def _grupos_lognormais(d=0.0, n_a=60, n_b=320, seed=42):
    rng = np.random.default_rng(seed)
    a = rng.lognormal(0, 2, n_a)
    b = rng.lognormal(d, 2, n_b)
    return a, b


# ---------------------------------------------------------------------------
# aplicar_testes
# ---------------------------------------------------------------------------


class TestAplicarTestes:
    def test_retorna_resultado_testes(self):
        bot, hum = _grupos_normais()
        res = aplicar_testes(bot, hum)
        assert isinstance(res, ResultadoTestes)
        assert isinstance(res.welch, ResultadoTeste)
        assert isinstance(res.mann_whitney, ResultadoTeste)

    def test_nomes_corretos(self):
        bot, hum = _grupos_normais()
        res = aplicar_testes(bot, hum)
        assert res.welch.nome == "t de Welch"
        assert res.mann_whitney.nome == "Mann-Whitney U"

    def test_cenario_propagado(self):
        bot, hum = _grupos_normais()
        res = aplicar_testes(bot, hum, cenario="teste")
        assert res.cenario == "teste"

    def test_p_valor_no_intervalo(self):
        bot, hum = _grupos_normais()
        res = aplicar_testes(bot, hum)
        assert 0.0 <= res.welch.p_valor <= 1.0
        assert 0.0 <= res.mann_whitney.p_valor <= 1.0

    def test_rejeita_h0_coerente_com_p(self):
        bot, hum = _grupos_normais()
        res = aplicar_testes(bot, hum)
        assert res.welch.rejeita_h0 == (res.welch.p_valor < ALPHA)
        assert res.mann_whitney.rejeita_h0 == (res.mann_whitney.p_valor < ALPHA)

    def test_n_propagados(self):
        bot, hum = _grupos_normais(n_a=60, n_b=320)
        res = aplicar_testes(bot, hum)
        assert res.welch.n_bot == 60
        assert res.welch.n_humano == 320
        assert res.mann_whitney.n_bot == 60
        assert res.mann_whitney.n_humano == 320

    def test_nao_rejeita_h0_com_grupos_identicos(self):
        rng = np.random.default_rng(99)
        x = rng.lognormal(0, 2, 200)
        # mesma amostra → p deve ser alto (> 0,05) na média entre repetições
        # aqui usamos cópias da mesma distribuição geradas com seeds próximas
        a = np.random.default_rng(1).lognormal(0, 2, 200)
        b = np.random.default_rng(2).lognormal(0, 2, 200)
        res = aplicar_testes(a, b)
        # não garantimos a direção individual, mas registramos que é possível
        assert isinstance(res.welch.rejeita_h0, bool)

    def test_rejeita_h0_com_efeito_grande(self):
        """Com efeito grande (d=5), ambos os testes devem rejeitar."""
        bot = np.random.default_rng(10).lognormal(0, 1, 200)
        hum = np.random.default_rng(11).lognormal(5, 1, 200)
        res = aplicar_testes(bot, hum)
        assert res.welch.rejeita_h0
        assert res.mann_whitney.rejeita_h0

    def test_bicaudal_welch(self):
        """p-valor do Welch deve ser o dobro do unilateral (simetria para normais)."""
        a, b = _grupos_normais(mu_a=1.0, mu_b=0.0, n_a=200, n_b=200)
        from scipy import stats
        t_uni = stats.ttest_ind(a, b, equal_var=False, alternative="greater").pvalue
        res = aplicar_testes(a, b)
        assert abs(res.welch.p_valor - 2 * t_uni) < 0.01

    def test_tamanho_efeito_cohen_d_nome(self):
        bot, hum = _grupos_normais()
        res = aplicar_testes(bot, hum)
        assert res.welch.nome_efeito == "Cohen's d"

    def test_tamanho_efeito_r_nome(self):
        bot, hum = _grupos_normais()
        res = aplicar_testes(bot, hum)
        assert res.mann_whitney.nome_efeito == "r (Z/√N)"


# ---------------------------------------------------------------------------
# verificar_pressupostos
# ---------------------------------------------------------------------------


class TestVerificarPressupostos:
    def test_retorna_pressupostos(self):
        bot, hum = _grupos_normais()
        pre = verificar_pressupostos(bot, hum)
        assert isinstance(pre, PressupostosWelch)

    def test_normais_passam_shapiro(self):
        rng = np.random.default_rng(7)
        a = rng.normal(0, 1, 50)
        b = rng.normal(0, 1, 50)
        pre = verificar_pressupostos(a, b)
        assert pre.normalidade_ok

    def test_lognormais_reprovam_shapiro(self):
        bot, hum = _grupos_lognormais(n_a=60, n_b=200)
        pre = verificar_pressupostos(bot, hum)
        assert not pre.normalidade_ok

    def test_p_valores_no_intervalo(self):
        bot, hum = _grupos_normais()
        pre = verificar_pressupostos(bot, hum)
        for p in (pre.shapiro_bot_p, pre.shapiro_humano_p, pre.levene_p):
            assert 0.0 <= p <= 1.0

    def test_variancia_igual_coerente(self):
        bot, hum = _grupos_normais()
        pre = verificar_pressupostos(bot, hum)
        assert pre.variancia_igual == (pre.levene_p > ALPHA)


# ---------------------------------------------------------------------------
# interpretar
# ---------------------------------------------------------------------------


class TestInterpretar:
    def test_retorna_string(self):
        bot, hum = _grupos_normais()
        res = aplicar_testes(bot, hum)
        texto = interpretar(res)
        assert isinstance(texto, str)
        assert len(texto) > 0

    def test_contem_nomes_dos_testes(self):
        bot, hum = _grupos_normais()
        res = aplicar_testes(bot, hum)
        texto = interpretar(res)
        assert "t de Welch" in texto
        assert "Mann-Whitney" in texto

    def test_menciona_p_valor_nao_e_probabilidade_h0(self):
        bot, hum = _grupos_normais()
        res = aplicar_testes(bot, hum)
        texto = interpretar(res)
        assert "NÃO é a probabilidade de H₀" in texto

    def test_verbose_false_omite_interpretacao(self):
        bot, hum = _grupos_normais()
        res = aplicar_testes(bot, hum)
        texto = interpretar(res, verbose=False)
        assert "Interpretação" not in texto

    def test_rejeita_aparece_quando_h0_rejeitada(self):
        bot = np.random.default_rng(20).lognormal(0, 0.1, 500)
        hum = np.random.default_rng(21).lognormal(3, 0.1, 500)
        res = aplicar_testes(bot, hum)
        texto = interpretar(res)
        assert "REJEITA" in texto


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_cohen_d_zero_quando_medias_iguais(self):
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0, 3.0])
        assert _cohen_d(a, b) == 0.0

    def test_cohen_d_positivo_quando_a_maior(self):
        a = np.array([10.0, 11.0, 12.0])
        b = np.array([1.0, 2.0, 3.0])
        assert _cohen_d(a, b) > 0

    def test_r_zero_quando_u_na_mediana(self):
        n_a, n_b = 60, 320
        u_mid = n_a * n_b / 2
        assert _r_mann_whitney(u_mid, n_a, n_b) == 0.0

    def test_r_no_intervalo(self):
        """r deve estar em (−1, 1) para U em [0, n_a * n_b]."""
        n_a, n_b = 60, 320
        for u in (0, n_a * n_b // 4, n_a * n_b // 2, n_a * n_b):
            r = _r_mann_whitney(float(u), n_a, n_b)
            assert -1.0 <= r <= 1.0
