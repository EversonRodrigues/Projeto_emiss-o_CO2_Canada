import pandas as pd
import plotly.express as px
import streamlit as st

from joblib import load

from notebooks.src.config import DADOS_CONSOLIDADOS, DADOS_TRATADOS, MODELO_FINAL

from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)

@st.cache_data
def carregar_dados(arquivo):
    return pd.read_parquet(arquivo)

@st.cache_resource
def carregar_modelo(arquivo):
    return load(arquivo)

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters")

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return df


df_consolidado = carregar_dados(DADOS_CONSOLIDADOS)
df_tratado = carregar_dados(DADOS_TRATADOS)
modelo = carregar_modelo(MODELO_FINAL)

colunas_para_retirar = [
    "co2_rating",
    "smog_rating",
    "combined_mpg",
    "engine_size_l",
    "cylinders",
    "city_l_100_km",
    "highway_l_100_km",
]

df_consolidado = df_consolidado.drop(columns=colunas_para_retirar)

# MODIFICANDO AS ORDENS DAS COLUNAS
df_consolidado = df_consolidado[
    [
        "model_year",
        "make",
        "model",
        "co2_emissions_g_km",
        "fuel_type",
        "vehicle_class",
        "combined_l_100_km",
    ]
]

fuel = {
    "X": "reg_gasoline",
    "Z": "premium_gasoline",
    "E": "ethanol",
    "D": "diesel",
    "N": "natural_gas",
}

# COLOCANDO O COMBUSTIVÉL EM EXTENSO PARA DEIXAR MAIS AMIGAVÉL
df_consolidado["fuel_type"] = df_consolidado["fuel_type"].map(fuel)

aba1,aba2 = st.tabs(["Dados", "Regressão"])

with aba1:

    df_filter = filter_dataframe(df_consolidado)
    st.dataframe(
        df_filter.style.background_gradient(
            subset=["co2_emissions_g_km","combined_l_100_km"],
            cmap="RdYlGn_r",
        )
    )

    cmin, cmax = (
        df_filter["co2_emissions_g_km"].min(),
        df_filter["co2_emissions_g_km"].max(),
    )
    
    fig1 = px.bar(
        df_filter[["make","co2_emissions_g_km"]].groupby("make").mean().reset_index(),
        x="make",
        y="co2_emissions_g_km",
        title="Média de emissão de CO<sub>2</sub> por fabricante (g/km)",
        color="co2_emissions_g_km",
        color_continuous_scale="RdYlGn_r",
        hover_data={"co2_emissions_g_km": ":.2f"},
    )

    fig1.update_xaxes(categoryorder="total descending")

    fig1.data[0].update(marker_cmin= cmin, marker_cmax= cmax)

    fig1.add_hline(
        y=df_filter["co2_emissions_g_km"].mean(),
        line_dash="dot",
        line_color="blue",
    )

    fig1.add_annotation(
        xref="paper",
        x=0.95,
        y=df_filter["co2_emissions_g_km"].mean(),
        text=f"Média: {df_filter["co2_emissions_g_km"].mean():.2f} (g/km)",
        showarrow=False,
        yshift=10,
    )

    st.plotly_chart(fig1)

    fig2 = px.bar(
        df_filter[["vehicle_class","co2_emissions_g_km"]].groupby("vehicle_class").mean().reset_index(),
        x="vehicle_class",
        y="co2_emissions_g_km",
        title="Média de emissão de CO<sub>2</sub> por classe de veículo (g/km)",
        color="co2_emissions_g_km",
        color_continuous_scale="RdYlGn_r",
        hover_data={"co2_emissions_g_km": ":.2f"},
        range_color=[cmin, cmax],
    )

    fig2.update_xaxes(categoryorder="total descending")

    fig2.data[0].update(marker_cmin= cmin, marker_cmax= cmax)

    fig2.add_hline(
        y=df_filter["co2_emissions_g_km"].mean(),
        line_dash="dot",
        line_color="blue",
    )

    fig2.add_annotation(
        xref="paper",
        x=0.95,
        y=df_filter["co2_emissions_g_km"].mean(),
        text=f"Média: {df_filter["co2_emissions_g_km"].mean():.2f} (g/km)",
        showarrow=False,
        yshift=10,
    )

    st.plotly_chart(fig2)

    fig3 = px.bar(
        df_filter[["model_year","co2_emissions_g_km"]].groupby("model_year").mean().reset_index(),
        x="model_year",
        y="co2_emissions_g_km",
        title="Média de emissão de CO<sub>2</sub> por Ano (g/km)",
        color="co2_emissions_g_km",
        color_continuous_scale="RdYlGn_r",
        hover_data={"co2_emissions_g_km": ":.2f"},
        range_color=[cmin, cmax],
    )

    fig3.update_xaxes(categoryorder="total descending")

    fig3.data[0].update(marker_cmin= cmin, marker_cmax= cmax)

    fig3.add_hline(
        y=df_filter["co2_emissions_g_km"].mean(),
        line_dash="dot",
        line_color="blue",
    )

    fig3.add_annotation(
        xref="paper",
        x=0.95,
        y=df_filter["co2_emissions_g_km"].mean(),
        text=f"Média: {df_filter["co2_emissions_g_km"].mean():.2f} (g/km)",
        showarrow=False,
        yshift=10,
    )

    st.plotly_chart(fig3)

    fig4 = px.scatter(
        df_filter,
        x="combined_l_100_km",
        y="co2_emissions_g_km",
        color="fuel_type",
        color_discrete_sequence= px.colors.qualitative.Dark2,
        opacity=0.5,
        title="Emissão de CO<sub>2</sub> X Consumo combinado - Tipo de combustível",
        labels={
            "combined_l_100_km": "Consumo combinado (l/100 km)",
            "co2_emissions_g_km": "Emissão de CO<sub>2</sub> (g/km)"
        }
    )

    fig4.update_layout(
        legend=dict(
            title="Tipo de combustível",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        )
    )

    st.plotly_chart(fig4)

    fig5 = px.scatter(
        df_filter,
        x="combined_l_100_km",
        y="co2_emissions_g_km",
        color="vehicle_class",
        color_discrete_sequence= px.colors.qualitative.Dark24,
        opacity=0.5,
        title="Emissão de CO<sub>2</sub> X Consumo combinado - Classe de veículo",
        labels={
            "combined_l_100_km": "Consumo combinado (l/100 km)",
            "co2_emissions_g_km": "Emissão de CO<sub>2</sub> (g/km)"
        }
    )

    st.plotly_chart(fig5)

    fig6 = px.treemap(
        df_filter,
        path=[
            px.Constant("co2_emissions_g_km"),
            "make",
            "vehicle_class",
            "fuel_type",
            "model_year",
            "model",            
        ],
        color="co2_emissions_g_km",
        color_continuous_scale="RdYlGn_r",
        range_color=[cmin, cmax],
        title="Treemap de emissão de CO<sub>2</sub>",
        labels={
            "co2_emissions_g_km": "Emissão de CO<sub>2</sub> (g/km)",
        },
        hover_data={"co2_emissions_g_km": ":.2f"},
    )

    st.plotly_chart(fig6)
    

with aba2:
    anos = sorted(df_tratado["model_year"].unique())
    transmissao = sorted(df_tratado["transmission"].unique())
    combustivel = sorted(df_tratado["fuel_type"].unique())
    veiculo = sorted(df_tratado["vehicle_class_grouped"].unique())
    tamanho_motor = sorted(df_tratado["engine_size_l_class"].unique())
    cilindros = sorted(df_tratado["cylinders_class"].unique())

    colunas_slider = (
        "city_l_100_km",
        "highway_l_100_km",
        "combined_l_100_km",
    )

    colunas_slider_min_max = {
        coluna:{
            "min_value": df_tratado[coluna].min(),
            "max_value": df_tratado[coluna].max(),
        }
        for coluna in colunas_slider
    }

    with st.form(key="formulario"):

        coluna_esquerda, coluna_direita = st.columns(2)

        with coluna_esquerda:
            widget_ano = st.selectbox("Ano", anos)
            widget_transmissao = st.selectbox("Tramissão", transmissao)
            widget_combustivel = st.selectbox("Combustível", combustivel)

        with coluna_direita:
            widget_veiculo = st.selectbox("Tipo de veículo", veiculo)
            widget_tamanho_motor = st.selectbox("Tamanho do motor", tamanho_motor)
            widget_cilindros = st.selectbox("Cilindros", cilindros)
    
        widget_city = st.slider(
            "Consumo urbano (l/100 km)",
            **colunas_slider_min_max["city_l_100_km"]
        )
    
        widget_highway = st.slider(
            "Consumo estrada (l/100 km)",
            **colunas_slider_min_max["highway_l_100_km"]
        )
    
        widget_combined = st.slider(
            "Consumo combinado (l/100 km)",
            **colunas_slider_min_max["combined_l_100_km"]
        )
        
        botao_previsao = st.form_submit_button("Prever emissão")

    entrada_modelo = {
        "model_year": widget_ano,
        "transmission": widget_transmissao,
        "fuel_type": widget_combustivel,
        "vehicle_class_grouped": widget_veiculo,
        "engine_size_l_class": widget_tamanho_motor,
        "cylinders_class": widget_cilindros,
        "city_l_100_km": widget_city,
        "highway_l_100_km": widget_highway,
        "combined_l_100_km": widget_combined,
    }

    df_entrada_modelo = pd.DataFrame([entrada_modelo])

    if botao_previsao:
        emissao = modelo.predict(df_entrada_modelo)
        st.metric(label="Emissão prevista (g/km)", value=f"{emissao[0]:.2f}")

# link - https://blog.streamlit.io/auto-generate-a-dataframe-filtering-ui-in-streamlit-with-filter_dataframe/