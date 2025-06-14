import logging
from logging.handlers import RotatingFileHandler

LOG_FILE = "text_enhancer.log"

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