# RandomCAD

随机骨料颗粒生成器 - 支持 AutoCAD 和中望CAD

## 项目简介

RandomCAD 是一个专业的随机骨料颗粒生成器，用于混凝土结构建模。它支持在 AutoCAD 和中望CAD 中生成随机分布的骨料颗粒，并提供完整的参数配置和可视化功能。

## 主要特性

- ✅ **双 CAD 支持**：同时支持 AutoCAD 和中望CAD
- ✅ **多种形状**：支持多边形、圆形、椭圆等形状
- ✅ **智能碰撞检测**：使用四叉树和 KD 树优化碰撞检测
- ✅ **GPU 加速**：可选的 GPU 加速碰撞检测（需要 PyTorch）
- ✅ **分组管理**：灵活的骨料分组配置
- ✅ **现代 UI**：基于 PySide6 的现代化用户界面
- ✅ **实时预览**：实时显示生成进度和结果
- ✅ **数据导出**：支持导出骨料数据和配置

## 系统要求

- Python 3.8+
- Windows 10/11
- AutoCAD 2010+ 或中望CAD 2020+
- 4GB+ RAM
- 100MB+ 可用磁盘空间

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 CAD 软件

选择以下任一 CAD 软件：

**选项 1：AutoCAD**
- 从 [Autodesk 官网](https://www.autodesk.com.cn/) 下载并安装 AutoCAD
- 推荐版本：AutoCAD 2020-2024

**选项 2：中望CAD（推荐）**
- 从 [中望官网](https://www.zwcad.com/) 下载并安装中望CAD
- 推荐版本：中望CAD 2023-2025

### 3. 启动程序

```bash
python main.py
```

### 4. 选择 CAD 类型

在程序界面的"生成区域设置"面板中：
- 选择 "AutoCAD" 或 "中望CAD (ZWCAD)"
- 确保 CAD 软件正在运行
- 点击"连接"按钮

### 5. 配置参数

- 设置生成区域边界
- 添加骨料分组
- 配置每个分组的参数（形状、数量、大小等）

### 6. 生成骨料

- 点击"生成"按钮
- 等待生成完成
- 骨料将自动绘制到 CAD 中

## 项目结构

```
RandomCAD/
├── main.py                    # 主入口文件
├── requirements.txt           # Python 依赖
├── README.md                 # 项目说明（本文件）
├── .gitignore               # Git 忽略规则
│
├── src/                     # 源代码
│   ├── core/                # 核心功能
│   │   ├── cad_connection.py    # CAD 连接管理
│   │   ├── generator.py        # 骨料生成器
│   │   ├── shapes.py          # 形状生成
│   │   ├── collision.py       # 碰撞检测
│   │   ├── group_manager.py   # 分组管理
│   │   ├── quadtree.py        # 四叉树索引
│   │   └── kd_tree.py        # KD 树索引
│   │
│   ├── ui/                  # 用户界面
│   │   ├── main_window.py     # 主窗口
│   │   └── widgets/          # UI 组件
│   │       ├── scrollable_frame.py
│   │       ├── shape_config_widget.py
│   │       └── group_config_widget.py
│   │
│   ├── utils/               # 工具函数
│   │   └── helpers.py
│   │
│   └── configs/            # 配置
│       └── config.py
│
├── tests/                   # 测试
│   ├── test_cad_connection.py
│   ├── test_shapes.py
│   ├── test_collision.py
│   └── test_integration.py
│
├── scripts/                 # 脚本工具
│   ├── test_cad_diagnostic.py
│   └── test_cad_automated.py
│
├── docs/                   # 文档
│   ├── MODULE_STRUCTURE.md   # 模块结构
│   ├── AUTOCAD_ERROR_FIX.md # AutoCAD 错误修复
│   ├── ZWCAD_SUPPORT.md     # 中望CAD 支持说明
│   └── DEBUG_GUIDE.md      # 调试指南
│
├── output/                 # 输出目录
│   ├── aggregates/         # 生成的骨料数据
│   └── exports/           # 导出的文件
│
└── logs/                  # 日志目录
    └── randomcad.log      # 运行日志
```

## 模块说明

### 核心模块（src/core/）

- **cad_connection.py**：CAD 连接管理，支持 AutoCAD 和中望CAD
- **generator.py**：随机骨料生成器主逻辑
- **shapes.py**：各种形状的生成算法
- **collision.py**：碰撞检测算法
- **group_manager.py**：骨料分组配置管理
- **quadtree.py**：四叉树空间索引
- **kd_tree.py**：KD 树空间索引

### UI 模块（src/ui/）

- **main_window.py**：主窗口界面
- **widgets/**：自定义 UI 组件

### 工具模块（src/utils/）

- **helpers.py**：辅助函数和工具

### 配置模块（src/configs/）

- **config.py**：配置常量和默认值

## 使用指南

### 基本使用流程

1. **启动程序**
   ```bash
   python main.py
   ```

2. **连接 CAD**
   - 在"生成区域设置"面板中选择 CAD 类型
   - 点击"连接"按钮
   - 等待连接成功提示

3. **设置生成区域**
   - 输入边界坐标
   - 或选择"使用当前视图"

4. **添加骨料分组**
   - 点击"添加分组"按钮
   - 配置分组参数：
     - 分组名称
     - 形状类型（多边形/圆形/椭圆）
     - 骨料数量
     - 尺寸范围
     - 颜色

5. **生成骨料**
   - 点击"生成"按钮
   - 查看生成进度
   - 等待完成

6. **导出数据**（可选）
   - 点击"导出"按钮
   - 选择导出格式
   - 保存到文件

### 高级功能

#### ITZ（界面过渡区）生成

ITZ 是骨料与水泥浆体之间的界面过渡区，对混凝土性能有重要影响。

- 在"高级设置"中启用 ITZ
- 设置 ITZ 厚度
- 选择 ITZ 颜色

#### GPU 加速

如果安装了 PyTorch (CUDA 版本)，可以在界面中启用 GPU 加速碰撞检测：

1. **环境准备与安装**：
   - 如果已安装 CPU 版本的 PyTorch，请先卸载它：
     ```bash
     pip uninstall torch
     ```
   - 安装与系统 CUDA 12.1 兼容的 PyTorch 运行库：
     ```bash
     pip install torch==2.2.2 --index-url https://download.pytorch.org/whl/cu121
     ```
   - 验证 GPU 及 CUDA 状态：
     ```bash
     python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
     ```

2. **在软件中启用**：
   - 启动程序后，在左侧面板底部的 **"使用 GPU 加速"** 复选框中勾选。
   - 勾选后，状态标签将更新为 `GPU 加速: ✅ 已启用`。
   - 在生成高密度或大数量级的骨料时，碰撞检测的重度距离矩阵计算将被下推至 GPU 硬件加速。

#### 空间索引优化

程序自动选择最优的空间索引：

- 四叉树：适合均匀分布的骨料
- KD 树：适合非均匀分布的骨料

## 测试

### 运行所有测试

```bash
python -m pytest tests/
```

### 运行特定测试

```bash
python -m pytest tests/test_cad_connection.py
python -m pytest tests/test_shapes.py
python -m pytest tests/test_collision.py
python -m pytest tests/test_integration.py
```

### CAD 诊断

```bash
python scripts/test_cad_automated.py
```

## 故障排除

### AutoCAD 连接失败

参考 [AUTOCAD_ERROR_FIX.md](docs/AUTOCAD_ERROR_FIX.md) 文档。

### 中望CAD 连接失败

参考 [ZWCAD_SUPPORT.md](docs/ZWCAD_SUPPORT.md) 文档。

### 常见问题

1. **程序启动失败**
   - 检查 Python 版本（需要 3.8+）
   - 确保所有依赖已安装
   - 查看日志文件 `logs/randomcad.log`

2. **CAD 连接失败**
   - 确保 CAD 软件正在运行
   - 以管理员身份运行程序
   - 检查 CAD 版本兼容性

3. **生成速度慢**
   - 启用 GPU 加速（需要 PyTorch）
   - 减少骨料数量
   - 优化碰撞检测参数

## 性能优化

### 性能基准测试 (Benchmark)

我们在配置为 **Intel i5-12450H CPU + NVIDIA GeForce RTX 2050 GPU (4GB VRAM)** 的系统上进行了碰撞检测的性能测试（运行 `python benchmark_gpu.py`），生成 200 个混合形状骨料的结果如下：

- **CPU 模式**：
  - 平均耗时: `11.303s ± 3.985s`
  - 最快 / 最慢: `6.781s / 14.301s`
- **GPU 模式 (RTX 2050)**：
  - 平均耗时: `14.028s ± 3.225s`
  - 最快 / 最慢: `11.341s / 17.604s`

> [!NOTE]
> **GPU 加速交叉点 (Crossover Point)**
> 在生成小数量级（如 < 500 个）骨料时，GPU 的数据打包、显存传输（CPU-GPU 通信）以及 CUDA 核函数启动开销可能会抵消并行计算的优势，导致 CPU 运行更快（本测试中 CPU 稍快约 19%）。
> 当骨料数量增加（例如 500 到 1000+ 个）且碰撞检测候选集庞大时，GPU 的并行吞吐优势会成倍体现，因此在大规模建模时启用 GPU 加速非常关键。

### 优化建议

1. **小规模生成 (< 300 骨料)**：建议使用默认的 CPU + 四叉树/KD 树索引，响应极速。
2. **大规模生成 (> 500 骨料)**：强烈建议启用 **GPU 加速**（勾选“使用 GPU 加速”）。
3. **空间索引选择**：
   - **四叉树**：适合均匀分布的骨料。
   - **KD 树**：适合非均匀分布的骨料。
4. **合理密实度**：过高的目标面积占比（如 > 0.6）会导致后期生成尝试次数激增，建议适当调大生成区域或调整粒径。

## 扩展开发

### 添加新的形状类型

1. 在 `src/core/shapes.py` 中添加形状生成逻辑
2. 在 `ShapeType` 枚举中添加新类型
3. 在 UI 中添加配置选项

### 添加新的 CAD 支持

1. 在 `src/core/cad_connection.py` 中添加 CAD 类型
2. 实现 CAD 特定的连接逻辑
3. 在 UI 中添加 CAD 类型选择

详细开发指南请参考 [MODULE_STRUCTURE.md](docs/MODULE_STRUCTURE.md)。

## 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 贡献流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范

- 遵循 PEP 8 代码风格
- 添加适当的注释和文档字符串
- 为新功能添加测试
- 更新相关文档

## 许可证

[待定]

## 联系方式

- 项目主页：[待定]
- 问题反馈：[待定]
- 邮箱：[待定]

## 致谢

感谢所有贡献者和用户的支持！

## 更新日志

### v2.0.1 (2025-12-25)

- ✅ 新增中望CAD（ZWCAD）支持
- ✅ 优化 CAD 连接错误检测
- ✅ 添加 CAD 安装自动检测
- ✅ 改进错误提示和诊断工具
- ✅ 重构代码结构，提高可维护性

### v2.0.0 (2025-12-25)

- ✅ 完全重构，使用 PySide6 UI
- ✅ 添加 CAD 连接状态监控
- ✅ 实现自动重连机制
- ✅ 添加心跳检测
- ✅ 优化碰撞检测性能
- ✅ 添加空间索引（四叉树、KD 树）
- ✅ 支持多种形状类型
- ✅ 添加分组管理功能

---

**最后更新**：2025-12-25  
**版本**：v2.0.1  
**维护者**：RandomCAD 开发团队
