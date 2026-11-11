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
    erros_2 = [i for i in secao(at, "2. Os dados") if i.type == "error"]
    assert len(erros_2) == 1 and "data/dados_reais.csv" in erros_2[0].value
    assert not [i for i in secao(at, "2. Os dados") if i.type == "plotly_chart"]


def test_secao_3_integra_o_g2_e_o_texto():
    itens = secao(abrir(), "3. Como os testes funcionam")
    graficos = [i for i in itens if i.type == "plotly_chart"]
    assert len(graficos) == 1 and graficos[0].proto.theme == ""
    estatisticas, exemplo = dashboard.dados_g2()
    fracoes = dashboard.fracao_na_regiao(estatisticas, exemplo)
    assert dashboard.texto_g2(exemplo, fracoes) in [i.value for i in itens if i.type == "markdown"]
    assert [i.label for i in itens if i.type == "expander"] == ["O que o p-valor não significa"]


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
    assert [i.label for i in itens if i.type == "expander"] == [
        "Ver dados do G4", "Ver o poder com efeitos negativos (Dependabot mais rápido)",
        "Sensibilidade: e se a cauda simulada fosse mais leve?"]


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
    erros_5 = [i for i in secao(at, "5. Poder") if i.type == "error"]
    assert len(erros_5) == 1 and "G4" in erros_5[0].value
    assert not [i for i in secao(at, "5. Poder") if i.type == "plotly_chart"]


def dados_erro_tipo_i():
    return dashboard.dados_g3(pd.read_csv(RAIZ / "data" / "simulacao_q1_resumo.csv"),
                              pd.read_csv(RAIZ / "data" / "simulacao_q3_comparacao.csv"))


def test_secao_4_integra_o_g3_o_texto_e_a_tabela():
    itens = secao(abrir(), "4. Erro tipo I")
    graficos = [i for i in itens if i.type == "plotly_chart"]
    assert len(graficos) == 1 and graficos[0].proto.theme == ""
    assert dashboard.texto_g3(dados_erro_tipo_i()) in [i.value for i in itens if i.type == "markdown"]
    assert [i.label for i in itens if i.type == "expander"] == [
        "Ver dados do G3", "Erro tipo I e erro tipo II no nosso cenário", "E se α fosse 1% em vez de 5%?"]


def test_texto_g3_tem_ate_quatro_frases_e_aponta_o_teste_que_se_desviou():
    texto = dashboard.texto_g3(dados_erro_tipo_i())
    assert 2 <= len(re.findall(r"[.!?](?:\s|$)", texto)) <= 4
    for trecho in ("4,3%", "5,0%", "11,2%", "0,5%", "8,5%", "liberal", "conservador"):
        assert trecho in texto


def test_topo_tem_links_do_repositorio_e_do_projects():
    markdowns = [m.value for m in abrir().main.markdown]
    assert any(dashboard.URL_REPOSITORIO in m and dashboard.URL_PROJECTS in m for m in markdowns)


# ---------------------------------------------------------------------------
# Seções 6 e 7 (#22)
# ---------------------------------------------------------------------------

from testes import ResultadoTeste, ResultadoTestes  # noqa: E402


def fabricar(p_welch, p_mw, d=0.3, r=0.2):
    def teste(nome, p, efeito, nome_efeito):
        return ResultadoTeste(nome, 1.0, p, p < 0.05, efeito, nome_efeito, 60, 320)
    return ResultadoTestes(teste("t de Welch", p_welch, d, "Cohen's d"),
                           teste("Mann-Whitney U", p_mw, r, "r (Z/√N)"), "real")


def resultado_real():
    return dashboard.resultado_g5(pd.read_csv(RAIZ / "data" / "dados_reais.csv"))


def test_secao_6_tem_tabela_texto_e_nao_esta_em_construcao():
    itens = secao(abrir(), "6. Dados reais")
    assert not [i for i in itens if i.type in ("info", "error")]
    assert len([i for i in itens if i.type == "arrow_data_frame" or i.type == "dataframe"]) == 1
    assert dashboard.texto_secao_6(resultado_real()) in [i.value for i in itens if i.type == "markdown"]


def test_secoes_6_e_7_sem_info():
    at = abrir()
    assert not any("#22" in i.value for i in at.info)


def test_texto_secao_6_cita_os_dois_p_valores_e_a_divergencia_real():
    res = resultado_real()
    texto = dashboard.texto_secao_6(res)
    assert dashboard.formatar_p(res.welch.p_valor) in texto
    assert dashboard.formatar_p(res.mann_whitney.p_valor) in texto
    assert "divergem" in texto


def test_texto_secao_6_caso_concordante_e_divergente():
    assert "Os dois testes rejeitam H₀" in dashboard.texto_secao_6(fabricar(0.001, 0.01))
    assert "nenhum dos dois testes rejeita H₀" in dashboard.texto_secao_6(fabricar(0.3, 0.6))
    assert "divergem" in dashboard.texto_secao_6(fabricar(0.3, 0.01))


def test_p_muito_pequeno_aparece_como_menor_que_0001():
    assert dashboard.formatar_p(1e-5) == "< 0,001"
    assert dashboard.formatar_p(0.9826) == "0,983"
    assert "< 0,001" in dashboard.texto_secao_6(fabricar(1e-6, 0.5))


def test_secao_7_tem_cinco_blocos_e_recomenda_um_teste():
    itens = secao(abrir(), "7. Conclusão")
    texto = "\n".join(i.value for i in itens if i.type == "markdown")
    for bloco in ("**Expectativa.**", "**Achados.**", "**Recomendação.**", "**Quando mudaria.**", "**Limitação.**"):
        assert bloco in texto
    assert "Recomendamos o Mann-Whitney" in texto
    assert "{evidencia}" not in texto and "não há evidência a α = 5%" in texto
    assert "Em construção" not in texto
    assert not [i for i in itens if i.type == "info"]


def test_texto_secao_7_reflete_os_desvios_e_o_poder_nao_monotono_do_welch():
    g4 = dados_poder()
    blocos = dashboard.texto_secao_7(resultado_real(), dados_erro_tipo_i(), g4)
    achados = blocos[1]
    for trecho in ("liberal no cenário base (11,2%)", "liberal com outliers extremos (8,5%)",
                   "conservador com amostras pequenas (0,5%)", "5,1%", "2,7%", "1,5%", "9,4%"):
        assert trecho in achados


# ---------------------------------------------------------------------------
# Explicações das perguntas 7, 8, 11 e 12, G2 com a fração simulada e poder do Welch
def complementar():
    return pd.read_csv(RAIZ / "data" / "simulacao_complementar.csv")


def frases(texto):
    return len(re.findall(r"[.!?](?:\s|$)", texto))


def test_texto_g2_com_fracoes_mostra_o_excesso_do_welch_e_mantem_ate_quatro_frases():
    estatisticas, exemplo = dashboard.dados_g2()
    fracoes = dashboard.fracao_na_regiao(estatisticas, exemplo)
    texto = dashboard.texto_g2(exemplo, fracoes)
    assert fracoes["welch"] > 0.08 > fracoes["mann_whitney"] > 0.03
    assert f"{fracoes['welch']:.1%}".replace(".", ",") in texto and "5% na curva teórica" in texto
    assert "5% no total" not in texto and 2 <= frases(texto) <= 4


def test_pvalor_nao_significa_cobre_os_quatro_pontos():
    texto = dashboard.texto_pvalor_nao_significa()
    for trecho in ("Não é a probabilidade de H₀", "Não é a chance de a conclusão", "Não mede o tamanho do efeito",
                   "Não garante relevância prática"):
        assert trecho in texto


def test_erros_tipo_i_e_ii_no_contexto_do_dependabot_e_qual_e_mais_grave():
    texto = dashboard.texto_erros_tipo_i_ii()
    for trecho in ("**Erro tipo I:**", "**Erro tipo II:**", "Dependabot", "não existe diferença",
                   "1 − poder", "**Qual é mais grave:**"):
        assert trecho in texto


def test_situacoes_explicam_que_o_cenario_base_ja_e_assimetrico_e_o_mecanismo_de_cada_violacao():
    texto = dashboard.texto_situacoes(carregar_parametros())
    for trecho in ("já é muito assimétrico", "3,9", "6,3", "não** comparam dados normais",
                   "Amostras pequenas (n = 10", "aproximação normal", "Outliers extremos", "média e "
                   "a variância"):
        assert trecho in texto


def test_nenhum_rotulo_do_dashboard_chama_o_cenario_base_de_normal():
    texto = "\n".join(m.value for m in abrir().main.markdown)
    assert "situação normal" not in texto.lower() and "Normal (cenário)" not in texto


def test_texto_alfa_compara_5_e_1_por_cento_com_os_numeros_da_simulacao():
    texto = dashboard.texto_alfa(complementar())
    for trecho in ("α = 1%", "0,8% a 0,9%", "3,6%", "1,7%", "0,0%", "98,3%", "92,5%", "16,2%", "1,5%",
                   "não muda para nenhum d > 0"):
        assert trecho in texto


def test_texto_queda_welch_explica_o_lado_negativo_das_rejeicoes():
    texto = dashboard.texto_queda_welch(complementar())
    for trecho in ("cai até d = 0,2", "11,2%", "11,1%", "4,8%", "1,7%", "3,4%", "t negativo", "erro tipo I"):
        assert trecho in texto


def test_texto_efeito_negativo_mostra_onde_a_vantagem_muda_de_lado():
    texto = dashboard.texto_efeito_negativo(complementar(), carregar_parametros())
    for trecho in ("−0,12", "21,8%", "14,3%", "muda de lado", "volta à frente", "100,0%"):
        assert trecho in texto.replace("-0,12", "−0,12")


def test_texto_sensibilidade_traz_o_truncamento_como_limitacao():
    sens = pd.read_csv(RAIZ / "data" / "simulacao_q2_sensibilidade.csv")
    texto = dashboard.texto_sensibilidade(sens, 5234.0858)
    for trecho in ("5.234 h", "11,2%", "14,1%", "54,4%", "99,8%", "limitação"):
        assert trecho in texto


def test_secoes_4_e_5_nao_mostram_erro_e_trazem_as_novas_explicacoes():
    at = abrir()
    assert not at.exception and not at.error
    secao4 = "\n".join(i.value for i in secao(at, "4. Erro tipo I") if i.type == "markdown")
    assert "Como ler as três situações" in secao4
    secao5 = "\n".join(i.value for i in secao(at, "5. Poder") if i.type == "markdown")
    assert "Por que o poder do Welch cai" in secao5 and "Dependabot é mais rápido" in secao5


def test_secao_7_limitacao_cita_a_sensibilidade_e_o_efeito_negativo():
    itens = secao(abrir(), "7. Conclusão")
    texto = "\n".join(i.value for i in itens if i.type == "markdown")
    assert "99,8%" in texto and "efeito negativo" in texto and "situação normal" not in texto
    assert "situação cenário" not in texto and texto.count("limitação") <= 1
