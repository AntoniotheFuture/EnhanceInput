import logging

import pyperclip
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QFrame, QLabel, QTextEdit, QDesktopWidget, \
    QHBoxLayout

class MainInterface(QMainWindow):

    def __init__(self, main_app=None):
        super().__init__()
        self.layout = None
        self.window_visible = False
        self.original_text = None
        self.status_label = None
        self.suggestions_layout = None
        self.suggestions_frame = None
        self.main_frame = None
        self.main_app = main_app
        self.init_ui()

        self.main_app.signals.getting_suggestions.connect(self.getting_suggestions)
        self.main_app.signals.show_status.connect(self.show_status)
        self.main_app.signals.show_suggestions.connect(self.show_suggestions)

    def init_ui(self):
        self.setWindowTitle('文本增强')
        self.setGeometry(100, 100, 800, 600)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        # 主框架
        self.main_frame = QFrame()
        self.setCentralWidget(self.main_frame)

        # 使用垂直布局管理器
        self.layout = QVBoxLayout()
        self.main_frame.setLayout(self.layout)

        # 打开配置按钮
        btn = QPushButton('打开配置')
        btn.clicked.connect(self.open_config_dialog)
        self.layout.addWidget(btn)

        # 原始文本标签
        original_label = QLabel("原始文本:")
        self.layout.addWidget(original_label, alignment=Qt.AlignLeft)

        # 原始文本显示
        self.original_text = QTextEdit()
        self.original_text.setFixedHeight(60)
        self.layout.addWidget(self.original_text)

        # 建议标签
        suggestions_label = QLabel("建议表达:")
        self.layout.addWidget(suggestions_label, alignment=Qt.AlignLeft)

        # 建议按钮框架
        self.suggestions_frame = QFrame()
        self.suggestions_layout = QVBoxLayout()
        self.suggestions_frame.setLayout(self.suggestions_layout)
        self.layout.addWidget(self.suggestions_frame)

        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: gray;")
        self.layout.addWidget(self.status_label, alignment=Qt.AlignBottom)

        logging.info("用户界面设置完成")

    def open_config_dialog(self):
        self.main_app.show_config_window()

    @pyqtSlot(str)
    def getting_suggestions(self, text: str):
        """显示窗口并设置文本"""
        try:
            self.original_text.clear()
            self.original_text.setText(text)
            self.clear_suggestions()

            logging.info("正在生成建议...")
            loading_label = QLabel("正在生成建议...")
            loading_label.setAlignment(Qt.AlignCenter)
            self.suggestions_layout.addWidget(loading_label)

            self.show_window()

            self.position_window_near_cursor()

        except Exception as e:
            logging.error(f"显示窗口时出错: {str(e)}")
            raise

    def position_window_near_cursor(self):
        """将窗口定位到光标附近"""
        try:
            cursor_pos = QCursor.pos()
            x, y = cursor_pos.x(), cursor_pos.y()
            logging.debug(f"光标位置: {x}, {y}")

            screen_geometry = QDesktopWidget().availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()

            window_width = self.width()
            window_height = self.height()

            new_x = x + 20
            new_y = y + 20

            if new_x + window_width > screen_width:
                new_x = x - window_width - 20
            if new_y + window_height > screen_height:
                new_y = y - window_height - 20

            self.move(new_x, new_y)
            logging.debug(f"窗口位置设置为: {new_x}, {new_y}")
        except Exception as e:
            logging.error(f"定位窗口时出错: {str(e)}")
            raise

    @pyqtSlot(list)
    def show_suggestions(self, suggestions: list):
        """在UI中显示建议"""
        try:
            self.clear_suggestions()

            if not suggestions:
                self.show_status("未获取到有效建议", True)
                return

            for i, suggestion in enumerate(suggestions, 1):
                h_layout = QHBoxLayout()

                # 创建建议按钮
                btn = QPushButton(suggestion)
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 5px;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #f0f0f0;
                    }
                """)
                btn.clicked.connect(lambda _, s=suggestion: self.pick_suggestion(s))
                h_layout.addWidget(btn, stretch=1)

                widget = QWidget()
                widget.setLayout(h_layout)
                self.suggestions_layout.addWidget(widget)

            self.adjustSize()
            logging.debug("建议已显示在UI中")
        except Exception as e:
            logging.error(f"显示建议时出错: {str(e)}")
            raise

    def clear_suggestions(self):
        """清除所有建议"""
        try:
            logging.debug("清除所有建议")
            # 获取布局中的所有项目
            items = []
            while self.suggestions_layout.count():
                item = self.suggestions_layout.takeAt(0)
                if item.widget():
                    items.append(item.widget())
                elif item.layout():
                    # 递归清除子布局
                    self._clear_layout(item.layout())

            # 安全删除所有部件
            for widget in items:
                widget.setParent(None)
                widget.deleteLater()

        except Exception as e:
            logging.error(f"清除建议时出错: {str(e)}")
            raise

    def _clear_layout(self, layout):
        """递归清除布局"""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def pick_suggestion(self, suggestion):
        """使用选中的建议替换原文本"""
        try:
            logging.info(f"用户选择了建议: {suggestion}")
            pyperclip.copy(suggestion)
            self.show_status("已复制到剪贴板")
            logging.info("已复制到剪贴板")
        except Exception as e:
            error_msg = f"替换错误: {str(e)}"
            self.show_status(error_msg, error=True)
            logging.error(error_msg, exc_info=True)

    def regenerate(self):
        # todo
        pass

    @pyqtSlot(str, bool)
    def show_status(self, message: str, error: bool = False):
        """显示状态消息"""
        try:
            color = "red" if error else "black"
            self.status_label.setText(message)
            self.status_label.setStyleSheet(f"color: {color};")

            level = logging.ERROR if error else logging.INFO
            logging.log(level, f"状态更新: {message}")

            self.adjustSize()
        except Exception as e:
            logging.error(f"更新状态时出错: {str(e)}")
            raise

    def show_window(self):
        if not self.window_visible:
            self.show()
            self.window_visible = True
        else:
            logging.debug("窗口已经显示")

    def closeEvent(self, event):
        """重写关闭事件，隐藏窗口而不是关闭"""
        event.ignore()
        self.hide()
        self.window_visible = False
        logging.info("主窗口隐藏")