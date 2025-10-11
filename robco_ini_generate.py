# -*- coding: utf-8 -*-
# robco_ini_generate.py — Robco INI 生成モジュール
#
# 生成:
# - robco_ammo_patch.ini（robcoammopatch）
# - robco_ll_patch.ini（robcollpatch）…必要入力が揃う場合のみ
#
# 仕様:
# - allocation_matrix は重み％、invertedChance = 100 - weight
# - ammo_map.json 優先（mappings[].source.formid -> target.formid）、無ければ ammo_map.ini の [UnmappedAmmo]
# - WeaponLeveledLists_Export.csv 優先（EditorID,FormID,SourceFile）、無ければ leveled_lists.json
# - 武器 Plugin|FormID は weapon_ammo_details.txt（推奨）または weapon_records.csv から取得
# - SuperMutants は対象外
#
from __future__ import annotations

from collections.abc import Iterable
import csv
import json
import locale
import logging
import time
import shutil
from pathlib import Path
import configparser
from collections import Counter

def _read_text_utf8_fallback(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        enc = locale.getpreferredencoding(False)
        return path.read_text(encoding=enc, errors='replace')

def _get_target_ll_editorids() -> dict:
    # SuperMutants は除外
    return {
        "Gunners": "LLI_Hostile_Gunner_Any",
        "Raiders": "LLI_Raider_Weapons",
        "Institute": "LL_InstituteLaserGun_SimpleRifle",
    }

def _find_leveled_lists_csv(output_dir: Path, cfg_path: Path | None) -> Path | None:
    # 明示パスがあれば最優先
    if cfg_path and cfg_path.is_file():
        return cfg_path
    # 既定候補
    candidates = [
        output_dir / 'WeaponLeveledLists_Export.csv',
        output_dir.parent / 'WeaponLeveledLists_Export.csv',
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None

def _load_ll_from_csv(output_dir: Path, cfg_path: Path | None) -> dict:
    """
    CSV(WeaponLeveledLists_Export.csv) から EditorID -> {plugin, formid} を構築。
    CSVヘッダ: EditorID,FormID,SourceFile（他カラムがあっても可）
    - フィールドのダブルクォートを除去
    - 全行を取り込み（特定EditorIDに絞り込まない）
    - Fallout4.esm を優先
    """
    mapping: dict[str, dict] = {}
    csv_path = _find_leveled_lists_csv(output_dir, cfg_path)
    targets = _get_target_ll_editorids()
    desired = set(targets.values())
    aliases = {"LL_InstituteLaserGun": "LL_InstituteLaserGun_SimpleRifle"}

    if not csv_path:
        logging.warning("[Robco][LL] WeaponLeveledLists_Export.csv が見つかりません（CSV 読込スキップ）")
        return mapping

    logging.info("[Robco][LL] CSV 読込: %s", csv_path)
    try:
        with csv_path.open('r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                edid = (row.get('EditorID') or '').strip().strip('"')
                formid = (row.get('FormID') or '').strip().strip('"').upper()
                plugin = (row.get('SourceFile') or '').strip().strip('"')
                if not edid:
                    continue
                prev = mapping.get(edid)
                if prev is None or (plugin.lower() == 'fallout4.esm' and prev.get('plugin', '').lower() != 'fallout4.esm'):
                    if plugin and formid and len(formid) == 8:
                        mapping[edid] = {'plugin': plugin, 'formid': formid}
    except Exception as e:
        logging.error(f"[Robco][LL] CSV 読込失敗: {e}")
        return {}

    return mapping

def _load_ll_from_json(output_dir: Path) -> dict:
    p = output_dir / "leveled_lists.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(_read_text_utf8_fallback(p))
        return data.get("LeveledLists", {}) or {}
    except Exception as e:
        logging.warning(f"[Robco][LL] leveled_lists.json 読み込み失敗（フォールバック無効）: {e}")
        return {}

def _load_ammo_map(ammo_map_file: Path) -> dict:
    """
    ammo_map.json を優先、無ければ ammo_map.ini の [UnmappedAmmo]。
    返却: dict[original_formid_lower] = target_formid_lower
    """
    json_path = ammo_map_file.with_suffix(".json")
    if json_path.is_file():
        try:
            data = json.loads(_read_text_utf8_fallback(json_path))
            mapping = {}
            for m in data.get("mappings", []):
                src = (m.get("source") or {})
                dst = (m.get("target") or {})
                sf = (src.get("formid") or "").lower()
                df = (dst.get("formid") or "").lower()
                if sf and df:
                    mapping[sf] = df
            if mapping:
                logging.info("[Robco][診断] ammo_map.json マッピング数: %d", len(mapping))
                return mapping
        except Exception as e:
            logging.warning(f"[Robco] ammo_map.json 読み込み失敗: {e}")

    mapping = {}
    if ammo_map_file.is_file():
        try:
            parser = configparser.ConfigParser()
            parser.read(ammo_map_file, encoding="utf-8")
            if parser.has_section("UnmappedAmmo"):
                for k, v in parser.items("UnmappedAmmo"):
                    mapping[k.lower()] = v.lower()
            logging.info("[Robco][診断] ammo_map.ini マッピング数: %d", len(mapping))
        except Exception as e:
            logging.warning(f"[Robco] ammo_map.ini 読み込み失敗: {e}")
    else:
        logging.info("[Robco][診断] ammo_map.* が見つかりません（マッピングなしとして続行）")
    return mapping

def _candidate_paths_for_weapon_records(output_dir: Path, extra: Path | None) -> Iterable[Path]:
    # 優先順で候補ディレクトリを列挙
    dirs = []
    # 1) Orchestrator の output_dir
    dirs.append(output_dir)
    # 2) output_dir の親（リポジトリ直下など）
    if output_dir.parent and output_dir.parent.exists():
        dirs.append(output_dir.parent)
    # 3) config で指定があれば（xEdit の Edit Scripts\Output など）
    if extra and extra.exists():
        dirs.append(extra)
    # 重複排除
    seen = set()
    for d in dirs:
        if d and d.exists():
            p = d.resolve()
            if p not in seen:
                seen.add(p)
                yield p

def _read_weapon_records(output_dir: Path, xedit_output_dir: Path | None) -> list[dict]:
    """
    武器 Plugin|FormID を取得。以下の候補ディレクトリを順に探します:
      - output_dir
      - output_dir.parent
      - xEdit 出力 (config Paths.xedit_output_dir を指定した場合)
    """
    candidates = list(_candidate_paths_for_weapon_records(output_dir, xedit_output_dir))
    records: list[dict] = []
    found_at: Path | None = None

    def try_load_txt(p: Path) -> bool:
        nonlocal records, found_at
        txt = p / "weapon_ammo_details.txt"
        if not txt.is_file():
            return False
        try:
            tmp = []
            for ln in txt.read_text(encoding="utf-8", errors="replace").splitlines():
                ln = ln.strip()
                if not ln or ln.startswith("#") or ln.startswith(";"):
                    continue
                parts = [s.strip() for s in ln.split("|")]
                if len(parts) < 6:
                    logging.warning(f"[RobcoLL] weapon_ammo_details.txt フォーマット不正: {ln}")
                    continue
                rec = {
                    "plugin": parts[0],
                    "weap_formid": parts[1].upper(),
                    "weap_editor_id": parts[2],
                    "ammo_plugin": parts[3],
                    "ammo_formid": parts[4].upper(),
                    "ammo_editor_id": parts[5],
                }
                if rec["plugin"] and rec["weap_formid"]:
                    tmp.append(rec)
            if tmp:
                records = tmp
                found_at = txt
                return True
        except Exception as e:
            logging.error(f"[RobcoLL] weapon_ammo_details.txt 読み込み失敗: {e}")
        return False

    def try_load_csv(p: Path) -> bool:
        nonlocal records, found_at
        csvf = p / "weapon_records.csv"
        if not csvf.is_file():
            return False
        try:
            tmp = []
            with csvf.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rec = {
                        "plugin": (row.get("plugin") or row.get("Plugin") or "").strip(),
                        "weap_formid": (row.get("weap_formid") or row.get("WeaponFormID") or "").strip().upper(),
                        "weap_editor_id": (row.get("weap_editor_id") or row.get("WeaponEditorID") or "").strip(),
                        "ammo_plugin": (row.get("ammo_plugin") or row.get("AmmoPlugin") or "").strip(),
                        "ammo_formid": (row.get("ammo_formid") or row.get("AmmoFormID") or "").strip().upper(),
                        "ammo_editor_id": (row.get("ammo_editor_id") or row.get("AmmoEditorID") or "").strip(),
                    }
                    if rec["plugin"] and rec["weap_formid"]:
                        tmp.append(rec)
            if tmp:
                records = tmp
                found_at = csvf
                return True
        except Exception as e:
            logging.error(f"[RobcoLL] weapon_records.csv 読み込み失敗: {e}")
        return False

    # 候補ディレクトリ順に探索
    for d in candidates:
        if try_load_txt(d) or try_load_csv(d):
            logging.info("[Robco][LL] 武器レコード入力: %s (件数=%d)", found_at, len(records))
            break

    if not records:
        logging.warning("[Robco][LL] 武器レコードが見つかりませんでした（weapon_ammo_details.txt / weapon_records.csv）")
        logging.warning("[Robco][LL] 探索ディレクトリ: %s", " | ".join(str(x) for x in candidates))

    return records
def _invert_robco_chance(weight_value) -> int:
    try:
        v = float(weight_value)
    except Exception:
        return 100
    v = max(0.0, min(100.0, v))
    return int(round(100.0 - v))

def _category_to_group(category: str) -> str | None:
    if not category:
        return None
    c = category.lower()
    if ("pistol" in c) or ("low" in c) or ("handgun" in c):
        return "pistol"
    if ("rifle" in c) or ("medium" in c) or ("advanced" in c) or ("military" in c) \
       or ("shotgun" in c) or ("energy" in c) or ("explosive" in c) or ("primitive" in c) or ("exotic" in c):
        return "rifle"
    return None

def _load_munitions_npc_list_map(output_dir: Path, specified: Path | None) -> dict[str, str]:
    """
    Munitions弾薬FormID -> NPC用フォームリストFormID のマップを読み込む。
    INI形式想定: [AmmoNPCList] <AmmoFormID>=<FormListFormID>
    """
    candidates: list[Path] = []
    if specified and specified.is_file():
        candidates.append(specified)
    candidates.append(output_dir / "munitions_npc_lists.ini")
    if output_dir.parent and output_dir.parent.exists():
        candidates.append(output_dir.parent / "munitions_npc_lists.ini")
    for p in candidates:
        if p.is_file():
            try:
                parser = configparser.ConfigParser()
                parser.read(p, encoding="utf-8")
                mapping: dict[str, str] = {}
                if parser.has_section("AmmoNPCList"):
                    for k, v in parser.items("AmmoNPCList"):
                        k_norm = (k or "").strip().upper()
                        v_norm = (v or "").strip().upper()
                        if k_norm and v_norm:
                            mapping[k_norm] = v_norm
                if mapping:
                    logging.info("[Robco][Ammo] NPC用フォームリストMap読込: %s (件数=%d)", p, len(mapping))
                    return mapping
            except Exception as e:
                logging.warning(f"[Robco][Ammo] munitions_npc_lists.ini 読込失敗: {e}")
    return {}

def _load_munitions_ammo_id_map(output_dir: Path) -> dict[str, str]:
    """
    munitions_ammo_ids.ini から FormID -> EditorID のマップを読み込む。
    """
    p = output_dir / "munitions_ammo_ids.ini"
    if not p.is_file():
        logging.warning("[Robco][Ammo] munitions_ammo_ids.ini が見つかりません。")
        return {}
    
    mapping: dict[str, str] = {}
    try:
        parser = configparser.ConfigParser()
        parser.read(p, encoding="utf-8")
        if parser.has_section("MunitionsAmmo"):
            for k, v in parser.items("MunitionsAmmo"):
                mapping[k.upper()] = v
        return mapping
    except Exception as e:
        logging.warning(f"[Robco][Ammo] munitions_ammo_ids.ini 読み込み失敗: {e}")
    return {}

def run(config) -> bool:
    """
    Robco Patcher 用 INI を生成。
    - robco_ammo_patch.ini（常時）
    - robco_ll_patch.ini（入力が揃った場合のみ）
    """
    logging.info(f"{'-' * 10} ステップ4: Robco Patcher INI 生成 {'-' * 10}")

    # --- 設定の読み込み ---
    simplify_ini = True # デフォルトはシンプル出力
    if hasattr(config, 'get_boolean'):
        simplify_ini = config.get_boolean('Parameters', 'simplify_robco_ammo_ini', fallback=True)

    try:
        strategy_file = config.get_path('Paths', 'strategy_file')
        output_dir = config.get_path('Paths', 'output_dir')
        ammo_map_file = config.get_path('Paths', 'ammo_map_file')
        try:
            leveled_lists_csv_cfg = config.get_path('Paths', 'leveled_lists_csv')
        except Exception:
            leveled_lists_csv_cfg = None

        weapon_data_file = output_dir / 'weapon_ammo_map.json'
        robco_patcher_dir = config.get_path('Paths', 'robco_patcher_dir')

        # 必須
        missing = []
        if not strategy_file.is_file(): missing.append(strategy_file)
        if not weapon_data_file.is_file(): missing.append(weapon_data_file)
        if missing:
            for f in missing:
                logging.error(f"[Robco] 必須ファイル未存在: {f}")
            return False

        # 入力読込
        strategy_data = json.loads(_read_text_utf8_fallback(strategy_file))
        try:
            weapon_data = json.loads(_read_text_utf8_fallback(weapon_data_file))
        except json.JSONDecodeError as e:
            logging.error(f"[Robco] weapon_ammo_map.json 読み込失敗: {e}")
            return False

        ammo_map_dict = _load_ammo_map(ammo_map_file)
        ammo_classification: dict = strategy_data.get('ammo_classification', {})
        allocation_matrix: dict = strategy_data.get('allocation_matrix', {})
        # 戦略側の指定があれば優先、無ければ従来の既定値
        faction_ll_map: dict = strategy_data.get('faction_leveled_lists') or _get_target_ll_editorids()

        # LL 解決（CSV 優先、JSON フォールバック）
        ll_csv_map = _load_ll_from_csv(output_dir, leveled_lists_csv_cfg)
        ll_json_map = _load_ll_from_json(output_dir)
        ll_editorid_to_pf = ll_csv_map if ll_csv_map else ll_json_map

        # 診断
        logging.info("[Robco][診断] weapon_ammo_map.json 件数: %d", len(weapon_data))
        logging.info("[Robco][診断] ammo_classification 件数: %d", len(ammo_classification))
        logging.info("[Robco][診断] allocation_matrix 勢力数: %d", len(allocation_matrix or {}))
        total_weights = sum(
            float(v or 0) for m in (allocation_matrix or {}).values() for v in (m or {}).values()
        )
        logging.info("[Robco][診断] allocation_matrix 総重み: %.1f", total_weights)
        cat_counter = Counter((info or {}).get("Category") for info in ammo_classification.values() if info)
        if cat_counter:
            logging.info("[Robco][診断] カテゴリ内訳:")
            for c, n in cat_counter.most_common():
                logging.info("  - %s: %d", c, n)
        logging.info("[Robco][診断] ammo_map マッピング数: %d", len(ammo_map_dict))
        logging.info("[Robco][診断] 使用 LL (EditorID): %s", ", ".join(faction_ll_map.values()))

        # 1) robco_ammo_patch.ini - 新構文
        # Step 1: 独自弾薬を全フォームリストから削除
        ammo_lines = [
            "; Robco Ammo Patcher - Auto generated (new syntax)",
            f"; GeneratedAt={time.strftime('%Y-%m-%d %H:%M:%S')}",
            "; Step1: formsToRemove=<OriginalAmmoFormID> ; 全フォームリストから削除",
            "; Step2: filterByWeapons=<Plugin>|<WeaponFormID>:setNewAmmo=<MunitionsAmmoFID>[:setNewAmmoList=<NPCAmmoListFID>]",
        ""
        ]
        added_ammo = 0
        for orig_fid_lower in sorted(set(ammo_map_dict.keys())):
            ammo_lines.append(f"formsToRemove={(orig_fid_lower or '').upper()}")
            added_ammo += 1

        # Step 2: 武器が使用する弾薬をMunitionsへ置換（必要に応じてNPCリストも設定）
        weapon_records = _read_weapon_records(
            output_dir,
            config.get_path('Paths', 'xedit_output_dir') if hasattr(config, 'get_path') else None
        )
        try:
            npc_list_map_path = config.get_path('Paths', 'munitions_npc_list_map')
        except Exception:
            npc_list_map_path = None
        npc_list_map = _load_munitions_npc_list_map(output_dir, npc_list_map_path)
        munitions_id_map = _load_munitions_ammo_id_map(output_dir)

        seen_weapon_lines: set[str] = set()
        for rec in weapon_records:
            weap_plugin = (rec.get("plugin") or "").strip()
            weap_fid = (rec.get("weap_formid") or "").upper()
            weap_eid = (rec.get("weap_editor_id") or "").strip()
            orig_ammo_fid = (rec.get("ammo_formid") or "").upper()
            orig_ammo_eid = (rec.get("ammo_editor_id") or "").strip()

            if not (weap_plugin and weap_fid and orig_ammo_fid):
                continue

            orig_ammo_fid_lower = orig_ammo_fid.lower()

            # --- ロジック分岐 ---
            if simplify_ini:
                # 【シンプルモード】マッピング対象の武器のみINIに記述
                if orig_ammo_fid_lower in ammo_map_dict:
                    mapped_ammo_fid = ammo_map_dict[orig_ammo_fid_lower].upper()
                    mapped_ammo_eid = munitions_id_map.get(mapped_ammo_fid, "UNKNOWN_MUNITIONS_AMMO")

                    comment = f"; [{weap_plugin}] {weap_eid} ({orig_ammo_eid}) -> {mapped_ammo_eid}"
                    line = f"filterByWeapons={weap_plugin}|{weap_fid}:setNewAmmo={mapped_ammo_fid}"
                    
                    npc_list_fid = npc_list_map.get(mapped_ammo_fid)
                    if npc_list_fid:
                        line += f":setNewAmmoList={npc_list_fid}"
                    
                    if comment not in seen_weapon_lines:
                        ammo_lines.append(f"\n{comment}")
                        seen_weapon_lines.add(comment)
                    if line not in seen_weapon_lines:
                        ammo_lines.append(line)
                        seen_weapon_lines.add(line)
            else:
                # 【互換モード】全武器をINIに記述（変更がない武器も含む）
                mapped_ammo_fid = (ammo_map_dict.get(orig_ammo_fid_lower) or orig_ammo_fid).upper()
                line = f"filterByWeapons={weap_plugin}|{weap_fid}:setNewAmmo={mapped_ammo_fid}"
                if line not in seen_weapon_lines:
                    ammo_lines.append(line)
                    seen_weapon_lines.add(line)
        
        # --- 出力先のディレクトリ構造を構築 ---
        # RobCo_Auto_Patcher/F4SE/Plugins/RobCo_Patcher/ を基準とする
        robco_base_dir = robco_patcher_dir / "F4SE" / "Plugins" / "RobCo_Patcher"
        formlist_dir = robco_base_dir / "formlist"
        weapon_dir = robco_base_dir / "weapon"
        formlist_dir.mkdir(parents=True, exist_ok=True)
        weapon_dir.mkdir(parents=True, exist_ok=True)

        # --- INIファイル1: 独自弾薬をフォームリストから削除 ---
        formlist_remove_lines = [f"; Munitions Auto-Patcher: Remove Custom Ammo from FormLists", f"; GeneratedAt={time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
        formlist_remove_lines.extend(f"formsToRemove={(orig_fid_lower or '').upper()}" for orig_fid_lower in sorted(set(ammo_map_dict.keys())))
        
        if len(formlist_remove_lines) > 3: # ヘッダー以外の行がある場合
            ammo_out_path = formlist_dir / "Munitions_FormList_RemoveCustomAmmo.ini"
            ammo_out_path.write_text("\n".join(ammo_lines), encoding="utf-8")
            logging.info("[Robco][Ammo] 生成: %s (件数=%d, サイズ=%d bytes)",
                        ammo_out_path.name, added_ammo, ammo_out_path.stat().st_size)
        else:
            logging.warning("[Robco][Ammo] 生成対象 0 件")

        # 2) robco_ll_patch.ini（新構文・確定追加）
        # --- INIファイル2: 武器の使用弾薬を変更 ---
        weapon_patch_lines = [f"; Munitions Auto-Patcher: Set Weapon Ammo", f"; GeneratedAt={time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
        weapon_patch_lines.extend(line for line in ammo_lines if line.strip().startswith("filterByWeapons") or line.strip().startswith("; ["))
        
        if any(line.strip().startswith("filterByWeapons") for line in weapon_patch_lines):
            weapon_out_path = weapon_dir / "Munitions_Weapon_SetAmmo.ini"
            weapon_out_path.write_text("\n".join(weapon_patch_lines), encoding="utf-8")
            logging.info("[Robco][Weapon] 生成: %s (サイズ=%d bytes)", weapon_out_path.name, weapon_out_path.stat().st_size)

        # --- INIファイル3: 武器をレベルドリストに追加 ---
        formlist_add_lines = [
            "; Munitions Auto-Patcher: Add Patched Weapons to Leveled Lists",
            f"; GeneratedAt={time.strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        added_ll = 0

        if weapon_records and ll_editorid_to_pf:
            seen_ll_lines: set[str] = set()
            for rec in weapon_records:
                weap_plugin = (rec.get("plugin") or "").strip()
                weap_eid = (rec.get("weap_editor_id") or "").strip()
                weap_fid = (rec.get("weap_formid") or "").upper()
                orig_ammo_fid = (rec.get("ammo_formid") or "").upper()
                if not (weap_plugin and weap_fid and orig_ammo_fid):
                    continue
                if orig_ammo_fid.lower() not in ammo_map_dict:
                    continue
                for faction, lli_editorid in faction_ll_map.items():
                    pf = ll_editorid_to_pf.get(lli_editorid) or {}
                    ll_fid = (pf.get("formid") or "").upper()
                    if not ll_fid:
                        logging.warning(f"[Robco][LL] LL 未解決: {lli_editorid}（CSV/JSON を確認）")
                        continue
                    
                    comment = f"; Add [{weap_plugin}] {weap_eid} to {faction}"
                    line = f"filterByFormLists={ll_fid}:formsToAdd={weap_plugin}|{weap_fid}"
                    if comment not in seen_ll_lines:
                        formlist_add_lines.append(f"\n{comment}")
                        seen_ll_lines.add(comment)
                    if line not in seen_ll_lines:
                        formlist_add_lines.append(line)
                        seen_ll_lines.add(line)
                        added_ll += 1

        ll_out_path = formlist_dir / "Munitions_FormList_AddWeaponsToLL.ini"
        if added_ll > 0:
            ll_out_path.write_text("\n".join(formlist_add_lines), encoding="utf-8")
            logging.info("[Robco][LL] 生成: %s (件数=%d, サイズ=%d bytes)",
                        ll_out_path.name, added_ll, ll_out_path.stat().st_size)
        else:
            logging.warning("[Robco][LL] 生成対象 0 件（weapon_records / CSV/JSON / allocation_matrix を確認）")

        # --- ZIPアーカイブの作成 ---
        try:
            # ZIPファイルはプロジェクトルートに出力
            zip_output_path = robco_patcher_dir.parent / f"{robco_patcher_dir.name}.zip"
            logging.info(f"[Robco][ZIP] ZIPアーカイブを作成します: {zip_output_path}")

            # 既存のZIPファイルを削除
            if zip_output_path.exists():
                zip_output_path.unlink()

            shutil.make_archive(
                base_name=str(zip_output_path.with_suffix('')), # 出力ファイル名 (拡張子なし)
                format='zip',                                  # フォーマット
                root_dir=robco_patcher_dir,                    # アーカイブのルートを RobCo_Auto_Patcher に設定
                base_dir='F4SE'                                # F4SE ディレクトリからアーカイブを開始
            )
            logging.info(f"[Robco][ZIP] {zip_output_path.name} の作成が完了しました。")
        except Exception as e:
            logging.error(f"[Robco][ZIP] ZIPアーカイブの作成中にエラーが発生しました: {e}", exc_info=True)

        logging.info("[Robco] Robco INI 生成完了")
        return True

    except Exception as e:
        logging.critical(f"[Robco] 例外発生: {e}", exc_info=True)
        return False