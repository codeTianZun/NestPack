"""当前配置文件与编辑会话：加载、保存、回填及防抖自动保存。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from core.config import load_config, randomized_layer_names, save_config
from core.models import DEFAULT_CONFIG_PATH, AppConfig, ConfigError
from gui.config.binding import ConfigBinding
from gui.config.paths import freeze_config_paths
from gui.config.storage import (
    create_default_config,
    is_blank_template,
    load_remembered_config_path,
    remember_config_path,
)


class ConfigSession(QObject):
    """持有当前配置路径与待保存状态，通过绑定读写编辑界面。"""

    applied = Signal()
    path_changed = Signal(object)
    status = Signal(str)

    def __init__(self, parent: QObject, binding: ConfigBinding) -> None:
        super().__init__(parent)
        self.path = load_remembered_config_path() or DEFAULT_CONFIG_PATH
        self._binding = binding
        binding.setParent(self)
        binding.changed.connect(self.schedule_save)
        self._applying = False
        self._paused = False
        self._dirty = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(400)
        self._timer.timeout.connect(self.flush)

    def load_initial(self) -> None:
        """加载上次配置，文件不可用时展示默认三层模板。"""
        if self.path.exists():
            try:
                self.apply(load_config(self.path, allow_incomplete=True))
                self.status.emit(f"已载入配置：{self.path.name}")
                return
            except ConfigError as error:
                if is_blank_template(self.path):
                    self.status.emit("配置尚未填写，请先选择原始输入和输出目录。")
                else:
                    self.status.emit(f"配置不可用：{error}")
            except OSError as error:
                self.status.emit(f"配置不可用：{error}")
        config = create_default_config()
        self.apply(config)
        if not self.path.exists():
            try:
                self._write(self.path, config)
                self.status.emit("已创建默认配置文件")
            except OSError as error:
                self.status.emit(f"无法创建默认配置文件：{error}")

    def apply(self, config: AppConfig) -> None:
        """回填期间挂起变更记录，完成后通知窗口刷新联动。"""
        self._timer.stop()
        self._applying = True
        try:
            self._binding.apply(config)
            self.applied.emit()
        finally:
            self._applying = False
        self._dirty = False

    def load(self, path: Path) -> None:
        """加载并切换当前配置；读取失败时保留原会话。"""
        config = load_config(path, allow_incomplete=True)
        self._set_path(path)
        self.apply(config)
        self.status.emit("配置已载入")

    def save(self, path: Path | None = None) -> None:
        """保存当前草稿，指定新路径时切换当前配置文件。"""
        target = path.resolve() if path is not None else self.path
        config = self._binding.collect(strict=False)
        moved = target.parent != self.path.parent
        if moved:
            config = freeze_config_paths(config, self.path.parent)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._write(target, config)
        self._timer.stop()
        self._dirty = False
        if path is not None:
            self._set_path(path)
        if moved:
            self.apply(config)
        self.status.emit(f"配置已保存：{target.name}")

    def collect(self) -> AppConfig:
        """严格收集本次执行使用的配置快照，保留内存中的密码。"""
        return self._binding.collect()

    def prepare_execution(self, config: AppConfig) -> AppConfig:
        """生成本次层名并保存；随机名称同时回填界面。"""
        if config.randomize_layer_names:
            config = randomized_layer_names(config, self.path.parent)
        self._write(self.path, config)
        if config.randomize_layer_names:
            self.apply(config)
        self._timer.stop()
        self._dirty = False
        self.status.emit("本次配置已保存")
        return config

    def schedule_save(self) -> None:
        """记录编辑变更；执行期间保留待保存标记。"""
        if self._applying:
            return
        self._dirty = True
        self.status.emit("待保存" if not self._paused else "任务结束后保存")
        if not self._paused:
            self._timer.start()

    def set_execution_active(self, active: bool) -> None:
        """执行期间暂停自动写盘，结束后补存编辑变更。"""
        self._paused = active
        if active:
            self._timer.stop()
        else:
            self.flush()

    def flush(self) -> None:
        """保存待写入的草稿；输入尚不可保存或写盘失败时保留待保存标记。"""
        if self._paused or self._applying or not self._dirty:
            return
        try:
            self._write(self.path, self._binding.collect(strict=False))
        except (ValueError, OSError) as error:
            self.status.emit(f"尚未保存：{error}")
            return
        self._dirty = False
        self.status.emit("已自动保存")

    def _set_path(self, path: Path) -> None:
        self.path = path.resolve()
        remember_config_path(self.path)
        self.path_changed.emit(self.path)

    @staticmethod
    def _write(path: Path, config: AppConfig) -> None:
        save_config(path, config if config.persist_passwords else config.without_passwords())
