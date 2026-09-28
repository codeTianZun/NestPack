"""默认层和来源独立层的编辑快照，不依赖 Qt。"""

from dataclasses import dataclass, field, replace
from pathlib import Path

from core.config import parse_config
from core.filesystem import normalize_user_path
from core.models import AppConfig, LayerConfig
from core.source_layers import default_source_layers


@dataclass
class LayerDrafts:
    """来源首次编辑时保存整套快照，恢复默认时移除快照。"""

    defaults: list[LayerConfig] = field(default_factory=list)
    sources: dict[Path, list[LayerConfig]] = field(default_factory=dict)

    def retain_sources(self, sources: list[str], config_dir: Path) -> None:
        paths = {normalize_user_path(path, config_dir) for path in sources}
        self.sources = {path: layers for path, layers in self.sources.items() if path in paths}

    def apply(self, config: AppConfig, config_dir: Path) -> None:
        self.defaults = list(config.layers)
        self.sources = {normalize_user_path(path, config_dir): list(layers)
                        for path, layers in config.source_layers.items()}
        self.retain_sources(config.effective_source_paths(), config_dir)

    def layers_for(self, source: Path | None, config_dir: Path) -> list[LayerConfig]:
        if source is None:
            return list(self.defaults)
        if source in self.sources:
            return list(self.sources[source])
        return default_source_layers(self.defaults, source, config_dir)

    def store(self, source: Path | None, layers: list[LayerConfig]) -> None:
        if source is None:
            self.defaults = list(layers)
        else:
            self.sources[source] = list(layers)

    def reset(self, source: Path) -> None:
        self.sources.pop(source, None)

    def collect(self, config: AppConfig, *, strict: bool) -> AppConfig:
        snapshot = replace(config, layers=list(self.defaults), source_layers={
            str(path): list(layers) for path, layers in self.sources.items()
        })
        return parse_config(snapshot.to_json_dict(), allow_incomplete=not strict)

    def passwords(self) -> list[str]:
        return list(dict.fromkeys(
            layer.password for layers in [self.defaults, *self.sources.values()]
            for layer in layers if layer.password
        ))
