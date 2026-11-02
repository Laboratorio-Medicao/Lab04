import re
import sys
import tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    for trecho in ("58%", "49%", "5.234", "mistura de duas lognormais"):
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
