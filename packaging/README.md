# RandomCAD 独立可执行程序 (.exe) 打包构建指南

为了方便非开发人员直接安装和运行 RandomCAD，我们设计了专用的打包机制。这使得您不需要配置 Python 开发环境，即可直接开箱使用。

我们通过新建的打包目录进行封装，**不影响主项目 `src/` 中的任何原始代码**。

---

## 📂 打包目录结构

- [**`packaging/run_app.py`**](file:///c:/Users/77271/Desktop/RandomCAD/packaging/run_app.py)：打包启动引导器。负责在打包沙盒内将 `comtypes` 所需的动态代码生成目录重定向至系统临时目录，从而解决 CAD 连接的写权限报错；同时负责在启动时动态加载系统中的 Python 环境（供轻量级版本调用全局 PyTorch）。
- [**`packaging/build_exe.py`**](file:///c:/Users/77271/Desktop/RandomCAD/packaging/build_exe.py)：打包自动化构建脚本。自动安装 PyInstaller 依赖，提供交互式参数选择，并按规则编译。

---

## ⚙️ 打包模式对比

为了平衡可执行文件的体积和 GPU 加速的便携性，我们提供了以下两种打包模式：

| 模式 | 大小 | 特点 | 适用场景 |
| :--- | :--- | :--- | :--- |
| **1. 轻量级模式 (推荐)** | **~60 MB** | 排除 `torch` 依赖包，体积小。默认以 CPU 碰撞检测运行。如果用户电脑上安装了 Python + PyTorch，运行 .exe 时会自动检测并调用，**仍可享用 GPU 加速**。 | 分发给一般用户、仅生成少量骨料或本地已有 PyTorch 环境的机器。 |
| **2. 完整模式** | **>1.5 GB** | 打包完整的 `torch` 科学计算和 CUDA 加速库。完全独立，开箱即可使用 GPU 加速，但体积非常臃肿，构建极慢。 | 分发给完全没有 Python 安装经验、同时有海量骨料（1000+ 颗粒）高密度生成需求的高端显卡用户。 |

---

## 🛠️ 打包运行步骤

1. 打开 Windows PowerShell（或命令行工具），进入项目的根目录。
2. 运行打包构建脚本：
   ```bash
   python packaging/build_exe.py
   ```
3. 根据屏幕提示进行选择：
   - 输入 `1` 编译轻量版，输入 `2` 编译完整版。
   - 输入 `A` 生成单一 `.exe` 文件（方便拷贝），输入 `B` 生成解压文件夹（启动速度快）。
4. 等待 PyInstaller 运行完毕，生成的成品将存放在：
   - `packaging/dist/RandomCAD/` (文件夹模式)
   - `packaging/dist/RandomCAD.exe` (单文件模式)

---

## ⚠️ 常见打包故障排除

### 1. 杀毒软件误报
PyInstaller 生成的单文件 `.exe` 偶尔会被 Windows Defender 等防病毒软件误报威胁。这是打包机制的常见误报，请在防火墙中添加信任或将打包模式改为 **文件夹模式 (B)** 即可解决。

### 2. comtypes 动态生成警告
在打包版本运行连接 CAD 时，程序会自动在系统的 `Temp/comtypes_cache` 下生成 CAD 动态库文件。这是正常现象，请不要删除正在运行中的缓存文件。
