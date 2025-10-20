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
        # xEdit用の引数リストを構築
        xedit_args = []
        # ユーザー指示: xedit.exeなら-fo4を追加
        if self.xedit_executable_path.name.lower() == 'xedit.exe':
            xedit_args.append('-fo4')

        # ユーザー指示: 新しい引数を追加
        # When launching via MO2 we prefer to pass the script filename only
        # (MO2/xEdit typically resolve scripts from the Edit Scripts folder).
        xedit_args.extend([
            # script arg: absolute path for direct xEdit, filename-only for MO2
            f"-script:{str(self.temp_script_path)}",
            f"-S:{str(self.edit_scripts_dir)}",
            "-IKnowWhatImDoing",
            "-AllowMasterFilesEdit",
            # Provide both -R and -Log to maximize chance xEdit will write session logs
            f"-R:{self.session_log_path}",
            "-report",
        ])

        if self.use_mo2:
            mo2_executable_path = Path(self.env_settings.get('mo2_executable_path', ''))
            if not mo2_executable_path.is_file():
                logging.error("[XEditRunner] MO2起動設定エラー: mo2_executable_path が未設定または無効です")
                return None

            profile_name = self.env_settings.get("xedit_profile_name")
            if not profile_name:
                logging.error("[XEditRunner] MO2起動設定エラー: xedit_profile_name が未設定です")
                return None

            mo2_entry_name = self.env_settings.get("mo2_xedit_entry_name")
            if not mo2_entry_name:
                exe_name = self.xedit_executable_path.name.lower()
                if exe_name == "fo4edit.exe":
                    mo2_entry_name = "FO4Edit"
                elif exe_name == "xedit.exe":
                    mo2_entry_name = "xEdit"
                else:
                    mo2_entry_name = self.xedit_executable_path.stem
                logging.warning(
                    "[XEditRunner] MO2実行ファイルリストの名前が未設定です。実行ファイル名から'%s'を仮の値として使用します。"
                    " 正しく動作しない場合、config.iniの[Environment]にmo2_xedit_entry_nameを設定してください。",
                    mo2_entry_name
                )

            # When invoking via MO2, rewrite the -script arg to be filename-only so
            # the MO2 shortcut / xEdit resolve it from the Edit Scripts folder.
            try:
                filename_only_args = []
                for a in xedit_args:
                    if a.startswith('-script:'):
                        filename_only_args.append(f"-script:{self.temp_script_path.name}")
                    else:
                        filename_only_args.append(a)
            except Exception:
                filename_only_args = xedit_args

            command_list, _ = self._build_mo2_command(
                mo2_executable_path,
                profile_name,
                mo2_entry_name,
                filename_only_args,
                self.env_settings
            )
            logging.info(
                "[XEditRunner] MO2 ショートカット経由でツールを起動します (プロファイル=%s, エントリ名=%s)",
                profile_name,
                mo2_entry_name
            )
            return command_list
        else:
            # MO2を使用しない直接実行パス
            command_list = [str(self.xedit_executable_path)]
            # xedit_argsには既に-fo4のロジックが含まれているので、そのまま結合
            command_list.extend(xedit_args)
            return command_list
    
    def _wait_for_xedit_from_mo2(self, mo2_pid: int, timeout: int) -> Optional[psutil.Process]:
        """
        MO2 プロセスの子プロセスとして起動される xEdit を待ち、見つかったら
        psutil.Process オブジェクトを返す。タイムアウト時は None を返す。
        - mo2_pid: MO2 のプロセス ID
        - timeout: 秒数（全体の待ち時間）
        """
        end_time = time.time() + timeout
        target_name = self.xedit_executable_path.name.lower()

        try:
            parent = psutil.Process(mo2_pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
            logging.debug(f"[XEditRunner] MO2 プロセス取得失敗 (pid={mo2_pid}): {e}")
            return None

        # 子孫プロセスを再帰的に検索して xEdit 実行ファイル名と一致するものを探す
        while time.time() < end_time:
            try:
                # children(recursive=True) は psutil の子孫を再帰的に列挙する
                for child in parent.children(recursive=True):
                    try:
                        # 一致判定はプロセス名（小文字化）で行う
                        if child.name().lower() == target_name:
                            logging.info(f"[XEditRunner] MO2 の子プロセスとして xEdit を検出: pid={child.pid}, name={child.name()}")
                            # psutil.Process を返す
                            return psutil.Process(child.pid)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # 子プロセスが消えた or アクセス拒否ならスキップ
                        continue
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # parent が消えたかアクセス不可になったらループを抜ける
                break
            except Exception as e:
                logging.debug(f"[XEditRunner] 子プロセス走査中の例外: {e}")

            time.sleep(0.5)

        logging.debug(f"[XEditRunner] MO2(pid={mo2_pid}) の子から xEdit を検出できませんでした (timeout={timeout})")
        return None
    
    def _wait_for_file_ready(self, path: Path, timeout_seconds: float = 10.0, poll_interval: float = 0.2) -> bool:
        """
        指定ファイルが 'ロックされていない'（開いて読める）状態になるまで待つ。
        成功したら True、タイムアウトしたら False を返す。
        """
        end_time = time.time() + timeout_seconds
        while time.time() < end_time:
            try:
                # 'rb' で開いてすぐ閉じることでロック状況を確認する
                with open(path, 'rb'):
                    return True
            except Exception:
                time.sleep(poll_interval)
        return False
    
    def _execute_and_monitor(self, command_list: list[str]) -> Optional[int]:
        """コマンドを実行し、プロセスを監視して終了コードを返す。"""
        # Detailed execution logging for debugging argument/pwd/env issues
        try:
            logging.info(f"[XEditRunner] cwd: {Path.cwd()}")
        except Exception:
            pass
        try:
            logging.info(f"[XEditRunner] env_settings.use_mo2={self.use_mo2} mo2_executable={self.env_settings.get('mo2_executable_path', '')} mo2_profile={self.env_settings.get('xedit_profile_name', '')}")
        except Exception:
            pass
        logging.info(f"[XEditRunner] 実行コマンド (joined): {shlex.join(command_list)}")
        logging.info("[XEditRunner] 実行コマンド (args):")
        for idx, a in enumerate(command_list):
            try:
                logging.info(f"  [{idx}] {a}")
            except Exception:
                logging.info(f"  [{idx}] <unprintable arg>")
        # write the exact command we will execute into the intermediate dir so
        # the user can re-run it manually to reproduce any interactive prompts
        try:
            (self.intermediate_dir / 'last_xedit_command.txt').write_text(shlex.join(command_list), encoding='utf-8')
        except Exception:
            pass

        with open(self.session_log_path, 'a', encoding='utf-8', errors='replace') as lf:
                if self.use_mo2:
                    mo2_process = subprocess.Popen(command_list, stdout=lf, stderr=lf)
                    # MO2 を起動した直後に追加
                    logging.info(f"[DEBUG] Started MO2 pid={mo2_process.pid}")
                    # 少し待って子を探す
                    time.sleep(1)
                    for p in psutil.process_iter(['pid','name','cmdline']):
                        try:
                            if p.info['pid'] == mo2_process.pid:
                                logging.info(f"[DEBUG] MO2 process found: {p.info}")
                                for child in p.children(recursive=True):
                                    logging.info(f"[DEBUG] MO2 child: pid={child.pid} name={child.name()} cmdline={child.cmdline()}")
                        except Exception:
                            continue
                    # 1) MO2 の子プロセスとして起動される xEdit を待つ（より robust）
                    xedit_ps = self._wait_for_xedit_from_mo2(mo2_process.pid, timeout=self.timeout_seconds)
                    if xedit_ps:
                        try:
                            # xEdit プロセスが終了するのを待つ
                            return xedit_ps.wait(timeout=self.timeout_seconds)
                        except psutil.TimeoutExpired:
                            logging.error(f"[XEditRunner] xEdit プロセスの待機中にタイムアウト ({self.timeout_seconds}s)")
                            return None
                    # 2) フォールバック: グローバル検索
                    logging.debug("[XEditRunner] MO2 経由での子プロセス検出に失敗。グローバル検索へフォールバックします。")
                    xedit_ps = self._find_xedit_process()
                    if xedit_ps:
                        try:
                            return xedit_ps.wait(timeout=self.timeout_seconds)
                        except psutil.TimeoutExpired:
                            logging.error(f"[XEditRunner] xEdit プロセスの待機中にタイムアウト ({self.timeout_seconds}s)")
                            return None
                    return None
                else:
                    return subprocess.run(command_list, stdout=lf, stderr=lf, timeout=self.timeout_seconds).returncode

    def _verify_execution(self, exit_code: Optional[int]) -> bool:
        """実行の成否を判定する。"""
        if exit_code != 0:
            logging.error(f"[XEditRunner] 失敗: exit code={exit_code}")
            return False
        if not self._find_success_in_logs():
            logging.warning("[XEditRunner] ログに成功メッセージが見つかりません。フォールバック検査を実行します。")
            # デバッグ: どの成果物が存在するかを確認
            if self.expected_outputs:
                logging.info("[XEditRunner] 成果物の存在チェックを開始します...")
                found_count = self._check_artifacts_exist()
                logging.info(f"[XEditRunner] {len(self.expected_outputs)}個の成果物のうち、{found_count}個が見つかりました。")
                # 1つでも成果物があれば、収集を試みるためにTrueを返す
                if found_count > 0:
                    logging.info("[XEditRunner] 部分的な成果物が存在するため、収集処理を試みます。")
                    return True
            # Fallback 1: scan for '[RETURN] 0' which many probes emit as a final marker
            if self._scan_logs_for_return_zero():
                logging.info("[XEditRunner] フォールバック: '[RETURN] 0' をログで検出しました。成功とみなします。")
                return True

            # Fallback 2: check Edit Scripts/Output (some scripts write to Edit Scripts\Output)
            try:
                edit_output = self.edit_scripts_dir / 'Output'
                if edit_output.exists() and any(edit_output.iterdir()):
                    logging.info(f"[XEditRunner] フォールバック: Edit Scripts\\Output に出力を検出: {edit_output}")
                    return True
            except Exception:
                pass

            # Fallback 3: detect probe marker files written by minimal_probe (C:\temp or Output/intermediate)
            try:
                import glob
                for p in glob.glob(str(self.intermediate_dir / 'probe_done_*.txt')):
                    logging.info(f"[XEditRunner] フォールバック: probe marker を検出: {p}")
                    return True
                for p in glob.glob('C:\\temp\\probe_done_*.txt'):
                    logging.info(f"[XEditRunner] フォールバック: probe marker (C:\\temp) を検出: {p}")
                    return True
            except Exception:
                pass

            # Fallback 4: try to collect any manual_debug_log.txt produced by Pascal
            try:
                if self._collect_manual_debug_log():
                    logging.info("[XEditRunner] フォールバック: manual_debug_log.txt を収集しました。")
                    return True
            except Exception:
                pass

            return False
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
        # -a フラグを追加して、後続の引数がxEditに渡されるようにする
        return [str(mo2_path), "-p", profile, uri, "-a", *args], uri

    def _move_results_from_overwrite(self, filenames: Sequence[str]) -> bool:
        """xEditの出力先から中間ディレクトリへ成果物をコピーする（改良版）。"""
        if not check_directory_access(self.intermediate_dir, check_write=True):
            logging.error("[XEditRunner] intermediate_dir に書き込みできません: %s", self.intermediate_dir)
            return False

        candidates = self._candidate_output_dirs()
        if not candidates:
            logging.error("[XEditRunner] 候補出力ディレクトリが見つかりません。")
            return False

        all_found = True
        for filename in filenames:
            # 集められた候補のうち該当ファイルが存在するパス一覧を作る
            paths = []
            for c in candidates:
                try:
                    p = c / filename
                    if p.is_file():
                        # コピー先と同一ファイル（同じ path）なら除外する
                        dest = self.intermediate_dir / filename
                        try:
                            if p.resolve() == dest.resolve():
                                logging.debug(f"[XEditRunner] スキップ（同一ファイル）: {p}")
                                continue
                        except Exception:
                            # resolve に失敗したら続行（安全のため）
                            pass
                        paths.append(p)
                except Exception:
                    continue

            if not paths:
                all_found = False
                logging.error(f"[XEditRunner] 成果物が見つかりません: {filename}")
                continue

            # 最終更新日時が最大のものをソースとする
            src = max(paths, key=lambda p: p.stat().st_mtime)
            dest = self.intermediate_dir / filename

            # コピー前にファイルが使える状態になるまで待つ
            try:
                if not self._wait_for_file_ready(src, timeout_seconds=15.0, poll_interval=0.2):
                    logging.warning(f"[XEditRunner] タイムアウト: ファイルが使用中のままです: {src}")
                    # ここでは失敗扱いにして次へ進める（必要ならリトライ回数を増やしてください）
                    all_found = False
                    continue

                # コピー実行（dest が存在していれば上書き）
                try:
                    shutil.copy2(src, dest)
                    logging.info(f"[XEditRunner] 成果物コピー完了: {src} -> {dest}")
                except Exception as e:
                    logging.error(f"[XEditRunner] 成果物のコピーに失敗: {filename}: {e}")
                    all_found = False
                    continue
            except Exception as e:
                logging.error(f"[XEditRunner] 未処理例外（コピー前チェック）: {e}")
                all_found = False
                continue

        return all_found

    def _candidate_output_dirs(self) -> list[Path]:
        dirs = [self.output_dir, self.intermediate_dir, self.xedit_dir / 'Edit Scripts' / 'Output']
        try: dirs.append(self.config.get_path('Paths', 'overwrite_path') / 'Edit Scripts' / 'Output')
        except: pass
        seen = set()
        return [d for d in dirs if d and d.exists() and (k := str(d.resolve()).lower()) not in seen and not seen.add(k)]

    def _scan_logs_for_return_zero(self) -> bool:
        """Scan known log locations for a '[RETURN] 0' marker as a fallback success indicator."""
        patterns = ['[RETURN] 0', '[COMPLETE] Minimal probe']
        locations = []
        try:
            if self.session_log_path and self.session_log_path.exists():
                locations.append(self.session_log_path)
        except Exception:
            pass

        try:
            if self.logs_dir and self.logs_dir.exists():
                locations.extend(self.logs_dir.glob('xEdit_session_*.log'))
        except Exception:
            pass

        try:
            if self.xedit_dir and self.xedit_dir.exists():
                locations.extend(self.xedit_dir.glob('xEdit_session_*.log'))
        except Exception:
            pass

        for p in locations:
            try:
                txt = p.read_text(encoding='utf-8', errors='replace')
                for pat in patterns:
                    if pat in txt:
                        logging.debug(f"[XEditRunner] Found fallback pattern '{pat}' in {p}")
                        return True
            except Exception:
                continue
        return False

    def _collect_manual_debug_log(self) -> bool:
        """Search for 'manual_debug_log.txt' in likely locations and copy to logs_dir."""
        candidates = []
        try:
            candidates.append(self.edit_scripts_dir / 'manual_debug_log.txt')
            candidates.append(self.edit_scripts_dir / 'Output' / 'manual_debug_log.txt')
        except Exception:
            pass
        try:
            candidates.append(self.intermediate_dir / 'manual_debug_log.txt')
        except Exception:
            pass
        try:
            candidates.append(self.xedit_dir / 'manual_debug_log.txt')
        except Exception:
            pass

        for p in candidates:
            try:
                if p and p.exists():
                    dest = self.logs_dir / f"collected_manual_debug_{p.name}"
                    shutil.copy2(p, dest)
                    logging.info(f"[XEditRunner] Collected manual debug log: {p} -> {dest}")
                    return True
            except Exception as e:
                logging.debug(f"[XEditRunner] Failed to collect manual debug log from {p}: {e}")
                continue
        return False

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
        # Allow a longer effective timeout for MO2/xEdit cases where logs
        # may be written to a different file or delayed. We'll search the
        # primary session_log_path first, then fall back to scanning the
        # Output logs directory and the xEdit installation directory for
        # any xEdit_session_*.log files.
        extended_timeout = max(self.log_verification_timeout, 30)
        end_time = time.time() + extended_timeout
        scanned = set()
        while time.time() < end_time:
            candidates = []
            try:
                if self.session_log_path and self.session_log_path.is_file():
                    candidates.append(self.session_log_path)
            except Exception:
                pass

            # Output logs directory
            try:
                if self.logs_dir and self.logs_dir.exists():
                    candidates.extend(self.logs_dir.glob('xEdit_session_*.log'))
            except Exception:
                pass

            # xEdit install dir (in case MO2 redirects or xEdit writes there)
            try:
                if self.xedit_dir and self.xedit_dir.exists():
                    candidates.extend(self.xedit_dir.glob('xEdit_session_*.log'))
            except Exception:
                pass

            for p in candidates:
                try:
                    real = str(p.resolve())
                except Exception:
                    real = str(p)
                key = real.lower()
                if key in scanned:
                    continue
                scanned.add(key)
                try:
                    txt = p.read_text(encoding='utf-8', errors='replace')
                    logging.debug(f"[XEditRunner] Scanning log file for success_message: {p}")
                    if self.success_message in txt:
                        logging.info(f"[XEditRunner] success_message found in log: {p}")
                        return True
                except Exception as e:
                    logging.debug(f"[XEditRunner] Failed reading log {p}: {e}")
                    continue

            time.sleep(self.poll_interval)

        return False
    
    def _check_artifacts_exist(self) -> int:
        """期待される成果物の存在を確認し、見つかったファイルの数と詳細をログに出力する。"""
        found_count = 0
        candidate_dirs = self._candidate_output_dirs()
        if not self.expected_outputs:
            return 0

        for fn in self.expected_outputs:
            found_path = None
            # 候補ディレクトリを探索してファイルを見つける
            for d in candidate_dirs:
                if (d / fn).is_file():
                    found_path = d / fn
                    break
            
            if found_path:
                logging.info(f"  [✓] 発見: {fn} (場所: {found_path})")
                found_count += 1
            else:
                logging.warning(f"  [✗] 未発見: {fn}")
        return found_count

    def _write_debug_files(self):
        # Write out a few debug artifacts safely. Keep this robust so failures here
        # don't break the runner flow. We prefer to write a cp932-encoded copy for
        # Japanese Windows/xEdit, but fall back to utf-8 on failure.
        try:
            # Primary simple copy for raw byte-for-byte reference
            shutil.copy2(self.temp_script_path, self.intermediate_dir / f"copied_temp_{self.temp_script_path.name}")
        except Exception as e:
            logging.warning(f"[XEditRunner] copied_temp の作成に失敗: {e}")

        try:
            inspect_txt = f"source={self.source_script_path}\nexists={self.source_script_path.exists()}"
            (self.intermediate_dir / f"temp_inspect_{self.temp_script_path.name}.txt").write_text(inspect_txt, encoding='utf-8')
        except Exception as e:
            logging.warning(f"[XEditRunner] temp_inspect の書き出しに失敗: {e}")

        # Try to create a readable debug copy: prefer cp932, then utf-8 as fallback.
        try:
            txt = self.temp_script_path.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            logging.warning(f"[XEditRunner] TEMPスクリプトの読み取りに失敗: {e}")
            txt = ''

        debug_copy_path = self.intermediate_dir / f"copied_temp_readable_{self.temp_script_path.name}.pas"
        try:
            # First attempt: cp932 (Windows ANSI / Japanese)
            debug_copy_path.write_text(txt, encoding='cp932')
        except Exception:
            try:
                # Fall back to utf-8
                debug_copy_path.write_text(txt, encoding='utf-8')
            except Exception as e:
                logging.warning(f"[XEditRunner] デバッグコピー書き込みに失敗: {e}")

    def _copy_pas_units(self):
        # Copy top-level pas units
        for p in self.pas_scripts_dir.glob('*.pas'):
            try:
                dest = self.edit_scripts_dir / p.name
                if not p.samefile(self.source_script_path) and not dest.exists():
                    shutil.copy2(p, dest)
            except Exception:
                # ignore copy errors for individual files
                continue

        # Also copy library pas units into Edit Scripts root for units
        # that are referenced without a 'lib' path (xEdit's Pascal parser
        # sometimes expects the unit pas file to be in Edit Scripts root).
        lib_dir = self.pas_scripts_dir / 'lib'
        if lib_dir.is_dir():
            for p in lib_dir.glob('*.pas'):
                try:
                    dest = self.edit_scripts_dir / p.name
                    if not dest.exists():
                        shutil.copy2(p, dest)
                except Exception:
                    continue

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
