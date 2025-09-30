import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
import argparse
import locale
import configparser

class AmmoMapperApp:
    def __init__(self, root_window, ammo_file_path, munitions_file_path, output_file_path):
        self.root = root_window
        self.root.title("Munitions Ammo Mapper")
        self.root.geometry("1000x750")

        # --- データ保持用の変数 ---
        self.ammo_to_map = []
        self.munitions_ammo_list = []

        # --- ファイルパスを引数から取得 ---
        self.ammo_file_path = Path(ammo_file_path)
        self.munitions_file_path = Path(munitions_file_path)
        self.output_file_path = Path(output_file_path)

        # --- UIのセットアップ ---
        self.setup_ui()

        # --- データの読み込みとUIの構築 ---
        self.reload_data_and_build_ui()

    def setup_ui(self):
        """GUIの基本レイアウトを設定"""
        # ファイルパス表示フレーム
        path_frame = ttk.LabelFrame(self.root, text="ファイルパス (xEdit Outputディレクトリから自動読み込み)")
        path_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # 変換元ファイルパス
        ttk.Label(path_frame, text="変換元:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ammo_path_label = ttk.Label(path_frame, text=str(self.ammo_file_path), foreground="blue")
        ammo_path_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        # Munitionsファイルパス
        ttk.Label(path_frame, text="Munitions:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        munitions_path_label = ttk.Label(path_frame, text=str(self.munitions_file_path), foreground="blue")
        munitions_path_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        # 出力ファイルパス
        ttk.Label(path_frame, text="出力先:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        output_path_label = ttk.Label(path_frame, text=str(self.output_file_path), foreground="green")
        output_path_label.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        # ファイル再選択ボタン
        reload_btn = ttk.Button(path_frame, text="ファイル再選択", command=self.manual_file_select)
        reload_btn.grid(row=0, column=2, rowspan=3, padx=10, pady=4)

        # メインフレーム（以下は以前と同じ）
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=1, padx=10, pady=5)

        self.canvas = tk.Canvas(main_frame, borderwidth=0)
        self.content_frame = ttk.Frame(self.canvas)
        
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        self.content_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self.on_mouse_wheel)

        # ヘッダー行
        headers = ["変換", "ESP名", "元弾薬EditorID", "変換先Munitions弾薬 (FormID | EditorID)"]
        for i, header in enumerate(headers):
            style = 'bold.TLabel'
            ttk.Style().configure(style, font=('Helvetica', 10, 'bold'))
            label = ttk.Label(self.content_frame, text=header, style=style)
            label.grid(row=0, column=i, padx=5, pady=(5, 10), sticky="w")
        
        self.content_frame.grid_columnconfigure(1, weight=1, minsize=200)
        self.content_frame.grid_columnconfigure(2, weight=1, minsize=200)
        self.content_frame.grid_columnconfigure(3, weight=2, minsize=350)

        # 保存ボタン
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        save_button = ttk.Button(button_frame, text="ammo_map.ini を保存", command=self.save_ini_file)
        save_button.pack(pady=5)

    def manual_file_select(self):
        """手動でファイルを選択"""
        # 変換元ファイル選択
        new_ammo_file = filedialog.askopenfilename(
            title="変換元弾薬リストファイルを選択",
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
            initialdir=self.ammo_file_path.parent
        )
        if new_ammo_file:
            self.ammo_file_path = Path(new_ammo_file)

        # Munitionsファイル選択
        new_munitions_file = filedialog.askopenfilename(
            title="Munitions弾薬リストファイルを選択",
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
            initialdir=self.munitions_file_path.parent
        )
        if new_munitions_file:
            self.munitions_file_path = Path(new_munitions_file)

        # UIを更新して再読み込み
        self.setup_ui()
        self.reload_data_and_build_ui()

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_mouse_wheel(self, event):
        if hasattr(event, "num"):
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
        else:
            scroll_speed = -1 if os.name == 'posix' else -int(event.delta / 120)
            self.canvas.yview_scroll(scroll_speed, "units")

    def reload_data_and_build_ui(self):
        for child in self.content_frame.winfo_children():
            if int(child.grid_info()['row']) > 0:
                child.destroy()
        self.ammo_to_map = []
        self.munitions_ammo_list = []

        if self.load_data():
            self.build_ui_rows()
        else:
            pass

    def load_data(self):
        """データを読み込み"""
        # --- Munitions弾薬リストを読み込む (INI形式) ---
        # Munitions弾薬リストを読み込む
        try:
            if not self.munitions_file_path.exists():
                messagebox.showerror("エラー", f"'{self.munitions_file_path}' が見つかりません。\n\nxEditスクリプト '03_ExportMunitionsAmmoIDs.pas' を実行してファイルを生成してください。")
                return False

            default_encoding = locale.getpreferredencoding()

            parser = configparser.ConfigParser()
            parser.read(self.munitions_file_path, encoding=default_encoding)
            if parser.has_section('MunitionsAmmo'):
                for form_id, editor_id in parser.items('MunitionsAmmo'):
                    self.munitions_ammo_list.append(f"{form_id.upper()} | {editor_id}")
            else:
                raise configparser.NoSectionError('MunitionsAmmo')

            self.munitions_ammo_list.sort()
        except Exception as e:
            messagebox.showerror("エラー", f"'{self.munitions_file_path}' の読み込みに失敗しました:\n{e}")
            return False

        # 変換元弾薬リストを読み込む
        try:
            if not self.ammo_file_path.exists():
                messagebox.showerror("エラー", f"'{self.ammo_file_path}' が見つかりません。\n\nxEditスクリプト '01_ExtractWeaponAmmoMapping.pas' を実行してファイルを生成してください。")
                return False

            parser = configparser.ConfigParser()
            parser.read(self.ammo_file_path, encoding=default_encoding)

            if not parser.has_section('UnmappedAmmo'):
                raise configparser.NoSectionError('UnmappedAmmo')

            for original_form_id, details_part in parser.items('UnmappedAmmo'):
                details = details_part.split('|')
                esp_name = details[0].strip() if len(details) > 0 else "(不明なESP)"
                editor_id = details[1].strip() if len(details) > 1 else "(不明なEditorID)"

                # 除外リスト
                if any(x in esp_name for x in ['Fallout4.esm', 'Munitions - An Ammo Expansion.esl', 'DLCRobot.esm', 'DLCCoast.esm', 'DLCNukaWorld.esm']):
                    continue

                self.ammo_to_map.append({
                    "original_form_id": original_form_id.upper(),
                    "esp_name": esp_name,
                    "editor_id": editor_id,
                    "widgets": {}
                })

        except Exception as e:
            messagebox.showerror("エラー", f"'{self.ammo_file_path}' の読み込みに失敗しました:\n{e}")
            return False
            
        return True

    def build_ui_rows(self):
        """UIの行を構築"""
        munitions_list_with_blank = [""] + self.munitions_ammo_list
        
        for index, ammo_data in enumerate(self.ammo_to_map):
            row_num = index + 1
            
            chk_var = tk.BooleanVar()
            chk = ttk.Checkbutton(self.content_frame, variable=chk_var)
            chk.grid(row=row_num, column=0, padx=(5, 10))
            
            ttk.Label(self.content_frame, text=ammo_data["esp_name"], wraplength=180).grid(row=row_num, column=1, sticky="w", padx=5)
            ttk.Label(self.content_frame, text=ammo_data["editor_id"], wraplength=180).grid(row=row_num, column=2, sticky="w", padx=5)
            
            combo = ttk.Combobox(self.content_frame, values=munitions_list_with_blank, state="readonly", width=50)
            combo.grid(row=row_num, column=3, sticky="ew", padx=5, pady=2)

            combo.bind("<FocusIn>", lambda e: self.disable_canvas_scroll())
            combo.bind("<FocusOut>", lambda e: self.enable_canvas_scroll())

            ammo_data['widgets'] = {'chk_var': chk_var, 'combo': combo}

    def disable_canvas_scroll(self):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def enable_canvas_scroll(self):
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self.on_mouse_wheel)

    def save_ini_file(self):
        """INIファイルを保存 - 修正版"""
        file_path = self.output_file_path
        
        lines_to_write = []
        has_error = False
        error_messages = []
        
        # セクションヘッダーを追加
        lines_to_write.append("[UnmappedAmmo]")
        
        for index, ammo_data in enumerate(self.ammo_to_map):
            if ammo_data['widgets']['chk_var'].get():
                selected_ammo = ammo_data['widgets']['combo'].get()
                
                if not selected_ammo:
                    has_error = True
                    error_messages.append(f"行 {index + 1}: {ammo_data['esp_name']} - {ammo_data['editor_id']} で変換先が選択されていません")
                    continue
                
                new_form_id = selected_ammo.split('|')[0].strip()
                original_form_id = ammo_data['original_form_id']
                
                # コメントを追加
                comment = f"; {ammo_data['esp_name']} の {ammo_data['editor_id']} を変換"
                lines_to_write.append(comment)
                lines_to_write.append(f"{original_form_id}={new_form_id}")

        if has_error:
            messagebox.showerror("エラー", "以下の問題があります:\n\n" + "\n".join(error_messages))
            return

        if len(lines_to_write) <= 1:  # セクションヘッダーのみ
            messagebox.showinfo("情報", "保存する項目が選択されていません。")
            return

        try:
            # 出力ディレクトリを作成
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("; Generated by Munitions Ammo Mapper\n")
                f.write("; 正しいINI形式で保存されます\n\n")
                for line in lines_to_write:
                    f.write(line + "\n")
            messagebox.showinfo("成功", f"'{file_path}' に保存しました。")
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの保存中にエラーが発生しました:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()

    parser = argparse.ArgumentParser(description="Munitions Ammo Mapper")
    parser.add_argument("--ammo-file", required=True, help="Path to unique_ammo_for_mapping.ini")
    parser.add_argument("--munitions-file", required=True, help="Path to munitions_ammo_ids.ini")
    parser.add_argument("--output-file", required=True, help="Path for the output ammo_map.ini")
    args = parser.parse_args()

    app = AmmoMapperApp(root,
                        ammo_file_path=args.ammo_file,
                        munitions_file_path=args.munitions_file,
                        output_file_path=args.output_file)
    root.mainloop()