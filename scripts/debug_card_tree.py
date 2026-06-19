import sys
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from qfluentwidgets import HeaderCardWidget, setTheme, Theme
setTheme(Theme.DARK)

card = HeaderCardWidget()
card.setTitle('Test Card')
card.resize(400, 300)

def dump(widget, depth=0):
    name = widget.objectName() or widget.__class__.__name__
    ss = widget.styleSheet()[:80] if widget.styleSheet() else ''
    geo = widget.geometry()
    print('%s%s [%d,%d %dx%d] ss="%s"' % (
        '  ' * depth, name, geo.x(), geo.y(), geo.width(), geo.height(), ss
    ))
    for child in widget.children():
        if child.isWidgetType() and child.parent() is widget:
            dump(child, depth + 1)

dump(card)
