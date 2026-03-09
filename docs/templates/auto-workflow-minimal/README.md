# auto-workflow-minimal

最小可复制骨架：
- `projects/example-project/`：示例项目目录
- `runtime/auto-advance/`：运行态文件目录
- `scripts/auto_advance_projects.py`：最小自动推进脚本
- `LaunchAgents/com.example.openclaw.project-auto-advance.plist`：定时触发器模板

使用方法：
1. 把 `projects/example-project` 改成你的项目
2. 把脚本里的 `/Users/you/.openclaw/workspace` 改成你的真实路径
3. 按需修改 `STEPS`
4. 把 plist 中的用户名和脚本路径改成实际值
5. 用 `launchctl bootstrap` 加载 plist
