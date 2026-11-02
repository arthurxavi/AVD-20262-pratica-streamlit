from datetime import date

# `pandas` manipula dados tabulares (DataFrames), como o CSV deste projeto.
import pandas as pd

# `altair` cria gráficos declarativos: descrevemos os dados e os canais visuais
# (eixos, cores e textos), e a biblioteca monta a visualização.
import altair as alt

# `streamlit` fornece os componentes da página, os filtros e a exibição dos gráficos.
import streamlit as st

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

# `st.cache_data` guarda em cache o resultado da função. Se ela for chamada de
# novo com os mesmos argumentos, Streamlit reutiliza o gráfico em vez de criá-lo
# outra vez. O DataFrame e o nome da variável fazem parte da chave do cache.
@st.cache_data(show_spinner=False)
def criar_histograma(df_variavel: pd.DataFrame, variavel: str) -> alt.Chart:
    """Cria um histograma Altair para uma variável numérica."""
    return (
        alt.Chart(df_variavel)
        .mark_bar(color="#4C78A8")
        .encode(
            # `bin` agrupa valores contínuos em até 20 faixas; `count()` conta
            # quantas linhas caem em cada faixa e forma a altura das barras.
            x=alt.X(
                f"{variavel}:Q",
                bin=alt.Bin(maxbins=20),
                title=variavel,
            ),
            y=alt.Y("count():Q", title="Frequência"),
            tooltip=[
                alt.Tooltip(
                    f"{variavel}:Q",
                    bin=alt.Bin(maxbins=20),
                    title="Faixa",
                ),
                alt.Tooltip("count():Q", title="Frequência"),
            ],
        )
        .properties(height=180, title=variavel)
    )


# Também armazenamos em cache o cálculo de correlação e a especificação Altair.
# O argumento com as colunas selecionadas limita os dados usados nesta função.
@st.cache_data(show_spinner=False)
def criar_mapa_correlacao(
    df_variaveis: pd.DataFrame, variaveis: tuple[str, ...]
) -> alt.LayerChart:
    """Calcula a correlação de Pearson e cria um heatmap Altair."""
    matriz = df_variaveis[list(variaveis)].corr(method="pearson")

    # Converte a matriz quadrada em tabela longa: cada linha passa a representar
    # uma célula do heatmap, com o nome das duas variáveis e sua correlação.
    dados = (
        matriz.rename_axis(index="variavel_y", columns="variavel_x")
        .reset_index()
        .melt(
            id_vars="variavel_y",
            var_name="variavel_x",
            value_name="correlacao",
        )
    )
    # Mantém "n/a" visível para pares em que a correlação não pode ser calculada,
    # por exemplo, quando uma das colunas tem o mesmo valor em todas as linhas.
    dados["rotulo"] = dados["correlacao"].map(
        lambda valor: f"{valor:.2f}" if pd.notna(valor) else "n/a"
    )

    # A lista `variaveis` preserva a ordem escolhida na barra lateral nos eixos.
    base = alt.Chart(dados).encode(
        x=alt.X(
            "variavel_x:N",
            title=None,
            sort=list(variaveis),
            axis=alt.Axis(labelAngle=-45),
        ),
        y=alt.Y("variavel_y:N", title=None, sort=list(variaveis)),
        tooltip=[
            alt.Tooltip("variavel_x:N", title="Variável X"),
            alt.Tooltip("variavel_y:N", title="Variável Y"),
            alt.Tooltip("correlacao:Q", title="Pearson", format=".2f"),
        ],
    )

    # A primeira camada desenha as células coloridas; a segunda escreve
    # o valor numérico em cada célula para facilitar a leitura do heatmap.
    heatmap = base.mark_rect().encode(
        color=alt.Color(
            "correlacao:Q",
            title="Pearson",
            scale=alt.Scale(scheme="redblue", domain=[-1, 1]),
        )
    )
    rotulos = base.mark_text(fontSize=11).encode(text=alt.Text("rotulo:N"))

    # `alt.layer` sobrepõe os textos às células. `alt.Step` define o espaço
    # reservado por categoria, então a matriz cresce quando mais variáveis
    # forem selecionadas.
    return (
        alt.layer(heatmap, rotulos)
        .properties(
            width=alt.Step(30),
            height=alt.Step(30),
        )
        .configure_axis(labelFontSize=10)
    )


# Filtra o Dashboard 2 e armazena em cache o resultado para reaproveitá-lo
# enquanto os dados e todos os filtros permanecerem iguais.
@st.cache_data(show_spinner=False)
def filtrar_dashboard_kpis(
    dados: pd.DataFrame,
    data_inicial: date,
    data_final: date,
    areas: tuple[str, ...],
    prioridades: tuple[str, ...],
    climas: tuple[str, ...],
    severidades: tuple[str, ...],
) -> pd.DataFrame:
    """Deduplica e filtra as ocorrências por data e categorias."""
    ocorrencias = dados.drop_duplicates(subset="Record_ID", keep="first")
    mascara = ocorrencias["Date"].between(data_inicial, data_final)
    mascara &= ocorrencias["Area_Type"].isin(areas)
    mascara &= ocorrencias["Dispatch_Priority"].isin(prioridades)
    mascara &= ocorrencias["Weather"].isin(climas)
    mascara &= ocorrencias["Accident_Severity"].isin(severidades)
    return ocorrencias.loc[mascara].copy()


# Cada função abaixo prepara e cria uma visualização Altair interativa.
# O DataFrame filtrado é argumento da função e, portanto, também participa
# da chave usada por `st.cache_data`.
@st.cache_data(show_spinner=False)
def criar_histograma_resposta(dados: pd.DataFrame) -> alt.Chart:
    """Mostra a frequência de ocorrências por faixa de tempo real de resposta."""
    return (
        alt.Chart(dados)
        .mark_bar(color="#4C78A8")
        .encode(
            x=alt.X(
                "Actual_Response_Time_min:Q",
                bin=alt.Bin(maxbins=20),
                title="Tempo real de resposta (minutos)",
            ),
            y=alt.Y("count():Q", title="Quantidade de ocorrências"),
            tooltip=[
                alt.Tooltip(
                    "Actual_Response_Time_min:Q",
                    bin=alt.Bin(maxbins=20),
                    title="Faixa de resposta (min)",
                ),
                alt.Tooltip("count():Q", title="Ocorrências"),
            ],
        )
        .properties(height=300)
        .interactive()
    )


@st.cache_data(show_spinner=False)
def criar_scatter_resposta(dados: pd.DataFrame) -> alt.Chart:
    """Compara o tempo esperado com o tempo real de resposta."""
    return (
        alt.Chart(dados)
        .mark_circle(size=55, opacity=0.55)
        .encode(
            x=alt.X(
                "Baseline_Expected_Response_Time_min:Q",
                title="Tempo esperado (minutos)",
            ),
            y=alt.Y(
                "Actual_Response_Time_min:Q",
                title="Tempo real de resposta (minutos)",
            ),
            color=alt.Color("Area_Type:N", title="Tipo de área"),
            tooltip=[
                alt.Tooltip("Record_ID:N", title="Registro"),
                alt.Tooltip("Date:T", title="Data", format="%d/%m/%Y"),
                alt.Tooltip("Area_Type:N", title="Área"),
                alt.Tooltip("Dispatch_Priority:N", title="Prioridade"),
                alt.Tooltip(
                    "Baseline_Expected_Response_Time_min:Q",
                    title="Tempo esperado (min)",
                    format=".1f",
                ),
                alt.Tooltip(
                    "Actual_Response_Time_min:Q",
                    title="Tempo real (min)",
                    format=".1f",
                ),
            ],
        )
        .properties(height=300)
        .interactive()
    )


@st.cache_data(show_spinner=False)
def criar_grafico_area(dados: pd.DataFrame) -> alt.Chart:
    """Mostra a participação percentual das ocorrências por tipo de área."""
    contagem = (
        dados.groupby("Area_Type", as_index=False)
        .agg(ocorrencias=("Record_ID", "nunique"))
    )
    contagem["percentual"] = (
        contagem["ocorrencias"] / contagem["ocorrencias"].sum() * 100
    )

    # Clicar na legenda destaca a área correspondente e reduz a opacidade das
    # demais fatias; o tooltip mostra contagem e percentual exatos.
    selecao_area = alt.selection_point(fields=["Area_Type"], bind="legend")
    return (
        alt.Chart(contagem)
        .mark_arc(outerRadius=115)
        .encode(
            theta=alt.Theta("ocorrencias:Q", title="Ocorrências"),
            color=alt.Color("Area_Type:N", title="Tipo de área"),
            opacity=alt.condition(
                selecao_area,
                alt.value(1),
                alt.value(0.3),
            ),
            tooltip=[
                alt.Tooltip("Area_Type:N", title="Área"),
                alt.Tooltip("ocorrencias:Q", title="Ocorrências"),
                alt.Tooltip("percentual:Q", title="Participação", format=".1f"),
            ],
        )
        .add_params(selecao_area)
        .properties(height=300)
    )


@st.cache_data(show_spinner=False)
def criar_grafico_horario(dados: pd.DataFrame) -> alt.Chart:
    """Mostra a quantidade de ocorrências em cada hora, de 0 a 23."""
    contagem = (
        dados.groupby("Hour")
        .agg(ocorrencias=("Record_ID", "nunique"))
        .reindex(range(24), fill_value=0)
        .rename_axis("Hour")
        .reset_index()
    )
    return (
        alt.Chart(contagem)
        .mark_bar(color="#4C78A8")
        .encode(
            x=alt.X(
                "Hour:O",
                title="Hora do dia",
                sort=list(range(24)),
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y("ocorrencias:Q", title="Quantidade de ocorrências"),
            tooltip=[
                alt.Tooltip("Hour:O", title="Hora"),
                alt.Tooltip("ocorrencias:Q", title="Ocorrências"),
            ],
        )
        .properties(height=300)
        .interactive()
    )


# Carrega os dados. No `data_loader.py`, `load_data()` usa `pandas.read_csv`
# para abrir `data/clean/dataset.csv` e retornar o conteúdo como DataFrame.
df = load_data()

# Primeiro, verifica se todas as colunas pedidas existem no DataFrame.
# A expressão `x not in df.columns` testa se o nome da coluna está ausente;
# a compreensão de lista reúne todos os nomes ausentes em uma nova lista.
COLUNAS_DASHBOARD_KPIS = [
    "Record_ID",
    "Date",
    "Area_Type",
    "Dispatch_Priority",
    "Weather",
    "Accident_Severity",
    "Actual_Response_Time_min",
    "Baseline_Expected_Response_Time_min",
    "Road_Closure_Duration_min",
]
colunas_necessarias = list(dict.fromkeys(VARIAVEIS + COLUNAS_DASHBOARD_KPIS))
colunas_ausentes = [
    variavel for variavel in colunas_necessarias if variavel not in df.columns
]
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

# Padroniza strings categóricas para que valores como "RAIN" e " Rain " não
# apareçam como opções diferentes nos filtros do Dashboard 2.
for coluna in ["Area_Type", "Dispatch_Priority", "Weather", "Accident_Severity"]:
    df[coluna] = df[coluna].astype("string").str.strip().str.title()

# Converte datas textuais para `datetime.date`, necessário para o intervalo
# selecionável e para a comparação de datas no filtro.
df["Date"] = pd.to_datetime(df["Date"], errors="raise").dt.date

# Duas abas separam os painéis: a primeira mantém o dashboard existente e a
# segunda contém o novo painel de métricas e análises.
aba_dashboard1, aba_dashboard2 = st.tabs(
    ["Dashboard 1 · Distribuição e correlação", "Dashboard 2 · Indicadores"]
)

# ---------------------------------------------------------------------------
# Aba 1: dashboard atual de histogramas e matriz de correlação.
# ---------------------------------------------------------------------------
with aba_dashboard1:
    st.title("Análise de acidentes de trânsito")
    st.caption(
        "Explore a distribuição das variáveis e a correlação entre elas. "
        "Use os filtros ao lado para definir a análise."
    )

    # Os filtros ficam em uma coluna própria desta aba, mantendo o painel
    # independente dos controles do novo dashboard.
    coluna_filtros, coluna_graficos = st.columns([1, 3.5])
    with coluna_filtros:
        st.subheader("Filtros")
        variaveis_selecionadas = st.multiselect(
            "Variáveis para análise",
            options=VARIAVEIS,
            default=VARIAVEIS,
            help="As variáveis selecionadas aparecem nos histogramas e no mapa de correlação.",
            key="dashboard1_variaveis",
        )

        intervalos = {}
        if variaveis_selecionadas:
            st.markdown("**Intervalos**")
            for variavel in variaveis_selecionadas:
                valores_validos = df[variavel].dropna()
                if valores_validos.empty:
                    st.warning(f"A variável {variavel} não possui valores disponíveis.")
                    continue

                minimo = valores_validos.min()
                maximo = valores_validos.max()
                if minimo == maximo:
                    st.caption(f"{variavel}: valor fixo {minimo}")
                    intervalos[variavel] = (minimo, maximo)
                elif pd.api.types.is_integer_dtype(df[variavel]):
                    intervalos[variavel] = st.slider(
                        variavel,
                        min_value=int(minimo),
                        max_value=int(maximo),
                        value=(int(minimo), int(maximo)),
                        step=1,
                        key=f"dashboard1_intervalo_{variavel}",
                    )
                else:
                    minimo_float = float(minimo)
                    maximo_float = float(maximo)
                    intervalos[variavel] = st.slider(
                        variavel,
                        min_value=minimo_float,
                        max_value=maximo_float,
                        value=(minimo_float, maximo_float),
                        step=max((maximo_float - minimo_float) / 100, 0.01),
                        key=f"dashboard1_intervalo_{variavel}",
                    )

    # Todos os intervalos selecionados são aplicados em conjunto.
    df_filtrado = df.copy()
    for variavel, (inicio, fim) in intervalos.items():
        df_filtrado = df_filtrado[df_filtrado[variavel].between(inicio, fim)]

    with coluna_graficos:
        st.caption(
            f"{len(df_filtrado):,} de {len(df):,} registros dentro dos intervalos selecionados."
        )
        coluna_distribuicao, coluna_correlacao = st.columns([1.25, 1])

        # Cada variável selecionada gera seu próprio histograma Altair.
        with coluna_distribuicao:
            st.subheader("Distribuição das variáveis")
            if not variaveis_selecionadas:
                st.info("Selecione ao menos uma variável nos filtros.")
            elif df_filtrado.empty:
                st.warning("Nenhum registro corresponde aos intervalos selecionados.")
            else:
                numero_colunas = 3
                colunas_histogramas = st.columns(numero_colunas)
                for indice, variavel in enumerate(variaveis_selecionadas):
                    grafico = criar_histograma(
                        df_filtrado[[variavel]].dropna(),
                        variavel,
                    )
                    colunas_histogramas[indice % numero_colunas].altair_chart(
                        grafico,
                        width="stretch",
                        alt=f"Distribuição da variável {variavel}",
                    )

        # Heatmap Altair da correlação de Pearson entre variáveis selecionadas.
        with coluna_correlacao:
            st.subheader("Matriz de correlação")
            if len(variaveis_selecionadas) < 2:
                st.info("Selecione ao menos duas variáveis para calcular a correlação.")
            elif df_filtrado.empty:
                st.warning("Nenhum registro corresponde aos intervalos selecionados.")
            else:
                figura_correlacao = criar_mapa_correlacao(
                    df_filtrado[variaveis_selecionadas],
                    tuple(variaveis_selecionadas),
                )
                st.altair_chart(
                    figura_correlacao,
                    width="stretch",
                    alt="Mapa de calor da correlação de Pearson entre as variáveis selecionadas",
                )

# ---------------------------------------------------------------------------
# Aba 2: KPIs e gráficos do rascunho do Dashboard 2.
# ---------------------------------------------------------------------------
with aba_dashboard2:
    st.title("Indicadores de ocorrências de trânsito")
    st.caption(
        "Use os filtros à esquerda para atualizar as métricas e os gráficos."
    )

    coluna_filtros_kpi, coluna_conteudo_kpi = st.columns([1, 3.5])
    with coluna_filtros_kpi:
        st.subheader("Widgets de controle")
        menor_data = min(df["Date"])
        maior_data = max(df["Date"])
        periodo = st.date_input(
            "Data (intervalo)",
            value=(menor_data, maior_data),
            min_value=menor_data,
            max_value=maior_data,
            format="DD/MM/YYYY",
            key="dashboard2_periodo",
        )

        # O controle permite selecionar qualquer subconjunto das categorias.
        areas_disponiveis = sorted(df["Area_Type"].dropna().unique().tolist())
        areas_selecionadas = st.multiselect(
            "Area_Type",
            options=areas_disponiveis,
            default=areas_disponiveis,
            key="dashboard2_areas",
        )
        prioridades_disponiveis = sorted(
            df["Dispatch_Priority"].dropna().unique().tolist()
        )
        prioridades_selecionadas = st.multiselect(
            "Dispatch_Priority",
            options=prioridades_disponiveis,
            default=prioridades_disponiveis,
            key="dashboard2_prioridades",
        )
        climas_disponiveis = sorted(df["Weather"].dropna().unique().tolist())
        climas_selecionados = st.multiselect(
            "Weather",
            options=climas_disponiveis,
            default=climas_disponiveis,
            key="dashboard2_climas",
        )
        severidades_disponiveis = sorted(
            df["Accident_Severity"].dropna().unique().tolist()
        )
        severidades_selecionadas = st.multiselect(
            "Accident_Severity",
            options=severidades_disponiveis,
            default=severidades_disponiveis,
            key="dashboard2_severidades",
        )

    with coluna_conteudo_kpi:
        if not isinstance(periodo, tuple) or len(periodo) != 2:
            st.info("Selecione uma data inicial e uma data final para o período.")
            st.stop()

        data_inicial, data_final = periodo
        if data_inicial > data_final:
            st.warning("A data inicial deve ser anterior à data final.")
            st.stop()

        df_dashboard2 = filtrar_dashboard_kpis(
            df,
            data_inicial,
            data_final,
            tuple(areas_selecionadas),
            tuple(prioridades_selecionadas),
            tuple(climas_selecionados),
            tuple(severidades_selecionadas),
        )
        total_ocorrencias = df_dashboard2["Record_ID"].nunique()
        if total_ocorrencias:
            tempo_medio_resposta = df_dashboard2["Actual_Response_Time_min"].mean()
            desvio_medio_meta = (
                df_dashboard2["Actual_Response_Time_min"]
                - df_dashboard2["Baseline_Expected_Response_Time_min"]
            ).mean()
            taxa_criticos = (
                df_dashboard2["Accident_Severity"].isin(["Severe", "Fatal"]).mean()
                * 100
            )
            tempo_medio_interdicao = df_dashboard2["Road_Closure_Duration_min"].mean()
            valor_tempo_resposta = f"{tempo_medio_resposta:.1f} min"
            valor_desvio_meta = f"{desvio_medio_meta:+.1f} min"
            valor_taxa_criticos = f"{taxa_criticos:.1f}%"
            valor_tempo_interdicao = f"{tempo_medio_interdicao:.1f} min"
        else:
            valor_tempo_resposta = "—"
            valor_desvio_meta = "—"
            valor_taxa_criticos = "—"
            valor_tempo_interdicao = "—"

        st.caption(
            f"{total_ocorrencias:,} ocorrências encontradas com os filtros selecionados."
        )

        # As cinco métricas seguem a justificativa: volume, tempo de resposta,
        # diferença para a meta, proporção crítica e duração da interdição.
        metricas = st.columns(5)
        metricas[0].metric(
            "1 · Total de ocorrências",
            f"{total_ocorrencias:,}",
            border=True,
        )
        metricas[1].metric(
            "2 · Tempo médio de resposta",
            valor_tempo_resposta,
            border=True,
        )
        metricas[2].metric(
            "3 · Desvio médio da meta",
            valor_desvio_meta,
            border=True,
            help="Média do tempo real menos o tempo esperado. Valor positivo indica atraso em relação à meta.",
        )
        metricas[3].metric(
            "4 · Taxa de chamados críticos",
            valor_taxa_criticos,
            border=True,
            help="Percentual de ocorrências classificadas como Severe ou Fatal.",
        )
        metricas[4].metric(
            "5 · Tempo médio de interdição",
            valor_tempo_interdicao,
            border=True,
        )

        if df_dashboard2.empty:
            st.warning("Nenhuma ocorrência corresponde aos filtros selecionados.")
        else:
            # Primeira linha do rascunho: tempo de resposta e comparação
            # entre o tempo esperado e o tempo real.
            coluna_hist_resposta, coluna_scatter = st.columns(2)
            with coluna_hist_resposta:
                st.subheader("Tempo real de resposta por frequência")
                st.altair_chart(
                    criar_histograma_resposta(df_dashboard2),
                    width="stretch",
                    alt="Distribuição das ocorrências por tempo real de resposta",
                )
            with coluna_scatter:
                st.subheader("Tempo esperado versus tempo real")
                st.altair_chart(
                    criar_scatter_resposta(df_dashboard2),
                    width="stretch",
                    alt="Comparação entre o tempo esperado e o tempo real de resposta",
                )

            # Segunda linha do rascunho: participação por área e volume por hora.
            coluna_pizza, coluna_horario = st.columns(2)
            with coluna_pizza:
                st.subheader("Ocorrências por tipo de área")
                st.altair_chart(
                    criar_grafico_area(df_dashboard2),
                    width="stretch",
                    alt="Percentual de ocorrências por tipo de área",
                )
            with coluna_horario:
                st.subheader("Ocorrências por hora do dia")
                st.altair_chart(
                    criar_grafico_horario(df_dashboard2),
                    width="stretch",
                    alt="Quantidade de ocorrências em cada hora do dia",
                )
