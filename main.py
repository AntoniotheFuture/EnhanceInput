import logging
import sys
import threading
import time
import typing
from typing import List, Optional

import keyboard
import pyperclip
from PyQt5.QtCore import QSharedMemory, QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QApplication

from Advisors.OpenAIAdvisor import OpenAIAdvisor
from WorkerSignals import WorkerSignals
from configurable.config import get_config
from configurable.config_interface import ConfigInterface
from logger import setup_logging
from src.main_interface import MainInterface

setup_logging()

class TextEnhancerApp(QApplication):

    main_window: MainInterface
    config_window: ConfigInterface


    def __init__(self, argv: typing.List[str]):
        super().__init__(argv)
        self.signals = WorkerSignals()
        self.main_window = MainInterface(main_app=self)
        self.config_window = ConfigInterface(main_app=self)
        self.config = get_config()

        # 禁用“最后一个窗口关闭时退出”的行为
        self.setQuitOnLastWindowClosed(False)

        self.main_window.hide()

        self._hotkey_registered = None
        self._current_hotkey = None
        self._hotkey_lock = threading.Lock()
        if not self.check_config():
           self.show_setting_window()
        else:
            self.register_hotkey()
        self.selected_text = ""
        logging.info("应用程序初始化完成")

    # 检查api是否满足运行要求，否则显示配置窗口
    def check_config(self) -> bool:
        required_configs = [
            ("settings", "hotkey"),
            ("openai", "api_key"),
            ("openai", "model"),
            ("settings", "prompt")
        ]
        for section, key in required_configs:
            if not self.config.get(section, key, fallback=None):
                return False
        return True

    def show_config_window(self):
        self.config_window.show()

    def register_hotkey(self):
        """注册全局快捷键"""
        with self._hotkey_lock:
            try:
                new_hotkey = self.config.get("settings", "hotkey", fallback=None)
                if not new_hotkey:
                    logging.warning("未找到有效的快捷键配置，跳过快捷键注册")
                    return
                
                # 如果快捷键未变化，无需重新注册
                if hasattr(self, '_current_hotkey') and self._current_hotkey == new_hotkey:
                    logging.info("快捷键未变化，无需重新注册")
                    return
                
                if hasattr(self, '_hotkey_registered') and self._hotkey_registered:
                    keyboard.remove_hotkey(self.hotkey_callback)
                
                keyboard.add_hotkey(new_hotkey, self.hotkey_callback, suppress=True)
                logging.info(f"快捷键注册成功: {new_hotkey}")
                
                self._current_hotkey = new_hotkey
                self._hotkey_registered = True
            except Exception as e:
                logging.error(f"注册快捷键失败: {str(e)}")
                raise

    def hotkey_callback(self):
        """快捷键回调函数"""
        try:
            logging.info("快捷键触发")
            # 保存当前剪贴板内容
            original_clipboard = pyperclip.paste()
            logging.debug("剪贴板内容已保存")

            try:
                # 模拟Ctrl+C复制选中的文本
                keyboard.send("ctrl+c")
                time.sleep(0.1)  # 等待剪贴板更新
                self.selected_text = pyperclip.paste().strip()
                logging.debug(f"获取到选中文本: {self.selected_text}")

                if not self.selected_text:
                    self.signals.show_status.emit("未选中文本", True)
                    logging.warning("未检测到选中文本")
                    return

                # 显示窗口并获取建议
                self.signals.getting_suggestions.emit(self.selected_text)
                # threading.Thread(target=self.get_suggestions, daemon=True).start()

                # 使用QThread代替普通线程
                self.worker = SuggestionWorker(self.selected_text, self.config)
                self.worker.finished.connect(self.on_suggestions_ready)
                self.worker.error.connect(self.on_suggestion_error)
                self.worker.start()

            except Exception as e:
                self.main_window.show_status(f"错误: {str(e)}", error=True)
                logging.error(f"处理选中文本时出错: {str(e)}")
            finally:
                # 恢复剪贴板内容
                pyperclip.copy(original_clipboard)
                logging.debug("剪贴板内容已恢复")

        except Exception as e:
            logging.error(f"快捷键回调出错: {str(e)}")
            self.main_window.show_status(f"系统错误: {str(e)}", error=True)

    def on_suggestions_ready(self, suggestions: list):
        self.main_window.show_suggestions(suggestions)

    def on_suggestion_error(self, text: str):
        self.main_window.show_status(text, True)

    def get_suggestions(self):
        """调用API获取建议"""
        try:
            self.signals.show_status.emit("正在生成建议...", False)
            logging.info("开始获取建议")

            suggestions = self.get_openai_suggestions()

            if suggestions:
                logging.info(f"成功获取 {len(suggestions)} 条建议")
                self.signals.show_suggestions.emit(suggestions)
                self.signals.show_status.emit("建议已生成", False)
            else:
                error_msg = "未能生成建议"
                self.signals.show_status.emit(error_msg, True)
                logging.warning(error_msg)

        except Exception as e:
            error_msg = f"API错误: {str(e)}"
            self.signals.show_status.emit(error_msg, True)
            logging.error(error_msg, exc_info=True)

    def get_openai_suggestions(self) -> Optional[List[str]]:
        api_key = self.config.get("openai", "api_key")
        model = self.config.get("openai", "model")
        temperature = self.config.getfloat("openai", "temperature")
        base_url = self.config.get("openai", "endpoint")
        prompt = self.config.get("settings", "prompt")
        prompt = prompt.replace("<text>", self.selected_text)
        openai_advisor = OpenAIAdvisor(api_key, model, temperature, base_url, prompt)
        try:
            suggestions = openai_advisor.get_text_suggestions(self.selected_text)
            logging.info(f"建议：{str(suggestions)}")
            return suggestions
        except Exception as e:
            logging.error(f"OpenAI 获取建议失败: {str(e)}", exc_info=True)
            raise

    def show_setting_window(self):
        self.config_window.show()


    def run(self):
        """运行主循环"""
        try:
            logging.info("应用程序启动")
        except Exception as e:
            logging.error(f"应用程序运行时出错: {str(e)}", exc_info=True)
        finally:
            logging.info("应用程序退出")


class SuggestionWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, selected_text, config):
        super().__init__()
        self.selected_text = selected_text
        self.config = config

    def run(self):
        try:
            api_key = self.config.get("openai", "api_key")
            model = self.config.get("openai", "model")
            temperature = self.config.getfloat("openai", "temperature")
            base_url = self.config.get("openai", "endpoint")
            prompt = self.config.get("settings", "prompt")
            prompt = prompt.replace("<text>", self.selected_text)

            openai_advisor = OpenAIAdvisor(api_key, model, temperature, base_url, prompt)
            suggestions = openai_advisor.get_text_suggestions(self.selected_text)
            self.finished.emit(suggestions)
        except Exception as e:
            self.error.emit(str(e))

def main():
    # 确保单实例运行
    shared_memory = QSharedMemory("TextEnhancerMutex")
    try:
        if not shared_memory.create(1):
            QMessageBox.warning(None, "文本增强工具", "程序已经在运行")
            logging.warning("程序已经在运行，退出")
            sys.exit(0)

        app = TextEnhancerApp([])
        app.exec_()
    except Exception as e:
        logging.error(f"应用程序初始化失败: {str(e)}", exc_info=True)
        QMessageBox.critical(None, "错误", f"应用程序初始化失败: {str(e)}")
    finally:
        if shared_memory and shared_memory.isAttached():
            try:
                shared_memory.detach()
                logging.info("共享内存已成功释放")
            except RuntimeError as e:
                logging.error(f"释放共享内存时出错: {str(e)}")


if __name__ == "__main__":
    main()