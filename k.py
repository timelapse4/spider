# -*- coding: utf-8 -*-
import sys
import re
import requests
import json
from urllib.parse import quote, unquote
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://hubserieshd.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "X-Requested-With": "XMLHttpRequest"
        }

    def getName(self):
        return "HubSeriesHD"

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|avi|mkv|mov|ts)(\?|$)|/get_file/', url or "", re.I))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        return {
            "class": [
                {"type_id": "country/korea", "type_name": "ซีรีส์เกาหลี"},
                {"type_id": "country/usa", "type_name": "ซีรีส์ฝรั่ง"},
                {"type_id": "country/china", "type_name": "ซีรีส์จีน"}
            ]
        }

    def homeVideoContent(self):
        return {"list": self.parseList(self.get(self.host + "/country/korea/"))}

    def categoryContent(self, tid, pg, filter, extend):
        path = str(tid or "country/korea").strip("/")
        if str(pg) == "1":
            url = f"{self.host}/{path}/"
        else:
            url = f"{self.host}/{path}/{pg}/"
        
        html = self.get(url)
        return {
            "page": int(pg),
            "pagecount": 999,
            "limit": 20,
            "total": 99999,
            "list": self.parseList(html)
        }

    def detailContent(self, ids):
        vid = ids[0]
        html = self.get(vid)
        
        name = self.clean(self.match(html, r'<h1[^>]*>(.*?)</h1>') or self.match(html, r'<meta property="og:title" content="(.*?)"'))
        pic = self.fix(self.match(html, r'<meta property="og:image" content="(.*?)"') or self.match(html, r'<img[^>]+class=["\']package-image["\'][^>]*src=["\']([^"\']+)["\']'))
        desc = self.clean(self.match(html, r'<meta property="og:description" content="(.*?)"'))
        remarks = self.clean(self.match(html, r'<div[^>]+class=["\']ep["\'][^>]*>(.*?)</div>'))
        
        ep_links = []
        seen_ep = set()
        
        # กวาดหาปุ่มเลือกตอนจากทุกแท็ก (button, div, a, li) ที่มีลิงก์ซ่อนอยู่ใน attribute ต่างๆ
        pattern = r'<(?:button|div|a|li)[^>]+(?:href|data-link|data-src|data-url|value)=["\']([^"\']+)["\'][^>]*>(.*?)</(?:button|div|a|li)>'
        raw_matches = re.findall(pattern, html, re.I | re.S)
        
        # หากไม่เจอแท็กปิด ให้กวาดหาจากแท็กเปิดแบบเดี่ยว
        if not raw_matches:
            pattern_single = r'<(?:button|div|a|li)[^>]+(?:href|data-link|data-src|data-url|value)=["\']([^"\']+)["\'][^>]*>(.*?)'
            raw_matches = re.findall(pattern_single, html, re.I | re.S)

        for link, text in raw_matches:
            clean_text = self.clean(text)
            full_link = self.fix(link)

            # ข้ามลิงก์ระบบ ลิงก์หมวดหมู่ และข้อความที่เป็นวันที่ (เช่น 03-08-2026)
            if any(x in full_link for x in ["/category/", "/country/", "/page/", "/tag/", "/search", "facebook", "twitter", "#"]):
                continue
            if re.search(r'\d{2}[-/\.]\d{2}[-/\.]\d{4}', clean_text):
                continue

            ep_num = None

            # 1. ค้นหาเลขตอนจากข้อความในปุ่ม (เช่น EP.1, ตอนที่ 1, EP 1)
            text_match = re.search(r'(?:EP\.?|ตอนที่)\s*(\d+)', clean_text, re.I)
            if text_match:
                ep_num = int(text_match.group(1))

            # 2. ค้นหาเลขตอนจากโครงสร้าง URL (เช่น /ep-1/, /ep1/, /episode-1)
            if ep_num is None:
                url_match = re.search(r'/(?:ep|episode)[-_]?(\d+)(?:/|\.html|$|\?)', full_link, re.I)
                if url_match:
                    ep_num = int(url_match.group(1))

            # 3. กรณีเป็นตัวเลขโดดๆ ในข้อความ (เช่น "1", "2") แต่ต้องไม่ใช่เลขปี ค.ศ. หรือ ID
            if ep_num is None:
                pure_num_match = re.search(r'^\s*(\d{1,3})\s*$', clean_text)
                if pure_num_match:
                    ep_num = int(pure_num_match.group(1))

            # จัดเก็บตอนที่ไม่ซ้ำ
            if ep_num is not None and ep_num > 0 and ep_num not in seen_ep:
                seen_ep.add(ep_num)
                ep_links.append((ep_num, full_link))

        # เรียงลำดับ ตอนที่ 1, 2, 3...
        ep_links.sort(key=lambda x: x[0])

        # กรณีหาตอนไม่เจอ ให้ใช้ลิงก์หน้าหลักเป็นตอนที่ 1
        if not ep_links:
            ep_links = [(1, vid)]

        # สร้างแท็บตัวเล่น 4 สำรอง
        play_flags = ["สำรอง 1", "สำรอง 2", "สำรอง 3", "สำรอง 4"]
        play_urls = []

        for server_idx in range(1, 5):
            ep_list = []
            for ep_num, ep_url in ep_links:
                ep_list.append(f"ตอนที่ {ep_num}${ep_url}#srv{server_idx}")
            play_urls.append("#".join(ep_list))

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": self.img(pic),
                "vod_remarks": remarks,
                "type_name": "",
                "vod_year": "",
                "vod_area": "Korea",
                "vod_lang": "",
                "vod_actor": "",
                "vod_director": "",
                "vod_content": desc,
                "vod_play_from": "$$$".join(play_flags),
                "vod_play_url": "$$$".join(play_urls)
            }]
        }

    def searchContent(self, key, quick, pg="1"):
        q = quote(key)
        url = f"{self.host}/search?name={q}"
        html = self.get(url)
        return {"list": self.parseList(html), "page": int(pg)}

    def parse_ok_ru(self, embed_url):
        """เจาะเอา Direct Link จาก OK.ru"""
        try:
            video_id = re.search(r'videoembed/(\d+)', embed_url) or re.search(r'video/(\d+)', embed_url)
            if not video_id:
                return ""
            vid = video_id.group(1)
            
            api_url = f"https://ok.ru/dk?cmd=videoPlayerMetadata&vId={vid}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "X-Requested-With": "XMLHttpRequest"
            }
            res = requests.post(api_url, headers=headers, timeout=8, verify=False)
            data = res.json()
            
            if "hlsManifestUrl" in data:
                return data["hlsManifestUrl"]
            
            if "videos" in data:
                videos = data["videos"]
                for quality in ["full", "hd", "sd", "low"]:
                    for v in videos:
                        if v.get("name") == quality and "url" in v:
                            return v["url"]
                if len(videos) > 0 and "url" in videos[-1]:
                    return videos[-1]["url"]
        except Exception:
            pass
        return ""

    def playerContent(self, flag, id, vipFlags):
        srv_idx = 1
        url = id
        if "#srv" in id:
            parts = id.split("#srv")
            url = parts[0]
            srv_idx = int(parts[1])

        try:
            html = self.get(url)
            
            btn_matches = re.findall(r'<[^>]+class=["\'][^"\']*(?:btn-server|server|player-option)[^"\']*["\'][^>]*>', html, re.I)
            
            server_urls = []
            for attr in ["data-link", "data-src", "data-url", "value"]:
                found = re.findall(rf'{attr}=["\']([^"\']+)["\']', html, re.I)
                for f in found:
                    f_fix = self.fix(f)
                    if not any(x in f_fix.lower() for x in ["ufa", "banner", "ads", "popup"]) and f_fix not in server_urls:
                        server_urls.append(f_fix)

            selected_url = ""
            if len(server_urls) >= srv_idx:
                selected_url = server_urls[srv_idx - 1]
            elif len(server_urls) > 0:
                selected_url = server_urls[0]

            if not selected_url:
                iframes = re.findall(r'<iframe[^>]+(?:src|data-src)=["\']([^"\']+)["\']', html, re.I)
                valid_iframes = []
                for iframe in iframes:
                    iframe_fix = self.fix(iframe)
                    if not any(x in iframe_fix.lower() for x in ["ufa", "banner", "ads", "popup"]):
                        valid_iframes.append(iframe_fix)
                
                if len(valid_iframes) >= srv_idx:
                    selected_url = valid_iframes[srv_idx - 1]
                elif len(valid_iframes) > 0:
                    selected_url = valid_iframes[0]

            if not selected_url:
                selected_url = url

            if "ok.ru" in selected_url:
                direct_ok = self.parse_ok_ru(selected_url)
                if direct_ok:
                    return {
                        "parse": 0,
                        "playUrl": "",
                        "url": direct_ok,
                        "header": {"User-Agent": "Mozilla/5.0", "Referer": "https://ok.ru/"}
                    }
                return {
                    "parse": 1,
                    "playUrl": "",
                    "url": selected_url,
                    "header": {"User-Agent": self.headers["User-Agent"], "Referer": "https://ok.ru/"}
                }

            if self.isVideoFormat(selected_url):
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": selected_url,
                    "header": self.headers
                }

            return {
                "parse": 1,
                "playUrl": "",
                "url": selected_url,
                "header": {
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": url
                }
            }

        except Exception:
            pass

        return {
            "parse": 1,
            "playUrl": "",
            "url": url,
            "header": self.headers
        }

    def localProxy(self, param):
        url = ""
        for k in ["url", "img", "pic"]:
            v = param.get(k, "")
            if isinstance(v, list):
                v = v[0] if len(v) > 0 else ""
            if v:
                url = v
                break
        url = unquote(url or "")
        if not url:
            return [404, "text/plain", "", ""]
        try:
            h = dict(self.headers)
            h.update({
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Referer": self.host + "/"
            })
            r = requests.get(url, headers=h, timeout=10, verify=False)
            ct = r.headers.get("Content-Type", "")
            if r.status_code == 200 and r.content:
                return [200, ct or "image/jpeg", r.content, ""]
        except Exception:
            pass
        return [404, "text/plain", "", ""]

    def destroy(self):
        return "Destroyed"

    def get(self, url):
        try:
            r = requests.get(url, headers=self.headers, timeout=10, verify=False)
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except Exception:
            return ""

    def match(self, text, rule):
        m = re.search(rule, text or "", re.S)
        return m.group(1) if m else ""

    def clean(self, text):
        return re.sub(r"\s+", " ", re.sub(r"<.*?>", "", text or "").replace("&nbsp;", " ")).strip()

    def fix(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return url

    def img(self, url):
        url = self.fix(url)
        if not url:
            return ""
        try:
            return self.getProxyUrl() + "&url=" + quote(url, safe="")
        except Exception:
            return url

    def parseList(self, html):
        res = []
        if not html:
            return res
        
        cards = re.findall(r'<a\s+class=["\']card["\']\s+href=["\']([^"\']+)["\']>(.*?)</a>', html, re.S | re.I)
        if cards:
            for href, block in cards:
                url = self.fix(href)
                img_m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.I)
                pic = img_m.group(1) if img_m else ""
                
                title_m = re.search(r'<div\s+class=["\']title["\']\s*>(.*?)</div>', block, re.S | re.I)
                if not title_m:
                    title_m = re.search(r'alt=["\']([^"\']+)["\']', block, re.I)
                title = self.clean(title_m.group(1)) if title_m else ""
                
                ep_m = re.search(r'<div\s+class=["\']ep["\']\s*>(.*?)</div>', block, re.S | re.I)
                remarks = self.clean(ep_m.group(1)) if ep_m else ""
                
                if url and title:
                    res.append({
                        "vod_id": url,
                        "vod_name": title,
                        "vod_pic": self.img(pic),
                        "vod_remarks": remarks
                    })
            return res

        seen = set()
        for m in re.finditer(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.S | re.I):
            href, block = m.group(1), m.group(2)
            url = self.fix(href)
            
            if url in seen or any(x in url for x in ["/category/", "/country/", "/page/", "/tag/", "#", "mailto:", "tel:"]):
                continue
                
            img_m = re.search(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\']', block, re.I)
            if not img_m:
                continue
            pic = img_m.group(1)
            
            title_m = re.search(r'alt=["\']([^"\']+)["\']', block, re.I)
            title = self.clean(title_m.group(1)) if title_m else self.clean(block)
            
            if title and len(title) > 1 and "logo" not in pic:
                seen.add(url)
                res.append({
                    "vod_id": url,
                    "vod_name": title,
                    "vod_pic": self.img(pic),
                    "vod_remarks": ""
                })
                
        return res
