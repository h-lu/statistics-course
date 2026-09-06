# V1历史归档：2026-09-05

此目录保存V2重写前的完整历史，**不是现行授课依据**。三份早期总计划按原内容归档，三个Git bundle保存仓库全部已有Git引用与历史，不只保存最后一次文件快照。

| 对象 | 归档前提交 | 恢复文件 |
|---|---|---|
| 学生模板 | `c596c4bec359c846315a6252d80ccd7ce5d1d11b` | `course-student-template.bundle` |
| 教师材料 | `147ffd08cdedbb6c5ccd467edce45454c670553d` | `course-instructor.bundle` |
| 自查程序及原6课题库 | `278f5fb2647018d8c9ac8ff8cbd246e6704c301a` | `stat-check.bundle` |

三个仓库另保留`archive/v1-2026-09-05`标签。bundle已用`git bundle verify`核验，可离线恢复。它们不包含数据库、账号口令或未跟踪运行配置；自查数据库按部署说明另行备份，不能用代码归档替代答题记录备份。

## 恢复到新目录

不要覆盖现行仓库。以下命令在本目录执行，以学生模板为例：

```bash
git bundle verify course-student-template.bundle
git clone course-student-template.bundle recovered-student-v1
git -C recovered-student-v1 switch --detach archive/v1-2026-09-05
```

教师和自查仓库同理，更换bundle名与新目录即可。已上线V2时，查看旧材料不等于回滚生产；恢复服务前还需核对数据库兼容性和活动场次。

## SHA-256

```text
19712751e4579db651140714bfdcefc4a2ca7f849412ddbeb55cefabb2ee4a52  30个逐课开放项目冲刺.md
cad528918e91ae37aab386eba0db70bc2b1307b9804264edb43e8f422181d960  AI时代统计学授课计划.md
e543d8d9c6d0d662474bdfdbb1bf53b2c04f16e0788c1da69fbb6ad3a99c3a15  Gitea项目制统计学授课计划.md
4d30ac9ef3fe598b8e6d650846c8366ddf85b8b6817bb66838a6a33b5f536751  course-instructor.bundle
b8dcd91d7c7e3923ab5758faff5723a29de5667043d2a600ef954db55f1faaf1  course-student-template.bundle
04ab44d3600869f7f16f16f61b1a0809309669d9e0046c211a0623fcb89fd4d2  stat-check.bundle
```

本归档含教师参考及历史混合模板内容，只保留在教师私有仓库，不复制到学生模板。
