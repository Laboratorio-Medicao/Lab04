import importlib

import executar_tudo


def test_etapas_na_ordem_do_pipeline():
    nomes = [m for _, m in executar_tudo.etapas()]
    assert nomes == ["estimar_parametros", "simulacao", "simulacao_q1", "simulacao_q2",
                     "simulacao_q3", "simulacao_complementar"]


def test_coleta_so_entra_com_a_opcao():
    assert "coletar_dados" not in [m for _, m in executar_tudo.etapas()]
    assert executar_tudo.etapas(coletar=True)[0][1] == "coletar_dados"


def test_toda_etapa_tem_main():
    for _, modulo in executar_tudo.etapas(coletar=True):
        assert callable(importlib.import_module(modulo).main)


def test_executar_chama_cada_etapa_em_ordem(monkeypatch):
    chamadas = []

    class Falso:
        def __init__(self, nome):
            self.nome = nome

        def main(self):
            chamadas.append(self.nome)

    monkeypatch.setattr(importlib, "import_module", lambda nome: Falso(nome))
    executar_tudo.executar()
    assert chamadas == [m for _, m in executar_tudo.etapas()]
