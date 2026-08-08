# -*- coding: utf-8 -*-
import sys
import re
import requests
from urllib.parse import quote, unquote
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://hubserieshd.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Referer": self.host + "/",
            "Origin": self.host
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
        
        episodes = []
        seen_ep = set()
        
        pattern = r'<[^>]+(?:href|data-link|data-src|data-url)=["\']([^"\']+)["\'][^>]*>(.*?)</[^>]+>'
        ep_links = []
        for link, text in re.findall(pattern, html, re.I | re.S):
            clean_text = self.clean(text)
            ep_match = re.search(r'(?:EP\.?|ตอนที่|\b)?\s*(\d+)', clean_text, re.I)
            if ep_match:
                ep_num = str(int(ep_match.group(1)))
                if ep_num not in seen_ep and len(ep_num) <= 3 and not any(x in link for x in ["/category/", "/country/", "/page/", "/tag/"]):
                    seen_ep.add(ep_num)
                    ep_links.append((int(ep_num), self.fix(link)))

        ep_links.sort(key=lambda x: x[0])

        for ep_num, ep_url in ep_links:
            episodes.append(f"ตอนที่ {ep_num}${ep_url}")

        if not episodes:
            episodes.append(f"เล่นMain${vid}")

        play_str = "#".join(episodes)

        # เพิ่มการแบ่งตัวเลือก Server สำรอง 1-4 ให้ตรงตามหน้าเว็บ
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
                "vod_play_from": "สำรอง 1$$$สำรอง 2$$$สำรอง 3$$$สำรอง 4",
                "vod_play_url": f"{play_str}$$$+{play_str}$$$++{play_str}$$$+++{play_str}"
            }]
        }

    def searchContent(self, key, quick, pg="1"):
        q = quote(key)
        url = f"{self.host}/search?name={q}"
        html = self.get(url)
        return {"list": self.parseList(html), "page": int(pg)}

    def playerContent(self, flag, id, vipFlags):
        # ลบสัญลักษณ์ตัวแยกสำรอง (+) ออกจาก URL
        clean_url = id.lstrip('+')

        # ถ้า id ที่ได้มาเป็นลิงก์ ok.ru โดยตรงอยู่แล้ว (resolve มาจากขั้นตอนก่อนหน้า)
        # ให้ไป resolve หา URL วิดีโอจริงจาก ok.ru ต่อ
        if "ok.ru/videoembed" in clean_url:
            target_url = self.resolveOkRu(clean_url) or clean_url
        else:
            # ดึง HTML ของหน้ารายตอนเพื่อเจาะหา iframe เครื่องเล่นวิดีโอหลัก
            html = self.get(clean_url)
            iframe_src = self.match(html, r'<iframe[^>]+src=["\']([^"\']+)["\']') or self.match(html, r'data-src=["\']([^"\']+)["\']')
            target_url = self.fix(iframe_src) if iframe_src else clean_url
            if "ok.ru/videoembed" in target_url:
                target_url = self.resolveOkRu(target_url) or target_url

        return {
            "parse": 1,
            "playUrl": "",
            "url": target_url,
            "header": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
                "Referer": self.host + "/"
            },
            # ปรับ Rule ดักจับเฉพาะ M3U8/HLS หรือ Embed Player และตัด .mp4 โฆษณาออกทั้งหมด
            "rule": ".*?(?:hls|m3u8|embed|ok\.ru/videoembed|vkuser\.net).*"
        }

    def resolveOkRu(self, embed_url):
        """แกะหน้า ok.ru/videoembed/xxxx เอา URL วิดีโอจริงจาก data-options JSON"""
        try:
            html = self.get(embed_url)
            raw = self.match(html, r'data-options=["\']([^"\']+)["\']')
            if not raw:
                return ""
            import html as htmlmod
            import json
            decoded = htmlmod.unescape(raw)
            data = json.loads(decoded)
            videos = data.get("videos") or data.get("metadata", {}).get("videos") or []
            if isinstance(videos, str):
                # บางกรณี metadata ยังเป็น string JSON ซ้อนอยู่อีกชั้น
                videos = json.loads(videos).get("videos", [])
            if not videos:
                return ""
            # เลือกคุณภาพสูงสุดที่มี (เรียงตาม index ท้ายสุด มักเป็นคุณภาพสูงสุด)
            best = videos[-1]
            return best.get("url", "")
        except Exception:
            return ""

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
