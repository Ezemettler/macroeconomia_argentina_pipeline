with source as (

    select * from {{ source('raw', 'raw_bcra_variables') }}

),

renamed as (

    select
        -- Explicit cast ensures DATE type regardless of source changes
        cast(fecha          as date)    as observation_date,
        cast(id_variable    as integer) as variable_id,
        cast(nombre_variable as string) as variable_name,
        cast(valor          as float64) as value

    from source

),

filtered as (

    -- Exclude rows where any key field is null
    select *
    from renamed
    where
        observation_date is not null
        and variable_id  is not null
        and variable_name is not null
        and value         is not null

)

select * from filtered
