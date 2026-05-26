# 中望CAD (ZWCAD) 支持说明

## 概述

RandomCAD v2.0 现在支持两种CAD软件：
1. **AutoCAD** - Autodesk AutoCAD
2. **中望CAD (ZWCAD)** - 广州中望数字化设计软件

## 新增功能

### 1. CAD类型选择

在主界面的"生成区域设置"面板中，新增了"CAD类型"下拉选择框：
- AutoCAD
- 中望CAD (ZWCAD)

### 2. 自动检测与连接

程序会根据选择的CAD类型自动使用相应的连接方式：
- AutoCAD：使用 `pyautocad` 库
- 中望CAD：使用 `ZWCAD` 库

### 3. 统一的API接口

两种CAD类型使用相同的API接口，确保功能一致性：
- `connect()` - 连接到CAD
- `disconnect()` - 断开连接
- `draw_boundary()` - 绘制边界
- `draw_aggregate()` - 绘制骨料
- `delete_object()` - 删除对象
- `prompt()` - 发送提示消息

## 使用方法

### 1. 选择CAD类型

启动程序后，在"生成区域设置"面板中：
1. 找到"CAD类型"下拉框
2. 选择"AutoCAD"或"中望CAD (ZWCAD)"
3. 确保相应的CAD软件已启动

### 2. 连接CAD

程序会自动尝试连接到选择的CAD：
- 如果连接成功，会在CAD命令行显示"随机骨料生成器已连接XXX"
- 如果连接失败，会显示详细的错误信息

### 3. 生成骨料

连接成功后，可以正常使用所有功能：
- 配置生成参数
- 生成骨料
- 绘制到CAD
- 导出数据

## 安装依赖

### AutoCAD 依赖

```bash
pip install pyautocad
pip install comtypes
```

### 中望CAD 依赖

中望CAD **不需要安装额外的 Python 库**，直接使用 `comtypes` 库连接：

```bash
pip install comtypes
```

**重要说明**：
- 中望CAD通过 COM 接口连接，与 AutoCAD 类似
- 只需要安装 `comtypes` 库即可
- 不需要安装专门的 ZWCAD Python 库
- 确保中望CAD软件已正确安装并注册 COM 组件

## 测试脚本

### 测试AutoCAD连接

```bash
python test_zwcad_connection.py
```

然后选择选项 `1` - AutoCAD

### 测试中望CAD连接

```bash
python test_zwcad_connection.py
```

然后选择选项 `2` - 中望CAD (ZWCAD)

### 测试两者

```bash
python test_zwcad_connection.py
```

然后选择选项 `3` - 两者都测试

## 代码实现

### CADType 枚举

```python
class CADType(Enum):
    """CAD类型枚举"""
    AUTOCAD = "autocad"
    ZWCAD = "zwcad"
```

### CADConnection 类

```python
class CADConnection:
    def __init__(self, auto_start: bool = True, cad_type: str = "autocad"):
        """
        初始化CAD连接管理器
        
        Args:
            auto_start: 如果CAD未运行，是否自动启动
            cad_type: CAD类型，可选值: "autocad", "zwcad"
        """
        self._cad_type = cad_type
        # ...
```

### 连接逻辑

```python
def connect(self) -> bool:
    if self._cad_type == CADType.AUTOCAD:
        # AutoCAD 连接逻辑
        self._acad_autocad = Autocad(create_if_not_exists=self._auto_start)
        self._doc = self._acad_autocad.doc
        self._model_space = self._doc.ModelSpace
    elif self._cad_type == CADType.ZWCAD:
        # 中望CAD 连接逻辑（使用 COM 接口）
        import comtypes.client
        self._acad_zwcad = comtypes.client.GetActiveObject("ZWCAD.Application")
        self._doc = self._acad_zwcad.ActiveDocument
        self._model_space = self._doc.ModelSpace
```

## UI 集成

### 主窗口修改

在 `MainWindow` 类中：

```python
def __init__(self):
    super().__init__()
    self.cad_type = "autocad"  # 默认为AutoCAD
    # ...

def _create_region_panel(self, layout: QVBoxLayout):
    # 添加CAD类型选择
    self.cad_type_combo = QComboBox()
    self.cad_type_combo.addItems(["AutoCAD", "中望CAD (ZWCAD)"])
    self.cad_type_combo.setCurrentIndex(0)
    self.cad_type_combo.currentTextChanged.connect(self._on_cad_type_changed)
    form_layout.addRow("CAD类型:", self.cad_type_combo)
    # ...

@Slot(str)
def _on_cad_type_changed(self, cad_type: str):
    """CAD类型变化处理"""
    if "中望" in cad_type or "ZWCAD" in cad_type:
        self.cad_type = "zwcad"
        logging.info("已选择中望CAD")
    else:
        self.cad_type = "autocad"
        logging.info("已选择AutoCAD")
```

### 生成器初始化

```python
def _initialize_generator(self) -> None:
    if self.generator is None:
        self.generator = RandomAggregateGenerator(
            auto_start=True, 
            cad_type=self.cad_type
        )
    # ...
```

## 兼容性

### AutoCAD

- **支持版本**：AutoCAD 2010 及以上
- **推荐版本**：AutoCAD 2018-2024
- **COM接口**：AutoCAD COM Automation

### 中望CAD

- **支持版本**：中望CAD 2020 及以上
- **推荐版本**：中望CAD 2023-2025
- **COM接口**：中望CAD COM Automation

**注意**：中望CAD的COM接口可能与AutoCAD略有不同，程序已做兼容处理。

## 故障排除

### AutoCAD 连接失败

参考 `AUTOCAD_DEBUG_GUIDE.md` 文档。

### 中望CAD 连接失败

#### 1. 检查中望CAD是否安装

运行诊断工具：

```bash
python test_cad_automated.py
```

应该看到 "检测到 X 个中望CAD安装"。

#### 2. 检查COM库是否安装

```bash
pip show comtypes
```

如果未安装，请安装：

```bash
pip install comtypes
```

#### 3. 确保中望CAD正在运行

- 手动启动中望CAD
- 打开一个文档
- 然后再尝试连接

#### 4. 以管理员身份运行

右键点击命令提示符，选择"以管理员身份运行"，然后运行程序。

#### 5. 查看详细日志

```bash
type logs\randomcad.log
```

### 常见错误

#### 错误1："COM库未安装，无法使用中望CAD"

**原因**：comtypes 库未安装

**解决**：
```bash
pip install comtypes
```

#### 错误2："未检测到运行中的中望CAD"

**原因**：中望CAD未运行或未启用自动启动

**解决**：
1. 手动启动中望CAD
2. 或在连接时设置 `auto_start=True`

#### 错误3："未知的CAD类型"

**原因**：代码中CAD类型设置错误

**解决**：
确保CAD类型为 "autocad" 或 "zwcad"

## 功能对比

| 功能 | AutoCAD | 中望CAD |
|------|----------|----------|
| 连接 | ✅ | ✅ |
| 绘制边界 | ✅ | ✅ |
| 绘制骨料 | ✅ | ✅ |
| 删除对象 | ✅ | ✅ |
| 发送提示消息 | ✅ | ✅ |
| 重绘 | ✅ | ✅ |
| 状态监控 | ✅ | ✅ |
| 自动重连 | ✅ | ✅ |
| 心跳检测 | ✅ | ✅ |

## 性能考虑

### AutoCAD

- 成熟的COM接口
- 稳定的连接
- 广泛的文档支持

### 中望CAD

- 较新的COM接口
- 可能需要额外的兼容处理
- 性能与AutoCAD相当

## 未来计划

1. **更多CAD支持**
   - 天正CAD
   - 浩辰CAD
   - 其他国产CAD

2. **性能优化**
   - 针对不同CAD的优化
   - 更好的并行处理

3. **功能扩展**
   - 更多CAD特定功能
   - 更好的错误处理

## 贡献

如果您有其他CAD软件的集成需求，欢迎贡献！

## 许可证

[待定]

## 联系方式

- 项目主页：[待定]
- 问题反馈：[待定]
- 邮箱：[待定]

---

**最后更新**：2025-12-25
**版本**：v2.0.0
**新增功能**：中望CAD (ZWCAD) 支持
