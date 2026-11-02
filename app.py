# `math` fornece funções matemáticas; aqui usamos `ceil` para arredondar
# para cima a quantidade de linhas necessárias na grade de histogramas.
import math

# `pandas` manipula dados tabulares (DataFrames), como o CSV deste projeto.
import pandas as pd

# `graph_objects` permite montar gráficos Plotly configurando cada elemento.
import plotly.graph_objects as go

# `streamlit` fornece os componentes da página, os filtros e a exibição dos gráficos.
import streamlit as st

# `make_subplots` cria uma figura com vários gráficos menores organizados em grade.
from plotly.subplots import make_subplots

# Função do projeto que lê o CSV e o devolve como um DataFrame do pandas.
from src.data_loader import load_data

# Define configurações gerais da página. Deve ser chamado antes de outros
# comandos de interface do Streamlit.
st.set_page_config(
    page_title="Acidentes de trânsito: distribuição e correlação",
    page_icon=":material/traffic:",
    layout="wide",  # Usa a largura disponível, útil para exibir gráficos lado a lado.
)

# Lista das colunas numéricas que podem ser selecionadas na barra lateral.
# Os nomes precisam corresponder exatamente aos cabeçalhos do arquivo CSV.
VARIAVEIS = [
    "Hour",
    "Month",
    "Is_Holiday",
    "Speed_Limit_kmh",
    "Visibility_m",
    "Congestion_Index",
    "Driver_Age",
    "Driver_Experience_yrs",
    "Vehicle_Age_yrs",
    "Recorded_Speed_kmh",
    "Baseline_Expected_Response_Time_min",
    "Vehicles_Involved",
    "Actual_Response_Time_min",
    "Road_Closure_Duration_min",
    "congestion_log",
]

# Carrega os dados. No `data_loader.py`, `load_data()` usa `pandas.read_csv`
# para abrir `data/clean/dataset.csv` e retornar o conteúdo como DataFrame.
df = load_data()

# Primeiro, verifica se todas as colunas pedidas existem no DataFrame.
# A expressão `x not in df.columns` testa se o nome da coluna está ausente;
# a compreensão de lista reúne todos os nomes ausentes em uma nova lista.
colunas_ausentes = [variavel for variavel in VARIAVEIS if variavel not in df.columns]
if colunas_ausentes:
    # `st.error` mostra um aviso de erro no app e `st.stop` interrompe a execução
    # deste rerun para evitar que o restante do código use colunas inexistentes.
    st.error(f"Colunas necessárias não encontradas no dataset: {', '.join(colunas_ausentes)}")
    st.stop()

# Os histogramas e a correlação exigem números. `is_numeric_dtype` verifica
# se uma coluna tem um tipo numérico reconhecido pelo pandas.
colunas_nao_numericas = [
    variavel
    for variavel in VARIAVEIS
    if not pd.api.types.is_numeric_dtype(df[variavel])
]
if colunas_nao_numericas:
    # Falha explicitamente caso uma coluna numérica tenha sido lida como texto.
    st.error(
        "As seguintes colunas precisam conter valores numéricos: "
        f"{', '.join(colunas_nao_numericas)}"
    )
    st.stop()

# Título e texto de orientação na área principal do dashboard.
st.title("Análise de acidentes de trânsito")
st.caption(
    "Explore a distribuição das variáveis e a correlação entre elas. "
    "Use os filtros na barra lateral para definir a análise."
)

# O bloco `with st.sidebar` coloca todos os elementos indentados na barra lateral.
# Ao alterar um widget, o Streamlit executa o script novamente e atualiza os gráficos.
with st.sidebar:
    st.header("Filtros")

    # `st.multiselect` permite escolher zero, uma ou várias opções.
    # `options` define as escolhas possíveis; `default` marca inicialmente
    # todas as variáveis como selecionadas.
    variaveis_selecionadas = st.multiselect(
        "Variáveis para análise",
        options=VARIAVEIS,
        default=VARIAVEIS,
        help="As variáveis selecionadas aparecem nos histogramas e no mapa de correlação.",
    )

    # Dicionário para guardar cada intervalo escolhido no formato
    # {nome_da_coluna: (limite_inicial, limite_final)}.
    intervalos = {}
    if variaveis_selecionadas:
        st.subheader("Intervalos")
        for variavel in variaveis_selecionadas:
            # `dropna()` cria uma série sem valores ausentes (NaN).
            # Isso evita tentar calcular os limites usando valores vazios.
            valores_validos = df[variavel].dropna()
            if valores_validos.empty:
                st.warning(f"A variável {variavel} não possui valores disponíveis.")
                continue

            # `min()` e `max()` encontram os extremos observados da coluna.
            minimo = valores_validos.min()
            maximo = valores_validos.max()

            # Se todos os registros têm o mesmo valor, não há faixa para escolher.
            # Guardamos o próprio valor como intervalo para manter o filtro consistente.
            if minimo == maximo:
                st.caption(f"{variavel}: valor fixo {minimo}")
                intervalos[variavel] = (minimo, maximo)
            # `is_integer_dtype` verifica se a coluna usa números inteiros.
            # Nesse caso, o controle deslizante avança de um número inteiro por vez.
            elif pd.api.types.is_integer_dtype(df[variavel]):
                # `st.slider` cria um controle de faixa quando `value` recebe
                # uma tupla (menor, maior). O usuário escolhe os dois limites.
                intervalos[variavel] = st.slider(
                    variavel,
                    min_value=int(minimo),
                    max_value=int(maximo),
                    value=(int(minimo), int(maximo)),
                    step=1,
                    key=f"intervalo_{variavel}",
                )
            else:
                # Para dados decimais, convertemos os limites para `float`.
                # A variável `passo` define o tamanho dos incrementos do slider:
                # aproximadamente 1% da amplitude, com mínimo de 0,01.
                minimo_float = float(minimo)
                maximo_float = float(maximo)
                intervalos[variavel] = st.slider(
                    variavel,
                    min_value=minimo_float,
                    max_value=maximo_float,
                    value=(minimo_float, maximo_float),
                    step=max((maximo_float - minimo_float) / 100, 0.01),
                    key=f"intervalo_{variavel}",
                )

# Aplica os filtros aos dados antes de desenhar os gráficos.
# `copy()` cria uma cópia do DataFrame original para que os filtros não alterem `df`.
df_filtrado = df.copy()

# `intervalos.items()` percorre os pares (nome da coluna, faixa escolhida).
# `between(inicio, fim)` retorna True para cada linha cujo valor está na faixa,
# incluindo os extremos. Usamos essa sequência de True/False para manter as linhas
# correspondentes no DataFrame.
for variavel, (inicio, fim) in intervalos.items():
    df_filtrado = df_filtrado[df_filtrado[variavel].between(inicio, fim)]

# `len()` conta as linhas. `:,` no texto formata a contagem com separador
# de milhar, facilitando a leitura de números grandes.
st.caption(
    f"{len(df_filtrado):,} de {len(df):,} registros dentro dos intervalos selecionados."
)

# `st.columns` divide a área principal em colunas. Os valores [1.25, 1]
# definem a proporção de largura: a área de histogramas fica um pouco maior.
coluna_distribuicao, coluna_correlacao = st.columns([1.25, 1])

# Matriz de histogramas: cada histograma agrupa os valores em faixas (bins)
# e conta quantos registros caem em cada faixa, mostrando a distribuição.
# `with coluna_distribuicao` direciona os componentes seguintes para essa coluna.
with coluna_distribuicao:
    st.subheader("Distribuição das variáveis")

    # Tratamento de situações em que não há dados para desenhar o gráfico.
    if not variaveis_selecionadas:
        st.info("Selecione ao menos uma variável na barra lateral.")
    elif df_filtrado.empty:
        st.warning("Nenhum registro corresponde aos intervalos selecionados.")
    else:
        # A grade terá três gráficos por linha. `ceil` arredonda o resultado
        # para cima: por exemplo, 4 gráficos precisam de 2 linhas.
        numero_colunas = 3
        numero_linhas = math.ceil(len(variaveis_selecionadas) / numero_colunas)

        # `make_subplots` cria uma figura contendo vários espaços para gráficos.
        # `subplot_titles` fornece um título para cada espaço; os espaçamentos
        # são reduzidos para caber melhor na página, especialmente com muitas linhas.
        figura_histogramas = make_subplots(
            rows=numero_linhas,
            cols=numero_colunas,
            subplot_titles=variaveis_selecionadas,
            vertical_spacing=min(0.08, 0.4 / numero_linhas),
            horizontal_spacing=0.08,
        )

        # `enumerate` percorre a lista e fornece tanto a posição (`indice`)
        # quanto o nome da variável. Usamos a posição para calcular em qual
        # linha e coluna da grade cada histograma deve ser colocado.
        for indice, variavel in enumerate(variaveis_selecionadas):
            # Divisão inteira (`//`) indica a linha da grade; resto (`%`)
            # indica a coluna. Somamos 1 porque Plotly numera linhas/colunas a partir de 1.
            linha = indice // numero_colunas + 1
            coluna = indice % numero_colunas + 1

            # `go.Histogram` descreve um histograma Plotly.
            # `x` recebe os valores da variável; `dropna()` remove valores ausentes.
            # `nbinsx` sugere até 20 faixas para agrupar os valores.
            figura_histogramas.add_trace(
                go.Histogram(
                    x=df_filtrado[variavel].dropna(),
                    nbinsx=20,
                    marker_color="#4C78A8",
                    hovertemplate="Faixa: %{x}<br>Frequência: %{y}<extra></extra>",
                    showlegend=False,
                ),
                # `add_trace` adiciona o histograma à posição correspondente na grade.
                row=linha,
                col=coluna,
            )
            # Define os nomes dos eixos de cada gráfico individual.
            figura_histogramas.update_xaxes(title_text=variavel, row=linha, col=coluna)
            figura_histogramas.update_yaxes(title_text="Frequência", row=linha, col=coluna)

        # Ajustes visuais da figura inteira: altura cresce conforme o número
        # de linhas, `bargap` controla o espaço entre barras e `margin` as bordas.
        figura_histogramas.update_layout(
            height=max(360, numero_linhas * 240),
            bargap=0.08,
            template="plotly_white",
            margin=dict(l=20, r=20, t=55, b=20),
        )
        # Exibe a figura Plotly no Streamlit. `width="stretch"` faz o gráfico
        # ocupar a largura disponível; `alt` descreve o gráfico para acessibilidade.
        st.plotly_chart(
            figura_histogramas,
            width="stretch",
            alt="Matriz de histogramas das variáveis selecionadas",
        )

# Heatmap (mapa de calor) da correlação de Pearson: cada célula representa
# a associação linear entre um par de variáveis. A correlação varia de -1 a 1:
# valores próximos de 1 indicam associação positiva, próximos de -1 negativa,
# e próximos de 0 pouca associação linear. Correlação não prova causalidade.
with coluna_correlacao:
    st.subheader("Matriz de correlação")

    # Correlação compara pares de colunas; por isso são necessárias duas ou mais.
    if len(variaveis_selecionadas) < 2:
        st.info("Selecione ao menos duas variáveis para calcular a correlação.")
    elif df_filtrado.empty:
        st.warning("Nenhum registro corresponde aos intervalos selecionados.")
    else:
        # Seleciona as colunas escolhidas e calcula a correlação de Pearson.
        # O resultado é uma matriz quadrada: linhas e colunas são as variáveis.
        # Valores ausentes são tratados pelo pandas durante o cálculo por pares.
        matriz_correlacao = df_filtrado[variaveis_selecionadas].corr(method="pearson")

        # Prepara textos para mostrar dentro das células do mapa.
        # `to_numpy()` transforma a matriz do pandas em uma matriz NumPy;
        # `:.2f` formata cada número com duas casas decimais.
        # Se o valor não existir (por exemplo, coluna constante), mostra "n/a".
        rotulos = [
            [
                f"{valor:.2f}" if pd.notna(valor) else "n/a"
                for valor in linha
            ]
            for linha in matriz_correlacao.to_numpy()
        ]

        # `go.Heatmap` constrói o mapa de calor:
        # `z` são os valores numéricos e `x`/`y` são os nomes dos eixos.
        # `zmin` e `zmax` mantêm a escala comparável entre -1 e 1.
        figura_correlacao = go.Figure(
            data=go.Heatmap(
                z=matriz_correlacao.to_numpy(),
                x=variaveis_selecionadas,
                y=variaveis_selecionadas,
                text=rotulos,
                texttemplate="%{text}",
                colorscale="RdBu",
                zmin=-1,
                zmax=1,
                colorbar=dict(title="Pearson"),
                hovertemplate=(
                    # Texto exibido quando o cursor passa sobre uma célula.
                    # %{x}, %{y} e %{z} são substituídos pelos valores do gráfico.
                    "Variável X: %{x}<br>Variável Y: %{y}"
                    "<br>Correlação: %{z:.2f}<extra></extra>"
                ),
            )
        )

        # Ajusta dimensões e apresentação do mapa. A altura aumenta com a
        # quantidade de variáveis, e o ângulo dos rótulos evita sobreposição.
        figura_correlacao.update_layout(
            height=max(420, len(variaveis_selecionadas) * 38),
            template="plotly_white",
            margin=dict(l=20, r=20, t=25, b=110),
            xaxis=dict(tickangle=-45),
            yaxis=dict(autorange="reversed"),
        )

        # Apresenta a matriz de correlação interativa na coluna da direita.
        st.plotly_chart(
            figura_correlacao,
            width="stretch",
            alt="Mapa de calor da correlação de Pearson entre as variáveis selecionadas",
        )
