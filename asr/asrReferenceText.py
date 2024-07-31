import concurrent.futures
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import traceback
import wave
import zipfile
from utils import storage
from tqdm import tqdm
from utils.config import config

def get_argv_s():
    argv_s = sys.argv[1:]
    argv_s_num = argv_s.__len__()
    print('输入参数个数 {}'.format(argv_s_num))
    # 返修
    if argv_s_num == 2:
        wav_dir, reference_text = argv_s
        # 检测目录是否存在
        if not os.path.exists(wav_dir):
            exit("wav_dir 目录不存在")
        # 检测文件是否存在
        if not os.path.exists(reference_text):
            exit("reference_text 文件不存在")
    else:
        exit("参数错误，最多两个参数")
    return [wav_dir, reference_text]


def file_to_zip(file_path, zip_file_path):
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(file_path, os.path.basename(file_path))


def upload_reference(reference_map, oss_dir_reference, wav_name):
    reference_url = ""
    reference = reference_map.get(wav_name, [])
    if reference:
        # 生成文件，上传minio
        reference_url = storage.upload_string_to_minio(oss_dir_reference, "\n".join(reference))
    return reference_url


def upload_file(wav_dir, reference_map):
    export_path = "./export"
    if not os.path.exists(export_path):
        os.makedirs(export_path, exist_ok=True)
    oss_dir = os.path.join("file/audio", wav_dir.split("/")[-1])
    oss_dir_audio = os.path.join(oss_dir, "audio")
    oss_dir_reference = os.path.join(oss_dir, "reference")
    oss_dir_zip = os.path.join(oss_dir, "zip")

    # minio 路径
    dir_txt = os.path.join(export_path, wav_dir.split("/")[-1] + ".txt")
    dir_zip = os.path.join(export_path, wav_dir.split("/")[-1] + ".zip")
    # 本地路径
    oss_dir_zip = os.path.join(oss_dir_zip, wav_dir.split("/")[-1] + ".zip")
    # 写入文件
    with open(dir_txt, "w") as f:
        with concurrent.futures.ThreadPoolExecutor(max_workers=config().getint("APP", 'MAX_WORKERS')) as executor:
            file_names = os.listdir(wav_dir)  # 获取文件名列表
            with tqdm(total=len(file_names)) as pbar:  # 创建进度条
                futures = []
                for wav_name in file_names:
                    futures.append(
                        executor.submit(get_wave_format, wav_name, oss_dir_audio, oss_dir_reference, reference_map))

                for futureExec in concurrent.futures.as_completed(futures):
                    try:
                        pbar.update(1)  # 每次循环更新进度条
                        f.write(futureExec.result() + "\n")
                    except Exception as e:
                        print(
                            "TranslatorService format_exc:{format_exc},e:{e}".format(format_exc=traceback.format_exc(),
                                                                                     e=e))
    # 文件压缩为zip
    file_to_zip(dir_txt, dir_zip)
    # 上传minion
    oss_url = storage.upload_file(dir_zip, oss_dir_zip)
    print("请使用以下url，上传平台:{}".format(oss_url))


def get_wave_format(wav_name, oss_dir_audio, oss_dir_reference, reference_map):
    # 获取 wav 文件路径
    wav_path = os.path.join(wav_dir, wav_name)
    oss_dir_audio_name = os.path.join(oss_dir_audio, wav_name)
    oss_dir_reference_name = os.path.join(oss_dir_reference, os.path.splitext(wav_name)[0] + ".txt")
    # 获取 wav 文件名
    wav_name = os.path.basename(wav_path)
    # 获取 参考文本
    ref_link = upload_reference(reference_map, oss_dir_reference_name, wav_name)
    # 上传minio
    oss_url = storage.upload_file(wav_path, oss_dir_audio_name)
    # 生成数据格式
    return json.dumps([
        {
            'wav_name': os.path.splitext(wav_name)[0],
            'wav_suf': 'wav',
            "length_time": get_wav_duration(wav_path),
            "object_key": oss_dir_audio_name,
            "ref_link": ref_link,
            "path": oss_url,
            "data": [],
            "global": []
        }
    ])


def get_wav_duration(wav_file_path):
    try:
        with wave.open(wav_file_path, 'r') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return duration
    except Exception as e:
        print(f"Error reading {wav_file_path}: {e}")
        return None


def get_reference_text(reference_text):
    # 读取文件
    with open(reference_text, 'r') as f:
        text = f.read()
        return generate_reference_map(text)


def generate_reference_map(text):
    audio_text_map = {}
    lines = text.split('\n')
    current_audio = None

    for line in lines:
        line = line.strip()
        if line == "":
            continue
        wave_name = line.split('/')[-1]
        if wave_name == "":
            continue
        if ".wav" in wave_name:
            current_audio = wave_name
            if current_audio:
                audio_text_map[current_audio] = []
        else:
            audio_text_map[current_audio].append(line.split(" ")[-1])
    return audio_text_map


if __name__ == '__main__':
    # 获取参数
    # wav_dir, reference_text = get_argv_s()
    wav_dir, reference_text = ["/Users/magicdata/Documents/fuzz/平台客户/6.0平台数据/测试脚本",
                               "/Users/magicdata/Documents/fuzz/code/python/annotatorTool/text/语音数据.txt"]
    # 读取参考文本
    reference_map = get_reference_text(reference_text)
    # 上传数据
    upload_file(wav_dir, reference_map)
