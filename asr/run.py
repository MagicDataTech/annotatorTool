# -*- coding: utf-8 -*-
"""
@Time    : 2021/1/29 15:47
@Author  : Dailiukun
@Site    :
@File    : text_to_upload_platform_v2.py
@Version : v1.0.0
"""
import re, sys, wave, os, time, json, threading
import shutil
import zipfile
from multiprocessing import Pool, Manager
from os import path
from collections import OrderedDict


err_ll = []
cmd_install1 = 'python3 -m pip install {} -i https://pypi.tuna.tsinghua.edu.cn/simple'
cmd_install2 = 'python -m pip install {} -i https://pypi.tuna.tsinghua.edu.cn/simple'
baoname = 'soundfile'
# minio config
endpointText = ''
bucket_name = ''
minio_conf = {
        'endpoint': '',
        'access_key': '',
        'secret_key': '',
        'secure': False
}

try:
    import soundfile
except:
    os.system(cmd_install1.format(baoname))
    try:
        import soundfile
    except:
        os.system(cmd_install2.format(baoname))
        import soundfile


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

baoname = 'loguru'
try:
    from loguru import logger
except:
    os.system(cmd_install1.format(baoname))
    try:
        from loguru import logger
    except:
        os.system(cmd_install2.format(baoname))
        from loguru import logger


def cmd_order_(cmd):
    """
    执行cmd命令
    :param cmd_or:
    :return:
    """
    os.system(cmd)


def copy_(k, v):
    """
    文件复制
    :param k:
    :param v:
    :return:
    """
    if not os.path.exists(v):
        make_dirs(os.path.dirname(v))
        shutil.copy(k, v)
    else:
        if os.path.getsize(k) != os.path.getsize(v):
            shutil.copy(k, v)


# TODO 多进程复制文件或执行cmd命令
def copy_main(copy_dic_list, nj):
    """
    多进程复制(dic:)、命令行(list:)
    :param copy_dic_list: 如果是列表会当做cmd 命令执行，字典会copy
    :param nj:
    :return:
    """
    type_ = type(copy_dic_list).__name__
    if type_ == 'dict':
        pool = Pool(nj)
        for k, v in copy_dic_list.items():
            pool.apply_async(copy_, args=(k, v))
        pool.close()
        pool.join()
    elif type_ == 'list':
        pool = Pool(nj)
        for cmd in copy_dic_list:
            pool.apply_async(cmd_order_, args=(cmd,))
        pool.close()
        pool.join()
    else:
        print('类型错误')


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
        process_data(self.name, self.dic_, self.st_time, self.waves_num, self.sox)
        # print("退出线程：" + self.name)


def pprinttlog(st_time, waves_num, y_num):
    now_t = time.time()
    sub_t = round((now_t - st_time), 3)
    print('{}/{} | 耗时 {} s'.format(y_num, waves_num, sub_t))


def process_data(threadName, dic_, st_time, waves_num, sox):
    if waves_num > 10000:
        cha_num = 1000
    else:
        cha_num = waves_num / 10
    up_end = 0
    sleep_num = 3
    if sox and waves_num > 10000:
        sleep_num = 10
    # print(cha_num)
    while dic_.__len__() != waves_num:

        if dic_.__len__() - up_end > cha_num:
            # cha_num = bc_num
            up_end = dic_.__len__()
            pprinttlog(st_time, waves_num, dic_.__len__())
        # print('睡眠', sleep_num)
        time.sleep(sleep_num)
        # print(dic_.__len__())
    pprinttlog(st_time, waves_num, dic_.__len__())


class waveReadTime:
    def __init__(self, time_dic_=None, mp4=False):
        self.time_dic_ = time_dic_
        self.mp4 = mp4

    def get_many_wavt(self, wav_p, name_k, waves_path_dic, nj=8):
        suffix = '.wav'
        if self.mp4:
            suffix = '.mp4'
        if not waves_path_dic:
            waves_path_dic = get_file_path_func(wav_p, suffix, reverse=True)
        print(nj)
        p = Pool(nj)
        result_dic = OrderedDict()
        thread = myThread(dic_=result_dic, waves_num=waves_path_dic.__len__(), st_time=time.time(), sox=False)
        thread.start()
        for basename, fl_path in waves_path_dic.items():

            if self.mp4:
                wavlong_ = p.apply_async(self.get_mp4_duration, args=(fl_path,))
            else:
                wavlong_ = p.apply_async(self.get_wav_time, args=(fl_path,))
            try:
                if name_k:
                    result_dic[basename] = wavlong_.get()
                else:
                    result_dic[fl_path] = wavlong_.get()
            except Exception as e:
                print('Error: {}'.format(e))
        p.close()
        p.join()
        thread.join()
        if waves_path_dic.__len__() > result_dic.__len__():
            print('警告！！！ 音频获取时长总数量小于输入数量，可以在 get_wavd_uration(wav_dir, False) 测试')
            sys.exit(1)

        return result_dic

    def get_wav_time(self, file_p, result_dic=None):
        if self.mp4:
            return self.get_mp4_duration(file_p)
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
        # print(long_)
        return long_

    def get_mp4_s_t(self, str_t):
        h, m, s = str_t.split(':')
        return_s = 3600 * int(h) + 60 * int(m) + float(s)
        return return_s

    def get_mp4_duration(self, file_path):
        cmd_ = "ffmpeg -i {} 2>&1 | grep 'Duration' | cut -d ' ' -f 4 | sed s/,// ".format(file_path)
        duration_ = os.popen(cmd_).read()
        s_ = self.get_mp4_s_t(duration_)
        return s_


# TODO: wave 时长读取
def get_wav_duration(wav_p, name_k=True, is_log=False, nj=8, mp4=False, waves_path_dic={}):
    """
    :param wav_p:输入路径文件夹或者音频路径
    :param name_k: 以路径/wav名称为 字典键
    :return:
    """
    wavread = waveReadTime(mp4=mp4)
    if not path.exists(wav_p):
        print('Warning！！！ Path "{}", Not Exist'.format(wav_p))
    elif path.isfile(wav_p):
        return wavread.get_wav_time(wav_p)
    elif path.isdir(wav_p):
        if is_log:
            if mp4:
                wav_longfile = path.join(path.dirname(wav_p), '{}_mp4long.json'.format(path.basename(wav_p)))
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


def get_log(dir_):
    if not path.exists(dir_):
        print("输入路径不存在！程序终止！！！{}".format(dir_))
        sys.exit(1)
    log_file = path.join(path.dirname(dir_), '脚本运行log.txt')
    log = logger
    log.add(log_file, encoding='utf-8')
    print("请查看脚本运行log：{}".format(log_file))
    log.info("请查看脚本运行log：{}".format(log_file))
    return log


def make_dirs(out_dir_):
    if not path.exists(out_dir_):
        os.makedirs(out_dir_)


def write_m(file_p, ll):
    with open(file_p, 'w', encoding='utf-8')as fall:
        fall.write(''.join(ll))


# TODO 往字典里面添加键值
def add_k_v_to_dic(dic: dict, k: str, v=None):
    """
    把键值对存入字典中
    :param dic:
    :param k:
    :param v:
    :return:
    """
    if k not in dic:
        dic[k] = v
    else:
        print('WarningError: key "{}" exist, old value: "{}" new value: "{}"'.format(k, dic[k], v))


# TODO 往字典里面添加键值
def add_k_list_to_dic(dic: dict, k: str, v=None):
    """
    把键值对存入字典中
    :param dic:
    :param k:
    :param v:
    :return:
    """
    if k not in dic:
        dic[k] = [v]
    else:
        dic[k].append(v)


# TODO 读取json格式文本返回字典
def read_text_get_json(file_p):
    """
    读取文本内容，返回序列化数据
    :param file_p:
    :return:
    """
    text = open(file_p, 'r', encoding='utf-8').read().replace('\n', '')
    dic_ = json.loads(text)
    return dic_


# TODO 写入json文件
def write_json(file_p, dic_):
    """
    :param file_p: 文件输出路径
    :param dic_:
    :return:
    """
    wav_t_l = [json.dumps(dic_, ensure_ascii=False, indent=4)]
    write_m(file_p, wav_t_l)


# TODO 获取目录下的所有文件  最常用
def get_file_path_func(inpath, end_="", reverse=False):
    """
    获取以 end 为后缀的文件
    :param path: 输入路径
    :param end_: 后缀名称 eg: .txt
    :param reverse: True 以文件全路径为键，以文件name为值，False反之
    :return:
    """
    dic_ = {}
    if reverse:
        for root, dirs, files in os.walk(inpath):
            for file in files:
                if file.endswith(end_):
                    file_path = path.join(root, file)
                    if file_path not in dic_:
                        dic_[file_path] = file
                    else:
                        print('警告！！！文件名称重复 {}'.format(file_path))
    else:
        for root, dirs, files in os.walk(inpath):
            for file in files:
                if file.endswith(end_):
                    if file not in dic_:
                        file_path = os.path.join(root, file)
                        dic_[file] = file_path
                    else:
                        print('警告！！！文件名称重复 {}'.format(file))
    return dic_


def get_all_wavlong_dic(wav_dir):
    wav_path_d = get_file_path_func(wav_dir, '.wav')
    print('开始跑 wav 时长')
    total_wav_num = wav_path_d.__len__()
    print('总音频个数 {}'.format(total_wav_num))
    print('总音频个数 {}'.format(total_wav_num))
    wav_long_d = get_wav_duration(wav_dir, is_log=True, waves_path_dic=wav_path_d)
    if wav_long_d.__len__() != wav_path_d.__len__():
        wav_long_d = get_wav_duration(wav_dir, waves_path_dic=wav_path_d)
    nolong_num = 0
    # time_ = 0
    for k, v in wav_path_d.items():
        if k not in wav_long_d:
            nolong_num += 1
            err_ll.append("{} 没跑出时长\n".format(k))
    if nolong_num > 0:
        info_ = '注意！！！有 {} 条wave没跑出时长结果'.format(nolong_num)
        err_ll.append("{}\n".format(info_))
        print(info_)
    return wav_long_d, wav_path_d


def read_m(file_):
    size_ = path.getsize(file_)
    ll = []
    if size_ > 210564847:  # 210564847    #200兆
        with open(file_, 'r', encoding='utf8')as fbase:
            while 1:
                line = fbase.readline()
                if not line:
                    break
                ll.append(line)
    else:
        with open(file_, 'r', encoding='utf8')as fbase:
            ll = fbase.readlines()
    return ll


def format_num(num):
    if float(num) == 0:
        return '0.000'
    else:
        num = str(num)
        if re.search('\.', num) and len(re.split('\.', num)[1]) == 3:
            return num
        else:
            num1000 = '%d' % (float(num) * 1000)
            num_c1000 = float(num1000) / 1000
            three_point_num = '%.3f' % num_c1000
            return three_point_num


def del_space_text(text):
    text = re.sub('\s+', ' ', text)
    text = re.sub(r'(?<![a-zA-Z])\s|\s(?![a-zA-Z])', '', text)
    return text


def get_time(timestr, group=True):
    if group:
        time_g = re.findall(r'[0-9.]+', timestr)
        if time_g.__len__() == 2:
            st, et = time_g
            if not re.findall(r'[0-9]', st):
                print(timestr, "开始时间未发现时间数字")
                sys.exit(1)
            if not re.findall(r'[0-9]', et):
                print(timestr, "结束时间未发现时间数字")
                sys.exit(1)
            return st, et
        else:
            return False
    else:
        t_ = re.findall('[0-9.]+', timestr)
        if t_.__len__() != 1:
            print(timestr, "未发现时间数字")
            sys.exit(0)
        t_ = t_[0]
        if not re.findall(r'[0-9]', t_):
            print(timestr, "结束时间未发现时间数字")
            sys.exit(0)
        return t_


def change1(a):
    k = a.group(0)
    return '||[{}]||'.format(k)


def change2(a):
    k = a.group(0)
    n_k = '||[{}]||'.format(k.strip('<>'))
    return n_k


def change3(a):
    k = a.group(0)
    n_k = '||{}||'.format(k)
    return n_k


def get_text_dir_dic(text_dir, time_i, text_i):
    """
    返修文本目录解析
    :param text_dir:
    :param wav_longdic:
    :return:
    """
    dic_ = {}
    for file_name, file_path in get_file_path_func(text_dir, '.txt').items():
        wav_name = path.splitext(file_name)[0] + '.wav'
        text_lines = read_m(file_path)
        if re.findall(r'[0-9.]+', text_lines[0].split('\t')[time_i]).__len__() < 2:
            text_lines = text_lines[1:]
        for line in text_lines:
            line_l = line.strip('\n').split('\t')
            start_time, end_time = get_time(line_l[time_i])
            text = line_l[text_i]
            info_list = [text, start_time, end_time]
            add_k_list_to_dic(dic_, wav_name, v=info_list)
    return dic_


def deal_vad_decode_file(line_ll, wav_longdic):
    dic_ = {}
    for line in line_ll:
        line = line.strip('\n')
        wav_name_timeg, base_text = line.split(' ', 1)
        wav_n_time = wav_name_timeg.split('.wav')
        wav_name = '{}.wav'.format(wav_n_time[0])
        s_e_time = get_time(wav_n_time[-1])
        # vad 或者 长音频
        if s_e_time:
            start_time = int(s_e_time[0]) / 100
            end_time = int(s_e_time[1]) / 100
            # 说明是 vad 文本文件
            if re.match(wav_name, base_text):
                info_list = ['', start_time, end_time]
            # 说明是 长语音 decode 文本文件
            else:
                text = del_space_text(base_text)
                info_list = [text, start_time, end_time]
        # 短音频解码文本 eg: G0021_S0051.wav 大 破
        else:
            start_time = 0
            if wav_name in wav_longdic:
                end_time = wav_longdic[wav_name]
            else:
                print('Warning ！！！没有该音频时长 {}, 程序终止'.format(wav_name))
                sys.exit(1)
            text = del_space_text(base_text)
            info_list = [text, start_time, end_time]
        add_k_list_to_dic(dic_, wav_name, v=info_list)
    return dic_


def deal_custom_file(line_ll, wav_longdic, table_num):
    dic_ = {}
    name_dic = {}
    for line in line_ll:
        if not line.strip():  # 空行过滤
            continue
        line = line.strip('\n')
        if table_num == 1:
            try:
                wav_name, text = line.split('\t')
            except:
                info_ = 'table 数量错误, 程序终止 {}'.format(line)
                print(info_)
                sys.exit(1)
            start_time = 0
            if not wav_name.endswith('.wav'):
                wav_name += '.wav'
            if wav_name not in name_dic:
                name_dic[wav_name] = None
            else:
                info_ = '警告！！！短音频名称重复， 程序终止，如果为长音频后面请加上时间段'
                print(info_)
                sys.exit(1)
            end_time = wav_longdic[wav_name]
        elif table_num == 3:
            try:
                wav_name, text, start_time, end_time = line.split('\t')
            except:
                info_ = 'table 数量错误, 程序终止 {}'.format(line)
                print(info_)
                sys.exit(1)
            if not wav_name.endswith('.wav'):
                wav_name += '.wav'
        else:
            info_ = 'table 数量错误, 程序终止'
            print(info_)
            sys.exit(1)
        info_list = [text, start_time, end_time]
        add_k_list_to_dic(dic_, wav_name, v=info_list)
    return dic_


def get_seg_dic(seg_file, wav_longdic):
    """
    vad/【长短语音】decode
    :param seg_file:
    :param wav_longdic:
    :return:
    """
    line_ll = read_m(seg_file)
    has_table = False
    table_num = re.findall('\t', line_ll[0]).__len__()
    if table_num:
        has_table = True
    if has_table:
        print(r'处理 自定义格式 文本')
        dic_ = deal_custom_file(line_ll, wav_longdic, table_num)
    else:
        print(r'处理 vad decode 文本')
        dic_ = deal_vad_decode_file(line_ll, wav_longdic)

    return dic_


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


def sorted_name_func(in_dic):
    dic_ = {}
    for name in in_dic:
        new_name = re.sub(r'[0-9]+', numzfill, name)
        dic_[name] = new_name
    sort_d = sort_dic(dic_, 1)
    after_sorted_dic = OrderedDict()
    for s_name in sort_d:
        after_sorted_dic[s_name] = in_dic[s_name]

    if in_dic.__len__() != sort_d.__len__():
        print('排序输入输出字典个数不一致')
        sys.exit(1)
    return after_sorted_dic


def get_time_d2(ll, n, dd):
    if n < len(ll) - 2:
        dd['qian'] = ll[n + 1][-2]
        dd['hou'] = ll[n + 2][-1]
    if n == len(ll) - 2:
        dd['qian'] = ll[-2][-2]
        dd['hou'] = ll[-1][-1]


def get_time_d1(ll, n, dd):
    if n < len(ll) - 2:
        dd['qian'] = ll[n + 1][-1]
        dd['hou'] = ll[n + 2][-2]
    if n == len(ll) - 2:
        dd['qian'] = ll[-2][-1]
        dd['hou'] = ll[-1][-2]


def del_time_err_index(ll, wav_name):
    del_ll = []
    if len(ll) >= 2:
        dd = {'qian': ll[0][-2], 'hou': ll[1][-1]}
        dd1 = {'qian': ll[0][-1], 'hou': ll[1][-2]}
        for n, l in enumerate(ll):
            st, et = l[-2:]
            if float(et) < float(st):
                del_ll.append(n)
                continue
            if n < len(ll) - 1:
                if float(dd['hou']) < float(dd['qian']):
                    del_ll.append(n)
                elif float(dd1['hou']) < float(dd1['qian']):
                    del_ll.append(n)
                get_time_d2(ll, n, dd)
                get_time_d1(ll, n, dd1)
    if del_ll:
        sort_del_ll = sorted(list(set(del_ll)), reverse=True)
        for index_ in sort_del_ll:
            ll.pop(index_)
            print('{} Time overlap Delete line {} text data'.format(wav_name, index_ + 1))
            err_ll.append('{} 时间段错误 删除第 {} 行文本段\n'.format(wav_name, index_ + 1))
        return True, ll
    else:
        return False, ll


def check_time_func(ll, wav_name):
    bool_ = True
    num_ = 0
    while bool_:
        # if num_ != 0:
        #     print('循环 {} 次'.format(num_))
        bool_, ll = del_time_err_index(ll, wav_name)
        num_ += 1
    # if num_ > 1:
    #     print(1)
    return ll


def del_end_time_greater_than_wav_dura(sort_txt_l, wav_dura, wav_name):
    """
    删除最后一行时间段大于音频总时长
    :return:
    """
    while True:
        end_l_st = float(sort_txt_l[-1][-2])
        end_l_et = float(sort_txt_l[-1][-1])
        if end_l_et > wav_dura:
            if wav_dura > end_l_st:
                sort_txt_l[-1][-1] = wav_dura
                print('{} 标注结束点时长 {} 大于音频总时长 {} 程序已自动修复\n'.format(wav_name, end_l_et, wav_dura))
                err_ll.append('{} 标注结束点时长 {} 大于音频总时长 {} 程序已自动修复\n'.format(wav_name, end_l_et, wav_dura))
                break
            else:
                if sort_txt_l.__len__() > 1:
                    sort_txt_l.pop()
                else:
                    sort_txt_l[-1][-2] = 0
                    sort_txt_l[-1][-1] = wav_dura
                    break
        else:
            break


def deal_to_uppt_dic(dic_, is_data_none, wav_longdic, bq_type, url_dic):
    """
    处理成 上平台格式json数据
    :param dic_:
    :return:
    """
    global total_wav_long, total_valid_long
    uppt_dic = {}
    if is_data_none:
        for wav_name, wav_dura in dic_.items():
            total_wav_long += wav_dura
            audio_url = url_dic[wav_name]
            wav_single_dic = {'wav_name': os.path.splitext(wav_name)[0], 'wav_suf': 'wav', "length_time": wav_dura,
                              "path": audio_url, 'data': []}
            add_k_v_to_dic(uppt_dic, wav_name, wav_single_dic)
    else:
        for wav_name, txt_l in dic_.items():
            # 列表按照时长排序
            sort_txt_l = sorted(txt_l, key=lambda item: float(item[1]))
            sort_txt_l = check_time_func(sort_txt_l, wav_name)
            data_l = []
            # 判断音频时长是否大于音频总时长
            if wav_name in wav_longdic:
                wav_dura = float(wav_longdic[wav_name])
                del_end_time_greater_than_wav_dura(sort_txt_l, wav_dura, wav_name)
            else:
                print('{} Error: No audio duration\n'.format(wav_name))
                sys.exit(1)
            total_wav_long += wav_dura
            for child_txt_l in sort_txt_l:
                text, star_time, end_time = child_txt_l
                if bq_type:
                    if bq_type == '1':
                        text = re.sub(r'\(.*?\)', change1, text)
                    elif bq_type == '2':
                        text = re.sub(r'<.*?>', change2, text)
                    elif bq_type == '3':
                        text = re.sub(r'\[.*?\]', change3, text)
                st, et = float(format_num(star_time)), float(format_num(end_time))
                total_valid_long += et - st
                child_dic = {"start_time": st, "end_time": et, "text": text}
                data_l.append(child_dic)
            delhouzhuiwav_name = path.splitext(wav_name)[0]
            audio_url = url_dic[wav_name]
            wav_single_dic = {"wav_name": delhouzhuiwav_name, "wav_suf": 'wav',
                              "length_time": float(format_num(wav_dura)),
                              "path": audio_url, "data": data_l}
            add_k_v_to_dic(uppt_dic, wav_name, wav_single_dic)
    return uppt_dic


def merge_up_mdt_fun(dic_):
    """
    合并mdt关联音频生成上平台文本
    :param dic_:
    :return:
    """
    mdt_merge_dic = {}
    for wav_name, data_v in dic_.items():
        base_name = wav_name.rsplit('__mdt_', 1)[0]
        add_k_list_to_dic(mdt_merge_dic, base_name, data_v)
    return mdt_merge_dic


def write_uppt_func(uppt_dic, wav_longdic, mdt=True, is_t=False, bao_wavnum=1):
    sort_uppt_dic = sorted_name_func(uppt_dic)
    zong_file_num = sort_uppt_dic.__len__()
    allbao_ll = []
    if mdt:
        info_ = '执行 __mdt_ 关联音频合并 参数 mdt: {}'.format(mdt)
        log.info(info_)
        sort_uppt_dic = merge_up_mdt_fun(sort_uppt_dic)
    for wav_name, data_v in sort_uppt_dic.items():
        bao_ll = [data_v]
        allbao_ll.append(json.dumps(bao_ll, ensure_ascii=False) + '\n')
    allbao_ll = []
    bao_ll = []
    every_bao_time = 0
    for wav_name, data_v in sort_uppt_dic.items():
        dict_list_type = type(data_v).__name__
        if dict_list_type == 'dict':
            bao_ll.append([data_v])
        elif dict_list_type == 'list':
            bao_ll.append(data_v)
        else:
            log.error('data 类型错误, 程序结束')
            sys.exit(1)
        if is_t:
            end_dic_ll = bao_ll[-1]
            # print(end_dic_ll.__len__())
            for dic_ in end_dic_ll:
                t_wave_name = dic_['Wav_name']
                # print(t_wave_name)
                every_bao_time += wav_longdic[t_wave_name + '.wav']

            if every_bao_time >= bao_wavnum:
                # print(every_bao_time)
                dozens = every_bao_time / bao_wavnum
                if dozens > 2:
                    log.warning(
                        '音频 {} 所在包 时长 {} 大于设置时长 {} 倍\n'.format(wav_name, round(every_bao_time, 5), round(dozens, 2)))
                    err_ll.append(
                        '音频 {} 所在包 时长 {} 大于设置时长 {} 倍\n'.format(wav_name, round(every_bao_time, 5), round(dozens, 2)))
                allbao_ll.append(json.dumps(bao_ll[0], ensure_ascii=False) + '\n')
                bao_ll.clear()
                every_bao_time = 0
        else:
            if bao_ll.__len__() == bao_wavnum:
                allbao_ll.append(json.dumps(bao_ll[0], ensure_ascii=False) + '\n')
                bao_ll.clear()
    if bao_ll:
        allbao_ll.append(json.dumps(bao_ll[0], ensure_ascii=False) + '\n')

    # print("一共生成 {} 包数据\n请查看：{}".format(allbao_ll.__len__(), out_file))
    # log.info("文件一共 {} 一共生成 {} 包数据\n请查看：{}".format(zong_file_num, allbao_ll.__len__(), out_file))
    # log.info("\nThere are {} documents, A total of {} packages.\n请查看：{}".format(zong_file_num, allbao_ll.__len__(),
    #                                                                             out_file))

    return allbao_ll, zong_file_num


def get_url_dic_func(oss_path, base_url, wav_longdic):
    url_dic = {}
    if os.path.isfile(oss_path):
        for line in read_m(oss_path):
            try:
                json_data = json.loads(line)
                wav_name = json_data['wav_name']
                url_ = json_data['path']
            except:
                line_l = line.split('\t')
                wav_name, url_ = line_l[0], line_l[1]
            if not wav_name.endswith('.wav'):
                wav_name += '.wav'
            add_k_v_to_dic(url_dic, wav_name, url_.strip())
    else:

        for wav_name, long_ in wav_longdic.items():
            urlwav_name = wav_name  # .replace('.wav', '.ogg')
            url_ = base_url + urlwav_name
            add_k_v_to_dic(url_dic, wav_name, url_)
    return url_dic


def wav_to_ogg_func(wav_path_d, ogg_dir, oss_path):
    print('开始 wav to ogg')
    ogg_cmd_ll = []
    for name_, path_ in wav_path_d.items():
        base_name = path.splitext(name_)[0]
        out_ogg_fp = path.join(ogg_dir, base_name + '.ogg')
        if not path.exists(out_ogg_fp):
            ogg_cmd_ll.append('sox {} {}'.format(path_, out_ogg_fp))
            print(name_, path_)
    copy_main(ogg_cmd_ll, 8)
    # print('格式转换完毕、开始上传 ogg 音频')
    cmd_1 = r'/sysdata/common_data/oss/ossutil64 cp -j 8 --parallel 8 -r -u {} {}'.format(ogg_dir, oss_path)
    print(cmd_1)
    os.system(cmd_1)


def uppt_main_func(argvs_l):
    wav_dir, seg_file, oss_path, base_url, time_i, text_i, is_data_none, bq_type, text_dir, is_uposs = argvs_l
    out_file = path.join(path.dirname(seg_file), '{}_uppt.txt'.format(path.basename(seg_file).replace(".txt", '')))
    wav_longdic, wav_path_d = get_all_wavlong_dic(wav_dir)
    url_dic = get_url_dic_func(oss_path, base_url, wav_longdic)
    print('Start organizing your text')
    if text_dir:
        seg_dic = get_text_dir_dic(text_dir, time_i, text_i)
    else:
        if is_data_none:
            seg_dic = wav_longdic
        else:
            seg_dic = get_seg_dic(seg_file, wav_longdic)
    uppt_dic = deal_to_uppt_dic(seg_dic, is_data_none, wav_longdic, bq_type, url_dic)
    allbao_ll, zong_file_num = write_uppt_func(uppt_dic, wav_longdic)
    if err_ll:
        err_file = path.join(path.dirname(seg_file), '{}_error.txt'.format(path.basename(seg_file).replace(".txt", '')))
        write_m(err_file, err_ll)
        info_ = "\nERROR: Please view the error logfile：{}".format(err_file)
        print(info_)
        write_m(err_file, err_ll)
    write_m(out_file, allbao_ll)
    # print("一共生成 {} 包数据\n请查看：{}".format(allbao_ll.__len__(), out_file))
    print("文件一共 {} 一共生成 {} 包数据\n请查看：{}".format(zong_file_num, allbao_ll.__len__(), out_file))
    print("\nThere are {} documents, A total of {} packages.\n请查看：{}".format(zong_file_num, allbao_ll.__len__(),
                                                                             out_file))
    # 暂时不转ogg
    # ogg_dir = wav_dir + '_ogg'
    # make_dirs(ogg_dir)
    # wav_to_ogg_func(wav_path_d, ogg_dir, oss_path)
    zip_file, zip_name = FileCompressionZip(out_file)
    print('压缩包已生成, {}'.format(zip_file))
    try:
        # from upload_oss import upload_core
        # zip_oss_url_path = base_url + zip_name
        # upload_core(zip_file, oss_path)
        print('开始上传压缩包')
        zip_oss_url_path = upload_file_minio(zip_file, oss_path)
        print('压缩包已上传, 可直接使用该 url 上项目：{}'.format(zip_oss_url_path))
        time.sleep(2)
        if is_uposs:
            print('开始上传 wav 音频')
            print(wav_dir, oss_path)
            uppool = Pool(8)
            for wav_name, wave_path in wav_path_d.items():
                # print(wav_name, wave_path)
                # upload_file_minio(wave_path, oss_path)
                uppool.apply_async(upload_file_minio, args=(wave_path, oss_path))
            uppool.close()
            uppool.join()
        print('压缩包已上传, 可直接使用该 url 上项目：{}'.format(zip_oss_url_path))
    except Exception as e:
        print('警告！！！上传 oss 失败：{}'.format(e))


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


def get_t_f(str_):
    str_ = str(str_)
    if str_.lower() == 'true':
        bool_ = True
    else:
        bool_ = False
    return bool_


def get_argvs():
    argvs = sys.argv[1:]
    argvs_num = argvs.__len__()
    print('输入参数个数 {}'.format(argvs_num))
    # 返修
    if argvs_num == 6:
        wav_dir, seg_file, oss_path, time_i, text_i, bq_type = argvs
        is_data_none = False
        text_dir = seg_file

    # decode vad 自定义文本
    elif argvs_num == 4:
        wav_dir, seg_file, oss_path, bq_type = argvs
        is_data_none = False
        text_dir = False
        time_i = 0
        text_i = 0

    # 空文本用于上平台识别
    elif argvs_num == 2:
        wav_dir, oss_path = argvs
        seg_file = wav_dir
        text_dir = False
        is_data_none = True
        bq_type = '0'
        time_i = 0
        text_i = 0
    # 返修
    # elif argvs_num == 0:
    #     # X:\data2\gongcheng\dailiukun\脚本测试\asr上平台脚本
    #     wav_dir = r'/projectgroup/data2/gongcheng/dailiukun/脚本测试/asr上平台脚本/wav-cut'
    #     text_dir = r'/projectgroup/data2/gongcheng/dailiukun/脚本测试/asr上平台脚本/1_txt_sep'
    #     seg_file = text_dir
    #     oss_path = 'oss://magicdatacloud/file/audio/chenranfang/test1/'
    #     is_data_none = False
    #     time_i = 0
    #     text_i = -1
    #     bq_type = '0'

    # 上平台空文本
    # elif argvs_num == 0:
    #     wav_dir, is_t = r'/project/data2/ttsdlk/ASR演示样例', 'tru'
    #     # wav_dir, is_t = r'T:\data5\WangXH\2_Tencent\12_Doc校对项目\4_part3_D4_D8\test', 20, 'true'
    #     seg_file = wav_dir
    #     text_dir = False
    #     is_data_none = True
    #     bq_type = '0'
    #     time_i = 0
    #     text_i = 0
    #     oss_path = 'oss://magicdatacloud/file/dailiukun/test/'

    # decode vad 自定义文本
    elif argvs_num == 0:
        seg_file = r'P:\data2\gongcheng\dailiukun\wav-cut_decode.txt'
        wav_dir = r'P:\data2\gongcheng\dailiukun\wav-cut'
        oss_path = 'http://10.64.200.181:7001/magicdatacloud/file/audio/oss沐露测试'
        is_data_none = False
        text_dir = False
        time_i = 0
        bq_type = '0'
        text_i = 0
    else:
        print('参数错误')
        sys.exit(1)
    try:
        time_i = int(time_i)
        text_i = int(text_i)
        if time_i > 0:
            time_i -= 1
        if text_i > 0:
            text_i -= 1
    except ValueError:
        print('输入参数类型错误，应该输入数字，请查看说明文档')
        sys.exit(1)

    if bq_type not in {'0', '1', '2', '3'}:
        print('注意！！！标签还原序号只能是0 1 2 3')
        sys.exit(1)
    if bq_type == '0':
        bq_type = None
    if re.match(r'http', oss_path):
        base_url = oss_path
        is_uposs = False
    else:
        is_uposs = True
        try:
            url_b = endpointText + '/' + bucket_name + '/file/audio/'
            base_url = url_b + oss_path
        except:
            exit("程序结束！！！：oss路径输入错误\neg: oss://magicdatacloud/file/audio/PM姓名全拼/项目名称")
    if not base_url.endswith('/'):
        base_url += '/'
    return [wav_dir, seg_file, oss_path, base_url, time_i, text_i, is_data_none, bq_type, text_dir, is_uposs]


def upload_file_minio(file_path, object_dir):
    #     // access-key: minioadmin
    # secret-key: magicdata@123
    # endpoint: http://10.64.200.181:7001
    # endpointText: 10.64.200.181:7001
    # access-path: http://10.64.200.181:7001/magicdatacloud/
    # bucket-name: magicdatacloud # oss的存储空间
    url_b = endpointText + '/' + bucket_name + '/file/audio/'
    try:
        file_name = os.path.basename(file_path)
        client = minio.Minio(**minio_conf)
        client.fput_object(bucket_name=bucket_name, object_name='file/audio/' + object_dir + '/' + file_name,
                           file_path=file_path)
    except Exception as e:
        print('上传文件失败：{}'.format(e))
    return url_b + object_dir + '/' + file_name


if __name__ == '__main__':
    total_valid_long = 0
    total_wav_long = 0
    argvs_l = get_argvs()
    print('starting', time.asctime())
    print(argvs_l)
    seg_file = argvs_l[1]
    log = get_log(seg_file)
    log.info(str(argvs_l))
    uppt_main_func(argvs_l)
    print('音频总时长：{}s\t{}h'.format(format_num(total_wav_long), format_num(total_wav_long/3600)))
    print('有效时长：{}s\t{}h'.format(format_num(total_valid_long), format_num(total_valid_long/3600)))
    print('END Done.', time.asctime())
