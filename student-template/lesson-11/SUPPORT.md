# 第11课操作参考：完成一次调查比较

下面从名册开始，取得两份回答，再读记录、计算和解释。固定示范用于核对操作；自己的标准任务仍需事先选定规模、形成判断和建议。所有命令在学生仓库根目录运行，只需Python标准库。

## 1. 先分清输入与回答

打开 `lesson-11/data/frame.csv` 和 `strata.csv`，按[数据说明](data/README.md)读前几行。名册告诉我们可以邀请谁，没有需求结果。若尚未运行基础小例：

```sh
python3 scripts/course_l11.py start 11
python3 scripts/course_l11.py run 11
```

默认 `analysis.py` 只核对100人小例，结果为70%、58%、82%，输出在 `artifacts/example.json`。下面才在固定4000人总体上真正发出模拟邀请。

## 2. 固定示范：先保存两份方案，再取得回答

这次事先固定：两种方式各邀请200人，邀请种子11、回答种子11。运行：

```sh
python3 lesson-11/survey_example.py survey --n 200 --selection-seed 11 --response-seed 11 --output lesson-11/artifacts/demo-200
```

`survey_example.py` 组合了已有调查工具：读取名册，制定并保存两份方案，随后分别取得回答、读回观测并计算汇总。它先提示“两份方案均已保存”，完成后提示尚未进行总体审计。

打开 `lesson-11/artifacts/demo-200/`：

|文件或目录|现在用来做什么|
|---|---|
|`plans/register_ordinary.json`、`plans/web_voluntary.json`|查看取得回答之前保存的两份方案|
|`register_ordinary/observations.csv`、`web_voluntary/observations.csv`|读取两种方式实际收到什么回答|
|`comparison.csv`|并排比较人数、比例与费用|
|`estimates.json`|查看未四舍五入的同一组统计量|
|`sample-records.csv`|从网上方式的观测中抽出五类记录，便于逐行阅读|

两个机制目录还各有 `request.json` 和 `receipt.json`，提交前再用它们核对文件对应关系。此时还没有 `audit.json`。

## 3. 先读五条记录，再读比例

以下是这次网上方式的真实输出。表中“未知”在原 `observations.csv` 中是空白。

|编号|组别|框内 in_frame|受邀 invited|回答 answered|观察需求 observed_need|邀请费用|
|---|---|---:|---:|---:|---|---:|
|A0002|A|0|0|0|未知|0|
|A0001|A|1|0|0|未知|0|
|A0004|A|1|1|0|未知|1|
|A0066|A|1|1|1|0|1|
|A0003|A|1|1|1|1|1|

另一个观测列 `invite_probability`：A0002为0，其余四人为200/3305，约0.060514。这是邀请机会，不是需求比例，也不是回答概率。

A0002不在网上名单，A0001在名单但没被抽中，A0004受邀却没有回答。这三个人的需求本次都不知道；A0066才是已知没有需求。A0004虽未回答，邀请费用仍为1。由此可见，观测CSV的4000行是4000人的过程记录，不是4000份有效回答。

## 4. 从回答人数算到比较表

`comparison.csv` 中比例以0至1保存；下表改用百分数显示，保留两位小数。

|指标|完整名册普通联系|网上邀请、自愿回答|
|---|---:|---:|
|抽样框人数|4000|3305|
|邀请人数|200|200|
|回答人数|145|101|
|A组回答人数|132|85|
|B组回答人数|13|16|
|A组有需求回答人数|57|54|
|B组有需求回答人数|9|14|
|A组需求比例|43.18%|63.53%|
|B组需求比例|69.23%|87.50%|
|直接比例|45.52%|67.33%|
|0.8/0.2构成比例|48.39%|68.32%|
|邀请费用（仅邀请，单位）|264|240|

普通联系收到145份回答，其中有需求57+9=66份，所以直接比例为66/145，约45.52%。分母是回答人数，不是邀请人数200或名册人数4000。网上方式对应为(54+14)/(85+16)=68/101，约67.33%。

构成加权先算每组回答者中的需求比例，再按全体A/B人数占比合并：

- 普通联系：A组57/132，B组9/13；0.8×(57/132)+0.2×(9/13)，约48.39%。
- 网上方式：A组54/85，B组14/16；0.8×(54/85)+0.2×(14/16)，约68.32%。

0.8和0.2来自全体3200/800人的构成，不来自实际回答人数。若某组无人回答，该组需求比例不知道，构成比例也记为“未知”；不要填0后继续加权。

费用按受邀者计算：普通联系邀请A组168人、B组32人，168×1+32×3=264；网上方式邀请A组180人、B组20人，费用240。回答数不同不会退还未回答者的邀请费用。

现在可以解释：这次网上方式的两组回答者都显示更高的需求比例；只改变A/B权重不会把组内比例改低。还不能单凭这次差异断定哪一个数更接近全体，因为尚未核对总体需求。

## 5. 保存比较后，再看总体审计

先保留上面的估计和初步解释，再运行：

```sh
python3 lesson-11/survey_example.py audit --output lesson-11/artifacts/demo-200
```

打开新生成的 `audit.json`：这份固定总体有1640/4000=41%的人有需求，A组为35%，B组为65%。这些真值来自完整合成总体，不是本次调查又收到的新回答。

现在把估计与41%比较：普通联系的直接比例高4.52个百分点，加权后高7.39个百分点；网上方式分别高26.33、27.32个百分点。**本次普通联系加权反而离真值更远。**权重调整了组别构成，但每组收到的人仍有随机波动，不能保证一次结果更准确。网上方式还受名单覆盖及有需求者更愿回答的影响；只按组别加权没有消除这些问题。单次示范不足以证明一种方法总是更好。

## 6. 换成自己的标准任务

在取得自己的回答前，选定共同邀请人数、两个种子和新目录，在报告中写下规模与资源的理由。两种方式保持相同邀请人数，先保存全部方案。可以采用本例程序，也可修改分析程序；请保留原始人口CSV。

将下面尖括号中的内容换成你事先选定的整数与新目录名，再执行（尖括号本身不输入）：

```text
python3 lesson-11/survey_example.py survey --n <邀请人数> --selection-seed <邀请种子> --response-seed <回答种子> --output lesson-11/artifacts/<新目录名>
```

读观测、填写自己的比较表，写出初步解释，然后对同一目录运行 `audit`。保留第一次方案及结果；要研究波动，先定重复方案；审计后改进时另记“事后修订”。不通过反复换种子选择最接近真值的一次。根据自己的结果提出建议，不能把示范表换一个标题作为正式报告。

## 7. 登记复现命令与输出

完成自己的报告后，编辑 `lesson-11/submission.json`：`report` 保持为自己的报告路径；`run` 改为能重建自己结果的命令参数列表。在上面的 `survey` 命令末加 `--audit`，即可先生成比较、再生成审计，用于一次完整复现。例如结构如下，各参数替换为自己的实际值：

```json
"run": ["python3", "lesson-11/survey_example.py", "survey", "--n", "自己的整数", "--selection-seed", "自己的整数", "--response-seed", "自己的整数", "--output", "lesson-11/artifacts/自己的目录", "--audit"]
```

`artifacts` 登记该目录的全部结果文件，包括两份 `plans`、两个机制目录内的方案/观测/凭据，以及 `estimates.json`、`comparison.csv`、`sample-records.csv`、`audit.json`。可在仓库根目录运行下面的短段，先将代码中的 `my-survey` 换成实际目录名，就能列出待登记路径；它不会修改完成状态或替你写报告：

```sh
python3 - <<'PY'
from pathlib import Path
import json
folder = Path("lesson-11/artifacts/my-survey")
print(json.dumps(sorted(str(p) for p in folder.rglob("*") if p.is_file()), ensure_ascii=False, indent=2))
PY
```

将清单复制到 `artifacts`，报告完成后才把 `status` 改为 `complete`，运行 `python3 scripts/course_l11.py check 11`，再按[提交流程](../docs/WORKFLOW.md)提交。最终标签检查在临时副本中删除登记的输出并按 `run` 重建，对比文件内容；不删除原提交的文件。

采集程序拒绝覆盖已存在的输出目录，这是为了保留原方案。正常做新实验时换目录；已完成结果不必原地再次运行。首次取得时分开运行 `survey`、`audit`，提交复现命令才合为带 `--audit` 的一次运行。

## 按需排错和查函数

|现象|先检查什么|
|---|---|
|名册人数不对|输入应为4000个唯一编号，A/B为3200/800，网上名单3305人|
|邀请或回答数异常|每种方式邀请数应为n，每人最多一次，回答数不超过邀请数|
|构成比例为未知|是否有一组无人回答；保留未知并解释限制|
|输出目录已存在|保留原目录，改用新目录|
|方案或观测不一致|核对同一目录的 `plans`、`request.json` 和 `receipt.json`，确认未手改或混用|

自行编写程序时，`sampling_tools.py` 的接口依次为：`load_frame()`、`make_request(frame, mechanism, n, selection_seed, response_seed)`、`write_request(request, path)`、`run_request(request, output_dir)`、`read_observations(path)`、`response_mean(rows, group=None)`、`composition_estimate(rows, population_counts)`，最后才调用 `audit_population(request, output_dir)`。可直接阅读 `survey_example.py` 查看它们怎样连起来；需要改变方法时仍能复用观测与汇总工具。
