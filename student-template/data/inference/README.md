# 推断与调查：合成数据说明

**这里全部是固定种子生成的教学合成数据，不是真实学校调查、医疗筛查或业务数据。** 筛查采用设备质量复核情境，不用于个人医疗建议。再生成：在仓库根运行 `python scripts/generate_inference.py`。种子20260909；重跑会恢复原始教学数据，分析不得手改这些CSV。

| 文件 | 每行描述什么 | 关键字段与单位 | 用途与局限 |
|---|---|---|---|
| screening_groups.csv | 一个设备来源组 | group；daily_volume每日台数；base_rate及low/high为故障基础率情境；review_minutes每台12分钟；missed_case_loss漏掉一台故障的损失；unnecessary_review_loss不必要复核损失 | 三个基础率是规划假设及范围，不是现场已证实的真值 |
| screening_validation.csv | 一个组的一种初筛方法的历史验证汇总 | condition_positive_n真实故障台数、true_positive_n检出数；condition_negative_n真实正常台数、true_negative_n正确排除数；test_cost每台初筛费用 | 验证集故障比例由验证抽样设定，不能当现场基础率；rapid/precise是备选初筛，不提供联合检验数据 |
| demand_history.csv | 一天 | day时间序号；weekday=0…6；event、rain为0/1；requests全天真实需求件数；split=history或holdout | 前126天用于选方案，末42天留作评估；包含过度离散和活动冲击，未来机制不保证不变 |
| capacity_options.csv | 一个可购买的日容量方案 | capacity件/日；daily_fixed_cost、unused_unit_cost、unserved_unit_loss均为同一虚拟货币单位 | 未服务损失可作敏感性分析；不含排队动态或跨日积压 |
| population_frame.csv | 抽样框内一人 | person_id唯一；campus、stage、stratum分层；baseline_score已知辅助分数0—100；responded是否自愿答复 | 3600人是本次明确目标总体；不代表其他院校或以后入学者 |
| voluntary_survey.csv | 一个已回答者 | person_id连接框；satisfaction满意度0—100；weekly_use每周次数 | 未回答者满意度不可见；参与机制在层内仍可能与满意度有关，加权不能自动消除 |
| sampling_costs.csv | 一个抽样层 | population_n人数；contact_cost联系一人成本；expected_response_rate规划回答率；min_completed最低完成数 | 用于L14新一轮概率抽样；回答率和已回答者标准差是设计输入而非保证 |
| estimation_populations.csv | 一个可反复抽样的有限总体单位 | unit_id；scenario=symmetric/long_tail/rare_cost；cost每次成本，同一虚拟货币单位 | 每情境6000人；本课允许计算全总体基准，真实调查通常没有这个便利 |
| decision_sample.csv | 从long_tail总体随机抽出的80条记录 | sample_id；source_id可复核来源；cost | L13行动分析先只用本文件；总体文件仅用于区间覆盖率模拟，不用于替代对80条样本的分析 |

筛查任务：一天最多复核1440分钟（120台），初筛费用预算4500，三个来源组都须提供服务；可以比较分组初筛、不同复核优先顺序及随机抽取。复核视为最终准确确认，是简化假设。所有损失和费用使用同一教学货币单位。不能把两种初筛的边际敏感度相乘假设独立。

需求分析任务：从容量方案中给出常态及已知活动日安排；检验历史选择在留出期的成本、未服务风险和稳健性。自行明确是风险中性成本最小，还是接受更高成本以限制尾部损失。

调查中未提供所需回答的情况称为无回答（也称无应答或非响应），不同于将答案记录为0。

调查任务：是否推广满意度改进方案，以目标总体平均满意度和低满意度人群为关注对象。L11评估当前自愿调查；L14设计预算6000的新一轮抽样，并比较预算4500或7500。不得以已知回答者代替完整抽样框抽样。

L12把各完整有限总体均值作为蒙特卡洛基准。L13管理者正在比较平均每次成本是否高于45：选择采取成本控制、有限试点或继续收集信息，说明阈值依据和区间支持程度。样本来自教学有限总体；仿真结论只适用于所检查的总体与抽样设计。

合成机制包括分组基础率差异、时段需求冲击、自愿回答选择以及不同尾部。这些设定是数据制作说明，不自动成为学生已从观察数据识别出的因果机制。
