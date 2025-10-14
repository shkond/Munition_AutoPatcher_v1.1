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

        # --- データ保持用の変数 ---
        self.ammo_to_map = []
        self.munitions_ammo_list = []
        self.weapon_records = []

        # --- ファイルパスを引数から取得 ---
        self.ammo_file_path = Path(ammo_file_path)
        self.munitions_file_path = Path(munitions_file_path)
        self.output_file_path = Path(output_file_path)

        if not self.headless:
            # --- UIのセットアップ ---
            self.setup_ui()

            # --- データの読み込みとUIの構築 ---
            self.reload_data_and_build_ui()
        else:
            self.load_data()

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
        headers = ["変換", "ESP名", "元弾薬EditorID", "OMOD (存在する場合優先)", "変換先Munitions弾薬 (FormID | EditorID)"]
        for i, header in enumerate(headers):
            style = 'bold.TLabel'
            ttk.Style().configure(style, font=('Helvetica', 10, 'bold'))
            label = ttk.Label(self.content_frame, text=header, style=style)
            label.grid(row=0, column=i, padx=5, pady=(5, 10), sticky="w")

        # カラム幅の調整（0=チェック, 1=ESP名, 2=EditorID, 3=OMOD, 4=選択コンボ）
        self.content_frame.grid_columnconfigure(1, weight=1, minsize=200)
        self.content_frame.grid_columnconfigure(2, weight=1, minsize=200)
        self.content_frame.grid_columnconfigure(3, weight=1, minsize=220)
        self.content_frame.grid_columnconfigure(4, weight=2, minsize=350)

        # 保存ボタン
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        save_button = ttk.Button(button_frame, text="ammo_map.ini を保存", command=self.save_ini_file)
        save_button.pack(pady=5)

    def _show_error(self, title: str, message: str):
        if getattr(self, "headless", False):
            print(f"[ERROR] {title}: {message}", file=sys.stderr)
        else:
            messagebox.showerror(title, message)

    def _show_info(self, title: str, message: str):
        if getattr(self, "headless", False):
            print(f"[INFO] {title}: {message}")
        else:
            messagebox.showinfo(title, message)

    def _show_success(self, title: str, message: str):
        if getattr(self, "headless", False):
            print(f"[SUCCESS] {title}: {message}")
        else:
            messagebox.showinfo(title, message)

    def manual_file_select(self):
        """手動でファイルを選択"""
        if self.headless:
            self._show_error("エラー", "ヘッドレスモードでは手動ファイル選択は利用できません。")
            return
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
        self.ammo_to_map = []
        self.munitions_ammo_list = []

        if self.headless:
            self.load_data()
            return

        if self.content_frame is None:
            return

        for child in self.content_frame.winfo_children():
            if int(child.grid_info()['row']) > 0:
                child.destroy()

        if self.load_data():
            self.build_ui_rows()
        else:
            pass

    def load_data(self):
        """データを読み込み"""
        self.weapon_records = []
        # --- Attempt to auto-detect xEdit/Pas-generated output files in common locations ---
        try:
            # Candidate files (relative to Output/ and workspace root)
            candidates = {
                'munitions': ['munitions_ammo_ids.ini', 'munitions_ammo_ids.ini'],
                'unmapped': ['unique_ammo_for_mapping.ini', 'ammo_map.ini'],
            }
            out_dir = Path('Output')
            # If the configured munitions/ammo paths are missing, try to find them in Output/
            if not self.munitions_file_path.exists():
                for name in candidates['munitions']:
                    p = out_dir / name
                    if p.exists():
                        try:
                            self.munitions_file_path = p
                            print(f"[mapper-debug] Auto-detected munitions file: {p}")
                        except Exception:
                            pass
                        break
            if not self.ammo_file_path.exists():
                for name in candidates['unmapped']:
                    p = out_dir / name
                    if p.exists():
                        try:
                            self.ammo_file_path = p
                            print(f"[mapper-debug] Auto-detected unmapped ammo file: {p}")
                        except Exception:
                            pass
                        break
        except Exception:
            pass
        # --- Munitions弾薬リストを読み込む (INI形式) ---
        # Munitions弾薬リストを読み込む
        try:
            if not self.munitions_file_path.exists():
                self._show_error("エラー", f"'{self.munitions_file_path}' が見つかりません。\n\nxEditスクリプト '03_ExportMunitionsAmmoIDs.pas' を実行してファイルを生成してください。")
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
            # Debug: report munitions list load
            try:
                print(f"[mapper-debug] Loaded Munitions ammo entries: {len(self.munitions_ammo_list)} from {self.munitions_file_path}")
            except Exception:
                pass
        except Exception as e:
            self._show_error("エラー", f"'{self.munitions_file_path}' の読み込みに失敗しました:\n{e}")
            return False

        # 変換元弾薬リストを読み込む
        try:
            if not self.ammo_file_path.exists():
                self._show_error("エラー", f"'{self.ammo_file_path}' が見つかりません。\n\nxEditスクリプト '01_ExtractWeaponAmmoMapping.pas' を実行してファイルを生成してください。")
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
                    "widgets": {},
                    # will be filled from weapon_omod_map JSON (if found)
                    "omods_info": []
                })

            # Debug: report unmapped ammo load
            try:
                print(f"[mapper-debug] Loaded UnmappedAmmo entries: {len(self.ammo_to_map)} from {self.ammo_file_path}")
            except Exception:
                pass

        except Exception as e:
            self._show_error("エラー", f"'{self.ammo_file_path}' の読み込みに失敗しました:\n{e}")
            return False
            
        # --- Try to enrich with weapon_omod_map.json if present ---
        try:
            # search common locations: same dir as ammo file, Output/, workspace Output/
            candidate_dirs = [self.ammo_file_path.parent, Path('Output'), Path.cwd() / 'Output']
            omod_records: dict[str, list[dict]] = {}
            loaded_weapon_records: list[dict] = []
            seen_sources: set[str] = set()

            for d in candidate_dirs:
                p = d / 'weapon_omod_map.ammofilled.details.json'
                if not p.exists():
                    p = d / 'weapon_omod_map.json'
                if not p.exists():
                    continue
                try:
                    resolved = str(p.resolve()).lower()
                except Exception:
                    resolved = str(p).lower()
                if resolved in seen_sources:
                    continue
                seen_sources.add(resolved)

                try:
                    txt = p.read_text(encoding='utf-8')
                    data = json.loads(txt)
                except Exception:
                    continue

                loaded_weapon_records.extend(data)
                for entry in data:
                    key_a = (entry.get('ammo_form_id') or '').strip().upper()
                    key_b = (entry.get('ammo_editor_id') or '').strip()
                    omods = entry.get('omods') or []
                    if key_a:
                        omod_records.setdefault(key_a, []).extend(omods)
                    if key_b:
                        omod_records.setdefault(key_b, []).extend(omods)

            self.weapon_records = loaded_weapon_records

            # attach to ammo_to_map rows
            for row in self.ammo_to_map:
                ofid = row['original_form_id'].upper()
                ed = row['editor_id']
                attached = []
                if ofid in omod_records:
                    attached.extend(omod_records[ofid])
                if ed in omod_records:
                    attached.extend(omod_records[ed])
                seen = set()
                uniq = []
                for o in attached:
                    if not isinstance(o, dict):
                        continue
                    key = (o.get('omod_plugin') or '') + '|' + (o.get('omod_form_id') or '')
                    if key and key not in seen:
                        seen.add(key)
                        uniq.append(o)
                row['omods_info'] = uniq
        except Exception:
            # swallow enrichment errors (retain previous behavior)
            self.weapon_records = []
            pass

        # Debug: report enrichment results
        try:
            total_with_omods = sum(1 for r in self.ammo_to_map if r.get('omods_info'))
            print(f"[mapper-debug] Rows with attached OMODs: {total_with_omods} / {len(self.ammo_to_map)}")
        except Exception:
            pass
        # indicate success
        return True

    def build_ui_rows(self):
        """UIの行を構築"""
        munitions_list_with_blank = [""] + self.munitions_ammo_list

        # Debug: report expected number of rows to build
        try:
            print(f"[mapper-debug] build_ui_rows expected rows: {len(self.ammo_to_map)}")
        except Exception:
            pass
        
        for index, ammo_data in enumerate(self.ammo_to_map):
            try:
                print(f"[mapper-debug] build_ui_rows processing index={index} esp={ammo_data.get('esp_name')} editor={ammo_data.get('editor_id')}")
            except Exception:
                pass
            row_num = index + 1
            
            chk_var = tk.BooleanVar()
            chk = ttk.Checkbutton(self.content_frame, variable=chk_var)
            chk.grid(row=row_num, column=0, padx=(5, 10))
            
            ttk.Label(self.content_frame, text=ammo_data["esp_name"], wraplength=180).grid(row=row_num, column=1, sticky="w", padx=5)
            ttk.Label(self.content_frame, text=ammo_data["editor_id"], wraplength=180).grid(row=row_num, column=2, sticky="w", padx=5)

            # OMOD info column
            omod_label_text = ""
            if ammo_data.get('omods_info'):
                try:
                    # show plugin|form pairs
                    parts = []
                    for o in ammo_data['omods_info']:
                        p = (o.get('omod_plugin') or '').strip()
                        f = (o.get('omod_form_id') or '').strip().upper()
                        parts.append(f"{p}|{f}")
                    omod_label_text = ", ".join(parts)
                except Exception:
                    omod_label_text = "(OMODあり)"
            ttk.Label(self.content_frame, text=omod_label_text, wraplength=220, foreground='darkgreen').grid(row=row_num, column=3, sticky="w", padx=5)

            combo = ttk.Combobox(self.content_frame, values=munitions_list_with_blank, state="readonly", width=50)
            combo.grid(row=row_num, column=4, sticky="ew", padx=5, pady=2)

            combo.bind("<FocusIn>", lambda e: self.disable_canvas_scroll())
            combo.bind("<FocusOut>", lambda e: self.enable_canvas_scroll())

            ammo_data['widgets'] = {'chk_var': chk_var, 'combo': combo}

        # Debug: report actual widget count under content_frame
        try:
            created = len([c for c in self.content_frame.winfo_children() if int(c.grid_info().get('row', 0)) > 0])
            print(f"[mapper-debug] build_ui_rows created widget rows: {created}")
        except Exception:
            pass

    def disable_canvas_scroll(self):
        if not self.canvas:
            return
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def enable_canvas_scroll(self):
        if not self.canvas:
            return
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self.on_mouse_wheel)

    def save_ini_file(self) -> bool:
        """Generate ammo_map.json and RobCo patch (method name retained for compatibility)."""
        output_dir = self.output_file_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.output_file_path.suffix.lower() == ".json":
            json_path = self.output_file_path
        else:
            json_path = self.output_file_path.with_suffix(".json")

        legacy_ini_candidates: list[Path] = []
        if self.output_file_path.suffix.lower() == ".ini":
            legacy_ini_candidates.append(self.output_file_path)
        else:
            legacy_ini_candidates.append(self.output_file_path.with_suffix(".ini"))

        robco_path = output_dir / "robco_ammo_patch.ini"

        weapon_lines: list[str] = []
        omod_lines: list[str] = []
        mapping_entries: list[dict[str, object]] = []
        has_error = False
        error_messages: list[str] = []

        npc_map: dict[str, str] = {}
        try:
            cand = output_dir / "munitions_npc_lists.ini"
            if not cand.exists():
                cand = Path("Output") / "munitions_npc_lists.ini"
            if cand.exists():
                cfg = configparser.ConfigParser()
                cfg.read(cand, encoding="utf-8")
                if cfg.has_section("AmmoNPCList"):
                    for k, v in cfg.items("AmmoNPCList"):
                        k_norm = normalize_form_id(k)
                        v_norm = normalize_form_id(v)
                        if k_norm and v_norm:
                            npc_map[k_norm.upper()] = v_norm.upper()
        except Exception:
            npc_map = {}

        weapon_by_form: dict[str, list[dict]] = {}
        weapon_by_editor: dict[str, list[dict]] = {}
        for entry in self.weapon_records or []:
            form_key = (entry.get("ammo_form_id") or "").strip().upper()
            editor_key = (entry.get("ammo_editor_id") or "").strip()
            if form_key:
                weapon_by_form.setdefault(form_key, []).append(entry)
            if editor_key:
                weapon_by_editor.setdefault(editor_key, []).append(entry)

        MUNITIONS_PLUGIN = "Munitions - An Ammo Expansion.esl"
        processed_rows = 0

        for index, ammo_data in enumerate(self.ammo_to_map):
            widgets = ammo_data.get("widgets") or {}
            selected_ammo = None

            try:
                if widgets and widgets.get("combo") is not None:
                    selected_ammo = widgets["combo"].get()
                    if not selected_ammo and ammo_data.get("selected_target"):
                        selected_ammo = ammo_data.get("selected_target")
                    chk = widgets.get("chk_var")
                    if chk is not None and not chk.get() and not ammo_data.get("selected_target"):
                        continue
                else:
                    selected_ammo = ammo_data.get("selected_target")
                    if not selected_ammo:
                        continue
            except Exception:
                continue

            if not selected_ammo:
                has_error = True
                error_messages.append(
                    f"行 {index + 1}: {ammo_data['esp_name']} - {ammo_data['editor_id']} で変換先が選択されていません"
                )
                continue

            parts = [p.strip() for p in selected_ammo.split("|", 1)]
            new_form_raw = parts[0] if parts else ""
            new_form_norm = normalize_form_id(new_form_raw)
            if not new_form_norm:
                has_error = True
                error_messages.append(f"行 {index + 1}: 変換先 FormID の形式が不正です -> '{selected_ammo}'")
                continue
            target_editor_id = parts[1].strip() if len(parts) > 1 else ""

            original_form_norm = normalize_form_id(ammo_data["original_form_id"])
            if not original_form_norm:
                has_error = True
                error_messages.append(f"行 {index + 1}: 元 FormID の形式が不正です -> '{ammo_data['original_form_id']}'")
                continue

            processed_rows += 1

            mapping_entry: dict[str, object] = {
                # legacy flat fields (preserve for backwards compatibility)
                "original_form_id": original_form_norm,
                "target_form_id": new_form_norm,
                "target_plugin": MUNITIONS_PLUGIN,
            }
            # structured fields expected by Orchestrator/robco loader
            mapping_entry["source"] = {
                "formid": original_form_norm,
                "plugin": (ammo_data.get("esp_name") or "")
            }
            mapping_entry["target"] = {
                "formid": new_form_norm,
                "plugin": MUNITIONS_PLUGIN
            }
            if ammo_data.get("esp_name"):
                mapping_entry["original_plugin"] = ammo_data["esp_name"]
                mapping_entry["source"]["plugin"] = ammo_data.get("esp_name")
            if ammo_data.get("editor_id"):
                mapping_entry["original_editor_id"] = ammo_data["editor_id"]
                mapping_entry["source"]["editor_id"] = ammo_data.get("editor_id")
            if target_editor_id:
                mapping_entry["target_editor_id"] = target_editor_id
                mapping_entry["target"]["editor_id"] = target_editor_id

            omod_payloads = []
            for omod in ammo_data.get("omods_info") or []:
                omod_plugin = (omod.get("omod_plugin") or "").strip()
                omod_form = normalize_form_id(omod.get("omod_form_id"))
                if not (omod_plugin and omod_form):
                    continue
                omod_payloads.append({
                    "omod_plugin": omod_plugin,
                    "omod_form_id": omod_form,
                })
                omod_lines.append(
                    f"filterByOMod={omod_plugin}|{omod_form.upper()}:changeOModPropertiesForm=Ammo={MUNITIONS_PLUGIN}|{new_form_norm.upper()}"
                )
            if omod_payloads:
                mapping_entry["omods"] = omod_payloads

            weapon_plugin = ""
            weapon_form = ""
            candidates = weapon_by_form.get(original_form_norm.upper(), [])
            if not candidates:
                candidates = weapon_by_editor.get(ammo_data["editor_id"], [])
            if candidates:
                chosen = candidates[0]
                weapon_plugin = (chosen.get("weapon_plugin") or "").strip()
                weapon_form = normalize_form_id(chosen.get("weapon_form_id")) or ""
                if weapon_plugin:
                    mapping_entry["weapon_plugin"] = weapon_plugin
                if weapon_form:
                    mapping_entry["weapon_form_id"] = weapon_form

            if weapon_plugin and weapon_form:
                line = f"filterByWeapons={weapon_plugin}|{weapon_form.upper()}:setNewAmmo={new_form_norm.upper()}"
                list_form = npc_map.get(new_form_norm.upper())
                if list_form:
                    line = line + f":setNewAmmoList={list_form}"
                    mapping_entry["setNewAmmoList"] = list_form
                weapon_lines.append(line)
            else:
                weapon_lines.append(
                    f"; WARNING: weapon plugin/form not found for {ammo_data['esp_name']} {ammo_data['editor_id']}. Intended setNewAmmo={new_form_norm.upper()}"
                )

            mapping_entries.append(mapping_entry)

        if has_error:
            self._show_error("エラー", "以下の問題があります:\n\n" + "\n".join(error_messages))
            return False

        if processed_rows == 0:
            self._show_info("情報", "保存する項目が選択されていません。")
            return False

        try:
            temp_path = robco_path.with_name(robco_path.name + ".part")
            with temp_path.open("w", encoding="utf-8") as f:
                f.write("; Generated by Munitions Ammo Mapper for RobCo Patcher\n")
                f.write("; Weapon lines (setNewAmmo) follow\n\n")
                for line in weapon_lines:
                    f.write(line + "\n")
                f.write("\n; OMOD lines (change OMOD Ammo) follow\n\n")
                for line in omod_lines:
                    f.write(line + "\n")
            temp_path.replace(robco_path)
        except Exception as e:
            self._show_error("エラー", f"RobCo パッチの保存中にエラーが発生しました:\n{e}")
            return False

        payload = {
            "meta": {
                "version": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "mapping_count": len(mapping_entries),
                "source": "mapper.py",
            },
            "mappings": mapping_entries,
        }

        try:
            json_temp = json_path.with_name(json_path.name + ".part")
            json_text = json.dumps(payload, ensure_ascii=False, indent=2)
            json_temp.write_text(json_text, encoding="utf-8")
            json_temp.replace(json_path)
        except Exception as e:
            self._show_error("エラー", f"ammo_map.json の保存中にエラーが発生しました:\n{e}")
            return False

        for legacy_path in legacy_ini_candidates:
            if legacy_path == json_path:
                continue
            try:
                legacy_path.unlink(missing_ok=True)
            except Exception:
                pass

        self._show_success("成功", f"マッピング JSON を保存しました: {json_path}")
        print(f"AMMO_MAP_JSON_WRITTEN:{json_path}")
        return True

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