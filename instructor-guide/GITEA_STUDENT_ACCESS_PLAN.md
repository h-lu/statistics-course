# Gitea 学生账号与仓库权限执行方案

> 状态：待实施，不表示服务器已经完成这些变更。
>
> 最近一次只读审计：2026-08-28。
>
> 适用范围：统计学项目课的学生账号、学生学期仓库和 Gitea Actions。

## 1. 已确定的管理方案

采用“每学期一个私有组织、组织持有一人一库、学生只写自己的仓库”。

示例结构：

```text
statistics/                         长期课程源材料
├── course-student-template         公共学生模板
├── course-instructor               教师私有材料
└── stat-check                      知识自查服务源码

statistics-2026-fall/               当学期私有组织
├── 256121101                       私有；该生 Write
├── 256121102                       私有；该生 Write
└── ...
```

教师是学期组织的 `Owners`。学生不成为组织成员，只作为自己仓库的直接
`Write collaborator`。这样学生可以 push、创建课程标签并查看 Actions，但不能：

- 删除或转移仓库；
- 改变 Private 状态；
- 关闭 Actions 或修改仓库设置；
- 添加其他协作者；
- 访问其他学生的仓库。

不采用下列方案：

- 不让学生自己拥有学期仓库；
- 不把所有学生仓库关联给一个共享 `students` 团队；
- 不为每名学生建立一个团队；
- 不把学生加入 `statistics/Owners`、管理员团队或教师仓库；
- 不依靠权限系统判断学生是否使用 AI。

### 为什么使用独立学期组织

1. 学生仓库、长期模板和教师材料边界清楚；
2. 期末可以按整个学期统一归档；
3. `roster.csv` 中所有人的 `repo_owner` 相同，便于汇总；
4. 当前学生 workflow 只排除 owner 为 `statistics` 的模板仓库。学生仓库位于
   `statistics-2026-fall` 时 Actions 会正常执行；若直接放在 `statistics`，现有
   workflow 会跳过检查。

## 2. 目标权限矩阵

| 对象 | 教师 | 对应学生 | 其他学生 |
|---|---|---|---|
| `statistics/course-student-template` | Owner | 无需访问 | 无需访问 |
| `statistics/course-instructor` | Owner | 无 | 无 |
| `statistics/stat-check` | Owner | 无 | 无 |
| 学生本人学期仓库 | Owner | Write collaborator | 无 |
| 其他学生学期仓库 | Owner | 无 | 对应学生 Write |

受限账号不会因为仓库是 Public 就自动获得读取权限，只能访问明确授予的仓库。
学期仓库已包含完整学生材料，因此学生无需再访问公共模板。若以后确实需要他们
查看模板，应显式授予模板 Read，而不是放宽整个账号。

## 3. 学生账号标准

只对本课名单中的账号定向应用以下值，不批量修改其他课程账号：

```text
admin                     = false
restricted                = true
visibility                = private
max_repo_creation         = 0
allow_create_organization = false
must_change_password      = true
prohibit_login            = false   # 在读期间
```

账号命名与密码规则：

- 登录名使用学号，避免姓名重名；
- `full_name` 可以填写姓名，但账号可见性保持 Private；
- 每人使用不同的随机初始密码，首次登录强制修改；
- 初始凭据通过校内系统或当面单独发放，不发到班级群；
- 明文凭据表只保留到首次登录完成，之后安全删除或加密归档；
- 学生可以修改自己的密码，并可自行添加 SSH key；
- 忘记密码时由教师管理员单独重置。当前未发现已启用的邮件找回配置。

当前 `students` 团队只可作为历史/名单用途：

- `can_create_org_repo` 必须为 `false`；
- `includes_all_repositories` 必须为 `false`；
- 不关联任何学生个人仓库、教师仓库或服务仓库；
- 在 Gitea 完成安全升级前，不把真实学生加入任何组织团队。

## 4. 开放学生写权限前的安全前置条件

### 4.1 2026-08-28 审计快照

- Gitea：`1.25.4`，容器使用 `latest` 标签；
- act_runner：`0.6.1`，容器使用 `latest` 标签；
- 已关闭自助注册，且要求登录后才能浏览；这两项保持不变；
- 当前启用的普通账号均不是 Restricted，多数仍可创建组织且个人仓库额度无限；
- `statistics/students` 当前没有关联仓库，因此尚未造成学生互相访问；
- runner 自身需要 Docker socket 来创建任务容器，但当前配置还允许学生任务请求
  挂载 `/var/run/docker.sock`；
- 学生任务容器当前加入 `mycourses_gitea` 内部网络。

上述最后两项使学生可修改的 workflow 可能越过普通 Gitea 账号权限。账号限制不能
替代 runner 隔离，所以在整改完成前，不向真实学生开放仓库 Write 权限。

此外，Gitea `< 1.26.0` 受 CVE-2026-22555 影响：组织成员可能绕过
`can_create_org_repo=false`，经 API 在组织内创建 fork 并利用 Actions。因此即使暂未
升级，也不要把学生加入 `statistics` 或学期组织的团队。

### 4.2 目标状态

执行时先重新核对官方最新稳定版与安全公告，不机械照搬审计日版本。按
2026-08-28 的信息，目标至少为：

- Gitea 升级到 `1.27.2` 或当时更新的安全稳定版；
- act_runner 升级到 `3.0.0` 或当时更新的安全稳定版；
- Docker Compose 固定明确版本，不再使用 `latest`；
- runner 的学生任务容器保持 `privileged: false`；
- `valid_volumes: []`，禁止 workflow 申请宿主卷；
- `docker_host: "-"`，runner 可以使用 Docker，但不把 socket 自动传入任务容器；
- `container.network` 留空，让 runner 为每个任务建立隔离网络，不把学生任务加入
  `mycourses_gitea`；
- 不在学期组织或学生仓库保存 PAT、管理员令牌、部署密钥或生产 Secret。

runner 目标配置的关键部分：

```yaml
container:
  network: ""
  privileged: false
  valid_volumes: []
  docker_host: "-"
```

Actions 权限设置：

- 学期组织 `Settings → Actions → General` 使用 Restricted 默认模式；
- 最大 token 权限只允许仓库内容读取，其余权限为 None；
- Cross-Repository Access 保持为空；
- 学生仓库不得覆盖组织级上限；
- 学生 workflow 顶层显式加入：

```yaml
permissions:
  contents: read
```

## 5. 批量开通流程

### 5.1 名单是唯一事实来源

使用不入 Git 的 `roster/roster.csv`：

```csv
student_id,name,email,gitea_login,repo_owner,repo_name,status
256121101,示例学生,example@school.edu,256121101,statistics-2026-fall,256121101,active
```

正式执行前确认：

- 学号无重复；
- Gitea 登录名无重复；
- 邮箱无重复；
- 每人只对应一个仓库；
- 学期组织名和学期一致；
- 不把测试账号混入正式评分名单。

### 5.2 `provision` 应是幂等操作

对名单中每名学生执行：

1. 账号不存在则创建，存在则只修正上述目标字段；
2. 生成唯一随机初始密码，并设置首次登录强制修改；
3. 从 `statistics/course-student-template` 生成私有仓库到学期组织；
4. 必须设置 `git_content=true`、`private=true` 和 `default_branch=main`；
5. 将对应学生加入该仓库，权限严格为 `write`；
6. 核对其他学生没有该仓库权限；
7. 记录实际仓库名到 `roster.csv`；
8. 不在命令输出、Git、Actions 日志或教师仓库中记录令牌和密码。

脚本重复运行时不得覆盖已有学生提交，不得重置已修改的密码，也不得重新生成已有
仓库。发现冲突时应停止并报告具体学生。

## 6. 管理工具保持简单

只实现四项命令即可：

```text
provision roster.csv       创建/修正账号、生成仓库、授予本人 Write
audit roster.csv           检查账号、仓库、协作者、Actions 与课程标签
reset-password 学号        单独重置密码并强制下次登录修改
close roster.csv           归档仓库、移除协作者、禁止学生登录
```

每个修改命令都应支持：

- 默认 `--dry-run`；
- 执行前生成 Gitea 数据库和配置备份；
- 只操作名单明确列出的账号和仓库；
- 输出不含密码、令牌和 OAuth Secret 的审计记录；
- 单个学生失败不静默跳过，最终给出成功/失败清单。

## 7. 实施顺序与验收

严格按下面顺序执行：

1. 重新读取本方案和当日官方安全公告；
2. 备份 Gitea 数据库、仓库数据、`app.ini`、Compose 和 runner 配置；
3. 升级并固定 Gitea 版本，检查登录、仓库、OAuth 和 API；
4. 升级并收紧 runner；
5. 用 `stat_test_student` 的一次性私有仓库回归：模板生成、push、tag、两次 Actions、
   教师状态脚本；
6. 创建私有学期组织；
7. 用测试账号验证 Restricted 用户只能看到自己的仓库，并能正常登录 stat-check；
8. 批量处理正式名单；
9. 运行 `audit`，人工抽查至少两个学生账号；
10. 更新 `roster/roster.example.csv` 和教师操作说明，使其反映学期组织结构。

最低验收标准：

- 学生能登录、改密码、clone、push、创建 final tag、查看自己的 Actions；
- 学生不能创建个人仓库或组织；
- 学生不能看见其他学生仓库和教师仓库；
- 学生不能修改仓库可见性、协作者或 Actions 设置；
- workflow 不能挂载 Docker socket，任务容器不在 Gitea 内部网络；
- 教师的 `course_status.py` 能得到 `GREEN / complete / success`；
- stat-check OAuth 登录和知识自查正常；
- 现有非统计学课程账号不受影响。

## 8. 学期中的操作

平时不需要逐个进入仓库管理：

- 课堂中学生只在自己的仓库工作；
- 教师使用 `scripts/course_status.py` 按 `roster.csv` 汇总 final tag 和 CI；
- 每次截止时保存带 `checked_at` 的 CSV 快照；
- 学生忘记密码时单独重置；
- 不把共享管理员令牌交给学生或写入 workflow；
- 不使用账号权限阻止 AI，而是继续依靠项目证据、更新数据和责任声明评价。

## 9. 期末冻结

期末不删除账号或仓库。按顺序执行：

1. 保存最后一次标签、SHA、CI 与评分快照；
2. 将全部学生仓库设为 `archive=true`；
3. 移除学生的 repository collaborator；
4. 将本课学生设为 `prohibit_login=true`；
5. 保留账号、提交、标签和仓库，维持评分追溯；
6. 下一学期如有重修学生，按新名单定向恢复账号，而不是恢复旧仓库写权限。

## 10. 参考资料

- [Gitea Restricted users](https://docs.gitea.com/1.25/help/faq/#restricted-users)
- [Gitea 1.25 权限实现](https://github.com/go-gitea/gitea/blob/release/v1.25/models/perm/access/repo_permission.go#L1717-L1766)
- [创建用户 API](https://docs.gitea.com/api/1.25/operations/admin-create-user/)
- [修改用户 API](https://docs.gitea.com/api/1.25/operations/admin-edit-user/)
- [模板生成 API](https://docs.gitea.com/api/1.25/operations/generate-repo/)
- [添加仓库协作者 API](https://docs.gitea.com/api/1.25/operations/repo-add-collaborator/)
- [Actions token 权限](https://docs.gitea.com/usage/actions/token-permissions/)
- [Runner 配置](https://docs.gitea.com/runner/develop/configuration/)
- [CVE-2026-22555 / GHSA-fhx7-m96w-mv29](https://github.com/go-gitea/gitea/security/advisories/GHSA-fhx7-m96w-mv29)
- [Gitea 1.27.2 发布说明](https://blog.gitea.com/release-of-1.27.2/)
- [Gitea Runner 3.0.0 发布说明](https://blog.gitea.com/release-of-runner-3.0.0/)
