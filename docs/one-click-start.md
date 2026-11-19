# 一键启动

Windows 10/11 与 macOS 各提供一个安装入口，无需提前安装开发工具。macOS 的 Intel 电脑需要 macOS 13 或以上版本。第一次联网下载较多组件；看到准备提示时保持窗口打开，完成后浏览器自动打开欢迎页。按 Open the court 进入项目，审核与数字人像测试共用一个服务。

## 第一次使用

Windows 打开 PowerShell，复制下面一行并回车：

```powershell
irm https://raw.githubusercontent.com/BDERyanYU/marketing-court/main/scripts/install-windows.ps1 | iex
```

macOS 打开终端，复制下面一行并回车：

```bash
curl -fsSL https://raw.githubusercontent.com/BDERyanYU/marketing-court/main/scripts/install-macos.sh | /bin/bash
```

首次出现 DeepSeek API key 提示时，粘贴项目维护者私下提供的密钥并回车。输入内容不可见，这是正常现象。密钥只存放在本机 `data/deepseek-api-key.txt` 中；项目已有 `.env` 或密钥文件时会复用，原配置不会被覆盖。启动时通过模型列表接口确认密钥和 `deepseek-flash` 可用，不发送生成请求。

安装完成后，桌面会出现 Marketing Court。以后双击即可，服务保持在启动窗口运行，按 Ctrl+C 退出。网页地址由启动器显示，一般为 `http://127.0.0.1:5180`；端口被占用会自动选择下一个。每个人在自己的电脑运行，数据也各自保存。

## 本机文件

Windows 安装在 `%LOCALAPPDATA%\MarketingCourt`；Mac 安装在 `~/Applications/MarketingCourt`。桌面快捷方式指向该目录的启动入口。已经自行下载或克隆的用户，可以运行根目录的 `Start-Windows.cmd` 或 `Start-Mac.command`。Mac 若无执行权限，在项目目录的终端执行 `bash Start-Mac.command`。

Python、uv、备用 Node.js 与 pnpm 均保存在项目内部，不修改系统环境变量或要求管理员权限。Node.js 可复用已安装的 20+ 版本，否则自动下载固定版本；下载组件校验固定哈希。后端依赖使用 `uv.lock`，前端使用 `pnpm-lock.yaml`。启动器将构建后的前端与后端合为同一地址，服务只监听本机。

启动数据位于项目的 `data/`，虚拟环境位于 `.venv/`，前端产物位于 `frontend/dist/`，均不提交 Git。已有项目、审核、画像和素材不会被初始化脚本删除。

## 出错与更新

- 网络或组件安装失败：修复网络后重新运行原命令或双击桌面入口，已下载内容会复用。需要能访问 GitHub、Python/Node 包服务、模型下载服务和 DeepSeek。
- 密钥无效：修改安装目录里的 `data/deepseek-api-key.txt`，保存后重新打开。如使用已有 `.env`，以其中的密钥配置为准。
- DeepSeek 余额、限流或生成错误：启动检查仅确认认证和模型，不保证后续生成成功；具体提示会显示在使用页面。
- 图片模型下载失败：重新启动会再试；模型准备成功后会保留在本机。
- 服务启动失败：查看 `data/launcher/server.log`，不会自动上传日志。
- 关闭网页不会停止服务；退出启动窗口或按 Ctrl+C 停止。再次运行入口会复用已启动的同一服务。
- 安装入口重复运行只启动已有副本，不覆盖代码和数据。需升级时先退出，维护者可用 Git 拉取最新 main，或将新 ZIP 的源码覆盖到原目录；保留 `.env`、`data/`，避免建立额外一层目录。再次启动会按新代码重建。

## 验证记录

Windows 已从没有配置、依赖或构建产物的隔离目录完成自动安装与启动，另行验证未预装 Node 时的下载、校验及执行；复用安装、重复启动和关闭服务检查通过。合并服务的欢迎页、审核、改写导出和数字人像浏览器回归通过；Paddle 与 ONNX 引擎均实际识别了示例图片的文字并验证归一化坐标。真实模式启动也通过 DeepSeek 模型列表检查和两个模块的就绪检查，未请求生成。后端自动测试 95 项通过，1 项额外的真实 OCR 集成测试默认跳过。

macOS 的脚本语法、Intel 与 Apple 芯片平台依赖检查通过，尚未在真实 Mac 上运行。Intel Mac 和 Windows 非 ASCII 安装路径使用 ONNX OCR，输出标记为 `rapidocr`，不会冒充 PaddleOCR 结果；后者避免 Paddle 原生加载器无法读取中文路径的问题。OCR 不增加图像语义审核能力。
