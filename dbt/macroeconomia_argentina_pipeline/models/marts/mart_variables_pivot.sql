with monthly as (

    select * from {{ ref('mart_variables_mensual') }}

),

pivoted as (

    select
        anio,
        mes,
        -- Construct first day of the month as a proper DATE for time series analysis
        date(anio, mes, 1)                                                                      as fecha_mes,
        max(case when nombre_variable = 'tipo_cambio_minorista'     then valor_cierre end)      as tipo_cambio_minorista,
        max(case when nombre_variable = 'inflacion_mensual'         then valor_cierre end)      as inflacion_mensual,
        max(case when nombre_variable = 'inflacion_interanual'      then valor_cierre end)      as inflacion_interanual,
        max(case when nombre_variable = 'reservas_internacionales'  then valor_cierre end)      as reservas_internacionales,
        max(case when nombre_variable = 'base_monetaria'            then valor_cierre end)      as base_monetaria,
        max(case when nombre_variable = 'tasa_prestamos_personales' then valor_cierre end)      as tasa_prestamos_personales,
        max(case when nombre_variable = 'prestamos_sector_privado'  then valor_cierre end)      as prestamos_sector_privado,
        max(case when nombre_variable = 'variacion_m2_privado'      then valor_cierre end)      as variacion_m2_privado,
        max(case when nombre_variable = 'uva'                       then valor_cierre end)      as uva

    from monthly
    group by anio, mes

),

with_lag as (

    select
        *,
        lag(tipo_cambio_minorista)    over (order by fecha_mes) as tipo_cambio_mes_anterior,
        lag(prestamos_sector_privado) over (order by fecha_mes) as credito_mes_anterior,
        lag(uva)                      over (order by fecha_mes) as uva_mes_anterior,
        lag(base_monetaria)           over (order by fecha_mes) as base_monetaria_mes_anterior

    from pivoted

),

-- Aggregate multiple events in the same month into a single string
eventos_por_mes as (

    select
        date_trunc(date(fecha), month)          as fecha_mes,
        string_agg(evento, ' | ' order by fecha) as evento

    from {{ ref('eventos_politicos') }}
    group by 1

)

select
    anio,
    mes,
    fecha_mes,
    -- Presidential terms based on inauguration dates
    case
        when fecha_mes >= '2023-12-01' then 'J. Milei'
        when fecha_mes >= '2019-12-01' then 'A. Fernandez'
        when fecha_mes >= '2015-12-01' then 'M. Macri'
        when fecha_mes >= '2007-12-01' then 'CFK'
        when fecha_mes >= '2003-05-01' then 'N. Kirchner'
    end                              as gobierno,
    tipo_cambio_minorista,
    -- NULL when either current or previous month has no data
    round(
        (tipo_cambio_minorista - tipo_cambio_mes_anterior) / tipo_cambio_mes_anterior * 100,
        2
    )                                as variacion_mensual_dolar,
    inflacion_mensual,
    inflacion_interanual,
    reservas_internacionales,
    base_monetaria,
    tasa_prestamos_personales,
    prestamos_sector_privado,
    round(
        (prestamos_sector_privado - credito_mes_anterior) / credito_mes_anterior * 100,
        2
    )                                as variacion_mensual_credito,
    variacion_m2_privado,
    uva,
    round(
        (uva - uva_mes_anterior) / uva_mes_anterior * 100,
        2
    )                                as variacion_mensual_uva,
    round(
        (base_monetaria - base_monetaria_mes_anterior) / base_monetaria_mes_anterior * 100,
        2
    )                                as variacion_mensual_base_monetaria,
    e.evento

from with_lag
left join eventos_por_mes e using (fecha_mes)
where fecha_mes >= '2003-05-01'
order by anio, mes
