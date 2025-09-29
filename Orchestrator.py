# =============================================================================
# Munitions 自動統合フレームワーク v2.5
#
# Orchestrator.py
#
# 変更履歴:
# v2.5 (2025-09-29):
#   - subprocess.runに `timeout` パラメータを追加。大規模なMOD環境でxEditの
#     プラグイン読み込みがタイムアウトするのを防ぐため、待ち時間を600秒(10分)に延長。
# =============================================================================

import subprocess
import os
import shutil
from pathlib import Path
from config_manager import ConfigManager
import logging
import time
import json
import configparser

class Orchestrator:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
    
    def run_xedit_script(self, script_key: str, success_message: str) -> bool:
        """
        指定されたスクリプトをxEditで実行し、ログから成功メッセージを探す。
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

        # 'lib' フォルダのパスを 'pas_scripts_dir' の中にあると想定
        source_lib_dir = self.config.get_path('Paths', 'pas_scripts_dir') / 'lib'
        dest_lib_dir = edit_scripts_dir / 'lib'
        temp_script_filename = f"TEMP_{int(time.time())}.pas"
        temp_script_path = edit_scripts_dir / temp_script_filename
        
        try:
            logging.info(f"スクリプト '{source_script_path.name}' を '{temp_script_filename}' として準備しています...")
            shutil.copy2(source_script_path, temp_script_path)

            if source_lib_dir.is_dir():
                logging.info(f"ライブラリフォルダ '{source_lib_dir.name}' を準備しています...")
                if dest_lib_dir.exists():
                    shutil.rmtree(dest_lib_dir)
                shutil.copytree(source_lib_dir, dest_lib_dir)

            env_settings = self.config.get_env_settings()
            command = []
            if env_settings.get('use_mo2', False):
                command.extend([
                    f'"{env_settings["mo2_executable_path"]}"',
                    '-p',
                    f'"{env_settings["xedit_profile_name"]}"'
                ])
            
            command.extend([
                f'"{xedit_executable_path}"',
                '-force',
                '-IKnowWhatImDoing',
                '-AllowMasterFilesEdit',
                f"-script:{temp_script_filename}"
            ])

            final_command = " ".join(command)
            logging.info(f"コマンドを実行します: {final_command}")
            
            # タイムアウトを600秒（10分）に設定
            process = subprocess.run(final_command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)

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
                if process.stderr:
                    logging.error("--- xEdit stderr ---")
                    for line in process.stderr.strip().splitlines():
                        logging.error(line)
                    logging.error("--- xEdit stderr end ---")
                return False

        except subprocess.TimeoutExpired:
            logging.error(f"xEditの実行がタイムアウトしました（10分以上）。MODの数が多いか、PCのスペックが影響している可能性があります。")
            return False
        except Exception as e:
            logging.critical(f"xEditの実行中に予期せぬ例外が発生しました: {e}", exc_info=True)
            return False
        finally:
            logging.info("一時ファイルをクリーンアップしています...")
            if temp_script_path.exists():
                try:
                    temp_script_path.unlink()
                    logging.info(f"  - 削除: {temp_script_path.name}")
                except OSError as e:
                    logging.warning(f"一時ファイル '{temp_script_path.name}' の削除に失敗しました: {e}")
            
            if dest_lib_dir.exists():
                try:
                    shutil.rmtree(dest_lib_dir)
                    logging.info(f"  - 削除: lib フォルダ")
                except OSError as e:
                    logging.warning(f"一時フォルダ 'lib' の削除に失敗しました: {e}")

    def run_strategy_generation(self):
        """00スクリプトのみを実行して戦略ファイルを生成する"""
        logging.info(f"{'='*20} 戦略ファイル生成処理を開始します {'='*20}")
        if self.run_xedit_script('strategy_generator', '[AutoPatcher] Strategy JSON generation complete.'):
            logging.info("戦略ファイルの生成が正常に完了しました。")
        else:
            logging.critical("プロセス失敗: 'strategy_generator' の実行中にエラーが発生しました。")

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

            logging.info(f"読み込み中: {strategy_file.name}")
            with open(strategy_file, 'r', encoding='utf-8') as f:
                strategy_data = json.load(f)

            ammo_map_dict = {}
            if ammo_map_file.is_file():
                logging.info(f"読み込み中: {ammo_map_file.name}")
                ammo_map_parser = configparser.ConfigParser()
                ammo_map_parser.read(ammo_map_file, encoding='utf-8')
                if ammo_map_parser.has_section('UnmappedAmmo'):
                     ammo_map_dict = {k: v for k, v in ammo_map_parser.items('UnmappedAmmo')}

            logging.info(f"読み込み中: {weapon_data_file.name}")
            with open(weapon_data_file, 'r', encoding='utf-8') as f:
                weapon_data = json.load(f)

            ini_content = []
            ini_content.append("; Munitions Auto Patcherによって自動生成されました")
            ini_content.append(f"; 生成日時: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            ini_content.append("\n[Settings]\n;\n\n[Leveled List Integration]\n;")

            ammo_classification = strategy_data.get('ammo_classification', {})
            allocation_matrix = strategy_data.get('allocation_matrix', {})
            faction_leveled_lists = strategy_data.get('faction_leveled_lists', {})
            
            logging.info(f"{len(weapon_data)}個の武器を処理しています...")
            for weapon in weapon_data:
                original_ammo_formid = weapon['ammo_form_id'].lower()
                final_ammo_formid = ammo_map_dict.get(original_ammo_formid, original_ammo_formid)
                
                ammo_category = ammo_classification.get(final_ammo_formid)
                if not ammo_category:
                    logging.warning(f"  - 武器 '{weapon['editor_id']}' の弾薬カテゴリが見つかりません (Ammo: {final_ammo_formid})。スキップします。")
                    continue
                
                leveled_list_entries = []
                for faction, lli_name in faction_leveled_lists.items():
                    faction_allocations = allocation_matrix.get(faction, {})
                    spawn_chance = faction_allocations.get(ammo_category)
                    
                    if spawn_chance and spawn_chance > 0:
                        leveled_list_entries.append(f"{lli_name}@{ammo_category}:{spawn_chance}")
                
                if not leveled_list_entries:
                    continue

                weapon_editor_id_safe = weapon['editor_id'].replace(' ', '_')
                ini_content.append(f"\n[Weapon.{weapon_editor_id_safe}]")
                ini_content.append(f"name = {weapon['full_name']}")
                ini_content.append(f"leveled_lists = {', '.join(leveled_list_entries)}")
                logging.info(f"  - 武器 '{weapon['editor_id']}' を処理しました。カテゴリ: {ammo_category}")

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
        
        logging.info(f"{'-'*10}ステップ1: データ抽出を開始します{'-'*10}")
        if not self.run_xedit_script('weapon_ammo_extractor', '[AutoPatcher] Weapon and ammo mapping extraction complete.'):
            logging.critical("プロセス失敗: 武器/弾薬情報の抽出中にエラーが発生しました。")
            return

        if not self.run_xedit_script('leveled_list_exporter', '[AutoPatcher] Leveled list export complete.'):
            logging.critical("プロセス失敗: レベルドリストの抽出中にエラーが発生しました。")
            return
            
        if not self.run_xedit_script('munitions_id_exporter', '[AutoPatcher] Munitions ammo ID export complete.'):
            logging.critical("プロセス失敗: Munitions弾薬IDの抽出中にエラーが発生しました。")
            return
        
        logging.info("データ抽出が正常に完了しました。")

        logging.info(f"{'-'*10}ステップ2: 弾薬マッピングツールを起動します{'-'*10}")
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

            process = subprocess.run([python_executable, str(mapper_path)], capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')
            
            if process.returncode != 0:
                logging.error("マッピングツールの実行でエラーが発生しました。")
                logging.error(f"--- mapper.py stderr ---\n{process.stderr}")
                return

            logging.info("マッピングツールが正常に終了しました。")

        except Exception as e:
            logging.critical(f"マッピングツールの起動中に予期せぬエラーが発生しました: {e}", exc_info=True)
            return
            
        if not self._generate_robco_ini():
            logging.critical("プロセス失敗: 最終的なINIファイルの生成中にエラーが発生しました。")
            return

        logging.info("全てのプロセスが正常に完了しました！")

