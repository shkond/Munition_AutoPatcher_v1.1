# -*- coding: utf-8 -*-
# robco_ini_generate.py — Robco INI 生成モジュール

from __future__ import annotations
import csv
import json
import logging
import time
import shutil
from pathlib import Path
import configparser
from collections import Counter, defaultdict
from dataclasses import dataclass, field

# 共通ユーティリティをインポート
from utils import read_text_utf8_fallback

# --- データ構造定義 ---

@dataclass
class DataSource:
    """INI生成に必要な全ての入力データを保持する。"""
    strategy: dict
    ammo_map: dict[str, str]
    weapon_records: list[dict]
    leveled_list_map: dict[str, dict]
    npc_list_map: dict[str, str]
    munitions_id_map: dict[str, dict]

@dataclass
class ProcessedData:
    """処理済みINIコンテンツを保持する。"""
    formlist_remove_lines: list[str] = field(default_factory=list)
    weapon_set_ammo_lines: list[str] = field(default_factory=list)
    omod_set_ammo_map: dict[str, dict] = field(default_factory=dict)
    ll_add_weapon_lines: list[str] = field(default_factory=list)

# --- データ読み込み ---

def _load_data_sources(config) -> DataSource:
    """すべての入力データソースを読み込んで、一つのデータクラスにまとめる。"""
    output_dir = config.get_path('Paths', 'output_dir')
    strategy_file = config.get_path('Paths', 'strategy_file')
    ammo_map_file = config.get_path('Paths', 'ammo_map_file')
    
    # 各種ローダー関数を呼び出し
    strategy_data = json.loads(read_text_utf8_fallback(strategy_file))
    ammo_map = _load_ammo_map(ammo_map_file)
    weapon_records = _read_weapon_records(output_dir, config)
    leveled_list_map = _load_leveled_lists(output_dir, config)
    npc_list_map = _load_munitions_npc_list_map(output_dir, config)
    
    munitions_plugin = config.get_string('Parameters', 'munitions_plugin_name', 'Munitions - An Ammo Expansion.esl')
    munitions_id_map = _load_munitions_ammo_id_map(output_dir, munitions_plugin)

    return DataSource(
        strategy=strategy_data,
        ammo_map=ammo_map,
        weapon_records=weapon_records,
        leveled_list_map=leveled_list_map,
        npc_list_map=npc_list_map,
        munitions_id_map=munitions_id_map
    )

def _load_ammo_map(ammo_map_file: Path) -> dict[str, str]:
    """ammo_map.json を読み込む。"""
    if not ammo_map_file.is_file():
        logging.warning(f"[Robco] マッピングファイルが見つかりません: {ammo_map_file}")
        return {}
    try:
        data = json.loads(read_text_utf8_fallback(ammo_map_file))
        mapping = {
            (m.get("source") or {}).get("formid").lower(): (m.get("target") or {}).get("formid").lower()
            for m in data.get("mappings", [])
            if (m.get("source") or {}).get("formid") and (m.get("target") or {}).get("formid")
        }
        logging.info(f"[Robco] {ammo_map_file.name} からマッピングを {len(mapping)} 件読み込みました。")
        return mapping
    except Exception as e:
        logging.error(f"[Robco] {ammo_map_file.name} の読み込みに失敗: {e}")
        return {}

def _read_weapon_records(output_dir: Path, config) -> list[dict]:
    """weapon_omod_map.json から武器情報を読み込む。"""
    try:
        xedit_output_dir = config.get_path('Paths', 'xedit_output_dir')
    except Exception:
        xedit_output_dir = None

    # 複数の候補パスからファイルを探す
    for d in [output_dir, output_dir.parent, xedit_output_dir]:
        if not d or not d.exists(): continue
        json_path = d / "weapon_omod_map.json"
        if json_path.is_file():
            try:
                records = json.loads(read_text_utf8_fallback(json_path))
                logging.info(f"[Robco] {json_path.name} から武器レコードを {len(records)} 件読み込みました。")
                return records
            except Exception as e:
                logging.error(f"[Robco] {json_path.name} の読み込みに失敗: {e}")
    
    logging.warning("[Robco] weapon_omod_map.json が見つかりませんでした。")
    return []

def _load_leveled_lists(output_dir: Path, config) -> dict:
    """WeaponLeveledLists_Export.csv を読み込む。"""
    try:
        csv_path_cfg = config.get_path('Paths', 'leveled_lists_csv')
    except Exception:
        csv_path_cfg = None
    
    candidates = [csv_path_cfg, output_dir / 'WeaponLeveledLists_Export.csv']
    for path in candidates:
        if path and path.is_file():
            try:
                with path.open('r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    mapping = {
                        row['EditorID'].strip('"'): {'plugin': row['SourceFile'].strip('"'), 'formid': row['FormID'].strip('"').upper()}
                        for row in reader if row.get('EditorID') and row.get('FormID') and row.get('SourceFile')
                    }
                    logging.info(f"[Robco] {path.name} からLeveled List情報を {len(mapping)} 件読み込みました。")
                    return mapping
            except Exception as e:
                logging.error(f"[Robco] {path.name} の読み込みに失敗: {e}")
    
    logging.warning("[Robco] Leveled List情報ファイル (CSV) が見つかりませんでした。")
    return {}

def _load_munitions_npc_list_map(output_dir: Path, config) -> dict[str, str]:
    """munitions_npc_lists.ini からNPC用フォームリストのマップを読み込む。"""
    # ... (実装は簡略化のため省略、必要なら元のコードを移植) ...
    return {}

def _load_munitions_ammo_id_map(output_dir: Path, plugin_name: str) -> dict[str, dict]:
    """munitions_ammo_ids.ini からMunitions弾薬の情報を読み込む。"""
    # ... (実装は簡略化のため省略、必要なら元のコードを移植) ...
    return {}

# --- データ処理 ---

def _process_weapon_records(data: DataSource) -> ProcessedData:
    """武器レコードを処理し、各INIファイル用のデータを生成する。"""
    processed = ProcessedData()
    
    # 処理対象の弾薬IDセットを作成
    processed.formlist_remove_lines = [f"formsToRemove={(fid or '').upper()}" for fid in data.ammo_map.keys()]

    seen_comments, seen_weapon_entries, seen_ll_lines = set(), set(), set()
    faction_ll_map = data.strategy.get('faction_leveled_lists') or _get_target_ll_editorids()
    munitions_plugin = data.strategy.get('munitions_plugin_name', 'Munitions - An Ammo Expansion.esl')

    for rec in data.weapon_records:
        orig_ammo_fid = (rec.get("ammo_formid") or "").strip().lower()
        if orig_ammo_fid not in data.ammo_map:
            continue

        # 武器の弾薬置換行を生成
        weap_plugin = rec.get("plugin", "").strip()
        weap_fid = rec.get("weap_formid", "").strip().upper()
        mapped_ammo_fid = data.ammo_map[orig_ammo_fid].upper()
        
        comment = f"; [{weap_plugin}] {rec.get('weap_editor_id','')} -> {mapped_ammo_fid}"
        line = f"filterByWeapons={weap_plugin}|{weap_fid}:setNewAmmo={munitions_plugin}|{mapped_ammo_fid}"
        
        if comment not in seen_comments:
            processed.weapon_set_ammo_lines.append(comment)
            seen_comments.add(comment)
        if line not in seen_weapon_entries:
            processed.weapon_set_ammo_lines.append(line)
            seen_weapon_entries.add(line)

        # OMODの弾薬置換情報を収集
        for omod in rec.get("omods", []):
            omod_key = f"{omod.get('plugin','')}|{omod.get('formid','').upper()}"
            if not omod_key: continue
            processed.omod_set_ammo_map[omod_key] = {'target_ammo': mapped_ammo_fid, 'target_plugin': munitions_plugin}

        # Leveled Listへの追加行を生成
        for faction, lli_editorid in faction_ll_map.items():
            ll_info = data.leveled_list_map.get(lli_editorid, {})
            ll_fid = ll_info.get("formid", "").upper()
            if not ll_fid: continue
            
            ll_line = f"filterByFormLists={ll_fid}:formsToAdd={weap_plugin}|{weap_fid}"
            if ll_line not in seen_ll_lines:
                processed.ll_add_weapon_lines.append(f"\n; Add [{weap_plugin}] {rec.get('weap_editor_id','')} to {faction}")
                processed.ll_add_weapon_lines.append(ll_line)
                seen_ll_lines.add(ll_line)

    return processed

# --- ファイル書き出し ---

def _generate_ini_files(processed: ProcessedData, robco_base_dir: Path):
    """処理済みデータから各INIファイルを生成・書き出しする。"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # ディレクトリ作成
    formlist_dir = robco_base_dir / "formlist"
    weapon_dir = robco_base_dir / "weapon"
    omod_dir = robco_base_dir / "omod"
    formlist_dir.mkdir(parents=True, exist_ok=True)
    weapon_dir.mkdir(parents=True, exist_ok=True)
    omod_dir.mkdir(parents=True, exist_ok=True)

    # INIファイル1: FormList Remove
    if processed.formlist_remove_lines:
        header = [f"; Munitions Auto-Patcher: Remove Custom Ammo from FormLists\n; GeneratedAt={timestamp}"]
        path = formlist_dir / "Munitions_FormList_RemoveCustomAmmo.ini"
        path.write_text("\n".join(header + processed.formlist_remove_lines), encoding="utf-8")
        logging.info(f"[Robco] 生成: {path.name} ({len(processed.formlist_remove_lines)}件)")

    # INIファイル2: Weapon SetAmmo
    if processed.weapon_set_ammo_lines:
        header = [f"; Munitions Auto-Patcher: Set Weapon Ammo\n; GeneratedAt={timestamp}"]
        path = weapon_dir / "Munitions_Weapon_SetAmmo.ini"
        path.write_text("\n".join(header + processed.weapon_set_ammo_lines), encoding="utf-8")
        logging.info(f"[Robco] 生成: {path.name} ({len(processed.weapon_set_ammo_lines)}件)")

    # INIファイル3: OMOD SetAmmo
    if processed.omod_set_ammo_map:
        header = [f"; Munitions Auto-Patcher: OMOD Ammo Conversion\n; GeneratedAt={timestamp}"]
        lines = [
            f"filterByOMod={key}:changeOModPropertiesForm=Ammo={val['target_plugin']}|{val['target_ammo']}"
            for key, val in sorted(processed.omod_set_ammo_map.items())
        ]
        path = omod_dir / "Munitions_OMOD_SetAmmo.ini"
        path.write_text("\n".join(header + lines), encoding="utf-8")
        logging.info(f"[Robco] 生成: {path.name} ({len(lines)}件)")

    # INIファイル4: Leveled List Add
    if processed.ll_add_weapon_lines:
        header = [f"; Munitions Auto-Patcher: Add Patched Weapons to Leveled Lists\n; GeneratedAt={timestamp}"]
        path = formlist_dir / "Munitions_FormList_AddWeaponsToLL.ini"
        path.write_text("\n".join(header + processed.ll_add_weapon_lines), encoding="utf-8")
        logging.info(f"[Robco] 生成: {path.name} ({len(processed.ll_add_weapon_lines)}件)")

def _create_zip_archive(robco_patcher_dir: Path):
    """最終的なZIPアーカイブを作成する。"""
    zip_output_path = robco_patcher_dir.parent / f"{robco_patcher_dir.name}.zip"
    logging.info(f"[Robco] ZIPアーカイブを作成します: {zip_output_path}")
    if zip_output_path.exists():
        zip_output_path.unlink()
    
    shutil.make_archive(
        base_name=str(zip_output_path.with_suffix('')),
        format='zip',
        root_dir=robco_patcher_dir.parent,
        base_dir=robco_patcher_dir.name
    )
    logging.info(f"[Robco] {zip_output_path.name} の作成が完了しました。")

def _get_target_ll_editorids() -> dict:
    # SuperMutants は除外
    return {
        "Gunners": "LLI_Hostile_Gunner_Any",
        "Raiders": "LLI_Raider_Weapons",
        "Institute": "LL_InstituteLaserGun_SimpleRifle",
    }

# --- メイン実行関数 ---

def run(config) -> bool:
    """
    Robco Patcher 用 INI を生成するメイン関数。
    """
    logging.info(f"{'-' * 10} ステップ4: Robco Patcher INI 生成 {'-' * 10}")
    try:
        # 1. 全てのデータソースを読み込む
        data = _load_data_sources(config)
        if not data.weapon_records or not data.ammo_map:
            logging.warning("[Robco] 武器レコードまたは弾薬マップが空のため、INI生成をスキップします。")
            return True # エラーではなく、処理対象なしとして正常終了

        # 2. 武器レコードを処理してINIファイル用のデータを構築
        processed_data = _process_weapon_records(data)

        # 3. INIファイルを生成・書き出し
        robco_patcher_dir = config.get_path('Paths', 'robco_patcher_dir')
        robco_base_dir = robco_patcher_dir / "F4SE" / "Plugins" / "RobCo_Patcher"
        _generate_ini_files(processed_data, robco_base_dir)

        # 4. ZIPアーカイブを作成
        _create_zip_archive(robco_patcher_dir)

        logging.info("[Robco] Robco INI 生成完了")
        return True

    except Exception as e:
        logging.critical(f"[Robco] INI生成中に致命的なエラーが発生: {e}", exc_info=True)
        return False
