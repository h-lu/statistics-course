# 第12课材料与运行入口

沿用自己的学生仓库与 Python 环境。本课使用第11课的同一份4000人数据。

## 已有学生仓库怎样取得材料

先保存并提交自己的作业，再在仓库根目录运行以下命令。尚未设置 course-release 时，先按仓库首页添加该远端。

```sh
git fetch course-release main
if [ ! -e scripts/course_l12.py ] && [ ! -L scripts/course_l12.py ]; then
  git restore --source=course-release/main -- scripts/course_l12.py docs/LESSON12_UPDATE.md
fi
python3 scripts/course_l12.py sync
```

sync 只添加缺失课包与依赖，不覆盖已有课目录、个人报告或原始数据。若提示共享文件不同，保留个人版本并请教师核对。

第12课标签的自动重现需要对应的检查入口。若你没有自行修改课程工作流，运行：

```sh
git restore --source=course-release/main -- .gitea/workflows/check.yml
```

若改过该文件，先请教师核对差异。查看 git status 和 git diff 后，按原流程提交新增材料。

## 开始与提交

```sh
python3 scripts/course_l12.py start 12
python3 scripts/course_l12.py run 12
```

完成正式项目后运行 python3 scripts/course_l12.py check 12，并按本课 README 使用 v2-l12-final 标签。已有作业与标签不变。
