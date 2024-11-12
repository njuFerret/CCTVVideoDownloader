import pathlib
import json
import logging

logger = logging.getLogger('__name__')
# 默认配置文件名
default_config_file = pathlib.Path("__file__").with_name("config.log")

DEFAULT_CONFIG = {
    "settings": {"file_save_path": "C:\\Video", "threading_num": "1", "whether_transcode": "False"},
    "programme": {},
}
# programme为节目单


def dump_default_config(fn_cfg=default_config_file):
    dump_config(config=DEFAULT_CONFIG, fn_cfg=fn_cfg)


def dump_config(config, fn_cfg=default_config_file):
    if isinstance(fn_cfg, str):
        fn_cfg = pathlib.Path(fn_cfg)
    elif not isinstance(fn_cfg, pathlib.Path):
        raise Exception(f"配置文件名错误: \n -> {fn_cfg}")

    # 无论有没有文件, 创建配置文件
    with fn_cfg.open('w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def load_config(fn_cfg=default_config_file):

    if isinstance(fn_cfg, str):
        fn_cfg = pathlib.Path(fn_cfg)
    elif not isinstance(fn_cfg, pathlib.Path):
        raise Exception(f"配置文件名错误: \n -> {fn_cfg}")

    # 如果配置文件不存在，则创建默认配置文件
    if not fn_cfg.exists():
        dump_default_config(fn_cfg=fn_cfg)

    # 读取配置json
    with fn_cfg.open('r', encoding='utf-8') as f:
        result = json.load(f)
        logger.debug(result)
        return result
