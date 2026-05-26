# RandomCAD 模块化结构文档

## 项目概述

RandomCAD 是一个随机骨料颗粒生成器，支持 AutoCAD 和中望CAD，使用 PySide6 构建 UI。

## 目录结构

```
RandomCAD/
├── main.py                          # 主入口文件
├── requirements.txt                 # Python 依赖列表
├── README.md                        # 项目说明文档
├── .gitignore                       # Git 忽略规则
│
├── src/                             # 源代码根目录
│   ├── __init__.py                  # 包初始化文件
│   │
│   ├── core/                        # 核心功能模块
│   │   ├── __init__.py             # 核心模块初始化
│   │   ├── cad_connection.py       # CAD 连接管理（AutoCAD/中望CAD）
│   │   ├── generator.py            # 随机骨料生成器
│   │   ├── shapes.py               # 形状生成算法
│   │   ├── collision.py            # 碰撞检测
│   │   ├── group_manager.py        # 分组配置管理
│   │   ├── quadtree.py             # 四叉树空间索引
│   │   └── kd_tree.py             # KD树空间索引
│   │
│   ├── ui/                         # 用户界面模块
│   │   ├── __init__.py            # UI 模块初始化
│   │   ├── main_window.py         # 主窗口
│   │   └── widgets/               # UI 组件子模块
│   │       ├── __init__.py        # 组件模块初始化
│   │       ├── scrollable_frame.py # 可滚动框架
│   │       ├── shape_config_widget.py  # 形状配置组件
│   │       └── group_config_widget.py  # 分组配置组件
│   │
│   ├── utils/                      # 工具函数模块
│   │   ├── __init__.py            # 工具模块初始化
│   │   └── helpers.py            # 辅助函数
│   │
│   └── configs/                   # 配置模块
│       ├── __init__.py            # 配置模块初始化
│       └── config.py              # 配置常量和默认值
│
├── tests/                          # 测试模块
│   ├── __init__.py                # 测试模块初始化
│   ├── test_cad_connection.py     # CAD 连接测试
│   ├── test_shapes.py             # 形状生成测试
│   ├── test_collision.py          # 碰撞检测测试
│   └── test_integration.py        # 集成测试
│
├── docs/                           # 文档目录
│   ├── README.md                  # 项目说明
│   ├── ARCHITECTURE.md            # 架构设计文档
│   ├── API.md                     # API 文档
│   ├── AUTOCAD_ERROR_FIX.md       # AutoCAD 错误修复
│   ├── ZWCAD_SUPPORT.md           # 中望CAD 支持说明
│   └── DEBUG_GUIDE.md            # 调试指南
│
├── scripts/                        # 脚本工具
│   ├── diagnose_cad.py            # CAD 诊断工具
│   └── test_cad_automated.py     # 自动化测试工具
│
├── logs/                           # 日志目录（运行时生成）
│   └── randomcad.log              # 运行日志
│
└── output/                         # 输出目录（运行时生成）
    ├── aggregates/                # 生成的骨料数据
    └── exports/                   # 导出的文件
```

## 模块说明

### 1. 主入口模块（main.py）

**职责**：程序入口点，初始化日志，启动 UI

**功能**：
- 配置日志系统
- 导入并启动主窗口
- 处理程序退出

**依赖**：
- `src.ui.main_window`

### 2. 核心模块（src/core/）

#### 2.1 cad_connection.py

**职责**：CAD 连接管理

**功能**：
- 连接 AutoCAD/中望CAD
- 状态监控和自动重连
- 心跳检测
- COM 资源管理
- 绘制边界和骨料

**主要类**：
- `CADConnection` - CAD 连接管理器
- `CADType` - CAD 类型枚举
- `ConnectionState` - 连接状态枚举

**依赖**：
- `comtypes`
- `pyautocad`（仅 AutoCAD）
- `winreg`（Windows 注册表）

#### 2.2 generator.py

**职责**：随机骨料生成器

**功能**：
- 生成随机骨料
- 碰撞检测
- ITZ（界面过渡区）生成
- 生成进度跟踪

**主要类**：
- `RandomAggregateGenerator` - 随机骨料生成器

**依赖**：
- `src.core.cad_connection`
- `src.core.shapes`
- `src.core.collision`
- `src.core.group_manager`

#### 2.3 shapes.py

**职责**：形状生成算法

**功能**：
- 生成多边形骨料
- 生成圆形骨料
- 生成椭圆骨料
- 形状参数化

**主要类**：
- `ShapeGenerator` - 形状生成器
- `ShapeType` - 形状类型枚举

**依赖**：
- `numpy`
- `shapely`

#### 2.4 collision.py

**职责**：碰撞检测

**功能**：
- 多边形碰撞检测
- 圆形碰撞检测
- GPU 加速（可选）
- 空间索引优化

**主要类**：
- `CollisionDetector` - 碰撞检测器

**依赖**：
- `numpy`
- `shapely`
- `torch`（可选，GPU 加速）

#### 2.5 group_manager.py

**职责**：分组配置管理

**功能**：
- 管理骨料分组
- 分组参数配置
- 分组统计

**主要类**：
- `GroupManager` - 分组管理器
- `GroupConfig` - 分组配置

**依赖**：
- `dataclasses`

#### 2.6 quadtree.py

**职责**：四叉树空间索引

**功能**：
- 构建四叉树
- 快速空间查询
- 碰撞检测优化

**主要类**：
- `QuadTree` - 四叉树
- `QuadTreeNode` - 四叉树节点

**依赖**：
- `numpy`

#### 2.7 kd_tree.py

**职责**：KD树空间索引

**功能**：
- 构建 KD 树
- 最近邻查询
- 范围查询

**主要类**：
- `KDTree` - KD 树
- `KDTreeNode` - KD 树节点

**依赖**：
- `numpy`

### 3. 用户界面模块（src/ui/）

#### 3.1 main_window.py

**职责**：主窗口

**功能**：
- UI 布局
- 事件处理
- 信号槽连接
- 生成控制

**主要类**：
- `MainWindow` - 主窗口

**依赖**：
- `PySide6.QtWidgets`
- `PySide6.QtCore`
- `src.core.generator`
- `src.ui.widgets`

#### 3.2 widgets/ 子模块

##### 3.2.1 scrollable_frame.py

**职责**：可滚动框架

**功能**：
- 提供可滚动容器
- 自动布局管理

**主要类**：
- `ScrollableFrame` - 可滚动框架

**依赖**：
- `PySide6.QtWidgets`

##### 3.2.2 shape_config_widget.py

**职责**：形状配置组件

**功能**：
- 形状参数配置
- 参数验证
- UI 交互

**主要类**：
- `ShapeConfigWidget` - 形状配置组件

**依赖**：
- `PySide6.QtWidgets`
- `src.core.shapes`

##### 3.2.3 group_config_widget.py

**职责**：分组配置组件

**功能**：
- 分组管理 UI
- 分组参数配置
- 分组列表显示

**主要类**：
- `GroupConfigWidget` - 分组配置组件

**依赖**：
- `PySide6.QtWidgets`
- `src.core.group_manager`

### 4. 工具模块（src/utils/）

#### 4.1 helpers.py

**职责**：辅助函数

**功能**：
- 数据转换
- 格式化
- 验证
- 日志辅助

**依赖**：
- `typing`
- `logging`

### 5. 配置模块（src/configs/）

#### 5.1 config.py

**职责**：配置常量和默认值

**功能**：
- 定义默认参数
- 配置管理
- 常量定义

**依赖**：
- `dataclasses`

### 6. 测试模块（tests/）

#### 6.1 test_cad_connection.py

**职责**：测试 CAD 连接

**功能**：
- 测试 AutoCAD 连接
- 测试中望CAD 连接
- 测试连接状态管理

#### 6.2 test_shapes.py

**职责**：测试形状生成

**功能**：
- 测试多边形生成
- 测试圆形生成
- 测试椭圆生成

#### 6.3 test_collision.py

**职责**：测试碰撞检测

**功能**：
- 测试碰撞检测算法
- 测试空间索引
- 性能测试

#### 6.4 test_integration.py

**职责**：集成测试

**功能**：
- 端到端测试
- 完整流程测试

### 7. 文档模块（docs/）

#### 7.1 README.md

**职责**：项目说明

**内容**：
- 项目介绍
- 功能特性
- 安装指南
- 使用说明

#### 7.2 ARCHITECTURE.md

**职责**：架构设计文档

**内容**：
- 系统架构
- 模块关系
- 设计模式
- 扩展性考虑

#### 7.3 API.md

**职责**：API 文档

**内容**：
- 类和方法说明
- 参数说明
- 返回值说明
- 使用示例

#### 7.4 AUTOCAD_ERROR_FIX.md

**职责**：AutoCAD 错误修复

**内容**：
- 错误分析
- 解决方案
- 故障排除

#### 7.5 ZWCAD_SUPPORT.md

**职责**：中望CAD 支持说明

**内容**：
- 中望CAD 集成
- 安装说明
- 使用方法
- 故障排除

#### 7.6 DEBUG_GUIDE.md

**职责**：调试指南

**内容**：
- 调试方法
- 常见问题
- 日志分析

### 8. 脚本工具（scripts/）

#### 8.1 diagnose_cad.py

**职责**：CAD 诊断工具

**功能**：
- 检测 CAD 安装
- 测试 CAD 连接
- 生成诊断报告

#### 8.2 test_cad_automated.py

**职责**：自动化测试工具

**功能**：
- 自动化 CAD 连接测试
- 依赖检查
- 安装检测

## 模块依赖关系

```
main.py
  └─ src.ui.main_window
        ├─ src.core.generator
        │     ├─ src.core.cad_connection
        │     ├─ src.core.shapes
        │     ├─ src.core.collision
        │     │     ├─ src.core.quadtree
        │     │     └─ src.core.kd_tree
        │     └─ src.core.group_manager
        └─ src.ui.widgets
              ├─ src.ui.widgets.scrollable_frame
              ├─ src.ui.widgets.shape_config_widget
              │     └─ src.core.shapes
              └─ src.ui.widgets.group_config_widget
                    └─ src.core.group_manager
```

## 设计原则

### 1. 单一职责原则
每个模块只负责一个明确的功能领域。

### 2. 低耦合高内聚
模块间通过清晰的接口通信，内部实现高度内聚。

### 3. 依赖注入
通过构造函数或方法参数传递依赖，避免硬编码。

### 4. 接口隔离
定义清晰的接口，客户端只依赖需要的接口。

### 5. 开闭原则
对扩展开放，对修改关闭。

## 扩展指南

### 添加新的形状类型

1. 在 `src/core/shapes.py` 中添加形状生成逻辑
2. 在 `ShapeType` 枚举中添加新类型
3. 在 `src/ui/widgets/shape_config_widget.py` 中添加配置 UI

### 添加新的 CAD 支持

1. 在 `src/core/cad_connection.py` 中添加 CAD 类型
2. 实现 CAD 特定的连接逻辑
3. 在 UI 中添加 CAD 类型选择

### 添加新的空间索引

1. 在 `src/core/` 中创建新的索引模块
2. 在 `src/core/collision.py` 中集成新索引
3. 添加性能测试

## 维护指南

### 修改核心功能
- 修改 `src/core/` 中的模块
- 更新相关测试
- 更新 API 文档

### 修改 UI
- 修改 `src/ui/` 中的模块
- 保持向后兼容
- 更新用户文档

### 添加新功能
- 在相应的模块中添加代码
- 添加单元测试
- 更新文档

### 修复 Bug
- 在 `tests/` 中添加回归测试
- 更新相关文档
- 记录修复内容

## 版本控制

### 分支策略
- `main` - 主分支，稳定版本
- `develop` - 开发分支
- `feature/*` - 功能分支
- `bugfix/*` - 修复分支

### 提交规范
- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `refactor:` - 重构
- `test:` - 测试
- `chore:` - 构建/工具

## 性能优化

### 空间索引
- 使用四叉树或 KD 树优化碰撞检测
- 根据骨料数量选择合适的索引

### 并行处理
- 使用多线程生成骨料
- 使用 GPU 加速碰撞检测（可选）

### 内存管理
- 及时释放 CAD 对象
- 使用生成器处理大量数据

## 安全考虑

### CAD 连接
- 验证 CAD 版本兼容性
- 处理 COM 异常
- 资源清理

### 数据验证
- 验证用户输入
- 检查参数范围
- 防止注入攻击

---

**文档版本**：v1.0  
**最后更新**：2025-12-25  
**维护者**：RandomCAD 开发团队
