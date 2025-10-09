# ★★★ 最終修正: startコマンドを使用して起動する ★★★
batch_content = (
    f'@echo off\n'
    f'echo Changing directory to {mo2_directory}\n'
    f'cd /d "{mo2_directory}"\n'
    f'echo Launching Mod Organizer...\n'
    f'start "" {command_string}\n'
)