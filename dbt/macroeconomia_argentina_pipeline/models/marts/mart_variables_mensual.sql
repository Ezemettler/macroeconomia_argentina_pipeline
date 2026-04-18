with source as (

    select * from {{ ref('stg_bcra_variables') }}

),

-- Rank observations within each (year, month, variable) window, most recent first
ranked as (

    select
        extract(year  from observation_date) as anio,
        extract(month from observation_date) as mes,
        variable_name                        as nombre_variable,
        value,
        row_number() over (
            partition by
                extract(year  from observation_date),
                extract(month from observation_date),
                variable_name
            order by observation_date desc
        ) as row_rank

    from source

),

-- Keep only the last observation of each month per variable (row_rank = 1)
monthly_close as (

    select
        anio,
        mes,
        nombre_variable,
        value as valor_cierre

    from ranked
    where row_rank = 1

)

select * from monthly_close
