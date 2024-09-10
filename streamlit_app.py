import streamlit as st
import datetime                 #para calendario en filtros de fecha
import pandas as pd             #data proccessing
import altair as alt            #
import re

#PAGE CONFIG
st.set_page_config(
    page_title="Reporte de Mantenimiento",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded")

alt.themes.enable("dark")

#FILTER IN THE SIDEBAR

with st.sidebar:
    st.title('🗂 Carga de Datos️')
    # Carga de documento
    uploaded_file = st.file_uploader('Datos de reporte "Tareas por trabajador por Orden con costo"', type=['xlsx'])

if uploaded_file is not None:

    data = pd.read_excel(uploaded_file)

    def data_prep(data=data):
        # remove blank spaces from strings
        data.columns = data.columns.str.strip()

        # quito espacios en blanco de las columnas string-like
        for col in data.select_dtypes(include=['object']).columns:
            data[col] = data[col].str.strip()

        # borro las columnas que no tienen valores distinguibles
        for col in data.columns:
            unique_values = data[col].unique()
            if len(unique_values) < 2:
                data.drop(col, axis=1, inplace=True)
            elif len(unique_values) == 2 and '' in unique_values or '-' in unique_values:
                data.drop(col, axis=1, inplace=True)

        # tampoco hay info en esta columna
        data.drop('Fechatar', axis=1, inplace=True)

        # indice es la clave de Orden de Trabajo
        data.set_index('Cve_ot', inplace=True)

        # asigno tipos de datos manualmente
        data.Prioridad = data.Prioridad.astype('category')

        # reformatear
        data['Tipo_mant'] = data['Tipo_mant'].map(lambda x: 'Preventivo' if x == 1 else 'Correctivo')

        # data engineering
        data['Mes'] = data.Fec_prog.dt.month
        data['Semana'] = data.Fec_prog.dt.isocalendar().week
        data['Fecha'] = data.Fec_prog
        data['Q'] = data.Fec_prog.dt.quarter
        data['FinDeSemana'] = data.Fec_prog.dt.weekday.map(lambda x: True if x >= 5 else False)

        # columnas redundantes, escogo quedarme con los nombres
        data.drop(columns=['Cve_tipt', 'Cve_equi', 'Paro_rea', 'Cve_tipe', 'Cve_plan', 'Cve_tare'], inplace=True)

        # mas correccion de datatypes
        columns_cat = data.select_dtypes(include=['object', 'category']).columns
        columns_fecha = data.select_dtypes(include=['datetime']).columns
        columns_num = data.select_dtypes(include=['number']).columns

        for col in columns_cat:
            data[col] = data[col].astype('category')

        # solo cambio el orden las columnas as a flex
        data = data[columns_cat.append(columns_num).append(columns_fecha)]

        # diccionario de columns nombres legibles

        mapeo_de_nombres = {'Tipo_mant': 'Tipo',
                            'Nom_tipe': 'Componente',
                            'Nom_plan': 'Zona',
                            'Nom_equi': 'Equipo',
                            'Nom_tare': 'Tarea',
                            'Nom_trab': 'Trabajador',
                            'Esti_hrs': 'Horas Estimadas',
                            'Real_hrs': 'Horas Realizadas',
                            'Costo_hr_': 'Costo por Hora ($/h)',
                            'Totaltare': 'Costo Tarea ($)',
                            'Fec_prog': 'Fecha Programada',
                            'Fec_inic': 'Fecha Inicial',
                            'Fec_term': 'Fecha Final'
                            }

        data.rename(columns=mapeo_de_nombres, inplace=True)
        return data
    # returns cleaned data

    data = data_prep(data)

    with st.sidebar:
        st.divider()

        st.title('Filtros 📥')

        lista_de_diagramas = ['Diagrama de Area',
                              'Mapa de Calor',
                              'Diagrama de Barras',
                              'Gráfico Circular']

        diagramas_seleccionados = st.multiselect('Diagramas afectados por el filtro: ', lista_de_diagramas)

        #check for filters
        if diagramas_seleccionados != []:
            diagramas_con_filtro = diagramas_seleccionados
        else:
            diagramas_con_filtro = lista_de_diagramas

        #filtro por tipo de tarea (preventivo o correctivo)
        tipo_de_tarea_seleccionada = st.multiselect('Tipo de tareas', ['Preventivo', 'Correctivo'])

        #check for filters
        if tipo_de_tarea_seleccionada != []:
            filtered_data = data[data['Tipo'].isin(tipo_de_tarea_seleccionada)]
        else:
            filtered_data = data

        #fechas minima y maxima dentro del menu
        min_date = datetime.datetime(2024, 1, 1)
        max_date = datetime.date(2034, 1, 1)

        #seleccion de fechas con exception handling (cuando escoge la primera hay error,
        # cuando escoge las dos se aplica el filtro)
        try:
            date_range = st.date_input("Escoge las fechas", (min_date, max_date))
            date_range=pd.date_range(date_range[0], date_range[1])
            filtered_data=filtered_data[filtered_data['Fecha Final'].isin(date_range)]
        except:
            filtered_data = data

        lista_nombre_trabajadores=data['Trabajador'].unique()

        trabajadores_selected=st.multiselect('Selecciona trabajadores', lista_nombre_trabajadores)

        if trabajadores_selected != []:
            filtered_data=filtered_data[filtered_data['Trabajador'].isin(trabajadores_selected)]

        st.divider()
        st.title('⚙️ Configuracion de Graficos️')

        st.subheader("Diagrama de Area")

        timeframes = ['Semana', 'Mes', 'Q', 'Fecha']
        timeFrame = st.selectbox('Selecciona la escala de tiempo: ', timeframes)


        st.subheader("Mapa de Calor")
        st.subheader("Diagrama de Barras")
        st.subheader("Gráfico circular")

    #Seleccion del tema
        selected_color_theme = 'reds'
    #st.sidedar --> return filtered_data, selected_color_theme

    #procesamiento de datos
    def datos_por_tipo_de_equipo(data=data):
        # obtener: datos_lineas_produccion
        datos_lineas_produccion = data.copy()

        # la columna "Nom_equip" a veces tiene el patron ".. LINEA (numero de linea)"
        pattern = r"(.+?)\s*LINEA\s*(\d+)"
        datos_lineas_produccion['Linea'] = datos_lineas_produccion['Equipo'].map(
            lambda x:
            int(re.match(pattern, x).group(2))
            if re.match(pattern, x) is not None
            else 0).astype(int)

        datos_lineas_produccion['Componente de Linea'] = datos_lineas_produccion['Equipo'].map(
            lambda x:
            re.match(pattern, x).group(1)
            if re.match(pattern, x) is not None
            else None)

        # solo nos quedamos con las filas relacionadas con las lineas de produccion
        datos_lineas_produccion = datos_lineas_produccion[~datos_lineas_produccion['Componente de Linea'].isna()].drop(
            columns=['Equipo'])

        # ahora columnas se vuelven redundantes
        datos_lineas_produccion['Componente de Linea'] = datos_lineas_produccion['Componente']
        datos_lineas_produccion.drop(columns=['Componente', 'Zona'], inplace=True)

        # linea se guarda como
        datos_lineas_produccion['Linea'] = datos_lineas_produccion['Linea'].astype('category')

        # datos horneados
        datos_horneados = data.query("Zona=='TOSTADA' & ~Equipo.str.contains('AMASA')")
        datos_horneados['Componente de Linea'] = datos_horneados['Componente']
        datos_horneados['Linea'] = datos_horneados['Componente de Linea'].map(lambda x: 'H').astype('category')
        datos_horneados = datos_horneados.drop(columns=['Componente', 'Zona', 'Equipo'])

        # keep the leftovers
        indexed_so_far = list(set(datos_horneados.index) | set(datos_lineas_produccion.index))

        datos_por_linea = pd.concat([datos_lineas_produccion, datos_horneados])

        otros = data.loc[[row for row in data.index if row not in indexed_so_far]]

        return datos_por_linea, otros, {'datos tortilla': datos_lineas_produccion, 'datos horneados': datos_horneados}
    # return datos_por_linea, otros, {'datos tortilla': datos_lineas_produccion, 'datos horneados': datos_horneados}

    st.title('Dashboard de Mantenimiento 🔩')
    st.divider()

    #creates streamlit objects
    col1, col2 = st.columns(2)

    def columna1(col1=col1):
        '''
        :param col1: objeto column de streamlit
        :param selected_color_theme: color global para las figuras
        :return: None
        '''

        #col1.title("Horas de Trabajo")

        if 'Diagrama de Area' in diagramas_con_filtro:
            selected_data = filtered_data
        else:
            selected_data = data

        #horas de trabajo por fecha
        areas_time_plot = alt.Chart(selected_data).mark_area().encode(
            alt.X(f'{timeFrame}:O'),
            alt.Y('sum(Horas Realizadas):Q'),
            alt.Color('Zona:N', scale=alt.Scale(scheme=selected_color_theme))
        ).interactive()
        col1.altair_chart(areas_time_plot, use_container_width=True)

        #revisar filtro en mapa de calor
        if 'Mapa de Calor' in diagramas_con_filtro:
            selected_data = filtered_data
        else:
            selected_data = data
        #creando datos por linea
        datos_linea, otros, datos_TyH = datos_por_tipo_de_equipo(data=selected_data)

        #creando figura
        heatmap = alt.Chart(datos_linea).mark_rect().encode(
            alt.Y('Mes:O'),
            alt.X('Linea:O', sort = list(str(i) for i in range(1, 14)) + ['H']),
            alt.Color('sum(Horas Realizadas):Q', scale=alt.Scale(scheme=selected_color_theme)),
            stroke=alt.value('black'),
            strokeWidth=alt.value(0.25)
        ).interactive()


        col1.altair_chart(heatmap, use_container_width=True)
    #corre script de columna 1, no return

    columna1(col1)

    def columna2(col2 = col2, selected_color_theme=selected_color_theme):
        '''
        :param col2: objeto column de streamlit
        :param selected_color_theme: color global para las figuras
        :return: None
        '''

        #Titulo columna
        #col2.title('Tareas')

        if 'Diagrama de Barras' in diagramas_con_filtro:
            selected_data = filtered_data
        else:
            selected_data = data

        #diagrama de barras
        stacked_bar_chart = alt.Chart(selected_data).mark_bar().encode(
            alt.X('Trabajador:N', title=None, sort='-y'),
            alt.Y('sum(Horas Realizadas):Q', title='Suma de Horas'),
            alt.Color('Trabajador:N',
                      legend=None),
            tooltip=['Trabajador:N', 'sum(Horas Realizadas):Q']
        ).interactive()

        col2.altair_chart(stacked_bar_chart, use_container_width=True)

        #pie chart
        agg = 'sum'

        if 'Gráfico Circular' in diagramas_con_filtro:
            selected_data = filtered_data
        else:
            selected_data = data



        # datos agrupados por tarea
        def make_pie_chart(datos_linea: pd.DataFrame, mostrar_n: int, color='Tarea'):
            datos_pie = datos_linea.groupby(color, observed=False)['Horas Realizadas'].sum().sort_values(
                ascending=False)
            datos_pie = pd.DataFrame({
                color: list(datos_pie.index),
                'Horas Realizadas': datos_pie
            })

            # las tareas no muy comunes se agrupan en 'Otras'
            datos_pie.iloc[mostrar_n, :] = ['Otras', datos_pie.iloc[mostrar_n + 1:, 1].sum()]
            datos_pie = datos_pie.iloc[:mostrar_n + 1, :]
            datos_pie.reset_index(drop=True, inplace=True)

            pie_chart = alt.Chart(datos_pie).mark_arc(innerRadius=50).encode(
                alt.Color(f'{color}:N', sort=datos_pie[color]),
                alt.Theta('Horas Realizadas:Q'),
                tooltip=[f'{color}:N', 'Horas Realizadas']
            ).interactive()
            return pie_chart

        datos_linea, otros, datos_TyH = datos_por_tipo_de_equipo(data=selected_data)
        pie_chart = make_pie_chart(datos_linea, 9)
        col2.altair_chart(pie_chart, use_container_width=True)

    columna2(col2 = col2)
