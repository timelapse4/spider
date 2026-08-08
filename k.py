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
        
        name = self.clean(self.match(html, r'<h1[^>]*>(.*?)</h1>') or self.match(html, r'<meta property="og:title" content="(.*?)"'))[span_2](start_span)[span_2](end_span)
        pic = self.fix(self.match(html, r'<meta property="og:image" content="(.*?)"') or self.match(html, r'<img[^>]+class=["\']package-image["\'][^>]*src=["\']([^"\']+)["\']'))[span_3](start_span)[span_3](end_span)
        desc = self.clean(self.match(html, r'<meta property="og:description" content="(.*?)"'))[span_4](start_span)[span_4](end_span)
        remarks = self.clean(self.match(html, r'<div[^>]+class=["\']ep["\'][^>]*>(.*?)</div>'))[span_5](start_span)[span_5](end_span)
        
        ep_links = []
        seen_ep = set()
        
        # ค้นหาปุ่มลิงก์ทั้งหมดในหน้า
        pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.I | re.S)
        
        for link, text in matches:
            full_link = self.fix(link)
            clean_text = self.clean(text)
            
            # กรองลิงก์ระบบ / หมวดหมู่ / ลิงก์ภายนอก
            if any(x in full_link for x in ["/category/", "/country/", "/page/", "/tag/", "/search", "facebook", "twitter", "#"]):
                continue

            # ข้ามลิงก์ที่เป็นรูปแบบวันที่ (เช่น 03-08-2026)[span_6](start_span)[span_6](end_span)
            if re.search(r'\d{2}[-/\.]\d{2}[-/\.]\d{4}', clean_text):
                continue

            ep_num = None

            # 1. พยายามหาเลข EP จาก URL ก่อน (แม่นยำที่สุด เช่น /ep-1/, /ep1/, /episode-2/)
            url_match = re.search(r'/(?:ep|episode)[-_]?(\d+)(?:/|\.html|$|\?)', full_link, re.I)
            if url_match:
                ep_num = int(url_match.group(1))

            # 2. ถ้าใน URL ไม่มี ให้หาจากข้อความในปุ่ม (เช่น EP.1, ตอนที่ 1, หรือตัวเลขโดดๆ 1)
            if ep_num is None:
                text_match = re.search(r'(?:EP\.?|ตอนที่|\b)\s*(\d+)\b', clean_text, re.I)[span_7](start_span)[span_7](end_span)
                if text_match:
                    val = int(text_match.group(1))
                    # ป้องกันการดึงเลขปี ค.ศ. หรือ ID หน้าเว็บที่มากกว่า 300[span_8](start_span)[span_8](end_span)
                    if val < 300:
                        ep_num = val

            # เก็บเฉพาะตอนที่ไม่ซ้ำ
            if ep_num is not None and ep_num not in seen_ep:
                seen_ep.add(ep_num)
                ep_links.append((ep_num, full_link))

        # เรียงลำดับ ตอนที่ 1, 2, 3... ให้ถูกต้อง
        ep_links.sort(key=lambda x: x[0])
        
        # ถ้าหาไม่เจอเลย ให้ใช้หน้าปัจจุบันเป็น ตอนที่ 1
        if not ep_links:
            ep_links = [(1, vid)][span_9](start_span)[span_9](end_span)

        # สร้างระบบเล่น 4 Server สำรอง[span_10](start_span)[span_10](end_span)
        play_flags = ["สำรอง 1", "สำรอง 2", "สำรอง 3", "สำรอง 4"][span_11](start_span)[span_11](end_span)
        play_urls = [][span_12](start_span)[span_12](end_span)

        for server_idx in range(1, 5):[span_13](start_span)[span_13](end_span)
            ep_list = [][span_14](start_span)[span_14](end_span)
            for ep_num, ep_url in ep_links:[span_15](start_span)[span_15](end_span)
                ep_list.append(f"ตอนที่ {ep_num}${ep_url}#srv{server_idx}")[span_16](start_span)[span_16](end_span)
            play_urls.append("#".join(ep_list))[span_17](start_span)[span_17](end_span)

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": self.img(pic),[span_18](start_span)[span_18](end_span)
                "vod_remarks": remarks,[span_19](start_span)[span_19](end_span)
                "type_name": "",
                "vod_year": "",
                "vod_area": "Korea",[span_20](start_span)[span_20](end_span)
                "vod_lang": "",
                "vod_actor": "",
                "vod_director": "",
                "vod_content": desc,[span_21](start_span)[span_21](end_span)
                "vod_play_from": "$$$".join(play_flags),[span_22](start_span)[span_22](end_span)
                "vod_play_url": "$$$".join(play_urls)[span_23](start_span)[span_23](end_span)
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
            video_id = re.search(r'videoembed/(\d+)', embed_url) or re.search(r'video/(\d+)', embed_url)[span_24](start_span)[span_24](end_span)
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
            
            btn_matches = re.findall(r'<[^>]+class=["\'][^"\']*(?:btn-server|server|player-option)[^"\']*["\'][^>]*>', html, re.I)[span_25](start_span)[span_25](end_span)
            
            server_urls = []
            for attr in ["data-link", "data-src", "data-url", "value"]:
                found = re.findall(rf'{attr}=["\']([^"\']+)["\']', html, re.I)[span_26](start_span)[span_26](end_span)
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
                iframes = re.findall(r'<iframe[^>]+(?:src|data-src)=["\']([^"\']+)["\']', html, re.I)[span_27](start_span)[span_27](end_span)
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
        
        cards = re.findall(r'<a\s+class=["\']card["\']\s+href=["\']([^"\']+)["\']>(.*?)</a>', html, re.S | re.I)[span_28](start_span)[span_28](end_span)
        if cards:
            for href, block in cards:
                url = self.fix(href)
                img_m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.I)[span_29](start_span)[span_29](end_span)
                pic = img_m.group(1) if img_m else ""
                
                title_m = re.search(r'<div\s+class=["\']title["\']\s*>(.*?)</div>', block, re.S | re.I)[span_30](start_span)[span_30](end_span)
                if not title_m:
                    title_m = re.search(r'alt=["\']([^"\']+)["\']', block, re.I)[span_31](start_span)[span_31](end_span)
                title = self.clean(title_m.group(1)) if title_m else ""
                
                ep_m = re.search(r'<div\s+class=["\']ep["\']\s*>(.*?)</div>', block, re.S | re.I)[span_32](start_span)[span_32](end_span)
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
        for m in re.finditer(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.S | re.I):[span_33](start_span)[span_33](end_span)
            href, block = m.group(1), m.group(2)[span_34](start_span)[span_34](end_span)
            url = self.fix(href)
            
            if url in seen or any(x in url for x in ["/category/", "/country/", "/page/", "/tag/", "#", "mailto:", "tel:"]):[span_35](start_span)[span_35](end_span)
                continue
                
            img_m = re.search(r'<img[^>]+(?:src|data-src)=["\']([^"\']+)["\']', block, re.I)[span_36](start_span)[span_36](end_span)
            if not img_m:
                continue
            pic = img_m.group(1)
            
            title_m = re.search(r'alt=["\']([^"\']+)["\']', block, re.I)[span_37](start_span)[span_37](end_span)
            title = self.clean(title_m.group(1)) if title_m else self.clean(block)[span_38](start_span)[span_38](end_span)
            
            if title and len(title) > 1 and "logo" not in pic:[span_39](start_span)[span_39](end_span)
                seen.add(url)
                res.append({
                    "vod_id": url,
                    "vod_name": title,
                    "vod_pic": self.img(pic),
                    "vod_remarks": ""
                })
                
        return res
