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

    # -------------- Overwrite → Output 処理 --------------

    def _move_results_from_overwrite(self, expected_filenames: Sequence[str]) -> bool:
        """
        MO2 Overwrite フォルダ配下 (Edit Scripts/Output) から成果物を
        Output へコピー + 検証後に原子的 rename。
        エラー時は Output に書きかけた一時ファイルをロールバック（削除）。
        Overwrite 側の原ファイルは削除しない（安全性優先）。
        """
        logging.info(f"[Overwrite収集] 期待ファイル: {list(expected_filenames)}")
        try:
            overwrite_path = self.config.get_path('Paths', 'overwrite_path')
            output_dir = self.config.get_path('Paths', 'output_dir')
        except (configparser.NoSectionError, configparser.NoOptionError):
            logging.error("設定エラー: [Paths] overwrite_path/output_dir が取得できません。")
            return False

        if not overwrite_path or not overwrite_path.is_dir():
            logging.error(f"Overwriteフォルダ不正: {overwrite_path}")
            return False

        output_dir.mkdir(parents=True, exist_ok=True)

        temp_created = []
        missing = []

        for filename in expected_filenames:
            source_file = overwrite_path / "Edit Scripts" / "Output" / filename
            dest_file = output_dir / filename
            temp_file = output_dir / (filename + ".part")

            if not source_file.is_file():
                logging.warning(f"[Overwrite収集] 見つからない: {filename}")
                missing.append(filename)
                continue

            try:
                logging.info(f"[Overwrite収集] コピー: {source_file} -> {temp_file}")
                shutil.copy2(source_file, temp_file)
                # 簡易検証（サイズ一致）
                if source_file.stat().st_size != temp_file.stat().st_size:
                    raise IOError(f"サイズ不一致 {source_file} -> {temp_file}")
                # 原子的置換 (既存あれば上書き)
                temp_file.replace(dest_file)
                temp_created.append(dest_file)
                logging.info(f"[Overwrite収集] 確定: {dest_file.name}")
            except Exception as e:
                logging.error(f"[Overwrite収集] コピー中エラー: {filename}: {e}")
                # 後続失敗扱い
                missing.append(filename)
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass

        if missing:
            # ロールバック（今回はコピーなので元ファイルは無傷。Output 側を削除するだけ）
            logging.error(f"[Overwrite収集] 必須ファイル欠落: {missing} → 処理中断")
            return False

        logging.info("[Overwrite収集] 全ファイル正常取得")
        return True

    # -------------- xEdit 実行 --------------

    def run_xedit_script(self, script_key: str, success_message: str) -> bool:
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
                    # 既存をバックアップ
                    timestamp = time.strftime('%Y%m%d_%H%M%S')
                    lib_backup_dir = edit_scripts_dir / f"_lib_backup_{timestamp}_{uuid.uuid4().hex}"
                    shutil.move(str(dest_lib_dir), str(lib_backup_dir))
                shutil.copytree(source_lib_dir, dest_lib_dir, dirs_exist_ok=True)

            command_list = []
            if use_mo2:
                command_list.extend([
                    str(env_settings["mo2_executable_path"]),
                    '-p',
                    str(env_settings["xedit_profile_name"])
                ])

            command_list.append(str(xedit_executable_path))

            # ゲーム指定（xEdit.exe の場合だけ補助フラグ）
            if xedit_executable_path.name.lower() == "xedit.exe":
                command_list.append("-FO4")

            # 共通引数を追加
            command_list.extend([
                "-force",
                "-IKnowWhatImDoing",
                "-AllowMasterFilesEdit",
                f"-script:{temp_script_filename}",
                f'-L:"{session_log_path}"'
            ])

            # -D 引数の条件付き追加
            if use_mo2 and not force_data_param:
                logging.info("[xEdit] MO2: -D は付与しません (force_data_param=False)")
            else:
                command_list.append(f'-D:"{game_data_path}"')
                if use_mo2:
                    logging.info("[xEdit] MO2: force_data_param=True → -D 付与")
                else:
                    logging.info("[xEdit] 非MO2: -D 付与")

            logging.info(f"[xEdit] 実行コマンド(list表示): {command_list}")

            # デバッグしやすい完全文字列（PowerShell用）も出力
            pwsh_line = " ".join(('\"{}\"'.format(a) if (" " in a and not a.startswith('"')) else a) for a in command_list)
            logging.debug(f"[xEdit] PowerShell で再現可能な形:\n{pwsh_line}")

            if use_mo2:
                # MO2 経由起動
                launch_ts = time.time()
                time_tolerance = 0.8  # 秒
                mo2_process = subprocess.Popen(command_list)
                logging.info(f"[xEdit] MO2 起動 PID={mo2_process.pid} / xEdit プロセス検出待機")

                xedit_executable_name = xedit_executable_path.name.lower()
                detect_start = time.time()
                while time.time() - detect_start < timeout_seconds:
                    for proc in psutil.process_iter(attrs=['pid', 'name', 'create_time']):
                        try:
                            if proc.info['name'].lower() == xedit_executable_name and \
                               proc.info['create_time'] >= (launch_ts - time_tolerance):
                                xedit_process_ps = psutil.Process(proc.info['pid'])
                                break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    if xedit_process_ps:
                        break
                    time.sleep(0.5)
                if not xedit_process_ps:
                    logging.error("[xEdit] 起動検出タイムアウト")
                    return False

                logging.info(f"[xEdit] xEdit 検出 PID={xedit_process_ps.pid} / 完了待ち (timeout={timeout_seconds}s)")
                try:
                    exit_code = xedit_process_ps.wait(timeout=timeout_seconds)
                except psutil.TimeoutExpired:
                    logging.error("[xEdit] 実行タイムアウト")
                    return False
                except psutil.NoSuchProcess:
                    logging.warning("[xEdit] 終了前にプロセスが消失（早期終了の可能性）")

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
                # stdout をログへ
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
                    except Exception as e:
                        pass
                time.sleep(poll_interval)

            # 成功判定ポリシー
            # 現在: exit_code == 0 かつ success_message 検出
            if exit_code != 0:
                logging.error(f"[xEdit] 失敗: exit code={exit_code}")
                return False
            if not success_found:
                logging.error("[xEdit] 失敗: success_message 未検出")
                return False

            logging.info(f"[xEdit] 成功: {source_script_path.name}")
            return True

        except subprocess.TimeoutExpired:
            logging.error(f"[xEdit] タイムアウト ({timeout_seconds}s 超過)")
            return False
        except Exception as e:
            logging.critical(f"[xEdit] 例外発生: {e}", exc_info=True)
            return False
        finally:
            if temp_script_path.exists():
                try: temp_script_path.unlink()
                except Exception: pass
            try:
                if dest_lib_dir.exists() and source_lib_dir.is_dir():
                    shutil.rmtree(dest_lib_dir)
                if lib_backup_dir and lib_backup_dir.exists():
                    shutil.move(str(lib_backup_dir), str(dest_lib_dir))
                elif not dest_lib_preexisted and dest_lib_dir.exists():
                    # 元々存在しなかったlibは削除
                    shutil.rmtree(dest_lib_dir)
            except Exception:
                pass
            if xedit_process_ps and xedit_process_ps.is_running():
                try: xedit_process_ps.terminate()
                except Exception: pass
            if mo2_process and mo2_process.poll() is None:
                try: mo2_process.terminate()
                except Exception: pass

    def _tail_file(self, path: Path, lines: int = 40) -> str:
        """
        ログなどの末尾数行を取得。大きなファイルでの負荷軽減。
        """
        try:
            content = path.read_text(encoding='utf-8', errors='replace').splitlines()
            return "\n".join(content[-lines:])
        except Exception:
            return "(ログ読込失敗)"

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
        if not self.run_xedit_script('weapon_ammo_extractor', '[AutoPatcher] Weapon and ammo mapping extraction complete.'):
            logging.critical("[Main] 武器/弾薬抽出失敗")
            return False
        if not self._move_results_from_overwrite(['weapon_ammo_map.json', 'unique_ammo_for_mapping.ini']):
            return False

        if not self.run_xedit_script('leveled_list_exporter', '[AutoPatcher] Leveled list export complete.'):
            logging.critical("[Main] レベルドリスト抽出失敗")
            return False
        if not self._move_results_from_overwrite(['exported_leveled_lists.json']):
            return False

        if not self.run_xedit_script('munitions_id_exporter', '[AutoPatcher] Munitions ammo ID export complete.'):
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
