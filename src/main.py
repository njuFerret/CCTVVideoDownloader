import subprocess
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtGui import QIcon, QPixmap, QMovie, QDesktopServices

# from qt_material import apply_stylesheet

from MainUI import Ui_MainWindow as MainUI

# from logger import CustomLogger
from api import CCTVVideoDownloaderAPI as API
from download_engine import DownloadEngine as Engine
from video_process import VideoProcess as Process
from ImportUI import Ui_Dialog as ImportUI
from AboutUI import Ui_Dialog as AboutUI
from SettingUI import Ui_Dialog as SettingUI
from DownloadUI import Ui_Dialog as DownloadUI
from ConcatUI import Ui_Dialog as ConcatUI
import pathlib
import logging
from settings import dump_config, load_config


thisScript = pathlib.Path(__file__)
root = thisScript.parent
logLevel = logging.DEBUG
logFile = thisScript.with_name('CCTVVideoDownloader.log')
logging.getLogger("urllib3").setLevel(logging.WARNING)

# fmt:off
# Basic logging configuration
logging.basicConfig(
    level=logLevel,
    format='%(asctime)s %(filename)s(%(lineno)04d) [%(levelname)-8s]: %(message)s',
    handlers=[logging.FileHandler(logFile, mode='w', encoding='utf-8'), logging.StreamHandler()],
    datefmt='%Y-%m-%d %H:%M:%S'
)
# fmt:on

logger = logging.getLogger(__name__)


class CCTVVideoDownloader(QtWidgets.QMainWindow, MainUI):
    seasonsChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = MainUI()
        self.ui.setupUi(self)

        # self = None
        # self.config['settings'] = {}
        self._PROGRAMME = {}

        self._SELECT_ID = None  # 选中的栏目ID
        self._SELECT_INDEX = None  # 选中的节目索引

        self.api = API()
        self.worker = Engine()
        self.process = Process()

        self.fn_jsn_cfg = root.joinpath('config.json')
        self.config = load_config(self.fn_jsn_cfg)
        self.seasonsChanged.connect(self.onSeasonsChanged)
        self.initUserInterface()

    def initUserInterface(self):
        self.ui.pushButton.setEnabled(False)
        # 设置表格只读
        self.ui.tableWidget_Config.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        # 开启右键菜单
        self.ui.tableWidget_Config.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.tableWidget_Config.customContextMenuRequested.connect(self.seasonMenu)
        self.ui.tableWidget_Config.viewport().installEventFilter(self)
        self.ui.tableWidget_List.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        # 设置标题
        self.setWindowTitle("央视频下载器")
        # 设置图标
        self.setWindowIcon(QIcon(":/resources/cctvvideodownload.ico"))

        # 初始化
        self._flash_programme_list()

        # 连接信号与槽
        self._function_connect()

    @QtCore.pyqtSlot()
    def onSeasonsChanged(self):
        dump_config(self.config, self.fn_jsn_cfg)

    # def setup_ui(self) -> None:
    #     '''初始化'''
    #     # 初始化日志
    #     # logger = CustomLogger("CCTVVideoDownloader", "CCTVVideoDownloader.log")
    #     logger.info("程序初始化...")
    #     # 加载主UI
    #     self = QtWidgets.QMainWindow()
    #     # 实例化主UI
    #     self.main_ui = MainUI()
    #     # 输出日志
    #     logger.info("加载主UI...")
    #     # 加载UI
    #     self.main_ui.setupUi(self)
    #     # 锁定下载按钮
    #     self.main_ui.pushButton.setEnabled(False)
    #     # 设置表格只读
    #     self.main_ui.tableWidget_Config.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    #     # 开启右键菜单
    #     self.main_ui.tableWidget_Config.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    #     self.main_ui.tableWidget_Config.customContextMenuRequested.connect(self.seasonMenu)
    #     self.main_ui.tableWidget_Config.viewport().installEventFilter(self)
    #     self.main_ui.tableWidget_List.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    #     # 设置标题
    #     self.setWindowTitle("央视频下载器")
    #     # 设置图标
    #     self.setWindowIcon(QIcon(":/resources/cctvvideodownload.ico"))

    #     # 检查配置文件
    #     # self._checkout_config()

    #     # 初始化
    #     self._flash_programme_list()

    #     # 连接信号与槽
    #     self._function_connect()

    #     # 显示UI
    #     self.show()
    #     logger.info("程序初始化完成")

    def addSeasonMenuItem(self, menu, item: QtWidgets.QTableWidgetItem, parent: QtWidgets.QTableWidget):
        def remove_item(item, parent):
            # logger.debug(f'isinstance(item, QTableWidgetItem)={isinstance(item, QtWidgets.QTableWidgetItem)}')
            parent.removeRow(item.row())
            self.seasonsChanged.emit()

        def remove_all_item():
            parent.clearContents()
            self.config["programme"] = {}
            self.seasonsChanged.emit()

        act = QtWidgets.QAction(f"删除当前节目", self)
        act.triggered.connect(lambda: remove_item(item=item, parent=parent))
        menu.addAction(act)
        act = QtWidgets.QAction(f"删除当前节目", self)
        act.triggered.connect(remove_all_item)
        menu.addAction(act)

        # # 添加菜单项
        # delete_menu_item = QtWidgets.QMenu("删除", self)
        # parent.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # parent.customContextMenuRequested.connect(self.delete_season_menu_item)
        # act = QtGui.QAction("删除当前节目", self)
        # act.triggered.connect(lambda: self.delete_current_season())
        # delete_menu_item.addAction(act)
        # act = QtGui.QAction("删除所有节目", self)
        # act.triggered.connect(lambda: self.delete_all_seasons())
        # delete_menu_item.addAction(act)
        # menu.addMenu(delete_menu_item)

    def eventFilter(self, source, event):
        if (
            event.type() == QtCore.QEvent.MouseButtonPress
            and event.buttons() == QtCore.Qt.RightButton
            and source is self.ui.tableWidget_Config.viewport()
        ):
            item = self.ui.tableWidget_Config.itemAt(event.pos())
            # print('Global Pos:', event.globalPos())
            if item is not None:
                # print('Table Item:', item.row(), item.column())
                self.menu = QtWidgets.QMenu(self)
                logger.debug(f'isinstance(item, QTableWidgetItem)={isinstance(item, QtWidgets.QTableWidgetItem)}')
                # self.menu.addAction(item.text())  # (QAction('test'))
                self.addSeasonMenuItem(self.menu, item, self.ui.tableWidget_Config)

                # menu.exec_(event.globalPos())
        return super().eventFilter(source, event)

    def seasonMenu(self, pos):
        logger.debug(f"pos====== {pos}")
        self.menu.exec_(self.ui.tableWidget_Config.mapToGlobal(pos))  # +++

    def _flash_programme_list(self) -> None:
        '''刷新节目列表'''
        logger.info("刷新节目列表...")
        # 检查更新节目单
        # self._checkout_config()
        config = self.config['programme']
        self.ui.tableWidget_Config.setRowCount(len(config))
        # 遍历
        num = 0
        for i in config:
            dict_tmp = config[i]
            name = dict_tmp['name']
            id = dict_tmp['id']
            # 加入表格
            item1 = QtWidgets.QTableWidgetItem(name)
            item2 = QtWidgets.QTableWidgetItem(id)
            self.ui.tableWidget_Config.setItem(num, 0, item1)
            self.ui.tableWidget_Config.setItem(num, 1, item2)
            num += 1
        # 更新
        self.ui.tableWidget_Config.viewport().update()
        logger.info("栏目列表刷新完成")

    def _flash_video_list(self) -> None:
        '''刷新视频列表'''
        logger.info("刷新视频列表...")
        if self._SELECT_ID != None:
            seasons = self.config['programme']
            if seasons:
                # 获取节目信息
                video_information = self.api.get_video_list(self._SELECT_ID)
                if video_information is None:
                    logger.error(f'无法解析列表: {self._SELECT_ID}')
                    return
                self.VIDEO_INFO = video_information
                self.ui.tableWidget_List.setRowCount(len(video_information))
                self.ui.tableWidget_List.setColumnWidth(0, 300)
                # for i in range(len(video_information)):
                #     item1 = QtWidgets.QTableWidgetItem(video_information[i][2])
                #     self.ui.tableWidget_List.setItem(i, 0, item1)
                for i in range(len(video_information)):
                    item1 = QtWidgets.QTableWidgetItem(video_information[i][2])
                    self.ui.tableWidget_List.setItem(i, 0, item1)
                self.ui.tableWidget_List.viewport().update()

                logger.info("视频列表刷新完成")
            else:
                logger.error("节目单为空!")
                self._raise_warning("节目单为空!")
        else:
            logger.error("未选中栏目而试图刷新列表")
            self._raise_warning("您还未选择节目!")

    def _display_video_info(self) -> None:
        if self._SELECT_INDEX != None:
            # 获取信息
            video_info = self.api.get_column_info(self._SELECT_INDEX)
            # 将信息显示到label
            self.ui.label_title.setText(video_info['title'])
            self.ui.label_introduce.setText(video_info['brief'])
            time_new = video_info["time"].replace(" ", "\n")
            self.ui.label_time.setText(time_new)
            if video_info["image"] != None:
                pixmap = QPixmap()
                pixmap.loadFromData(video_info["image"])
                self.ui.label_img.setPixmap(pixmap)
            else:
                self.ui.label_img.setText("图片加载失败")
                self._raise_warning("图片获取失败")
                logger.warning("图片获取失败")
        else:
            pass

        # 恢复下载按钮
        self.ui.pushButton.setEnabled(True)

    def _is_program_selected(self, r: int, c: int) -> None:
        # 获取ID
        selected_item_id = self.ui.tableWidget_Config.item(r, 1).text()
        # 获取名称
        selected_item_name = self.ui.tableWidget_Config.item(r, 0).text()
        # 输出日志
        logger.info(f"选中栏目:{selected_item_name}, 视频ID: {selected_item_id}")
        # 设置ID
        self._SELECT_ID = selected_item_id

        self._flash_video_list()

    def _is_video_selected(self, r: int, c: int) -> None:
        # 获取INDEX
        self._SELECT_INDEX = self.ui.tableWidget_List.currentRow()
        # 输出日志
        logger.info(f"当前视频: {self._SELECT_INDEX}, ID: {333}")
        # 节目信息
        self._WILL_DOWNLOAD = {
            "name": self.VIDEO_INFO[self._SELECT_INDEX][2],
            "guid": self.VIDEO_INFO[self._SELECT_INDEX][0],
        }

        self._display_video_info()

    def _open_save_location(self) -> None:
        '''打开文件保存位置'''
        path = self.config['settings']["file_save_path"]
        command = ["explorer", path]
        # 创建STARTUPINFO对象以隐藏命令行窗口
        startupinfo = subprocess.STARTUPINFO()
        # startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(command, startupinfo=startupinfo)

    def _dialog_setting(self) -> None:
        '''设置对话框'''
        logger.info("打开设置")
        self._dialog_setting_base = QtWidgets.QDialog()
        self.dialog_setting = SettingUI()
        self.dialog_setting.setupUi(self._dialog_setting_base)
        # 锁定
        self.dialog_setting.radioButton_ts.setChecked(True)
        self.dialog_setting.radioButton_mp4.setEnabled(False)
        self.dialog_setting.radioButton_ts.setEnabled(False)
        # 锁定线程数上限与下限
        self.dialog_setting.spinBox.setMaximum(5)
        self.dialog_setting.spinBox.setMinimum(1)
        # 填充默认值
        self.dialog_setting.lineEdit_file_save_path.setText(self.config['settings']["file_save_path"])
        self.dialog_setting.spinBox.setValue(int(self.config['settings']["threading_num"]))

        # 绑定按钮
        def open_file_save_path():
            file_save_path = self.dialog_setting.lineEdit_file_save_path.text()
            file_save_path = QtWidgets.QFileDialog.getExistingDirectory(
                self._dialog_setting_base, "选择保存路径", file_save_path
            )
            if file_save_path:
                self.dialog_setting.lineEdit_file_save_path.setText(file_save_path)

        def save_settings():
            file_save_path = self.dialog_setting.lineEdit_file_save_path.text()
            thread_num = self.dialog_setting.spinBox.value()
            self.config['settings']["file_save_path"] = file_save_path
            self.config['settings']["threading_num"] = str(thread_num)
            logger.info(f"保存设置:{self.config['settings']}")
            # 更新配置
            import json

            with open("config.json", "r", encoding="utf-8") as f:
                config = json.loads(f.read())
            config["settings"] = self.config['settings']
            with open("config.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(config, indent=4))
            logger.info("配置已更新")

        self.dialog_setting.pushButton_open.clicked.connect(open_file_save_path)
        self.dialog_setting.buttonBox.accepted.connect(save_settings)

        self._dialog_setting_base.show()

    def _dialog_download(self) -> None:
        '''下载对话框'''
        logger.info("开始下载")
        logger.info(f"使用线程数:{self.config['settings']['threading_num']}")
        # 锁定下载按钮
        self.ui.pushButton.setEnabled(False)
        # 获取下载视频参数
        urls = self.api.get_m3u8_urls_450(self._WILL_DOWNLOAD["guid"])
        file_save_path = self.config['settings']["file_save_path"]
        name = self._WILL_DOWNLOAD["name"]
        self._dialog_download_base = QtWidgets.QDialog()
        self._dialog_concat_base = QtWidgets.QDialog()
        self.dialog_download = DownloadUI()
        self.dialog_concat = ConcatUI()
        self.dialog_download.setupUi(self._dialog_download_base)
        self._dialog_download_base.closeEvent = lambda event: self.worker.quit()
        self._dialog_download_base.closeEvent = lambda event: self.ui.pushButton.setEnabled(True)
        # 设置模态
        self._dialog_download_base.setModal(True)
        self._dialog_concat_base.setModal(True)
        # 去除边框
        self._dialog_concat_base.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        # 初始化表格
        self.dialog_download.tableWidget.setRowCount(len(urls) - 1)
        self.dialog_download.progressBar_all.setValue(0)
        self.dialog_download.tableWidget.setColumnWidth(0, 55)
        self.dialog_download.tableWidget.setColumnWidth(1, 65)
        self.dialog_download.tableWidget.setColumnWidth(2, 85)
        self.dialog_download.tableWidget.setColumnWidth(3, 70)

        def center_dialog_on_main_window(dialog, main_window):
            # 获取主窗口的几何信息
            main_window_rect = main_window.frameGeometry()
            # 获取屏幕中心点
            center_point = main_window_rect.center()
            # 设置对话框的位置为中心点
            dialog.move(center_point.x() - dialog.width() // 2, center_point.y() - dialog.height() // 2)

        # 在显示对话框之前调用函数设定位置
        center_dialog_on_main_window(self._dialog_download_base, self)
        self._dialog_download_base.show()

        self._progress_dict = {i: 0 for i in range(len(urls))}

        # 开始下载
        self.worker.transfer(name, urls, file_save_path, int(self.config['settings']["threading_num"]))
        self.worker.start()

        def video_concat():
            logger.info("开始视频拼接")
            self.process.transfer(self.config['settings']["file_save_path"], self._WILL_DOWNLOAD["name"])
            self.dialog_concat.setupUi(self._dialog_concat_base)
            # 在显示对话框之前调用函数设定位置
            center_dialog_on_main_window(self._dialog_concat_base, self)
            self._dialog_concat_base.show()
            self.process.concat()
            self.process.concat_finished.connect(finished)

        def finished(flag: bool):
            if flag:
                logger.info("视频拼接完成")
                # 解锁下载按钮
                self.ui.pushButton.setEnabled(True)
                self._dialog_concat_base.close()

        def display_info(info: list):
            '''将信息显示到表格中'''
            item1 = QtWidgets.QTableWidgetItem(str(info[0]))
            if info[1] == 1:
                item2 = QtWidgets.QTableWidgetItem("下载中")
            elif info[1] == 0:
                item2 = QtWidgets.QTableWidgetItem("完成")
            elif info[1] == -1:
                item2 = QtWidgets.QTableWidgetItem("等待")
            item3 = QtWidgets.QTableWidgetItem(info[2])
            item4 = QtWidgets.QTableWidgetItem(str(int(info[3])) + "%")
            self.dialog_download.tableWidget.setItem(int(info[0]) - 1, 0, item1)
            self.dialog_download.tableWidget.setItem(int(info[0]) - 1, 1, item2)
            self.dialog_download.tableWidget.setItem(int(info[0]) - 1, 2, item3)
            self.dialog_download.tableWidget.setItem(int(info[0]) - 1, 3, item4)

            self._progress_dict[info[0]] = int(info[3])
            total_progress = sum(self._progress_dict.values()) / len(self._progress_dict) * 2
            self.dialog_download.progressBar_all.setValue(int(total_progress))

            self.dialog_download.tableWidget.viewport().update()

            if total_progress == 100:
                logger.info("下载完成")
                self._dialog_download_base.close()
                # 调用拼接
                video_concat()

        # 生成信息列表
        num = 1
        info_list = []
        for i in urls:
            info = [str(num), -1, i, "0"]
            num += 1
            display_info(info)

        self.worker.download_info.connect(display_info)

    def _dialog_about(self) -> None:
        '''关于对话框'''
        # 输出日志
        logger.info("打开关于")
        self._dialog_about_base = QtWidgets.QDialog()
        self.dialog_about = AboutUI()
        self.dialog_about.setupUi(self._dialog_about_base)
        # 显示动图
        self._movie = QMovie(":/resources/afraid.gif")
        self.dialog_about.label_img.setMovie(self._movie)
        self._movie.setScaledSize(QtCore.QSize(100, 100))
        # 设置模态
        self._dialog_about_base.setModal(True)

        self._dialog_about_base.show()
        self._movie.start()
        # 链接
        self.dialog_about.label_link.setOpenExternalLinks(True)
        self.dialog_about.label_link.linkActivated.connect(
            lambda: QDesktopServices.openUrl(QtCore.QUrl("https://github.com/letr007/CCTVVideoDownloader"))
        )

    def _dialog_import(self) -> None:
        '''节目导入对话框'''
        logger.info("打开节目导入")
        self._dialog_import_base = QtWidgets.QDialog()
        self.dialog_import = ImportUI()
        self.dialog_import.setupUi(self._dialog_import_base)
        # 设置模态
        self._dialog_import_base.setModal(True)
        self._dialog_import_base.show()
        url = None

        # 此处获取视频列表
        def url():
            # 获取值
            url = self.dialog_import.lineEdit.text()
            self._dialog_import_base.close()
            # 请求获取节目信息
            column_info = self.api.get_play_column_info(url)
            if column_info != None:
                import json

                with open("config.json", "r", encoding="utf-8") as f:
                    # 读取配置文件
                    config = json.loads(f.read())
                # 获取当前最大的 key 值，并自增
                max_key = max(map(int, config["programme"].keys())) + 1 if config["programme"] else 1
                # 检查 id 是否已经存在
                for prog in config["programme"].values():
                    if prog["id"] == column_info[1]:
                        logger.warning(f"节目ID [{column_info[1]}] 已存在")
                        return

                config["programme"][str(max_key)] = {"name": column_info[0], "id": column_info[1]}
                with open("config.json", "w+", encoding="utf-8") as f:
                    # 写入配置文件
                    f.write(json.dumps(config, indent=4, ensure_ascii=False))

                self._flash_programme_list()

                logger.info(f"导入节目:{column_info[0]}")

        self.dialog_import.buttonBox.accepted.connect(url)

    def _function_connect(self) -> None:
        '''连接信号与槽'''
        # 绑定退出
        self.ui.actionexit.triggered.connect(self.close)
        # 绑定刷新按钮
        self.ui.flash_list.clicked.connect(self._flash_video_list)
        self.ui.flash_program.clicked.connect(self._flash_programme_list)
        # 绑定栏目表格点击事件
        self.ui.tableWidget_Config.cellClicked.connect(self._is_program_selected)
        # 绑定节目表格点击事件
        self.ui.tableWidget_List.cellClicked.connect(self._is_video_selected)
        # 绑定导入
        self.ui.actionimport.triggered.connect(self._dialog_import)
        # 绑定关于
        self.ui.actionabout.triggered.connect(self._dialog_about)
        # 绑定打开文件保存位置
        self.ui.actionfile.triggered.connect(self._open_save_location)
        # 绑定设置
        self.ui.actionsetting.triggered.connect(self._dialog_setting)
        # 绑定下载
        self.ui.pushButton.clicked.connect(self._dialog_download)

    # def _checkout_config(self) -> None:
    #     '''检查配置文件'''
    #     import json

    #     jsn_cfg = root.joinpath("config.json")
    #     if not jsn_cfg.exists():

    #     try:
    #         with open("config.json", "r", encoding="utf-8") as f:
    #             # 读取配置文件
    #             config = json.loads(f.read())
    #             self.config['settings'] = config["settings"]
    #             self._PROGRAMME = config["programme"]
    #             logger.info("读取配置文件成功")
    #     except Exception as e:
    #         logger.error("读取配置文件失败")
    #         logger.debug(f"错误详情:{e}")
    #         self._raise_error(e)
    #         return

    def _raise_error(self, error: Exception) -> None:
        '''错误抛出,仅抛出引发程序异常退出的错误'''
        logger.critical("程序异常退出")
        logger.critical(f"错误详情:{error}")
        # 给出错误提示窗口
        import sys, os

        path = os.getcwd()
        path = os.path.join(path, "CCTVVideoDownloader.log")
        QtWidgets.QMessageBox.critical(self, "错误", f"错误详情:\n{error}\n请检查日志文件\n{path}")
        sys.exit(1)

    def _raise_warning(self, warning: str) -> None:
        '''警告抛出,抛出警告'''
        QtWidgets.QMessageBox.warning(self, "警告", warning)


def main():
    import sys

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
    # 创建QApplication对象，它是整个应用程序的入口
    app = QtWidgets.QApplication(sys.argv)
    # 美化主题
    # apply_stylesheet(app, theme='dark_blue.xml')
    # 实例化主类
    CTVD = CCTVVideoDownloader()
    # 初始化UI
    CTVD.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
