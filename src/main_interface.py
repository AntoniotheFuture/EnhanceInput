import logging

import pyperclip
from PyQt5.QtCore import Qt, pyqtSlot, QRectF
from PyQt5.QtGui import QCursor, QColor, QPainterPath, QPainter
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QFrame, QLabel, QTextEdit, QDesktopWidget, \
    QHBoxLayout, QGraphicsDropShadowEffect


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

        # 设置无边框和背景透明
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_ui()
        self.init_custom_title_bar()

        self.main_app.signals.getting_suggestions.connect(self.getting_suggestions)
        self.main_app.signals.show_status.connect(self.show_status)
        self.main_app.signals.show_suggestions.connect(self.show_suggestions)

        self.current_selected_index = -1  # 当前选中按钮的索引
        self.suggestion_buttons = []  # 存储所有建议按钮

    def init_ui(self):
        self.setWindowTitle('文本增强')
        self.setGeometry(100, 100, 800, 600)

        # 主容器Widget - 用于实现圆角
        self.main_container = QWidget()
        self.main_container.setObjectName("mainContainer")
        self.main_container.setStyleSheet("""
            #mainContainer {
                background: white;
                border-radius: 15px;
            }
        """)
        self.setCentralWidget(self.main_container)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.main_container.setGraphicsEffect(shadow)

        # 主布局
        self.layout = QVBoxLayout(self.main_container)
        self.layout.setContentsMargins(15, 15, 15, 15)  # 留出圆角空间

        self.main_container.setLayout(self.layout)

        # 使用垂直布局管理器
        # self.layout = QVBoxLayout()
        # self.main_frame.setLayout(self.layout)

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

    def init_custom_title_bar(self):
        """初始化自定义标题栏"""
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("background: transparent;")

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)

        # 标题文字
        self.title_label = QLabel("文本增强工具")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
            }
        """)

        # 空白区域用于拖动
        self.drag_widget = QWidget()
        self.drag_widget.setStyleSheet("background: transparent;")

        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                font-size: 18px;
                color: #999;
                background: transparent;
            }
            QPushButton:hover {
                color: #333;
                background: #f0f0f0;
                border-radius: 15px;
            }
        """)
        close_btn.clicked.connect(self.hide)

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.drag_widget, 1)  # 可拉伸的空白区域
        title_layout.addWidget(close_btn)

        # 将标题栏添加到主布局顶部
        self.layout.insertWidget(0, title_bar)

        # 拖动窗口的变量
        self.drag_position = None

    def mousePressEvent(self, event):
        """鼠标按下事件 - 开始拖动"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动窗口"""
        if self.drag_position and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 结束拖动"""
        self.drag_position = None
        event.accept()

    def paintEvent(self, event):
        """绘制圆角窗口"""
        path = QPainterPath()
        rect = self.rect()  # 获取QRect
        rectf = QRectF(rect)  # 转换为QRectF
        path.addRoundedRect(rectf, 15, 15)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(240, 240, 240, 200))  # 半透明背景
        painter.drawPath(path)

        painter.end()

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
            self.suggestion_buttons.clear()
            self.current_selected_index = -1

            for i, suggestion in enumerate(suggestions, 1):
                h_layout = QHBoxLayout()

                # 创建建议按钮
                btn = QPushButton(suggestion)
                btn.setObjectName(f"suggestionBtn_{i}")
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 5px;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        background: white;
                    }
                    QPushButton:hover {
                        background-color: #f0f0f0;
                    }
                    QPushButton:focus {
                        background-color: #e0e0e0;
                        border: 1px solid #999;
                    }
                """)
                btn.clicked.connect(lambda _, s=suggestion: self.pick_suggestion(s))

                # 添加到布局
                h_layout.addWidget(btn)
                widget = QWidget()
                widget.setLayout(h_layout)
                self.suggestions_layout.addWidget(widget)

                # 存储按钮引用
                self.suggestion_buttons.append(btn)

            # 默认选中第一个
            if self.suggestion_buttons:
                self.select_suggestion(0)

            self.adjustSize()

        except Exception as e:
            logging.error(f"显示建议时出错: {str(e)}")
            raise

    def select_suggestion(self, index):
        """选择指定索引的建议"""
        if not self.suggestion_buttons:
            return

        # 取消之前的选择
        if 0 <= self.current_selected_index < len(self.suggestion_buttons):
            btn = self.suggestion_buttons[self.current_selected_index]
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 5px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    background: white;
                }
            """)

        # 设置新的选择
        self.current_selected_index = index % len(self.suggestion_buttons)
        btn = self.suggestion_buttons[self.current_selected_index]
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 5px;
                border: 1px solid #999;
                border-radius: 3px;
                background: #e0e0e0;
            }
        """)
        btn.setFocus()

    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key_Escape:
            self.hide()
            event.accept()
            return
        # 只在有建议按钮且焦点不在输入框时处理
        if self.suggestion_buttons and not self.original_text.hasFocus():
            if event.key() == Qt.Key_Up:
                self.select_suggestion(self.current_selected_index - 1)
                event.accept()
                return
            elif event.key() == Qt.Key_Down:
                self.select_suggestion(self.current_selected_index + 1)
                event.accept()
                return
            elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if 0 <= self.current_selected_index < len(self.suggestion_buttons):
                    btn = self.suggestion_buttons[self.current_selected_index]
                    btn.click()
                    event.accept()
                    return

        super().keyPressEvent(event)

    def clear_suggestions(self):
        """清除所有建议"""
        try:
            self.suggestion_buttons.clear()
            self.current_selected_index = -1

            logging.debug("清除所有建议")
            # 获取布局中的所有项目
            # items = []
            while self.suggestions_layout.count():
                item = self.suggestions_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                # if item.widget():
                #     items.append(item.widget())
                # elif item.layout():
                #     # 递归清除子布局
                #     self._clear_layout(item.layout())

            # 安全删除所有部件
            # for widget in items:
            #     widget.setParent(None)
            #     widget.deleteLater()

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