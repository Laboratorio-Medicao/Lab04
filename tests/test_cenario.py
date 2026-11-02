import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CENARIO = (RAIZ / "docs/cenario.md").read_text(encoding="utf-8")
PARAMETROS = json.loads((RAIZ / "data/parametros_simulacao.json").read_text(encoding="utf-8"))


def br(valor, casas=2):
    return f"{valor:.{casas}f}".replace(".", ",").replace("-", "−")


def test_cenario_cita_os_parametros_do_json():
    for grupo in ("com_bot", "sem_bot", "h0"):
        for valor in PARAMETROS["mistura"][grupo].values():
            assert br(valor) in CENARIO, f"{grupo}: {valor}"


def test_cenario_cita_descritivas_e_comparacao_do_json():
    for grupo in ("com_bot", "sem_bot"):
        for chave in ("mediana", "media", "maximo", "desvio", "assimetria"):
            assert br(PARAMETROS["descritivas"][grupo][chave]) in CENARIO, f"{grupo}: {chave}"
        assert br(PARAMETROS["descritivas"][grupo]["minimo"], 4) in CENARIO, f"{grupo}: minimo"
        for modelo in ("real", "lognormal", "mistura"):
            for valor in PARAMETROS["comparacao"][grupo][modelo].values():
                assert br(valor) in CENARIO, f"{grupo}/{modelo}: {valor}"


def test_cenario_cita_tamanhos_e_efeito_do_json():
    assert f"n={PARAMETROS['n']['com_bot']}" in CENARIO
    assert f"n={PARAMETROS['n']['sem_bot']}" in CENARIO
    for chave in ("delta_log_observado", "delta_padronizado"):
        assert br(PARAMETROS[chave]) in CENARIO
    assert br(PARAMETROS["simulacao"]["sigma_log_h0"]) in CENARIO


def test_cenario_tem_hipoteses_com_sinal():
    assert "≠" in CENARIO and "H₀" in CENARIO and "H₁" in CENARIO


def test_pergunta_nao_tem_direcao():
    assert "mais rapidamente" not in CENARIO


def test_cenario_nao_guarda_numeros_antigos():
    assert "487,5" not in CENARIO and "(0,3h" not in CENARIO


def test_hipotese_inicial_preserva_o_texto_original():
    assert "com n=35 por grupo a aproximação pode ser insuficiente" in CENARIO
    assert "Nota de 20" in CENARIO
