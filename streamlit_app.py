import re
import streamlit as st
import datetime
import pandas as pd
import altair as alt
import datetime as dt

def lista_ultimos_seis_meses(today:dt.date):
    ##LISTA DE ULTIMOS 6 MESES EN ORDEN
    ultimos_meses = list()
    for mes in range(0, 6):
        mes_anterior = today.month - 1
        if (mes_anterior - mes) > 0:
            ultimos_meses.append(mes_anterior - mes)
        else:
            ultimos_meses.append(14 - mes)

    return ultimos_meses

def clean_blanks(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Quita los espacios vacios.
    :param df: datos de mantenimiento
    :return: base de sin espacios_vacios
    '''
    df = df.copy()

    # remove blank spaces from strings
    df.columns = df.columns.str.strip()

    # quito espacios en blanco de las columnas string-like
    for col in df.select_dtypes(include=['object']).columns:
        df.loc[:, col] = df[col].astype('string', errors='ignore').str.strip()

    return df

def preprocess_maintenance_data(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Preprocesa los datos del reporte "Tareas Realizadas Por Trabajador Por Orden Con Costo".
    :param df: datos de mantenimiento crudos
    :return: datos de mantenimiento preprocesados
    '''

    df = clean_blanks(df)

    bad_columns = ['Cve_suc',
                   'Paro_cto',
                   'No_req',
                   'Status',
                   'Usuario',
                   'Fec_lec',
                   'Lect_act',
                   'Unid_lec',
                   'Cve_trab',
                   'Cve_cate',
                   'Nom_cate',
                   'Fechatar',
                   'Cve_tipt',
                   'Cve_equi',
                   'Paro_rea',
                   'Cve_tipe',
                   'Cve_plan',
                   'Cve_tare',
                   'Cve_mant',
                   'Cve_fal',
                   'Paro_est',
                   'Cve_turn',
                   'Sal_auto',
                   'Num_resp',
                   'Suc_req']

    df.drop(bad_columns, axis=1, inplace=True)

    # mas correccion de datatypes
    category_cols = df.select_dtypes(include=['object', 'category']).columns
    date_cols = df.select_dtypes(include=['datetime']).columns
    numeric_cols = df.select_dtypes(include=['number']).columns

    for col in category_cols:
        df.loc[:, col] = df[col].astype('category')

    # orden en que quiero mostrar las columnas
    orden_de_cols = category_cols.append(numeric_cols).append(date_cols)

    # solo cambio el orden las columnas as a flex
    df = df[orden_de_cols]
    return df

def match_equipo(x: str):
    categs_equipo = ['ALIMENTADOR',
                     'HORNO',
                     'ENFRIADOR',
                     'AMASADORA',
                     'ESTACIÓN DE FILTRACIÓN',
                     'EMBOLSADORA',
                     'APILADOR']

    check = False
    count = 0
    while check == False and count < len(categs_equipo):
        check = (categs_equipo[count] in x)
        count += 1

    if count < len(categs_equipo) - 1:
        return categs_equipo[count - 1]
    else:
        return 'otro'

def datos_por_lineas(df: pd.DataFrame, columna_equipo='equipo') -> pd.DataFrame:
    '''
    Toma datos preprocesados y realiza operaciones en la columna_equipo para separar el tipo de equipo de la linea.
    :param: df : datos de mantenimiento proprocesados
    '''

    # obtener: datos_lineas_produccion
    df = df.copy()

    # la columna "Nom_equip" casi siempre tiene el patron "(nombre componente) LINEA (numero de linea)"
    pattern = r"(.+?)\s*LINEA\s*(\d+)"

    # con el patron extraigo el num de linea
    df.loc[:, 'linea'] = df[columna_equipo].map(
        lambda x:
        re.match(pattern, x).group(2)
        if re.match(pattern, x) is not None
        else 0)

    sin_linea = df['linea'] == 0
    horneados = df['equipo'].str.contains('TOSTADA')

    df.linea = df.linea.fillna(0)
    df.linea = pd.to_numeric(df.linea, errors='ignore', downcast='integer')
    #df.linea = df.linea.map(lambda x: round(x))
    df.linea = df.linea.astype('object')
    df.loc[sin_linea, 'linea'] = df.loc[sin_linea, 'linea'].astype(str).map(lambda x: 'n/a')
    df.loc[(horneados) & (sin_linea), 'linea'] = df.loc[(horneados) & (sin_linea), 'linea'].astype(str).map(lambda x: 'H')
    df.linea = df.linea.astype(str).astype('category')

    df[columna_equipo] = df[columna_equipo].apply(match_equipo)

    return df

def data_engineering_maintenance_data(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Data engineerning para dashboard de mantenimiento.
    Toma los datos preprocesados y regresa los datos procesados, listos para ser utilizados en el dashboard.
    :param df: datos de mantenimiento preprocesados
    :return:
    '''

    # nombres mas legibles
    nuevos_nombres = {'Tipo_mant': 'tipo_mantenimiento',
                      'Nom_tipe': 'componente',
                      'Nom_plan': 'zona',
                      'Nom_equi': 'equipo',
                      'Nom_tare': 'tarea',
                      'Nom_trab': 'trabajador',
                      'Esti_hrs': 'horas_estimadas',
                      'Real_hrs': 'horas_reales',
                      'Costo_hr_': 'costo_hora',
                      'Totaltare': 'costo_tarea',
                      'Fec_prog': 'fecha_programada',
                      'Fec_inic': 'fecha_inicial',
                      'Fec_term': 'fecha_final',
                      'Cve_ot': 'orden_de_trabajo',
                      'Prioridad': 'prioridad',
                      'Part_tar': 'parte_tarea'}
    df.rename(columns=nuevos_nombres, inplace=True)

    # asigno tipos de datos manualmente
    df.prioridad = df.prioridad.astype('category')
    df['tipo_mantenimiento'] = df['tipo_mantenimiento'].map(lambda x: 'PREVENTIVO' if x == 2 else 'CORRECTIVO')

    # extras de fecha
    df['año'] = df.fecha_programada.dt.year
    df['mes'] = df.fecha_programada.dt.month
    df['semana'] = df.fecha_programada.dt.isocalendar().week
    df['dia'] = df.fecha_programada.dt.day
    df['dia_de_demana'] = df.fecha_programada.dt.dayofweek

    #preferencia
    df['zona'].map(lambda x: 'TORTILLA' if x == 'PRODUCCION' else x)
    df = datos_por_lineas(df, columna_equipo='equipo')

    #tarea resumida por primera pablabra
    df.loc[:, 'tipo_tarea'] = df.tarea.map(lambda x: x.split()[0])

    return df

def data_prep(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Prepara los datos de mantenimiento para ser graficados
    :param df: excel de datos de mantenimiento
    :return: datos preparados
    '''
    df = preprocess_maintenance_data(df)
    df = data_engineering_maintenance_data(df)
    return df

def generar_diagrama_de_calor(df: pd.DataFrame) -> alt.Chart:
    '''
    Toma los datos procesados de mantenimiento para ser graficados
    :param df: datos procesados
    :return: diagrama de calor de mantenimiento
    '''
    first = True
    for year in df['año'].unique():
        if first == True:

            hm_t = alt.Chart(df.query(f"año=={year}")).mark_rect().encode(
                alt.Y('month(fecha_inicial):T', title='Mes'),
                alt.X('linea:O', title = 'Linea', sort=['1','2','3','4','5','6','7','8','9','10','11','12','13']),
                alt.Color(
                    'sum(horas_reales):Q',
                    scale=alt.Scale(scheme='blues'),
                    title='Horas'
                ),
                stroke=alt.value('black'),
                strokeWidth=alt.value(0.25),
                tooltip=alt.Tooltip('sum(horas_reales):Q', )
            ).transform_filter(
                (alt.datum.linea != "H") & (alt.datum.linea != "n/a")
            ).properties(title=str(year))

            hm_h = alt.Chart(df.query(f"año=={year}")).mark_rect().encode(
                alt.Y('month(fecha_inicial):T', title=None),
                alt.X('linea:N', title = 'Linea'),
                alt.Color(
                    'sum(horas_reales):Q',
                    scale=alt.Scale(scheme='reds'),
                    title='Horas'
                ),
                stroke=alt.value('black'),
                strokeWidth=alt.value(0.25),
                tooltip=alt.Tooltip('sum(horas_reales):Q', )
            ).transform_filter(
                alt.datum.linea == "H"
            ).properties(title=str(year))
            first = False

        else:
            hm_t = hm_t.properties(height=150, width=300)
            hm_t = (alt.Chart(df.query(f"año=={year}")).mark_rect().encode(
                alt.Y('month(fecha_inicial):T', title='Mes'),
                alt.X('linea:O', title='Linea',
                      sort=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13']),
                alt.Color(
                    'sum(horas_reales):Q',
                    scale=alt.Scale(scheme='blues'),
                    title='Horas'
                ),
                stroke=alt.value('black'),
                strokeWidth=alt.value(0.25),
                tooltip=alt.Tooltip('sum(horas_reales):Q', )
            ).transform_filter(
                (alt.datum.linea != "H") & (alt.datum.linea != "n/a")
            ).properties(height=150, width=300).properties(title=str(year))
                    & hm_t)

            hm_h = hm_h.properties(height=150)
            hm_h = (alt.Chart(df.query(f"año=={year}")).mark_rect().encode(
                alt.Y('month(fecha_inicial):T', title=None),
                alt.X('linea:N', title='Linea'),
                alt.Color(
                    'sum(horas_reales):Q',
                    scale=alt.Scale(scheme='reds'),
                    title='Horas'
                ),
                stroke=alt.value('black'),
                strokeWidth=alt.value(0.25),
                tooltip=alt.Tooltip('sum(horas_reales):Q', )
            ).transform_filter(
                alt.datum.linea == "H"
            ).properties(height=150).properties(title=str(year))
                    & hm_h)

    # junto los diagramas sin que compartan escala
    heat_correctivos = (hm_t | hm_h).resolve_scale(
        color='independent',  # Make sure y-scales are independent
    )
    return heat_correctivos

def generar_diagrama_tiempo(df: pd.DataFrame, timeFrame: str) -> alt.Chart:
    diagrama_de_tiempo = alt.Chart(df).mark_bar().encode(
        alt.X('fecha_inicial:T',
              timeUnit = timeFrame,
              axis = alt.Axis(format='%B'),
              title = None),
        alt.Y('sum(horas_reales):Q',
              axis = alt.Axis(title = None)),
        alt.Color('zona:N',
                  legend = alt.Legend(orient = 'top'),
                  title = 'Zona'),
    ).interactive()

    return diagrama_de_tiempo

def generar_diagrama_de_barras(df: pd.DataFrame) -> alt.Chart:
    diagra_de_barras = alt.Chart(df).mark_bar().encode(
        alt.Y('trabajador:N', title=None, sort='-x'),
        alt.X('sum(horas_reales):Q', title='Horas Trabajadas'),
        alt.Color('trabajador:N',
                  legend=None),
        tooltip=['trabajador:N', 'sum(horas_reales):Q']
    ).interactive()
    return diagra_de_barras

def generar_pie_chart(df: pd.DataFrame, mostrar_n: int):
    datos_pie = df.groupby('tipo_tarea',
                           observed=False)['horas_reales'].count().sort_values(ascending=False)

    datos_pie = pd.DataFrame({
        'tipo_tarea': list(datos_pie.index),
        'Incidencias': datos_pie
    })

    if mostrar_n < len(datos_pie):
        # las tareas no muy comunes se agrupan en 'Otras'
        datos_pie.iloc[mostrar_n, :] = ['Otras', datos_pie.iloc[mostrar_n + 1:, 1].sum()]
        datos_pie = datos_pie.iloc[:mostrar_n + 1, :]
        datos_pie.reset_index(drop=True, inplace=True)

    pie_chart = alt.Chart(datos_pie).mark_arc(innerRadius=50).encode(
        alt.Color('tipo_tarea:N',
                  sort=datos_pie['tipo_tarea'].tolist(),
                  legend=alt.Legend(orient='left'),
                  title='Tipo de Tarea'),
        alt.Theta('Incidencias:Q',
                  sort=datos_pie['tipo_tarea'].tolist()),
        tooltip=['tipo_tarea:N', 'Incidencias']
    ).interactive()
    return pie_chart

# PAGE CONFIG
st.set_page_config(
    page_title = "Reporte de Mantenimiento",
    page_icon = "🏂",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

alt.themes.enable("dark")

#FILTER IN THE SIDEBAR

with st.sidebar:
    st.title('Carga tus datos 🗂')
    uploaded_file = st.file_uploader('Datos de reporte "Tareas por trabajador por Orden con costo"', type=['xlsx'])

if uploaded_file is not None:
    #PROCESAMIENTO DE DATOS
    data = pd.read_excel(uploaded_file)
    data = data_prep(data)

    ##LISTA DE ULTIMOS 6 MESES EN ORDEN
    fecha_actual = dt.datetime.today().date()
    ultimos_seis_meses = lista_ultimos_seis_meses(fecha_actual)
    st.title('Dashboard de Mantenimiento 🔩')


    #SELECCIONA MES DEL REPORTE
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
        meses_legibles_inv = {v: k for k, v in meses_legibles.items()}

        mes_de_trabajo = st.selectbox(label = 'Mes',
                                      options = [meses_legibles_inv[mes]
                                                 for mes in ultimos_seis_meses])

        ano_de_trabajo = st.selectbox(label='Año',
                                      options=[2025, 2024])
        seis_meses_atras = (dt.date(ano_de_trabajo,
                                   meses_legibles[mes_de_trabajo],
                                   15)
                            - dt.timedelta(days = 30*7))
        data = data.query(f'fecha_programada > "{seis_meses_atras.year}-{seis_meses_atras.month}-01"')

        st.divider()

    with st.expander('Configuración del reporte'):
        st.subheader('Filtros 📥')

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
                                                    options = ['PREVENTIVO', 'CORRECTIVO'])

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

        st.subheader('⚙️ Configuracion de Graficos️')

        #config unidad de tiempo en diagrama de tiempo
        st.markdown("#### Diagrama de Area")
        timeframes = ['Semana', 'Mes', 'Q', 'Dia']
        timeFrameName = st.selectbox(label = 'Selecciona la escala de tiempo: ',
                                 options = timeframes)
        timeDict = {'Semana': 'week', 'Mes' : 'month', 'Q' : 'quarter', 'Dia': 'dayofyear'}
        timeFrame = timeDict[timeFrameName]

    #Seleccion del tema
        selected_color_theme = 'reds'

    #KPIs
    with st._main:
        if 'KPIs' in diagramas_con_filtro:
            selected_data = filtered_data
        else:
            selected_data = data

        # DATOS DEL MES ANTERIOR
        try:
            if meses_legibles[mes_de_trabajo] != 1:
                mes_anterior = selected_data.query(
                    f'mes == {(meses_legibles[mes_de_trabajo] - 1)} & año == {ano_de_trabajo}')
            else:
                mes_anterior = selected_data.query(f'mes == 12 & año == {ano_de_trabajo - 1}')
        except KeyError:
            mes_anterior = None

        # DATOS DEL MES ACTUAL
        selected_data = selected_data.query(f'mes == {(meses_legibles[mes_de_trabajo])} & año == {ano_de_trabajo}')

        val1 = float((selected_data['tipo_mantenimiento'] == 'PREVENTIVO').sum())
        val2 = float((selected_data['tipo_mantenimiento'] == 'CORRECTIVO').sum())
        val3 = float(selected_data['horas_reales'].sum())

        # DIFERENCIA ENTRE MES ANTERIOR Y MES ACTUAL
        try:
            dif1 = val1 - (mes_anterior['tipo_mantenimiento'] == 'PREVENTIVO').sum()
            dif2 = val2 - (mes_anterior['tipo_mantenimiento'] == 'CORRECTIVO').sum()
            dif3 = round(val3 - mes_anterior['horas_reales'].sum(), 2)
        except:
            dif1 = None
            dif2 = None
            dif3 = None

        kpi1, kpi2, kpi3 = st.columns(3)

        kpi1.metric(label="Tareas Preventivas", value=val1, delta=dif1)
        kpi2.metric(label="Tareas Correctivas", value=val2, delta=dif2)
        kpi3.metric(label="Horas Totales", value=val3, delta=dif3)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        # COLUMNA 1:
        ### DIAGRAMA DE TIEMPO

        if 'Diagrama de Area' in diagramas_con_filtro:
            selected_data = filtered_data
        else:
            selected_data = data

        st.write("Horas Trabajadas por Fecha")

        # horas de trabajo por fecha
        diagrama_de_tiempo = generar_diagrama_tiempo(selected_data, timeFrame)

        st.altair_chart(diagrama_de_tiempo,
                          use_container_width = True)

        ### DIAGRAMA DE CALOR

        # revisar filtro en mapa de calor
        if 'Mapa de Calor' in diagramas_con_filtro:
            selected_data = filtered_data
        else:
            selected_data = data
        # creando figura
        heatmap = generar_diagrama_de_calor(selected_data)
        st.altair_chart(heatmap,
                          use_container_width=True)

    # COLUMNA 2:
    with col2:
        ### DIAGRAMA DE BARRAS
        if 'Diagrama de Barras' in diagramas_con_filtro:
            # datos con filtro arbitrario aplicado
            selected_data = filtered_data
        else:
            selected_data = data

        # DATOS DEL MES
        selected_data = selected_data.query(f'mes == {(meses_legibles[mes_de_trabajo])} & año == {ano_de_trabajo}')

        st.write('Horas por Trabajador')
        diagrama_de_barras = generar_diagrama_de_barras(selected_data)
        st.altair_chart(diagrama_de_barras,
                          use_container_width = True)
        #PIE CHART
        agg = 'sum'


        ### DIAGRAMA PIE CHART
        if 'Diagrama de Pastel' in diagramas_con_filtro:
            selected_data = filtered_data
        else:
            selected_data = data

        # ahora nos quedamos solo con aquellos del mes de trabajo actual
        selected_data = selected_data.query(f'mes == {(meses_legibles[mes_de_trabajo])} & año == {ano_de_trabajo}')

        pie_chart = generar_pie_chart(selected_data, 9)

        st.write('Incidencias por Tarea')
        st.altair_chart(pie_chart, use_container_width = True)

    st.divider()

    with st.expander('Top 10 Tareas:'):
        last_thing = data.query(f'mes=={meses_legibles[mes_de_trabajo]}')[
            ['orden_de_trabajo',
             'fecha_programada',
             'costo_tarea',
             'horas_reales',
             'tipo_tarea',
             'zona',
             'equipo',
             'componente',
             'trabajador']].sort_values(
            by=['costo_tarea'],
            ascending=False).head(10)

        st.dataframe(last_thing)
    st.caption('Apoyo visual para análisis de datos de mantenimiento. \nDiseñado para exponer resumen del mes.')
