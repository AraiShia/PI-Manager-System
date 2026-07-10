"""文件对话框辅助函数"""
from PySide6.QtWidgets import QFileDialog, QMessageBox


def open_file_dialog(parent, title: str, filter_str: str) -> str:
    """打开文件选择对话框"""
    dialog = QFileDialog(parent, title)
    dialog.setNameFilter(filter_str)
    dialog.setFileMode(QFileDialog.ExistingFile)
    if dialog.exec():
        files = dialog.selectedFiles()
        return files[0] if files else ""
    return ""


def save_file_dialog(parent, title: str, default_name: str, filter_str: str) -> str:
    """打开保存文件对话框"""
    dialog = QFileDialog(parent, title)
    dialog.setAcceptMode(QFileDialog.AcceptSave)
    dialog.selectFile(default_name)
    dialog.setNameFilter(filter_str)
    if dialog.exec():
        files = dialog.selectedFiles()
        return files[0] if files else ""
    return ""


def excel_filter() -> str:
    return "Excel Files (*.xlsx *.xls);;All Files (*)"


def show_info(parent, title: str, message: str):
    QMessageBox.information(parent, title, message)


def show_error(parent, title: str, message: str):
    QMessageBox.critical(parent, title, message)
