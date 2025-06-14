import logging
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QWidget, \
    QMessageBox, QGridLayout, QTextEdit

from configurable.config import get_config

class ConfigInterface(QDialog):

    def __init__(self, main_app=None):
        super().__init__()
        self.prompt_input = None
        self.openai_temperature_input = None
        self.openai_model_input = None
        self.openai_endpoint_input = None
        self.openai_api_key_input = None
        self.hotkey_input = None
        self.api_provider_combo = None
        self.main_app = main_app
        self.config = get_config()

        self.init_ui()

    def reset_hotkey(self):
        default_config = self.config.get_default()
        self.hotkey_input.setText(default_config["settings"]["hotkey"])

    def reset_api(self):
        default_config = self.config.get_default()
        self.openai_endpoint_input.setText(default_config["openai"]["endpoint"])
        self.openai_api_key_input.setText(default_config["openai"]["api_key"])
        self.openai_model_input.setText(default_config["openai"]["model"])
        self.openai_temperature_input.setText(default_config["openai"]["temperature"])

    def reset_prompt(self):
        default_config = self.config.get_default()
        self.prompt_input.setText(default_config["settings"]["prompt"])

    def init_ui(self):
        self.setWindowTitle('配置界面')
        self.setGeometry(200, 200, 600, 400)

        main_layout = QVBoxLayout()

        # 创建标签页容器
        tab_widget = QTabWidget()

        # 快捷键设置页面
        hotkey_tab = QWidget()
        hotkey_layout = QGridLayout()
        hotkey_label = QLabel("快捷键组合:")
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setText(self.config.get("settings", "hotkey", fallback=""))
        hotkey_layout.addWidget(self.hotkey_input, 0, 1)
        hotkey_layout.addWidget(hotkey_label, 0, 0)

        reset_button = QPushButton("重置")
        reset_button.clicked.connect(self.reset_hotkey)
        hotkey_layout.addWidget(reset_button, 1, 0)

        hotkey_tab.setLayout(hotkey_layout)

        # API设置页面
        api_tab = QWidget()
        api_layout = QGridLayout()

        row = 0
        label = QLabel("接入点:")
        self.openai_endpoint_input = QLineEdit()
        self.openai_endpoint_input.setText(self.config.get("openai", "endpoint", fallback=""))
        api_layout.addWidget(label, row, 0)
        api_layout.addWidget(self.openai_endpoint_input, row, 1)
        row += 1

        label = QLabel("API密钥:")
        self.openai_api_key_input = QLineEdit()
        self.openai_api_key_input.setText(self.config.get("openai", "api_key", fallback=""))
        api_layout.addWidget(label, row, 0)
        api_layout.addWidget(self.openai_api_key_input, row, 1)
        row += 1

        label = QLabel("模型:")
        self.openai_model_input = QLineEdit()
        self.openai_model_input.setText(self.config.get("openai", "model", fallback=""))
        api_layout.addWidget(label, row, 0)
        api_layout.addWidget(self.openai_model_input, row, 1)
        row += 1

        label = QLabel("温度:")
        self.openai_temperature_input = QLineEdit()
        self.openai_temperature_input.setText(self.config.get("openai", "temperature", fallback=""))
        api_layout.addWidget(label, row, 0)
        api_layout.addWidget(self.openai_temperature_input, row, 1)
        row += 1

        reset_button = QPushButton("重置")
        reset_button.clicked.connect(self.reset_api)
        api_layout.addWidget(reset_button, row, 0)

        api_tab.setLayout(api_layout)

        # 提示词设置页面
        prompt_tab = QWidget()
        prompt_layout = QGridLayout()
        label = QLabel("提示词:")
        self.prompt_input = QTextEdit()
        self.prompt_input.setText(self.config.get("settings", "prompt", fallback=""))
        prompt_layout.addWidget(label, 0, 0)
        prompt_layout.addWidget(self.prompt_input, 0, 1)

        reset_button = QPushButton("重置")
        reset_button.clicked.connect(self.reset_prompt)
        prompt_layout.addWidget(reset_button, 1, 0)

        prompt_tab.setLayout(prompt_layout)

        # 添加标签页
        tab_widget.addTab(hotkey_tab, "快捷键")
        tab_widget.addTab(api_tab, "OPenAI API设置")
        tab_widget.addTab(prompt_tab, "提示词")

        main_layout.addWidget(tab_widget)

        # 保存按钮
        save_btn = QPushButton('保存', self)
        save_btn.clicked.connect(self.save_config)
        main_layout.addWidget(save_btn)

        self.setLayout(main_layout)

    def save_config(self):
        try:
            # 保存快捷键设置
            new_hotkey = self.hotkey_input.text().strip()
            if new_hotkey:
                self.config.set("settings", "hotkey", new_hotkey)

            # 保存OpenAI API密钥
            self.config.set("openai", "endpoint", self.openai_endpoint_input.text())
            self.config.set("openai", "api_key", self.openai_api_key_input.text())
            self.config.set("openai", "model", self.openai_model_input.text())
            self.config.set("openai", "temperature", self.openai_temperature_input.text())

            self.config.set("settings", "prompt", self.prompt_input.toPlainText())

            self.config.save()

            QMessageBox.information(self, "成功", "设置已保存")
            logging.info("设置已更新")

            if self.main_app:
                self.main_app.register_hotkey()
        except Exception as e:
            logging.error(f"保存设置时出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")