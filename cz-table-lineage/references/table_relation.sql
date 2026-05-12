-- 根据过去 {N} 天的作业运行情况，构建作业涉及的表的产出血缘关系图
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