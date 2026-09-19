# 项目操作与提交步骤

## 建立个人仓库

在课程模板页面点击“使用此模板”，以自己的账号创建私有仓库`statistics-2026-v2`，复制页面显示的克隆地址。已有旧版练习仓库时保留它，新建本学期使用的V2仓库，不覆盖旧作业。

```bash
git clone 你的仓库地址
cd statistics-2026-v2
git config user.name "你的姓名"
git config user.email "你的学校邮箱"
python --version
```

使用自己的已登录Git身份，按教师要求授予阅卷账号读取权限。不要向AI或仓库提供密码、令牌、私钥。

## 同步后续课程

课程发布仓库按日程逐课开放。教师发布新课后，在仓库根目录运行`python scripts/course.py sync`。工具会获取发布仓库中的课次，只新增本地不存在的目录；已经存在的课次会跳过，不覆盖你的代码、报告或结果。命令结束后先检查`git diff --cached`，再提交并推送。若首次使用时没有配置SSH密钥，可从Gitea页面复制自己的SSH克隆地址并完成登录配置后再同步。

当前版本还会补齐本地缺少的 `docs/READING_GUIDE.md`，前提是发布仓库含有该文件；没有新课次时也会检查指南是否缺少。已有指南和其他共用文件不会自动覆盖，工具也不会通过 `sync` 更新自身。旧版工具的更新步骤见[学生仓库首页](../README.md)，只在教师通知后执行。

## 每课的简单流程

以第3课为例，从仓库根目录执行：

```bash
python scripts/course.py start 03
python scripts/course.py run 03
```

阅读`lesson-03/README.md`和`LEARN.md`，可以让AI协助你选择方法、编写程序和解释结果。`analysis.py`提供可以运行的示例代码，你可以修改程序、采用其他方法或安装所需分析库。原始数据保持不变，清洗后的数据另存。

完成后在`lesson-03/submission.json`中填好报告路径、分析结果文件列表和运行命令，并把`status`设为`complete`。例如：

```json
{
  "lesson": "lesson-03",
  "status": "complete",
  "report": "lesson-03/report.md",
  "artifacts": ["lesson-03/artifacts/evidence.csv"],
  "run": ["python", "lesson-03/analysis.py"]
}
```

`evidence.csv`只是文件名示例，应换成你真正生成的文件。命令和路径相对于仓库根目录；若使用其他程序或工具，修改`run`即可。Python运行命令使用`python`，检查工具会沿用当前Python环境。所需分析库写入`requirements.txt`，不要使用只在自己电脑上有效的绝对路径。

本地 `check` 只检查完成状态、路径和文件，不重新运行分析。推送后的自动检查（CI）会在临时副本中移除列出的结果文件，再运行分析程序重新生成文件，并比较前后内容；原提交不受影响。优先列出可以重复生成相同内容的CSV、JSON等数值结果，固定随机种子、排序和输出精度。图表也应提交，但自动嵌入生成时间的PDF等不必列入逐字节比较清单。报告、图表与数值结果应保持一致。

```bash
python scripts/course.py run 03
python scripts/course.py check 03
git status
git diff
git add lesson-03 requirements.txt
git commit -m "完成第03课数据适用性项目"
git push
git tag v2-l03-final
git push origin v2-l03-final
```

如果新增了共用程序或其他结果文件，也需核对后加入提交。自动检查只核对提交配置、文件和程序运行结果，不能判断统计方法与结论是否合理。推送后查看Actions；遇到检查排队或网络故障时，先保存文件与本地提交，并向教师说明。

最终标签或修订标签只检查对应课次；普通分支检查本地已有课次，尚未发布的课次无需提前建立。已存在课次缺少提交配置时仍会报错，不会默认为完成。

## 代表作品修订

保留原最终标签，不覆盖它。修订报告时记录改了什么、依据是什么，完成后提交新版本并使用`v2-l03-revision-1`。修订用于作品质量评价，不改变原版本是否按时提交。详见[成果与评分](ASSESSMENT.md)。
