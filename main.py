import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext
import time
import requests
import tempfile
import json
# Членососники
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# Определяем текущую директорию скрипта
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Текущая версия программы
CURRENT_VERSION = "1.0.0"
# Абсолютные пути для файлов конфигурации и версии
LOCAL_VERSION_FILE = os.path.join(CURRENT_DIR, "version.txt")
CONFIG_FILE = os.path.join(CURRENT_DIR, "bot_config.txt")

# --- Обновление через GitHub ---
# URL для получения последнего релиза через GitHub API.
# Замените username и repository на свои данные.
GITHUB_LATEST_RELEASE_URL = "https://raw.githubusercontent.com/LeonidTape/discord_controller/refs/heads/main/releases.json"

# Имя файла с новой версией, как оно указано в релизе (например, new_version.exe)
NEW_EXE_NAME = "new_version.exe"


def get_local_version():
    if not os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(CURRENT_VERSION)
        return CURRENT_VERSION
    else:
        with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
            file_version = f.read().strip()
        if file_version != CURRENT_VERSION:
            with open(LOCAL_VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(CURRENT_VERSION)
            return CURRENT_VERSION
        return file_version

def load_bot_path():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            path = f.read().strip()
            if path:
                if not os.path.isabs(path):
                    path = os.path.join(CURRENT_DIR, path)
                return path
    return os.path.join(CURRENT_DIR, "index.py")

def save_bot_path(path):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(path)

class CustomScrolledTextbox(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master)
        self.textbox = scrolledtext.ScrolledText(self, **kwargs)
        self.textbox.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.textbox.config(state="disabled")

    def insert(self, index, text):
        self.textbox.config(state="normal")
        self.textbox.insert(index, text)
        self.textbox.see("end")
        self.textbox.config(state="disabled")
        
    def clear(self):
        self.textbox.config(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.config(state="disabled")

class BotController:
    def __init__(self, text_widget, bot_path, on_ready_callback=None, update_progress_callback=None):
        self.process = None
        self.text_widget = text_widget
        self.bot_path = bot_path
        self.on_ready_callback = on_ready_callback
        self.update_progress_callback = update_progress_callback
        self.progress_finished = False
        self.last_message_time = time.time()
        self.error_occurred = False

    def update_bot_path(self, new_path):
        self.bot_path = new_path

    def start_bot(self):
        self.progress_finished = False
        self.last_message_time = time.time()
        self.error_occurred = False
        if self.process is None or self.process.poll() is not None:
            try:
                # Запускаем бота через sys.executable и создаём новую консоль
                self.process = subprocess.Popen(
                    [sys.executable, '-u', self.bot_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=os.path.dirname(os.path.abspath(self.bot_path)),
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                threading.Thread(target=self.read_output, daemon=True).start()
                self.write_to_console("Бот запущен...\n")
            except Exception as e:
                self.write_to_console(f"Не удалось запустить бота: {e}\n")
        else:
            self.write_to_console("Бот уже запущен.\n")

    def stop_bot(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.write_to_console("Бот остановлен.\n")

    def read_output(self):
        for line in self.process.stdout:
            self.write_to_console(line)
        self.process.stdout.close()

    def write_to_console(self, text):
        def inner():
            self.text_widget.insert("end", text)
            self.last_message_time = time.time()
            if "error" in text.lower() or "exception" in text.lower():
                self.error_occurred = True
            if self.update_progress_callback:
                self.update_progress_callback()
        self.text_widget.after(0, inner)

def main():
    # Устанавливаем рабочую директорию в каталог скрипта
    os.chdir(CURRENT_DIR)
    bot_path = load_bot_path()

    root = ttk.Window(themename="darkly")
    root.title("Discord Controller")
    root.geometry("900x800")
    root.minsize(900, 800)

    main_frame = ttk.Frame(root, padding=15)
    main_frame.grid(row=0, column=0, sticky="nsew")
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    # Верхнее меню
    top_frame = ttk.Frame(main_frame)
    top_frame.grid(row=0, column=0, sticky="w", padx=5, pady=(0, 0))

    def choose_bot_path():
        file_path = filedialog.askopenfilename(
            title="Выберите файл бота", 
            filetypes=[("Файлы Python", "*.py")]
        )
        if file_path:
            file_path = os.path.abspath(file_path)
            controller.update_bot_path(file_path)
            save_bot_path(file_path)
            controller.write_to_console(f"Выбран новый путь: {file_path}\n")
            nonlocal last_mod_time
            try:
                last_mod_time = os.path.getmtime(file_path)
            except Exception as e:
                controller.write_to_console(f"Ошибка получения времени модификации файла: {e}\n")

    dropdown_button = ttk.Menubutton(top_frame, text="Меню", bootstyle="secondary")
    dropdown_menu = tk.Menu(dropdown_button, tearoff=0)
    dropdown_menu.add_command(label="Выберите файл бота", command=choose_bot_path)
    dropdown_button["menu"] = dropdown_menu
    dropdown_button.pack(side="left", padx=5, pady=0)

    progress_bar = ttk.Progressbar(top_frame, mode="determinate", bootstyle="info", maximum=100)
    progress_bar.pack_forget()

    # Центральная панель – консоль
    console_frame = CustomScrolledTextbox(
        main_frame,
        font=("Consolas", 11),
        background="#171717",
        foreground="#ffffff",
        wrap="none"
    )
    console_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    main_frame.rowconfigure(1, weight=1)
    main_frame.columnconfigure(0, weight=1)

    # Нижняя панель – переключатели и кнопка перезапуска
    bottom_frame = ttk.Frame(main_frame)
    bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 5))
    bottom_frame.columnconfigure(0, weight=1)
    bottom_frame.columnconfigure(1, weight=1)

    THRESHOLD_LINES = 50

    def update_progress():
        content = console_frame.textbox.get("1.0", "end-1c")
        line_count = len(content.splitlines())
        progress = min((line_count / THRESHOLD_LINES) * 100, 100)
        progress_bar['value'] = progress
        if progress >= 100:
            root.after(500, lambda: progress_bar.pack_forget())
        root.after(500, periodic_check)

    def finish_progress_bar_with_status():
        if progress_bar.winfo_ismapped():
            progress_bar['value'] = 100
            progress_bar.config(bootstyle="danger" if controller.error_occurred else "success")
            def reset_bar():
                progress_bar.stop()
                progress_bar.pack_forget()
                progress_bar.config(bootstyle="info")
                progress_bar['value'] = 0
                controller.error_occurred = False
            root.after(1000, reset_bar)
            controller.progress_finished = True

    def start_progress_bar():
        progress_bar['value'] = 0
        progress_bar.config(bootstyle="info")
        progress_bar.pack(side="left", padx=(5, 0), pady=0)

    def periodic_check():
        if progress_bar.winfo_ismapped() and not controller.progress_finished:
            if time.time() - controller.last_message_time >= 2:
                finish_progress_bar_with_status()
        root.after(500, periodic_check)

    periodic_check()

    controller = BotController(console_frame, bot_path,
                                 on_ready_callback=None,
                                 update_progress_callback=update_progress)

    # Функция проверки обновлений через GitHub API
    def check_for_updates():
        try:
            response = requests.get(GITHUB_LATEST_RELEASE_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                remote_version = data.get("tag_name", CURRENT_VERSION)
                local_version = get_local_version()
                if remote_version != local_version:
                    controller.write_to_console(f"Найдена новая версия: {remote_version}. Обновление...\n")
                    # Поиск нужного файла в списке assets
                    assets = data.get("assets", [])
                    new_exe_url = None
                    for asset in assets:
                        if asset.get("name") == NEW_EXE_NAME:
                            new_exe_url = asset.get("browser_download_url")
                            break
                    if not new_exe_url:
                        controller.write_to_console("Новая версия не найдена среди релизов.\n")
                        return
                    new_exe_path = os.path.join(tempfile.gettempdir(), NEW_EXE_NAME)
                    with requests.get(new_exe_url, stream=True) as r:
                        r.raise_for_status()
                        with open(new_exe_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                    controller.write_to_console("Новая версия загружена.\n")
                    # Обновляем локальный файл версии
                    with open(LOCAL_VERSION_FILE, "w", encoding="utf-8") as f:
                        f.write(remote_version)
                    # Запуск нового exe и завершение текущей программы
                    subprocess.Popen([new_exe_path])
                    controller.write_to_console("Обновление завершено. Перезапуск...\n")
                    os._exit(0)
                else:
                    controller.write_to_console("Версия программы актуальна.\n")
            else:
                controller.write_to_console(f"Не удалось проверить обновления: HTTP статус {response.status_code}\n")
        except Exception as e:
            controller.write_to_console(f"Ошибка проверки обновлений: {e}\n")

    # Запуск проверки обновлений в отдельном потоке
    threading.Thread(target=check_for_updates, daemon=True).start()

    toggle_var = tk.BooleanVar(value=False)
    def toggle_callback():
        if toggle_var.get():
            console_frame.clear()
            start_progress_bar()
            controller.start_bot()
            restart_button.config(state="normal")
        else:
            controller.stop_bot()
            restart_button.config(state="disabled")
            progress_bar.pack_forget()

    toggle_switch = ttk.Checkbutton(
        bottom_frame,
        text="Запустить бота",
        variable=toggle_var,
        onvalue=True,
        offvalue=False,
        bootstyle=SUCCESS + "-square-toggle",
        command=toggle_callback
    )
    toggle_switch.grid(row=0, column=0, padx=(1, 10), pady=5, sticky="w")

    def restart_button_callback():
        restart_button.config(state="disabled")
        controller.write_to_console("Перезапуск бота...\n")
        controller.stop_bot()
        console_frame.clear()
        start_progress_bar()
        root.after(1000, lambda: (
            controller.start_bot(),
            restart_button.config(state="normal" if toggle_var.get() else "disabled")
        ))
    restart_button = ttk.Button(
        bottom_frame,
        text="Перезапустить бота",
        command=restart_button_callback,
        bootstyle="secondary"
    )
    restart_button.grid(row=0, column=1, padx=(0, 10), pady=5, sticky="e")
    restart_button.config(state="disabled")

    auto_restart_var = tk.BooleanVar(value=False)
    auto_restart_toggle = ttk.Checkbutton(
        bottom_frame,
        text="Автоперезапуск при обновлении файла",
        variable=auto_restart_var,
        bootstyle="info-square-toggle"
    )
    auto_restart_toggle.grid(row=1, column=0, columnspan=2, sticky="w", padx=(1, 10), pady=0)

    try:
        last_mod_time = os.path.getmtime(controller.bot_path)
    except Exception as e:
        last_mod_time = 0
        controller.write_to_console(f"Ошибка получения времени модификации файла: {e}\n")

    def check_file_update():
        nonlocal last_mod_time
        if auto_restart_var.get():
            try:
                new_mod_time = os.path.getmtime(controller.bot_path)
                if new_mod_time > last_mod_time:
                    last_mod_time = new_mod_time
                    controller.write_to_console("Файл обновлен, автоперезапуск бота...\n")
                    restart_button_callback()
            except Exception as e:
                controller.write_to_console(f"Ошибка проверки времени модификации файла: {e}\n")
        root.after(1000, check_file_update)

    check_file_update()

    def on_closing():
        controller.stop_bot()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
