# jptrans · 日语翻译小工具

一个零依赖的 Python 命令行工具，把日语翻译成中文（也支持英文、繁体）。
支持两个免费后端，可以单独用，也可以同时用来对照：

| 引擎 | 说明 | 需要 key | 免费额度 |
|---|---|---|---|
| `google` | Google 翻译免 key 非官方接口（浏览器插件常用的那个） | 不需要 | 无明确额度，请求太频繁会被限流 |
| `azure` | 微软 Azure Translator，也就是 Bing 翻译的引擎 | 需要 | F0 免费档每月 200 万字符 |

Azure 请求默认带 `profanityAction=NoAction`，不会屏蔽粗口或成人词汇。

## 安装

只需要 Python 3.8+，不用装任何包：

```bash
git clone https://github.com/awesome-jack/jp-translator.git
cd jp-translator
python jptrans.py "こんにちは"
```

## 用法

```bash
python jptrans.py "今日はいい天気ですね"          # 默认 google
python jptrans.py -e azure "今日はいい天気ですね"  # 用 Azure (Bing)
python jptrans.py -e both "今日はいい天気ですね"   # 两个都翻，方便对照
python jptrans.py -t en "こんにちは"               # 翻成英文 (zh / zh-tw / en)
python jptrans.py -f novel.txt -o novel_zh.txt     # 翻译整个文件，长文本自动分段
echo "テキスト" | python jptrans.py                # 管道输入
python jptrans.py -i                               # 交互模式，一句一句翻
```

## 申请 Azure 免费 key

1. 注册 Azure 账号（一般需要绑定信用卡做验证，免费档不扣费）。
2. 在 Azure 门户创建 **Translator** 资源，定价层选 **F0 (Free)**。
3. 在资源的「密钥和终结点」里复制 **Key** 和 **位置/区域**（例如 `eastasia`）。
4. 设置环境变量：

```bash
# macOS / Linux
export AZURE_TRANSLATOR_KEY="你的key"
export AZURE_TRANSLATOR_REGION="eastasia"

# Windows PowerShell
$env:AZURE_TRANSLATOR_KEY="你的key"
$env:AZURE_TRANSLATOR_REGION="eastasia"
```

不要把 key 写进代码或提交到 GitHub。

## 注意

- `google` 后端是非官方接口，Google 随时可能改动或限流；遇到「人机验证 / 429」就稍等再试，或换 `azure`。
- 中国大陆网络访问 Google 和部分 Azure 端点可能需要代理。
- 翻译内容由第三方服务处理，请自行遵守各服务条款。

## License

MIT
