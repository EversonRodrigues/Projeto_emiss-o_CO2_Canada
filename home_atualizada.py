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

# ============================
# Funções utilitárias
# ============================

@st.cache_data
def carregar_dados(arquivo):
    return pd.read_parquet(arquivo)

@st.cache_resource
def carregar_modelo(arquivo):
    return load(arquivo)

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Interface interativa para filtragem de dataframe no Streamlit."""
    modify = st.checkbox("🔍 Adicionar filtros")
    if not modify:
        return df
    df = df.copy()
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)
    with st.container():
        to_filter_columns = st.multiselect("Colunas para filtrar", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                options = right.multiselect(f"{column}", df[column].unique(), default=list(df[column].unique()))
                df = df[df[column].isin(options)]
            elif is_numeric_dtype(df[column]):
                _min, _max = float(df[column].min()), float(df[column].max())
                step = (_max - _min) / 100
                values = right.slider(f"{column}", min_value=_min, max_value=_max, value=(_min, _max), step=step)
                df = df[df[column].between(*values)]
            elif is_datetime64_any_dtype(df[column]):
                dates = right.date_input(f"{column}", value=(df[column].min(), df[column].max()))
                if len(dates) == 2:
                    df = df.loc[df[column].between(*map(pd.to_datetime, dates))]
            else:
                text = right.text_input(f"{column} (texto ou regex)")
                if text:
                    df = df[df[column].astype(str).str.contains(text)]
    return df

def plot_bar(df, x, y, titulo, cmin, cmax):
    fig = px.bar(
        df.groupby(x)[y].mean().reset_index(),
        x=x, y=y,
        title=titulo.replace("CO2", "CO\u2082"),
        color=y,
        color_continuous_scale="RdYlGn_r",
        hover_data={y: ":.2f"},
        range_color=[cmin, cmax],
    )
    fig.update_layout(template="plotly_white", title_x=0.5)
    fig.update_xaxes(categoryorder="total descending")
    fig.add_hline(y=df[y].mean(), line_dash="dot", line_color="blue")
    fig.add_annotation(
        xref="paper", x=0.95, y=df[y].mean(),
        text=f"Média: {df[y].mean():.2f} (g/km)", showarrow=False, yshift=10
    )
    return fig

def plot_scatter(df, x, y, color, titulo, legenda):
    fig = px.scatter(
        df, x=x, y=y, color=color,
        opacity=0.5,
        title=titulo.replace("CO2", "CO\u2082"),
        labels={k: v.replace("CO2", "CO\u2082") for k, v in legenda.items()},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(
        template="plotly_white",
        title_x=0.5,
        margin=dict(t=80, b=50),
        legend=dict(
            title=color,
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
    )
    return fig


def plot_treemap(df, cmin, cmax):
    fig = px.treemap(
        df,
        path=[px.Constant("CO\u2082"), "make", "vehicle_class", "fuel_type", "model_year", "model"],
        color="co2_emissions_g_km",
        color_continuous_scale="RdYlGn_r",
        range_color=[cmin, cmax],
        title="Treemap de emissão de CO\u2082",
        labels={"co2_emissions_g_km": "Emissão de CO\u2082 (g/km)"},
        hover_data={"co2_emissions_g_km": ":.2f"},
    )
    return fig

# ============================
# Carregamento de dados
# ============================

df_consolidado = carregar_dados(DADOS_CONSOLIDADOS)
df_tratado = carregar_dados(DADOS_TRATADOS)
modelo = carregar_modelo(MODELO_FINAL)

colunas_para_retirar = [
    "co2_rating", "smog_rating", "combined_mpg",
    "engine_size_l", "cylinders", "city_l_100_km", "highway_l_100_km"
]
df_consolidado = df_consolidado.drop(columns=colunas_para_retirar)
df_consolidado = df_consolidado[["model_year", "make", "model", "co2_emissions_g_km", "fuel_type", "vehicle_class", "combined_l_100_km"]]

fuel = {"X": "reg_gasoline", "Z": "premium_gasoline", "E": "ethanol", "D": "diesel", "N": "natural_gas"}
df_consolidado["fuel_type"] = df_consolidado["fuel_type"].map(fuel)

# ============================
# Interface
# ============================

aba1, aba2 = st.tabs(["📊 Visualização de Dados", "🧠 Previsão de Emissão CO2"])

with aba1:
    st.subheader("📂 Base de Dados")
    df_filter = filter_dataframe(df_consolidado)
    st.dataframe(df_filter.style.background_gradient(subset=["co2_emissions_g_km", "combined_l_100_km"], cmap="RdYlGn_r"))

    cmin, cmax = df_filter["co2_emissions_g_km"].min(), df_filter["co2_emissions_g_km"].max()

    with st.expander("📈 Gráficos de Barras"):
        st.plotly_chart(plot_bar(df_filter, "make", "co2_emissions_g_km", "Emissão por Fabricante", cmin, cmax))
        st.plotly_chart(plot_bar(df_filter, "vehicle_class", "co2_emissions_g_km", "Emissão por Classe de Veículo", cmin, cmax))
        st.plotly_chart(plot_bar(df_filter, "model_year", "co2_emissions_g_km", "Emissão por Ano", cmin, cmax))

    with st.expander("📉 Gráficos de Dispersão"):
        st.plotly_chart(plot_scatter(
            df_filter, "combined_l_100_km", "co2_emissions_g_km", "fuel_type",
            "Emissão vs Consumo por Combustível",
            {"combined_l_100_km": "Consumo (l/100 km)", "co2_emissions_g_km": "Emissão (g/km)"}
        ))
        st.plotly_chart(plot_scatter(
            df_filter, "combined_l_100_km", "co2_emissions_g_km", "vehicle_class",
            "Emissão vs Consumo por Classe de Veículo",
            {"combined_l_100_km": "Consumo (l/100 km)", "co2_emissions_g_km": "Emissão (g/km)"}
        ))

    with st.expander("🗺️ Treemap"):
        st.plotly_chart(plot_treemap(df_filter, cmin, cmax))

with aba2:
    st.subheader("⚙️ Previsão de Emissão CO2")
    anos = sorted(df_tratado["model_year"].unique())
    transmissao = sorted(df_tratado["transmission"].unique())
    combustivel = sorted(df_tratado["fuel_type"].unique())
    veiculo = sorted(df_tratado["vehicle_class_grouped"].unique())
    tamanho_motor = sorted(df_tratado["engine_size_l_class"].unique())
    cilindros = sorted(df_tratado["cylinders_class"].unique())

    colunas_slider = ("city_l_100_km", "highway_l_100_km", "combined_l_100_km")
    colunas_slider_min_max = {
        coluna: {
            "min_value": df_tratado[coluna].min(),
            "max_value": df_tratado[coluna].max(),
        } for coluna in colunas_slider
    }

    with st.form(key="formulario"):
        col1, col2 = st.columns(2)
        with col1:
            widget_ano = st.selectbox("Ano", anos)
            widget_transmissao = st.selectbox("Transmissão", transmissao)
            widget_combustivel = st.selectbox("Combustível", combustivel)
        with col2:
            widget_veiculo = st.selectbox("Tipo de veículo", veiculo)
            widget_tamanho_motor = st.selectbox("Tamanho do motor", tamanho_motor)
            widget_cilindros = st.selectbox("Cilindros", cilindros)
        widget_city = st.slider("Consumo urbano (l/100 km)", **colunas_slider_min_max["city_l_100_km"])
        widget_highway = st.slider("Consumo estrada (l/100 km)", **colunas_slider_min_max["highway_l_100_km"])
        widget_combined = st.slider("Consumo combinado (l/100 km)", **colunas_slider_min_max["combined_l_100_km"])
        botao_previsao = st.form_submit_button("🚗 Prever emissão CO2")

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
        with st.spinner("Calculando emissão CO2..."):
            emissao = modelo.predict(df_entrada_modelo)
            st.metric(label="📏 Emissão CO2 prevista (g/km)", value=f"{emissao[0]:.2f}")
