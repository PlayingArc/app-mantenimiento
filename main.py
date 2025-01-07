import streamlit as st
import datetime
import pandas as pd
import altair as alt

from base import (data_prep,
                  generar_diagrama_tiempo,
                  generar_diagrama_de_calor,
                  generar_diagrama_de_barras,
                  generar_pie_chart)

# PAGE CONFIG
st.set_page_config(
    page_title = "Reporte de Mantenimiento",
    page_icon = "🏂",
    layout = "wide",
    initial_sidebar_state = "expanded")

alt.themes.enable("dark")

#FILTER IN THE SIDEBAR

with st.sidebar:
    st.title('🗂 Carga de Datos️')
    # Carga de documento
    uploaded_file = st.file_uploader('Datos de reporte "Tareas por trabajador por Orden con costo"', type=['xlsx'])

if uploaded_file is not None:

    data = pd.read_excel(uploaded_file)
    data = data_prep(data)

    with st.sidebar:
        st.divider()
        st.subheader('Generar Reporte')

        meses_legibles = {'Enero' : 1,
                          'Febrero' : 2,
                          'Marzo' : 3,
                          'Abril' : 4,
                          'Mayo' : 5,
                          'Junio' : 6,
                          'Julio' : 7,
                          'Agosto' : 8,
                          'Septiembre' : 9,
                          'Octubre' : 10,
                          'Noviembre' : 11,
                          'Diciembre' : 12}

        mes_de_trabajo = st.selectbox(label = 'El mes de trabajo: ',
                                      options = meses_legibles.keys())

        st.divider()

        st.title('Filtros 📥')

        lista_de_diagramas = ['Diagrama de Area',
                              'Mapa de Calor',
                              'KPIs',
                              'Diagrama de Barras',
                              'Diagrama de Pastel']

        diagramas_seleccionados = st.multiselect(label = 'Diagramas afectados por el filtro: ',
                                                 options = lista_de_diagramas)

        #check for filters
        if diagramas_seleccionados != []:
            diagramas_con_filtro = diagramas_seleccionados
        else:
            diagramas_con_filtro = lista_de_diagramas

        #filtro por tipo de tarea (preventivo o correctivo)
        tipo_de_tarea_seleccionada = st.multiselect(label = 'Tipo de tareas',
                                                    options = ['Preventivo', 'Correctivo'])

        #check for filters
        if tipo_de_tarea_seleccionada != []:
            filtered_data = data[data['tipo_mantenimiento'].isin(tipo_de_tarea_seleccionada)]
        else:
            filtered_data = data

        #fechas minima y maxima dentro del menu
        min_date = datetime.datetime(2024, 1, 1)
        max_date = datetime.date(2044, 12, 31)

        #seleccion de fechas con exception handling (cuando escoge la primera hay error,
        # cuando escoge las dos se aplica el filtro)
        try:
            date_range = st.date_input("Escoge las fechas", (min_date, max_date))
            date_range = pd.date_range(date_range[0], date_range[1])
            filtered_data = filtered_data[filtered_data.fecha_inicial.isin(date_range)]
        except:
            filtered_data = data

        lista_nombre_trabajadores = data.trabajador.unique().tolist()
        trabajadores_selected = st.multiselect(label = 'Selecciona trabajadores',
                                               options = lista_nombre_trabajadores)

        if trabajadores_selected != []:
            filtered_data = filtered_data[filtered_data['trabajador'].isin(trabajadores_selected)]

        st.divider()

        st.title('⚙️ Configuracion de Graficos️')

        #config unidad de tiempo en diagrama de tiempo
        st.subheader("Diagrama de Area")
        timeframes = ['Semana', 'Mes', 'Q', 'Dia']
        timeFrameName = st.selectbox(label = 'Selecciona la escala de tiempo: ',
                                 options = timeframes)
        timeDict = {'Semana': 'week', 'Mes' : 'month', 'Q' : 'quarter', 'Dia': 'dayofyear'}
        timeFrame = timeDict[timeFrameName]

        st.subheader("Diagrama de Pastel")
        st.write('---pendiente por habilitar---')


    #Seleccion del tema
        selected_color_theme = 'reds'

    st.title('Dashboard de Mantenimiento 🔩')
    st.divider()
    col1, col2 = st.columns(2)

    # COLUMNA 1:
    ### DIAGRAMA DE TIEMPO

    if 'Diagrama de Area' in diagramas_con_filtro:
        selected_data = filtered_data
    else:
        selected_data = data

    col1.write("Horas Trabajadas por Fecha")
    # horas de trabajo por fecha
    diagrama_de_tiempo = generar_diagrama_tiempo(selected_data, timeFrame)

    col1.altair_chart(diagrama_de_tiempo,
                      use_container_width = True)

    ### DIAGRAMA DE CALOR

    # revisar filtro en mapa de calor
    if 'Mapa de Calor' in diagramas_con_filtro:
        selected_data = filtered_data
    else:
        selected_data = data
    # creando figura
    heatmap = generar_diagrama_de_calor(selected_data)
    col1.altair_chart(heatmap,
                      use_container_width=True)



    # COLUMNA 2:
    ### DIAGRAMA KPIS

    if 'KPIs' in diagramas_con_filtro:
        selected_data = filtered_data
    else:
        selected_data = data

        # datos del mes anterior
    try:
        mes_anterior = selected_data.query(f'mes == {(meses_legibles[mes_de_trabajo] - 1)}')
    except KeyError:
        mes_anterior = None

    # ahora nos quedamos solo con aquellos del mes de trabajo actual
    selected_data = selected_data.query(f'mes == {(meses_legibles[mes_de_trabajo])}')

    val1 = float((selected_data['tipo_mantenimiento'] == 'PREVENTIVO').sum())
    val2 = float((selected_data['tipo_mantenimiento'] == 'CORRECTIVO').sum())
    val3 = float(selected_data['horas_reales'].sum())

    try:
        # datos del mes anterior
        dif1 = val1 - (mes_anterior['tipo_mantenimiento'] == 'PREVENTIVO').sum()
        dif2 = val2 - (mes_anterior['tipo_mantenimiento'] == 'CORRECTIVO').sum()
        dif3 = round(val3 - mes_anterior['horas_reales'].sum(), 2)

    except:
        dif1 = None
        dif2 = None
        dif3 = None

    kpi1, kpi2, kpi3 = col2.columns(3)

    kpi1.metric(label = "Tareas Preventivas", value = val1, delta = dif1)
    kpi2.metric(label = "Tareas Correctivas", value = val2, delta = dif2)
    kpi3.metric(label = "Horas Totales", value = val3, delta = dif3)

    col2.divider()


    ### DIAGRAMA DE BARRAS
    if 'Diagrama de Barras' in diagramas_con_filtro:
        # datos con filtro arbitrario aplicado
        selected_data = filtered_data
    else:
        selected_data = data

    # ahora nos quedamos solo con aquellos del mes de trabajo actual
    selected_data = selected_data[selected_data['mes'] == meses_legibles[mes_de_trabajo]]

    col2.write('Horas por Trabajador')

    #diagrama de barras
    diagrama_de_barras = generar_diagrama_de_barras(selected_data)
    col2.altair_chart(diagrama_de_barras,
                      use_container_width = True)
    #pie chart
    agg = 'sum'


    ### DIAGRAMA PIE CHART
    if 'Diagrama de Pastel' in diagramas_con_filtro:
        selected_data = filtered_data
    else:
        selected_data = data

    selected_data = selected_data[selected_data['mes'] == meses_legibles[mes_de_trabajo]]

    pie_chart = generar_pie_chart(selected_data, 9)

    col2.write('Incidencias por Tarea')
    col2.altair_chart(pie_chart, use_container_width = True)

    st.divider()
    st.caption('Apoyo visual para análisis de datos de mantenimiento. \nDiseñado para exponer resumen del mes.')