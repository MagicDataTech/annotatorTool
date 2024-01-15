import io

import minio

from utils.config import config

client = None
bucket_name = config().get("APP", 'BUCKET_NAME')
endpoint_text = config().get("APP", 'ENDPOINT_TEXT')


def get_minio():
    global client
    # 创建 MinIO 客户端
    if client is None:
        minio_conf = {
            'endpoint': config().get("APP", 'ENDPOINT'),
            'access_key': config().get("APP", 'ACCESS_KEY'),
            'secret_key': config().get("APP", 'SECRET_KEY'),
            # 如开启 https 为 True
            'secure': config().getboolean("APP", 'SECURE')
        }
        client = minio.Minio(**minio_conf)
    return client


# 本地文件地址，对象存储地址
def upload_file(file_path, object_dir):
    global bucket_name
    global endpoint_text
    # 上传文件
    get_minio().fput_object(bucket_name, object_dir, file_path)
    return f"{endpoint_text}/{bucket_name}/{object_dir}"


def upload_string_to_minio(object_name, content):
    global bucket_name
    global endpoint_text
    data = content.encode('utf-8')  # 将字符串编码为字节
    value_as_a_stream = io.BytesIO(data)
    get_minio().put_object(bucket_name, object_name, value_as_a_stream, len(data))
    return f"{endpoint_text}/{bucket_name}/{object_name}"