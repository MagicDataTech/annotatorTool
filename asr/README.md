# CV生成上平台格式

## 修改minio链接（run.py）
```
# 访问地址
endpointText = ""
# 存储桶名称
bucket_name = ''
# minio配置
minio_conf = {
    'endpoint': '',
    'access_key': '',
    'secret_key': '',
    # 如开启 https 为 True
    'secure': False
}
```

## 环境依赖
```
1. python3
```
## 使用说明
```shell
python3 run.py 本地图片路径, minio存储路径
```

## 参数说明
|  参数名  | 说明                          |
|  ----  |-----------------------------|
| dir  | 输入音频所在目录                    |
| miniopath | 想要上传的minio路径 eg：20230202img |

    

