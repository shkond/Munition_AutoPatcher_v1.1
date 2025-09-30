# =============================================================================
# Munitions 自動統合フレームワーク v2.1
#
# config_manager.py
#
# 変更履歴:
# v2.1 (2025-09-29):
#   - get_stringメソッドを追加。
#   - get_booleanメソッドを追加。
#   - パスを読み込む際に os.path.normpath を適用し、'/' と '\' の混在を吸収するようにした。
# =============================================================================

import configparser
from pathlib import Path
import os

class ConfigManager:
    """
    config.ini ファイルの読み込みとアクセスを管理するクラス。
    型変換、パス解決、エラーハンドリングを一元的に担う。
    """
    def __init__(self, config_path: str = 'config.ini'):
        """
        指定されたパスから設定ファイルを読み込み、初期化する。
        :param config_path: config.ini ファイルへのパス。
        """
        self.config_path = Path(config_path).resolve()
        if not self.config_path.is_file():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {self.config_path}")

        self.config = configparser.ConfigParser(interpolation=configparser.BasicInterpolation())
        self.config.read(self.config_path, encoding='utf-8')

        # project_rootがconfig.iniで指定されていればそれを使い、
        # なければconfig.iniファイルのあるディレクトリを基準にする
        project_root_str = self.get_string('Paths', 'project_root', '.')
        # config.ini自身の場所を基準に解決することで、より堅牢にする
        self.project_root = (self.config_path.parent / project_root_str).resolve()

    def _resolve_path(self, path_str: str) -> Path:
        """
        文字列のパスを正規化し、絶対パスの Path オブジェクトに変換する。
        'project_root' を基準に解決する。
        """
        # スラッシュとバックスラッシュの混在を吸収
        normalized_path_str = os.path.normpath(path_str)
        p = Path(normalized_path_str)

        if not p.is_absolute():
            return (self.project_root / p).resolve()
        return p.resolve()

    def get_path(self, section: str, key: str) -> Path:
        """指定されたセクションとキーからパスを Path オブジェクトとして返す。"""
        return self._resolve_path(self.config.get(section, key))

    def get_string(self, section: str, key: str, fallback: str = '') -> str:
        """指定されたセクションとキーから値を文字列として返す。"""
        return self.config.get(section, key, fallback=fallback)

    def get_boolean(self, section: str, key: str, fallback: bool = False) -> bool:
        """指定されたセクションとキーから値を真偽値として返す。"""
        return self.config.getboolean(section, key, fallback=fallback)

    def get_script_filename(self, key: str) -> str:
        """'Scripts' セクションからスクリプトのファイル名を返す。"""
        return self.get_string('Scripts', key)

    def get_env_settings(self) -> dict:
        """[Environment] セクションの設定を辞書として返す。"""
        use_mo2 = self.get_boolean('Environment', 'use_mo2')
        settings = {'use_mo2': use_mo2}
        if use_mo2:
            settings['mo2_executable_path'] = os.path.normpath(self.get_string('Environment', 'mo2_executable_path'))
            settings['xedit_profile_name'] = self.get_string('Environment', 'xedit_profile_name')
            settings['game_data_path'] = self.get_path('Paths', 'game_data_path')
            # Overwriteディレクトリのパスを取得
            # ★★★ 修正点: Orchestratorから 'overwrite_path' として参照できるようにする ★★★
            overwrite_dir = self.get_string('Environment', 'mo2_overwrite_dir')
            self.config.set('Paths', 'overwrite_path', overwrite_dir)
        return settings

    def get_parameter(self, key: str) -> str:
        """[Parameters] セクションから指定されたパラメータを文字列として返す。"""
        return self.get_string('Parameters', key)

    def save_setting(self, section: str, key: str, value: str):
        """設定を保存する。GUIからの呼び出しを想定。"""
        self.config.set(section, key, value)
        with open(self.config_path, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
