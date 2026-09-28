# Windows 平台参考

CLI 入口参数与 JSON 输出契约（manifest schema、error_kind）跨平台一致，
见 `cli.md`；解包见 `unpack.md`。

## CLI

源码使用 `python -m cli`；发布程序使用 `nestpack-cli.exe`。
双击或无参数启动进入数字菜单，选择任务后才检查来源；来源失效时可重新选择。
参数调用直接执行，例如：

```powershell
.\nestpack-cli.exe --source "D:\data" --output "D:\out" --layer rar --yes --non-interactive --json
```

## GUI（PySide6，仅 Windows 桌面）

- 启动：`pwsh -File scripts\windows\start_gui.ps1`，或 `python -m gui`。
- 主界面「解包…」按钮打开解包对话框（自动预置当前界面各层密码为候选）。
- 发布程序缺少 WinRAR 时提供官网安装指引，缺少 7-Zip 时询问是否下载；
  「设置」提供「WinRAR 安装指引」和「安装/修复 7-Zip」。
  7-Zip 程序及许可材料保存在 exe 同目录的 `dependencies/7z/`。
- 层级卡片密码栏「随机」按钮生成 16 位随机强密码；来源列表支持
  从资源管理器拖放添加。
- 完成弹窗会显示密码明文并提供一键复制清单。

## 平台差异（win32）

- 自动检测 WinRAR.exe/Rar.exe（dependencies → PATH → 注册表 → ProgramFiles）。
- 7z / zip 层先按同序查找 7z.exe / 7za.exe / 7zz.exe；7z 请求在完整工具
  缺失时再查找 7zr.exe。含 ZIP 层的压缩任务在规划时要求完整工具，解包在
  识别到 ZIP 层时校验工具能力。`--install-tools` 或 `scripts/fetch_tools.py`
  会装 7zr.exe（仅 .7z）与支持 -tzip 的 7za.exe。
- `show_winrar_gui: false` 时追加 `-ibck` 切后台。

## 单文件构建

Windows GUI 与 CLI 构建入口为 `scripts/windows/build_exe.ps1`（内部调
`scripts/build.py`），分别生成 `NestPack.exe` 与 `nestpack-cli.exe`，详见
《打包说明.md》。
