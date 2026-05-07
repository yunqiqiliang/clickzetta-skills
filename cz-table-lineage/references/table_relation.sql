CREATE OR REPLACE FUNCTION public.__normalize_table(t STRING) 
RETURNS STRING
RETURN case when contains(t, '__delta__') or contains(t, '__incr__') then NULL -- remove delta/incr tables
    when contains(t, '__DIRECTORY__EXTERNAL__') then NULL -- show volume directory
    when contains(t, '_$kafka$_') then regexp_replace(t, r'([\w\.\-]+)_\$kafka\$_\w+$', r'KAFKA.$1') -- kafka pipe
    when t rlike r'_t_\w{32}$' then regexp_replace(t, r'([\w\.]+)_t_\w{32}$', r'VOLUME.$1') -- volume
    else t -- as it is
    end
;

CREATE OR REPLACE FUNCTION public.__normalize_objects(ts ARRAY<STRING>) 
RETURNS ARRAY<STRING>
RETURN TRANSFORM(FILTER(ts, x -> x is not null and x != ''), x -> public.__normalize_table(x))
;

-- 根据过去 24 小时的作业运行情况，构建作业涉及的表的产出血缘关系图
with raw as (
    select split(input_objects, ',') as input, split(output_objects, ',') as output
    from information_schema.job_history
    where start_time>=now() - interval {N} day
        and output_objects is not null
        and job_type != 'COMPACTION_JOB' -- 去掉 compaction 作业，对构建血缘关系是干扰项
),
normalized as (
    select public.__normalize_objects(input) as input,
        public.__normalize_objects(output) as output
    from raw
),
exploded (
    select table_name, explode(input) as upstream 
    from (
        select explode(output) as table_name, input
        from normalized
    )
)
select table_name, upstream
from exploded
where table_name is not null and  table_name != '' and upstream is not null and upstream != ''
group by table_name, upstream
;