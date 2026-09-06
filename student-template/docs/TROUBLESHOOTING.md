# 环境与排障

课程通用工具和每课示例代码支持Python 3.10及以上，只用标准库。先确认`python --version`与`git --version`；系统使用`python3`时替换命令名称即可。所有命令从仓库根目录执行。

需要第三方分析库时，建议使用虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell：`.venv\Scripts\Activate.ps1`；macOS/Linux：`source .venv/bin/activate`。若PowerShell限制激活，可直接使用`.venv\Scripts\python.exe`，无需修改全局安全策略。

按实际分析需要安装，例如`python -m pip install numpy pandas scipy matplotlib`，将用到的依赖及可复现版本写进`requirements.txt`。使用其他库也可以，不要求全部安装。不要把`.venv`提交到仓库。

| 问题 | 先检查 |
|---|---|
| 找不到文件 | 当前是否在仓库根目录；文件名大小写与数据字典是否一致 |
| 无法导入包 | 安装包的Python是否就是运行脚本的Python |
| 中文乱码 | 数据CSV按UTF-8读取；必要时对带BOM的表用utf-8-sig |
| Git推送失败 | 使用自己仓库的页面地址、账号权限与已登录凭据；不要把密码贴给AI |
| 标签已存在 | 不覆盖原最终标签；后续修订用revision标签 |
| 检查失败 | 根据提示补齐报告、结果文件路径或完成状态；自动检查不能判断统计结论是否正确 |
| 网络或CI排队 | 保存文件及本地commit，向教师说明；不重复创建仓库或覆盖原标签 |

向AI求助可提供操作系统、Python版本、命令和完整报错，不提供密码、令牌或私人数据。
