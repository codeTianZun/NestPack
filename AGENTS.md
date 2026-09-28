以“当前有效要求”为成品的唯一依据。
用户的补充、撤回和修正用于更新当前有效要求；成品只表达更新后的当前状态。
- 最终代码、文档、测试、注释和提交信息只表达当前有效要求。
- 用户的修正替换旧要求，不自动形成新的否定要求。
- 被撤回、否决或由 Agent 擅自提出的概念，不得以否定说明、保护分支、fallback、配置、类型、测试或解释性注释残留在成品中。
- 只有当前业务契约、真实外部输入、信任边界、可达数据流、已知事故、回归测试或兼容性要求能够证明必要时，才加入否定约束或防御代码。
- 修改要求后，按当前有效要求正向重写受影响内容。
- 完成前检查最终 diff；任何只能由已被否决方案解释的改动都应删除。
# AGENTS.md

NestPack：多层嵌套压缩工具（RAR / 7z / ZIP 逐层可选、可混合嵌套；Windows
GUI/CLI + Linux CLI，共用 `core/` 引擎，版本 1.0.0）。智能体会话从本文件开始导航。

## 必读

1. **开发文档.md** —— 现行架构、模块职责、配置 schema、关键设计
   决策（历史结论，避免反复）与新会话执行指引。改代码前先读。
2. **使用说明.md** —— CLI/GUI 全部用法与 JSON 字段语义
   （只改行为不动代码时读对应章节即可）。
3. 涉及的模块源码、入口脚本与对应使用文档；业务术语见 **CONTEXT.md**。

## 硬规则

- 产品范围仅限 Linux CLI、Windows CLI、Windows GUI；功能、依赖、
  构建产物与文档都应服务于这三种运行方式。
- 本项目禁止新增、保留或运行自动化测试，也不要把测试接回 CI、依赖或
  构建流程。修改后可按实际需要做静态检查或手动验证，不设每次会话
  开始和结束必须运行固定命令的要求。
- CLI 链（core/cli/platforms）不得导入 PySide6；GUI 纯逻辑放无 Qt
  依赖的模块（参照 `gui/config/storage.py`、`gui/config/passwords.py`），
  CI 不装 PySide6。
- 遵循现有风格：类型标注、中文 docstring/字符串、不加多余注释。
- 实施完成前不提交（除非用户明确要求）。

## 快速定位

| 要改什么 | 去哪里 |
|---|---|
| 压缩计划构建 / 工具路径 / 输出冲突校验 | `core/compression/planning.py` |
| 默认层名 / 分卷与伪装路径 | `core/naming.py` |
| 默认层展开 / 来源独立层 / 实际任务选择 | `core/source_layers.py` |
| 压缩计划 / 任务与层 / 结构化结果 | `core/compression/models.py` |
| 多来源调度 / 并行停止 / 根因传播 / 全局进度 | `core/compression/scheduler.py` |
| 逐层压缩 / 按层选工具 / 中间层清理 | `core/compression/layers.py` |
| 单层压缩 / 自检 / 临时归档 | `core/compression/archive.py` |
| 正式产物发布 / 伪装落盘 / 分卷替换与失败恢复 | `core/compression/outputs.py` |
| 来源暂存 / 输入作用域 | `core/compression/workspace.py` |
| 格式协议 / 注册 / 内容识别 | `core/backends/base.py`、`core/backends/__init__.py` |
| RAR / 7z / ZIP 命令与分卷规则、退出码表 | `core/backends/rar.py`、`sevenzip.py`、`zip.py` |
| RAR 自解压目标 / 品牌模板 / 图标与脚本 | `core/sfx.py`、`core/config/sfx.py`、`core/models.py` |
| RAR / PE / ELF 自解压内容识别 | `core/rar_content.py` |
| 用户取消 / 内部停止信号 / CancelledError | `core/cancellation.py` |
| 子进程启动 / 输出 / 停止与资源回收 | `core/process.py` |
| 路径展开 / 原子文本写入 / 临时目录 / 可取消复制 | `core/filesystem.py` |
| 别名 / 填充 / 时间戳 | `core/compression/privacy.py` |
| 压缩级别 / 磁盘估算 | `core/compression/level.py`、`preflight.py` |
| 解包流程 / 密码尝试 | `core/unpack/workflow.py`、`extraction.py` |
| 解包工作目录 / 失败保留 | `core/unpack/workspace.py` |
| 解包内容识别 / 伪装分卷 | `core/unpack/content.py`、`volumes.py` |
| 配置读写 / 文档解析 / 字段校验 / 随机层名 | `core/config/storage.py`、`schema.py`、`validation.py`、`naming.py` |
| 共享模型 / 常量 / 配置错误 | `core/models.py` |
| 版权与许可展示 | `core/legal.py` |
| 工具检测（rar/7z、dependencies 目录） | `platforms/*/detection.py`、`platforms/tools.py` |
| 完成摘要 / 密码清单 / --json manifest | `core/result_summary.py` |
| CLI 参数 / 主流程 / 解包流程 | `cli/args.py` / `cli/main.py` / `cli/unpack_cmd.py` |
| CLI 数字菜单 / 任务与层编辑 | `cli/menu.py` / `cli/wizard.py` / `cli/prompts.py` |
| CLI 参数配置 / 压缩预览与执行 | `cli/configuration.py` / `cli/compress_cmd.py` |
| GUI 应用接线 / 任务互斥 / 关闭协调 | `gui/main.py` |
| 主窗口布局 / 来源与层名联动 | `gui/views/main_window.py` |
| GUI 配置会话 / 自动保存 / 字段绑定 | `gui/config/session.py`、`gui/config/binding.py` |
| GUI 默认层与来源独立层草稿 | `gui/config/layers.py` |
| GUI 最近配置与目录 / 默认模板 / 随机密码 | `gui/config/storage.py`、`gui/config/passwords.py` |
| GUI 路径选择起点 / 另存时固定路径 | `gui/config/paths.py` |
| GUI 当前来源层名编辑 / 最终路径预览 | `gui/views/layer_names.py`、`gui/config/naming.py` |
| GUI 后台任务 / 线程状态与回收 | `gui/tasks/`、`gui/tasks/threading.py` |
| GUI 工具路径 / 浏览与检测提示 / 安装动作 | `gui/views/runtime_panel.py` |
| GUI 压缩输出 / 已有归档伪装 | `gui/views/output_panel.py`、`gui/views/video_dialog.py` |
| GUI 解包表单 / 候选密码 / 原归档提取入口 | `gui/views/unpack_panel.py` |
| GUI 配置操作 / 任务选项 | `gui/views/config_bar.py`、`gui/views/task_options.py` |
| GUI 层选择 / 右侧层编辑 / 逐层伪装 | `gui/views/layers_panel.py`、`layer_card.py`、`layer_editor.py`、`disguise_panel.py` |
| GUI 面板 / 对话框 / 字段读写 | `gui/views/` |
| 自解压设置界面与数字菜单 | `gui/views/sfx_dialog.py`、`cli/sfx.py` |
| GUI 主题 / 文件选择器外观与中文文案 / 项目 Logo | `gui/appearance/` |
| Windows GUI/CLI 与 Linux CLI 单文件构建 / 图标 | `scripts/build.py` |
| RAR 官网安装指引 / 7-Zip 下载与许可保留 | `platforms/tool_installer.py`、`scripts/fetch_tools.py` |
| Python 依赖一键安装 | `scripts/windows/install_deps.ps1` / `scripts/linux/install_deps.sh` |
| Linux CLI 可执行文件构建入口 | `scripts/linux/build_linux.sh` |
