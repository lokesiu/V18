# LOGO 替换指南 — 把顶部"明证台"大字换成矢量 LOGO

> 状态: `app/main_window.py` 当前处于 WIP 状态(被 6F2FF27 commit 锁定),无法直接修改。
> 本文档记录当 WIP 解除后,如何把 `Logo` 组件接入到标题栏。

---

## 为什么需要 LOGO

当前 V18 桌面应用在顶部标题栏用的是 `setWindowTitle("明证台")` — 一个普通文字标题。
对于商业化产品,需要换成"品牌标识 + 文字"的 LOGO 形式,具备:

- 矢量绘制 (任意 DPI 不糊)
- 主题感知 (深/浅色背景自适应)
- 品牌辨识度 (红色印章 + M 字 + 金色天平点)

## 已经准备好的组件

`app/widgets/logo.py` 提供三个粒度的组件,任选其一:

| 组件 | 类名 | 大小 | 用途 |
|------|------|------|------|
| 完整 LOGO | `Logo` | 默认 28×28 mark + 文字 | **推荐**,顶栏首选 |
| 仅图标 | `LogoMark` | 24×24 起 | 任务栏 / 桌面快捷方式 |
| 仅文字 | `LogoWordmark` | 16px 起 | 报告封面 / 邮件签名 |

## 接入步骤(等 WIP 解除后执行)

### 1. 在 `app/main_window.py` 中 import

```python
# app/main_window.py
from app.widgets.logo import Logo
```

### 2. 替换 setWindowTitle

```python
# Before:
self.setWindowTitle("明证台")

# After:
self.setWindowTitle("明证台 V18")  # 保留,任务栏 tooltip 用
self._title_logo = Logo(mark_size=24, show_latin=True)
self.setWindowIcon(...)  # 可选:LogoMark(size=32) 导出为 .ico
```

### 3. 把 LOGO 注入导航栏/标题栏

```python
# FluentWindow 的标题栏由 setTitleBar 自定义
from qfluentwidgets import FluentTitleBar

class V18TitleBar(FluentTitleBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hBoxLayout.insertSpacing(0, 12)
        self.logo = Logo(mark_size=20, show_latin=False)
        self.hBoxLayout.insertWidget(1, self.logo, 0, Qt.AlignVCenter)
        # 移除默认的 titleLabel
        self.titleLabel.hide()
```

### 4. 同步窗口图标 (可选)

```python
from app.widgets.logo import LogoMark
from PySide6.QtGui import QPixmap, QIcon

def _make_icon(size=64):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    mark = LogoMark(size=size)
    mark.render(pix)  # 需要给 LogoMark 加一个 render 方法
    return QIcon(pix)

self.setWindowIcon(_make_icon(64))
```

> 注: `LogoMark.render(pixmap)` 是一个待添加的辅助方法,目前只支持 `paintEvent`。
> 如果需要导出为图标文件,可以用 `QWidget.grab()`:

```python
mark = LogoMark(size=128)
mark.show()  # 必须先 show,否则 grab 返回空
QApplication.processEvents()
pix = mark.grab()
pix.save("assets/icons/v18_logo_128.png")
```

## 视觉规范

| 元素 | 颜色 | 备注 |
|------|------|------|
| 盾牌主体 | `#B91C1C` → `#7F1D1D` (深红渐变) | 印章红,法律行业暗示 |
| 内部 M 字 | `#FFFFFF` | 2.4px 圆头线 |
| 装饰点 | `#D97706` (金) | 天平感,品牌强调点 |
| 文字 | `#0F172A` (深) / `#F8FAFC` (浅) | 主题感知 |
| 副标题 | `#64748B` (中灰) | MINGZHENGTAI · V18 |

## 不破坏现有 CI

`app/widgets/logo.py` 完全是新文件,无 import 副作用。`app/main_window.py` 改动
是**用户侧接入**,不影响:

- ✅ 现有 939 passing 测试
- ✅ `scripts/verify_harness.py` 14 项检查
- ✅ `scripts/scan_repo.py` 7 类扫描

## 当前状态

- ✅ `app/widgets/logo.py` 已创建,可用 `python -c "from app.widgets.logo import Logo; print(Logo())"` 验证
- ⏳ `app/main_window.py` 等待 WIP 解除 (用户可手动 push 时一并合入)
- ⏳ 截图脚本 `scripts/screenshot_v18.py` 等 WIP 解除后追加 LOGO 截图
