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
    Fallout4.esm を優先。Institute は LL_InstituteLaserGun をエイリアスで SimpleRifle にマップ。
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
                edid = (row.get('EditorID') or '').strip()
                formid = (row.get('FormID') or '').strip().upper()
                plugin = (row.get('SourceFile') or '').strip()
                if not edid:
                    continue
                edid_alias = aliases.get(edid, edid)
                if edid_alias not in desired:
                    continue
                prev = mapping.get(edid_alias)
                if prev is None or (plugin.lower() == 'fallout4.esm' and prev.get('plugin', '').lower() != 'fallout4.esm'):
                    if plugin and formid and len(formid) == 8:
                        mapping[edid_alias] = {'plugin': plugin, 'formid': formid}
    except Exception as e:
        logging.error(f"[Robco][LL] CSV 読込失敗: {e}")
        return {}

    for ed in desired:
        if ed in mapping:
            logging.info("[Robco][LL] 解決: %s -> %s|%s", ed, mapping[ed]['plugin'], mapping[ed]['formid'])
        else:
            logging.warning("[Robco][LL] 未解決: %s（CSVに行が無い/列名不一致/値欠落）", ed)
    return mapping

def _load_ll_from_json(output_dir: Path) -> dict:
    p = output_dir / "leveled_lists.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(_read_text_utf8_fallback(p))
        return data.get("LeveledLists", {}) or {}
    except Exception as e:
        logging.warning(f"[Robco][LL] leveled_lists.json 読込失敗（フォールバック無効）: {e}")
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

def run(config) -> bool:
    """
    Robco Patcher 用 INI を生成。
    - robco_ammo_patch.ini（常時）
    - robco_ll_patch.ini（入力が揃った場合のみ）
    """
    logging.info(f"{'-' * 10} ステップ4: Robco Patcher INI 生成 {'-' * 10}")
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
            logging.error(f"[Robco] weapon_ammo_map.json 読込失敗: {e}")
            return False

        ammo_map_dict = _load_ammo_map(ammo_map_file)
        ammo_classification: dict = strategy_data.get('ammo_classification', {})
        allocation_matrix: dict = strategy_data.get('allocation_matrix', {})
        faction_ll_map: dict = _get_target_ll_editorids()

        # LL 解決（CSV 優先、JSON フォールバック）
        ll_csv_map = _load_ll_from_csv(output_dir, leveled_lists_csv_cfg)
        ll_json_map = _load_ll_from_json(output_dir)
        ll_editorid_to_pf = ll_csv_map if ll_csv_map else ll_json_map

        # 診断
        logging.info("[Robco][診断] weapon_ammo_map.json 件数: %d", len(weapon_data))
        logging.info("[Robco][診断] ammo_classification 件数: %d", len(ammo_classification))
        cat_counter = Counter((info or {}).get("Category") for info in ammo_classification.values() if info)
        if cat_counter:
            logging.info("[Robco][診断] カテゴリ内訳:")
            for c, n in cat_counter.most_common():
                logging.info("  - %s: %d", c, n)
        logging.info("[Robco][診断] ammo_map マッピング数: %d", len(ammo_map_dict))
        logging.info("[Robco][診断] 使用 LL (EditorID): %s", ", ".join(faction_ll_map.values()))

        # 1) robco_ammo_patch.ini
        munitions_plugin_name = "Munitions - An Ammo Expansion.esl"
        ammo_lines = [
            "; Robco Ammo Patcher - Auto generated",
            f"; GeneratedAt={time.strftime('%Y-%m-%d %H:%M:%S')}",
            "; syntax: filterByAmmos=<Plugin>|<FormID>:ammoCategory=pistol|rifle:attackDamage=none:setNewProjectile=none:addToFormList=none",
            ""
        ]
        added_ammo = 0
        for formid_upper, info in ammo_classification.items():
            group = _category_to_group((info or {}).get("Category", ""))
            if not group:
                continue
            mapped = ammo_map_dict.get(formid_upper.lower(), formid_upper).upper()
            ammo_lines.append(
                f"filterByAmmos={munitions_plugin_name}|{mapped}:ammoCategory={group}:attackDamage=none:setNewProjectile=none:addToFormList=none"
            )
            added_ammo += 1

        robco_patcher_dir.mkdir(parents=True, exist_ok=True)
        ammo_out_path = robco_patcher_dir / "robco_ammo_patch.ini"
        if added_ammo > 0:
            ammo_out_path.write_text("\n".join(ammo_lines), encoding="utf-8")
            logging.info("[Robco][Ammo] 生成: %s (件数=%d, サイズ=%d bytes)",
                         ammo_out_path.name, added_ammo, ammo_out_path.stat().st_size)
        else:
            logging.warning("[Robco][Ammo] 生成対象 0 件")

        # 2) robco_ll_patch.ini（条件が揃えば生成）
        ll_lines = [
            "; Robco LL Patcher - Auto generated",
            f"; GeneratedAt={time.strftime('%Y-%m-%d %H:%M:%S')}",
            "; syntax: filterByLLs=<Plugin>|<FormID>:addToLLs=<Plugin>|<FormID>~1~1~<invertedChance>",
            ""
        ]
        added_ll = 0
        weapon_records = _read_weapon_records(
        output_dir,
        # 任意: config.ini に Paths.xedit_output_dir を追加しておくとここで参照されます
        config.get_path('Paths', 'xedit_output_dir') if hasattr(config, 'get_path') else None
        )

        if weapon_records and ll_editorid_to_pf and allocation_matrix:
            # ammo_formid -> category
            def ammo_category_for(fid: str) -> str | None:
                info = ammo_classification.get((fid or "").upper())
                return (info or {}).get("Category") if info else None

            for rec in weapon_records:
                ammo_fid = (rec.get("ammo_formid") or "").upper()
                weap_plugin = rec.get("plugin") or ""
                weap_fid = (rec.get("weap_formid") or "").upper()
                if not (weap_plugin and weap_fid and ammo_fid):
                    continue

                cat = ammo_category_for(ammo_fid)
                if not cat:
                    continue

                for faction, lli_editorid in faction_ll_map.items():
                    weight = (allocation_matrix.get(faction) or {}).get(cat, 0)
                    if weight <= 0:
                        continue

                    pf = ll_editorid_to_pf.get(lli_editorid) or {}
                    if not (pf.get("plugin") and pf.get("formid")):
                        logging.warning(f"[Robco][LL] LL 未解決: {lli_editorid}（CSV/JSON を確認）")
                        continue

                    inv = _invert_robco_chance(weight)
                    ll_lines.append(
                        f"filterByLLs={pf['plugin']}|{pf['formid']}:addToLLs={weap_plugin}|{weap_fid}~1~1~{inv}"
                    )
                    added_ll += 1

            if added_ll > 0:
                outp = robco_patcher_dir / "robco_ll_patch.ini"
                outp.write_text("\n".join(ll_lines), encoding="utf-8")
                logging.info("[Robco][LL] 生成: %s (行=%d, サイズ=%d bytes)", outp.name, added_ll, outp.stat().st_size)
            else:
                logging.warning("[Robco][LL] 生成対象 0 件（weapon_records / CSV/JSON / allocation_matrix を確認）")
        else:
            logging.info("[Robco][LL] 必要データ不足のためスキップ")

        return True

    except Exception as e:
        logging.critical(f"[Robco] 例外発生: {e}", exc_info=True)
        return False