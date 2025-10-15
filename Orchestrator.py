from collections import Counter
import csv
import subprocess
import shutil
from pathlib import Path
import logging
import time
import json
import configparser
import locale
import psutil
import shlex
import uuid
from typing import Sequence, Optional, Callable

from robco_ini_generate import run as generate_robco_inis
from admin_check import is_admin, check_directory_access
from utils import read_text_utf8_fallback

class XEditRunner:
    """xEditの実行に関するすべてのロジックをカプセル化するクラス。"""

    def __init__(self, config_manager, script_key: str, success_message: str, expected_outputs: Optional[list[str]] = None):
        self.config = config_manager
        self.script_key = script_key
        self.success_message = success_message
        self.expected_outputs = expected_outputs

        # --- パスの設定 ---
        self.output_dir = self.config.get_path('Paths', 'output_dir')
        self.logs_dir = self.output_dir / 'logs'
        self.intermediate_dir = self.output_dir / 'intermediate'

        self.xedit_executable_path = self.config.get_path('Paths', 'xedit_executable')
        self.xedit_dir = self.xedit_executable_path.parent
        self.edit_scripts_dir = self.xedit_dir / "Edit Scripts"
        self.pas_scripts_dir = self.config.get_path('Paths', 'pas_scripts_dir')
        self.game_data_path = self.config.get_path('Paths', 'game_data_path')
        
        self.env_settings = self.env_settings = self.config.get_env_settings()
        self.use_mo2 = self.env_settings.get('use_mo2', False)
        self.timeout_seconds = self._get_numeric('Parameters', 'xedit_timeout_seconds', 600, int)
        self.log_verification_timeout = self._get_numeric('Parameters', 'log_verification_timeout_seconds', 10, int)
        self.poll_interval = self._get_numeric('Parameters', 'log_poll_interval_seconds', 0.5, float)
        
        # --- 実行中の状態 ---
        self.source_script_path: Path | None = None
        self.temp_script_path: Path | None = None
        self.session_log_path: Path | None = None
        self.lib_backup_dir: Path | None = None
        self.xedit_lib_backup: Path | None = None

    def run(self) -> bool:
        """xEdit実行のメインフローを制御する。"""
        try:
            if not self._prepare_environment(): return False
            command_list = self._build_command()
            if not command_list: return False
            exit_code = self._execute_and_monitor(command_list)
            if not self._verify_execution(exit_code): return False
            if self.expected_outputs and not self._collect_artifacts():
                logging.warning("[XEditRunner] 成果物の収集に失敗しましたが、処理を続行します。")
            return True
        except (subprocess.TimeoutExpired, psutil.TimeoutExpired):
            logging.error(f"[XEditRunner] タイムアウト ({self.timeout_seconds}s 超過)")
            if self.expected_outputs: self._collect_artifacts()
            return False
        except Exception as e:
            logging.critical(f"[XEditRunner] 例外発生: {e}", exc_info=True)
            return False
        finally:
            self._cleanup_environment()

    def _prepare_environment(self) -> bool:
        """xEdit実行前のファイル準備を行う。"""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.intermediate_dir.mkdir(parents=True, exist_ok=True)

        self.source_script_path = self.pas_scripts_dir / self.config.get_script_filename(self.script_key)
        if not self.source_script_path.is_file():
            logging.error(f"[XEditRunner] スクリプト未存在: {self.source_script_path}")
            return False

        if not self._validate_data_path(self.game_data_path):
            return False

        temp_script_filename = f"TEMP_{int(time.time())}_{uuid.uuid4().hex}.pas"
        self.temp_script_path = self.edit_scripts_dir / temp_script_filename
        shutil.copy2(self.source_script_path, self.temp_script_path)
        print(f"TEMP_SCRIPT:{temp_script_filename}")

        self.session_log_path = self.logs_dir / f"xEdit_session_{int(time.time())}.log"
        self._write_debug_files()
        self._backup_and_copy_libs()
        self._copy_pas_units()
        return True

    def _build_command(self) -> Optional[list[str]]:
        """実行するコマンドラインを構築する。"""
        xedit_args = [f"-script:{self.temp_script_path.name}", f"-S:{self.edit_scripts_dir}", "-IKnowWhatImDoing", "-AllowMasterFilesEdit", f"-Log:{self.session_log_path}", f"-R:{self.session_log_path}", "-cache"]
        if self.use_mo2:
            mo2_executable_path = Path(self.env_settings.get('mo2_executable_path', ''))
            profile_name = self.env_settings.get("xedit_profile_name")
            if not (mo2_executable_path.is_file() and profile_name):
                logging.error("[XEditRunner] MO2の実行ファイルまたはプロファイル名が設定されていません。")
                return None
            mo2_entry_name = self.env_settings.get("mo2_xedit_entry_name", "xEdit")
            command_list, _ = self._build_mo2_command(mo2_executable_path, profile_name, mo2_entry_name, xedit_args, self.env_settings)
            return command_list
        else:
            return [str(self.xedit_executable_path), "-FO4" if self.xedit_executable_path.name.lower() == "xedit.exe" else None, *xedit_args, f"-D:{self.game_data_path}"]

    def _execute_and_monitor(self, command_list: list[str]) -> Optional[int]:
        """コマンドを実行し、プロセスを監視して終了コードを返す。"""
        with open(self.session_log_path, 'a', encoding='utf-8', errors='replace') as lf:
            if self.use_mo2:
                mo2_process = subprocess.Popen(command_list, stdout=lf, stderr=lf)
                xedit_ps = self._find_xedit_process()
                if not xedit_ps: return None
                return xedit_ps.wait(timeout=self.timeout_seconds)
            else:
                return subprocess.run(command_list, stdout=lf, stderr=lf, timeout=self.timeout_seconds).returncode

    def _verify_execution(self, exit_code: Optional[int]) -> bool:
        """実行の成否を判定する。"""
        if exit_code != 0:
            logging.error(f"[XEditRunner] 失敗: exit code={exit_code}")
            return False
        if not self._find_success_in_logs():
            logging.warning("[XEditRunner] ログに成功メッセージが見つかりません。")
            return self.expected_outputs and self._check_artifacts_exist()
        return True

    def _collect_artifacts(self) -> bool:
        """生成されたファイルを成果物として収集する。"""
        return self._move_results_from_overwrite(self.expected_outputs)

    def _cleanup_environment(self):
        """一時ファイルやバックアップをクリーンアップする。"""
        if str(self.config.get_string('Environment', 'keep_temp_scripts', 'false')).lower() not in ('1', 'true', 'yes'):
            if self.temp_script_path and self.temp_script_path.exists(): self.temp_script_path.unlink()
        if self.lib_backup_dir and self.lib_backup_dir.exists(): shutil.move(str(self.lib_backup_dir), str(self.edit_scripts_dir / 'lib'))
        if self.xedit_lib_backup and self.xedit_lib_backup.exists(): shutil.move(str(self.xedit_lib_backup), str(self.xedit_dir / 'lib'))

    def _get_numeric(self, section: str, option: str, default, cast: Callable):
        try: return cast(self.config.get_string(section, option)) or default
        except: return default

    def _validate_data_path(self, path: Path) -> bool:
        if not path.is_dir() or not (path / "Fallout4.esm").is_file():
            logging.error(f"[XEditRunner] DataパスまたはFallout4.esmが見つかりません: {path}")
            return False
        return True

    def _build_mo2_command(self, mo2_path: Path, profile: str, entry: str, args: list[str], env: dict) -> tuple[list[str], str]:
        fmt, inst = env.get("mo2_shortcut_format", "auto"), env.get("mo2_instance_name", "")
        uri = f"moshortcut://{inst}/{entry}" if fmt == "instance" and inst else f"moshortcut://:{entry}" if fmt == "with_colon" else f"moshortcut://{entry}"
        return [str(mo2_path), "-p", profile, uri, *args], uri

    def _move_results_from_overwrite(self, filenames: Sequence[str]) -> bool:
        """xEditの出力先から中間ディレクトリへ成果物をコピーする。"""
        if not check_directory_access(self.intermediate_dir, check_write=True): return False
        candidates = self._candidate_output_dirs()
        if not candidates: return False
        all_found = True
        for filename in filenames:
            paths = [p for c in candidates if (p := c / filename).is_file()]
            if not paths: all_found = False; logging.error(f"[XEditRunner] 成果物が見つかりません: {filename}"); continue
            try: shutil.copy2(max(paths, key=lambda p: p.stat().st_mtime), self.intermediate_dir / filename)
            except Exception as e: all_found = False; logging.error(f"[XEditRunner] 成果物のコピーに失敗: {filename}: {e}")
        return all_found

    def _candidate_output_dirs(self) -> list[Path]:
        dirs = [self.output_dir, self.intermediate_dir, self.xedit_dir / 'Edit Scripts' / 'Output']
        try: dirs.append(self.config.get_path('Paths', 'overwrite_path') / 'Edit Scripts' / 'Output')
        except: pass
        seen = set()
        return [d for d in dirs if d and d.exists() and (k := str(d.resolve()).lower()) not in seen and not seen.add(k)]

    def _find_xedit_process(self) -> Optional[psutil.Process]:
        name = self.xedit_executable_path.name.lower()
        end_time = time.time() + self.timeout_seconds
        while time.time() < end_time:
            for p in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    if p.info['name'].lower() == name and p.info['create_time'] > (time.time() - 10):
                        return psutil.Process(p.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied): continue
            time.sleep(0.5)
        return None

    def _find_success_in_logs(self) -> bool:
        end_time = time.time() + self.log_verification_timeout
        while time.time() < end_time:
            if self.session_log_path.is_file():
                try:
                    if self.success_message in self.session_log_path.read_text(encoding='utf-8', errors='replace'): return True
                except: pass
            time.sleep(self.poll_interval)
        return False
    
    def _check_artifacts_exist(self) -> bool:
        return all(any((d / fn).is_file() for d in self._candidate_output_dirs()) for fn in self.expected_outputs)

    def _write_debug_files(self):
        try:
            shutil.copy2(self.temp_script_path, self.intermediate_dir / f"copied_temp_{self.temp_script_path.name}")
            (self.intermediate_dir / f"temp_inspect_{self.temp_script_path.name}.txt").write_text(f"source={self.source_script_path}\nexists={self.source_script_path.exists()}")
        except Exception as e: logging.warning(f"[XEditRunner] デバッグ用ファイルの書き出しに失敗: {e}")

    def _copy_pas_units(self):
        for p in self.pas_scripts_dir.glob('*.pas'):
            if not p.samefile(self.source_script_path) and not (self.edit_scripts_dir / p.name).exists():
                shutil.copy2(p, self.edit_scripts_dir / p.name)

    def _backup_and_copy_libs(self):
        source_lib_dir = self.pas_scripts_dir / 'lib'
        if not source_lib_dir.is_dir(): return
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        for lib_path in [self.edit_scripts_dir / 'lib', self.xedit_dir / 'lib']:
            if lib_path.exists():
                backup = lib_path.parent / f"_lib_backup_{timestamp}_{lib_path.name}"
                shutil.move(str(lib_path), str(backup))
                if lib_path == self.edit_scripts_dir / 'lib': self.lib_backup_dir = backup
                else: self.xedit_lib_backup = backup
            shutil.copytree(source_lib_dir, lib_path, dirs_exist_ok=True)

class Orchestrator:
    """全自動パッチ処理のオーケストレータ。"""

    def __init__(self, config_manager):
        self.config = config_manager
        if not is_admin():
            logging.warning("管理者権限で実行されていません。ファイルの移動やコピーが失敗する可能性があります。")

    def run_xedit_script(self, script_key: str, success_message: str, expected_outputs: Optional[list[str]] = None) -> bool:
        try:
            runner = XEditRunner(self.config, script_key, success_message, expected_outputs)
            return runner.run()
        except Exception as e:
            logging.critical(f"[Orchestrator] XEditRunnerの初期化または実行中に致命的なエラー: {e}", exc_info=True)
            return False

    def run_strategy_generation(self) -> bool:
        logging.info("戦略ファイル生成処理開始")
        try:
            output_dir = self.config.get_path('Paths', 'output_dir')
            intermediate_dir = output_dir / 'intermediate'
            categories_file = self.config.get_path('Paths', 'ammo_categories_file')
            munitions_id_file = intermediate_dir / 'munitions_ammo_ids.ini'
            strategy_file = self.config.get_path('Paths', 'strategy_file')

            if not all(p.is_file() for p in [categories_file, munitions_id_file, strategy_file]):
                logging.error("[Strategy] 戦略生成に必要なファイルが不足しています。")
                return False

            rules = json.loads(read_text_utf8_fallback(categories_file)).get("classification_rules", [])
            parser = configparser.ConfigParser()
            parser.read(munitions_id_file, encoding='utf-8')

            ammo_classification = {}
            if parser.has_section('MunitionsAmmo'):
                for form_id, editor_id in parser.items('MunitionsAmmo'):
                    eid_lower = editor_id.lower()
                    for rule in rules:
                        if any(kw.lower() in eid_lower for kw in rule["keywords"]):
                            ammo_classification[form_id.upper()] = {"Category": rule["Category"], "Power": rule["Power"]}
                            break
            
            strategy_data = json.loads(read_text_utf8_fallback(strategy_file))
            strategy_data["ammo_classification"] = ammo_classification
            strategy_file.write_text(json.dumps(strategy_data, indent=2, ensure_ascii=False), encoding='utf-8')
            logging.info(f"[Strategy] 更新完了: {strategy_file.name}")
            return True
        except Exception as e:
            logging.critical(f"[Strategy] 例外発生: {e}", exc_info=True)
            return False

    def _generate_robco_ini(self) -> bool:
        return generate_robco_inis(self.config)
    
    def run_full_process(self) -> bool:
        """全自動フローを実行。"""
        logging.info("全自動処理開始")

        logging.info("ステップ1: xEdit 抽出")
        if not self.run_xedit_script('all_extractors', '[AutoPatcher] All extractions complete.', [
            'weapon_omod_map.json', 'weapon_ammo_map.json', 'unique_ammo_for_mapping.ini',
            'WeaponLeveledLists_Export.csv', 'munitions_ammo_ids.ini'
        ]):
            logging.critical("[Main] xEditによるデータ抽出に失敗しました。")
            return False

        logging.info("ステップ2: 戦略ファイル更新")
        if not self.run_strategy_generation():
            logging.critical("[Main] 戦略ファイル更新失敗")
            return False

        logging.info("ステップ3: マッピングツール起動")
        try:
            output_dir = self.config.get_path('Paths', 'output_dir')
            intermediate_dir = output_dir / 'intermediate'
            cmd = [
                shutil.which("python") or "python",
                str(self.config.get_path('Paths', 'project_root') / 'mapper.py'),
                "--ammo-file", str(intermediate_dir / 'unique_ammo_for_mapping.ini'),
                "--munitions-file", str(intermediate_dir / 'munitions_ammo_ids.ini'),
                "--output-file", str(self.config.get_path('Paths', 'ammo_map_file'))
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if proc.returncode != 0:
                logging.error(f"[Main] mapper.py 実行エラー\n{proc.stderr}")
                return False
        except Exception as e:
            logging.critical(f"[Main] マッピングツール起動例外: {e}", exc_info=True)
            return False

        logging.info("ステップ4: 最終INI生成")
        if not self._generate_robco_ini():
            logging.critical("[Main] 最終 INI 生成失敗")
            return False

        logging.info("全工程正常完了")
        return True
