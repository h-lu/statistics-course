# 课程数据

以下均为固定种子生成的教学合成数据，不是现实学校、企业或个人的记录。情境约束用于练习统计判断，分析结果不能作为现实机构的事实或政策效果。

- [service](service/README.md)：服务工单、满意度、业务与窗口、排班和接触记录。
- [alerts](alerts/README.md)：设备风险分数、故障标签、设备信息和每日复核容量。
- [inference](inference/README.md)：筛查、需求、抽样框、无回答和统计估计的模拟研究。
- [experiments](experiments/README.md)：实验设计、结果、配对、多指标和逐日观测。
- [prediction](prediction/README.md)：连续结果与风险预测，含时间、实体和变量可用性。
- [policy](policy/README.md)：支持项目的观察性研究数据、政策评估面板数据、时间序列及决策分析资料。

先读各数据字典，确认观测单位、变量含义、观测时间与结果变量。保留原始数据不变，另存清洗后的数据和计算结果。重新生成课程数据的脚本在`scripts/generate_*.py`，分析时通常直接读取已提供的CSV即可。
