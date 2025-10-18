"""
照片地图主程序
版本: v0.1  
开发日期: 2025-03
开发者: HuangHuadong & HangYi
版权所有 © 2025 照片地图项目组。保留所有权利。

本程序是照片地图应用的主入口，提供图形界面和核心功能。

主要功能模块:
- 照片扫描: 递归扫描指定目录下的照片文件
- EXIF解析: 提取照片的GPS、时间等EXIF信息
- 地图生成: 基于照片位置信息生成交互式地图
- 缩略图处理: 生成照片缩略图用于地图标记
- 历史记录: 保存和加载之前的扫描记录
- 进度监控: 实时显示处理进度和状态

开源引用说明：
- Leaflet.js (https://leafletjs.com) - 用于地图展示，遵循 BSD-2-Clause 许可
- OpenStreetMap (https://www.openstreetmap.org) - 地图数据来源，遵循 ODbL 许可
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor
from utils import scan_photos, process_photo
from map_generator import generate_map_html
from config import SUPPORTED_FORMATS, TEMP_DIR_NAME, THUMBNAIL_SIZE
from tkinter import ttk
import webbrowser
import logging
import datetime
from PIL import Image, ImageTk  # For custom buttons and styling
import json  # For history file handling

# Custom themed widgets
class GradientFrame(tk.Canvas):
    """
    渐变背景框架组件
    
    参考自：TkinterDesigner项目
    来源：https://github.com/ParthJadhav/Tkinter-Designer
    许可：MIT License
    """
    def __init__(self, parent, color1="#f5f7fa", color2="#c3cfe2", **kwargs):
        tk.Canvas.__init__(self, parent, **kwargs)
        self._color1 = color1
        self._color2 = color2
        self.bind("<Configure>", self._draw_gradient)

    def _draw_gradient(self, event=None):
        self.delete("gradient")
        width = self.winfo_width()
        height = self.winfo_height()
        limit = width
        (r1, g1, b1) = self.winfo_rgb(self._color1)
        (r2, g2, b2) = self.winfo_rgb(self._color2)
        r_ratio = float(r2 - r1) / limit
        g_ratio = float(g2 - g1) / limit
        b_ratio = float(b2 - b1) / limit

        for i in range(limit):
            nr = int(r1 + (r_ratio * i))
            ng = int(g1 + (g_ratio * i))
            nb = int(b1 + (b_ratio * i))
            color = "#%4.4x%4.4x%4.4x" % (nr, ng, nb)
            self.create_line(i, 0, i, height, tags=("gradient",), fill=color)
        self.lower("gradient")

class StyledButton(tk.Canvas):
    """
    自定义样式按钮组件
    
    参考自：CustomTkinter项目
    来源：https://github.com/TomSchimansky/CustomTkinter
    许可：MIT License
    """
    def __init__(self, parent, text, command=None, width=180, height=40, 
                 bg_color="#4287f5", hover_color="#3278e5", textcolor="white", 
                 corner_radius=10, **kwargs):
        tk.Canvas.__init__(self, parent, width=width, height=height, 
                          highlightthickness=0, bd=0, **kwargs)
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.textcolor = textcolor
        self.corner_radius = corner_radius
        self.command = command
        self.text = text
        
        # 固定尺寸
        self.width = width
        self.height = height
        self.configure(width=width, height=height)
        
        # 初始绘制
        self.button_shape = None
        self.text_shape = None
        self.draw_normal()
        
        # 绑定事件
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
        # 保存事件处理器引用
        self._on_press = self.on_press
        self._on_release = self.on_release
    
    def draw_normal(self):
        self.delete("all")
        self.button_shape = self.create_rounded_rectangle(
            0, 0, self.width, self.height, 
            radius=self.corner_radius, 
            fill=self.bg_color, 
            outline="")
        self.text_shape = self.create_text(
            self.width/2, 
            self.height/2, 
            text=self.text, 
            fill=self.textcolor, 
            font=("等线", 11, "bold")
        )
        
    def draw_hover(self):
        self.delete("all")
        self.button_shape = self.create_rounded_rectangle(
            0, 0, self.width, self.height, 
            radius=self.corner_radius, 
            fill=self.hover_color, 
            outline="")
        self.text_shape = self.create_text(
            self.width/2, 
            self.height/2, 
            text=self.text, 
            fill=self.textcolor, 
            font=("等线", 11, "bold")
        )
    
    def draw_pressed(self):
        self.delete("all")
        self.button_shape = self.create_rounded_rectangle(
            2, 2, self.width-2, self.height-2, 
            radius=self.corner_radius, 
            fill=self.hover_color, 
            outline="")
        self.text_shape = self.create_text(
            self.width/2+1, 
            self.height/2+1, 
            text=self.text, 
            fill=self.textcolor, 
            font=("等线", 11, "bold")
        )
    
    def create_rounded_rectangle(self, x1, y1, x2, y2, radius=10, **kwargs):
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, **kwargs, smooth=True)
    
    def on_enter(self, event):
        self.draw_hover()
        
    def on_leave(self, event):
        self.draw_normal()
        
    def on_press(self, event):
        self.draw_pressed()
        if self.command:
            self.command()
            
    def on_release(self, event):
        self.draw_hover() if self.winfo_containing(event.x_root, event.y_root) == self else self.draw_normal()

class StyledProgressBar(tk.Canvas):
    """
    自定义样式进度条组件
    
    参考自：CustomTkinter项目
    来源：https://github.com/TomSchimansky/CustomTkinter
    许可：MIT License
    """
    def __init__(self, parent, width=300, height=15, color1="#ff416c", color2="#ff4b2b", 
                 bg_color="#f0f0f0", corner_radius=8, **kwargs):
        tk.Canvas.__init__(self, parent, width=width, height=height, 
                           highlightthickness=0, **kwargs)
        self.color1 = color1
        self.color2 = color2
        self.bg_color = bg_color
        self.corner_radius = corner_radius
        self.progress_value = 0
        
        # Draw the progress bar
        self._draw_progress()
        
    def _draw_progress(self):
        self.delete("all")
        
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Calculate progress width
        progress_width = int(width * (self.progress_value / 100.0))
        
        # Add subtle shadow effect for 3D appearance
        shadow_color = "#eeeeee"  # Very light gray
        shadow_offset = 1
        self.create_rectangle(
            shadow_offset, shadow_offset, 
            width + shadow_offset, height + shadow_offset,
            fill=shadow_color, outline="", width=0
        )
        
        # Draw background - manual rounded rectangle
        # Main rectangle
        self.create_rectangle(
            self.corner_radius, 0, 
            width - self.corner_radius, height, 
            fill=self.bg_color, outline="")
        self.create_rectangle(
            0, self.corner_radius, 
            width, height - self.corner_radius, 
            fill=self.bg_color, outline="")
        
        # Create rounded corner arcs for background
        self.create_arc(0, 0, 2*self.corner_radius, 2*self.corner_radius, 
                         start=90, extent=90, fill=self.bg_color, outline="")
        self.create_arc(width - 2*self.corner_radius, 0, width, 2*self.corner_radius, 
                         start=0, extent=90, fill=self.bg_color, outline="")
        self.create_arc(0, height - 2*self.corner_radius, 2*self.corner_radius, height, 
                         start=180, extent=90, fill=self.bg_color, outline="")
        self.create_arc(width - 2*self.corner_radius, height - 2*self.corner_radius, width, height, 
                         start=270, extent=90, fill=self.bg_color, outline="")
        
        # Draw progress fill with gradient if there is progress
        if progress_width > 0:
            # Create gradient fill for progress
            for i in range(progress_width):
                # Linear gradient calculation
                r = i / width if width > 0 else 0
                color_r = int(int(self.color1[1:3], 16) * (1-r) + int(self.color2[1:3], 16) * r)
                color_g = int(int(self.color1[3:5], 16) * (1-r) + int(self.color2[3:5], 16) * r)
                color_b = int(int(self.color1[5:7], 16) * (1-r) + int(self.color2[5:7], 16) * r)
                color = f"#{color_r:02x}{color_g:02x}{color_b:02x}"
                self.create_line(i, 0, i, height, fill=color, width=1)
            
            # Clip the progress to the rounded rectangle shape
            # Create a polygon to cover areas outside the rounded corners
            if progress_width > self.corner_radius:
                # Cover the left side
                self.create_rectangle(
                    0, self.corner_radius,
                    self.corner_radius, height - self.corner_radius,
                    fill=self.color1, outline="")
                    
                # Left rounded corners need to be filled with gradient color
                self.create_arc(
                    0, 0, 2*self.corner_radius, 2*self.corner_radius,
                    start=90, extent=90, fill=self.color1, outline="")
                self.create_arc(
                    0, height - 2*self.corner_radius, 2*self.corner_radius, height,
                    start=180, extent=90, fill=self.color1, outline="")
                
            # If progress extends to the right edge, fill right corners
            if progress_width > width - self.corner_radius:
                # Right edge will use the last gradient color
                right_color = color
                self.create_rectangle(
                    width - self.corner_radius, self.corner_radius,
                    width, height - self.corner_radius,
                    fill=right_color, outline="")
                    
                # Right rounded corners
                self.create_arc(
                    width - 2*self.corner_radius, 0, width, 2*self.corner_radius,
                    start=0, extent=90, fill=right_color, outline="")
                self.create_arc(
                    width - 2*self.corner_radius, height - 2*self.corner_radius, width, height,
                    start=270, extent=90, fill=right_color, outline="")
                
    def set(self, value):
        if 0 <= value <= 100:
            self.progress_value = value
            self._draw_progress()
            self.update_idletasks()

# 添加一个创建虚线分隔符的函数
def create_dashed_line(parent, width=660, dash_length=6, space_length=4, height=2, color="#e0e0e0"):
    """创建虚线分隔符"""
    dash_frame = tk.Frame(parent, height=height, width=width, bg="#ffffff")
    dash_frame.pack(pady=10)
    
    canvas = tk.Canvas(dash_frame, height=height, width=width, bg="#ffffff", highlightthickness=0)
    canvas.pack()
    
    # 计算需要的虚线段数量
    segments = int(width / (dash_length + space_length))
    
    # 绘制虚线
    for i in range(segments):
        x_start = i * (dash_length + space_length)
        x_end = x_start + dash_length
        canvas.create_line(x_start, height/2, x_end, height/2, fill=color, width=height)
    
    return dash_frame

class PhotoMapApp:
    def __init__(self, root):
        self.root = root
        root.title("照片地图v0.1")
        
        # 设置窗口大小
        root.geometry("700x660")
        root.resizable(False, False)
        
        # 在初始化时设置日志和状态文件路径到logs目录
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 将历史记录文件移至logs目录
        self.history_file = os.path.join(log_dir, "photo_map_history.log")
        self.status_file = None  # 将在选择目录时初始化
        
        # 创建UI元素
        self.create_ui_elements()
        
        # 默认状态
        self.directory = ""
        self.html_path = None
        self.processing_thread = None
        
        # 尝试加载历史记录
        self.load_history()

    def create_window_icon(self):
        # Could create a photo icon here if available
        pass

    def create_shadow_effect(self, widget):
        """Create a shadow effect behind a widget"""
        widget.configure(highlightbackground="#e0e0e0", highlightthickness=1)
        
    def create_ui_elements(self):
        """Create all UI elements"""
        # 主框架 - 纯白背景，无底纹
        main_frame = ttk.Frame(self.root, padding=(20, 10))
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.configure(style="Clean.TFrame")

        # 标题 - 使用更现代的字体和颜色
        title_frame = ttk.Frame(main_frame, style="Clean.TFrame")
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        title_label = tk.Label(
            title_frame, 
            text="照片地图生成工具", 
            font=("等线", 18, "bold"), 
            fg="#333333",
            bg="#ffffff"
        )
        title_label.pack(pady=(0, 5))
        
        subtitle_label = tk.Label(
            title_frame, 
            text="浏览您的照片足迹", 
            font=("等线", 11), 
            fg="#666666",
            bg="#ffffff"
        )
        subtitle_label.pack(pady=(0, 15))
        
        # 使用普通分隔线
        separator = ttk.Separator(main_frame, style="Elegant.TSeparator")
        separator.pack(fill=tk.X, pady=10)
        
        # 第一步：选择照片目录
        self.step1_frame = ttk.Frame(main_frame, style="Card.TFrame")
        self.step1_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # 标题左对齐
        step1_label = tk.Label(
            self.step1_frame, 
            text="选择照片目录", 
            font=("等线", 12, "bold"), 
            fg="#333333",
            bg="#ffffff"
        )
        step1_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self.select_button = StyledButton(
            self.step1_frame, 
            text="浏览文件夹", 
            command=self.select_directory,
            bg_color="#4facfe", 
            hover_color="#4aa3f0",
            width=160, 
            height=38
        )
        self.select_button.pack(padx=10, pady=10)
        
        # 修改：目录提示文字居中对齐
        directory_label_frame = ttk.Frame(self.step1_frame, style="Clean.TFrame")
        directory_label_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.directory_label = tk.Label(
            directory_label_frame, 
            text="未选择目录", 
            fg="#999999",
            bg="#ffffff"
        )
        self.directory_label.pack(expand=True, fill=tk.X)
        self.directory_label.configure(anchor="center")
        
        # 第一步和第二步之间的虚线分隔符
        create_dashed_line(main_frame)
        
        # 第二步：生成地图
        self.step2_frame = ttk.Frame(main_frame, style="Card.TFrame")
        self.step2_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # 标题左对齐
        step2_label = tk.Label(
            self.step2_frame, 
            text="生成地图", 
            font=("等线", 12, "bold"), 
            fg="#333333",
            bg="#ffffff"
        )
        step2_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self.start_button = StyledButton(
            self.step2_frame, 
            text="开始处理", 
            command=self.start_processing,
            bg_color="#ff416c", 
            hover_color="#f30b5c",
            width=160, 
            height=38
        )
        self.start_button.pack(padx=10, pady=10)
        
        # 进度条 - 更现代的样式
        progress_frame = ttk.Frame(self.step2_frame, style="Clean.TFrame")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress, 
            style="Colorful.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X)
        
        # 进度标签居中对齐
        progress_label_frame = ttk.Frame(progress_frame, style="Clean.TFrame")
        progress_label_frame.pack(fill=tk.X, pady=(5, 10))
        
        self.progress_label = tk.Label(
            progress_label_frame, 
            text="处理进度：0%", 
            fg="#666666",
            bg="#ffffff"
        )
        self.progress_label.pack(expand=True, fill=tk.X)
        self.progress_label.configure(anchor="center")
        
        # 第二步和第三步之间的虚线分隔符
        create_dashed_line(main_frame)
        
        # 第三步：打开地图
        self.step3_frame = ttk.Frame(main_frame, style="Card.TFrame")
        self.step3_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # 标题左对齐
        step3_label = tk.Label(
            self.step3_frame, 
            text="打开照片地图", 
            font=("等线", 12, "bold"), 
            fg="#333333",
            bg="#ffffff"
        )
        step3_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        self.open_map_button = StyledButton(
            self.step3_frame, 
            text="打开照片地图", 
            command=self.open_photo_map,
            bg_color="#4287f5", 
            hover_color="#3278e5",
            width=160, 
            height=38
        )
        self.open_map_button.pack(padx=10, pady=10)
        
        # 修改：地图状态提示文字居中对齐
        map_status_frame = ttk.Frame(self.step3_frame, style="Clean.TFrame")
        map_status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.map_status_label = tk.Label(
            map_status_frame, 
            text="未生成地图", 
            fg="#999999",
            bg="#ffffff"
        )
        self.map_status_label.pack(expand=True, fill=tk.X)
        self.map_status_label.configure(anchor="center")
        
        # 页脚和分隔线
        footer_frame = ttk.Frame(main_frame, style="Clean.TFrame")
        footer_frame.pack(fill=tk.X, pady=(15, 0))
        
        separator = ttk.Separator(footer_frame, style="Elegant.TSeparator")
        separator.pack(fill=tk.X, pady=(0, 5))
        
        version_label = tk.Label(
            footer_frame, 
            text="照片地图v0.1 by Dong & Yi", 
            font=("等线", 8), 
            fg="#999999",
            bg="#ffffff"
        )
        version_label.pack(side=tk.RIGHT, padx=5)

    def save_history(self, directory=None, html_path=None):
        """Save the current directory and map path to history file"""
        if not (directory or html_path):
            return
            
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            history_entries = []
            
            # Read existing entries if file exists
            if os.path.exists(self.history_file):
                try:
                    with open(self.history_file, "r", encoding="utf-8") as f:
                        history_entries = [json.loads(line) for line in f if line.strip()]
                except Exception as e:
                    logging.error(f"读取历史记录时出错: {str(e)}")
            
            # Create new entry
            entry = {"timestamp": timestamp}
            if directory:
                entry["directory"] = directory
            if html_path:
                entry["html_path"] = html_path
                
            # Add to entries list
            history_entries.append(entry)
            
            # Keep only the latest 20 entries
            if len(history_entries) > 20:
                history_entries = history_entries[-20:]
                
            # Write back to file
            with open(self.history_file, "w", encoding="utf-8") as f:
                for entry in history_entries:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                
            logging.info("已保存历史记录")
        except Exception as e:
            logging.error(f"保存历史记录时出错: {str(e)}")
            
    def load_history(self):
        """Load history and update UI with the most recent entry"""
        if not os.path.exists(self.history_file):
            logging.info("未找到历史记录文件")
            return
            
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history_entries = [json.loads(line) for line in f if line.strip()]
                
            if not history_entries:
                logging.info("历史记录为空")
                return
                
            # Get the most recent entry
            latest_entry = history_entries[-1]
            
            # Update directory if available
            if "directory" in latest_entry:
                self.directory = latest_entry["directory"]
                # Show directory path, truncated if too long
                directory_display = self.directory
                if len(directory_display) > 40:
                    directory_display = "..." + directory_display[-40:]
                self.directory_label.config(text=directory_display, fg="#4facfe")
                
                # Create status file path
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                self.status_file = os.path.join(self.directory, f"photomap_status_{timestamp}.txt")
                
                logging.info(f"从历史记录加载目录: {self.directory}")
                
            # Update HTML path if available
            if "html_path" in latest_entry:
                html_path = latest_entry["html_path"]
                if os.path.exists(html_path):
                    self.html_path = html_path
                    self.map_status_label.config(text=f"地图已存在: {os.path.basename(html_path)}", fg="#1a73e8")
                    logging.info(f"从历史记录加载地图: {html_path}")
                    
            # Always check for existing maps if directory is set
            if self.directory:
                self.check_existing_map()
                
        except Exception as e:
            logging.error(f"加载历史记录时出错: {str(e)}")
        
    def select_directory(self):
        self.directory = filedialog.askdirectory()
        if self.directory:
            # 将状态文件保存到logs目录
            log_dir = "logs"
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            self.status_file = os.path.join(log_dir, f"photomap_status_{timestamp}.txt")
            
            # Show directory path, truncated if too long
            directory_display = self.directory
            if len(directory_display) > 40:
                directory_display = "..." + directory_display[-40:]
            self.directory_label.config(text=directory_display, fg="#4facfe")
            
            # Log the selected directory
            logging.info(f"选择目录: {self.directory}")
            self.write_status(f"选择目录: {self.directory}")
            
            # Save to history
            self.save_history(directory=self.directory)
            
            # Check if there's already a generated map
            self.check_existing_map()

    def check_existing_map(self):
        """Check if a map already exists in the selected directory"""
        if not self.directory and self.html_path and os.path.exists(self.html_path):
            # We have a valid map file but no directory selected yet
            self.map_status_label.config(text=f"地图已存在: {os.path.basename(self.html_path)}", fg="#1a73e8")
            return
            
        if not self.directory:
            return
            
        # Look for HTML files that might be photo maps
        potential_maps = []
        map_path = os.path.join(self.directory, "photo_map.html")
        
        if os.path.exists(map_path):
            # Found existing map
            self.html_path = map_path
            self.map_status_label.config(text=f"地图已存在: {os.path.basename(map_path)}", fg="#1a73e8")
            self.write_status("找到现有地图文件")
            logging.info(f"找到现有地图文件: {map_path}")
            
            # Save to history
            self.save_history(html_path=map_path)
            return
            
        # Check if there are other HTML files that might be maps
        for file in os.listdir(self.directory):
            if file.endswith(".html") and "map" in file.lower():
                potential_maps.append(os.path.join(self.directory, file))
                
        if potential_maps:
            # Use the most recent HTML file
            latest_map = max(potential_maps, key=os.path.getmtime)
            self.html_path = latest_map
            self.map_status_label.config(text=f"地图已存在: {os.path.basename(latest_map)}", fg="#1a73e8")
            self.write_status("找到现有地图文件")
            logging.info(f"找到现有地图文件: {latest_map}")
            
            # Save to history
            self.save_history(html_path=latest_map)
        else:
            self.map_status_label.config(text="未生成地图", fg="#6c757d")
            logging.info("未找到现有地图文件")

    def write_status(self, status_message):
        """Write status message to the status file"""
        if not self.status_file:
            return
            
        try:
            with open(self.status_file, "a", encoding="utf-8") as f:
                timestamp = logging.Formatter("%(asctime)s").format(logging.LogRecord("", 0, "", 0, "", None, None))
                f.write(f"{timestamp} - {status_message}\n")
            
            # Also log to the application log file
            logging.info(status_message)
        except Exception as e:
            logging.error(f"写入状态文件失败: {str(e)}")

    def start_processing(self):
        if not self.directory:
            messagebox.showerror("错误", "请先选择照片目录")
            return

        temp_dir = os.path.join(self.directory, TEMP_DIR_NAME)
        os.makedirs(temp_dir, exist_ok=True)

        # We still want to visually disable buttons during processing
        # but only for functionality, not appearance
        self.select_button.bind("<ButtonPress-1>", lambda e: None)
        self.select_button.bind("<ButtonRelease-1>", lambda e: None)
        self.start_button.bind("<ButtonPress-1>", lambda e: None)
        self.start_button.bind("<ButtonRelease-1>", lambda e: None)
        self.open_map_button.bind("<ButtonPress-1>", lambda e: None)
        self.open_map_button.bind("<ButtonRelease-1>", lambda e: None)
        
        self.progress.set(0)
        self.progress_label.config(text="处理进度：0%")
        self.map_status_label.config(text="正在生成地图...", fg="#ff416c")
        
        # Log the start of processing
        self.write_status("开始处理照片")

        # Create a separate thread for processing to prevent UI freezing
        self.processing_thread = ThreadPoolExecutor(max_workers=1)
        self.processing_thread.submit(self.process_photos_thread)

    def process_photos_thread(self):
        try:
            photo_list = scan_photos(self.directory, SUPPORTED_FORMATS, TEMP_DIR_NAME)
            if not photo_list:
                self.write_status("未找到支持的图片文件")
                self.root.after(0, lambda: messagebox.showerror("错误", "未找到支持的图片文件"))
                self.root.after(0, lambda: self.map_status_label.config(text="未生成地图", fg="#888888"))
                self.root.after(0, lambda: self.reset_ui_state())
                return

            photo_data = []
            total = len(photo_list)
            self.write_status(f"找到 {total} 张照片，开始处理")
            logging.info(f"找到 {total} 张照片，开始处理")

            with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
                futures = [
                    executor.submit(
                        self.safe_process_photo,
                        photo_path,
                        os.path.join(self.directory, TEMP_DIR_NAME),
                        self.directory,
                    )
                    for photo_path in photo_list
                ]

                for i, future in enumerate(futures):
                    try:
                        result = future.result()
                        if result:
                            photo_data.append(result)
                            logging.info(f"处理成功: {result['photo_path']}")
                    except Exception as e:
                        logging.error(f"处理失败: {str(e)}")
                    finally:
                        progress_value = (i + 1) / total * 100
                        # Use after method to update UI from background thread
                        self.root.after(0, lambda v=progress_value: self.update_progress(v))
                        # Process pending events to keep UI responsive
                        self.root.update_idletasks()

            if not photo_data:
                self.write_status("未找到包含位置信息的图片")
                self.root.after(0, lambda: messagebox.showerror("错误", "未找到包含位置信息的图片"))
                self.root.after(0, lambda: self.map_status_label.config(text="未生成地图", fg="#888888"))
                self.root.after(0, lambda: self.reset_ui_state())
                return

            self.write_status(f"成功处理 {len(photo_data)} 张带有位置信息的照片")
            logging.info(f"成功处理 {len(photo_data)} 张带有位置信息的照片")
            html_path = generate_map_html(photo_data, self.directory)
            if not html_path:
                self.write_status("地图生成失败")
                logging.error("地图生成失败")
                self.root.after(0, lambda: messagebox.showerror("错误", "地图生成失败，请检查日志"))
                self.root.after(0, lambda: self.map_status_label.config(text="地图生成失败", fg="#ff0000"))
                self.root.after(0, lambda: self.reset_ui_state())
                return

            # 生成 readme.txt 到logs目录
            log_dir = "logs"
            readme_content = """
照片地图v0.1 使用说明
=====================

欢迎使用照片地图v0.1！这款工具可以帮您把带有位置信息的照片展示在地图上，简单易用，功能强大。

### 主要特点
- **一键扫描所有照片**：只需选择一个父文件夹，软件会自动遍历所有子文件夹中的照片。
- **快速处理**：采用多线程技术，大幅提升照片处理速度。
- **流畅展示**：可在前端展示海量照片，流畅不卡顿。
- **随时查看**：生成HTML文件，随时打开即可重新查看。
- **本地化处理**：所有操作均在本地完成，无需联网。

### 使用步骤
1. 点击"浏览文件夹"按钮，选择照片所在的目录。
2. 点击"开始处理"按钮，开始处理并生成地图。
3. 处理完成后，点击"打开照片地图"按钮查看地图。

### 注意事项
- 照片必须包含位置信息（EXIF数据中的位置信息）才能在地图上展示。
- 支持的照片格式：.jpg、.jpeg、.png、.heic。
- 如有问题或建议，欢迎发送邮件至：849371874@qq.com

版权所有 © 2024 照片地图项目组
"""
            readme_path = os.path.join(log_dir, "readme.txt")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)
            logging.info(f"已生成 readme.txt: {readme_path}")

            # Save the html path and activate step 3
            self.html_path = html_path
            self.write_status(f"地图生成成功: {os.path.basename(html_path)}")
            self.root.after(0, lambda: self.progress.set(100))
            self.root.after(0, lambda: self.progress_label.config(text="处理进度：100%"))
            self.root.after(0, lambda: self.open_map_button.config(state="normal"))
            self.root.after(0, lambda: self.map_status_label.config(text=f"地图已生成: {os.path.basename(html_path)}", fg="#1a73e8"))
            self.root.after(0, lambda: self.reset_ui_state(keep_map_button_enabled=True))
            self.root.after(0, lambda: self.save_history(directory=self.directory, html_path=self.html_path))
            self.root.after(0, lambda: messagebox.showinfo("成功", "照片地图已成功生成！\n请点击\"打开照片地图\"按钮查看。"))

        except Exception as e:
            error_msg = f"处理过程中出错: {str(e)}"
            logging.error(error_msg)
            self.write_status(error_msg)
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
            self.root.after(0, lambda: self.reset_ui_state())

    def update_progress(self, value):
        """Update progress bar and label from the main thread"""
        self.progress.set(value)
        self.progress_label.config(text=f"处理进度：{int(value)}%")
        if value % 10 == 0:  # Log every 10% progress
            self.write_status(f"处理进度: {int(value)}%")
        
    def reset_ui_state(self, keep_map_button_enabled=False):
        """Reset UI state after processing"""
        # Restore button functionality
        self.select_button.bind("<ButtonPress-1>", self.select_button._on_press)
        self.select_button.bind("<ButtonRelease-1>", self.select_button._on_release)
        
        # Check if there's an existing map first
        if self.html_path and os.path.exists(self.html_path):
            self.open_map_button.bind("<ButtonPress-1>", self.open_map_button._on_press)
            self.open_map_button.bind("<ButtonRelease-1>", self.open_map_button._on_release)
            self.map_status_label.config(text=f"地图已存在: {os.path.basename(self.html_path)}", fg="#1a73e8")
        elif keep_map_button_enabled:
            self.open_map_button.bind("<ButtonPress-1>", self.open_map_button._on_press)
            self.open_map_button.bind("<ButtonRelease-1>", self.open_map_button._on_release)
        else:
            # Check if there's any existing map in the directory
            self.check_existing_map()

    def open_photo_map(self):
        """Open the generated map in a web browser"""
        if not self.html_path:
            messagebox.showerror("错误", "地图文件不存在，请先生成地图。")
            return
            
        if os.path.exists(self.html_path):
            self.write_status(f"打开地图: {os.path.basename(self.html_path)}")
            logging.info(f"打开地图: {self.html_path}")
            webbrowser.open(self.html_path)
        else:
            self.write_status("尝试打开地图失败: 文件不存在")
            logging.error("尝试打开地图失败: 文件不存在")
            
            # Recheck for existing maps in case the file was moved
            self.check_existing_map()
            
            if self.html_path and os.path.exists(self.html_path):
                # Found an alternative map, open it
                self.write_status(f"找到替代地图: {os.path.basename(self.html_path)}")
                logging.info(f"找到替代地图: {self.html_path}")
                webbrowser.open(self.html_path)
            else:
                messagebox.showerror("错误", "地图文件不存在，请先生成地图。")

    def safe_process_photo(self, photo_path, temp_dir, base_dir):
        try:
            return process_photo(
                photo_path,
                temp_dir,
                base_dir,
                thumbnail_size=THUMBNAIL_SIZE,
            )
        except Exception as e:
            logging.error(f"处理 {photo_path} 时出错: {str(e)}")
            return None

if __name__ == "__main__":
    # Create a log directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Use timestamp in log filename for uniqueness
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = os.path.join(log_dir, f"photo_map_{timestamp}.log")
    
    # Update logging configuration - ensure to remove any handlers first
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
    
    logging.info("应用程序启动")
    
    root = tk.Tk()
    # Set system appearance for ttk widgets
    style = ttk.Style()
    style.theme_use('clam')  # Using clam theme as base
    
    # Configure ttk styles
    style.configure("TButton", font=("等线", 10))
    style.configure("TLabel", font=("等线", 10))
    style.configure("TEntry", font=("等线", 10))
    style.configure("Horizontal.TProgressbar", 
                    troughcolor="#f5f5f5", 
                    background="#4facfe",
                    thickness=8)
                    
    # Configure more modern styles
    style.configure("TFrame", background="#ffffff")
    style.configure("TLabel", background="#ffffff", font=("等线", 10))
    
    # Set window background color
    root.configure(background="#ffffff")
    
    app = PhotoMapApp(root)
    root.mainloop()