---
name: cz-table-lineage
description: |
  表血缘可视化工具。从 ClickZetta information_schema.job_history 获取表依赖关系和成本数据，
  导出 CSV 后嵌入 HTML 模板生成交互式血缘图。
  当用户说"表血缘"、"table lineage"、"依赖关系图"、"数据流向"、"上下游分析"、
  "血缘可视化"、"pipeline 可视化"时触发。
---

# 表血缘可视化工作流

## 参考文件

| 文件 | 说明 |
|------|------|
| `references/table_relation.sql` | UDF 定义 + 表关系查询 SQL |
| `references/table_cost.sql` | UDF 定义 + 表成本查询 SQL |
| `references/table_lineage_standalone.html` | 可视化 HTML 模板 |

## 指令

### 步骤 0：确定时间范围

询问用户需要分析多长时间的血缘数据。默认 1 天。用户可指定天数如 1、7、30 等。
SQL 中的 `interval 30 day` 替换为用户指定的天数，成本 SQL 中的除数也同步替换。

### 步骤 1：创建归一化 UDF

读取 `references/table_relation.sql` 开头的两个 `CREATE OR REPLACE FUNCTION` 语句，通过 cz-cli 执行（已存在则跳过）。

### 步骤 2：导出表关系数据

读取 `references/table_relation.sql` 中的查询 SQL，将 `interval` 天数替换为用户指定值，通过 cz-cli 执行，将结果保存为 `table_relation.csv`。

### 步骤 3：导出表成本数据

读取 `references/table_cost.sql` 中的查询 SQL，将 `interval` 天数和除数替换为用户指定值，通过 cz-cli 执行，将结果保存为 `table_cost.csv`。

### 步骤 4：生成可视化页面

1. 读取 `references/table_lineage_standalone.html` 作为模板
2. 找到注释 `<!-- Data injection point` 所在行，在其**后面**插入：

```html
<script>
window.LINEAGE_DATA = {
  relation: `...table_relation.csv 原始文本...`,
  cost: `...table_cost.csv 原始文本...`
};
</script>
```

3. 将结果写入目标文件（如 `table_lineage.html`），用浏览器打开。

页面检测到 `window.LINEAGE_DATA` 后自动渲染，跳过文件选择。

### 步骤 5：引导用户使用可视化功能

- **点击节点**：高亮上游（橙色）和下游（青色）完整依赖路径
- **搜索**：顶部搜索框过滤表名（快捷键 `/` 或 `Cmd+K`）
- **缩放/平移**：鼠标滚轮缩放，拖拽平移，`F` 键适配屏幕
- **右下角小地图**：点击或拖拽快速导航
- **主题切换**：支持亮色/暗色主题
- **悬停查看详情**：DML CRU/day、累计成本、查询成本等指标

## 平台特有知识

- `information_schema.job_history` 的 `input_objects` 和 `output_objects` 是逗号分隔的表名列表
- 归一化通过 UDF `public.__normalize_table` 和 `public.__normalize_objects` 完成，首次使用需创建
- Kafka 源表名格式：`xxx_$kafka$_yyy`，归一化为 `KAFKA.xxx`
- Volume 源表名格式：`xxx_t_<32位hash>`，归一化为 `VOLUME.xxx`
- `__delta__`、`__incr__`、`__DIRECTORY__EXTERNAL__` 中间表/目录被过滤
- `COMPACTION_JOB` 类型作业不参与血缘构建
- 有 output 的作业视为产出作业（DML），无 output 的视为查询作业
- 成本数据为日均值：总量除以查询天数

## 故障排除

可视化为空
原因：CSV 文件格式不正确或无有效数据行
解决方案：确认 CSV 有正确的表头（table_name,upstream），且 upstream 列不全为空

节点过多导致卡顿
原因：浏览器渲染大量 DOM 节点
解决方案：在 SQL 查询中添加 schema 过滤条件，缩小分析范围

查询 job_history 超时
原因：数据量过大
解决方案：缩短时间窗口，如 `interval 30 day` 改为 `interval 1 day`
