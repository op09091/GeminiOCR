import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from tkinter.font import Font
import threading
import mimetypes
from pathlib import Path
from google import genai
from google.genai.types import HttpOptions, Part
import tempfile
import fitz  # PyMuPDF
from datetime import datetime
import subprocess
import platform
import json

# --- Constants ---
# 默认配置, 如果配置文件读取失败, 则使用此配置
DEFAULT_CONFIG = {
    "api_key": "YOUR_API_KEY_HERE",  # 替换为你的默认 API 密钥
    "model_name": "gemini-1.5-pro",
    "image_extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
    "pdf_extension": ".pdf",
    "default_prompt": "请提取图片上的文字返回，使用markdown以保留图片文字的格式，例如标题、加粗、居中等等",
    "gui": {
        "width": 700,
        "height": 550,
        "padding": 10,
        "bg_color": "#f0f0f0",
        "button_color": "#4a7abc",
        "button_text_color": "white",
        "success_color": "#4CAF50",
        "error_color": "#F44336",
    },
}

CONFIG_FILE = "config.json"


def load_config(config_file=CONFIG_FILE, default_config=DEFAULT_CONFIG):
    """加载配置文件, 如果文件不存在或格式错误, 则使用默认配置."""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 确保配置项完整性, 对缺失的配置项使用默认值.  避免用户修改配置文件导致程序出错
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
            elif isinstance(value, dict):  # 嵌套字典的配置
                for sub_key, sub_value in value.items():
                    if sub_key not in config[key]:
                        config[key][sub_key] = sub_value
        return config
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        print(f"加载配置文件 '{config_file}' 失败: {e}, 使用默认配置")
        return default_config


class EnhancedTextExtractor:
    def __init__(self, root, config):
        self.root = root
        self.config = config  # 使用传入的配置
        self.root.attributes('-topmost', True)
        self.root.after(200, lambda: self.root.attributes('-topmost', False))
        self.root.configure(bg=self.config["gui"]["bg_color"])

        # 初始化变量
        self.file_list = []
        self.output_dir_var = tk.StringVar()
        self.output_filename_var = tk.StringVar()
        self.prompt_var = tk.StringVar(value=self.config["default_prompt"])
        self.progress_var = tk.DoubleVar()
        self.is_processing = False

        self._initialize_api_client()
        self._setup_ui()

    def _initialize_api_client(self):
        """初始化 Gemini API 客户端"""
        try:
            self.client = genai.Client(
                api_key=self.config["api_key"],
                http_options=HttpOptions(api_version="v1")
            )
        except Exception as e:
            messagebox.showerror("API 初始化错误", f"无法初始化 Gemini API: {e}")
            self.root.destroy()  # 如果 API 初始化失败，直接关闭应用

    def _setup_ui(self):
        """设置用户界面"""
        self._setup_styles()
        self._center_window()
        self._create_main_frame()
        self._create_widgets()
        self._layout_widgets()

    def _setup_styles(self):
        """设置自定义样式"""
        self.title_font = Font(family="Helvetica", size=12, weight="bold")
        button_style = {
            "bg": self.config["gui"]["button_color"],
            "fg": self.config["gui"]["button_text_color"],
            "relief": tk.RAISED,
            "padx": 10,
            "pady": 5,
            "borderwidth": 2,
            "font": ("Helvetica", 10)
        }

        self.style = ttk.Style()
        self.style.configure("TFrame", background=self.config["gui"]["bg_color"])
        self.style.configure("TLabel", background=self.config["gui"]["bg_color"], font=("Helvetica", 10))
        self.style.configure("TButton", font=("Helvetica", 10))
        self.style.configure("Success.TButton", background=self.config["gui"]["success_color"])
        self.style.configure("Default.TButton", **button_style)

    def _center_window(self):
        """将窗口居中显示"""
        width, height = self.config["gui"]["width"], self.config["gui"]["height"]
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = (screen_width - width) // 2
        center_y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{center_x}+{center_y}")
        self.root.minsize(width, height)

    def _create_main_frame(self):
        """创建主框架"""
        self.main_frame = ttk.Frame(self.root, padding=self.config["gui"]["padding"])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(5, weight=1)  # 输出文本区域行

    def _create_widgets(self):
        """创建所有界面组件"""
        # 文件选择
        self.files_frame = ttk.LabelFrame(self.main_frame, text="文件选择")
        self.files_entry = ttk.Entry(self.files_frame)
        self.select_files_button = ttk.Button(
            self.files_frame, text="选择文件", command=self.select_files, style="Default.TButton")
        self.clear_files_button = ttk.Button(
            self.files_frame, text="清除选择", command=self.clear_files, style="Default.TButton")

        # 输出目录选择
        self.output_dir_frame = ttk.LabelFrame(self.main_frame, text="输出目录")
        self.output_dir_entry = ttk.Entry(self.output_dir_frame)
        self.select_output_dir_button = ttk.Button(
            self.output_dir_frame, text="选择目录", command=self.select_output_directory, style="Default.TButton")
        self.clear_output_dir_button = ttk.Button(
            self.output_dir_frame, text="清除选择", command=self.clear_output_directory, style="Default.TButton")

        # 选项设置
        self.options_frame = ttk.LabelFrame(self.main_frame, text="选项设置")
        self.output_filename_label = ttk.Label(self.options_frame, text="输出文件名:")
        self.output_filename_entry = ttk.Entry(self.options_frame, textvariable=self.output_filename_var, width=20)
        self.prompt_label = ttk.Label(self.options_frame, text="提示文本:")
        self.prompt_entry = ttk.Entry(self.options_frame, textvariable=self.prompt_var, width=40)

        # 开始提取按钮
        self.start_button = ttk.Button(
            self.main_frame, text="开始提取文字", command=self.start_extraction, style="Default.TButton")

        # 进度条
        self.progress_frame = ttk.Frame(self.main_frame)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, variable=self.progress_var, mode='determinate', length=500)
        self.progress_label = ttk.Label(self.progress_frame, text="准备就绪")

        # 输出文本区域
        self.output_frame = ttk.LabelFrame(self.main_frame, text="处理日志")
        self.output_text = scrolledtext.ScrolledText(
            self.output_frame, height=10, wrap=tk.WORD, font=("Consolas", 9))

        # 状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)

    def _layout_widgets(self):
        """排列界面组件"""
        grid_padding = {'padx': 5, 'pady': 5}
        pack_padding = {'padx': 5, 'pady': 5}

        # 文件选择框架
        self.files_frame.grid(row=1, column=0, columnspan=3, sticky="ew", **grid_padding)
        self.files_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, **pack_padding)
        self.select_files_button.pack(side=tk.LEFT, **pack_padding)
        self.clear_files_button.pack(side=tk.LEFT, **pack_padding)

        # 输出目录选择框架
        self.output_dir_frame.grid(row=2, column=0, columnspan=3, sticky="ew", **grid_padding)
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, **pack_padding)
        self.select_output_dir_button.pack(side=tk.LEFT, **pack_padding)
        self.clear_output_dir_button.pack(side=tk.LEFT, **pack_padding)

        # 选项框架
        self.options_frame.grid(row=3, column=0, columnspan=3, sticky="ew", **grid_padding)
        self.output_filename_label.grid(row=0, column=0, sticky="w", **grid_padding)
        self.output_filename_entry.grid(row=0, column=1, sticky="w", **grid_padding)
        self.prompt_label.grid(row=0, column=2, sticky="w", padx=(15, 5), pady=5)
        self.prompt_entry.grid(row=0, column=3, sticky="ew", **grid_padding)
        self.options_frame.columnconfigure(3, weight=1)

        # 开始提取按钮
        self.start_button.grid(row=4, column=0, columnspan=3, pady=15, sticky="we")

        # 进度框架
        self.progress_frame.grid(row=5, column=0, columnspan=3, sticky="ew", **grid_padding)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, **pack_padding)
        self.progress_label.pack(side=tk.LEFT, **pack_padding)

        # 输出文本区域
        self.output_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", **grid_padding)
        self.output_text.pack(fill=tk.BOTH, expand=True, **pack_padding)

        # 状态栏
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(6, weight=1)

    def _update_status(self, message, is_error=False):
        """更新状态栏信息"""
        self.status_bar.config(
            text=message,
            foreground=self.config["gui"]["error_color"] if is_error else "black"
        )

    def _update_log_text(self, message, level="INFO"):
        """更新日志文本区域"""
        colors = {
            "INFO": "black",
            "SUCCESS": self.config["gui"]["success_color"],
            "ERROR": self.config["gui"]["error_color"],
            "WARN": "orange"
        }

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}\n"

        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, formatted_message)

        # 给消息添加颜色标签
        color = colors.get(level, "black")
        self.output_text.tag_config(level, foreground=color)
        last_line_start = self.output_text.index(f"end-{len(formatted_message)}c")
        self.output_text.tag_add(level, last_line_start, tk.END)

        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def _extract_text_from_image(self, image_path):
        """使用 Gemini API 从单个图片中提取文字"""
        try:
            mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            prompt = self.prompt_var.get() or self.config["default_prompt"]
            contents = [prompt, Part.from_bytes(data=image_bytes, mime_type=mime_type)]
            response = self.client.models.generate_content(model=self.config["model_name"], contents=contents)
            return response.text
        except FileNotFoundError:
            self._update_log_text(f"文件未找到: {image_path}", "ERROR")
            return None
        except Exception as e:
            self._update_log_text(f"处理图片时出错: {e}", "ERROR")
            return None

    def _process_pdf(self, pdf_path, output_file):
        """使用 PyMuPDF 处理 PDF，提取每页文字并立即写入"""
        try:
            self._update_log_text(f"处理PDF文件: {os.path.basename(pdf_path)}")
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count

            for page_num in range(total_pages):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                temp_image_path = os.path.join(tempfile.gettempdir(), f"temp_pdf_page_{page_num}.png")
                pix.save(temp_image_path)

                text = self._extract_text_from_image(temp_image_path)
                if text:
                    output_file.write(f"{text}\n")
                    output_file.flush()
                    self._update_log_text(f"提取了页面 {page_num + 1} 的文字", "SUCCESS")
                else:
                    self._update_log_text(f"无法提取页面 {page_num + 1} 的文字", "WARN")

                # 删除临时文件
                try:
                    os.remove(temp_image_path)
                except OSError:
                    pass

                # 更新进度
                progress_percent = (page_num + 1) / total_pages * 100
                self.progress_var.set(progress_percent)
                self.progress_label.config(text=f"处理进度: {page_num + 1}/{total_pages} ({progress_percent:.1f}%)")

            doc.close()
        except Exception as e:
            self._update_log_text(f"处理PDF时出错: {e}", "ERROR")

    def _is_image_file(self, filename):
        """检查文件是否为图片"""
        return filename.lower().endswith(tuple(self.config["image_extensions"]))

    def _is_pdf_file(self, filename):
        """检查文件是否为PDF"""
        return filename.lower().endswith(self.config["pdf_extension"])

    def _process_files(self, file_list, output_file_path):
        """处理文件列表，为每个文件分别处理"""
        self.is_processing = True
        self.progress_var.set(0)
        total_files = len(file_list)
        files_processed = 0

        try:
            if not file_list:
                self._update_log_text("没有选择文件。", "WARN")
                return

            with open(output_file_path, "w", encoding="utf-8") as outfile:
                for file_path in file_list:
                    files_processed += 1
                    progress_percent_file = (files_processed / total_files) * 100

                    if self._is_pdf_file(file_path):
                        self._process_pdf(file_path, outfile)
                    elif self._is_image_file(file_path):
                        self._update_log_text(f"开始处理: {os.path.basename(file_path)}")
                        text = self._extract_text_from_image(file_path)
                        if text:
                            outfile.write(text + "\n\n---\n\n")  # 图片之间添加分隔符
                            outfile.flush()
                            self._update_log_text(f"成功提取 {os.path.basename(file_path)} 的文字", "SUCCESS")
                        else:
                            self._update_log_text(f"未能从 {os.path.basename(file_path)} 提取文字", "WARN")
                    else:
                        self._update_log_text(f"跳过不支持的文件类型: {os.path.basename(file_path)}", "WARN")

                    self.progress_var.set(progress_percent_file)
                    self.progress_label.config(
                        text=f"文件处理进度: {files_processed}/{total_files} ({progress_percent_file:.1f}%)"
                    )

            self._update_status("文字提取完成")
            self._update_log_text(f"文字提取完成。输出文件: {output_file_path}", "SUCCESS")
            messagebox.showinfo("处理完成", f"文字提取完成！\n\n输出文件: {output_file_path}")

        except Exception as e:
            self._update_log_text(f"处理过程中发生错误: {str(e)}", "ERROR")
            messagebox.showerror("错误", str(e))
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))

    def _open_output_folder(self, folder_path):
        """在文件管理器中打开输出文件夹"""
        try:
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", folder_path])
            else:  # Linux
                subprocess.Popen(["xdg-open", folder_path])
        except Exception as e:
            self._update_log_text(f"无法打开输出文件夹: {e}", "WARN")

    def select_files(self):
        """打开文件对话框选择多个文件（图片和 PDF）"""

        # 使用配置文件中的扩展名
        image_ext_str = ";*".join(self.config["image_extensions"])
        pdf_ext_str = self.config["pdf_extension"]
        filetypes = (
            ("支持的文件", f"*{image_ext_str};*{pdf_ext_str}"),
            ("所有文件", "*.*")
        )

        filenames = filedialog.askopenfilenames(title='选择文件', filetypes=filetypes)

        if filenames:
            self.file_list = list(filenames)
            self._update_files_entry()

            # 计算文件类型统计
            image_count = sum(1 for f in self.file_list if self._is_image_file(f))
            pdf_count = sum(1 for f in self.file_list if self._is_pdf_file(f))
            status_message = f"已选择 {len(self.file_list)} 个文件（{image_count} 个图片，{pdf_count} 个PDF）"
            self._update_status(status_message)
            self._update_log_text(status_message)

            # 设置默认输出文件名和目录
            if self.file_list:
                first_file_path = Path(self.file_list[0])
                self.output_filename_var.set(f"{first_file_path.stem}.txt")

                # 修改此处：总是更新输出目录为当前选择的文件所在目录
                self.output_dir_var.set(str(first_file_path.parent))
                self._update_output_dir_entry()
                self._update_log_text(f"已自动更新输出目录为: {first_file_path.parent}")

    def clear_files(self):
        """清除已选择的文件"""
        self.file_list = []
        self._update_files_entry()
        self._update_status("已清除文件选择")
        self._update_log_text("已清除文件选择")

    def _update_files_entry(self):
        """更新文件输入框显示"""
        self.files_entry.delete(0, tk.END)
        if not self.file_list:
            return

        display_text = ""
        if self.file_list:
            display_text = os.path.normpath(self.file_list[0]) if len(
                self.file_list) == 1 else f"{os.path.normpath(self.file_list[0])} 等 {len(self.file_list)} 个文件"
        self.files_entry.insert(0, display_text)

    def select_output_directory(self):
        """打开对话框选择输出目录"""
        directory = filedialog.askdirectory(title='选择输出目录')
        if directory:
            self.output_dir_var.set(directory)
            self._update_output_dir_entry()
            status_message = f"已选择输出目录: {directory}"
            self._update_status(status_message)
            self._update_log_text(status_message)

    def clear_output_directory(self):
        """清除输出目录选择"""
        self.output_dir_var.set("")
        self._update_output_dir_entry()
        self._update_status("已清除输出目录选择")
        self._update_log_text("已清除输出目录选择")

    def _update_output_dir_entry(self):
        """更新输出目录输入框显示"""
        self.output_dir_entry.delete(0, tk.END)
        self.output_dir_entry.insert(0, os.path.normpath(self.output_dir_var.get()))

    def start_extraction(self):
        """在单独的线程中开始处理"""
        if self.is_processing:
            return

        output_dir = self.output_dir_var.get()
        output_filename = self.output_filename_var.get() or "output.txt"

        # 检查必要条件
        if not output_dir:
            messagebox.showerror("错误", "请选择输出目录！")
            return
        if not self.file_list:
            messagebox.showerror("错误", "请选择文件！")
            return

        # 构建完整输出路径
        output_file_path = os.path.join(output_dir, output_filename)

        # 检查文件是否已存在
        if os.path.exists(output_file_path):
            if not messagebox.askyesno("文件已存在", f"文件 {output_filename} 已存在。\n是否覆盖？"):
                return

        # 禁用开始按钮并清空日志
        self.start_button.config(state=tk.DISABLED)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)

        # 重置进度条
        self.progress_var.set(0)
        self.progress_label.config(text="准备处理...")

        # 创建并启动处理线程
        extraction_thread = threading.Thread(
            target=self._process_files,
            args=(self.file_list, output_file_path),
            daemon=True
        )
        extraction_thread.start()

    def run(self):
        """运行应用程序的主循环"""
        self.root.mainloop()


def main():
    """主函数"""
    mimetypes.init()
    config = load_config()  # 加载配置
    root = tk.Tk()
    root.title("GeminiOCR")
    app = EnhancedTextExtractor(root, config)  # 传入配置
    app.run()


if __name__ == "__main__":
    main()