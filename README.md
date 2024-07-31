# AnnotatorTool

此内容包含Annotator上传任务基础脚本工具。
```
config.ini.exp 重命名为 config.ini，并且修改为正确的minio 配置
```

```
参考文本格式
../asr_audio/0329_wav_output/14.wav
65_15367036551711682415947user Reference Text: 好不用了谢谢不好我是黑猪不是黑户我是黑户了兄弟不用不用打了拜拜好嘛好嘛谢谢

../asr_audio/0329_wav_output/19.wav
73_15369453241711678531429user Reference Text: ce 
```

## 使用方式
```shell
conda create -n annotatorTool -y python=3.8
conda activate annotatorTool
pip install -r requirements.txt
```

``` 
 asr 带参考文本使用教程
 python asr/asrReferenceText.py 音频本地路径 参考文本路径
 python asr/asrReferenceText.py /audio audio.txt
```

1. [CV-图像](./cv/)
2. [ASR-音频](./asr/)