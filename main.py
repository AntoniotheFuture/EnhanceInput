import ctypes
import logging
import os
import sys
import threading
import time
import tkinter as tk
from configparser import ConfigParser
from logging.handlers import RotatingFileHandler
from tkinter import ttk, messagebox
from typing import List, Optional

import keyboard
import openai
import pyperclip
import requests

# 常量定义
CONFIG_FILE = "text_enhancer.ini"
LOG_FILE = "text_enhancer.log"
DEFAULT_CONFIG = {
    "settings": {
        "hotkey": "ctrl+alt+e",
        "api_provider": "openai",
        "window_width": "400",
        "window_height": "200",
    },
    "openai": {
        "api_key": "your-api-key-here",
        "model": "gpt-3.5-turbo",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "temperature": "0.7",
    },
    "anthropic": {
        "api_key": "your-api-key-here",
        "model": "claude-3-sonnet-20240229",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "temperature": "0.7",
    }
}


# 设置日志
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


setup_logging()


class TextEnhancerApp:
    def __init__(self):
        self._hotkey_registered = None
        self._current_hotkey = None
        self._hotkey_lock = threading.Lock()
        self.load_config()
        self.setup_ui()
        self.register_hotkey()
        self.selected_text = ""
        self.window_visible = False
        self.root.withdraw()  # 初始隐藏窗口
        logging.info("应用程序初始化完成")

    def load_config(self):
        """加载或创建配置文件"""
        try:
            self.config = ConfigParser()
            if not os.path.exists(CONFIG_FILE):
                logging.info("未找到配置文件，创建默认配置")
                self.config.read_dict(DEFAULT_CONFIG)
                with open(CONFIG_FILE, "w") as f:
                    self.config.write(f)
            else:
                self.config.read(CONFIG_FILE)
                logging.info("配置文件加载成功")
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
            raise

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(CONFIG_FILE, "w") as f:
                self.config.write(f)
            logging.info("配置文件保存成功")
        except Exception as e:
            logging.error(f"保存配置文件失败: {str(e)}")
            raise

    def setup_ui(self):
        """设置用户界面"""
        try:
            self.root = tk.Tk()
            self.root.title("文本增强工具")
            self.root.geometry(
                f"{self.config.getint('settings', 'window_width')}x{self.config.getint('settings', 'window_height')}")
            self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

            # 使窗口置顶
            self.root.attributes("-topmost", True)

            # 主框架
            self.main_frame = ttk.Frame(self.root, padding="10")
            self.main_frame.pack(fill=tk.BOTH, expand=True)

            # 原始文本标签
            self.original_label = ttk.Label(self.main_frame, text="原始文本:", font=('Arial', 10, 'bold'))
            self.original_label.pack(anchor=tk.W)

            # 原始文本显示
            self.original_text = tk.Text(self.main_frame, height=3, wrap=tk.WORD, font=('Arial', 9))
            self.original_text.pack(fill=tk.X, pady=(0, 10))
            self.original_text.config(state=tk.DISABLED)

            # 建议标签
            self.suggestions_label = ttk.Label(self.main_frame, text="建议表达:", font=('Arial', 10, 'bold'))
            self.suggestions_label.pack(anchor=tk.W)

            # 建议按钮框架
            self.suggestions_frame = ttk.Frame(self.main_frame)
            self.suggestions_frame.pack(fill=tk.BOTH, expand=True)

            # 状态标签
            self.status_label = ttk.Label(self.main_frame, text="就绪", foreground="gray")
            self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

            # 配置菜单
            self.menu_bar = tk.Menu(self.root)
            self.config_menu = tk.Menu(self.menu_bar, tearoff=0)
            self.config_menu.add_command(label="设置...", command=self.show_settings_dialog)
            self.menu_bar.add_cascade(label="配置", menu=self.config_menu)
            self.root.config(menu=self.menu_bar)

            logging.info("用户界面设置完成")
        except Exception as e:
            logging.error(f"设置用户界面失败: {str(e)}")
            raise

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
                    self.show_status("未选中文本", error=True)
                    logging.warning("未检测到选中文本")
                    return

                # 显示窗口并获取建议
                self.show_window_with_text(self.selected_text)
                threading.Thread(target=self.get_suggestions, daemon=True).start()

            except Exception as e:
                self.show_status(f"错误: {str(e)}", error=True)
                logging.error(f"处理选中文本时出错: {str(e)}")
            finally:
                # 恢复剪贴板内容
                pyperclip.copy(original_clipboard)
                logging.debug("剪贴板内容已恢复")

        except Exception as e:
            logging.error(f"快捷键回调出错: {str(e)}")
            self.show_status(f"系统错误: {str(e)}", error=True)

    def show_window_with_text(self, text: str):
        """显示窗口并设置文本"""
        try:
            self.original_text.config(state=tk.NORMAL)
            self.original_text.delete(1.0, tk.END)
            self.original_text.insert(tk.END, text)
            self.original_text.config(state=tk.DISABLED)

            # 清除之前的建议
            for widget in self.suggestions_frame.winfo_children():
                widget.destroy()

            # 显示加载状态
            loading_label = ttk.Label(self.suggestions_frame, text="正在生成建议...")
            loading_label.pack(pady=10)

            # 定位窗口到鼠标位置
            self.position_window_near_cursor()

            # 显示窗口
            if not self.window_visible:
                self.root.deiconify()
                self.window_visible = True
                logging.debug("窗口已显示")
        except Exception as e:
            logging.error(f"显示窗口时出错: {str(e)}")
            raise

    def position_window_near_cursor(self):
        """将窗口定位到光标附近"""
        try:
            # 获取光标位置
            cursor_pos = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(cursor_pos))
            x, y = cursor_pos.x, cursor_pos.y
            logging.debug(f"光标位置: {x}, {y}")

            # 获取屏幕尺寸
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            # 计算窗口位置，确保不会超出屏幕
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()

            new_x = x + 20
            new_y = y + 20

            if new_x + window_width > screen_width:
                new_x = x - window_width - 20
            if new_y + window_height > screen_height:
                new_y = y - window_height - 20

            self.root.geometry(f"+{new_x}+{new_y}")
            logging.debug(f"窗口位置设置为: {new_x}, {new_y}")
        except Exception as e:
            logging.error(f"定位窗口时出错: {str(e)}")
            raise

    def get_suggestions(self):
        """调用API获取建议"""
        try:
            self.show_status("正在生成建议...")
            logging.info("开始获取建议")

            api_provider = self.config.get("settings", "api_provider")
            logging.debug(f"使用API提供商: {api_provider}")

            if api_provider == "openai":
                suggestions = self.get_openai_suggestions()
            elif api_provider == "anthropic":
                suggestions = self.get_anthropic_suggestions()
            else:
                error_msg = f"不支持的API提供商: {api_provider}"
                logging.error(error_msg)
                raise ValueError(error_msg)

            if suggestions:
                self.show_suggestions(suggestions)
                self.show_status("建议已生成")
                logging.info(f"成功获取 {len(suggestions)} 条建议")
            else:
                error_msg = "未能生成建议"
                self.show_status(error_msg, error=True)
                logging.warning(error_msg)

        except Exception as e:
            error_msg = f"API错误: {str(e)}"
            self.show_status(error_msg, error=True)
            logging.error(error_msg, exc_info=True)

    def get_openai_suggestions(self) -> Optional[List[str]]:
        """调用OpenAI API获取建议"""
        try:
            api_key = self.config.get("openai", "api_key")
            model = self.config.get("openai", "model")
            temperature = self.config.getfloat("openai", "temperature")
            base_url = self.config.get("openai", "endpoint")

            client = openai.OpenAI(api_key=api_key, base_url=base_url)

            prompt = (
                f"请为以下文本提供三种更优雅、专业的表达方式，保持原意但改进措辞。"
                f"直接返回三个选项，每个选项占一行，不要编号或其他说明。\n\n"
                f"文本: {self.selected_text}"
            )

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的写作助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=500
            )

            content = response.choices[0].message.content
            suggestions = [s.strip() for s in content.split("\n") if s.strip()]

            logging.debug(f"从OpenAI获取的原始响应: {content}")
            return suggestions[:3]  # 只返回前三个建议

        except Exception as e:
            logging.error(f"OpenAI API调用失败: {str(e)}", exc_info=True)
            raise
    def get_anthropic_suggestions(self) -> Optional[List[str]]:
        """调用Anthropic API获取建议"""
        try:
            api_key = self.config.get("anthropic", "api_key")
            model = self.config.get("anthropic", "model")
            endpoint = self.config.get("anthropic", "endpoint")
            temperature = self.config.getfloat("anthropic", "temperature")

            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }

            prompt = (
                f"请为以下文本提供三种更优雅、专业的表达方式，保持原意但改进措辞。"
                f"直接返回三个选项，每个选项占一行，不要编号或其他说明。\n\n"
                f"文本: {self.selected_text}"
            )

            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": temperature
            }

            logging.debug(f"发送请求到Anthropic API: {endpoint}")
            response = requests.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()

            content = response.json()["content"][0]["text"]
            suggestions = [s.strip() for s in content.split("\n") if s.strip()]

            logging.debug(f"从Anthropic获取的原始响应: {content}")
            return suggestions[:3]  # 只返回前三个建议

        except Exception as e:
            logging.error(f"Anthropic API调用失败: {str(e)}", exc_info=True)
            raise

    def show_suggestions(self, suggestions: List[str]):
        """在UI中显示建议"""
        try:
            # 清除加载状态
            for widget in self.suggestions_frame.winfo_children():
                widget.destroy()

            # 为每个建议创建按钮
            for i, suggestion in enumerate(suggestions, 1):
                frame = ttk.Frame(self.suggestions_frame)
                frame.pack(fill=tk.X, pady=2)

                btn = ttk.Button(
                    frame,
                    text=suggestion,
                    command=lambda s=suggestion: self.use_suggestion(s),
                    style="Suggestion.TButton"
                )
                btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

                # 添加编号标签
                label = ttk.Label(frame, text=f"{i}.", width=3)
                label.pack(side=tk.LEFT)

            # 调整窗口大小以适应内容
            self.root.update_idletasks()
            logging.debug("建议已显示在UI中")
        except Exception as e:
            logging.error(f"显示建议时出错: {str(e)}")
            raise

    def use_suggestion(self, suggestion: str):
        """使用选中的建议替换原文本"""
        try:
            logging.info(f"用户选择了建议: {suggestion}")
            # 保存当前剪贴板内容
            # original_clipboard = pyperclip.paste()
            # logging.debug("剪贴板内容已保存")

            try:
                # 将建议文本复制到剪贴板
                pyperclip.copy(suggestion)

                # # 模拟Ctrl+V粘贴
                # keyboard.send("ctrl+v")
                #
                # # 隐藏窗口
                # self.hide_window()

                self.show_status("已复制到剪贴板")
                logging.info("已复制到剪贴板")

            except Exception as e:
                error_msg = f"替换错误: {str(e)}"
                self.show_status(error_msg, error=True)
                logging.error(error_msg, exc_info=True)
            # finally:
                # 恢复剪贴板内容
                # pyperclip.copy(original_clipboard)
                # logging.debug("剪贴板内容已恢复")

        except Exception as e:
            logging.error(f"使用建议时出错: {str(e)}")
            raise

    def hide_window(self):
        """隐藏窗口"""
        try:
            self.root.withdraw()
            self.window_visible = False
            logging.debug("窗口已隐藏")
        except Exception as e:
            logging.error(f"隐藏窗口时出错: {str(e)}")
            raise

    def show_status(self, message: str, error: bool = False):
        """显示状态消息"""
        try:
            color = "red" if error else "black"
            self.status_label.config(text=message, foreground=color)
            self.root.update_idletasks()
            level = logging.ERROR if error else logging.INFO
            logging.log(level, f"状态更新: {message}")
        except Exception as e:
            logging.error(f"更新状态时出错: {str(e)}")
            raise

    def show_settings_dialog(self):
        """显示统一的设置对话框"""
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title("设置")
            dialog.transient(self.root)
            dialog.grab_set()

            # 创建笔记本式布局
            notebook = ttk.Notebook(dialog)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # 快捷键设置标签页
            hotkey_frame = ttk.Frame(notebook)
            notebook.add(hotkey_frame, text="快捷键")

            ttk.Label(hotkey_frame, text="快捷键组合:").grid(row=0, column=0, sticky=tk.W, pady=(10, 0))

            hotkey_var = tk.StringVar(value=self.config.get("settings", "hotkey"))
            hotkey_entry = ttk.Entry(hotkey_frame, textvariable=hotkey_var)
            hotkey_entry.grid(row=0, column=1, padx=5, pady=(10, 0), sticky=tk.EW)

            ttk.Label(hotkey_frame, text="例如: ctrl+alt+e, shift+win+s").grid(row=1, column=1, sticky=tk.W, padx=5)

            # API设置标签页
            api_frame = ttk.Frame(notebook)
            notebook.add(api_frame, text="API设置")

            row_label = 0
            row_value = 0

            # API提供商选择
            ttk.Label(api_frame, text="API提供商:").grid(row=row_label, column=0, sticky=tk.W, pady=(10, 2))
            api_provider_var = tk.StringVar(value=self.config.get("settings", "api_provider"))
            api_provider_combo = ttk.Combobox(api_frame, textvariable=api_provider_var, values=["openai", "anthropic"])
            api_provider_combo.grid(row=row_label, column=1, sticky=tk.EW, padx=5, pady=(10, 2))

            row_label += 1
            row_value += 1

            # OpenAI设置
            ttk.Label(api_frame, text="OpenAI endPoint:").grid(row=row_label, column=0, sticky=tk.W, pady=2)
            openai_endpoint_var = tk.StringVar(value=self.config.get("openai", "endpoint"))
            openai_endpoint_entry = ttk.Entry(api_frame, textvariable=openai_endpoint_var, show="*")
            openai_endpoint_entry.grid(row=row_label, column=1, sticky=tk.EW, padx=5, pady=2)

            row_label += 1
            row_value += 1

            ttk.Label(api_frame, text="OpenAI API密钥:").grid(row=row_label, column=0, sticky=tk.W, pady=2)
            openai_key_var = tk.StringVar(value=self.config.get("openai", "api_key"))
            openai_key_entry = ttk.Entry(api_frame, textvariable=openai_key_var, show="*")
            openai_key_entry.grid(row=row_label, column=1, sticky=tk.EW, padx=5, pady=2)

            row_label += 1
            row_value += 1

            ttk.Label(api_frame, text="OpenAI 模型:").grid(row=row_label, column=0, sticky=tk.W, pady=2)
            openai_model_var = tk.StringVar(value=self.config.get("openai", "model"))
            openai_model_entry = ttk.Entry(api_frame, textvariable=openai_model_var)
            openai_model_entry.grid(row=row_label, column=1, sticky=tk.EW, padx=5, pady=2)

            row_label += 1
            row_value += 1

            # Anthropic设置
            ttk.Label(api_frame, text="Anthropic API密钥:").grid(row=row_label, column=0, sticky=tk.W, pady=2)
            anthropic_key_var = tk.StringVar(value=self.config.get("anthropic", "api_key"))
            anthropic_key_entry = ttk.Entry(api_frame, textvariable=anthropic_key_var, show="*")
            anthropic_key_entry.grid(row=row_label, column=1, sticky=tk.EW, padx=5, pady=2)

            row_label += 1
            row_value += 1

            ttk.Label(api_frame, text="Anthropic 模型:").grid(row=row_label, column=0, sticky=tk.W, pady=2)
            anthropic_model_var = tk.StringVar(value=self.config.get("anthropic", "model"))
            anthropic_model_entry = ttk.Entry(api_frame, textvariable=anthropic_model_var)
            anthropic_model_entry.grid(row=row_label, column=1, sticky=tk.EW, padx=5, pady=2)

            row_label += 1
            row_value += 1

            # 通用参数
            ttk.Label(api_frame, text="温度(0-1):").grid(row=row_label, column=0, sticky=tk.W, pady=2)
            temp_var = tk.StringVar()

            # 根据当前选择的API提供商设置默认温度值
            def update_temp_default(*args):
                provider = api_provider_var.get()
                if provider == "openai":
                    temp_var.set(self.config.get("openai", "temperature"))
                elif provider == "anthropic":
                    temp_var.set(self.config.get("anthropic", "temperature"))

            api_provider_var.trace_add("write", update_temp_default)
            update_temp_default()  # 初始化

            temp_entry = ttk.Entry(api_frame, textvariable=temp_var)
            temp_entry.grid(row=row_label, column=1, sticky=tk.EW, padx=5, pady=2)

            # 窗口设置标签页
            window_frame = ttk.Frame(notebook)
            notebook.add(window_frame, text="窗口设置")

            ttk.Label(window_frame, text="窗口宽度:").grid(row=0, column=0, sticky=tk.W, pady=(10, 2))
            width_var = tk.StringVar(value=self.config.get("settings", "window_width"))
            ttk.Entry(window_frame, textvariable=width_var).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=(10, 2))

            ttk.Label(window_frame, text="窗口高度:").grid(row=1, column=0, sticky=tk.W, pady=2)
            height_var = tk.StringVar(value=self.config.get("settings", "window_height"))
            ttk.Entry(window_frame, textvariable=height_var).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)

            # 保存按钮
            def save_settings():
                try:
                    # 保存快捷键设置
                    new_hotkey = hotkey_var.get().strip()
                    if new_hotkey:
                        self.config.set("settings", "hotkey", new_hotkey)

                    # 保存API设置
                    self.config.set("settings", "api_provider", api_provider_var.get())

                    # 保存OpenAI设置
                    self.config.set("openai", "endpoint", openai_endpoint_entry.get())
                    self.config.set("openai", "api_key", openai_key_var.get())
                    self.config.set("openai", "model", openai_model_var.get())

                    # 保存Anthropic设置
                    self.config.set("anthropic", "api_key", anthropic_key_var.get())
                    self.config.set("anthropic", "model", anthropic_model_var.get())

                    # 保存温度参数
                    provider = api_provider_var.get()
                    if provider == "openai":
                        self.config.set("openai", "temperature", temp_var.get())
                    elif provider == "anthropic":
                        self.config.set("anthropic", "temperature", temp_var.get())

                    # 保存窗口设置
                    self.config.set("settings", "window_width", width_var.get())
                    self.config.set("settings", "window_height", height_var.get())

                    self.save_config()
                    self.register_hotkey()

                    # 更新窗口大小
                    self.root.geometry(f"{width_var.get()}x{height_var.get()}")

                    dialog.destroy()
                    messagebox.showinfo("成功", "设置已保存")
                    logging.info("设置已更新")
                except Exception as e:
                    logging.error(f"保存设置时出错: {str(e)}")
                    messagebox.showerror("错误", f"保存设置失败: {str(e)}")

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=10)

            ttk.Button(btn_frame, text="保存", command=save_settings).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

            # 使所有列可扩展
            for frame in [hotkey_frame, api_frame, window_frame]:
                frame.columnconfigure(1, weight=1)

            logging.info("设置对话框已显示")
        except Exception as e:
            logging.error(f"显示设置对话框时出错: {str(e)}")
            raise

    def run(self):
        """运行主循环"""
        try:
            logging.info("应用程序启动")
            self.root.mainloop()
        except Exception as e:
            logging.error(f"应用程序运行时出错: {str(e)}", exc_info=True)
        finally:
            logging.info("应用程序退出")


def main():
    # 确保单实例运行
    mutex = None
    try:
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "TextEnhancerMutex")
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            ctypes.windll.user32.MessageBoxW(0, "程序已经在运行", "文本增强工具", 0x40)
            logging.warning("程序已经在运行，退出")
            sys.exit(0)

        app = TextEnhancerApp()
        app.run()
    except Exception as e:
        logging.error(f"应用程序初始化失败: {str(e)}", exc_info=True)
        messagebox.showerror("错误", f"应用程序初始化失败: {str(e)}")
    finally:
        if mutex:
            ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()