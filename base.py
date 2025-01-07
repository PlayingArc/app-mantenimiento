import pandas as pd
import altair as alt
import re

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
    df['tipo_mantenimiento'] = df['tipo_mantenimiento'].map(lambda x: 'PREVENTIVO' if x == 1 else 'CORRECTIVO')

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
    hm_t = alt.Chart(df).mark_rect().encode(
        alt.Y('month(fecha_inicial):O', title='Mes'),
        alt.X('linea:O', title = 'Linea'),
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
    )

    hm_h = alt.Chart(df).mark_rect().encode(
        alt.Y('month(fecha_inicial):O', title=None),
        alt.X('linea:O', title = 'Linea'),
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
    )

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