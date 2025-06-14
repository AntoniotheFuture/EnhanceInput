import logging
import os
from configparser import ConfigParser

CONFIG_FILE = "text_enhancer.ini"

DEFAULT_CONFIG = {
    "settings": {
        "hotkey": "ctrl+alt+e",
        "api_provider": "openai",
        "window_width": "400",
        "window_height": "200",
        "prompt": f"请为以下文本提供三种更优雅、专业的表达方式，保持原意但改进措辞。"
                f"直接返回三个选项，每个选项占一行，不要编号或其他说明。\n\n"
                f"文本:<text>",
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

class ConfigManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_file=CONFIG_FILE):
        if not hasattr(self, "initialized"):
            """加载或创建配置文件"""
            self.config = ConfigParser()
            try:
                if not os.path.exists(CONFIG_FILE):
                    logging.info("未找到配置文件，创建默认配置")
                    self.config.read_dict(DEFAULT_CONFIG)
                    with open(CONFIG_FILE, "w") as f:
                        self.config.write(f)
                else:
                    self.config.read(CONFIG_FILE)
                    logging.info("配置文件加载成功")
                self.initialized = True
            except Exception as e:
                logging.error(f"加载配置文件失败: {str(e)}")
                raise

    def get(self, section, key, fallback=None):
        """获取配置值"""
        return self.config.get(section, key, fallback=fallback)

    def get_default(self):
        return DEFAULT_CONFIG

    def set(self, section, key, value):
        """设置配置值"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, value)

    def getfloat(self, section, key, fallback=None):
        """获取配置值"""
        return self.config.getfloat(section, key, fallback=fallback)

    def save(self, config_file=CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w") as f:
                self.config.write(f)
            logging.info("配置文件保存成功")
        except Exception as e:
            logging.error(f"保存配置文件失败: {str(e)}")
            raise



# 全局访问配置对象
def get_config():
    return ConfigManager()
