# 2026-10-09 课程重设计前归档

这份归档保存本次独立本地重设计开始前的教学源文件。归档开始时本独立副本的 `git status --short` 为空；主编另核原始项目复制前与复核时的 `git status --porcelain --untracked-files=all` 均为空。因此688个tracked文件覆盖此次基线的全部非ignored教学工作树。它来自复制工作树的当前字节，而不是仅导出历史提交。没有读取或复制忽略文件、真实学生仓库、账号、成绩、生产数据库、环境变量或凭据；线上发布仓库、服务与历史场次未改动。

| 包 | 文件数 | 原文件字节 | 范围 |
|---|---:|---:|---|
| `source-tracked.tar.gz` | 688 | 6,361,883 | 重设计前全部受版本管理的教学源文件，含已有 V1 历史归档；作为完整恢复保底 |
| `lessons-01-08.tar.gz` | 96 | 526,937 | 原学生与教师第1–8课完整课包；已在新课作者修改前归档 |
| `lessons-09-32-and-specific-assets.tar.gz` | 397 | 3,366,311 | 原学生与教师第9–32课、双份全部历史题库、后续专用数据与生成器 |
| `old-course-documents.tar.gz` | 17 | 74,216 | 原总纲、总说明、支持导航、数据说明、发布说明、编写接口与旧审查记录 |

每个包有同名 `*.manifest.json`，逐路径记录 SHA-256 和原文件字节数。[verification.json](verification.json) 记录压缩包 SHA-256、包字节数和已核验状态。[scope-and-restore-map.json](scope-and-restore-map.json) 记录退出活跃目录的原路径、保留的历史题库路径和共享数据边界。

第9–32课的学生/教师活跃目录现在只保留 `README.md` 大纲占位。`data/inference`、`experiments`、`prediction`、`policy` 及对应生成器已退出活跃模板；第1–8课仍需要的 `data/service`、`data/alerts` 和对应生成器保留。没有删掉学生提交、线上记录或数据库。

原第9–32课题库的两份副本分别位于教师 `knowledge-check/question-bank/archive/redesign-2026-10-09/` 和服务 `app/question_bank/archive/redesign-2026-10-09/`。文件名、ID、题目、答案和字节不变。服务显式加载该历史目录供旧场次按 ID 读取；新场次目录仅列第1–8课，不重新解释或评分历史答案。归档中的 `.yml` 不作为新课内容发布。

## 校验与恢复

从总仓库根目录执行，全部命令只用 Python 标准库：

```bash
python3 archive/redesign-2026-10-09/restore.py --package source-tracked --verify-only
python3 archive/redesign-2026-10-09/restore.py --package lessons-01-08 --verify-only
python3 archive/redesign-2026-10-09/restore.py --package lessons-09-32-and-specific-assets --verify-only
python3 archive/redesign-2026-10-09/restore.py --package old-course-documents --verify-only
```

恢复到新目录，先查看再选择所需文件：

```bash
python3 archive/redesign-2026-10-09/restore.py \
  --package source-tracked --destination restored-before-redesign
```

恢复程序先核对压缩包与每个成员的字节/SHA-256，再写入新的空目录；已有文件一律拒绝覆盖。恢复出的材料是历史版本，不自动回填活跃目录，不发布、不推送，也不恢复生产数据库。若只需原1–8课或后续旧材料，将 `--package` 换为上表中的对应名称。

本次作者已逐包验证全部成员；完整源包另在临时空目录实际恢复并逐文件复验。归档验证证明文件可恢复，不代表旧材料已适合新大纲或真实学生90分钟试教。

## 本地验证证据

- 四个包的成员路径、原字节数和SHA-256全部核验；完整源包在临时空目录实际恢复，688文件再次核验一致；已有内容的恢复目标被拒绝覆盖。
- 学生工作流33项、本地手动发布7项、教师逐课题库版本选择4项测试通过；包含未来占位不执行、不同步、不发布、原作品不覆盖。
- 知识自查全部261项测试通过，含87套题库、历史字节保护、两份副本一致、旧场次/响应保留与未来旧课拒绝新建场次。
- Shell发布脚本语法与 `git diff --check` 通过。

FastAPI的TestClient在受限环境中连最小空应用启动也会挂起；上述自查测试经自动审核批准，在临时合成数据库中运行，未访问生产账号或成绩，未安装依赖。课程课包的实跑和学习路径检查由各课作者与最终审查记录另行给出；这些归档/工具测试不证明实班90分钟适用性。
