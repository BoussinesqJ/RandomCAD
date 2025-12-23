# main.py

import logging
from ui.main_window import AggregateGeneratorGUI
import tkinter as tk

# --- 日志配置 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/aggregate_generator.log"),
        logging.StreamHandler()
    ]
)

def main():
    """主函数"""
    logging.info("程序启动")
    root = tk.Tk()
    app = AggregateGeneratorGUI(root)
    root.mainloop()
    logging.info("程序退出")

if __name__ == "__main__":
    main()