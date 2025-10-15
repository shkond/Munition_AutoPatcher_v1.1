# =============================================================================
# Munitions 自動統合フレームワーク v2.5
#
# AutoPatcherGUI.py
# =============================================================================

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
import queue
import logging.handlers
from pathlib import Path

from admin_check import is_admin, request_admin_elevation

class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)

class Application(tk.Frame):
    def __init__(self, master, config_manager, orchestrator, log_queue):
        super().__init__(master)
        self.master = master
        self.master.title("Munitions 自動統合フレームワーク v2.5")
        self.pack(padx=10, pady=10)

        self.config_manager = config_manager
        self.orchestrator = orchestrator
        self.is_running = False
        self.log_queue = log_queue
        
        self.create_widgets()
        self.load_settings()

        self.after(100, self.poll_log_queue)

    def create_widgets(self):
        settings_frame = ttk.LabelFrame(self, text="環境設定")
        settings_frame.pack(fill="x", expand=True, pady=5)

        self.use_mo2_var = tk.BooleanVar()
        self.use_mo2_check = ttk.Checkbutton(settings_frame, text="Mod Organizer 2 を使用してxEditを起動する", variable=self.use_mo2_var, command=self.toggle_mo2_settings)
        self.use_mo2_check.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=5)

        self.mo2_settings_frame = ttk.Frame(settings_frame)
        self.mo2_settings_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=15)

        ttk.Label(self.mo2_settings_frame, text="MO2実行ファイル:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.mo2_executable_var = tk.StringVar()
        self.mo2_executable_entry = ttk.Entry(self.mo2_settings_frame, textvariable=self.mo2_executable_var, width=60)
        self.mo2_executable_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.mo2_browse_button = ttk.Button(self.mo2_settings_frame, text="参照...", command=lambda: self.browse_file(self.mo2_executable_var, "MO2実行ファイル (ModOrganizer.exe)", [("Executable files", "*.exe")]))
        self.mo2_browse_button.grid(row=0, column=2, sticky="e", padx=5, pady=2)

        ttk.Label(self.mo2_settings_frame, text="プロファイル名:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.xedit_profile_var = tk.StringVar()
        self.xedit_profile_entry = ttk.Entry(self.mo2_settings_frame, textvariable=self.xedit_profile_var, width=60)
        self.xedit_profile_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(self.mo2_settings_frame, text="実行ファイルリスト名:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.mo2_entry_name_var = tk.StringVar()
        self.mo2_entry_name_entry = ttk.Entry(self.mo2_settings_frame, textvariable=self.mo2_entry_name_var, width=60)
        self.mo2_entry_name_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(self.mo2_settings_frame, text="Overwriteフォルダ:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.mo2_overwrite_dir_var = tk.StringVar()
        self.mo2_overwrite_dir_entry = ttk.Entry(self.mo2_settings_frame, textvariable=self.mo2_overwrite_dir_var, width=60)
        self.mo2_overwrite_dir_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        self.mo2_overwrite_browse_button = ttk.Button(self.mo2_settings_frame, text="参照...", command=lambda: self.browse_directory(self.mo2_overwrite_dir_var, "MO2のOverwriteフォルダを選択"))
        self.mo2_overwrite_browse_button.grid(row=3, column=2, sticky="e", padx=5, pady=2)
        
        ttk.Label(self.mo2_settings_frame, text="ショートカット形式:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.mo2_shortcut_format_var = tk.StringVar()
        format_combo = ttk.Combobox(self.mo2_settings_frame, textvariable=self.mo2_shortcut_format_var, values=["auto", "no_colon", "with_colon", "instance"], state="readonly", width=57)
        format_combo.grid(row=4, column=1, sticky="ew", padx=5, pady=2)
        format_combo.set("auto")
        
        ttk.Label(self.mo2_settings_frame, text="インスタンス名:").grid(row=5, column=0, sticky="w", padx=5, pady=2)
        self.mo2_instance_name_var = tk.StringVar()
        self.mo2_instance_name_entry = ttk.Entry(self.mo2_settings_frame, textvariable=self.mo2_instance_name_var, width=60)
        self.mo2_instance_name_entry.grid(row=5, column=1, sticky="ew", padx=5, pady=2)
        
        self.mo2_settings_frame.columnconfigure(1, weight=1)

        ttk.Label(settings_frame, text="xEdit実行ファイル:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.xedit_executable_var = tk.StringVar()
        self.xedit_executable_entry = ttk.Entry(settings_frame, textvariable=self.xedit_executable_var, width=70)
        self.xedit_executable_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(settings_frame, text="参照...", command=lambda: self.browse_file(self.xedit_executable_var, "xEdit実行ファイル (xEdit.exe)", [("Executable files", "*.exe")])).grid(row=2, column=2, sticky="e", padx=5, pady=5)
        settings_frame.columnconfigure(1, weight=1)

        run_frame = ttk.LabelFrame(self, text="実行")
        run_frame.pack(fill="x", expand=True, pady=5)
        run_frame.columnconfigure(0, weight=1)
        run_frame.columnconfigure(1, weight=1)

        self.strategy_button = ttk.Button(run_frame, text="1. 戦略ファイル (strategy.json) を生成・更新", command=self.start_strategy_generation)
        self.strategy_button.grid(row=0, column=0, padx=5, pady=10, sticky="ew")

        self.run_button = ttk.Button(run_frame, text="2. 全自動処理を開始", command=self.start_full_process)
        self.run_button.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        self.simplify_ini_var = tk.BooleanVar()
        self.simplify_ini_check = ttk.Checkbutton(run_frame, text="Robco INI の出力をシンプルにする (推奨: 変更対象の武器のみ記録)", variable=self.simplify_ini_var)
        self.simplify_ini_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=(0, 10))

        log_frame = ttk.LabelFrame(self, text="ログ")
        log_frame.pack(fill="both", expand=True, pady=5)
        log_frame.grid_propagate(False)
        log_frame.config(width=800, height=300)

        log_scrollbar = ttk.Scrollbar(log_frame)
        self.log_text = tk.Text(log_frame, wrap="word", state="disabled", yscrollcommand=log_scrollbar.set)
        log_scrollbar.config(command=self.log_text.yview)

        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red", font=("TkDefaultFont", 9, "bold"))
        self.log_text.tag_config("CRITICAL", foreground="red", background="yellow", font=("TkDefaultFont", 9, "bold"))
        self.log_text.tag_config("DEBUG", foreground="gray")

        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        log_scrollbar.pack(side="right", fill="y")

    def browse_file(self, var, title, filetypes):
        filepath = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if filepath:
            normalized_path = Path(filepath).as_posix()
            var.set(normalized_path)

            if var is self.mo2_executable_var:
                self._auto_detect_mo2_overwrite(normalized_path)

    def _auto_detect_mo2_overwrite(self, mo2_exe_path_str: str):
        """MO2の実行可能ファイルパスからOverwriteフォルダを自動検出する。"""
        try:
            mo2_exe_path = Path(mo2_exe_path_str)
            mo2_base_dir = mo2_exe_path.parent
            found_path = None

            # パターン1: インスタンス版 (profiles/<profile_name>/overwrite)
            profiles_dir = mo2_base_dir / 'profiles'
            if profiles_dir.is_dir():
                current_profile = self.xedit_profile_var.get()
                if current_profile:
                    profile_overwrite_path = profiles_dir / current_profile / 'overwrite'
                    if profile_overwrite_path.is_dir():
                        found_path = profile_overwrite_path

            # パターン2: ポータブル版 (overwrite)
            if not found_path:
                portable_overwrite_path = mo2_base_dir / 'overwrite'
                if portable_overwrite_path.is_dir():
                    found_path = portable_overwrite_path
            
            if found_path:
                self.mo2_overwrite_dir_var.set(found_path.as_posix())
                logging.info(f"MO2のOverwriteフォルダを自動検出しました: {found_path}")
            else:
                logging.warning("MO2のOverwriteフォルダの自動検出に失敗しました。手動で設定してください。")
        except Exception as e:
            logging.warning(f"Overwriteフォルダの自動検出中にエラーが発生しました: {e}")

    def browse_directory(self, var, title):
        """ディレクトリ選択ダイアログを開き、選択されたパスを変数に設定する"""
        dirpath = filedialog.askdirectory(title=title)
        if dirpath:
            var.set(dirpath)

    def toggle_mo2_settings(self):
        state = "normal" if self.use_mo2_var.get() else "disabled"
        for child in self.mo2_settings_frame.winfo_children():
            child.configure(state=state)

    def load_settings(self):
        try:
            self.use_mo2_var.set(self.config_manager.get_boolean('Environment', 'use_mo2'))
            self.mo2_executable_var.set(self.config_manager.get_string('Environment', 'mo2_executable_path'))
            self.xedit_profile_var.set(self.config_manager.get_string('Environment', 'xedit_profile_name'))
            self.mo2_entry_name_var.set(self.config_manager.get_string('Environment', 'mo2_xedit_entry_name'))
            self.mo2_overwrite_dir_var.set(self.config_manager.get_string('Environment', 'mo2_overwrite_dir'))
            self.mo2_shortcut_format_var.set(self.config_manager.get_string('Environment', 'mo2_shortcut_format', 'auto'))
            self.mo2_instance_name_var.set(self.config_manager.get_string('Environment', 'mo2_instance_name', ''))
            self.simplify_ini_var.set(self.config_manager.get_boolean('Parameters', 'simplify_robco_ammo_ini', fallback=True))
            self.xedit_executable_var.set(str(self.config_manager.get_path('Paths', 'xedit_executable')))
        except Exception as e:
            messagebox.showwarning("設定読み込みエラー", f"config.ini の一部設定が読み込めませんでした。\n{e}")
            logging.warning(f"設定の読み込み中にエラー: {e}")
        self.toggle_mo2_settings()
    
    def save_settings(self):
        try:
            self.config_manager.save_setting('Environment', 'use_mo2', str(self.use_mo2_var.get()))
            self.config_manager.save_setting('Environment', 'mo2_executable_path', self.mo2_executable_var.get())
            self.config_manager.save_setting('Environment', 'xedit_profile_name', self.xedit_profile_var.get())
            self.config_manager.save_setting('Environment', 'mo2_xedit_entry_name', self.mo2_entry_name_var.get())
            self.config_manager.save_setting('Environment', 'mo2_overwrite_dir', self.mo2_overwrite_dir_var.get())
            self.config_manager.save_setting('Environment', 'mo2_shortcut_format', self.mo2_shortcut_format_var.get())
            self.config_manager.save_setting('Environment', 'mo2_instance_name', self.mo2_instance_name_var.get())
            self.config_manager.save_setting('Parameters', 'simplify_robco_ammo_ini', str(self.simplify_ini_var.get()))
            self.config_manager.save_setting('Paths', 'xedit_executable', self.xedit_executable_var.get())
            logging.info("設定が config.ini に正常に保存されました。")
            return True
        except Exception as e:
            messagebox.showerror("設定保存エラー", f"設定の保存中にエラーが発生しました。\n{e}")
            logging.error(f"設定の保存に失敗しました: {e}", exc_info=True)
            return False
    
    def poll_log_queue(self):
        while True:
            try:
                record = self.log_queue.get_nowait()
            except queue.Empty:
                break
            else:
                msg = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s').format(record)
                self.log_text.config(state="normal")
                self.log_text.insert(tk.END, msg + '\n', record.levelname)
                self.log_text.config(state="disabled")
                self.log_text.see(tk.END)
        self.after(100, self.poll_log_queue)

    def start_process(self, process_func):
        if self.is_running:
            messagebox.showwarning("実行中", "プロセスは既に実行中です。")
            return
        if not self.save_settings():
            return
        
        thread = threading.Thread(target=process_func)
        thread.daemon = True
        thread.start()

    def start_strategy_generation(self):
        self.start_process(self.run_strategy_generation_in_thread)

    def start_full_process(self):
        self.start_process(self.run_full_process_in_thread)

    def run_process_wrapper(self, target_func, process_name):
        self.is_running = True
        self.run_button.config(state="disabled")
        self.strategy_button.config(state="disabled")
        
        self.log_text.config(state="normal")
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state="disabled")
        
        was_successful = True
        try:
            target_func()
            final_log = self.log_text.get("1.0", tk.END)
            if "プロセス失敗" in final_log or "CRITICAL" in final_log:
                 was_successful = False
        except Exception:
            logging.critical("プロセスの実行中にキャッチされない例外が発生しました。", exc_info=True)
            was_successful = False
        finally:
            self.is_running = False
            self.run_button.config(state="normal")
            self.strategy_button.config(state="normal")
            
            logging.info(f"{ '='*20} {process_name}が終了しました {'='*20}")

            if was_successful:
                messagebox.showinfo("完了", f"{process_name}が正常に完了しました！")
            else:
                messagebox.showerror("エラー", f"{process_name}中にエラーが発生しました。\n詳細はログを確認してください。")

    def run_strategy_generation_in_thread(self):
        self.run_process_wrapper(self.orchestrator.run_strategy_generation, "戦略ファイル生成処理")

    def run_full_process_in_thread(self):
        self.run_process_wrapper(self.orchestrator.run_full_process, "全自動処理")

def setup_logging(log_queue):
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    file_handler = logging.FileHandler("patcher.log", mode='w', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    
    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(formatter)
    
    logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler, queue_handler])

if __name__ == '__main__':
    if not is_admin():
        if messagebox.askyesno("管理者権限の確認", "このアプリケーションは管理者権限で実行されていません。\nファイルの移動やコピーが失敗する可能性があります。\n\n管理者権限で再起動しますか？"): # Changed from to \n
            if not request_admin_elevation():
                messagebox.showerror("エラー", "管理者権限での再起動に失敗しました。\n手動で「管理者として実行」を選択して起動してください。")
        else:
            logging.warning("[警告] 管理者権限なしで続行します")
    
    gui_log_queue = queue.Queue()
    setup_logging(gui_log_queue)
    
    root = tk.Tk()
    app = None
    try:
        from config_manager import ConfigManager
        from Orchestrator import Orchestrator

        config_mgr = ConfigManager('config.ini')
        orchestrator_instance = Orchestrator(config_mgr)
        app = Application(master=root, config_manager=config_mgr, orchestrator=orchestrator_instance, log_queue=gui_log_queue)
    except Exception as e:
        logging.critical("アプリケーションの初期化中に致命的なエラーが発生しました。", exc_info=True)
        messagebox.showerror("致命的なエラー", f"アプリケーションの起動に失敗しました:\n{e}")
        root.destroy()
    
    if app:
        app.mainloop()