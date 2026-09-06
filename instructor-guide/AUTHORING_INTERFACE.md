# V2内容编写与工具约定

这是课程作者的实现约定，不发布给学生。

- 学生目录仍为`lesson-01`到`lesson-32`；每课`README.md`、`LEARN.md`、可运行的`analysis.py`（示例代码，不是完整答案）、`report.md`（标题与提示，不填假答案）、`submission.json`。
- `submission.json`初始为`{"lesson": "lesson-NN", "status": "not_started", "report": "lesson-NN/report.md", "artifacts": [], "run": ["python", "lesson-NN/analysis.py"]}`。status最终为complete；artifacts填写支持分析结论的结果文件路径（可多份）。run是从仓库根执行的参数列表，允许学生改用其他入口。项目不强制额外contract/update/预标签；分析选择与修订写进report。
- 统一学生命令`python scripts/course.py start NN`（只设in_progress）、`python scripts/course.py run NN`（运行所选程序）、`python scripts/course.py check NN`（检查提交文件，不判断统计质量）。最终标签`v2-lNN-final`。允许修订标签`v2-lNN-revision-1`，保留原始标签。
- `analysis.py`示例代码用标准库读取本课数据，生成一份描述性CSV或JSON至本课`artifacts/`，不得含TODO阻断，也不得用固定推荐冒充成果。允许pandas/numpy/scipy/statsmodels/sklearn等第三方分析；课程工具不强制安装全部包。
- 共享数据在学生`data/<world>/`，生成脚本在`scripts/generate_<world>.py`；必须固定种子。数据CSV由脚本生成，README列单位、字段与局限。每组数据的作者负责本范围需要的全部字段，课次材料必须引用真实存在的文件。不将答案写入学生原始数据。
- 教师每课`lesson-NN/RUNBOOK.md`（90分钟可调节时间、关键知识、巡视/反馈、六问审核）与`REFERENCE.md`（可复现参考计算命令或代码、可接受路线、评价所依据的数值、关系及适用条件）。参考不是唯一答案。
- 题库在教师`knowledge-check/question-bank/lesson-v2r1-NN.yml`，`lesson_id: v2-lNN-r1`，title以`第NN课 · `开始；结构见`knowledge-check/question-bank/SCHEMA.md`。每课5概念，每概念a/b两题，每题4选项、一个答案和解释。概念ID在单课唯一；AI概念提示不泄露原题答案。a/b不能只调换同一道题答案位置。错项可信，正确字母分散。
- 学生README每课底部链接`https://hblu.top/stat-check/`，提示确认页面为当日课次；教师选择场次，学生页自动跟随。评分与通用操作链接`../docs/WORKFLOW.md`和`../docs/KNOWLEDGE_CHECK.md`，不要逐课重复后台说明。
- 总表、使用说明、评分、统一工具、CI、历史迁移与部署由主编维护；各课作者不改这些共用文件，不自行推送或部署。
