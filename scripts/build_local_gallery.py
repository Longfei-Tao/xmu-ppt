#!/usr/bin/env python3
"""Build a local-only, offline template gallery.

大白话：生成一个只放在你电脑上的「模板目录网页」，双击就能按分类看封面。
不改在线画廊、不改 README、不上传任何图片；数据用 <script> 直接加载，
所以 file:// 双击打开也能用（不会被浏览器的跨域限制拦住）。
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_CATALOG = ROOT / "skills/xmu-ppt/templates/external/external_catalog.json"
BUILTIN_CATALOG = ROOT / "docs/templates/catalog.json"
ROOT_LOCAL = ROOT / "skills/xmu-ppt/templates/external/root.local.json"
CATEGORIES_FILE = ROOT / "skills/xmu-ppt/templates/external/categories.json"
DUP_FILE = ROOT / "skills/xmu-ppt/templates/external/duplicates.json"
SOURCE_MAP_FILE = ROOT / "skills/xmu-ppt/templates/external/source_map.local.json"
BUILTIN_PREVIEWS = ROOT / "docs/templates/previews"

OUT = ROOT / "local-gallery"
COVERS = OUT / "covers"
PAGES = OUT / "pages"
CATEGORY_DIR = OUT / "categories"
PLACEHOLDER = "placeholder.webp"

COVER_W, COVER_H = 960, 540
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def make_placeholder(label: str = "暂无预览") -> None:
    """生成一张明确标注「暂无预览」的占位图，绝不伪装成模板外观。"""
    OUT.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (COVER_W, COVER_H), "#EEF2F6")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype(FONT_PATH, 34)
        small = ImageFont.truetype(FONT_PATH, 20)
    except OSError:
        font = small = ImageFont.load_default()
    draw.text((COVER_W // 2, COVER_H // 2 - 30), label,
              fill="#7C8B9C", font=font, anchor="mm")
    draw.text((COVER_W // 2, COVER_H // 2 + 24), "本地模板库 · 仅本机浏览",
              fill="#A6B2BF", font=small, anchor="mm")
    image.save(OUT / PLACEHOLDER, "WEBP", quality=80)


def fit_cover(image: Image.Image) -> Image.Image:
    """等比缩放并居中留白，不拉伸、不裁切模板原图。"""
    image = image.convert("RGB")
    canvas = Image.new("RGB", (COVER_W, COVER_H), "#FFFFFF")
    image.thumbnail((COVER_W, COVER_H), Image.Resampling.LANCZOS)
    canvas.paste(image, ((COVER_W - image.width) // 2, (COVER_H - image.height) // 2))
    return canvas


def extract_embedded_cover(pptx: Path, dest: Path) -> bool:
    """从 pptx 自带的 docProps/thumbnail.jpeg 抽封面；只读，不渲染、不改动原件。"""
    try:
        with zipfile.ZipFile(pptx) as zf:
            if "docProps/thumbnail.jpeg" not in zf.namelist():
                return False
            raw = zf.read("docProps/thumbnail.jpeg")
        with Image.open(io.BytesIO(raw)) as image:
            fit_cover(image).save(dest, "WEBP", quality=82)
        return True
    except (OSError, zipfile.BadZipFile, ValueError):
        return False


def display_name(raw: str) -> str:
    """展示名二次脱敏；索引已清洗，这里兜底去掉任何残留占位。"""
    s = (raw or '').replace('_XXX', '').replace('XXX', '').strip('_ ·-')
    return s or '未命名模板'


def render_cover(template_id: str, dest: Path) -> bool:
    """统一用本机渲染的第 1 页做封面：满幅 16:9、尺寸一致、清晰。"""
    first = PAGES / template_id / '01.webp'
    if not first.exists():
        return False
    with Image.open(first) as image:
        image.convert('RGB').resize((COVER_W, COVER_H), Image.Resampling.LANCZOS).save(
            dest, "WEBP", quality=85
        )
    return True


def collect_cards() -> tuple[list[dict], dict]:
    external = load_json(EXTERNAL_CATALOG)
    builtin = load_json(BUILTIN_CATALOG)
    categories = load_json(CATEGORIES_FILE)["categories"]
    removed = {g["remove"] for g in load_json(DUP_FILE)["groups"]}
    source_map = (load_json(SOURCE_MAP_FILE, {}) or {}).get("paths", {})
    root = Path(load_json(ROOT_LOCAL)["root"])
    name_by_id = {c["id"]: c["name"] for c in categories}

    cards: list[dict] = []

    # 内置 15 套：封面复用仓库已有预览图，天然满幅清晰
    for deck in builtin:
        cover = COVERS / f"{deck['id']}.webp"
        source_png = BUILTIN_PREVIEWS / f"{int(deck['number']):02d}.png"
        if source_png.exists():
            with Image.open(source_png) as image:
                fit_cover(image).save(cover, "WEBP", quality=82)
            cover_status = "builtin"
        else:
            cover_status = "placeholder"
        cards.append({
            "number": int(deck["number"]),
            "id": deck["id"],
            "name": display_name(deck["name"]),
            "style": deck.get("style", ""),
            "tags": deck.get("tags", []),
            "category": "institution",
            "category_name": name_by_id.get("institution", "厦门大学等高校/机构风格"),
            "pages": None,
            "cover": f"covers/{cover.name}",
            "cover_status": cover_status,
            "pages_dir": None,
            "namespace": "builtin",
            "rights": "内置模板（素材许可见 docs/assets.md）",
            "flags": [],
            "routes": deck.get("routes", []),
        })

    # 外部模板：跳过重复副本；封面统一改用渲染第 1 页
    for item in external["templates"]:
        if item["id"] in removed:
            continue
        cover = COVERS / f"{item['id']}.webp"
        if render_cover(item["id"], cover):
            status = "rendered"
        else:
            rel = source_map.get(item.get("source_key"))
            pptx = root / rel if rel else None
            if pptx and pptx.exists() and extract_embedded_cover(pptx, cover):
                status = "embedded"
            else:
                status = "placeholder"
        flags = []
        if item.get("promo_text"):
            flags.append("含推广文字")
        if item.get("security_flags"):
            flags.append("含特殊媒体/外部链接")
        cards.append({
            "number": int(item["number"]),
            "id": item["id"],
            "name": display_name(item["name"]),
            "style": item.get("style", ""),
            "tags": item.get("tags", []),
            "category": item["primary_category"],
            "category_name": name_by_id.get(item["primary_category"], item["category_name"]),
            "pages": item["page_count"],
            "cover": f"covers/{cover.name}",
            "cover_status": status,
            "pages_dir": f"pages/{item['id']}",
            "namespace": item["namespace"],
            "rights": "来源待核验 · 不可再分发",
            "flags": flags,
            "routes": ["strict-native"],
            "style_prefix": item.get("style_prefix", ""),
            "sha8": item["sha256"][:8],
        })

    cards.sort(key=lambda c: c["number"])
    counts = {
        "total": len(cards),
        "builtin": sum(1 for c in cards if c["namespace"] == "builtin"),
        "external": sum(1 for c in cards if c["namespace"] != "builtin"),
        "covers_ready": sum(1 for c in cards if c["cover_status"] != "placeholder"),
        "covers_missing": sum(1 for c in cards if c["cover_status"] == "placeholder"),
        "duplicates_removed": len(removed),
        "by_category": {},
    }
    for card in cards:
        key = card["category"]
        counts["by_category"][key] = counts["by_category"].get(key, 0) + 1
    return cards, {
        "generated_on": date.today().isoformat(),
        "categories": [{"id": c["id"], "name": c["name"]} for c in categories],
        "counts": counts,
        "templates": cards,
    }

def write_catalog_js(data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    (OUT / "catalog.js").write_text(
        "window.LOCAL_CATALOG = " + payload + ";\n", encoding="utf-8"
    )


HTML = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>本地模板库 · 离线浏览</title>
<style>
  :root {
    --ink: #17324D; --muted: #63758A; --line: #E3E8EF; --bg: #F7F9FB;
    --card: #FFFFFF; --accent: #2F5D8C; --accent-soft: #EEF4FA;
    --warn: #B4690E; --warn-soft: #FFF6E8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC",
                 "Microsoft YaHei", "Segoe UI", sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  header {
    padding: 28px 32px 20px; background: var(--card);
    border-bottom: 1px solid var(--line);
  }
  h1 { margin: 0 0 6px; font-size: 22px; font-weight: 600; letter-spacing: .2px; }
  .sub { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.6; }
  .bar {
    display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
    padding: 16px 32px; background: var(--card); border-bottom: 1px solid var(--line);
  }
  .nav { display: flex; flex-wrap: wrap; gap: 8px; }
  .nav a, .chip {
    display: inline-block; padding: 7px 14px; border-radius: 999px;
    border: 1px solid var(--line); background: var(--card); color: var(--ink);
    font-size: 13px; text-decoration: none; cursor: pointer;
    transition: background .18s ease, border-color .18s ease, transform .18s ease;
  }
  .nav a:hover, .chip:hover { background: var(--accent-soft); border-color: #C9DCEC; }
  .nav a:active, .chip:active { transform: scale(.97); }
  .nav a.on { background: var(--accent); border-color: var(--accent); color: #fff; }
  .nav a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible {
    outline: 3px solid rgba(47,93,140,.32); outline-offset: 2px;
  }
  input[type=search], select {
    padding: 8px 12px; border: 1px solid var(--line); border-radius: 9px;
    background: var(--card); color: var(--ink); font-size: 13px; min-width: 180px;
  }
  .status { padding: 14px 32px 0; color: var(--muted); font-size: 13px; }
  .grid {
    display: grid; gap: 18px; padding: 18px 32px 48px;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  }
  .card {
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    overflow: hidden; transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease;
  }
  .card:hover { box-shadow: 0 8px 24px rgba(23,50,77,.10); transform: translateY(-2px); border-color: #CFDCE8; }
  .card img { width: 100%; aspect-ratio: 16/9; object-fit: cover; display: block; background: #EEF2F6; }
  .body { padding: 12px 14px 14px; }
  .title { margin: 0 0 4px; font-size: 14px; font-weight: 600; }
  .meta { margin: 0 0 8px; color: var(--muted); font-size: 12px; line-height: 1.5; }
  .badges { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px; }
  .badge { font-size: 11px; padding: 3px 8px; border-radius: 6px; background: var(--accent-soft); color: var(--accent); }
  .badge.warn { background: var(--warn-soft); color: var(--warn); }
  button.choose {
    width: 100%; padding: 8px 10px; border: 1px solid var(--line); border-radius: 9px;
    background: var(--card); color: var(--accent); font-size: 13px; cursor: pointer;
    transition: background .18s ease, transform .18s ease;
  }
  button.choose:hover { background: var(--accent-soft); }
  button.choose:active { transform: scale(.98); }
  dialog {
    width: min(980px, 94vw); max-height: 92vh; padding: 0; border: 1px solid var(--line);
    border-radius: 16px; box-shadow: 0 24px 64px rgba(23,50,77,.22);
  }
  dialog::backdrop { background: rgba(23,50,77,.36); }
  .dlg-head { display: flex; justify-content: space-between; align-items: center; padding: 18px 22px; border-bottom: 1px solid var(--line); }
  .dlg-head h2 { margin: 0; font-size: 17px; font-weight: 600; }
  .dlg-body { padding: 20px 22px 24px; overflow: auto; max-height: 76vh; }
  .hero { width: 100%; max-height: 330px; object-fit: contain; background: var(--bg); border-radius: 10px; border: 1px solid var(--line); display: block; }
  .film { display: flex; gap: 10px; overflow-x: auto; padding: 12px 0 4px; }
  .film figure { flex: 0 0 176px; margin: 0; }
  .film img { width: 176px; aspect-ratio: 16/9; object-fit: cover; border-radius: 8px; border: 1px solid var(--line); background: #EEF2F6; }
  .film figcaption { font-size: 11px; color: var(--muted); padding-top: 4px; text-align: center; }
  .film figure.key img { border: 2px solid var(--accent); }
  .film figure.key figcaption { color: var(--accent); font-weight: 600; }
  .facts { font-size: 12px; color: var(--muted); line-height: 1.8; margin: 12px 0; }
  textarea {
    width: 100%; min-height: 96px; padding: 12px; border: 1px solid var(--line);
    border-radius: 9px; font-size: 12px; line-height: 1.7; color: var(--ink);
    background: var(--bg); resize: vertical;
  }
  .dlg-actions { display: flex; gap: 10px; justify-content: flex-end; padding: 14px 22px; border-top: 1px solid var(--line); }
  .dlg-actions button { padding: 8px 16px; border-radius: 9px; border: 1px solid var(--line); background: var(--card); color: var(--ink); cursor: pointer; font-size: 13px; }
  .dlg-actions button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .note { font-size: 12px; color: var(--muted); padding: 0 32px 32px; line-height: 1.7; }
  code { background: var(--accent-soft); padding: 1px 5px; border-radius: 4px; font-size: 12px; }
</style>
</head>
<body>
<header>
  <h1>本地模板库 · 离线浏览</h1>
  <p class="sub">仅在你这台电脑上显示，不上传 GitHub、不改动在线画廊。数据来自 <code>catalog.js</code>，双击本文件即可打开。模板原件与预览图均不入库。</p>
</header>
<div class="bar">
  <nav class="nav" id="nav"></nav>
  <input type="search" id="search" placeholder="搜索名称 / 风格 / 标签" />
  <select id="style"><option value="">全部视觉风格</option></select>
</div>
<div class="status" id="status"></div>
<main class="grid" id="grid"></main>
<p class="note" id="note"></p>

<dialog id="detail">
  <div class="dlg-head"><h2 id="dlg-title"></h2><button id="dlg-close" aria-label="关闭">关闭</button></div>
  <div class="dlg-body">
    <img class="hero" id="dlg-cover" alt="模板封面" />
    <div class="film" id="dlg-film"></div>
    <p class="facts" id="dlg-facts"></p>
    <textarea id="dlg-prompt" readonly></textarea>
  </div>
  <div class="dlg-actions">
    <span id="dlg-hint" style="flex:1; align-self:center; font-size:12px; color:var(--muted)"></span>
    <button class="primary" id="dlg-copy">复制给 AI 的选用指令</button>
  </div>
</dialog>

<script src="catalog.js"></script>
<script>
'use strict';
const $ = id => document.getElementById(id);
const DATA = window.LOCAL_CATALOG || {categories: [], templates: [], counts: {}};
const PAGES_PER_DECK = 6;
let current = null;

function currentCategory() {
  const m = location.hash.match(/cat=([^&]+)/);
  return m ? decodeURIComponent(m[1]) : 'all';
}
function currentStyle() {
  const m = location.hash.match(/style=([^&]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

function buildNav() {
  const cats = [{id: 'all', name: '全部'}].concat(DATA.categories.filter(c => c.id !== 'medical-other'));
  $('nav').replaceChildren();
  for (const c of cats) {
    const a = document.createElement('a');
    a.textContent = c.name;
    a.href = '#cat=' + encodeURIComponent(c.id);
    a.dataset.cat = c.id;
    a.addEventListener('click', () => { $('style').value = ''; render(); });
    $('nav').append(a);
  }
  const styles = [...new Set(DATA.templates.map(t => t.style_prefix).filter(Boolean))].sort();
  for (const s of styles) {
    const o = document.createElement('option');
    o.value = s; o.textContent = s;
    $('style').append(o);
  }
}

function render() {
  const cat = currentCategory();
  const style = $('style').value || currentStyle();
  const q = $('search').value.trim().toLowerCase();
  document.querySelectorAll('#nav a').forEach(a => a.classList.toggle('on', a.dataset.cat === cat));
  const matches = DATA.templates.filter(t =>
    (cat === 'all' || t.category === cat) &&
    (!style || t.style_prefix === style) &&
    (!q || (t.name + ' ' + t.style + ' ' + t.tags.join(' ') + ' ' + t.id).toLowerCase().includes(q))
  );
  const grid = $('grid');
  grid.replaceChildren();
  for (const t of matches) {
    const card = document.createElement('article');
    card.className = 'card';
    const img = document.createElement('img');
    img.src = t.cover;
    img.alt = t.name + ' 封面';
    img.loading = 'lazy';
    img.addEventListener('error', () => { img.onerror = null; img.src = 'PLACEHOLDER'; });
    const body = document.createElement('div');
    body.className = 'body';
    const title = document.createElement('p');
    title.className = 'title';
    title.textContent = String(t.number).padStart(3, '0') + ' · ' + t.name;
    const meta = document.createElement('p');
    meta.className = 'meta';
    meta.textContent = t.category_name + ' · ' + (t.style || '未标注风格') +
      (t.pages ? ' · ' + t.pages + ' 页' : ' · 内置模板');
    const badges = document.createElement('div');
    badges.className = 'badges';
    const mk = (text, warn) => {
      const b = document.createElement('span');
      b.className = 'badge' + (warn ? ' warn' : '');
      b.textContent = text;
      return b;
    };
    badges.append(mk(t.namespace === 'builtin' ? '内置 15 套' : '严格保真'));
    if (t.cover_status === 'placeholder') badges.append(mk('暂无封面', true));
    if (t.namespace !== 'builtin') badges.append(mk('来源待核验', true));
    for (const f of (t.flags || [])) badges.append(mk(f, true));
    const btn = document.createElement('button');
    btn.className = 'choose';
    btn.textContent = '查看外观并选用';
    btn.addEventListener('click', () => showDetail(t));
    body.append(title, meta, badges, btn);
    card.append(img, body);
    grid.append(card);
  }
  $('status').textContent = '共 ' + matches.length + ' 套模板' +
    (cat !== 'all' ? '（分类已锁定）' : '') +
    (style ? ' · 风格：' + style : '');
  $('note').textContent = '已按封面指纹合并 ' + (DATA.counts.duplicates_removed || 0) +
    ' 套重复模板，仅保留完整可用的一个版本。提示：第 2、3、4 页是版式页，选中后会重点保护；' +
    '逐页预览由本机渲染脚本生成，尚未生成的页会显示占位图，不影响选用。';
}

function showDetail(t) {
  current = t;
  $('dlg-title').textContent = String(t.number).padStart(3, '0') + ' · ' + t.name;
  const cover = $('dlg-cover');
  // 详情大图优先用本机渲染的第 1 页（满幅清晰）；失败退回封面，最后才是占位图
  cover.onerror = () => {
    if (t.pages_dir && cover.src.indexOf('/01.webp') !== -1) {
      cover.src = t.cover;
    } else {
      cover.onerror = null;
      cover.src = 'PLACEHOLDER';
    }
  };
  cover.src = t.pages_dir ? t.pages_dir + '/01.webp' : t.cover;
  const film = $('dlg-film');
  film.replaceChildren();
  const total = t.pages_dir ? PAGES_PER_DECK : 0;
  for (let i = 1; i <= total; i++) {
    const fig = document.createElement('figure');
    if (i >= 2 && i <= 4) fig.className = 'key';
    const img = document.createElement('img');
    img.src = t.pages_dir + '/' + String(i).padStart(2, '0') + '.webp';
    img.alt = '第 ' + i + ' 页';
    img.loading = 'lazy';
    img.addEventListener('error', () => { img.onerror = null; img.src = 'PLACEHOLDER'; });
    const cap = document.createElement('figcaption');
    cap.textContent = '第 ' + i + ' 页' + (i >= 2 && i <= 4 ? ' · 版式页保护' : '');
    fig.append(img, cap);
    film.append(fig);
  }
  $('dlg-facts').textContent =
    'ID ' + t.id + ' · ' + t.category_name + ' · ' + (t.pages ? t.pages + ' 页' : '内置模板') +
    (t.sha8 ? ' · 指纹 ' + t.sha8 : '') + '\\n' +
    '版权：' + t.rights + '。仅本机浏览与选用，不得公开再分发。' +
    (t.flags && t.flags.length ? '\\n注意：' + t.flags.join('、') : '');
  $('dlg-prompt').value = t.namespace === 'builtin'
    ? '使用 xmu-ppt 的「' + t.name + '」模板（ID ' + t.id + '）制作关于【填写主题】的 PPT。模板已由我选定。'
    : '使用 xmu-ppt 的严格保真路线 strict-native，模板 ID ' + t.id + '（' + t.name +
      '，共 ' + t.pages + ' 页）。制作关于【填写主题】的 PPT。请 1:1 完整保留所选模板全部页面，' +
      '尤其第 2、3、4 页版式页的图片、图形、装饰、占位区与版式，只把新文案套入对应文本区域，' +
      '不删页、不重排、不替换任何素材。模板已由我选定。';
  $('dlg-hint').textContent = '';
  $('detail').showModal();
}

$('dlg-copy').addEventListener('click', async () => {
  const text = $('dlg-prompt');
  try {
    await navigator.clipboard.writeText(text.value);
    $('dlg-hint').textContent = '已复制，粘贴到 AI 聊天并填写主题即可。';
  } catch (e) {
    text.focus(); text.select();
    $('dlg-hint').textContent = '浏览器限制了剪贴板，请按 Ctrl+C 手动复制（已选中）。';
  }
});
$('dlg-close').addEventListener('click', () => $('detail').close());
$('search').addEventListener('input', render);
$('style').addEventListener('change', render);
window.addEventListener('hashchange', render);
buildNav();
render();
// 支持 #deck=<ID> 直接打开某套模板详情，便于收藏或分享本地链接
const deckMatch = location.hash.match(/deck=([^&]+)/);
if (deckMatch) {
  const target = DATA.templates.find(x => x.id === decodeURIComponent(deckMatch[1]));
  if (target) showDetail(target);
}
</script>
</body>
</html>
"""


def write_index_html() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(
        HTML.replace("PLACEHOLDER", PLACEHOLDER), encoding="utf-8"
    )


def write_category_mirrors(categories: list[dict]) -> None:
    CATEGORY_DIR.mkdir(parents=True, exist_ok=True)
    for cat in categories:
        target = f"index.html#cat={cat['id']}"
        (CATEGORY_DIR / f"{cat['id']}.html").write_text(
            "<!doctype html><html lang=\"zh-CN\"><meta charset=\"utf-8\">"
            f"<title>{cat['name']} · 本地模板库</title>"
            f"<p>正在打开「{cat['name']}」… <a href=\"../{target}\">若未跳转请点此</a></p>"
            f"<script>location.replace('../{target}');</script></html>\n",
            encoding="utf-8",
        )


def main() -> int:
    root_cfg = load_json(ROOT_LOCAL)
    root = Path(root_cfg["root"])
    if not root.is_dir():
        raise SystemExit(f"外部模板根目录不存在：{root}")
    COVERS.mkdir(parents=True, exist_ok=True)
    PAGES.mkdir(parents=True, exist_ok=True)
    make_placeholder()
    cards, data = collect_cards()
    write_catalog_js(data)
    write_index_html()
    write_category_mirrors(load_json(CATEGORIES_FILE)["categories"])
    counts = data["counts"]
    print(f"本地画廊已生成：{OUT}")
    print(f"共 {counts['total']} 套（内置 {counts['builtin']} + 外部 {counts['external']}）")
    print(f"封面可用 {counts['covers_ready']}，暂无封面 {counts['covers_missing']}（由渲染脚本补齐）")
    print(f"分类分布：{counts['by_category']}")
    print(f"打开方式：双击 {OUT / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
