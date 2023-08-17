# -*- coding: utf-8 -*-
"""
@Time    : 2022/3/24 15:11
@Author  : Dailiukun
@Site    : 
@File    : cvUpPlat.py
@Version : v1.0.0
"""

import re, sys, os, json, zipfile, time, threading, wave, platform
from multiprocessing import Pool, Manager
from collections import OrderedDict
import os.path as path

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
downloadSource = r'https://pypi.douban.com/simple'
cmd_install1 = 'python3 -m pip install {} -i {}'.format('{}', downloadSource)
cmd_install2 = 'python -m pip install {} -i {}'.format('{}', downloadSource)
minioname = 'minio'
try:
    import minio
except:
    os.system(cmd_install1.format(minioname))
    try:
        import minio
    except:
        os.system(cmd_install2.format(minioname))
        import minio

baoname = 'pillow'
try:
    from PIL import Image
except:
    os.system(cmd_install1.format(baoname))
    try:
        from PIL import Image
    except:
        os.system(cmd_install2.format(baoname))
        from PIL import Image

is_end = True


class myThread(threading.Thread):
    def __init__(self, name='thread1', threadID='0', dic_={}, st_time=time.time(), waves_num=0, sox=False):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.dic_ = dic_
        self.sox = sox
        self.st_time = st_time
        self.waves_num = waves_num

    def run(self):
        # print("开启线程：" + self.name)
        my_process_data(self.name, self.dic_, self.st_time, self.waves_num, self.sox)
        # print("退出线程：" + self.name)


def myprinttlog(st_time, y_num):
    now_t = time.time()
    sub_t = round((now_t - st_time), 3)
    print('{} | 耗时 {} s'.format(y_num, sub_t))


def my_process_data(threadName, dic_, st_time, waves_num, sox):
    sleep_num = 5
    if sox:
        sleep_num = 15

    while is_end:
        myprinttlog(st_time, dic_.__len__())
        time.sleep(sleep_num)
    myprinttlog(st_time, dic_.__len__())


class waveReadTime:
    def __init__(self, time_dic_=None, mp4=False, img=False):
        self.time_dic_ = time_dic_
        self.mp4 = mp4
        self.img = img

    def yield_wave_dic(self, dic_):
        for k, v in dic_.items():
            yield k, v

    def get_many_wavt(self, wav_p, name_k, waves_path_dic, nj=8):
        suffix = '.wav'
        if self.mp4:
            suffix = '.mp4'
        elif self.img:
            suffix = {'.jpg', '.png', '.jpeg'}
        print(suffix)
        if not waves_path_dic:
            waves_path_dic = get_file_yield_func(wav_p, suffix)
        else:
            waves_path_dic = self.yield_wave_dic(waves_path_dic)
        print(nj)
        p = Pool(nj)
        # result_dic = OrderedDict()
        result_dic = Manager().dict()
        thread = myThread(dic_=result_dic, st_time=time.time(), sox=False)
        thread.start()
        total_num = 0
        for basename, fl_path in waves_path_dic:
            # print(basename, fl_path)
            total_num += 1
            if self.mp4:
                p.apply_async(self.get_mp4_duration, args=(fl_path, basename, name_k, result_dic))
            elif self.img:
                # wavlong_ = p.apply_async(self.get_img_info, args=(fl_path,))
                p.apply_async(self.get_img_info, args=(fl_path, basename, name_k, result_dic))
            else:
                p.apply_async(self.get_wav_time, args=(fl_path, basename, name_k, result_dic))

        p.close()
        p.join()
        global is_end
        is_end = False
        thread.join()
        if total_num > result_dic.__len__():
            print('警告！！！ 音频获取时长总数量小于输入数量，可以在 get_wavd_uration(wav_dir, False) 测试')
            sys.exit(1)

        return dict(result_dic)

    def get_wav_time(self, file_p, basename, name_k, result_dic):
        if self.mp4:
            return self.get_mp4_duration(file_p, basename, name_k, result_dic)
        wav_name = path.basename(file_p)
        size_ = os.path.getsize(file_p)
        try:
            if size_ < 2000:
                file_p += 1
            w = wave.open(file_p)
            w.close()
            params = w.getparams()
            [nchannels, sampwidth, sample_rate, nframes] = params[:4]
            long_ = nframes / sample_rate

        except Exception as e:
            try:
                if size_ < 2000:
                    file_p += 1
                sample_data, sample_rate = soundfile.read(file_p, dtype=None)
                data_len = len(sample_data)
                long_ = data_len / sample_rate
            except Exception as e:
                try:
                    popen = os.popen(u'sox {file_path} -n stat 2>&1'.format(file_path=file_p))
                    content = popen.read()
                    li = re.findall(u'Length \(seconds\):(.*?)Scaled by:', content, re.DOTALL)
                    wav_len_str = li[0].strip()
                    long_ = float(wav_len_str)
                    popen.close()
                except:
                    long_ = None
                    print('{}\t{}\n'.format('wav读取失败', wav_name))
        try:
            if name_k:
                result_dic[basename] = long_
            else:
                result_dic[file_p] = long_
        except Exception as e:
            print('Error: {}'.format(e))
        return long_

    def get_mp4_s_t(self, str_t):
        h, m, s = str_t.split(':')
        return_s = 3600 * int(h) + 60 * int(m) + float(s)
        return return_s

    def get_mp4_duration(self, fl_path, basename, name_k, result_dic):
        cmd_ = "ffmpeg -i '{}' 2>&1 | grep 'Duration' | cut -d ' ' -f 4 | sed s/,// ".format(fl_path)
        duration_ = os.popen(cmd_).read()
        s_ = self.get_mp4_s_t(duration_)
        try:
            if name_k:
                result_dic[basename] = s_
            else:
                result_dic[fl_path] = s_
        except Exception as e:
            print('Error: {}'.format(e))
        return s_

    def get_img_info(self, fl_path, basename, name_k, result_dic):
        img = Image.open(fl_path)
        width_, height_ = img.size
        depth_ = len(img.split())
        # print(width_, height_, depth_)
        try:
            if name_k:
                result_dic[basename] = [width_, height_, depth_]
            else:
                result_dic[fl_path] = [width_, height_, depth_]
        except Exception as e:
            print('Error: {}'.format(e))
        return width_, height_, depth_


# TODO: wave 时长读取
def get_wav_duration(wav_p, name_k=True, is_log=False, nj=8, mp4=False, img=False, waves_path_dic={}):
    """
    :param wav_p:输入路径文件夹或者音频路径
    :param name_k: 以路径/wav名称为 字典键
    :return:
    """
    wavread = waveReadTime(mp4=mp4, img=img)
    if not path.exists(wav_p):
        print('Warning！！！ Path "{}", Not Exist'.format(wav_p))
    elif path.isfile(wav_p):
        if img:
            return wavread.get_img_info(wav_p, '0', '0', {})
        elif mp4:
            return wavread.get_mp4_duration(wav_p, '0', '0', {})
        return wavread.get_wav_time(wav_p, '0', '0', {})
    elif path.isdir(wav_p):
        if is_log:
            if mp4:
                wav_longfile = path.join(path.dirname(wav_p), '{}_mp4long.json'.format(path.basename(wav_p)))
            elif img:
                wav_longfile = path.join(path.dirname(wav_p), '{}_img.json'.format(path.basename(wav_p)))
            else:
                wav_longfile = path.join(path.dirname(wav_p), '{}_wavelong.json'.format(path.basename(wav_p)))
            if not path.exists(wav_longfile):
                wav_long_d = wavread.get_many_wavt(wav_p, name_k, waves_path_dic, nj=nj)
                write_json(wav_longfile, wav_long_d)
                print("写入时长文件：{}".format(wav_longfile))
            else:
                # print("读取了已有wav时长文件：{}".format(wav_longfile))
                print("读取了已有时长文件：{}".format(wav_longfile))
                wav_long_d = read_text_get_json(wav_longfile)
        else:
            wav_long_d = wavread.get_many_wavt(wav_p, name_k, waves_path_dic, nj=nj)
        return wav_long_d


def get_file_yield_func(path, end_="", all=False, reverse=False):
    """
    获取以 end 为后缀的文件 输出未字典
    :param path: 输入路径
    :param end_: 后缀名称 eg: .txt
    :param reverse: True 以文件全路径为键，以文件name为值，False反之
    :return:
    """
    dic_ = {}
    end_class_name = type(end_).__name__
    if reverse:
        for root, dirs, files in os.walk(path):
            for file in files:
                if all:
                    is_y = True
                else:
                    base_n, suffix = os.path.splitext(file)
                    if end_class_name == 'str':
                        if suffix == end_:
                            is_y = True
                        else:
                            is_y = False
                    else:
                        if suffix in end_:
                            is_y = True
                        else:
                            is_y = False
                if is_y:
                    file_path = os.path.join(root, file)
                    if file_path not in dic_:
                        dic_[file_path] = file
                        yield file_path, file
                    else:
                        print('警告！！！文件名称重复 {}'.format(file_path))
    else:
        for root, dirs, files in os.walk(path):
            for file in files:
                if all:
                    is_y = True
                else:
                    base_n, suffix = os.path.splitext(file)
                    if end_class_name == 'str':
                        if suffix == end_:
                            is_y = True
                        else:
                            is_y = False
                    else:
                        if suffix in end_:
                            is_y = True
                        else:
                            is_y = False
                if is_y:
                    file_path = os.path.join(root, file)
                    if file not in dic_:
                        dic_[file] = file_path
                        yield file, file_path
                    else:
                        print('WarningError: key "{}" exist, old value: "{}" new value: "{}"'.format(file, dic_[file],
                                                                                                     file_path))
    return dic_


def read_text_get_json(file_p):
    """
    读取文本内容，返回序列化数据
    :param file_p:
    :return:
    """
    text = open(file_p, 'r', encoding='utf-8').read().replace('\n', '')
    dic_ = json.loads(text)
    return dic_


def write_m(file_p, ll: list):
    """
    写入文件get
    :param file_p: 路径
    :param ll: 列表
    :return:
    """
    with open(file_p, 'w', encoding='utf-8')as fall:
        fall.write(''.join(ll))


# TODO 写入json文件
def write_json(file_p, dic_):
    """
    :param file_p: 文件输出路径
    :param dic_:
    :return:
    """
    wav_t_l = [json.dumps(dic_, ensure_ascii=False, indent=4)]
    write_m(file_p, wav_t_l)


def get_file_path_func(path, end_="", reverse=False):
    """
    获取以 end 为后缀的文件 输出未字典
    :param path: 输入路径
    :param end_: 后缀名称 eg: .txt
    :param reverse: True 以文件全路径为键，以文件name为值，False反之
    :return:
    """
    dic_ = {}
    if reverse:
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(end_):
                    file_path = os.path.join(root, file)
                    if file_path not in dic_:
                        dic_[file_path] = file
                        # yield file_path, file
                    else:
                        print('警告！！！文件名称重复 {}'.format(file_path))
    else:
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(end_):
                    if file not in dic_:
                        file_path = os.path.join(root, file)
                        dic_[file] = file_path
                        # yield file, file_path
                    else:
                        print('WarningError: key "{}" exist, old value: "{}" new value: "{}"'.format(file, dic_[file],
                                                                                                     file_path))
    return dic_


def get_image_info(file_path, file_name, base_url, img_info_dic={}, frame=0):
    """
    :param file_path:
    :param file_name:
    :param base_url: http://magicdatacloud.oss-accelerate.aliyuncs.com/file/dailiukun/cv1118p2/
    :return:
    """
    if file_name in img_info_dic:
        width_, height_, depth_ = img_info_dic[file_name]
    else:
        img = Image.open(file_path)
        width_, height_ = img.size
        depth_ = len(img.split())
    image_info = {
        "file_name": file_name,
        "width": width_,
        "height": height_,
        "area": height_ * width_,
        "depth": depth_,
        "frame": frame,
        "file_url": base_url + file_name
    }
    return image_info, width_, height_


def get_image_info_v2(file_path, file_name, v2_base_url, img_info_dic={}, frame=0):
    """
    :param file_path:
    :param file_name:
    :param base_url: http://magicdatacloud.oss-accelerate.aliyuncs.com/file/dailiukun/cv1118p2/
    :return:
    """
    if file_name in img_info_dic:
        width_, height_, depth_ = img_info_dic[file_name]
    else:
        # img = Image.open(file_path)
        # width_, height_ = img.size
        # depth_ = len(img.split())
        try:
            width_, height_, depth_ = get_wav_duration(file_path, img=True)
        except:
            return
    image_info = {
        "file_name": file_name,
        "width": width_,
        "height": height_,
        "area": height_ * width_,
        "depth": depth_,
        "file_path": v2_base_url + file_name
    }
    return image_info, width_, height_


def sort_dic(dic_, index=1):
    """
    对字典排序，返回list
    :param dic_: dict
    :param index: 以 键或值排序
    :param is_total: 是否总和，一般用于 value 值为 数字的字典
    :return: list
    """
    sort_dd = sorted(dic_.items(), key=lambda item: item[index], reverse=False)
    return dict(sort_dd)


def numzfill(a):
    num = a.group(0)
    return num.zfill(6)


def sorted_name_func(in_dic, index=1):
    dic_ = {}
    for k, v in in_dic.items():
        name = k if index == 0 else v
        new_name = re.sub(r'[0-9]+', numzfill, name)
        dic_[k] = new_name
    sort_d = sort_dic(dic_, 1)
    after_sorted_dic = OrderedDict()
    for s_name in sort_d:
        after_sorted_dic[s_name] = in_dic[s_name]
    if in_dic.__len__() != sort_d.__len__():
        print('输入输出字典个数不一致')
        sys.exit(1)
    return after_sorted_dic


def get_every_img_dir_dic(input_img_dir):
    """
    每个目录下的图片返回一组数据 并根据名称排序
    :param input_img_dir:
    :return:
    """
    ssuffix_set = {'.jpg', '.jpeg', '.png'}
    for root, dirs, files in os.walk(input_img_dir):
        # print(root, len(files), files)
        img_dir_dic = {}
        for file in files:
            base_n, suffix = os.path.splitext(file)
            if base_n.startswith('.'):
                continue
            if suffix in ssuffix_set:
                # print(file)
                file_path = os.path.join(root, file)
                # img_f_ll.append([file, file_path])
                img_dir_dic[file] = file_path
        if img_dir_dic:
            yield sorted_name_func(img_dir_dic, 0)


def get_res_ll_code0(image_dir, img_info_dic):
    """
    常规操作 一条一包
    :param image_dir:
    :param img_info_dic:
    :return:
    """
    res_ll = []
    file_path_dic = get_file_yield_func(image_dir, end_={".jpeg", ".jpg", ".png"})
    # file_path_dic = get_file_path_func(image_dir, '')
    for file_name, file_path in file_path_dic:
        # base_n, suffix_ = os.path.splitext(file_name)
        # print(base_n, suffix_)
        # if suffix_ in {".jpeg", ".jpg", ".png"}:
        c_dic = {
            "info": {},
            "image": "",
            "annotations": [],
            "categories": [],
            "rotation": 0,
            "valid": True,
            "invalid_reason": ""
        }
        try:
            image_info, w, h = get_image_info(file_path, file_name, base_url, img_info_dic=img_info_dic)
        except:
            continue
        c_dic['image'] = image_info
        json_str = json.dumps([c_dic], ensure_ascii=False)
        # print(json_str)
        res_ll.append(json_str + '\n')
    return res_ll, file_path_dic


def get_res_ll_code1(image_dir, img_info_dic):
    """
    每个图片所在文件夹为一包数据
    :param image_dir:
    :param img_info_dic:
    :return:
    """
    img_group_dic_ll = get_every_img_dir_dic(image_dir)
    res_ll = []
    file_path_dic = {}
    for dic_group in img_group_dic_ll:
        bao_ll = []
        frame = 0
        for img_name, img_path in dic_group.items():
            if img_name not in file_path_dic:
                file_path_dic[img_name] = img_path
            else:
                print('图片名称重复', img_name)
                exit(1)
            c_dic = {
                "info": {},
                "image": "",
                "annotations": [],
                "categories": [],
                "rotation": 0,
                "valid": True,
                "invalid_reason": ""
            }
            frame += 1
            try:
                image_info, w, h = get_image_info(img_path, img_name, base_url, img_info_dic=img_info_dic, frame=frame)
            except:
                frame -= 1
                continue
            c_dic['image'] = image_info
            bao_ll.append(c_dic)
        res_ll.append(json.dumps(bao_ll, ensure_ascii=False) + '\n')
    return res_ll, file_path_dic


def get_res_ll_code2(image_dir, img_info_dic, bao_num):
    """
    目录中所有图片名称进行排序 根据指定包数 bao_num 参数 分包处理
    :param image_dir:
    :param img_info_dic:
    :param bao_num:
    :return:
    """
    res_ll = []
    file_path_dic0 = get_file_yield_func(image_dir, end_={".jpeg", ".jpg", ".png"})
    # file_path_dic = get_file_path_func(image_dir, '')
    file_path_dic = {}
    for file_name, file_path in file_path_dic0:
        if file_name not in file_path_dic:
            file_path_dic[file_name] = file_path
        else:
            print('图片名称重复', file_name)
            exit(1)
    file_path_dic = sorted_name_func(file_path_dic, 0)
    bao_ll = []
    frame = 0
    for img_name, img_path in file_path_dic.items():
        c_dic = {
            "info": {},
            "image": "",
            "annotations": [],
            "categories": [],
            "rotation": 0,
            "valid": True,
            "invalid_reason": ""
        }
        frame += 1
        try:
            image_info, w, h = get_image_info(img_path, img_name, base_url, img_info_dic=img_info_dic, frame=frame)
        except:
            frame -= 1
            continue
        c_dic['image'] = image_info
        bao_ll.append(c_dic)
        if len(bao_ll) == bao_num:
            res_ll.append(json.dumps(bao_ll, ensure_ascii=False) + '\n')
            bao_ll = []
            frame = 0

    if bao_ll:
        res_ll.append(json.dumps(bao_ll, ensure_ascii=False) + '\n')
    return res_ll, file_path_dic


def get_res_ll_code3(image_dir, img_info_dic, bao_num, v2_base_url):
    """
    CVV2 新格式上平台
    :param image_dir:
    :param img_info_dic:
    :param bao_num:
    :param v2_base_url:
    :return:
    """
    res_ll = []
    file_path_dic0 = get_file_yield_func(image_dir, end_={".jpeg", ".jpg", ".png"})
    # file_path_dic = get_file_path_func(image_dir, '')
    file_path_dic = {}
    for file_name, file_path in file_path_dic0:
        if file_name not in file_path_dic:
            file_path_dic[file_name] = file_path
        else:
            print('图片名称重复', file_name)
            exit(1)
    bao_ll = []
    for img_name, img_path in file_path_dic.items():
        c_dic = {
            "info": {
                "process_info": []
            },
            "image": "",
            "categories": [],
            "result": {
                "rotation": 0,
                "valid": True,
                "invalid_reason": []
            }
        }
        # frame += 1

        info_l = get_image_info_v2(img_path, img_name, v2_base_url, img_info_dic=img_info_dic)
        if info_l:
            image_info, w, h = info_l
        else:
            continue
        c_dic['image'] = image_info
        bao_ll.append(c_dic)
        if len(bao_ll) == bao_num:
            res_ll.append(json.dumps(bao_ll, ensure_ascii=False) + '\n')
            bao_ll = []

    if bao_ll:
        res_ll.append(json.dumps(bao_ll, ensure_ascii=False) + '\n')
    return res_ll, file_path_dic


def main_func(image_dir, oss_path, base_url, is_uposs, code_, bao_num, v2_base_url):
    img_info_dic = get_wav_duration(image_dir, img=True, is_log=True)
    if code_ == '0':
        res_ll, file_path_dic = get_res_ll_code0(image_dir, img_info_dic)
    elif code_ == '1':
        res_ll, file_path_dic = get_res_ll_code1(image_dir, img_info_dic)
    elif code_ == '2':
        res_ll, file_path_dic = get_res_ll_code2(image_dir, img_info_dic, bao_num)
    else:  # CVV2 格式
        res_ll, file_path_dic = get_res_ll_code3(image_dir, img_info_dic, bao_num, v2_base_url)
    out_file = image_dir + '_UP.txt'
    write_m(out_file, res_ll)
    zip_file, zip_name = FileCompressionZip(out_file)
    try:
        print('开始上传压缩包')
        zip_oss_url_path = upload_file_minio(zip_file, oss_path)
        print('压缩包已上传, 可直接使用该 url 上项目：{}'.format(zip_oss_url_path))
        time.sleep(2)
        if is_uposs:
            print('开始上传 图片')
            uppool = Pool(8)
            for wav_name, wave_path in file_path_dic.items():
                # print(wav_name, wave_path)
                # upload_file_minio(wave_path, oss_path)
                uppool.apply_async(upload_file_minio, args=(wave_path, oss_path))
            uppool.close()
            uppool.join()
        print('压缩包已上传, 可直接使用该 url 上项目：{}'.format(zip_oss_url_path))
    except Exception as e:
        print('警告！！！上传 minio 失败：{}'.format(e))
    print("请查看上平台文本：{}".format(out_file))


def FileCompressionZip(input_):
    """
    :return:
    """
    # input_ = r"C:\Users\MagicDatat\Desktop\ys\test"
    base_dir = os.path.dirname(input_)
    base_name = os.path.basename(input_)
    os.chdir(base_dir)
    if os.path.isdir(input_):
        out_zipfile = input_ + ".zip"
        z = zipfile.ZipFile(out_zipfile, 'w', zipfile.ZIP_DEFLATED)
        for dirpath, dirnames, filenames in os.walk(input_):
            for filename in filenames:
                f_p = os.path.join(dirpath, filename).replace(base_dir, '').strip(os.sep)
                print(f_p)
                z.write(f_p)
    elif os.path.isfile(input_):
        out_zipfile = os.path.splitext(input_)[0] + ".zip"
        z = zipfile.ZipFile(out_zipfile, 'w', zipfile.ZIP_DEFLATED)
        z.write(base_name)
    else:
        exit("程序出错！！！")
    z.close()
    return out_zipfile, os.path.basename(out_zipfile)


def get_oss_base_url(oss_path):
    """
    数据上传 oss 后获取基础url
    :param oss_path:
    :return:
    """
    base_url = 'https://magicdatacloud.oss-cn-beijing.aliyuncs.com/' + re.search(r'oss://.*?/(.*)',
                                                                                 oss_path).group(1)
    if not base_url.endswith('/'):
        base_url += '/'
    return base_url


def get_argvs():
    argvs = sys.argv[1:]
    argvs_num = argvs.__len__()
    print('输入参数个数 {}\t{}'.format(argvs_num, argvs))
    # 返修
    if argvs_num == 2:
        image_dir, oss_path = argvs
        code_ = '2'
        bao_num = 1
    elif argvs_num == 3:
        image_dir, oss_path, code_ = argvs
    elif argvs_num == 0:
        image_dir = r'C:\Users\MagicDatat\Desktop\client'
        oss_path = r'test'
        code_ = '2'
        bao_num = 1
    else:
        print('程序结束！！！输入参数个数 {}，应该为 2 个参数'.format(argvs_num))
        sys.exit(1)
    code_dic = {'1': '0', '2': '3'}
    code_ = code_dic[code_]
    if re.match(r'http', oss_path):
        base_url = oss_path
        is_uposs = False
    else:
        is_uposs = True
        try:
            base_url = endpointText + '/{}/file/image/{}'.format(bucket_name, oss_path)
        except:
            exit("程序结束！！！oss_path 参数错误")
    if code_ not in {'0', '1', '2', '3'}:
        exit('输入处理方式 code 参数错误！！！eg：0/1/2')
    if code_ in {'2', '3'}:
        try:
            bao_num = int(bao_num)
        except:
            print('处理方式为 2 时， bao_num 参数必须填且为整数！！！')
            exit("ERROR: 参数错误")
    if not base_url.endswith('/'):
        base_url += '/'
    if not os.path.exists(image_dir):
        exit('输入路径不存在：{}'.format(image_dir))
    v2_base_url = '/'.join(base_url.split('/')[3:])
    bao_num = 1
    print(base_url)
    print(v2_base_url)
    return [image_dir, oss_path, base_url, is_uposs, code_, bao_num, v2_base_url]


def upload_file_minio(file_path, object_dir):
    try:
        file_name = os.path.basename(file_path)
        client = minio.Minio(**minio_conf)
        client.fput_object(bucket_name=bucket_name, object_name='file/image/' + object_dir + '/' + file_name,
                           file_path=file_path)
    except Exception as e:
        print('上传文件失败：{}'.format(e))
    return endpointText + '/' + bucket_name + '/file/image/' + object_dir + '/' + file_name


if __name__ == '__main__':
    # file_ = r'X:\\cv\\xx.萌宠猫咪脸部关键点标注\\1.原始文件\\猫咪嘴巴待标注照片\\猫咪嘴巴待标注照片\\打哈欠的猫咪\\6f8e83.jpg'
    # print(get_wav_duration(file_, img=True))
    # exit()
    # get_image_info(r"C:\Users\MagicDatat\Desktop\FYQD_0001.jpg", 'FYQD_0001.jpg', '21')
    image_dir, oss_path, base_url, is_uposs, code_, bao_num, v2_base_url = get_argvs()
    start_ = time.time()
    print(start_)
    print([image_dir, oss_path, base_url, is_uposs, code_, bao_num, v2_base_url])
    # exit(1)
    main_func(image_dir, oss_path, base_url, is_uposs, code_, bao_num, v2_base_url)
    print("耗时：{}\nEnd Done.".format(time.time() - start_))
