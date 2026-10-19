# 第11课操作参考

概念与小例见 [LEARN](LEARN.md)，任务要求见 [README](README.md)。本页按需要查阅。

## 1. 正式调查工具

`sampling_tools.py` 提供以下函数：

|函数|用途|
|---|---|
|`load_frame()`|读取不含需求结果的公开名册|
|`choose_invites(frame, n, seed, mechanism)`|在相应名单内等概率、无放回抽取编号|
|`make_request(frame, mechanism, n, selection_seed, response_seed)`|生成包含邀请编号的方案|
|`write_request(request, path)`|保存方案，返回文件散列；不覆盖旧文件|
|`run_request(request, output_dir)`|生成观测和凭据；使用尚不存在的目录|
|`read_observations(path)`|读回观测，未知需求保持为 `None`|
|`response_mean(rows, group=None)`|计算回答者需求比例；无人回答时返回 `None`|
|`composition_estimate(rows, population_counts)`|按已知组人数调整；缺组时返回 `None`|
|`audit_population(request, output_dir)`|取得回答后核对记录与总体真值|

机制名称为 `register_ordinary` 和 `web_voluntary`；`register_complete` 是可选的理想完整回答对照。

操作顺序：读取名册 → 制定两份方案 → 保存全部方案 → 分别取得回答 → 估计与比较 → 总体审计。自行选择邀请人数和种子，记录理由。需要了解函数参数时，可查看函数帮助或请AI解释接口。

## 2. 输出怎么看

- `request.json`：事先保存的方案。
- `observations.csv`：每个编号的抽样框、邀请、回答状态和观察结果。
- `receipt.json`：实际邀请数、回答数及文件散列，用来核对一次运行的文件是否对应。

追踪一个编号时，依次看 `in_frame`、`invited`、`answered` 和 `observed_need`。CSV空白读回后是 `None`；明确的0表示回答没有需求。完整字段见 [数据说明](data/README.md)。

起点程序输出 `example.json`，其中 `formal_acquisition_run=false` 表示它运行的是100人小例。正式结果由上述调查工具生成。

## 3. 常见问题

|现象|检查方法|
|---|---|
|名册人数不对|应有4000个唯一编号，A/B人数3200/800，网上名单3305人；核对输入路径和文件版本|
|邀请数或回答数异常|邀请数应等于请求的n，每人最多一次，回答数不超过邀请数|
|构成调整结果为空|检查是否有组无人回答；缺少组内比例时保留未知|
|提示输出目录已存在|换一个新目录运行，保留原结果|
|提示方案或观测已改变|对照 `request.json` 和 `receipt.json`，确认没有混用不同运行的文件|

## 4. 提交前核对

报告、运行命令和输出文件应对应同一组实验。使用新情境或改变回答规则时，在报告中说明；原始人口CSV保持不变。重复模拟用于观察已定方案的波动，第一次方案与事后修订分别记录。
