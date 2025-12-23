project_root/
│
├── main.py                 # 主程序入口
├── config.py               # 配置和常量
├── utils.py                # 通用工具
│
├── core/                   # 核心逻辑包
│   ├── __init__.py
│   ├── generator.py        # 核心生成器类 (RandomAggregateGenerator)
│   ├── shapes.py           # 形状生成逻辑
│   ├── collision.py        # 碰撞检测逻辑 (check_collision_shapely)
│   └── group_manager.py    # 组管理逻辑
│
└── ui/                     # 用户界面包
    ├── __init__.py
    ├── widgets.py          # 自定义UI组件 (如 ScrollableFrame)
    └── main_window.py      # 主窗口类 (AggregateGeneratorGUI)