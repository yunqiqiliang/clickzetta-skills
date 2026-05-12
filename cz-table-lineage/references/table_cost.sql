-- 根据过去 {N} 天的作业运行情况，计算表的产出代价和查询量
with raw as (
    select cru, split(input_objects, ',') as input, split(output_objects, ',') as output
    from information_schema.job_history
    where start_time>=now() - interval {N} day
),
normalized as (
    select cru,
        public.__normalize_objects(input) as input,
        public.__normalize_objects(output) as output    
    from raw
),
as_output (
    select table_name, sum(cru) as dml_cru, count(1) as dml_job_cnt
    from (
        select explode(output) as table_name, cru
        from normalized
        where output is not null and size(output) > 0 -- 有 output 的作业认为是产出作业
    )
    group by table_name
),
as_input (
    select table_name, sum(cru) as query_cru, count(1) as query_job_cnt
    from (
        select explode(input) as table_name, cru
        from normalized
        where output is null or size(output) == 0 -- 没有 output 的作业认为是查询作业
    )
    where not contains(table_name, '__dql__') -- 过滤掉 show tables/pipes 之类查询
        and not starts_with(table_name, 'system_meta_warehouse.information_schema.') -- 过滤掉查询 information_schema
    group by table_name
)
select coalesce(a.table_name, b.table_name) as table_name,
    -- per day
    round(dml_cru / {N}, 3) as dml_cru, dml_job_cnt / {N} as dml_job_cnt,
    round(query_cru / {N}, 3) as query_cru, query_job_cnt / {N} as query_job_cnt
from as_output a full join as_input b on a.table_name = b.table_name
;
