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

# ★★★ 追加: 管理者権限確認 ★★★
from admin_check import is_admin, check_directory_access

class Orchestrator:
    """
    全自動パッチ処理のオーケストレータ。

    主要ステップ:
      1. xEdit スクリプトによるデータ抽出
      2. 戦略ファイルへの分類情報反映
      3. 弾薬マッピングツール起動 (mapper.py)
      4. Robco Patcher 用最終 INI 生成

    成功/失敗判定:
      - xEdit 実行は exit code と success_message（ログ内キーワード）の双方を利用
      - 戦略・INI 生成はファイル存在と例外非発生で判定

    依存する config_manager の想定インタフェース（抜粋）:
      - get_path(section, option) -> Path
      - get_string(section, option) -> str | None
      - get_script_filename(key) -> str
      - get_env_settings() -> dict
    """

    def __init__(self, config_manager):
        self.config = config_manager
        
        # ★★★ 追加: 管理者権限の確認と警告 ★★★
        if not is_admin():
            logging.warning("=" * 60)
            logging.warning("[警告] アプリケーションが管理者権限で実行されていません")
            logging.warning("ファイルの移動やコピーが失敗する可能性があります。")
            logging.warning("推奨: PowerShell を「管理者として実行」で起動してから実行してください")
            logging.warning("=" * 60)
    
    # -------------- 内部ユーティリティ --------------

    def _get_numeric(self, section: str, option: str, default, cast: Callable):
        """
        Config から数値（int/float）を取得。未設定・変換失敗時は default。
        """
        try:
            raw = self.config.get_string(section, option)
            if raw is None or raw == "":
                return default
            return cast(raw)
        except Exception:
            return default

    def _validate_data_path(self, path: Path) -> bool:
        """
        xEdit実行前にDataパスの妥当性を検証し、デバッグに役立つ情報をログ出力する。
        """
        if not path.is_dir():
            logging.error(f"[xEdit] Dataパスが存在しません: {path}")
            return False
        esm = path / "Fallout4.esm"
        if not esm.is_file():
            logging.error(f"[xEdit] Fallout4.esm が見つかりません: {esm}")
            try:
                # 診断情報として存在するesmファイルをリストアップ
                existing_esms = [p.name for p in path.glob('*.esm')]
                logging.warning(f"[xEdit] 診断: Dataフォルダ内のESMファイル (先頭5件): {existing_esms[:5]}")
            except Exception:
                pass # 診断情報の取得失敗は本筋に影響させない
            return False
        return True

    def _read_text_utf8_fallback(self, path: Path) -> str:
        """
        UTF-8 で読み込み、失敗時は locale 推奨エンコーディングで再試行。
        """
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            enc = locale.getpreferredencoding()
            return path.read_text(encoding=enc, errors="replace")

    def _candidate_output_dirs(self) -> list[Path]:
        """
        xEdit 実行後に成果物が置かれうる候補ディレクトリを優先順で返す。
        - 1) MO2 overwrite/Edit Scripts/Output
        - 2) 環境設定 mo2_overwrite_dir/Edit Scripts/Output（存在すれば）
        - 3) xEdit 実行フォルダ/Edit Scripts/Output
        - 4) アプリケーション output_dir（念のため）
        """
        candidates: list[Path] = []

        # 1) overwrite_path/Edit Scripts/Output
        try:
            ow = self.config.get_path('Paths', 'overwrite_path') / 'Edit Scripts' / 'Output'
            candidates.append(ow)
        except Exception:
            pass

        # 2) Environment 側に mo2_overwrite_dir があるなら候補に追加
        try:
            env = self.config.get_env_settings() or {}
            ow2 = env.get('mo2_overwrite_dir')
            if ow2:
                candidates.append(Path(ow2) / 'Edit Scripts' / 'Output')
        except Exception:
            pass

        # 3) xEdit 実行フォルダ/Edit Scripts/Output
        try:
            xedit_out = self.config.get_path('Paths', 'xedit_executable').parent / 'Edit Scripts' / 'Output'
            candidates.append(xedit_out)
        except Exception:
            pass

        # 4) output_dir（再実行時などに既に存在する可能性）
        try:
            app_out = self.config.get_path('Paths', 'output_dir')
            candidates.append(app_out)
        except Exception:
            pass

        # 正規化 + 既存ディレクトリに絞る + 重複排除
        seen = set()
        uniq_existing: list[Path] = []
        for d in candidates:
            try:
                key = str(d.resolve()).lower()
            except Exception:
                key = str(d).lower()
            if key not in seen and d and d.exists():
                seen.add(key)
                uniq_existing.append(d)
        return uniq_existing

    def _move_results_from_overwrite(self, expected_filenames: Sequence[str]) -> bool:
        """
        期待ファイルを候補ディレクトリ（MO2 Overwrite / xEdit Output / ほか）から探索し、
        アプリ output_dir にコピー（.part → 置換）する。
        1つでも見つからない場合は False を返す。
        """
        expected = list(expected_filenames)
        logging.info(f"[成果物収集] 期待ファイル: {expected}")

        try:
            output_dir = self.config.get_path('Paths', 'output_dir')
        except (configparser.NoSectionError, configparser.NoOptionError):
            logging.error("設定エラー: [Paths] output_dir を取得できません。")
            return False
        
        # ★★★ 追加: 出力ディレクトリのアクセス権限確認 ★★★
        output_dir.mkdir(parents=True, exist_ok=True)
        if not check_directory_access(output_dir, check_write=True):
            logging.error(f"[成果物収集] 出力ディレクトリへの書き込み権限がありません: {output_dir}")
            logging.error("[成果物収集] 対処方法: アプリケーションを管理者権限で実行してください")
            return False

        candidates = self._candidate_output_dirs()
        if not candidates:
            logging.error("[成果物収集] 探索候補ディレクトリがありません。設定を見直してください。")
            return False

        logging.info("[成果物収集] 探索候補:")
        for d in candidates:
            logging.info(f"  - {d}")

        missing: list[str] = []
        successfully_moved: list[str] = []
        
        for filename in expected:
            # 候補全てを走査して一致ファイルを集め、最も新しいものを採用
            found_paths: list[Path] = []
            for root in candidates:
                p = root / filename
                if p.is_file():
                    found_paths.append(p)
                    logging.debug(f"[成果物収集] 候補発見: {p}")

            if not found_paths:
                logging.warning(f"[成果物収集] 見つからない: {filename}")
                missing.append(filename)
                continue

            # 最も新しいファイルを採用
            try:
                src = max(found_paths, key=lambda x: x.stat().st_mtime)
                logging.info(f"[成果物収集] 最新ファイル選択: {src}")
            except Exception as e:
                logging.warning(f"[成果物収集] mtime比較失敗: {e} → 最初の候補を使用")
                src = found_paths[0]

            dest = output_dir / filename
            temp = output_dir / (filename + ".part")

            try:
                # ★★★ 追加: ソースファイルの読み取り権限確認 ★★★
                if not src.exists():
                    raise FileNotFoundError(f"ソースファイルが存在しません: {src}")
                
                src_size = src.stat().st_size
                logging.debug(f"[成果物収集]   元ファイルサイズ: {src_size} bytes")
                
                logging.info(f"[成果物収集] 取得: {src} -> {dest}")
                shutil.copy2(src, temp)
                
                # サイズ/mtime 簡易検証
                temp_size = temp.stat().st_size
                if src_size != temp_size:
                    raise IOError(f"サイズ不一致 src={src_size}, temp={temp_size}")
                
                temp.replace(dest)
                logging.info(f"[成果物収集] 確定: {dest.name}")
                successfully_moved.append(filename)
                
            except PermissionError as e:
                logging.error(f"[成果物収集] アクセス権限エラー: {filename}: {e}")
                logging.error(f"[成果物収集] 対処方法: アプリケーションを管理者権限で実行してください")
                missing.append(filename)
                if temp.exists():
                    try:
                        temp.unlink()
                    except Exception:
                        pass
            except Exception as e:
                logging.error(f"[成果物収集] コピー中エラー: {filename}: {e}", exc_info=True)
                missing.append(filename)
                if temp.exists():
                    try:
                        temp.unlink()
                    except Exception:
                        pass

        # ★★★ 修正: 結果サマリーを詳細化 ★★★
        logging.info(f"[成果物収集] 結果サマリー: 成功={len(successfully_moved)}, 失敗={len(missing)}")
        if successfully_moved:
            logging.info(f"[成果物収集]   成功: {successfully_moved}")
        
        if missing:
            logging.error(f"[成果物収集] 必須ファイル欠落: {missing}")
            logging.error("[成果物収集] 上記ファイルは次の場所を探索しました:")
            for d in candidates:
                logging.error(f"  - {d}")
            
            # ★★★ 追加: 権限不足の可能性を明示 ★★★
            if not is_admin():
                logging.error("[成果物収集] ヒント: 管理者権限で実行していないため、")
                logging.error("[成果物収集]         アクセス権限の問題が発生している可能性があります")
            
            return False

        logging.info("[成果物収集] 全ファイルを output_dir へ集約完了")
        return True

    # -------------- xEdit 実行 --------------

    def run_xedit_script(self, script_key: str, success_message: str, expected_outputs: Optional[list[str]] = None) -> bool:
        """
        指定された Pascal スクリプトを xEdit 経由で実行。
        成功判定:
          1) xEdit プロセス exit code == 0
          2) success_message がログに含まれる
        現状は (1) かつ (2) を成功とする（将来ポリシー変更はここで集約）。
        """
        xedit_executable_path = self.config.get_path('Paths', 'xedit_executable')
        xedit_dir = xedit_executable_path.parent
        edit_scripts_dir = xedit_dir / "Edit Scripts"

        if not edit_scripts_dir.is_dir():
            logging.error(f"[xEdit] 'Edit Scripts' フォルダが見つかりません: {edit_scripts_dir}")
            return False

        pas_scripts_dir = self.config.get_path('Paths', 'pas_scripts_dir')
        source_script_path = pas_scripts_dir / self.config.get_script_filename(script_key)
        if not source_script_path.is_file():
            logging.error(f"[xEdit] スクリプト未存在: {source_script_path}")
            return False

        temp_script_filename = f"TEMP_{int(time.time())}_{uuid.uuid4().hex}.pas"
        temp_script_path = edit_scripts_dir / temp_script_filename

        env_settings = self.config.get_env_settings()
        game_data_path = self.config.get_path('Paths', 'game_data_path')

        # 事前検証
        logging.info(f"[xEdit] 設定上の game_data_path={game_data_path}")
        if not self._validate_data_path(game_data_path):
            logging.critical("[xEdit] Dataパス検証失敗のため中断")
            return False

        source_lib_dir = pas_scripts_dir / 'lib'
        dest_lib_dir = edit_scripts_dir / 'lib'
        lib_backup_dir = None
        dest_lib_preexisted = dest_lib_dir.exists()

        use_mo2 = env_settings.get('use_mo2', False)
        force_data_param = self.config.get_boolean('Parameters', 'force_data_param', False)

        timeout_seconds = self._get_numeric('Parameters', 'xedit_timeout_seconds', 600, int)
        log_verification_timeout = self._get_numeric('Parameters', 'log_verification_timeout_seconds', 10, int)
        poll_interval = self._get_numeric('Parameters', 'log_poll_interval_seconds', 0.5, float)

        output_dir = self.config.get_path('Paths', 'output_dir')
        output_dir.mkdir(parents=True, exist_ok=True)
        session_log_path = output_dir / f"xEdit_session_{int(time.time())}.log"

        mo2_process = None
        xedit_process_ps = None
        exit_code: Optional[int] = None

        try:
            shutil.copy2(source_script_path, temp_script_path)

            # lib ディレクトリ差し替え
            if source_lib_dir.is_dir():
                if dest_lib_dir.exists():
                    timestamp = time.strftime('%Y%m%d_%H%M%S')
                    lib_backup_dir = edit_scripts_dir / f"_lib_backup_{timestamp}_{uuid.uuid4().hex}"
                    shutil.move(str(dest_lib_dir), str(lib_backup_dir))
                shutil.copytree(source_lib_dir, dest_lib_dir, dirs_exist_ok=True)

            # ★★★ 修正: コマンドライン構築を変更 ★★★
            command_list = []

            if use_mo2:
                mo2_executable = env_settings.get("mo2_executable_path")
                if not mo2_executable:
                    logging.error("[xEdit] MO2起動設定エラー: mo2_executable_path が未設定です")
                    return False

                profile_name = env_settings.get("xedit_profile_name")
                if not profile_name:
                    logging.error("[xEdit] MO2起動設定エラー: xedit_profile_name が未設定です")
                    return False

                mo2_entry_name = env_settings.get("mo2_xedit_entry_name")
                if not mo2_entry_name:
                    exe_name = xedit_executable_path.name.lower()
                    if exe_name == "fo4edit.exe":
                        mo2_entry_name = "FO4Edit"
                    elif exe_name == "xedit.exe":
                        mo2_entry_name = "xEdit"
                    else:
                        mo2_entry_name = xedit_executable_path.stem
                    logging.warning(
                        "[xEdit] MO2実行ファイルリストの名前が未設定です。仮の値 '%s' を使用します。"
                        " config.ini の [Environment] mo2_xedit_entry_name に設定を追加してください。",
                        mo2_entry_name
                    )

                xedit_executable_name = xedit_executable_path.name.lower()
                command_list = [
                    str(mo2_executable),
                    "-p",
                    profile_name,
                    f"moshortcut://Fallout 4:{mo2_entry_name}"
                ]
                logging.info(
                    "[xEdit] MO2 ショートカット経由でツールを起動します (プロファイル=%s, エントリ名=%s)",
                    profile_name,
                    mo2_entry_name
                )
            else:
                command_list.append(str(xedit_executable_path))
                if xedit_executable_path.name.lower() == "xedit.exe":
                    command_list.append("-FO4")
                command_list.extend([
                    "-IKnowWhatImDoing",
                    "-AllowMasterFilesEdit",
                    f"-script:{temp_script_filename}",
                    f'-L:"{session_log_path}"'
                ])
                logging.info("[xEdit] キャッシュ機能は廃止されました (-cache 引数は付与されません)")
                logging.info("[xEdit] 高速化: QuickShowConflicts 無効化 (-QS:0)")
                command_list.append(f'-D:"{game_data_path}"')
                if force_data_param:
                    logging.info("[xEdit] 直接起動: force_data_param=True のため -D を付与")
                else:
                    logging.info("[xEdit] 直接起動: -D を付与")

            logging.info(f"[xEdit] 実行コマンド(list表示): {command_list}")

            # デバッグ用完全文字列
            pwsh_line = " ".join(('\"{}\"'.format(a) if (" " in a and not a.startswith('"')) else a) for a in command_list)
            logging.debug(f"[xEdit] PowerShell で再現可能な形:\n{pwsh_line}")

            # --- プロセス実行 ---
            if use_mo2:
                launch_ts = time.time()
                time_tolerance = 0.8
                mo2_process = subprocess.Popen(command_list)
                logging.info(f"[xEdit] MO2 起動 PID={mo2_process.pid} / xEdit プロセス検出待機")

                xedit_executable_name = xedit_executable_path.name.lower()
                detect_start_time = time.time()
                while time.time() - detect_start_time < timeout_seconds:
                    for proc in psutil.process_iter(attrs=['pid', 'name', 'create_time']):
                        try:
                            if proc.info['name'].lower() == xedit_executable_name and \
                               proc.info['create_time'] >= (launch_ts - time_tolerance):
                                xedit_process_ps = psutil.Process(proc.info['pid'])
                                break
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            continue
                    if xedit_process_ps:
                        break
                    time.sleep(0.5)

                if not xedit_process_ps:
                    profile_name = env_settings.get('xedit_profile_name', '<未設定>')
                    logging.error("[xEdit] MO2経由でのxEdit起動検出タイムアウト")
                    logging.error("[xEdit] トラブルシューティング:")
                    logging.error("  1. MO2の『実行』メニューから xEdit が起動できるか確認")
                    logging.error(f"  2. MO2が起動し、プロファイル '{profile_name}' がロードされるか確認")
                    return False

                logging.info(f"[xEdit] xEdit 検出 PID={xedit_process_ps.pid} / 完了待ち (timeout={timeout_seconds}s)")
                exit_code = xedit_process_ps.wait(timeout=timeout_seconds)
                logging.info(f"[xEdit] xEdit 終了 (PID={xedit_process_ps.pid})")
            else:
                # 直接起動
                proc = subprocess.run(
                    command_list,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors='replace',
                    timeout=timeout_seconds
                )
                exit_code = proc.returncode
                logging.info("[xEdit] ---- STDOUT 開始 ----")
                if proc.stdout:
                    for line in proc.stdout.strip().splitlines():
                        logging.info(line)
                logging.info("[xEdit] ---- STDOUT 終了 ----")
                if proc.stderr:
                    logging.debug("[xEdit] ---- STDERR ----")
                    for line in proc.stderr.strip().splitlines():
                        logging.debug(line)
        
            # ログファイルポーリング（MO2/直接共通）
            success_found = False
            poll_start = time.time()
            while time.time() - poll_start < log_verification_timeout:
                if session_log_path.is_file():
                    try:
                        content = session_log_path.read_text(encoding='utf-8', errors='replace')
                        if success_message in content:
                            success_found = True
                            break
                    except Exception:
                        pass
                time.sleep(poll_interval)

            # ★★★ 修正: 成功判定ポリシー ★★★
            if exit_code != 0:
                logging.error(f"[xEdit] 失敗: exit code={exit_code}")
                return False
 
            if not success_found:
                logging.warning("[xEdit] success_message 未検出 (fallback: 成果物検証に委ね)")

            # ★★★ 修正: 成果物の検証と移動を統合 ★★★
            if expected_outputs:
                # 候補ディレクトリを確認して成果物の存在を検証
                candidates = self._candidate_output_dirs()
                
                logging.info(f"[xEdit] 成果物検証: {len(candidates)} 箇所を探索")
                for idx, d in enumerate(candidates, 1):
                    logging.debug(f"[xEdit]   {idx}. {d}")
                
                found_count = 0
                missing_files = []
                
                for filename in expected_outputs:
                    found = False
                    for candidate_dir in candidates:
                        file_path = candidate_dir / filename
                        if file_path.is_file():
                            logging.info(f"[xEdit] 出力確認 OK: {filename} -> {file_path}")
                            found_count += 1
                            found = True
                            break
                    if not found:
                        missing_files.append(filename)
                
                # ★★★ 重要: ファイルが見つかった場合、_move_results_from_overwrite を呼び出す ★★★
                if found_count > 0:
                    logging.info(f"[xEdit] 成果物 {found_count}/{len(expected_outputs)} 件検出 → 収集処理開始")
                    
                    # 全ファイルが見つからなくても、見つかったものだけ移動を試みる
                    if missing_files:
                        logging.warning(f"[xEdit] 一部成果物未検出: {missing_files}")
                    
                    # ★★★ ここで _move_results_from_overwrite を呼び出す ★★★
                    if not self._move_results_from_overwrite(expected_outputs):
                        logging.error("[xEdit] 成果物の収集に失敗")
                        return False
                    
                    logging.info(f"[xEdit] 成果物収集完了")
                else:
                    # 1つも見つからない場合は失敗
                    logging.error(f"[xEdit] 期待成果物が1つも見つかりません: {expected_outputs}")
                    logging.error(f"[xEdit] 探索した場所:")
                    for d in candidates:
                        logging.error(f"  - {d}")
                    return False

            # ★★★ 修正: ここで最終的な成功を返す ★★★
            logging.info(f"[xEdit] 成功: {source_script_path.name}")
            return True

        except subprocess.TimeoutExpired:
            logging.error(f"[xEdit] タイムアウト ({timeout_seconds}s 超過)")
            if expected_outputs:
                logging.info("[xEdit] タイムアウト後、成果物の緊急収集を試みます...")
                if self._move_results_from_overwrite(expected_outputs):
                    logging.warning("[xEdit] いくつかの成果物を収集できましたが、プロセスは失敗とみなします。")
            return False
        except psutil.TimeoutExpired:
            logging.error(f"[xEdit] タイムアウト ({timeout_seconds}s 超過) - MO2経由")
            if expected_outputs:
                candidates = self._candidate_output_dirs()
                for filename in expected_outputs:
                    for candidate_dir in candidates:
                        file_path = candidate_dir / filename
                        if file_path.is_file():
                            logging.warning(f"[xEdit] タイムアウト後に成果物を検出: {file_path}")
                            try:
                                self._move_results_from_overwrite([filename])
                            except Exception as e:
                                logging.error(f"[xEdit] 緊急収集失敗: {e}")
        except Exception as e:
            logging.critical(f"[xEdit] 例外発生: {e}", exc_info=True)
            return False
        finally:
            # クリーンアップ: 一時スクリプトとlibバックアップの処理
            try:
                if temp_script_path.exists():
                    temp_script_path.unlink()
                    logging.debug(f"[xEdit] 一時スクリプト削除: {temp_script_path}")
            except Exception as e:
                logging.warning(f"[xEdit] 一時スクリプト削除失敗: {e}")

            if lib_backup_dir and lib_backup_dir.exists():
                try:
                    if dest_lib_dir.exists():
                        shutil.rmtree(dest_lib_dir)
                    shutil.move(str(lib_backup_dir), str(dest_lib_dir))
                    logging.debug(f"[xEdit] lib ディレクトリ復元完了")
                except Exception as e:
                    logging.warning(f"[xEdit] lib ディレクトリ復元失敗: {e}")

    # -------------- 戦略ファイル更新 --------------

    def run_strategy_generation(self) -> bool:
        """
        ammo_categories.json の classification_rules を用いて
        strategy.json の ammo_classification を更新。
        """
        logging.info(f"{'=' * 16} 戦略ファイル生成処理開始 {'=' * 16}")
        try:
            categories_file = self.config.get_path('Paths', 'project_root') / 'ammo_categories.json'
            munitions_id_file = self.config.get_path('Paths', 'output_dir') / 'munitions_ammo_ids.ini'
            strategy_file = self.config.get_path('Paths', 'strategy_file')

            missing = []
            if not categories_file.is_file(): missing.append(categories_file)
            if not munitions_id_file.is_file(): missing.append(munitions_id_file)
            if not strategy_file.is_file(): missing.append(strategy_file)
            if missing:
                for f in missing:
                    logging.error(f"[Strategy] 必要ファイル未存在: {f}")
                return False

            # ルール読み込み
            rules_data = json.loads(categories_file.read_text(encoding='utf-8'))
            rules = rules_data.get("classification_rules", [])
            # ルール検証
            for idx, rule in enumerate(rules):
                if "keywords" not in rule or "Category" not in rule or "Power" not in rule:
                    logging.error(f"[Strategy] ルール欠落(index={idx}): {rule}")
                    return False

            parser = configparser.ConfigParser()
            parser.read(munitions_id_file, encoding='utf-8')

            ammo_classification = {}
            if parser.has_section('MunitionsAmmo'):
                for form_id, editor_id in parser.items('MunitionsAmmo'):
                    eid_lower = editor_id.lower()
                    matched = False
                    for rule in rules:
                        for kw in rule["keywords"]:
                            if kw.lower() in eid_lower:
                                ammo_classification[form_id.upper()] = {
                                    "Category": rule["Category"],
                                    "Power": rule["Power"]
                                }
                                matched = True
                                break
                        if matched:
                            break
                    if not matched:
                        logging.warning(f"[Strategy] 未分類: {editor_id} ({form_id.upper()})")

            strategy_raw = self._read_text_utf8_fallback(strategy_file)
            strategy_data = json.loads(strategy_raw)
            strategy_data["ammo_classification"] = ammo_classification
            strategy_file.write_text(
                json.dumps(strategy_data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            logging.info(f"[Strategy] 更新完了: {strategy_file.name} (分類数={len(ammo_classification)})")
            return True

        except Exception as e:
            logging.critical(f"[Strategy] 例外発生: {e}", exc_info=True)
            return False

    # -------------- Robco INI 生成 --------------

    def _generate_robco_ini(self):
        """
        抽出されたデータ、戦略ファイル、マッピングファイルに基づいて
        最終的な Robco Patcher の weapons.ini を生成する。
        """
        logging.info(f"{'-' * 10} ステップ4: Robco Patcher INI 生成 {'-' * 10}")
        try:
            strategy_file = self.config.get_path('Paths', 'strategy_file')
            ammo_map_file = self.config.get_path('Paths', 'ammo_map_file')
            output_dir = self.config.get_path('Paths', 'output_dir')
            weapon_data_file = output_dir / 'weapon_ammo_map.json'
            robco_patcher_dir = self.config.get_path('Paths', 'robco_patcher_dir')
            robco_ini_filename = self.config.get_string('Parameters', 'robco_output_filename') or "weapons.ini"
            output_ini_path = robco_patcher_dir / robco_ini_filename

            for f in [strategy_file, weapon_data_file]:
                if not f.is_file():
                    logging.error(f"[RobcoINI] 必須ファイル未存在: {f}")
                    return False

            strategy_data = json.loads(self._read_text_utf8_fallback(strategy_file))
            try:
                weapon_data = json.loads(self._read_text_utf8_fallback(weapon_data_file))
            except json.JSONDecodeError as e:
                logging.error(f"[RobcoINI] weapon_ammo_map.json 読込失敗: {e}")
                return False

            ammo_map_dict = {}
            if ammo_map_file.is_file():
                parser = configparser.ConfigParser()
                parser.read(ammo_map_file, encoding='utf-8')
                if parser.has_section('UnmappedAmmo'):
                    ammo_map_dict = {k.lower(): v.lower() for k, v in parser.items('UnmappedAmmo')}

            ammo_classification = strategy_data.get('ammo_classification', {})
            allocation_matrix = strategy_data.get('allocation_matrix', {})
            faction_leveled_lists = strategy_data.get('faction_leveled_lists', {})

            ini_lines = [
                "; Generated by Munitions Auto Patcher",
                f"; GeneratedAt={time.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "[Settings]",
                "; (Reserved for future use)",
                "",
                "[Leveled List Integration]",
                "; Weapon sections follow."
            ]

            processed = 0
            skipped_no_category = 0

            for weapon in weapon_data:
                editor_id = weapon.get('editor_id')
                ammo_form = (weapon.get('ammo_form_id') or "").lower()
                full_name = weapon.get('full_name', editor_id)

                if not editor_id or not ammo_form:
                    logging.warning(f"[RobcoINI] 不完全定義スキップ: {weapon}")
                    continue

                final_ammo_formid = ammo_map_dict.get(ammo_form, ammo_form)
                ammo_info = ammo_classification.get(final_ammo_formid.upper())
                if not ammo_info:
                    skipped_no_category += 1
                    continue

                leveled_entries = []
                for faction, lli_name in faction_leveled_lists.items():
                    faction_alloc = allocation_matrix.get(faction, {})
                    spawn_chance = faction_alloc.get(ammo_info["Category"])
                    if spawn_chance and spawn_chance > 0:
                        leveled_entries.append(f"{lli_name}@{ammo_info['Category']}:{spawn_chance}")

                if not leveled_entries:
                    continue

                safe_id = editor_id.replace(' ', '_')
                ini_lines.append(f"\n[Weapon.{safe_id}]")
                ini_lines.append(f"name = {full_name}")
                ini_lines.append(f"leveled_lists = {', '.join(leveled_entries)}")
                processed += 1

            robco_patcher_dir.mkdir(parents=True, exist_ok=True)
            output_ini_path.write_text("\n".join(ini_lines), encoding='utf-8')
            logging.info(f"[RobcoINI] 生成成功: {output_ini_path.name} (処理={processed}, 未分類スキップ={skipped_no_category})")
            return True

        except Exception as e:
            logging.critical(f"[RobcoINI] 例外発生: {e}", exc_info=True)
            return False

    # -------------- 全体実行 --------------

    def run_full_process(self) -> bool:
        """
        全自動フローを実行。
        戻り値: True=全工程成功, False=途中失敗
        """
        logging.info(f"{'=' * 20} 全自動処理開始 {'=' * 20}")

        # --- ステップ1: データ抽出 ---
        logging.info(f"{'-' * 10} ステップ1: xEdit 抽出 {'-' * 10}")
        if not self.run_xedit_script(
            'weapon_ammo_extractor',
            '[AutoPatcher] Weapon and ammo mapping extraction complete.',
            expected_outputs=['weapon_ammo_map.json', 'unique_ammo_for_mapping.ini']
        ):
            logging.critical("[Main] 武器/弾薬抽出失敗")
            return False
        # _move_results_from_overwrite は found が overwrite 内にあれば従来どおり移動、
        # そうでなければ xEdit 実行フォルダから overwrite_path へコピーするロジックを拡張しても良い

        if not self.run_xedit_script(
            'leveled_list_exporter',
            '[AutoPatcher] Leveled list export complete.',
            expected_outputs=['leveled_lists.json']
        ):
            logging.critical("[Main] レベルドリスト抽出失敗")
            return False
        if not self._move_results_from_overwrite(['leveled_lists.json']):
            return False

        if not self.run_xedit_script(
            'munitions_id_exporter',
            '[AutoPatcher] Munitions ammo ID export complete.',
            expected_outputs=['munitions_ammo_ids.ini']
        ):
            logging.critical("[Main] Munitions ID 抽出失敗")
            return False
        if not self._move_results_from_overwrite(['munitions_ammo_ids.ini']):
            return False

        logging.info("[Main] ステップ1 完了")

        # --- ステップ2: 戦略ファイルの更新 ---
        logging.info(f"{'-' * 10} ステップ2: 戦略ファイル更新 {'-' * 10}")
        if not self.run_strategy_generation():
            logging.critical("[Main] 戦略ファイル更新失敗")
            return False

        # --- ステップ3: 弾薬マッピング ---
        logging.info(f"{'-' * 10} ステップ3: マッピングツール起動 {'-' * 10}")
        logging.info("[Main] マッピング確認後にツールを終了してください。")
        try:
            mapper_path = self.config.get_path('Paths', 'project_root') / 'mapper.py'
            if not mapper_path.is_file():
                logging.error(f"[Main] mapper.py 不在: {mapper_path}")
                return False

            python_exec = shutil.which("python") or shutil.which("python3")
            if not python_exec:
                logging.error("[Main] Python 実行ファイルが見つかりません。PATH を確認してください。")
                return False

            output_dir = self.config.get_path('Paths', 'output_dir')
            ammo_file = output_dir / 'unique_ammo_for_mapping.ini'
            munitions_file = output_dir / 'munitions_ammo_ids.ini'
            output_file = self.config.get_path('Paths', 'ammo_map_file')

            cmd = [
                python_exec,
                str(mapper_path),
                "--ammo-file", str(ammo_file),
                "--munitions-file", str(munitions_file),
                "--output-file", str(output_file)
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if proc.returncode != 0:
                logging.error("[Main] mapper.py 実行エラー")
                if proc.stderr:
                    logging.error(f"[mapper stderr]\n{proc.stderr}")
                return False
            logging.info("[Main] マッピングツール正常終了")
        except Exception as e:
            logging.critical(f"[Main] マッピングツール起動例外: {e}", exc_info=True)
            return False

        # --- ステップ4: 最終INI生成 ---
        if not self._generate_robco_ini():
            logging.critical("[Main] 最終 INI 生成失敗")
            return False

        logging.info("[Main] 全工程正常完了")
        return True

