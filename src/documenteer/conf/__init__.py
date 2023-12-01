from ._toml import DocumenteerConfig
from ._utils import (
    extend_static_paths_with_asset_extension,
    get_asset_path,
    get_template_dir,
)

__all__ = [
    "get_asset_path",
    "extend_static_paths_with_asset_extension",
    "get_template_dir",
    "DocumenteerConfig",
]
