import re
import sys
import tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import dashboard
from simulacao import carregar_parametros

RAIZ = Path(__file__).resolve().parent.parent
APP = str(RAIZ / "dashboard.py")
SECOES = ["1. Cenário", "2. Os dados", "3. Como os testes funcionam", "4. Erro tipo I",
          "5. Poder", "6. Dados reais", "7. Conclusão"]


def abrir():
    return AppTest.from_file(APP, default_timeout=30).run()


def secao(at, titulo):
    itens = list(at.main.children.values())
    inicio = next(i for i, n in enumerate(itens) if n.type == "header" and n.value == titulo)
    fim = next((i for i in range(inicio + 1, len(itens)) if itens[i].type == "header"), len(itens))
    return itens[inicio + 1:fim]


def test_dashboard_abre_sem_erro():
    assert not abrir().exception


def test_dashboard_tem_as_sete_secoes():
    assert [h.value for h in abrir().header] == SECOES


def test_secao_2_integra_o_g1_o_texto_e_a_tabela():
    itens = secao(abrir(), "2. Os dados")
    graficos = [i for i in itens if i.type == "plotly_chart"]
    assert len(graficos) == 1 and graficos[0].proto.theme == ""
    assert dashboard.texto_g1(carregar_parametros()) in [i.value for i in itens if i.type == "markdown"]
    tabelas = [i for i in itens if i.type == "expander"]
    assert len(tabelas) == 1 and tabelas[0].label == "Ver dados do G1"
    assert any("10.000 sorteios" in i.value for i in itens if i.type == "caption")
    assert len(tabelas[0].dataframe) == 1


def test_avisos_de_secao_pendente_citam_o_card():
    assert all(re.fullmatch(r"Em construção: card #\d+( e #\d+)?\.", i.value) for i in abrir().info)


def test_dashboard_abre_fora_da_raiz(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert not abrir().exception


def test_texto_g1_tem_ate_quatro_frases_com_dados_reais():
    texto = dashboard.texto_g1(carregar_parametros())
    assert 2 <= len(re.findall(r"[.!?](?:\s|$)", texto)) <= 4
    for trecho in ("58%", "49%", "5.234", "mistura de duas lognormais", "ln(T)", "separados em 1 hora"):
        assert trecho in texto


def test_comando_unico_chama_o_streamlit():
    resultado = MagicMock(returncode=0)
    with patch.object(dashboard.runtime, "exists", return_value=False), \
         patch.object(dashboard.subprocess, "run", return_value=resultado) as run:
        with pytest.raises(SystemExit) as saida:
            dashboard.main()
    assert run.call_args.args[0] == [sys.executable, "-m", "streamlit", "run", APP]
    assert saida.value.code == 0


def test_comando_unico_encerra_sem_traceback_no_ctrl_c():
    with patch.object(dashboard.runtime, "exists", return_value=False), \
         patch.object(dashboard.subprocess, "run", side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit) as saida:
            dashboard.main()
    assert saida.value.code == 0


def test_tema_claro_fixo():
    config = tomllib.loads((RAIZ / ".streamlit/config.toml").read_text(encoding="utf-8"))
    assert config["theme"]["base"] == "light"
    assert config["server"]["headless"] is True
    assert config["browser"]["gatherUsageStats"] is False


def test_erro_nos_dados_aparece_na_secao_2_sem_derrubar_as_demais():
    invalidos = pd.DataFrame({"grupo": ["com_bot", "sem_bot"], "horas_ate_merge": [0.0, 1.0]})
    original = pd.read_csv

    def leitura(caminho, *a, **k):
        return invalidos if "dados_reais" in str(caminho) else original(caminho, *a, **k)

    with patch.object(pd, "read_csv", side_effect=leitura):
        at = abrir()
    assert not at.exception
    assert [h.value for h in at.header] == SECOES
    assert len(at.error) == 1 and "data/dados_reais.csv" in at.error[0].value
    assert not [i for i in secao(at, "2. Os dados") if i.type == "plotly_chart"]


def test_secao_3_integra_o_g2_e_o_texto():
    itens = secao(abrir(), "3. Como os testes funcionam")
    graficos = [i for i in itens if i.type == "plotly_chart"]
    assert len(graficos) == 1 and graficos[0].proto.theme == ""
    _, exemplo = dashboard.dados_g2()
    assert dashboard.texto_g2(exemplo) in [i.value for i in itens if i.type == "markdown"]


def test_texto_g2_tem_ate_quatro_frases():
    _, exemplo = dashboard.dados_g2()
    texto = dashboard.texto_g2(exemplo)
    assert 2 <= len(re.findall(r"[.!?](?:\s|$)", texto)) <= 4


def dados_poder():
    return dashboard.dados_g4(pd.read_csv(RAIZ / "data" / "simulacao_q2_poder.csv"),
                              pd.read_csv(RAIZ / "data" / "simulacao_q3_poder.csv"))


def test_secao_5_integra_o_g4_o_texto_e_a_tabela():
    itens = secao(abrir(), "5. Poder")
    graficos = [i for i in itens if i.type == "plotly_chart"]
    assert len(graficos) == 1 and graficos[0].proto.theme == ""
    assert dashboard.texto_g4(dados_poder()) in [i.value for i in itens if i.type == "markdown"]
    assert [i.label for i in itens if i.type == "expander"] == ["Ver dados do G4"]


def test_texto_g4_tem_ate_quatro_frases_com_dados_reais():
    texto = dashboard.texto_g4(dados_poder())
    assert 2 <= len(re.findall(r"[.!?](?:\s|$)", texto)) <= 4
    for trecho in ("100%", "54%", "49%", "3%", "9%"):
        assert trecho in texto


def test_erro_nos_csvs_de_poder_aparece_na_secao_5_sem_derrubar_as_demais():
    original = pd.read_csv
    def leitura(caminho, *a, **k):
        if "simulacao_q2_poder" in str(caminho):
            return pd.DataFrame({"d": [0.0]})
        return original(caminho, *a, **k)
    with patch.object(pd, "read_csv", side_effect=leitura):
        at = abrir()
    assert not at.exception
    assert [h.value for h in at.header] == SECOES
    assert len(at.error) == 1 and "G4" in at.error[0].value
    assert not [i for i in secao(at, "5. Poder") if i.type == "plotly_chart"]


def dados_erro_tipo_i():
    return dashboard.dados_g3(pd.read_csv(RAIZ / "data" / "simulacao_q1_resumo.csv"),
                              pd.read_csv(RAIZ / "data" / "simulacao_q3_comparacao.csv"))


def test_secao_4_integra_o_g3_o_texto_e_a_tabela():
    itens = secao(abrir(), "4. Erro tipo I")
    graficos = [i for i in itens if i.type == "plotly_chart"]
    assert len(graficos) == 1 and graficos[0].proto.theme == ""
    assert dashboard.texto_g3(dados_erro_tipo_i()) in [i.value for i in itens if i.type == "markdown"]
    assert [i.label for i in itens if i.type == "expander"] == ["Ver dados do G3"]


def test_texto_g3_tem_ate_quatro_frases_e_aponta_o_teste_que_se_desviou():
    texto = dashboard.texto_g3(dados_erro_tipo_i())
    assert 2 <= len(re.findall(r"[.!?](?:\s|$)", texto)) <= 4
    for trecho in ("4,3%", "5,0%", "11,2%", "0,5%", "8,5%", "liberal", "conservador"):
        assert trecho in texto
