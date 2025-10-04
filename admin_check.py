"""
管理者権限確認ユーティリティ
Windows環境でのみ動作します
"""

import sys
import ctypes
import logging
from pathlib import Path


def is_admin() -> bool:
    """
    現在のプロセスが管理者権限で実行されているかを確認します。
    
    Returns:
        bool: 管理者権限の場合 True、それ以外 False
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logging.warning(f"管理者権限の確認に失敗しました: {e}")
        return False


def require_admin(message: str = "このアプリケーションは管理者権限で実行する必要があります。"):
    """
    管理者権限を要求し、権限がない場合はエラーメッセージを表示して終了します。
    
    Args:
        message: 権限がない場合に表示するメッセージ
    """
    if not is_admin():
        logging.error(message)
        print(f"\n[エラー] {message}")
        print("\n対処方法:")
        print("  1. PowerShell または コマンドプロンプトを「管理者として実行」で開く")
        print("  2. 以下のコマンドを実行:")
        print(f"     cd {Path.cwd()}")
        print(f"     python {sys.argv[0]}")
        print("\nまたは、アプリケーションのショートカットを右クリック → 「管理者として実行」")
        sys.exit(1)


def request_admin_elevation():
    """
    管理者権限で再起動を試みます (Windows のみ)。
    
    Returns:
        bool: 再起動に成功した場合 True (この関数からは戻らない)
              失敗した場合 False
    """
    if is_admin():
        return True
    
    try:
        # ShellExecuteW を使って管理者権限で再起動
        script = sys.argv[0]
        params = ' '.join(sys.argv[1:])
        
        result = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # lpOperation (管理者として実行)
            sys.executable, # lpFile (Python インタープリタ)
            f'"{script}" {params}',  # lpParameters
            None,           # lpDirectory
            1               # nShowCmd (SW_SHOWNORMAL)
        )
        
        # result > 32 なら成功
        if result > 32:
            sys.exit(0)  # 現在のプロセスを終了
        else:
            logging.warning(f"管理者権限での再起動に失敗しました (エラーコード: {result})")
            return False
            
    except Exception as e:
        logging.error(f"管理者権限要求中にエラーが発生しました: {e}")
        return False


def check_file_access(file_path: Path, mode: str = 'r') -> bool:
    """
    指定されたファイルへのアクセス権限を確認します。
    
    Args:
        file_path: 確認するファイルのパス
        mode: アクセスモード ('r': 読み取り, 'w': 書き込み, 'rw': 読み書き)
    
    Returns:
        bool: アクセス可能な場合 True
    """
    import os
    
    if not file_path.exists():
        logging.warning(f"ファイルが存在しません: {file_path}")
        return False
    
    try:
        if 'r' in mode:
            # 読み取りテスト
            with open(file_path, 'r') as f:
                f.read(1)
        
        if 'w' in mode:
            # 書き込みテスト (実際には書き込まない)
            if os.access(file_path, os.W_OK):
                return True
            else:
                logging.warning(f"書き込み権限がありません: {file_path}")
                return False
        
        return True
        
    except PermissionError:
        logging.error(f"アクセス権限がありません: {file_path}")
        return False
    except Exception as e:
        logging.error(f"アクセス確認中にエラーが発生しました: {e}")
        return False


def check_directory_access(dir_path: Path, check_write: bool = True) -> bool:
    """
    指定されたディレクトリへのアクセス権限を確認します。
    
    Args:
        dir_path: 確認するディレクトリのパス
        check_write: 書き込み権限も確認する場合 True
    
    Returns:
        bool: アクセス可能な場合 True
    """
    import os
    
    if not dir_path.exists():
        logging.warning(f"ディレクトリが存在しません: {dir_path}")
        return False
    
    try:
        # 読み取りテスト
        list(dir_path.iterdir())
        
        if check_write:
            # 書き込みテスト (一時ファイル作成)
            test_file = dir_path / f".access_test_{os.getpid()}.tmp"
            try:
                test_file.touch()
                test_file.unlink()
                return True
            except PermissionError:
                logging.warning(f"書き込み権限がありません: {dir_path}")
                return False
        
        return True
        
    except PermissionError:
        logging.error(f"ディレクトリへのアクセス権限がありません: {dir_path}")
        return False
    except Exception as e:
        logging.error(f"アクセス確認中にエラーが発生しました: {e}")
        return False


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("管理者権限確認ツール")
    print("=" * 60)
    
    if is_admin():
        print("\n✓ このプロセスは管理者権限で実行されています")
    else:
        print("\n✗ このプロセスは管理者権限で実行されていません")
        print("\n管理者権限で再起動しますか? (y/n): ", end="")
        
        response = input().lower()
        if response == 'y':
            print("管理者権限で再起動中...")
            if not request_admin_elevation():
                print("再起動に失敗しました。手動で管理者として実行してください。")