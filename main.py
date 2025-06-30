import tkinter as tk
from tkinter import filedialog
import pyautogui
import threading
import keyboard
import os
import time


class NovelReader:
    def __init__(self, master):
        self.master = master
        self.master.title("小说阅读器")
        self.master.overrideredirect(True)
        self.master.geometry("800x150")
        self.master.attributes("-topmost", True)
        self.master.attributes("-alpha", 0.95)

        # 字体设置
        self.font_name = "微软雅黑"
        self.font_size = 14

        # 创建文本区域
        self.text_area = tk.Text(
            master,
            font=(self.font_name, self.font_size),
            wrap="word",
            relief="flat",
            borderwidth=0,
            height=10,
            bg="#28262A",
            fg="#bbbbbb",
            insertbackground="#bbbbbb",
            highlightthickness=0
        )
        self.text_area.pack(expand=True, fill="both")
        self.text_area.config(state="disabled")

        # 事件绑定
        self.text_area.bind("<MouseWheel>", self.on_mouse_wheel)
        self.text_area.bind("<Button-4>", self.on_mouse_wheel)  # Linux 向上滚动
        self.text_area.bind("<Button-5>", self.on_mouse_wheel)  # Linux 向下滚动

        self.text_area.bind("<FocusIn>", lambda e: self.master.focus())
        self.text_area.bind("<ButtonPress-1>", self.start_move)
        self.text_area.bind("<B1-Motion>", self.do_move)

        # 仅保留上下键和功能键
        self.master.bind("<Escape>", lambda e: self.master.quit())
        self.master.bind("<c>", self.pick_color_at_cursor)
        self.master.bind("<f>", self.open_file_dialog)
        self.master.bind("<h>", self.toggle_hide_show)
        self.master.bind("<Up>", self.scroll_up)  # 向上滚动
        self.master.bind("<Down>", self.scroll_down)  # 向下滚动

        # 调整窗口大小的部件
        self.resizer = tk.Frame(self.master, cursor="bottom_right_corner", bg=self.text_area["bg"], width=10, height=10)
        self.resizer.place(relx=1.0, rely=1.0, anchor="se")
        self.resizer.bind("<ButtonPress-1>", self.start_resize)
        self.resizer.bind("<B1-Motion>", self.do_resize)

        # 使用计时器避免频繁重绘导致的递归错误
        self.last_resize_time = 0
        self.resize_timer = None

        # 初始化内容
        self.lines = []
        self.current_line = 0  # 当前阅读位置（逻辑行）
        self.line_height = self.font_size + 6  # 初始行高估算
        self.line_count = 1  # 单行显示

        # 加载初始内容
        self.load_novel("novel1.txt") if os.path.exists("novel1.txt") else self.load_dummy()
        self.update_background_color((40, 38, 42))

        # 全局热键监听
        threading.Thread(target=self.global_hotkey_listener, daemon=True).start()

    def load_dummy(self):
        """加载默认提示内容（合并为一个段落）"""
        # 将所有提示信息合并为一个文本块
        self.lines = ["\n".join([
            "[提示] 按 F 键选择小说文件",
            "[提示] 按 H 键隐藏/显示窗口",
            "[提示] 按 C 键设置背景颜色",
            "[提示] ↑ 键向上滚动，↓ 键向下滚动",
            "[提示] 按 Ctrl+Shift+` 键召唤界面",
            "[提示] ESC 退出程序",
        ])]
        self.current_line = 0
        self.show_content()

    def start_move(self, event):
        """开始移动窗口"""
        self._x = event.x
        self._y = event.y

    def do_move(self, event):
        """移动窗口"""
        x = event.x_root - self._x
        y = event.y_root - self._y
        self.master.geometry(f"+{x}+{y}")

    def start_resize(self, event):
        """开始调整窗口大小"""
        self._init_width = self.master.winfo_width()
        self._init_height = self.master.winfo_height()
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root

    def do_resize(self, event):
        """调整窗口大小 - 防抖动防递归"""
        current_time = time.time()
        if current_time - self.last_resize_time < 0.1:  # 避免频繁更新
            if self.resize_timer:
                self.master.after_cancel(self.resize_timer)
            self.resize_timer = self.master.after(100, lambda: self.complete_resize(event))
            return

        self.last_resize_time = current_time

        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        new_width = max(100, self._init_width + dx)  # 最小宽度100px

        # 最小高度可低至一行
        new_height = max(30, self._init_height + dy)  # 最小高度30px
        self.master.geometry(f"{int(new_width)}x{int(new_height)}")

        # 延迟更新内容显示
        if self.resize_timer:
            self.master.after_cancel(self.resize_timer)
        self.resize_timer = self.master.after(200, self.update_after_resize)

    def complete_resize(self, event):
        """完成调整窗口大小"""
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        new_width = max(100, self._init_width + dx)  # 最小宽度100px
        new_height = max(30, self._init_height + dy)  # 最小高度30px
        self.master.geometry(f"{int(new_width)}x{int(new_height)}")
        self.update_after_resize()

    def update_after_resize(self):
        """调整大小后更新显示"""
        # 计算可显示行数
        text_height = self.text_area.winfo_height()
        if text_height > 0 and self.line_height > 0:
            self.line_count = max(1, text_height // self.line_height)

        self.show_content()

    def load_novel(self, filepath):
        """加载小说文件"""
        try:
            with open(filepath, "rb") as f:
                raw_data = f.read()
            try:
                text = raw_data.decode('gbk')
            except UnicodeDecodeError:
                try:
                    text = raw_data.decode('utf-8')
                except UnicodeDecodeError:
                    text = raw_data.decode('utf-8', errors='ignore')

            # 将整个小说作为单一文本块处理
            self.lines = [text]
        except Exception as e:
            self.lines = [f"[错误] 读取文件失败: {e}"]

        self.current_line = 0
        self.show_content()

    def show_content(self):
        """显示当前内容（安全方法，避免递归）"""
        if not self.lines or not hasattr(self, 'text_area'):
            return

        try:
            self.text_area.config(state="normal")
            self.text_area.delete("1.0", tk.END)

            # 只显示当前整个文本块（可能包含多行）
            if self.lines:
                self.text_area.insert(tk.END, self.lines[0])

            self.text_area.config(state="disabled")
            self.text_area.yview_moveto(0.0)
        except Exception as e:
            print(f"显示内容错误: {e}")

    def scroll_up(self, event=None):
        """向上滚动一行"""
        # 使用tkinter内置滚动更可靠
        self.text_area.yview_scroll(-1, "units")

    def scroll_down(self, event=None):
        """向下滚动一行"""
        self.text_area.yview_scroll(1, "units")

    def on_mouse_wheel(self, event):
        """鼠标滚轮滚动"""
        if event.num == 5 or event.delta < 0:
            # 向下滚动
            self.scroll_down()
        elif event.num == 4 or event.delta > 0:
            # 向上滚动
            self.scroll_up()
        return "break"

    def rgb_to_hex(self, rgb):
        """RGB转十六进制"""
        return '#%02x%02x%02x' % rgb

    def get_subtle_contrast_color(self, rgb):
        """获取适当的对比色"""
        r, g, b = rgb

        def clamp(x):
            return max(0, min(255, x))

        brighter = (clamp(r + 30), clamp(g + 30), clamp(b + 30))
        darker = (clamp(r - 30), clamp(g - 30), clamp(b - 30))

        def brightness(c):
            return (c[0] * 299 + c[1] * 587 + c[2] * 114) / 1000

        bg_bright = brightness(rgb)
        bright_diff = abs(brightness(brighter) - bg_bright)
        dark_diff = abs(brightness(darker) - bg_bright)

        if bright_diff >= dark_diff and bright_diff >= 15:
            return brighter
        elif dark_diff >= 15:
            return darker
        else:
            return (r ^ 15, g ^ 15, b ^ 15)

    def update_background_color(self, rgb):
        """更新背景颜色"""
        bg_hex = self.rgb_to_hex(rgb)
        fg_rgb = self.get_subtle_contrast_color(rgb)
        fg_hex = self.rgb_to_hex(fg_rgb)

        self.master.configure(bg=bg_hex)
        self.text_area.config(bg=bg_hex, fg=fg_hex, insertbackground=fg_hex)
        self.resizer.config(bg=bg_hex)

    def pick_color_at_cursor(self, event=None):
        """选取光标处的颜色作为背景色"""
        x, y = pyautogui.position()
        img = pyautogui.screenshot(region=(x, y, 1, 1))
        color = img.getpixel((0, 0))
        self.update_background_color(color)

        # 移动窗口到鼠标位置
        w = self.master.winfo_width()
        h = self.master.winfo_height()
        self.master.geometry(f"+{x - w // 2}+{y - h // 2}")

    def open_file_dialog(self, event=None):
        """打开文件对话框"""
        filepath = filedialog.askopenfilename(
            title="选择小说文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filepath:
            self.load_novel(filepath)

    def toggle_hide_show(self, event=None):
        """隐藏/显示窗口"""
        current_alpha = self.master.attributes("-alpha")
        if current_alpha > 0:
            self.master.attributes("-alpha", 0)
        else:
            self.master.attributes("-alpha", 0.95)
            self.master.deiconify()
            self.master.focus_force()

    def global_hotkey_listener(self):
        """全局热键监听"""
        keyboard.add_hotkey('ctrl+shift+`', self.restore_window)
        keyboard.wait()

    def restore_window(self):
        """恢复窗口"""
        self.master.after(0, self._restore_window_ui)

    def _restore_window_ui(self):
        """在UI线程中恢复窗口"""
        self.master.attributes("-alpha", 0.95)
        self.master.deiconify()
        self.master.focus_force()
# 那比如说我在这一行加一个注释怎么办呢

if __name__ == "__main__":
    root = tk.Tk()
    app = NovelReader(root)
    root.mainloop()