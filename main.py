"""
RandomCAD 主入口文件

随机骨料颗粒生成器 - 支持 AutoCAD 和中望CAD
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/randomcad.log"),
        logging.StreamHandler()
    ]
)


def main():
    """
    主函数
    
    初始化日志并启动 UI
    """
    logging.info("=" * 60)
    logging.info("RandomCAD 随机骨料生成器启动")
    logging.info("=" * 60)
    
    try:
        from src.ui.main_window import main as run_ui
        run_ui()
    except ImportError as e:
        logging.error(f"导入模块失败: {e}")
        logging.error("请确保所有依赖已正确安装")
        logging.error("运行: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logging.error(f"程序运行出错: {e}", exc_info=True)
        sys.exit(1)
    
    logging.info("=" * 60)
    logging.info("RandomCAD 程序退出")
    logging.info("=" * 60)


if __name__ == "__main__":
    main()
