import configparser

_conf = None


def config():
    global _conf
    if _conf is None:
        # 创建配置解析器对象
        _conf = configparser.ConfigParser()
        # 读取 ini 配置文件
        _conf.read('../config.ini', encoding="utf-8-sig")
    return _conf
