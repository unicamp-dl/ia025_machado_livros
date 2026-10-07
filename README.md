# Machado de Assis — romances (um `.txt` por livro)

Dataset derivado para exercícios de **classificação de texto**: dado um trecho, identificar de qual romance de Machado de Assis ele veio.

Há duas versões paralelas dos mesmos oito romances:

| Pasta | Conteúdo |
| --- | --- |
| `livros_com_nomes/` | Texto cru, com nomes próprios |
| `livros_sem_nomes/` | Mesmo texto, com entidades de pessoa (`PER`) substituídas por `[NOME]` |

A versão sem nomes tende a ser **mais difícil**: o modelo não pode se apoiar só em Capitu, Brás Cubas, Rubião, etc.

## Romances incluídos

Cada arquivo é um romance; o **rótulo** é o nome do arquivo (sem `.txt`):

- `a_mao_e_a_luva.txt` — A Mão e a Luva
- `helena.txt` — Helena
- `iaia_garcia.txt` — Iaiá Garcia
- `memorias_postumas_de_bras_cubas.txt` — Memórias Póstumas de Brás Cubas
- `quincas_borba.txt` — Quincas Borba
- `dom_casmurro.txt` — Dom Casmurro
- `esau_e_jaco.txt` — Esaú e Jacó
- `memorial_de_aires.txt` — Memorial de Aires

Metadados (tamanhos, linhas de origem no dump, contagem de `[NOME]`): ver [`manifest.json`](manifest.json).

## O que estes arquivos são (e não são)

- Texto **cru**, fatiado a partir do dump concatenado do Projeto Machado.
- Podem conter números de página, linhas curtas, cabeçalhos/rodapés de edição digital, quebras estranhas.
- **Não** há split treino/validação/teste pronto: chunking, limpeza e splits ficam a cargo de quem usa o dataset.
- Em `livros_sem_nomes/`, só entidades `PER` foram mascaradas (spaCy `pt_core_news_lg`). O NER erra em português oitocentista; topônimos e vocativos ainda podem vazar informação da obra.

## Origem

Construído a partir do dump [`textonormalizado1000.txt`](https://github.com/ethelbeluzzi/projetomachado/blob/main/textonormalizado1000.txt) do **[Projeto Machado](https://github.com/ethelbeluzzi/projetomachado)** ([ethelbeluzzi/projetomachado](https://github.com/ethelbeluzzi/projetomachado)), que por sua vez usa textos do [Domínio Público](http://www.dominiopublico.gov.br/).

Este repositório **não** inclui o Projeto Machado completo — apenas o recorte dos oito romances acima, em duas pastas.

## Reprodução

Para regenerar os `.txt` a partir do dump original, clone o Projeto Machado **na raiz deste repositório** (pasta `projetomachado/`):

```bash
git clone https://github.com/ethelbeluzzi/projetomachado.git
```

O script [`machado_livros.py`](machado_livros.py) espera o dump em `projetomachado/textonormalizado1000.txt`. Em seguida:

```bash
uv sync
uv run python machado_livros.py
```

## Licença / uso

Os arquivos originais do Domínio Público / Projeto Machado são descritos lá como destinados a **uso educativo**. Respeite essa restrição ao reutilizar o material.

## Estrutura sugerida do repositório

```
README.md
manifest.json
machado_livros.py          # regeneração (opcional)
livros_com_nomes/*.txt
livros_sem_nomes/*.txt
projetomachado/            # só local, via git clone (não versionado aqui)
```

## Citação / créditos

- Textos: Machado de Assis (domínio público), via Domínio Público / Projeto Machado.
- Dataset concatenado original: [ethelbeluzzi/projetomachado](https://github.com/ethelbeluzzi/projetomachado).
- Recorte por romance + versão com nomes mascarados: este repositório.
