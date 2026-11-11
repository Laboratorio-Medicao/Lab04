# Apresentação oral — LAB04

Regras do enunciado: o grupo responde às **15 perguntas oficiais usando o próprio dashboard**. A apresentação dura **até 7 minutos**, com respostas **curtas e diretas (~30 s cada)**. As perguntas são divididas entre os integrantes e **cada um responde a pelo menos 4**. O professor pode pedir a **qualquer integrante** que responda a **qualquer pergunta**, então todos devem saber todas.

Os textos das perguntas são os do PDF oficial. As respostas abaixo são roteiros curtos para o grupo ajustar, com números tirados do dashboard (`python -m dashboard`) e dos CSVs em `data/`.

## Divisão

| Integrante | Perguntas | Tema |
|---|---|---|
| Guilherme | 1, 2, 3, 4, 5 | Cenário, hipóteses, dados e o que cada teste compara |
| Arthur | 6, 7, 8, 9, 10 | G2, p-valor, erros tipo I e II, G3 e G4 |
| Marcos | 11, 12, 13, 14, 15 | Violação de pressuposto, α, expectativa, dados reais e recomendação |

Cada integrante tem 5 perguntas como titular (mínimo exigido: 4).

---

## Perguntas e roteiros de resposta

### Guilherme

**1. Qual é o cenário de vocês e o que H₀ e H₁ afirmam, em palavras simples?** *(dashboard, seção 1)*
Comparamos o tempo até o merge de PRs abertos pelo Dependabot e por humanos no `pallets/flask`. H₀: os dois grupos têm a mesma distribuição de tempo, sem diferença sistemática. H₁: os grupos diferem, um tende a ser mergeado mais rápido ou mais devagar que o outro.

**2. O teste de vocês é unicaudal ou bicaudal? Por quê?** *(seção 1)*
Bicaudal. Não temos razão a priori para supor a direção: o bot pode ser mergeado rápido (CI verde) ou esperar por janela de manutenção. A direção não foi escolhida olhando os dados.

**3. Como os dados reais foram coletados, e o que eles mostraram sobre a forma da distribuição?** *(seções 1 e 2, G1)*
Pela API GraphQL do GitHub, todos os PRs merged criados entre 2021-04-28 e 2024-08-01: 60 do Dependabot e 320 de humanos. A distribuição é muito assimétrica à direita: mediana de 0,77 h (bot) e 1,07 h (humanos), contra médias de 19,5 h e 153,1 h, com máximo de 5.234 h. Cerca de 58% (bot) e 49% (humanos) são mergeados em menos de 1 hora.

**4. Como os dados reais ajudaram a escolher os parâmetros da simulação?** *(seção 2, G1)*
Os dados mostram dois regimes, abaixo e acima de 1 hora. Por isso modelamos cada grupo como mistura de duas lognormais, com proporção, média e desvio de ln(T) estimados em cada regime. Uma lognormal única exagerava a média e o máximo do grupo humano.

**5. O que cada um dos dois testes compara de fato (médias, postos, proporções...)?** *(seção 3)*
O t de Welch compara as **médias** dos dois grupos. O Mann-Whitney compara **postos**: se um PR de um grupo tende a demorar mais que um PR do outro. Os dois têm a mesma H₀ de "mesma distribuição", mas testam consequências diferentes dela.

### Arthur

**6. No G2: o que é a distribuição da estatística sob H₀, e por que a região de rejeição fica onde fica?** *(seção 3, G2)*
É como a estatística do teste se distribuiria se H₀ fosse verdadeira. A região de rejeição fica nas duas caudas porque o teste é bicaudal: são os valores extremos, raros sob H₀ (5% no total na curva teórica). Atenção: no Welch, o histograma simulado tem cerca de 11% nessa região, mais que a curva teórica, e isso é o mesmo excesso de erro tipo I que aparece no G3.

**7. O que significa o p-valor do exemplo mostrado no G2? E o que ele não significa?** *(seção 3, G2)*
No exemplo (sorteado sob H₀), o t vale −1,48 e p = 0,14: se H₀ fosse verdadeira, uma estatística tão extrema ocorreria em 14% das amostras. Não é a probabilidade de H₀ ser verdadeira, não mede o tamanho do efeito e não garante relevância prática.

**8. No cenário de vocês, o que seria um erro tipo I e um erro tipo II? Qual dos dois seria mais grave?**
Erro tipo I: concluir que PRs do Dependabot e de humanos têm tempos diferentes quando na verdade são iguais. Erro tipo II: não perceber uma diferença que existe. Para nós o **tipo I é mais grave**: um falso positivo levaria a mudar a política de revisão ou de automação por uma diferença que não existe. O tipo II só nos faz manter o processo atual, e o custo é menor. Por isso o erro tipo I inflado do Welch pesa na nossa recomendação.

**9. No G3, algum teste se afastou de 5%? Ele ficou liberal ou conservador, e por quê?** *(seção 4, G3)*
Sim, o t de Welch. Ficou liberal no cenário base (11,2%) e com outliers extremos (8,5%), e conservador com amostras pequenas (0,5%). O Mann-Whitney ficou perto de 5% (entre 4,3% e 5,0%). A causa é a forte assimetria, que prejudica a aproximação normal da estatística t.

**10. No G4, qual teste tem mais poder? A diferença entre eles muda conforme o tamanho do efeito?** *(seção 5, G4)*
O Mann-Whitney, em todas as situações e para todo d > 0. A diferença muda com o tamanho do efeito: é maior em efeitos médios e diminui em efeitos grandes, quando o MW já está em 100% e o Welch sobe. Com d = 0,5 na situação base, MW 98,3% contra Welch 16,2%; com d = 1,0, 100% contra 54,4%. O poder do Welch chega a cair de 5,1% (d = 0,1) para 2,7% (d = 0,2) antes de subir. Em d = 0 o valor é o erro tipo I, não poder. Atenção: isso vale para efeitos positivos (Dependabot mais lento). Com efeito negativo, o sentido observado nos dados reais, o Welch ganha em d = −0,1 (21,8% contra 14,3%), em boa parte por causa do erro tipo I que ele já tem nesse sentido, e o Mann-Whitney volta à frente a partir de d = −0,2.

### Marcos

**11. Que violação de pressuposto vocês simularam, e por que ela afeta mais um teste do que o outro?** *(seções 4 e 5)*
Duas: amostras pequenas (n = 10 por grupo) e outliers extremos (desvio de ln T multiplicado por 1,5). Afetam mais o Welch porque ele depende da média e da variância, que ficam dominadas por poucos valores extremos e sem o apoio do teorema central do limite. O Mann-Whitney usa postos e quase não sente os outliers. Lembrar: a situação base já é assimétrica.

**12. Se vocês usassem α = 0,01 em vez de 0,05, o que mudaria no G3 e no G4?**
**G3:** a linha de referência desce para 1%. O Mann-Whitney fica perto dela nas três situações (0,8%, 0,8% e 0,9%). O Welch continua fora: 3,6% na situação base (3,6 vezes a referência) e 1,7% com outliers extremos, e com n = 10 vai a 0,0%. **G4:** todas as curvas descem, porque o critério fica mais rígido. Na situação base, em d = 0,5 o Mann-Whitney vai de 98,3% para 92,5% e o Welch de 16,2% para 1,5%. Em d = 1,0, o Welch vai de 54,4% para 17,0%. O Mann-Whitney segue acima do Welch em todos os pontos com d > 0, então a ordem não muda. Nos dados reais, o Welch (p < 0,001) segue rejeitando e o Mann-Whitney (p = 0,98) segue sem rejeitar.

**13. A simulação confirmou o que o grupo esperava antes de simular? Se não, o que explica a diferença?** *(seção 7)*
Confirmou. Esperávamos que o Mann-Whitney fosse mais confiável por causa da assimetria e dos outliers, e foi: erro tipo I perto de 5% e muito mais poder. O Welch teve erro tipo I fora de 5% e poder baixo e instável. Ressalva: a cauda simulada é mais pesada que a real, o que prejudica o Welch, e a sensibilidade com tempos truncados mostra o Welch bem melhor (poder de 99,8% em d = 1,0).

**14. Nos dados reais, os dois testes chegaram à mesma conclusão? O tamanho do efeito tem importância prática?** *(seção 6)*
Não. O Welch rejeita H₀ (t = −4,41, p < 0,001, Cohen's d = −0,27, efeito pequeno). O Mann-Whitney não rejeita (U = 9.582,5, p = 0,983, r = −0,001, efeito desprezível). A diferença de médias vem de poucos PRs muito lentos, mas o PR típico dos dois grupos demora quase o mesmo. Na prática, o efeito é pequeno ou desprezível.

**15. Qual teste vocês recomendam para o cenário, em que situação mudariam a recomendação, e qual é a principal limitação do estudo?** *(seção 7)*
Recomendamos o Mann-Whitney: erro tipo I perto de 5% e mais poder nos dados assimétricos. Mudaríamos para o t de Welch se a pergunta fosse sobre a média (por exemplo, tempo total de espera) ou com amostras grandes e pouco assimétricas. Principal limitação: um único repositório (`pallets/flask`) e uma simulação estimada desses mesmos dados, então os resultados podem não valer para outros projetos.

---

## Antes de apresentar

- Conferir os números acima com o dashboard aberto, pois o texto dele é gerado dos CSVs.
- As respostas das perguntas 8 e 12 não aparecem no dashboard (ver `RELATORIO_AUDITORIA.md`, M-03). Os números do α = 0,01 foram calculados reexecutando as simulações da Q1 a Q3 com semente 42; esses valores não estão em nenhum CSV do repositório.
- **Tempo:** 15 respostas de 30 s dão 7,5 min, acima do limite de 7 min. Meta combinada: **no máximo 25 s por resposta** (15 × 25 s ≈ 6 min 15 s). As respostas acima têm o detalhe completo, então cada integrante deve resumir à ideia central e deixar os números extras para se o professor pedir.
