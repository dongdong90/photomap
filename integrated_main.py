"""
照片地图主程序
版本: v0.9.1
开发日期: 2025-10
开发者: dong, yi, flow, qwen, gemini, grok
版权所有 © 2025 照片地图项目组。保留所有权利。

本程序是照片地图应用的集成版本，提供一体化界面和动态管理功能。

主要功能模块:
- 照片文件夹管理: 添加、删除、刷新照片文件夹
- 照片处理: 动态处理照片（生成缩略图、读取坐标）
- 地图展示: 集成地图显示界面
- 实时更新: 动态更新地图内容
- 智能过滤: 自动跳过没有GPS坐标的照片
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from concurrent.futures import ThreadPoolExecutor
import webbrowser
import logging
import datetime
from PIL import Image, ImageTk
import json
import threading
import time

# 导入现有模块
from utils import scan_photos, process_photo
from map_generator import generate_map_html
from config import SUPPORTED_FORMATS, TEMP_DIR_NAME, THUMBNAIL_SIZE

class IntegratedPhotoMapApp:
    def __init__(self, root):
        self.root = root
        root.title("照片地图")
        
        # 设置窗口大小和扁平化样式
        root.geometry("1200x800")
        root.minsize(1000, 700)
        
        # 设置扁平化窗口样式
        root.configure(bg="#ffffff")
        
        # 初始化数据结构
        self.photo_folders = []  # 存储添加的照片文件夹路径
        self.all_photo_data = []  # 存储所有处理后的照片数据
        self.processing_lock = threading.Lock()  # 处理线程锁
        self.unified_temp_dir = "unified_photo_temp"  # 统一的临时目录
        self.pending_folders = 0  # 批量操作时待处理的文件夹数量
        self.completed_folders = 0  # 批量操作时已完成的文件夹数量
        self.html_path = "integrated_photo_map.html"  # 默认HTML文件路径
        
        # 创建统一临时目录
        os.makedirs(self.unified_temp_dir, exist_ok=True)
        
        # 创建日志目录
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志
        self.setup_logging()
        
        # 创建UI元素
        self.create_ui_elements()
        
        # 启动时加载历史记录但不自动处理
        self.load_folder_history(auto_process=False)
        
        # 检查是否存在已生成的HTML文件并打开
        self.check_and_open_existing_html()

    def setup_logging(self):
        """设置日志记录"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = os.path.join(log_dir, f"integrated_photo_map_{timestamp}.log")
        
        # 更新日志配置
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_filename, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        
        logging.info("一体化照片地图应用启动")

    def create_ui_elements(self):
        """创建所有UI元素"""
        # 主框架 - 扁平化设计
        main_frame = tk.Frame(self.root, bg="#ffffff")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # 创建顶部工具栏
        self.create_top_toolbar(main_frame)
        
        # 创建主内容区域
        content_frame = tk.Frame(main_frame, bg="#ffffff")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        
        # 创建左右布局的主容器
        main_container = tk.Frame(content_frame, bg="#ffffff")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # 左侧区域 - 文件夹管理
        left_frame = tk.Frame(main_container, bg="#ffffff")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        
        # 文件夹管理区域标题
        folder_title = tk.Label(
            left_frame, 
            text="照片文件夹管理", 
            font=("等线", 14, "normal"), 
            fg="#212529",
            bg="#ffffff"
        )
        folder_title.pack(fill=tk.X, pady=(0, 8))
        
        # 文件夹管理区域
        self.create_folder_management_section(left_frame)
        
        # 右侧区域 - 地图和日志
        right_frame = tk.Frame(main_container, bg="#ffffff")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))
        
        # 地图显示区域
        self.create_map_display_section(right_frame)
        
        # 状态信息区域（移到地图下方）
        self.create_status_section(right_frame)
        
        # 页脚
        footer_frame = tk.Frame(content_frame, bg="#ffffff", height=24)
        footer_frame.pack(fill=tk.X, pady=(16, 0))
        footer_frame.pack_propagate(False)
        
        version_label = tk.Label(
            footer_frame, 
            text="照片地图 v0.9.1 by dong, yi, flow, qwen, gemini, grok", 
            font=("等线", 8), 
            fg="#6c757d",
            bg="#ffffff"
        )
        version_label.pack(side=tk.RIGHT)

    def create_top_toolbar(self, parent):
        """创建顶部工具栏"""
        toolbar_frame = tk.Frame(parent, bg="#ffffff", height=60, relief="flat", bd=0)
        toolbar_frame.pack(fill=tk.X, padx=16, pady=(16, 0))
        toolbar_frame.pack_propagate(False)
        
        # 标题
        title_label = tk.Label(
            toolbar_frame, 
            text="照片地图", 
            font=("等线", 16, "normal"), 
            fg="#212529",
            bg="#ffffff"
        )
        title_label.pack(side=tk.LEFT)
        
        # 空白区域
        spacer = tk.Frame(toolbar_frame, bg="#ffffff")
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 照片处理功能按钮 - 右对齐
        button_frame = tk.Frame(toolbar_frame, bg="#ffffff")
        button_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加照片文件夹按钮
        add_folder_btn = self.create_flat_button(
            button_frame, 
            "添加文件夹", 
            self.add_photo_folder,
            "#4361ee", 
            "#3a0ca3"
        )
        add_folder_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # 刷新所有文件夹按钮
        refresh_btn = self.create_flat_button(
            button_frame, 
            "刷新", 
            self.refresh_all_folders,
            "#4cc9f0", 
            "#4895ef"
        )
        refresh_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # 删除文件夹按钮
        delete_btn = self.create_flat_button(
            button_frame, 
            "删除", 
            self.remove_selected_folder,
            "#f72585", 
            "#b5179e"
        )
        delete_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # 生成地图按钮
        generate_map_btn = self.create_flat_button(
            button_frame, 
            "生成地图", 
            self.generate_and_update_map,
            "#4facfe", 
            "#00f2fe"
        )
        generate_map_btn.pack(side=tk.LEFT, padx=(0, 8))
        
    def open_settings(self):
        """打开设置对话框"""
        messagebox.showinfo("设置", "设置功能待实现")
        
    def show_help(self):
        """显示帮助信息"""
        help_text = """
照片地图一体化工具使用说明：

1. 添加照片文件夹：选择包含照片的文件夹
2. 刷新所有文件夹：重新扫描所有已添加的文件夹
3. 生成并更新地图：根据照片地理位置生成地图
4. 在地图区域可以预览生成的地图
5. 点击"在浏览器中打开地图"查看完整交互地图
        """
        messagebox.showinfo("帮助", help_text)

    def create_folder_management_section(self, parent):
        """创建文件夹管理区域"""
        # 区域框架 - 扁平化设计
        section_frame = tk.Frame(parent, bg="#ffffff")
        section_frame.pack(fill=tk.BOTH, expand=True)
        
        # 文件夹列表容器
        list_container = tk.Frame(section_frame, bg="#f8f9fa")
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # 文件夹列表
        list_frame = tk.Frame(list_container, bg="#ffffff")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview显示文件夹列表 - 扁平化样式
        columns = ("path", "status", "photo_count")
        self.folder_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        # 定义列标题
        self.folder_tree.heading("path", text="文件夹路径")
        self.folder_tree.heading("status", text="状态")
        self.folder_tree.heading("photo_count", text="照片数量")
        
        # 定义列宽
        self.folder_tree.column("path", width=300)
        self.folder_tree.column("status", width=80)
        self.folder_tree.column("photo_count", width=80)
        
        # 设置样式
        style = ttk.Style()
        style.configure("Treeview", 
                        background="#ffffff",
                        foreground="#212529",
                        rowheight=24,
                        fieldbackground="#ffffff",
                        relief="flat",
                        bd=0)
        style.configure("Treeview.Heading",
                        background="#f8f9fa",
                        foreground="#212529",
                        relief="flat",
                        font=("等线", 9, "normal"))
        style.map("Treeview", background=[("selected", "#e9ecef")], foreground=[("selected", "#212529")])
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.folder_tree.yview)
        self.folder_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.folder_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右键菜单
        self.folder_menu = tk.Menu(self.folder_tree, tearoff=0, font=("等线", 9))
        self.folder_menu.add_command(label="刷新", command=self.refresh_selected_folder)
        self.folder_menu.add_command(label="删除", command=self.remove_selected_folder)
        self.folder_menu.add_command(label="在文件管理器中打开", command=self.open_folder_in_explorer)
        
        # 绑定右键菜单
        self.folder_tree.bind("<Button-3>", self.show_folder_context_menu)

    def create_map_display_section(self, parent):
        """创建地图显示区域"""
        # 区域框架 - 扁平化设计
        section_frame = tk.Frame(parent, bg="#ffffff")
        section_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        # 标题栏
        title_bar = tk.Frame(section_frame, bg="#ffffff", height=32)
        title_bar.pack(fill=tk.X, pady=(0, 8))
        title_bar.pack_propagate(False)
        
        title_label = tk.Label(
            title_bar, 
            text="地图预览", 
            font=("等线", 14, "normal"), 
            fg="#212529",
            bg="#ffffff"
        )
        title_label.pack(side=tk.LEFT)
        
        # 地图状态标签
        self.map_status_label = tk.Label(
            title_bar,
            text="未生成地图",
            font=("等线", 9),
            fg="#6c757d",
            bg="#ffffff"
        )
        self.map_status_label.pack(side=tk.RIGHT)
        
        # 地图控制工具栏
        map_toolbar = tk.Frame(section_frame, bg="#ffffff")
        map_toolbar.pack(fill=tk.X, pady=(0, 8))
        
        # 打开外部浏览器按钮 - 扁平化样式
        open_browser_btn = self.create_flat_button(
            map_toolbar, 
            "在浏览器中打开", 
            self.open_map_in_browser,
            "#4361ee", 
            "#3a0ca3"
        )
        open_browser_btn.pack(side=tk.LEFT)
        
        # 地图显示区域（使用Canvas作为占位符）
        map_display_frame = tk.Frame(section_frame, bg="#f8f9fa")
        map_display_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建地图显示画布 - 扁平化设计
        self.map_canvas = tk.Canvas(map_display_frame, bg="#ffffff", highlightthickness=0, relief="flat")
        self.map_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 添加扁平化的地图预览占位图
        self.map_placeholder = tk.Label(
            self.map_canvas,
            text="🗺️ 地图预览区域\n点击上方按钮在浏览器中查看完整地图",
            font=("等线", 11),
            fg="#6c757d",
            bg="#ffffff"
        )
        self.map_placeholder.place(relx=0.5, rely=0.5, anchor="center")

    def create_status_section(self, parent):
        """创建状态信息区域"""
        # 区域框架 - 扁平化设计
        section_frame = tk.Frame(parent, bg="#ffffff")
        section_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题栏
        title_bar = tk.Frame(section_frame, bg="#ffffff", height=32)
        title_bar.pack(fill=tk.X, pady=(0, 8))
        title_bar.pack_propagate(False)
        
        title_label = tk.Label(
            title_bar, 
            text="处理日志", 
            font=("等线", 14, "normal"), 
            fg="#212529",
            bg="#ffffff"
        )
        title_label.pack(side=tk.LEFT)
        
        # 清空日志按钮 - 扁平化样式
        clear_log_btn = self.create_flat_button(
            title_bar, 
            "清空日志", 
            self.clear_status_log,
            "#f72585", 
            "#b5179e"
        )
        clear_log_btn.pack(side=tk.RIGHT)
        
        # 状态文本框容器
        status_container = tk.Frame(section_frame, bg="#f8f9fa")
        status_container.pack(fill=tk.BOTH, expand=True)
        
        # 状态文本框 - 扁平化设计
        text_frame = tk.Frame(status_container, bg="#ffffff")
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_text = tk.Text(
            text_frame, 
            wrap=tk.WORD, 
            bg="#ffffff", 
            fg="#212529",
            font=("等线", 9),
            relief="flat",
            padx=12,
            pady=12,
            spacing1=2,
            spacing2=2,
            spacing3=2
        )
        
        # 滚动条
        status_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 进度条容器
        progress_frame = tk.Frame(section_frame, bg="#ffffff")
        progress_frame.pack(fill=tk.X, pady=(8, 0))
        
        # 进度条标签
        self.progress_label = tk.Label(
            progress_frame,
            text="处理进度: 0%",
            font=("等线", 9),
            fg="#6c757d",
            bg="#ffffff"
        )
        self.progress_label.pack(side=tk.LEFT)
        
        # 进度条
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            length=200
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 进度条数值显示
        self.progress_value_label = tk.Label(
            progress_frame,
            text="0/0",
            font=("等线", 9),
            fg="#6c757d",
            bg="#ffffff"
        )
        self.progress_value_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 设置文本框标签样式
        self.status_text.tag_configure("timestamp", foreground="#6c757d", font=("等线", 8))
        self.status_text.tag_configure("info", foreground="#1e90ff")
        self.status_text.tag_configure("warning", foreground="#ffa500")
        self.status_text.tag_configure("error", foreground="#ff4500")

    def create_styled_button(self, parent, text, command, color1, color2, width=120, height=35):
        """创建样式化按钮"""
        # 创建按钮框架
        button_frame = tk.Frame(parent, bg="#ffffff", width=width, height=height)
        button_frame.pack_propagate(False)
        
        # 创建按钮
        button = tk.Button(
            button_frame,
            text=text,
            command=command,
            font=("等线", 10, "bold"),
            fg="white",
            bg=color1,
            activebackground=color2,
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        
        # 添加悬停效果
        def on_enter(e):
            button.config(bg=color2)
            # 添加轻微的提升效果
            button_frame.config(relief="solid", bd=1)
        
        def on_leave(e):
            button.config(bg=color1)
            # 恢复原始状态
            button_frame.config(relief="flat", bd=0)
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        
        # 添加阴影效果
        button_frame.config(
            highlightbackground="#e0e0e0",
            highlightcolor="#e0e0e0",
            highlightthickness=1
        )
        
        button.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        return button_frame

    def create_modern_button(self, parent, text, command, color1, color2, width=150, height=35):
        """创建现代化按钮"""
        # 创建按钮框架
        button_frame = tk.Frame(parent, bg=parent.cget("bg"), width=width, height=height)
        button_frame.pack_propagate(False)
        
        # 创建现代化按钮
        button = tk.Button(
            button_frame,
            text=text,
            command=command,
            font=("等线", 10, "bold"),
            fg="white",
            bg=color1,
            activebackground=color2,
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=20,
            pady=5
        )
        
        # 添加悬停效果和阴影
        def on_enter(e):
            button.config(bg=color2)
            button_frame.config(bg=color2)
        
        def on_leave(e):
            button.config(bg=color1)
            button_frame.config(bg=parent.cget("bg"))
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        
        # 圆角效果和阴影通过框架实现
        button_frame.config(
            relief="flat",
            bd=0
        )
        
        button.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        return button_frame

    def create_flat_button(self, parent, text, command, color1, color2, width=100, height=32):
        """创建扁平化按钮"""
        # 创建按钮框架
        button_frame = tk.Frame(parent, bg=parent.cget("bg"), width=width, height=height)
        button_frame.pack_propagate(False)
        
        # 创建扁平化按钮
        button = tk.Button(
            button_frame,
            text=text,
            command=command,
            font=("等线", 9, "normal"),
            fg="white",
            bg=color1,
            activebackground=color2,
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=12,
            pady=4
        )
        
        # 添加悬停效果
        def on_enter(e):
            button.config(bg=color2)
        
        def on_leave(e):
            button.config(bg=color1)
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        
        button.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        return button_frame

    def log_status(self, message):
        """记录状态信息"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}\n"
        
        # 添加到状态文本框
        self.status_text.insert(tk.END, log_message)
        self.status_text.see(tk.END)
        
        # 记录到日志文件
        logging.info(message)

    def show_folder_context_menu(self, event):
        """显示文件夹右键菜单"""
        item = self.folder_tree.identify_row(event.y)
        if item:
            self.folder_tree.selection_set(item)
            self.folder_menu.post(event.x_root, event.y_root)

    def add_photo_folder(self):
        """添加照片文件夹"""
        folder_path = filedialog.askdirectory(title="选择照片文件夹")
        if folder_path:
            # 检查文件夹是否已存在
            if folder_path in self.photo_folders:
                messagebox.showinfo("提示", f"文件夹 {folder_path} 已添加")
                return
            
            self.photo_folders.append(folder_path)
            self.log_status(f"添加照片文件夹: {folder_path}")
            
            # 添加到Treeview
            folder_id = self.folder_tree.insert("", "end", values=(folder_path, "未处理", "0"))
            
            # 保存到历史记录
            self.save_folder_history()
            
            # 开始处理该文件夹（单个操作）
            self.process_folder_async(folder_path, folder_id, is_batch_operation=False)

    def remove_selected_folder(self):
        """删除选中的文件夹"""
        selected = self.folder_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的文件夹")
            return
            
        # 获取选中项的数据
        item = selected[0]
        values = self.folder_tree.item(item, "values")
        folder_path = values[0]
        
        # 确认删除
        if messagebox.askyesno("确认删除", f"确定要删除文件夹 {folder_path} 吗？"):
            # 从列表中移除
            if folder_path in self.photo_folders:
                self.photo_folders.remove(folder_path)
            
            # 从照片数据中移除该文件夹的照片
            with self.processing_lock:
                self.all_photo_data = [p for p in self.all_photo_data if not p["photo_path"].startswith(folder_path)]
            
            # 保存历史记录
            self.save_folder_history()
            
            # 从Treeview中移除
            self.folder_tree.delete(item)
            
            self.log_status(f"删除照片文件夹: {folder_path}")
            
            # 保存更新后的文件夹历史记录
            self.save_folder_history()
            
            # 更新地图（单个操作）
            self.generate_and_update_map_async()

    def refresh_selected_folder(self):
        """刷新选中的文件夹"""
        selected = self.folder_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要刷新的文件夹")
            return
            
        # 获取选中项的数据
        item = selected[0]
        values = self.folder_tree.item(item, "values")
        folder_path = values[0]
        
        # 从照片数据中移除该文件夹的旧照片数据
        with self.processing_lock:
            self.all_photo_data = [p for p in self.all_photo_data if not p["photo_path"].startswith(folder_path)]
        
        # 重新处理该文件夹（单个操作）
        self.process_folder_async(folder_path, item, is_batch_operation=False)

    def refresh_all_folders(self):
        """刷新所有文件夹"""
        if not self.photo_folders:
            messagebox.showwarning("警告", "没有添加任何照片文件夹")
            return
            
        # 确认刷新
        if messagebox.askyesno("确认刷新", "确定要刷新所有文件夹吗？这可能需要一些时间。"):
            self.log_status("开始刷新所有文件夹...")
            
            # 清空现有照片数据
            self.all_photo_data.clear()
            
            # 重置进度条
            self.reset_progress_bar()
            
            # 记录需要处理的文件夹数量
            self.pending_folders = len(self.folder_tree.get_children())
            self.completed_folders = 0
            
            # 重新处理所有文件夹，标记为批量操作
            for item in self.folder_tree.get_children():
                values = self.folder_tree.item(item, "values")
                folder_path = values[0]
                self.process_folder_async(folder_path, item, is_batch_operation=True)
            
            # 启动检查完成状态的线程
            self.check_batch_completion()

    def check_batch_completion(self):
        """检查批量操作是否完成"""
        def check_thread():
            # 等待所有文件夹处理完成
            while self.completed_folders < self.pending_folders:
                time.sleep(0.5)  # 每500ms检查一次
            
            # 所有文件夹处理完成后，更新地图
            self.root.after(0, self.generate_and_update_map_async)
            self.log_status("所有文件夹刷新完成，地图已更新")
            
            # 重置进度条
            self.root.after(0, self.reset_progress_bar)
        
        # 启动检查线程
        threading.Thread(target=check_thread, daemon=True).start()

    def open_folder_in_explorer(self):
        """在文件管理器中打开选中的文件夹"""
        selected = self.folder_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要打开的文件夹")
            return
            
        # 获取选中项的数据
        item = selected[0]
        values = self.folder_tree.item(item, "values")
        folder_path = values[0]
        
        # 打开文件夹
        try:
            os.startfile(folder_path)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {str(e)}")

    def process_folder_async(self, folder_path, folder_id, is_batch_operation=False):
        """异步处理文件夹"""
        # 更新状态为处理中
        self.folder_tree.item(folder_id, values=(folder_path, "处理中", "0"))
        
        # 在线程中处理
        def process_thread():
            try:
                self.log_status(f"开始处理文件夹: {folder_path}")
                
                # 使用统一的临时目录
                temp_dir = self.unified_temp_dir
                
                # 扫描照片
                photo_list = scan_photos(folder_path, SUPPORTED_FORMATS, TEMP_DIR_NAME)
                self.log_status(f"在 {folder_path} 中找到 {len(photo_list)} 张照片")
                
                # 处理照片
                photo_data = []
                processed_count = 0
                total_photos = len(photo_list)
                
                # 更新进度条总数
                self.root.after(0, lambda: self.update_progress_bar(0, total_photos))
                
                with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
                    futures = [
                        executor.submit(
                            self.safe_process_photo,
                            photo_path,
                            temp_dir,
                            folder_path,
                        )
                        for photo_path in photo_list
                    ]
                    
                    for i, future in enumerate(futures, 1):
                        try:
                            result = future.result()
                            if result:
                                photo_data.append(result)
                                processed_count += 1
                                
                            # 更新进度条
                            self.root.after(0, lambda current=i, total=total_photos: self.update_progress_bar(current, total))
                            
                            # 更新文件夹列表中的照片计数
                            self.root.after(0, lambda fid=folder_id, count=processed_count: self.folder_tree.item(
                                fid, 
                                values=(folder_path, "处理中", str(count))
                            ))
                        except Exception as e:
                            self.log_status(f"处理照片时出错: {str(e)}", "error")
                
                # 更新全局照片数据
                with self.processing_lock:
                    # 移除该文件夹的旧数据
                    self.all_photo_data = [p for p in self.all_photo_data if not p["photo_path"].startswith(folder_path)]
                    # 添加新数据
                    self.all_photo_data.extend(photo_data)
                
                # 更新UI
                self.root.after(0, lambda: self.folder_tree.item(
                    folder_id, 
                    values=(folder_path, "已完成", str(processed_count))
                ))
                
                self.log_status(f"文件夹 {folder_path} 处理完成，共处理 {processed_count} 张照片")
                
                # 保存更新后的文件夹历史记录
                self.save_folder_history()
                
                # 更新完成计数器（如果是批量操作）
                if is_batch_operation:
                    with self.processing_lock:
                        self.completed_folders += 1
                
                # 根据操作类型决定是否更新地图
                if is_batch_operation:
                    # 批量操作时，不立即打开HTML，等所有操作完成后再打开
                    pass
                else:
                    # 单个操作时，立即更新地图
                    self.generate_and_update_map_async()
                
            except Exception as e:
                self.log_status(f"处理文件夹 {folder_path} 时出错: {str(e)}", "error")
                self.root.after(0, lambda: self.folder_tree.item(
                    folder_id, 
                    values=(folder_path, "处理失败", "0")
                ))
                
                # 更新完成计数器（即使是失败的情况）
                if is_batch_operation:
                    with self.processing_lock:
                        self.completed_folders += 1
                
                # 重置进度条
                self.root.after(0, self.reset_progress_bar)
        
        # 启动处理线程
        threading.Thread(target=process_thread, daemon=True).start()

    def safe_process_photo(self, photo_path, temp_dir, base_dir):
        """安全处理单张照片"""
        try:
            # 处理照片
            result = process_photo(
                photo_path,
                temp_dir,
                base_dir,
                thumbnail_size=THUMBNAIL_SIZE,
            )
            
            # 如果处理成功，确保照片和缩略图路径正确
            # utils.py中的process_photo已经处理了路径，这里不需要重复处理
            # 只需要确保路径是相对于HTML文件所在目录的
            if result:
                # 检查是否有GPS坐标，如果没有则跳过处理
                if result["latitude"] is None or result["longitude"] is None:
                    self.log_status(f"跳过处理照片 {photo_path}：没有GPS坐标信息")
                    return None
                
                # 确保照片路径和缩略图路径相对于当前目录（HTML文件所在目录）
                photo_path_from_result = result["photo_path"]
                thumbnail_path_from_result = result["thumbnail_path"]
                
                # 确保照片路径相对于当前目录
                try:
                    if photo_path_from_result.startswith("file:///"):
                        # 已经是绝对路径，保持不变
                        result["photo_path"] = photo_path_from_result
                    else:
                        result["photo_path"] = os.path.relpath(photo_path_from_result, ".").replace("\\", "/")
                except ValueError:
                    # 跨磁盘情况，使用绝对路径
                    if not photo_path_from_result.startswith("file:///"):
                        result["photo_path"] = "file:///" + os.path.abspath(photo_path_from_result).replace("\\", "/")
                
                # 确保缩略图路径相对于当前目录
                try:
                    if thumbnail_path_from_result.startswith("file:///"):
                        # 已经是绝对路径，保持不变
                        result["thumbnail_path"] = thumbnail_path_from_result
                    else:
                        result["thumbnail_path"] = os.path.relpath(thumbnail_path_from_result, ".").replace("\\", "/")
                except ValueError:
                    # 跨磁盘情况，使用绝对路径
                    if not thumbnail_path_from_result.startswith("file:///"):
                        result["thumbnail_path"] = "file:///" + os.path.abspath(thumbnail_path_from_result).replace("\\", "/")
                
            return result
        except Exception as e:
            logging.error(f"处理 {photo_path} 时出错: {str(e)}")
            return None

    def generate_and_update_map(self):
        """生成并更新地图"""
        if not self.all_photo_data:
            messagebox.showwarning("警告", "没有可显示的照片数据")
            return
            
        # 确认生成地图
        if messagebox.askyesno("确认生成", "确定要生成新的地图吗？"):
            self.generate_and_update_map_async()

    def generate_and_update_map_async(self):
        """异步生成并更新地图"""
        if not self.all_photo_data:
            self.log_status("没有照片数据可生成地图")
            return
            
        def generate_thread():
            try:
                self.log_status(f"开始生成地图，共 {len(self.all_photo_data)} 张照片...")
                
                # 生成地图HTML文件（使用当前目录作为基础目录）
                base_dir = "."
                html_path = generate_map_html(self.all_photo_data, base_dir, "integrated_photo_map.html")
                
                if html_path:
                    self.log_status(f"地图生成成功: {html_path}")
                    # 保存HTML路径供后续使用
                    self.html_path = html_path
                    # 在浏览器中打开地图
                    self.root.after(0, lambda: webbrowser.open(f"file://{os.path.abspath(html_path)}"))
                else:
                    self.log_status("地图生成失败")
                    
            except Exception as e:
                self.log_status(f"生成地图时出错: {str(e)}", "error")
        
        # 启动生成线程
        threading.Thread(target=generate_thread, daemon=True).start()

    def open_map_in_browser(self):
        """在浏览器中打开地图"""
        if hasattr(self, 'html_path') and os.path.exists(self.html_path):
            webbrowser.open(f"file://{os.path.abspath(self.html_path)}")
            self.update_map_preview()
        else:
            messagebox.showwarning("警告", "请先生成地图")
    
    def update_map_preview(self):
        """更新地图预览"""
        if hasattr(self, 'html_path') and os.path.exists(self.html_path):
            # 在预览区域显示地图已生成的提示
            self.map_placeholder.config(
                text="地图已生成\n点击上方按钮在浏览器中查看完整地图",
                fg="#4facfe"
            )
            
            # 可以在这里添加更多预览功能，例如:
            # 1. 使用matplotlib生成静态地图预览
            # 2. 显示照片分布的统计信息
            # 3. 显示最新的处理状态
            
            # 示例：显示照片统计信息
            photo_count = len(self.all_photo_data)
            folder_count = len(self.photo_folders)
            
            # 更新地图状态标签
            self.map_status_label.config(
                text=f"已生成地图 ({photo_count}张照片, {folder_count}个文件夹)",
                fg="#4facfe"
            )
        else:
            self.map_placeholder.config(
                text="地图预览区域\n点击上方按钮在浏览器中查看完整地图",
                fg="#999999"
            )
            self.map_status_label.config(text="未生成地图", fg="#999999")

    def log_status(self, message, level="info"):
        """记录状态信息"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        
        # 添加到状态文本框，使用不同标签样式
        self.status_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        
        if level == "warning":
            self.status_text.insert(tk.END, f"{message}\n", "warning")
        elif level == "error":
            self.status_text.insert(tk.END, f"{message}\n", "error")
        else:
            self.status_text.insert(tk.END, f"{message}\n", "info")
            
        self.status_text.see(tk.END)
        
        # 记录到日志文件
        if level == "warning":
            logging.warning(message)
        elif level == "error":
            logging.error(message)
        else:
            logging.info(message)

    def clear_status_log(self):
        """清空状态日志"""
        self.status_text.delete(1.0, tk.END)

    def reset_progress_bar(self):
        """重置进度条"""
        self.progress_bar["value"] = 0
        self.progress_label.config(text="处理进度: 0%")
        self.progress_value_label.config(text="0/0")

    def update_progress_bar(self, current, total):
        """更新进度条"""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar["value"] = progress
            self.progress_label.config(text=f"处理进度: {progress}%")
            self.progress_value_label.config(text=f"{current}/{total}")
        else:
            self.reset_progress_bar()

    def save_folder_history(self):
        """保存文件夹历史记录，包括状态和照片数量"""
        try:
            # 创建包含详细信息的文件夹数据
            folder_details = []
            for item in self.folder_tree.get_children():
                values = self.folder_tree.item(item, "values")
                folder_details.append({
                    "path": values[0],
                    "status": values[1],
                    "photo_count": values[2]
                })
            
            history_file = os.path.join("logs", "folder_history.json")
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump([folder["path"] for folder in folder_details], f, ensure_ascii=False, indent=2)
            
            # 保存详细的文件夹状态信息
            details_file = os.path.join("logs", "folder_details.json")
            with open(details_file, "w", encoding="utf-8") as f:
                json.dump(folder_details, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存文件夹历史记录时出错: {str(e)}")

    def load_folder_history(self, auto_process=False):
        """加载文件夹历史记录"""
        try:
            history_file = os.path.join("logs", "folder_history.json")
            details_file = os.path.join("logs", "folder_details.json")
            
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    folders = json.load(f)
                    self.photo_folders = folders
                    
                # 尝试加载详细的文件夹状态信息
                if os.path.exists(details_file):
                    with open(details_file, "r", encoding="utf-8") as f:
                        folder_details = json.load(f)
                    
                    # 添加到UI，使用保存的状态和照片数量
                    for folder_info in folder_details:
                        self.folder_tree.insert("", "end", values=(
                            folder_info["path"], 
                            folder_info["status"], 
                            folder_info["photo_count"]
                        ))
                else:
                    # 如果没有详细信息文件，使用默认值
                    for folder in folders:
                        self.folder_tree.insert("", "end", values=(folder, "未处理", "0"))
                    
                # 如果需要自动处理，则处理文件夹
                if auto_process and folders:
                    # 记录需要处理的文件夹数量
                    self.pending_folders = len(folders)
                    self.completed_folders = 0
                    
                    # 处理所有文件夹
                    for item in self.folder_tree.get_children():
                        values = self.folder_tree.item(item, "values")
                        folder_path = values[0]
                        # 使用批量操作模式处理文件夹
                        self.process_folder_async(folder_path, item, is_batch_operation=True)
                    
                    # 启动检查完成状态的线程
                    self.check_batch_completion()
        except Exception as e:
            self.log_status(f"加载文件夹历史记录时出错: {str(e)}", "error")

    def check_and_open_existing_html(self):
        """检查并打开已存在的HTML文件"""
        if os.path.exists(self.html_path):
            try:
                webbrowser.open(f"file://{os.path.abspath(self.html_path)}")
                self.log_status(f"打开已存在的地图文件: {self.html_path}")
            except Exception as e:
                self.log_status(f"打开地图文件时出错: {str(e)}", "error")

if __name__ == "__main__":
    root = tk.Tk()
    app = IntegratedPhotoMapApp(root)
    root.mainloop()