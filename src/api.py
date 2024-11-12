import requests
from typing import Dict, List
from bs4 import BeautifulSoup
import logging
from urllib import parse
import pathlib

logger = logging.getLogger(__name__)

# fmt:off
# 视频合集基本信息
api_collection_url = 'https://api.cntv.cn/NewVideoset/getVideoAlbumInfoByVideoId?id={}&serviceId=tvcctv'
# 视频合集详细信息
api_video_url = "https://api.cntv.cn/NewVideo/getVideoListByAlbumIdNew?id={}&serviceId=tvcctv&pub=1&mode=0&part=0&n=36&sort=asc"

# fmt:on


class CCTVVideoDownloaderAPI:
    def __init__(self):
        self._COLUMN_INFO = None
        # self.sess = requests.session

    def get_video_list(self, video_id: str) -> Dict[str, List[str]]:
        # api_url = f"https://api.cntv.cn/NewVideo/getVideoListByColumn?id={id}&n=20&sort=desc&p=1&mode=0&serviceId=tvcctv"
        api_url = api_video_url.format(video_id)
        response = requests.get(api_url, timeout=10)
        logger.debug(response.text)
        # json格式解析

        if 'msg' in response.text:
            logger.error(f'get_video_list 解析错误: vid={video_id}')
            return

        resp_format = response.json()

        list_detials = resp_format["data"]["list"]
        # 定义列表
        list_information = []
        list_index = []
        # 索引
        index = 0
        # 遍历
        for i in list_detials:
            guid, time, title, image, brief = i["guid"], i["time"], i["title"], i["image"], i["brief"]
            list_tmp = [guid, time, title, image, brief]
            list_information.append(list_tmp)
            list_index.append(index)
            index += 1
        # 列表转字典
        dict_information = dict(zip(list_index, list_information))
        self._COLUMN_INFO = dict_information
        return self._COLUMN_INFO

    def get_column_info(self, index: int) -> Dict[str, str]:
        if self._COLUMN_INFO != None:
            video_info = self._COLUMN_INFO[index]
            time = video_info[1]
            title = video_info[2]
            brief = self.brief_formating(video_info[4])
            # 获取图片
            try:
                response = requests.get(video_info[3])
                if response.status_code == 200:
                    image = response.content
                else:
                    image = None
            except Exception:
                image = None
            column_info = {"time": time, "title": title, "brief": brief, "image": image}
            return column_info

    def brief_formating(self, s: str) -> str:
        '''格式化介绍信息'''
        # 首先替换所有空格和\r为换行符
        replaced = s.replace(' ', '\n')
        replaced = replaced.replace('\r', '\n')

        # 消除连续的换行符
        import re

        result = re.sub(r'\n+', '\n', replaced)

        # string = ""
        # for i in range(0, len(result), 13):
        #     string += result[i:i+13] + '\n'

        return result

    #  已弃用
    def _get_http_video_info(self, guid: str) -> Dict:
        api_url = f"https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid={guid}"
        response = requests.get(api_url, timeout=10)
        # json格式解析
        resp_format = response.json()
        return resp_format

    def get_m3u8_urls_450(self, guid: str) -> List:
        api_url = f"https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid={guid}"
        response = requests.get(api_url, timeout=10)
        resp_format = response.json()
        hls_enc2_url = resp_format["hls_url"]
        # 获取main.m3u8
        main_m3u8 = requests.get(hls_enc2_url, timeout=5)
        main_m3u8_txt = main_m3u8.text
        # 切分
        main_m3u8_list = main_m3u8_txt.split("\n")
        HD_m3u8_url = main_m3u8_list[-2]
        hls_head = hls_enc2_url.split("/")[2]  # eg:dhls2.cntv.qcloudcdn.com
        HD_m3u8_url = "https://" + hls_head + HD_m3u8_url
        # 获取2000.m3u8，即高清m3u8文件，内含ts
        video_m3u8 = requests.get(HD_m3u8_url)
        # 提取ts列表
        video_m3u8_list = video_m3u8.text.split("\n")
        video_list = []
        import re

        for i in video_m3u8_list:
            if re.match(r"\d+.ts", i):
                video_list.append(i)
        # 转化为urls列表
        dl_url_head = HD_m3u8_url[:-8]
        urls = []
        for i in video_list:
            tmp = dl_url_head + i
            urls.append(tmp)
        # print(urls)
        return urls

    def get_play_column_info(self, url: str) -> List:
        '''从视频播放页链接获取栏目标题和ID'''

        def _url(link):
            '''从原始页面链接获取视频名称及ID'''
            # url = 'https://api.cntv.cn/NewVideoset/getVideoAlbumInfoByVideoId?id={}&serviceId=tvcctv'
            # 如果 link == 'https://tv.cctv.com/2024/07/20/VIDEiGA59ClpEojV1wBSgw2Q240720.shtml?spm=C28340.Pu9TN9YUsfNZ.S93183.28'
            # page_id should be VIDEiGA59ClpEojV1wBSgw2Q240720
            page_id = pathlib.PurePosixPath(parse.urlsplit(link).path).stem
            url = api_collection_url.format(page_id)
            return url

        try:
            response = requests.get(_url(url), timeout=10)
            # {
            #     "data": {
            #         "id": "VIDAVtVHU1IAcHgq95ohrCBJ240605",
            #         "title": "《海天雄鹰》",
            #         "url": "https://tv.cctv.com/2024/06/05/VIDAVtVHU1IAcHgq95ohrCBJ240605.shtml",
            #         "image": "https://p1.img.cctvpic.com/photoAlbum/vms/image/de57dcd72ca7637a4b8e4fa299e67033.jpg",
            #         "image2": "https://p1.img.cctvpic.com/photoAlbum/vms/image/de57dcd72ca7637a4b8e4fa299e67033.jpg",
            #         "image3": "https://p1.img.cctvpic.com/photoAlbum/vms/image/de57dcd72ca7637a4b8e4fa299e67033.jpg",
            #         "brief": "讲述了随着中国第一艘航母平台开始出海试航，中国海军成立了首支舰载机试飞大队，以谢振宇、余涛为代表的顶尖青年飞行员，在海军功勋飞行员秦大地大队长的带领下，以严谨的科学态度和时不我待的使命意识，攻克了舰载机着舰和起飞技术这一世界性难题。中国航母终于成军，谢振宇和余涛传承了老一辈的“海天雄鹰精神”，率领中国舰载机机群在辽阔海空上展翅翱翔。",
            #         "fc": "电视剧",
            #         "sc": "军旅",
            #         "order": 1
            #     }
            # }
            d = response.json()
            if 'data' in d.keys():  # response 为 json 列表
                result = [d['data']['title'], d['data']['id']]
                return result

        except Exception as e:
            logger.error(f"获取合集信息出错: {e}")
            return


if __name__ == "__main__":
    api = CCTVVideoDownloaderAPI()
    import json

    list1 = api.get_video_list("TOPC1451464665008914")
    print(list1)
    # list2 = api._get_http_video_info("8665a11a622e5601e64663a77355af15")
    # print(json.dumps(list2, indent=4))
    list3 = api.get_m3u8_urls_450("a5324e8cdda44d72bd569d1dba2e4988")
    # print(list3)
    # tmp = api.get_column_info(0)
    # print(tmp)
    # print(api.get_play_column_info("https://tv.cctv.com/2024/06/21/VIDEs2DfNN70XHJ1OySUipyV240621.shtml?spm=C31267.PXDaChrrDGdt.EbD5Beq0unIQ.3"))
