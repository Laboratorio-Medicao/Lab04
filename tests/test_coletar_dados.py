from unittest.mock import MagicMock, patch

import pytest

import coletar_dados as cd


def no(numero, tipo="User", login="alguem"):
    autor = None if tipo is None else {"__typename": tipo, "login": login}
    return {"number": numero, "author": autor,
            "createdAt": "2023-01-01T00:00:00Z", "mergedAt": "2023-01-01T01:00:00Z"}


def pagina(nos, proximo=None, total=None):
    return {"data": {"search": {
        "issueCount": len(nos) if total is None else total,
        "pageInfo": {"hasNextPage": proximo is not None, "endCursor": proximo},
        "nodes": nos}}}


def test_eh_humano_aceita_apenas_user():
    assert cd.eh_humano(no(1)) is True
    assert cd.eh_humano(no(1, tipo="Bot")) is False
    assert cd.eh_humano(no(1, tipo=None)) is False


def test_termos_busca_usam_a_mesma_janela():
    janela = "created:2021-04-28..2024-08-01"
    assert janela in cd.termos_busca("com_bot") and "author:app/dependabot" in cd.termos_busca("com_bot")
    assert janela in cd.termos_busca("sem_bot") and "-author:app/dependabot" in cd.termos_busca("sem_bot")


def test_horas_ate_merge_preserva_merge_em_segundos():
    assert cd.horas_ate_merge("2023-01-01T00:00:00Z", "2023-01-01T00:00:10Z") == 0.0028


def test_coletar_grupo_percorre_paginas_e_ordena():
    paginas = [pagina([no(9)], "c1", total=2), pagina([no(3)], total=2)]
    with patch.object(cd, "gh_graphql", side_effect=paginas):
        linhas = cd.coletar_grupo("com_bot")
    assert [l["pr_number"] for l in linhas] == [3, 9]


def test_coleta_incompleta_falha():
    with patch.object(cd, "gh_graphql", return_value=pagina([no(1)], total=2)):
        with pytest.raises(RuntimeError, match="incompleta"):
            cd.coletar_grupo("com_bot")


def test_coletar_grupo_sem_bot_descarta_bots_e_ghost():
    nos = [no(1), no(2, tipo="Bot", login="pre-commit-ci"), no(3, tipo=None)]
    with patch.object(cd, "gh_graphql", return_value=pagina(nos)):
        assert [l["pr_number"] for l in cd.coletar_grupo("sem_bot")] == [1]


def test_coletar_grupo_com_bot_mantem_autor_bot():
    with patch.object(cd, "gh_graphql", return_value=pagina([no(1, tipo="Bot", login="dependabot")])):
        assert len(cd.coletar_grupo("com_bot")) == 1


def test_busca_acima_do_limite_falha():
    with patch.object(cd, "gh_graphql", return_value=pagina([no(1)], total=1001)):
        with pytest.raises(RuntimeError, match="1000"):
            cd.coletar_grupo("sem_bot")


def test_gh_graphql_decodifica_utf8():
    resposta = MagicMock(returncode=0, stdout='{"data": {}}')
    with patch.object(cd.subprocess, "run", return_value=resposta) as run:
        cd.gh_graphql("termos")
    run.assert_called_once()
    assert run.call_args.kwargs["encoding"] == "utf-8"
