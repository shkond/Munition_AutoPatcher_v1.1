import locale
from pathlib import Path

def read_text_utf8_fallback(path: Path) -> str:
    """
    UTF-8 でファイルを読み込み、失敗した場合はシステムのデフォルトエンコーディングで再試行する。
    """
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # UTF-8で失敗した場合、ロケール依存のエンコーディングでフォールバック
        fallback_encoding = locale.getpreferredencoding()
        return path.read_text(encoding=fallback_encoding, errors='replace')
