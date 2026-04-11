import logging
import sys
from pathlib import Path


def setup_logger(name="DouyinDownloader", log_dir=None):
    """
    设置日志记录器

    Args:
        name: 日志名称
        log_dir: 日志文件目录，如果为 None 则只输出到控制台
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.propagate = False

        # 终端输出处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件日志处理器（如果指定了 log_dir）
        if log_dir:
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            log_file = log_path / "cli.log"

            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)  # 文件记录更详细的 DEBUG 信息
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


logger = setup_logger()

