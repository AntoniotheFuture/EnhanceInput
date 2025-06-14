# UI更新信号
from PyQt5.QtCore import QObject, pyqtSignal


class WorkerSignals(QObject):
    getting_suggestions = pyqtSignal(str)
    show_status = pyqtSignal(str, bool)  # 用于更新状态栏的信号，同时显示窗口
    show_suggestions = pyqtSignal(list)  # 用于更新建议列表的信号