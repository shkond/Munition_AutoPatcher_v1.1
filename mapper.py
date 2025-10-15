import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
import argparse
import locale
import configparser
import json
import sys
from datetime import datetime, timezone

# utils.pyから共通関数をインポート (もしあれば)
# from utils import read_text_utf8_fallback

def normalize_form_id(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    filtered = "".join(ch for ch in text if ch in "0123456789abcdef")
    if not filtered:
        return None
    if len(filtered) > 8:
        filtered = filtered[-8:]
    return filtered.rjust(8, "0")

class AmmoMapperApp:
    def __init__(self, root_window, ammo_file_path, munitions_file_path, output_file_path, *, headless: bool = False):
        self.root = root_window
        self.headless = headless

        self.canvas: tk.Canvas | None = None
        self.content_frame: ttk.Frame | None = None

        if not self.headless:
            if self.root is None:
                raise ValueError("root_window must be provided when headless is False")
            self.root.title("Munitions Ammo Mapper")
            self.root.geometry("1000x750")
        else:
            if self.root is not None:
                try:
                    self.root.withdraw()
                except Exception:
                    pass

        self.ammo_to_map = []
        self.munitions_ammo_list = []
        self.weapon_records = []

        self.ammo_file_path = Path(ammo_file_path)
        self.munitions_file_path = Path(munitions_file_path)
        self.output_file_path = Path(output_file_path)

        if not self.headless:
            self.setup_ui()
            self.reload_data_and_build_ui()
        else:
            self.load_data()

    def setup_ui(self):
        """GUIの基本レイアウトを設定"""
        path_frame = ttk.LabelFrame(self.root, text="ファイルパス")
        path_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        ttk.Label(path_frame, text="変換元:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(path_frame, text=str(self.ammo_file_path), foreground="blue").grid(row=0, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(path_frame, text="Munitions:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(path_frame, text=str(self.munitions_file_path), foreground="blue").grid(row=1, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(path_frame, text="出力先:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(path_frame, text=str(self.output_file_path), foreground="green").grid(row=2, column=1, sticky="w", padx=5, pady=2)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=1, padx=10, pady=5)

        self.canvas = tk.Canvas(main_frame, borderwidth=0)
        self.content_frame = ttk.Frame(self.canvas)
        
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        self.content_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)

        headers = ["変換", "ESP名", "元弾薬EditorID", "OMOD (存在する場合優先)", "変換先Munitions弾薬 (FormID | EditorID)"]
        for i, header in enumerate(headers):
            ttk.Label(self.content_frame, text=header, font=('Helvetica', 10, 'bold')).grid(row=0, column=i, padx=5, pady=(5, 10), sticky="w")

        self.content_frame.grid_columnconfigure(4, weight=1)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        save_button = ttk.Button(button_frame, text="マッピングを保存 (JSON)", command=self.save_mappings_json)
        save_button.pack(pady=5)

    def on_mouse_wheel(self, event):
        scroll_speed = -1 if os.name == 'posix' else -int(event.delta / 120)
        self.canvas.yview_scroll(scroll_speed, "units")

    def reload_data_and_build_ui(self):
        self.ammo_to_map = []
        self.munitions_ammo_list = []
        for child in self.content_frame.winfo_children():
            if int(child.grid_info()['row']) > 0:
                child.destroy()
        if self.load_data():
            self.build_ui_rows()

    def load_data(self):
        """INI形式の弾薬リストを読み込む"""
        try:
            # Munitions弾薬リスト
            parser = configparser.ConfigParser()
            parser.read(self.munitions_file_path, encoding=locale.getpreferredencoding())
            if parser.has_section('MunitionsAmmo'):
                self.munitions_ammo_list = [f"{form_id.upper()} | {editor_id}" for form_id, editor_id in parser.items('MunitionsAmmo')]
                self.munitions_ammo_list.sort()
            
            # 変換元弾薬リスト
            parser.read(self.ammo_file_path, encoding=locale.getpreferredencoding())
            if parser.has_section('UnmappedAmmo'):
                exclude_list = ['Fallout4.esm', 'Munitions - An Ammo Expansion.esl', 'DLCRobot.esm', 'DLCCoast.esm', 'DLCNukaWorld.esm']
                for original_form_id, details_part in parser.items('UnmappedAmmo'):
                    details = details_part.split('|')
                    esp_name = details[0].strip() if len(details) > 0 else "(不明)"
                    if any(x in esp_name for x in exclude_list):
                        continue
                    self.ammo_to_map.append({
                        "original_form_id": original_form_id.upper(),
                        "esp_name": esp_name,
                        "editor_id": details[1].strip() if len(details) > 1 else "(不明)",
                        "widgets": {},
                        "omods_info": [] # 将来の拡張用
                    })
            return True
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました:\n{e}")
            return False

    def build_ui_rows(self):
        """データに基づいてUIの行を動的に構築する"""
        munitions_list_with_blank = [""] + self.munitions_ammo_list
        for index, ammo_data in enumerate(self.ammo_to_map):
            row_num = index + 1
            chk_var = tk.BooleanVar()
            ttk.Checkbutton(self.content_frame, variable=chk_var).grid(row=row_num, column=0, padx=(5, 10))
            ttk.Label(self.content_frame, text=ammo_data["esp_name"]).grid(row=row_num, column=1, sticky="w", padx=5)
            ttk.Label(self.content_frame, text=ammo_data["editor_id"]).grid(row=row_num, column=2, sticky="w", padx=5)
            ttk.Label(self.content_frame, text="").grid(row=row_num, column=3, sticky="w", padx=5) # OMODプレースホルダー
            combo = ttk.Combobox(self.content_frame, values=munitions_list_with_blank, state="readonly", width=50)
            combo.grid(row=row_num, column=4, sticky="ew", padx=5, pady=2)
            ammo_data['widgets'] = {'chk_var': chk_var, 'combo': combo}

    def save_mappings_json(self) -> bool:
        """ユーザーの選択に基づいてammo_map.jsonを生成・保存する。"""
        json_path = self.output_file_path.with_suffix(".json")
        json_path.parent.mkdir(parents=True, exist_ok=True)

        mapping_entries = []
        has_error = False

        for index, ammo_data in enumerate(self.ammo_to_map):
            widgets = ammo_data.get("widgets", {})
            chk_var = widgets.get("chk_var")
            if not (chk_var and chk_var.get()):
                continue

            selected_ammo = widgets.get("combo").get()
            if not selected_ammo:
                messagebox.showerror("エラー", f"行 {index + 1}: {ammo_data['editor_id']} の変換先が選択されていません")
                has_error = True
                continue

            parts = [p.strip() for p in selected_ammo.split("|", 1)]
            new_form_norm = normalize_form_id(parts[0])
            if not new_form_norm:
                messagebox.showerror("エラー", f"行 {index + 1}: 変換先FormIDの形式が不正です -> '{selected_ammo}'")
                has_error = True
                continue

            mapping_entries.append({
                "source": {
                    "formid": normalize_form_id(ammo_data["original_form_id"]),
                    "plugin": ammo_data.get("esp_name"),
                    "editor_id": ammo_data.get("editor_id")
                },
                "target": {
                    "formid": new_form_norm,
                    "plugin": "Munitions - An Ammo Expansion.esl",
                    "editor_id": parts[1] if len(parts) > 1 else ""
                }
            })

        if has_error:
            return False
        if not mapping_entries:
            messagebox.showinfo("情報", "保存する項目が選択されていません。")
            return False

        payload = {
            "meta": {
                "version": 2,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": "mapper.py",
            },
            "mappings": mapping_entries,
        }

        try:
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("成功", f"マッピング情報を保存しました: {json_path}")
            return True
        except Exception as e:
            messagebox.showerror("エラー", f"ammo_map.json の保存中にエラーが発生しました:\n{e}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Munitions Ammo Mapper")
    parser.add_argument("--ammo-file", required=True)
    parser.add_argument("--munitions-file", required=True)
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()

    root = tk.Tk()
    app = AmmoMapperApp(root, **vars(args))
    root.mainloop()
