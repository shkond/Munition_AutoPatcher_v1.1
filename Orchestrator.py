import re
import subprocess
import os
import shutil
from pathlib import Path
import logging
import time
import json
import configparser
import locale
import psutil
import shlex

class Orchestrator:
    # ★★★ 修正点: ConfigManagerをインポートするのではなく、
    #            インスタンスをコンストラクタで受け取るように変更。
    def __init__(self, config_manager): # config_manager: ConfigManager
        self.config = config_manager
    
    def _move_results_from_overwrite(self, expected_filenames: list[str]) -> bool:
        """
        MO2のOverwriteフォルダから指定されたファイルを探し、
        アプリケーションのOutputフォルダに移動する。
        """
        logging.info(f"Overwriteフォルダから結果ファイルを検索しています: {expected_filenames}")
        try:
            overwrite_path = self.config.get_path('Paths', 'overwrite_path')
            output_dir = self.config.get_path('Paths', 'output_dir')
        except (configparser.NoSectionError, configparser.NoOptionError):
            logging.error("設定エラー: config.iniの[Paths]に 'overwrite_path' が設定されていません。")
            return False

        if not overwrite_path or not overwrite_path.is_dir():
            logging.error(f"Overwriteフォルダが見つからないか、設定が正しくありません: {overwrite_path}")
            return False

        output_dir.mkdir(parents=True, exist_ok=True)
        
        all_files_found = True
        for filename in expected_filenames:
            # ★★★ 修正点: xEditスクリプトの出力先は通常 "overwrite\Edit Scripts\Output" ★★★
            source_file = overwrite_path / "Edit Scripts" / "Output" / filename
            destination_file = output_dir / filename

            if source_file.is_file():
                try:
                    logging.info(f"  - 移動中: '{source_file}' -> '{destination_file}'")
                    shutil.move(str(source_file), str(destination_file))
                except Exception as e:
                    logging.error(f"ファイル '{filename}' の移動中にエラーが発生しました: {e}")
                    all_files_found = False
            else:
                logging.warning(f"  - スキップ: Overwriteフォルダに '{filename}' が見つかりませんでした。")
                all_files_found = False
        
        if all_files_found:
            logging.info("すべての結果ファイルの移動が完了しました。")
        else:
            logging.error("必須ファイルの一部が見つからなかったため、処理を中断します。")
            return False
            
        return True

    def run_xedit_script(self, script_key: str, success_message: str) -> bool:
        """
        指定されたスクリプトをxEditで実行し、成功を検証する。
        この関数はファイル操作を行わず、プロセスの実行と監視に専念する。
        ライブラリ(`lib`フォルダ)の自動ステージング・クリーンアップも行う。
        """
        xedit_executable_path = self.config.get_path('Paths', 'xedit_executable')
        xedit_dir = xedit_executable_path.parent
        edit_scripts_dir = xedit_dir / "Edit Scripts"

        if not edit_scripts_dir.is_dir():
            logging.error(f"xEditの 'Edit Scripts' フォルダが見つかりません: {edit_scripts_dir}")
            return False

        source_script_path = self.config.get_path('Paths', 'pas_scripts_dir') / self.config.get_script_filename(script_key)
        if not source_script_path.is_file():
            logging.error(f"指定されたスクリプトファイルが見つかりません: {source_script_path}")
            return False

        source_lib_dir = self.config.get_path('Paths', 'pas_scripts_dir') / 'lib'
        dest_lib_dir = edit_scripts_dir / 'lib'
        temp_script_filename = f"TEMP_{int(time.time())}.pas"
        temp_script_path = edit_scripts_dir / temp_script_filename
        # ★★★ 修正点: MO2プロセスハンドルをtryブロックの外で初期化 ★★★
        mo2_process = None
        xedit_process = None

        try:
            logging.info(f"スクリプト '{source_script_path.name}' を '{temp_script_filename}' として準備しています...")
            shutil.copy2(source_script_path, temp_script_path)

            if source_lib_dir.is_dir():
                logging.info(f"ライブラリフォルダ '{source_lib_dir.name}' を準備しています...")
                if dest_lib_dir.exists():
                    shutil.rmtree(dest_lib_dir)
                shutil.copytree(source_lib_dir, dest_lib_dir)

            env_settings = self.config.get_env_settings()

            # ★★★ 修正点: game_data_pathをconfigから直接取得し、-d引数を正しく設定する ★★★
            game_data_path = self.config.get_path('Paths', 'game_data_path')

            command_list = []
            if env_settings.get('use_mo2', False):
                command_list.extend([
                    str(env_settings["mo2_executable_path"]),
                    '-p',
                    str(env_settings["xedit_profile_name"])
                ])
            command_list.append(str(xedit_executable_path))

            # --- ログ出力設定 ---
            # OutputフォルダにxEditのログを直接出力させることで、エラー原因の特定を容易にする
            output_dir = self.config.get_path('Paths', 'output_dir')
            output_dir.mkdir(parents=True, exist_ok=True) # 念のためフォルダ作成
            debug_log_path = output_dir / f"xEdit_debug_{int(time.time())}.txt"
            session_log_path = output_dir / f"xEdit_log_{int(time.time())}.txt"

            command_list.extend([
                "-force",
                "-IKnowWhatImDoing",
                "-AllowMasterFilesEdit",
                f"-script:{temp_script_filename}",
                f'-L:"{session_log_path}"', # 通常ログの出力先を指定
                f'-d:"{game_data_path}"' # ゲームのDataフォルダを -d で正しく指定
            ])

            logging.info(f"コマンドを実行します: {' '.join(map(shlex.quote, command_list))}")

            if env_settings.get('use_mo2', False):
                xedit_executable_name = xedit_executable_path.name
                timeout_seconds = 600  # 10分

                launch_timestamp = time.time()
                time_tolerance = 0.5

                mo2_process = subprocess.Popen(command_list)
                logging.info(f"ModOrganizer.exe (PID: {mo2_process.pid}) を起動しました。")

                logging.info(f"'{xedit_executable_name}' プロセスが起動するのを待機しています...")
                start_time = time.time()
                while time.time() - start_time < timeout_seconds:
                    for proc in psutil.process_iter(attrs=['pid', 'name', 'create_time']):
                        try:
                            if proc.info['name'].lower() == xedit_executable_name.lower():
                                if proc.info['create_time'] >= launch_timestamp - time_tolerance:
                                    xedit_process = psutil.Process(proc.info['pid'])
                                    break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    if xedit_process:
                        break
                    time.sleep(1)

                if not xedit_process:
                    logging.error(f"タイムアウト: '{xedit_executable_name}' が {timeout_seconds} 秒以内に起動しませんでした。")
                    return False

                logging.info(f"'{xedit_executable_name}' (PID: {xedit_process.pid}) を検出しました。処理完了を待機します...")

                try:
                    xedit_process.wait(timeout=timeout_seconds)
                    logging.info(f"'{xedit_executable_name}' プロセスが終了しました。")
                except psutil.TimeoutExpired:
                    logging.error(f"タイムアウト: '{xedit_executable_name}' が {timeout_seconds} 秒以内に終了しませんでした。")
                    return False
                except psutil.NoSuchProcess:
                    logging.info(f"'{xedit_executable_name}' プロセスは既に終了していました。")

                # --- ポーリング処理によるログファイルの検証 ---
                logging.info("xEditのログファイルをポーリングで検証します...")
                log_verification_timeout = 10  # 最大10秒間待機
                log_check_start_time = time.time()

                while time.time() - log_check_start_time < log_verification_timeout:
                    # ★★★ 修正点: -Lで指定したログファイルを直接確認する ★★★
                    if session_log_path.is_file():
                        try:
                            log_content = session_log_path.read_text(encoding='utf-8', errors='replace')
                            if success_message in log_content:
                                logging.info(f"xEditログファイルで完了メッセージ '{success_message}' を確認しました。")
                                return True
                        except IOError as e:
                            logging.debug(f"ログファイルの読み取り中にIOエラーが発生しました。リトライします...: {e}")
                    
                    time.sleep(0.5) # 0.5秒待ってから再試行

                # ★★★ 修正点: ログ検証がタイムアウトした場合の処理 ★★★
                # ログ検証がタイムアウトした場合、ここに到達する
                logging.error(f"xEditは終了しましたが、ログファイルで完了メッセージを確認できませんでした。")
                logging.error(f"考えられる原因: xEditがエラーで異常終了した可能性があります。詳細は {debug_log_path.name} を確認してください。")
                if debug_log_path.is_file():
                    try:
                        debug_content = debug_log_path.read_text(encoding='utf-8', errors='replace')
                        if debug_content.strip(): # 空でなければ出力
                            logging.error(f"--- xEdit Debug Log ({debug_log_path.name}) ---")
                            logging.error(debug_content.strip())
                            logging.error("--- End of xEdit Debug Log ---")
                    except Exception as e:
                        logging.error(f"デバッグログファイルの読み込みに失敗しました: {e}")
                return False
            else:
                process = subprocess.run(command_list, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
                stdout = process.stdout
                logging.info("--- xEdit stdout ---")
                if stdout:
                    for line in stdout.strip().splitlines():
                        logging.info(line)
                logging.info("--- xEdit stdout end ---")
    
                if success_message in stdout:
                    logging.info(f"スクリプト '{source_script_path.name}' の正常な完了を確認しました。")
                    return True
                else:
                    logging.error(f"スクリプト '{source_script_path.name}' の実行結果に完了メッセージが見つかりません。")
                    return False
        except subprocess.TimeoutExpired:
            logging.error(f"xEditの実行がタイムアウトしました（10分以上）。")
            return False
        except Exception as e:
            logging.critical(f"xEditの実行中に予期せぬ例外が発生しました: {e}", exc_info=True)
            return False
        finally:
            # --- ★★★ 修正点: finallyブロックでデバッグログを読み込む ---
            # 正常に完了しなかった場合、デバッグログの内容を出力する
            # `return True` で正常終了した場合は、このブロックは実行されない
            if 'xedit_process' in locals() and xedit_process is not None: # MO2モードで実行されたか確認
                log_content = ""
                if session_log_path.is_file():
                    try:
                        log_content = session_log_path.read_text(encoding='utf-8', errors='replace')
                    except Exception:
                        pass # 読み取り失敗は無視
                
                if success_message not in log_content:
                    if debug_log_path.is_file():
                        try:
                            debug_content = debug_log_path.read_text(encoding='utf-8', errors='replace')
                            if debug_content: # 空のログは出力しない
                                logging.error(f"--- xEdit Debug Log ({debug_log_path.name}) ---")
                                logging.error(debug_content.strip())
                                logging.error("--- End of xEdit Debug Log ---")
                        except Exception as e:
                            logging.error(f"デバッグログファイルの読み込みに失敗しました: {e}")


            logging.info("プロセスと一時ファイルをクリーンアップしています...")
            
            # xEditプロセスがまだ生きていれば終了させる
            if xedit_process and xedit_process.is_running():
                try:
                    logging.warning(f"xEditプロセス (PID: {xedit_process.pid}) がまだ実行中のため、強制終了します。")
                    xedit_process.terminate()
                    xedit_process.wait(timeout=5)
                except psutil.Error as e:
                    logging.error(f"xEditプロセスの終了に失敗しました: {e}")

            # MO2プロセスがまだ生きていれば終了させる
            if mo2_process and mo2_process.poll() is None:
                try:
                    logging.info(f"残存しているModOrganizerプロセス (PID: {mo2_process.pid}) を終了します。")
                    mo2_process.terminate()
                    mo2_process.wait(timeout=5) # 終了を待つ
                except Exception as e:
                    logging.error(f"ModOrganizerプロセスの終了に失敗しました: {e}")

            if temp_script_path.exists():
                try:
                    temp_script_path.unlink()
                    logging.info(f" - 削除: {temp_script_path.name}")
                except OSError as e:
                    logging.warning(f"一時ファイル '{temp_script_path.name}' の削除に失敗しました: {e}")
            
            if dest_lib_dir.exists():
                try:
                    shutil.rmtree(dest_lib_dir)
                    logging.info(f" - 削除: lib フォルダ")
                except OSError as e:
                    logging.warning(f"一時フォルダ 'lib' の削除に失敗しました: {e}")

    def run_strategy_generation(self):
        """ammo_categories.jsonのルールに基づき、戦略ファイル(strategy.json)を更新する。"""
        logging.info(f"{'='*20} 戦略ファイル生成処理を開始します {'='*20}")
        try:
            categories_file = self.config.get_path('Paths', 'project_root') / 'ammo_categories.json'
            munitions_id_file = self.config.get_path('Paths', 'output_dir') / 'munitions_ammo_ids.ini'
            strategy_file = self.config.get_path('Paths', 'strategy_file')

            if not munitions_id_file.is_file() or not categories_file.is_file() or not strategy_file.is_file():
                logging.error(f"戦略生成に必要なファイルが見つかりません。")
                if not munitions_id_file.is_file(): logging.error(f" - 見つからないファイル: {munitions_id_file}")
                if not categories_file.is_file(): logging.error(f" - 見つからないファイル: {categories_file}")
                if not strategy_file.is_file(): logging.error(f" - 見つからないファイル: {strategy_file}")
                return False

            with open(categories_file, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            rules = rules_data.get("classification_rules", [])

            parser = configparser.ConfigParser()
            parser.read(munitions_id_file, encoding=locale.getpreferredencoding())
            
            ammo_classification = {}
            if parser.has_section('MunitionsAmmo'):
                for form_id, editor_id in parser.items('MunitionsAmmo'):
                    editor_id_lower = editor_id.lower()
                    found_rule = False
                    for rule in rules:
                        if any(keyword.lower() in editor_id_lower for keyword in rule["keywords"]):
                            ammo_classification[form_id.upper()] = {
                                "Category": rule["Category"],
                                "Power": rule["Power"]
                            }
                            found_rule = True
                            break
                    if not found_rule:
                        logging.warning(f"  - 分類ルールが見つからない弾薬: {editor_id} (FormID: {form_id.upper()})")
            
            with open(strategy_file, 'r', encoding=locale.getpreferredencoding()) as f:
                strategy_data = json.load(f)
            strategy_data["ammo_classification"] = ammo_classification
            with open(strategy_file, 'w', encoding='utf-8') as f:
                json.dump(strategy_data, f, indent=2, ensure_ascii=False)

            logging.info(f"戦略ファイル '{strategy_file.name}' の弾薬分類を正常に更新しました。")
            return True

        except Exception as e:
            logging.critical(f"戦略ファイルの生成中に致命的なエラーが発生しました: {e}", exc_info=True)
            return False

    def _generate_robco_ini(self):
        """
        抽出されたデータ、戦略ファイル、マッピングファイルに基づいて
        最終的な Robco Patcher の weapons.ini を生成する。
        """
        logging.info(f"{'-'*10}ステップ3: Robco Patcher用INIファイルの生成を開始します{'-'*10}")
        try:
            strategy_file = self.config.get_path('Paths', 'strategy_file')
            ammo_map_file = self.config.get_path('Paths', 'ammo_map_file')
            output_dir = self.config.get_path('Paths', 'output_dir')
            weapon_data_file = output_dir / 'weapon_ammo_map.json'
            robco_patcher_dir = self.config.get_path('Paths', 'robco_patcher_dir')
            robco_ini_filename = self.config.get_string('Parameters', 'robco_output_filename')
            output_ini_path = robco_patcher_dir / robco_ini_filename

            required_files = [strategy_file, weapon_data_file]
            for f in required_files:
                if not f.is_file():
                    logging.error(f"INI生成に必要なファイルが見つかりません: {f}")
                    return False
            default_encoding = locale.getpreferredencoding()

            logging.info(f"読み込み中: {strategy_file.name}")
            with open(strategy_file, 'r', encoding=default_encoding) as f:
                strategy_data = json.load(f)

            ammo_map_dict = {}
            if ammo_map_file.is_file():
                logging.info(f"読み込み中: {ammo_map_file.name}")
                ammo_map_parser = configparser.ConfigParser()
                ammo_map_parser.read(ammo_map_file, encoding=default_encoding)
                if ammo_map_parser.has_section('UnmappedAmmo'):
                     ammo_map_dict = {k: v for k, v in ammo_map_parser.items('UnmappedAmmo')}

            logging.info(f"読み込み中: {weapon_data_file.name}")
            with open(weapon_data_file, 'r', encoding=default_encoding) as f:
                weapon_data = json.load(f)

            ini_content = []
            ini_content.append("; Munitions Auto Patcherによって自動生成されました")
            ini_content.append(f"; 生成日時: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            ini_content.append("\n[Settings]\n;\n\n[Leveled List Integration]\n;")

            ammo_classification = strategy_data.get('ammo_classification', {})
            allocation_matrix = strategy_data.get('allocation_matrix', {})
            faction_leveled_lists = strategy_data.get('faction_leveled_lists', {})
            
            logging.info(f"{len(weapon_data)}個の武器定義を処理しています...")
            for weapon in weapon_data:
                original_ammo_formid = weapon['ammo_form_id'].lower()
                final_ammo_formid = ammo_map_dict.get(original_ammo_formid, original_ammo_formid)
                
                ammo_info = ammo_classification.get(final_ammo_formid.upper())
                if not ammo_info:
                    logging.warning(f"  - 武器 '{weapon['editor_id']}' の弾薬カテゴリが見つかりません (Ammo: {final_ammo_formid})。スキップします。")
                    continue
                
                leveled_list_entries = []
                for faction, lli_name in faction_leveled_lists.items():
                    faction_allocations = allocation_matrix.get(faction, {})
                    spawn_chance = faction_allocations.get(ammo_info["Category"])
                    
                    if spawn_chance and spawn_chance > 0:
                        leveled_list_entries.append(f"{lli_name}@{ammo_info['Category']}:{spawn_chance}")
                
                if not leveled_list_entries:
                    continue

                weapon_editor_id_safe = weapon['editor_id'].replace(' ', '_')
                ini_content.append(f"\n[Weapon.{weapon_editor_id_safe}]")
                ini_content.append(f"name = {weapon['full_name']}")
                ini_content.append(f"leveled_lists = {', '.join(leveled_list_entries)}")
                logging.info(f"  - 武器 '{weapon['editor_id']}' を処理しました。カテゴリ: {ammo_info['Category']}")

            robco_patcher_dir.mkdir(parents=True, exist_ok=True)
            with open(output_ini_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(ini_content))

            logging.info(f"正常に '{output_ini_path.name}' を生成しました。")
            return True

        except Exception as e:
            logging.critical(f"Robco Patcher用INIファイルの生成中に致命的なエラーが発生しました: {e}", exc_info=True)
            return False

    def run_full_process(self):
        """全ての自動化プロセスを実行する"""
        logging.info(f"{'='*20} 全自動処理を開始します {'='*20}")
        
        # --- ステップ1: データ抽出 ---
        logging.info(f"{'-'*10}ステップ1: xEditからデータを抽出します{'-'*10}")
        
        if not self.run_xedit_script('weapon_ammo_extractor', '[AutoPatcher] Weapon and ammo mapping extraction complete.'):
            logging.critical("プロセス失敗: 武器/弾薬情報の抽出中にエラーが発生しました。")
            return
        if not self._move_results_from_overwrite(['weapon_ammo_map.json', 'unique_ammo_for_mapping.ini']): return
        
        if not self.run_xedit_script('leveled_list_exporter', '[AutoPatcher] Leveled list export complete.'):
            logging.critical("プロセス失敗: レベルドリストの抽出中にエラーが発生しました。")
            return
        if not self._move_results_from_overwrite(['exported_leveled_lists.json']): return
            
        if not self.run_xedit_script('munitions_id_exporter', '[AutoPatcher] Munitions ammo ID export complete.'):
            logging.critical("プロセス失敗: Munitions弾薬IDの抽出中にエラーが発生しました。")
            return
        if not self._move_results_from_overwrite(['munitions_ammo_ids.ini']): return
        
        logging.info("データ抽出が正常に完了しました。")

        # --- ステップ2: 戦略ファイルの更新 ---
        if not self.run_strategy_generation():
            logging.critical("プロセス失敗: 戦略ファイルの更新中にエラーが発生しました。")
            return

        # --- ステップ3: 弾薬マッピング ---
        logging.info(f"{'-'*10}ステップ3: 弾薬マッピングツールを起動します{'-'*10}")
        logging.info("マッピングが必要な弾薬を確認し、設定後にウィンドウを閉じてください。")
        try:
            mapper_path = self.config.get_path('Paths', 'project_root') / 'mapper.py'
            if not mapper_path.is_file():
                logging.error(f"マッピングツール (mapper.py) が見つかりません: {mapper_path}")
                return

            python_executable = shutil.which("python") or shutil.which("python3")
            if not python_executable:
                logging.error("'python' コマンドが見つかりません。Pythonがインストールされ、PATHが通っているか確認してください。")
                return

            # mapper.py に渡すファイルパスを準備
            output_dir = self.config.get_path('Paths', 'output_dir')
            ammo_file = output_dir / 'unique_ammo_for_mapping.ini'
            munitions_file = output_dir / 'munitions_ammo_ids.ini'
            output_file = self.config.get_path('Paths', 'ammo_map_file')

            command = [
                python_executable,
                str(mapper_path),
                "--ammo-file", str(ammo_file),
                "--munitions-file", str(munitions_file),
                "--output-file", str(output_file)
            ]

            process = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')
            
            if process.returncode != 0:
                logging.error("マッピングツールの実行でエラーが発生しました。")
                logging.error(f"--- mapper.py stderr ---\n{process.stderr}")
                return

            logging.info("マッピングツールが正常に終了しました。")

        except Exception as e:
            logging.critical(f"マッピングツールの起動中に予期せぬエラーが発生しました: {e}", exc_info=True)
            return

        # --- ステップ4: 最終INI生成 ---
        if not self._generate_robco_ini():
            logging.critical("プロセス失敗: 最終的なINIファイルの生成中にエラーが発生しました。")
            return

        logging.info("全てのプロセスが正常に完了しました！")
