# 第8课支持路线

## 先知道今天要交出什么

完成README的两期、三层分析、实算核对、一项替代方案比较与发布判断。起始概览不是完整成果。先自行预计，再读输出；遇到概念查LEARN，卡住再看HINTS。

## 核心概念与原理

一张工单可能有多次接触；主键识别记录，分析单位规定分母。先把接触按工单汇总，再补入工单信息，能同时保留工单等权和接触总量。排班用日期+窗口唯一键，在窗口日层接入，避免随工单或接触重复累计。完整手算在LEARN第3节。

## 基础练习（可信起点）：入门跟做

在学生仓库根运行以下命令，程序和数据均为相对路径。每次输出文件位置后打开该文件核对。

### 第一步：预计并核算两张工单

**动作：** 先算等待2、10分钟以及接触2、3、4、7工作人员分钟。预计展开等待均值及只改去重分母的结果，再运行：

```bash
python3 lesson-08/experiments.py duplication
python3 lesson-08/analysis.py --stage inventory
```

**目的：** 区分工单数、接触数和指标分母。**成功信号：** 打开lesson-08/artifacts/experiment_duplication.json，能逐步解释6、4、8和16各从何来；lesson-08/artifacts/main/inventory.json包含七表、1265导出行和1200编号。**反思：** 对等待数值去重会不会删掉等待恰好相同的不同工单？

### 第二步：核对一条原记录再追加

**动作：** 阅读config.json的冲突规则，写下选择及理由；运行：

```bash
python3 lesson-08/analysis.py --stage clean
```

打开lesson-08/artifacts/main/cleaning_audit.json与lesson-08/artifacts/main/clean_tickets.csv；挑一张第二期有修订或秒单位的工单，回tickets_raw.csv核对最大数值修订、缺失编码和换算。**目的：** 统一单位并保留信息的适用范围。**成功信号：** 两期4800唯一工单；原1265行能分解为保留工单、完全重复与被取代版本。**反思：** 缺等待是否意味着已知办结状态也失效？

### 第三步：先汇总接触再补调查

**动作：** 预计窗口字典连接的行数，运行：

```bash
python3 lesson-08/analysis.py --stage join
```

打开lesson-08/artifacts/main/ticket_contact_summary.csv与lesson-08/artifacts/main/join_audit.json，挑一张多次接触工单，回visits.csv相加工作人员分钟，核对contact_count/contact_minutes。读survey_status_all，区分缺登记、未知邀请、未受邀、受邀无回答和有效评分。**目的：** 让每种测量保留正确单位。**成功信号：** 一个工单一行，汇总前后接触分钟一致，未匹配原因有专列。**反思：** 左连接为何仍需检查右表唯一键？

### 第四步：在三层计算并核对日期

**动作：** 先写等待/办结/满意比例的有效条件，再运行：

```bash
python3 lesson-08/analysis.py --stage indicators
```

打开lesson-08/artifacts/main/ticket_metrics.json、lesson-08/artifacts/main/window_days.csv、lesson-08/artifacts/main/reconciliation.json。挑一个窗口日，复算staff_count×open_hours−absence_hours，再将接触分钟/60；等待分母看served_wait_n，办结分母看completion_n，满意比例分母看response_n。

**目的：** 把对象、分母、日期和单位接到解释上。**成功信号：** 全体接触分钟＝已分配＋未分配；排班键唯一、保留无活动计划日与无计划活动日，未知计划量为空而非0。**反思：** 没有业务输入记录能否证明来源完整？计划工时能否解释个人生产率？

## 入门反思

现在用一句话分别说明等待、工作量、排班是在描述什么对象。说明一个检查通过后仍未解决的问题，例如实际接触窗口没有测量。

## 标准任务（本课应完成）

回README完成标准任务。独立选择一个合理替代规则，不再逐步代选：检查已给的config-alternative.json候选方案，按用途只改window_join或metric_scope之一；先写预计再运行。

```bash
python3 lesson-08/analysis.py --stage indicators --config lesson-08/config-alternative.json --output lesson-08/artifacts/alternative
```

确认该文件存在并已按你选择的规则保存。比较两个目录中的choices_used与ticket_metrics及审计，给出分母、指标差异和采用理由。若差异小，也说明覆盖怎样变；当前结果相近不等于规则等价。正式报告采用的配置要与submission运行命令一致。提交前运行 `python3 lesson-08/reproduce.py`，它重算两份证据；在submission中用该命令才能在删掉结果后的重现检查中生成替代输出。若提交提高实验，run增加 `--experiment revision` 等所选项。

## 提高与拓展（提前完成后）

按EXERCISES选一项新问题，使用experiments.py的unmatched、revision或staffing案例。它们是另设反例，正式数据没有当前最新版本冲突，不能写成发现了真实冲突。提高要求解释规则改变如何影响结论或核对条件。

## 卡住时按顺序排查

1. 先确认根目录含scripts与data，命令使用python3、文件名拼写正确。
2. 看命令退出状态与本次输出目录，不把旧结果存在当作本次成功。
3. JSON用英文双引号、合法选项，不写注释；保留错误信息，别手改输出掩盖错误。
4. 数量不符先查修订、两期ID、字典键和连接范围，不随意删接触。
5. 指标不符查分子/分母/单位；未知状态不是0，空分母为null。
6. 工时不符查contact_date、分钟/60、合计缺勤减一次、窗口日唯一键与报告日期集合。
7. 报告从“用途—规则—预计—结果—差异—建议和条件”写起，无需复制全部输出。

## 提交前自检

原CSV未改；标准两期三层与比较均完成；每项数字有时期/单位/分母和文件；审计能说明差额；submission状态与运行命令对应实际成果；重跑后执行check；检查暂存内容只含本课需要的文件。评分与final保留规则见README。按教师开放的第8课场次完成知识自查。
