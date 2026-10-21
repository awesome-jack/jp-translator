#!/usr/bin/env python3
"""jptrans - 日语翻译小工具 (Japanese -> Chinese translator).

两个后端 / Two backends:
  google : Google 翻译免 key 非官方接口 (translate.googleapis.com, client=gtx)
  azure  : 微软 Azure Translator (Bing 翻译引擎), 免费 F0 档每月 200 万字符

用法 / Usage:
  python jptrans.py "こんにちは"                 # 默认 google
  python jptrans.py -e azure "こんにちは"
  python jptrans.py -e both "こんにちは"         # 两个都翻, 对照看
  echo "テキスト" | python jptrans.py
  python jptrans.py -f input.txt -o output.txt
  python jptrans.py -i                           # 交互模式

Azure 需要环境变量 AZURE_TRANSLATOR_KEY 和 AZURE_TRANSLATOR_REGION (如 eastasia)。
只依赖 Python 标准库。
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
GOOGLE_MAX = 4500   # 每段字符上限
AZURE_MAX = 9000    # Azure 单次上限 10000 字符, 留余量


def _chunks(text, limit):
    """按行切分, 尽量不切断句子。"""
    out, buf = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            if buf:
                out.append(buf); buf = ""
            out.append(line[:limit]); line = line[limit:]
        if len(buf) + len(line) > limit:
            out.append(buf); buf = ""
        buf += line
    if buf:
        out.append(buf)
    return out or [""]


def _http(req, retries=3):
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and "google" in req.full_url and i == retries - 1:
                raise RuntimeError("Google 限流 (429): 当前 IP 请求过多, 稍后再试或换 azure 引擎") from None
            if e.code in (429, 500, 502, 503) and i < retries - 1:
                time.sleep(2 ** i)
                continue
            body = e.read().decode("utf-8", "ignore")
            raise RuntimeError(f"HTTP {e.code}: {body[:300]}") from None
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            if i < retries - 1:
                time.sleep(2 ** i)
                continue
            raise RuntimeError(f"网络错误: {getattr(e, 'reason', e)}") from None
        except json.JSONDecodeError:
            raise RuntimeError("返回的不是 JSON, 可能被 Google 人机验证拦截 (IP 请求过多), "
                               "稍后再试或换 azure 引擎") from None


def translate_google(text, src="ja", tgt="zh-CN"):
    result = []
    for part in _chunks(text, GOOGLE_MAX):
        if not part.strip():
            result.append(part); continue
        data = urllib.parse.urlencode({
            "client": "gtx", "sl": src, "tl": tgt, "dt": "t", "q": part,
        }).encode()
        req = urllib.request.Request(
            "https://translate.googleapis.com/translate_a/single",
            data=data, headers={"User-Agent": UA,
                                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
        resp = _http(req)
        result.append("".join(seg[0] for seg in resp[0] if seg and seg[0]))
    return "".join(result)


def translate_azure(text, src="ja", tgt="zh-Hans"):
    key = os.environ.get("AZURE_TRANSLATOR_KEY")
    region = os.environ.get("AZURE_TRANSLATOR_REGION")
    if not key:
        raise RuntimeError("缺少环境变量 AZURE_TRANSLATOR_KEY")
    endpoint = os.environ.get("AZURE_TRANSLATOR_ENDPOINT",
                              "https://api.cognitive.microsofttranslator.com")
    params = urllib.parse.urlencode({
        "api-version": "3.0", "from": src, "to": tgt,
        "profanityAction": "NoAction",   # 不屏蔽粗口/成人词汇
    })
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/json; charset=UTF-8",
        "X-ClientTraceId": str(uuid.uuid4()),
    }
    if region:
        headers["Ocp-Apim-Subscription-Region"] = region
    result = []
    for part in _chunks(text, AZURE_MAX):
        if not part.strip():
            result.append(part); continue
        req = urllib.request.Request(
            f"{endpoint}/translate?{params}",
            data=json.dumps([{"Text": part}]).encode("utf-8"), headers=headers)
        resp = _http(req)
        result.append(resp[0]["translations"][0]["text"])
    return "".join(result)


ENGINES = {"google": translate_google, "azure": translate_azure}
TARGETS = {  # 统一的目标语言代码 -> 各引擎代码
    "zh": ("zh-CN", "zh-Hans"), "zh-tw": ("zh-TW", "zh-Hant"),
    "en": ("en", "en"), "ja": ("ja", "ja"),
}


def run(text, engine, src, tgt):
    g, a = TARGETS.get(tgt.lower(), (tgt, tgt))
    if engine == "both":
        out = []
        for name, code in (("google", g), ("azure", a)):
            try:
                out.append(f"[{name}]\n{ENGINES[name](text, src, code)}")
            except Exception as e:
                out.append(f"[{name}] 失败: {e}")
        return "\n\n".join(out)
    return ENGINES[engine](text, src, g if engine == "google" else a)


def main():
    p = argparse.ArgumentParser(description="日语翻译小工具 (Google / Azure)")
    p.add_argument("text", nargs="*", help="要翻译的文本; 省略则读 stdin")
    p.add_argument("-e", "--engine", choices=["google", "azure", "both"], default="google")
    p.add_argument("-s", "--source", default="ja", help="源语言 (默认 ja, 可用 auto)")
    p.add_argument("-t", "--target", default="zh", help="目标语言: zh / zh-tw / en (默认 zh)")
    p.add_argument("-f", "--file", help="从文件读取")
    p.add_argument("-o", "--output", help="写入文件")
    p.add_argument("-i", "--interactive", action="store_true", help="交互模式")
    a = p.parse_args()
    src = a.source
    if src == "auto":
        src = "auto" if a.engine == "google" else ""

    if a.interactive:
        print(f"交互模式 ({a.engine}), 空行或 Ctrl+C 退出")
        try:
            while True:
                line = input("ja> ").strip()
                if not line:
                    break
                try:
                    print(run(line, a.engine, src, a.target))
                except Exception as e:
                    print(f"错误: {e}")
        except (KeyboardInterrupt, EOFError):
            pass
        return

    if a.file:
        with open(a.file, encoding="utf-8") as f:
            text = f.read()
    elif a.text:
        text = " ".join(a.text)
    else:
        text = sys.stdin.read()
    if not text.strip():
        p.error("没有输入文本")
    try:
        out = run(text, a.engine, src, a.target)
    except Exception as e:
        sys.exit(f"错误: {e}")
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        print(out)


if __name__ == "__main__":
    main()
