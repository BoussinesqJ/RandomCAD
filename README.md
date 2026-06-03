# RandomCAD

**混凝土细观结构随机骨料颗粒生成器** — 支持 AutoCAD & 中望CAD

> 面向混凝土数值模拟 (FEM) 和采空区邻位充填二维细观建模，生成符合真实级配的随机多边形/圆形/椭圆形骨料分布，并通过 COM 自动化直接绘制到 AutoCAD 或中望CAD。

---

## 目录

- [功能亮点](#功能亮点)
- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [架构概览](#架构概览)
- [模块详解](#模块详解)
- [核心算法](#核心算法)
- [性能基准与优化建议](#性能基准与优化建议)
- [使用指南](#使用指南)
- [测试](#测试)
- [故障排除](#故障排除)
- [扩展开发](#扩展开发)
- [贡献指南](#贡献指南)
- [引用方式](#引用方式)
- [许可证](#许可证)
- [更新日志](#更新日志)

---

## 功能亮点

| 特性 | 说明 |
|------|------|
| **双 CAD 支持** | AutoCAD 2010+（pyautocad）与中望CAD 2020+（comtypes 原生 COM）无缝切换 |
| **多形状级配** | 单组内同时勾选多边形、圆形、椭圆形，按权重随机混合生成 |
| **智能碰撞检测** | 空间索引 → AABB 宽相 → Shapely 窄相 三阶段分层流水线 |
| **GPU 加速** | 可选 PyTorch CUDA 加速 AABB 重叠检测，大规模生成（500+ 骨料）显著提速 |
| **自适应并行** | 线程池根据实时成功率动态调整 worker 数量 |
| **ITZ 界面过渡区** | 自动生成骨料周围界面过渡区（通过 Shapely buffer） |
| **实时双通道渲染** | 本地 QGraphicsView 预览 + CAD COM 同步绘制 |
| **数据导出** | CSV / JSON 格式导出完整骨料元数据 |
| **无 CAD 亦可用** | 未安装 CAD 时自动切换为本地独立预览模式 |

---

## 系统要求

- **操作系统**：Windows 10/11
- **Python**：3.8+
- **CAD 软件**：AutoCAD 2010+ 或 中望CAD 2020+（可选，无 CAD 亦可运行预览）
- **内存**：4GB+ RAM
- **磁盘**：100MB+ 可用空间
- **可选**：NVIDIA GPU + CUDA 12.1（用于 GPU 加速碰撞检测）

---

## 快速开始

### 方式 A：独立可执行文件 (.exe) [推荐]

无需配置 Python 环境，直接编译运行：

```bash
python packaging/build_exe.py
# 产物位于 packaging/dist/RandomCAD.exe
```

详细打包说明见 [packaging/README.md](packaging/README.md)。

### 方式 B：源码运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 确保至少一个 CAD 软件正在运行（可选）

# 3. 启动程序
python main.py
```

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│  main.py  ─── 配置日志 → 启动 src.ui.main_window.main()   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  src/ui/          UI 层 (PySide6)                          │
│  ├─ main_window.py         主窗口，双通道渲染调度           │
│  └─ widgets/               自定义组件                       │
│     ├─ preview_widget.py   QGraphicsView 2D 画布            │
│     ├─ group_config_widget.py   分组参数编辑器              │
│     ├─ shape_config_widget.py   形状参数编辑器              │
│     └─ scrollable_frame.py      可滚动容器                  │
└─────────────────────────────────────────────────────────────┘
         │ 依赖
         ▼
┌─────────────────────────────────────────────────────────────┐
│  src/core/        核心逻辑层                                │
│  ├─ generator.py           生成器主引擎（自适应并行）       │
│  ├─ cad_connection.py      CAD COM 自动化（双 CAD 支持）   │
│  ├─ shapes.py              纯几何形状生成                   │
│  ├─ collision.py           分层碰撞检测（可选 GPU）         │
│  ├─ group_manager.py       分组配置与进度管理               │
│  ├─ quadtree.py            四叉树空间索引                   │
│  ├─ kd_tree.py             KD 树空间索引                    │
│  └─ spatial_index.py       SpatialIndex 统一接口协议        │
└─────────────────────────────────────────────────────────────┘
         │ 依赖
         ▼
┌─────────────────────────────────────────────────────────────┐
│  src/utils/       工具层  │  src/configs/   配置层          │
│  └─ helpers.py             │  └─ config.py                  │
└─────────────────────────────────────────────────────────────┘
```

**依赖方向**：`main.py` → `ui` → `core` → `utils` + `configs`（单向，无循环依赖）

---

## 模块详解

### 核心层 (`src/core/`)

#### `generator.py` — 生成器主引擎（~1105 行）

系统的中枢，`RandomAggregateGenerator` 类编排完整的生成流水线：

- **两种生成模式**：`count`（按数量填充）/ `porosity`（按孔隙率填充）
- **试件类型**：矩形 / 圆形边界
- **主循环**：使用 `ThreadPoolExecutor` 提交候选放置，接受首个无碰撞结果，取消其余任务
- **自适应并行**：每 5 秒监控成功率，动态调整 worker 数
- **停滞检测**：连续 500 次失败或 60 秒无进展 → 自动停止
- **边界调整**：将靠近边界的骨料推至边缘，使 ITZ 层贴合边界
- **回调解耦**：通过 `('aggregate', points, color, layer)` 元组回调将生成与渲染分离

#### `cad_connection.py` — CAD 连接层（~778 行）

统一的 COM 自动化抽象：

- **双 CAD 引擎**：AutoCAD（`pyautocad.Autocad`）与中望CAD（`comtypes.client` 原生 COM）
- **Windows 注册表扫描**：自动检测已安装的 CAD 版本
- **心跳守护线程**：5 秒间隔检查 `_doc.Name` 存活状态
- **自动重连**：指数退避策略，最多 3 次重试，2 秒基础延迟
- **观察者模式**：状态变更通过 `_state_callbacks` 通知监听者
- **线程安全**：`threading.Lock` 保护连接操作，子线程 COM 初始化显式处理

#### `shapes.py` — 纯几何生成（~201 行）

无状态函数，返回 `List[Tuple[float, float]]`：

| 函数 | 说明 |
|------|------|
| `generate_random_polygon()` | 不规则凸多边形（高斯角度扰动 + 最短边优化） |
| `generate_circle()` | 参数化圆形 |
| `generate_ellipse()` | 参数化旋转椭圆 |

#### `collision.py` — 分层碰撞检测（~182 行）

三阶段流水线：

1. **空间索引**：Quadtree / KDTree 缩小候选集
2. **宽相 AABB**：GPU（PyTorch CUDA tensor）或 CPU 批量轴对齐包围盒重叠检测
3. **窄相精确**：Shapely `intersects()` 多边形精确相交判定

支持 `allow_touching` 模式（允许骨料边缘接触）。

#### `quadtree.py` / `kd_tree.py` — 空间索引

两种可互换的空间索引实现，通过 `SpatialIndex` Protocol（`spatial_index.py`）统一接口：

| 接口方法 | 说明 |
|----------|------|
| `insert(obj)` | 插入单个对象 |
| `insert_batch(objects)` | 批量插入 |
| `query_range(bounds)` | 按范围查询 |
| `query_shapely(obj, min_distance)` | 按 Shapely 对象查询 |
| `clear()` | 清空索引 |
| `get_stats()` | 获取统计信息 |

- **Quadtree**：经典区域四叉树，`max_objects=10`，`max_depth=5` 时分裂
- **KDTree**：自适应 KD 树，沿中位数交替 X/Y 轴切分，缓存对象边界框

#### `group_manager.py` — 分组管理（~153 行）

管理多个骨料分组的配置和运行时状态：

- 每组：`id`, `area_ratio`, `itz_thickness`, `max_count`, `layer_color`, `shapes[]`
- 运行时统计：`target_area`, `generated_area`, `count`
- 贪心平衡策略：`select_next_group()` 选择进度最低的分组

---

### UI 层 (`src/ui/`)

#### `main_window.py` — 主窗口（~1108 行）

基于 PySide6 的单窗口应用：

- **左侧面板**（400px 固定宽度）：可滚动控制区域，包含区域设置、分组管理、生成模式、参数配置、进度条、操作按钮
- **右侧面板**：`PreviewWidget` 预览画布（弹性填充）
- **`GenerationWorker(QThread)`**：后台线程执行生成，通过 Qt 信号桥接主线程
- **双通道渲染**：draw_command 信号同时派发到本地 `PreviewWidget` 和 CAD `draw_aggregate()`
- **"同步到 CAD"**：本地预览满意后一键同步导入 CAD

#### `preview_widget.py` — 本地画布（~234 行）

自定义 `QGraphicsView` 2D 画布：

- Y 轴翻转（`scale(1, -1)`），匹配 CAD/笛卡尔坐标系
- 鼠标滚轮缩放 + 拖拽平移
- 装饰性画笔（线宽不随缩放变化）
- 分层渲染：骨料 z=2，ITZ z=1（半透明），边界 z=-10（虚线）

---

### 工具层与配置层

#### `utils/helpers.py`（~244 行）

无状态数学工具：`clip`, `calculate_polygon_area`（鞋带公式）, `calculate_bounding_circle`, `is_near_boundary`, `move_toward_boundary`, `adjust_points_to_boundary` 等。

#### `configs/config.py`（~86 行）

- `SpecimenType` 枚举（RECTANGLE / CIRCLE）
- `CADColorMap`（7 种 AutoCAD 颜色索引 + 中文名称）
- 各类默认参数（区域、形状、分组、生成参数）

---

## 核心算法

### 随机骨料放置算法

```
对于每个分组（按进度贪心选择）：
    重复直到达到目标（数量 / 孔隙率）：
        1. 在边界内随机采样候选中心点
        2. 按权重随机选择形状类型（多边形/圆/椭圆）
        3. 在尺寸范围内随机生成形状参数
        4. 多线程并行提交候选放置：
            a. 空间索引查询邻近骨料
            b. AABB 宽相快速排除
            c. Shapely 窄相精确碰撞检测
        5. 接受首个无碰撞候选，取消其余任务
        6. 插入空间索引，更新进度
        7. 停滞检测：连续失败 500 次 或 60 秒无进展 → 停止
```

### 自适应并行策略

```
每 5 秒：
    计算成功率 = 成功数 / (成功数 + 失败数)
    if 成功率 < 20%:
        减少 worker 数（区域趋近饱和，减少无效竞争）
    elif 成功率 > 80%:
        增加 worker 数（仍有大量空间，提高吞吐）
```

### ITZ 生成

对每个已放置的骨料多边形执行 Shapely `buffer(itz_thickness)`，生成等距偏移轮廓作为界面过渡区。

---

## 性能基准与优化建议

**测试环境**：Intel i5-12450H + NVIDIA GeForce RTX 2050 (4GB VRAM)

| 模式 | 200 个骨料平均耗时 | 最快 / 最慢 |
|------|-------------------|-------------|
| CPU | 11.303s ± 3.985s | 6.781s / 14.301s |
| GPU (RTX 2050) | 14.028s ± 3.225s | 11.341s / 17.604s |

> **GPU 加速交叉点**：小规模（< 500 骨料）时 GPU 的数据传输和 CUDA 启动开销可能抵消并行优势；大规模（500~1000+）时 GPU 并行吞吐优势成倍体现。

### 优化建议

| 场景 | 推荐配置 |
|------|----------|
| 小规模（< 300 骨料） | CPU + 四叉树/KD 树索引 |
| 大规模（> 500 骨料） | 启用 GPU 加速 |
| 均匀分布 | 四叉树索引 |
| 非均匀分布 | KD 树索引 |
| 高密实度（> 0.6） | 调大生成区域或调整粒径，避免后期尝试次数激增 |

---

## 使用指南

### 基本流程

```
启动程序 → 选择 CAD 类型 → 连接 CAD → 设置边界 → 配置分组 → 点击生成 → 导出数据
```

1. **启动**：`python main.py`
2. **连接 CAD**：左侧面板选择 AutoCAD/中望CAD，点击"连接"（可选，无 CAD 亦可本地预览）
3. **设置区域**：输入边界坐标或选择"使用当前视图"
4. **配置分组**：添加分组，设置形状类型、数量/占比、尺寸范围、颜色
5. **生成**：点击"生成"，查看进度条和实时预览
6. **同步**：本地预览满意后点击"同步绘制到 CAD"
7. **导出**：点击"导出"保存 CSV/JSON 数据

### GPU 加速启用

```bash
# 如已安装 CPU 版 PyTorch，先卸载
pip uninstall torch

# 安装 CUDA 12.1 版本
pip install torch==2.2.2 --index-url https://download.pytorch.org/whl/cu121

# 验证
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

程序启动后勾选左侧面板底部的 **"使用 GPU 加速"** 复选框。

---

## 测试

```bash
# 运行全部测试 (99 个)
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_helpers.py        # 42 个 - 工具函数
python -m pytest tests/test_quadtree.py       # 10 个 - 四叉树
python -m pytest tests/test_kd_tree.py        #  7 个 - KD 树
python -m pytest tests/test_shapes.py         # 17 个 - 形状生成
python -m pytest tests/test_collision.py      #  8 个 - 碰撞检测
python -m pytest tests/test_cad_connection.py #  5 个 - CAD 连接
python -m pytest tests/test_integration.py    # 10 个 - 集成测试

# CAD 诊断
python scripts/test_cad_automated.py

# GPU 性能基准
python benchmark_gpu.py
```

---

## 故障排除

| 问题 | 排查步骤 |
|------|----------|
| 程序启动失败 | 检查 Python ≥ 3.8；`pip install -r requirements.txt`；查看 `logs/randomcad.log` |
| CAD 连接失败 | 确保 CAD 正在运行；以管理员身份运行；检查版本兼容性；参考 [AUTOCAD_ERROR_FIX.md](docs/AUTOCAD_ERROR_FIX.md) / [ZWCAD_SUPPORT.md](docs/ZWCAD_SUPPORT.md) |
| 生成速度慢 | 启用 GPU 加速；减少骨料数量；优化空间索引选择 |
| 碰撞检测不准 | 检查 `allow_touching` 设置；确认 ITZ 厚度参数 |

---

## 扩展开发

### 添加新形状类型

1. `src/core/shapes.py`：实现生成函数，返回 `List[Tuple[float, float]]`
2. `src/core/collision.py`：确保碰撞检测兼容新形状
3. `src/ui/widgets/shape_config_widget.py`：添加 UI 配置面板

### 添加新 CAD 支持

1. `src/core/cad_connection.py`：在 `CADType` 枚举中添加新类型
2. 实现连接/断开/绘制方法
3. `src/ui/main_window.py`：在 CAD 类型选择器中添加选项

详细模块结构说明见 [docs/MODULE_STRUCTURE.md](docs/MODULE_STRUCTURE.md)。

---

## 贡献指南

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'feat: add your feature'`
4. 推送：`git push origin feature/your-feature`
5. 开启 Pull Request

**代码规范**：遵循 PEP 8；添加 docstring；新功能需附带测试。

---

## 引用方式

如在学术研究或工程设计中使用本项目：

### 文本引用

> BoussinesqJ. RandomCAD: 适用于混凝土与采空区充填细观结构建模的高性能随机骨料颗粒生成器 [OL]. GitHub, 2026. https://github.com/BoussinesqJ/RandomCAD.

### BibTeX

```bibtex
@misc{randomcad2026,
  author = {BoussinesqJ},
  title = {RandomCAD: A High-Performance Random Aggregate Generator for Concrete and Gob Backfilling Modeling},
  year = {2026},
  publisher = {GitHub},
  journal = {GitHub Repository},
  howpublished = {\url{https://github.com/BoussinesqJ/RandomCAD}}
}
```

---

## 许可证

本项目采用 [MIT License](LICENSE) 授权许可。

---

## 更新日志

### v1.1 (2026-06-04)

- **🐛 Bug 修复**：
  - 修复 `status_label` 显示字面量 `"info"` 而非实际消息内容
  - 修复 `is_near_boundary` / `move_toward_boundary` / `adjust_points_to_boundary` 忽略 `min_distance` 参数
  - 移除 `_generate_single_aggregate` 中不必要的 `PYAUTOCAD_AVAILABLE` 守卫，纯本地预览模式可正常生成
  - 修复 `quadtree.clear()` 中误导性的局部变量赋值
  - 修复 `benchmark_gpu.py` 形状配置键名与实际 schema 不匹配
- **🔒 线程安全与资源管理**：
  - 生成器共享数据加 `_state_lock` 线程锁保护并发读写
  - `CADConnection` 新增 `__enter__`/`__exit__` 上下文管理器
  - `import winreg` 改为平台守卫，非 Windows 平台不再崩溃
- **⚡ 性能优化**：
  - GPU 碰撞检测新增 tensor 缓存，避免重复创建 existing bounds tensor
  - 线程池不再每 5 秒 shutdown+recreate，固定 `max_workers=12` 通过任务数控制并行度
- **🏗️ 架构重构**：
  - `cad_connection.py`：抽取 `_draw_polyline()` 公共方法，`draw_boundary`/`draw_aggregate` 委托调用
  - `shapes.py`：移除重复的 `calculate_distance`，统一从 `helpers.py` 导入
  - 新增 `SpatialIndex` Protocol，`Quadtree` 和 `KDTree` 实现统一接口
  - `generator.py`：`Union[Quadtree, KDTree]` 类型提示替换为 `SpatialIndex`
  - `helpers.py`：新增 `_get_xy()` 辅助函数，几何函数同时支持 tuple 和对象访问；移除 `generator.py` 中所有 `APoint` 耦合
- **🧪 测试覆盖**：
  - 新增 `test_helpers.py`（42 个测试）、`test_quadtree.py`（10 个）、`test_kd_tree.py`（7 个），总计 99 个测试全部通过
- **✨ 功能增强**：
  - UI 多边形参数面板新增「不规则度」「尖锐度」「优化短边」可配置控件
  - `load_config` 新增完整错误处理（文件不存在、JSON 解析失败、格式校验）
  - `_sync_to_cad` 支持圆形试件边界绘制（不再只画矩形）

### v1.0 (2026-05-26)

- **✨ 本地自适应预览画布**：基于 QGraphicsView 的独立 2D 画布，支持与 CAD 双通道实时渲染；新增"同步绘制到 CAD"功能
- **✨ 单组多形状级配**：各分组内支持多边形/圆形/椭圆形按权重混合生成
- **🚀 GPU 碰撞检测加速**：集成 PyTorch CUDA 12.1，界面新增 GPU 开关
- **📊 性能基准测试工具**：新增 `benchmark_gpu.py`，实测 RTX 2050 与 CPU 模式耗时
- **📦 独立 .exe 打包**：新增 `packaging/` 目录，支持单文件/文件夹格式发布
- **📝 文档与规范**：补充 MIT 许可证、BibTeX 引用；更新路线图至采空区充填建模
- ✅ 新增中望CAD（ZWCAD）支持
- ✅ CAD 连接状态监控 + 自动重连 + 心跳检测
- ✅ 空间索引优化（四叉树、KD 树）
- ✅ 多形状支持 + 分组管理功能
- ✅ 完全重构，使用 PySide6 UI

---

**最后更新**：2026-06-04
**版本**：v1.1
**维护者**：BoussinesqJ
