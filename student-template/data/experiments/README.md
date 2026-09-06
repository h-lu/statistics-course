# 随机实验与比较：合成数据说明

**全部数据是教学合成数据，不代表真实员工、教学效果或产品效果。** 生成命令：`python scripts/generate_experiments.py`；主种子20260915，区组内团队分配种子1501。原始CSV不手改。

| 文件 | 观测单位及字段 | 重要说明 |
|---|---|---|
| experiment_roster.csv | 480名参与者；person_id；team共24个团队、每队20人；block共4区组；baseline_minutes基线处理时间分钟；workload工作量指数 | L15设计材料；名单不含分组和实验后结果；团队内成员共享方法，须考虑污染 |
| experiment_outcomes.csv | 每人一行；assigned_arm=tool/usual；received_tool实际使用0/1；followup_observed0/1；followup_minutes随访分钟（未观察留空）；implementation_cost工具组每人8货币单位 | L16实施结果；实际按团队随机，每区组6队中3队tool；不得把480人当480个独立随机化单位；实际使用与失访发生在分配后 |
| paired_study.csv | 每人两行，共60人；sequence=AB/BA；period=1/2；method=A/B；minutes | 合成数据采用预置平衡序列，各30人；同一人两次测量相关；讨论时期效应与残留效应，平衡本身不证明随机分配 |
| independent_comparison.csv | 100名不同参与者；person_id；arm=A/B；minutes | 独立两组，各50人；不能与配对研究混合冒充同一实验 |
| repeated_measurements.csv | 48人×6周；person_id；arm=tool/usual；week；minutes | 合成数据采用预置平衡分组，每人只属于一组，6行不是6个独立人；不是实际随机分配日志 |
| experiment_metrics.csv | 每人每指标一行，480×12；person_id、team、assigned_arm、metric、value | 合成的完整指标面板，与L16有失访的主要分析数据不同，是单独用于L19的完整数据集；不可拿它为L16补回未观测值 |
| metric_plan.csv | 指标单位/用途；family=primary/safety/exploratory；desirable_direction；practical_threshold | 处理时间、培训/返工为分钟；error_rate为0—1比例；output/handoff/escalations为计数指标；其余0—100量表分。practical_threshold表示值得关注的差异大小，不代表自动安全通过 |
| experiment_costs.csv | item、value、unit | L18：预算12000，启动600，每人18，每团队100，每队20人；最小有实际意义的改善3分钟；L16价值换算每分钟2 |
| daily_experiment.csv | 一天的一组新参与者；day=1…30；arm；n_assigned每天每组40；n_observed；conversions | 每天是新个体，无跨天重复；conversions只包含观测到的人，未观察者的真实结局未知；分析中区分完整案例转化率与“分配后被确认转化”复合结局 |

L15实验设计任务：为处理时间改进工具设计可信、可执行的随机实验，预先说明主要目标量、随机化单位、分层或区组安排、组间污染、失访、停止与实施成本。可以提出个体或团队方案，但必须解释后果；团队之间仍可能交流。

L16实施说明：四个区组内各随机抽3队使用工具，其余常规。实际分配采用固定种子1501、按团队名排序后逐区组打乱。评价应按分配分析（意向性分析原则），保留全部随机化名单；缺失结果仍需额外假设。L15若提出其他设计，先说明实际实施与原方案的差异，不声称实验按自己的方案执行。处理时间更低为改善。

L17三份比较数据分别代表交叉配对、独立两组和同一参与者的重复测量，不能互相拼接。它们的组别/顺序为合成平衡布局，用于练习比较结构，不证明真实随机分配；分组差可描述关联，若作随机实验的因果解释还需另有分配机制与设计假设。L18可复用L16的团队变异与依从性信息作为规划输入；样本中的这些数值有不确定性。

L19主指标预先指定处理时间，两个安全指标为错误率和质量分；其余用于探索。应预先说明哪些分析结论构成一个多重检验族、校正目标以及哪些结果仅能生成后续假设。指标面板整体相关，不能把12列视为12次独立研究。

L20推广团队每天查看结果，但最终要选一种预先可执行的停止规则。应按时间顺序用30天数据模拟执行规则、比较固定终点和提前停止的错误率及时间成本。日序可能含共同环境变化，缺失比例组间不同；给出“已确认转化”与真实转化效应的区别。合成数据没有赋予学生额外的真实因果结论。
