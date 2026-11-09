'use strict';
const $ = id => document.getElementById(id);
let templates = [];
let recommendation = null;
let current = null;
let saved = false;
let nativeReady = false;
let canChoose = false;
const published = document.documentElement.dataset.mode === 'published';

async function readJSON(url) {
  const response = await fetch(url, {cache: 'no-store'});
  if (!response.ok) throw new Error('加载失败，请刷新页面重试。');
  return response.json();
}

function render() {
  const scene = $('scene').value;
  const query = $('search').value.trim().toLowerCase();
  const matches = templates.filter(deck => (!scene || deck.tags.includes(scene)) &&
    `${deck.name} ${deck.style} ${deck.tags.join(' ')}`.toLowerCase().includes(query));
  const recommended = recommendation?.recommended || [];
  const groupOf = d => d.namespace === 'external' ? 1 : 0;
  matches.sort((a, b) => (groupOf(a) - groupOf(b)) ||
    (Number(recommended.includes(b.id)) - Number(recommended.includes(a.id))));
  const grouped = matches.some(d => d.namespace === 'external');
  const counts = {
    builtin: templates.filter(d => d.namespace !== 'external').length,
    external: templates.filter(d => d.namespace === 'external').length,
  };
  $('cards').replaceChildren();
  let shownGroup = null;
  for (const deck of matches) {
    const group = groupOf(deck);
    if (grouped && group !== shownGroup) {
      const heading = document.createElement('h2');
      heading.className = 'group-title';
      heading.textContent = group
        ? `外部模板（${counts.external} 套 · 本机自备 · 不公开分发）`
        : `内置模板（${counts.builtin} 套 · 随仓库分发）`;
      $('cards').append(heading);
      shownGroup = group;
    }
    const card = document.createElement('article');
    card.className = 'card';
    const image = document.createElement('img');
    image.src = deck.preview;
    image.alt = `${deck.name}封面预览`;
    image.loading = 'lazy';
    const body = document.createElement('div');
    body.className = 'card-body';
    const title = document.createElement('h2');
    title.textContent = `${deck.serial || String(deck.number).padStart(3, '0')} ${deck.name}`;
    const style = document.createElement('p');
    style.textContent = deck.style;
    const tags = document.createElement('p');
    tags.textContent = deck.tags.join(' · ');
    const badge = document.createElement('p');
    badge.className = 'badge';
    badge.textContent = (deck.namespace === 'external'
      ? (published ? '外部 · ' : '本机 · ') : '') +
      (recommended.includes(deck.id) ? '场景推荐 · ' : '') +
      (deck.routes.includes('native') ? '支持灵活排版 / 保持原版式' : '仅支持灵活排版');
    const reason = recommendation?.recommendation_reasons?.[deck.id];
    if (recommended.includes(deck.id) && reason) badge.textContent += ` · ${reason}`;
    const button = document.createElement('button');
    button.textContent = '查看详情并选择';
    button.addEventListener('click', () => showDetail(deck));
    body.append(title, style, tags, badge, button);
    card.append(image, body);
    $('cards').append(card);
  }
  $('status').textContent = matches.length ? `共 ${matches.length} 套模板` : '没有匹配的模板，请调整筛选条件。';
}

function updatePrompt() {
  const mode = $('route').value === 'native' ? '保持原模板每一页的版式，用原生填充只替换文字' : '沿用模板风格，使用 SVG 灵活排版';
  const ref = current.namespace === 'external'
    ? `序号 ${current.serial}（模板 ID ${current.id}）`
    : `ID ${current.id}`;
  $('prompt').value = `使用 xmu-ppt 的「${current.name}」模板（${ref}），${mode}。制作关于【填写汇报主题】的 PPT，约【填写页数】页。模板已由我选定，请开始整理内容。`;
}

const ROLE_LABELS = {
  cover_candidate: '封面', toc_candidate: '目录', chapter_candidate: '章节页',
  section_candidate: '章节页', content_candidate: '内容页',
  ending_candidate: '结尾页', thanks_candidate: '结尾页',
};
const LAYOUT_LABELS = {
  cover: '封面',
  toc: '目录',
  'numbered-cards': '目录 · 编号卡片',
  'chapter-divider': '章节分隔页',
  'hero-statement': '主标题 + 正文',
  'two-block': '双栏对照',
  'multi-block': '多块内容',
  list: '列表',
  content: '内容页',
  ending: '结尾页',
};

function renderLegacyPreviews(deck) {
  const grid = $('previews');
  const number = String(deck.number).padStart(2, '0');
  const items = deck.namespace === 'external'
    ? [['封面', deck.preview]]
    : [
        ['封面', deck.preview],
        ['正文（SVG 原型）', `previews/${number}-content.svg`],
        ['章节页（SVG 原型）', `previews/${number}-chapter.svg`],
      ];
  grid.hidden = false;
  grid.classList.toggle('single', items.length === 1);
  grid.replaceChildren();
  for (const [name, file] of items) {
    const figure = document.createElement('figure');
    const image = document.createElement('img');
    image.src = file;
    image.alt = `${deck.name}${name}预览`;
    const caption = document.createElement('figcaption');
    caption.textContent = name;
    figure.append(image, caption);
    grid.append(figure);
  }
}

async function loadFullPages(deck) {
  const status = $('page-status');
  const grid = $('pages');
  const warning = $('coverage-warning');
  grid.replaceChildren();
  grid.hidden = true;
  warning.hidden = true;
  if (published) {
    status.textContent = deck.namespace === 'external'
      ? `外部模板：公开页不提供外部模板预览；请在本机自备原件后查看。`
      : '静态预览：此处仅显示 3 页原型；逐页预览请在本机模板选择页中查看。';
    renderLegacyPreviews(deck);
    return {complete: false, static: true};
  }
  try {
    const data = await readJSON(`/api/deck-pages/${deck.number}`);
    if (!data.available) {
      status.textContent = '此模板尚未建立原生页库。';
      warning.textContent = '该模板没有 source.pptx 与逐页布局索引，无法按原版式制作。请先完成模板入库。';
      warning.hidden = false;
      renderLegacyPreviews(deck);
      return {complete: false};
    }
    status.textContent = `原模板共 ${data.source_page_count} 页，已生成 ${data.preview_count} 页真实预览` +
      (data.complete ? '（全部可查看）' : '（预览不齐）') + '。点击任意一页可放大。';
    if (!data.preview_count) {
      renderLegacyPreviews(deck);
    } else {
      grid.hidden = false;
      $('previews').hidden = true;
      for (const [index, page] of data.pages.entries()) {
        const figure = document.createElement('figure');
        const image = document.createElement('img');
        // 第一页就是封面。统一使用画廊卡片同一张封面图，避免详情页与卡片
        // 因为取图路径不同（老封面 vs 逐页渲染）而出现两个版本。
        image.src = index === 0 ? deck.preview : (page.preview || deck.preview);
        image.alt = `${deck.name} 第 ${page.slide} 页`;
        image.loading = 'lazy';
        image.title = page.summary || '';
        const media = page.preview ? document.createElement('a') : document.createElement('div');
        if (page.preview) {
          media.href = page.preview;
          media.target = '_blank';
          media.rel = 'noopener';
        }
        media.append(image);
        const caption = document.createElement('figcaption');
        const heading = document.createElement('strong');
        heading.textContent = `第 ${page.slide} 页 · ${LAYOUT_LABELS[page.layout] || ROLE_LABELS[page.role] || page.role || '内容页'}`;
        const meta = document.createElement('span');
        meta.className = 'meta';
        meta.textContent = `${page.slot_count} 个文字槽` +
          (page.tables ? ` · ${page.tables} 个表格` : '') +
          (page.charts ? ` · ${page.charts} 个图表` : '') +
          (page.preview ? '' : ' · 缺预览');
        caption.append(heading, meta);
        figure.append(media, caption);
        grid.append(figure);
      }
    }
    if (!data.complete) {
      warning.textContent = `此模板仅生成了 ${data.preview_count}/${data.source_page_count} 页预览，尚未完成全页入库，不能保证每一页都按原版式制作。`;
      warning.hidden = false;
    }
    return data;
  } catch (error) {
    status.textContent = `全页信息读取失败：${error.message}`;
    renderLegacyPreviews(deck);
    return {complete: false};
  }
}

async function showDetail(deck) {
  current = deck;
  $('detail-title').textContent = `${deck.serial || String(deck.number).padStart(3, '0')} ${deck.name}`;
  $('description').textContent = deck.style;
  $('previews').replaceChildren();
  $('selection-status').textContent = saved ? '此项目已确认模板。更换模板请回到聊天中新建项目。' : '';
  $('choose').textContent = published ? '复制使用指令' : '确认使用此模板';
  $('prompt-label').hidden = !published;
  const pages = await loadFullPages(deck);
  // 公开页只有 3 页原型，无法判断全页是否入库，按 routes 声明即可；
  // 本机页必须以真实全页预览完整为条件，避免误报「可原生填充」。
  nativeReady = deck.routes.includes('native') && (published || pages.complete);
  const svgReady = deck.routes.includes('svg');
  canChoose = published || nativeReady || svgReady;
  $('route').value = nativeReady ? 'native' : 'svg';
  $('route').querySelector('[value="svg"]').disabled = saved || !svgReady || (nativeReady && !published);
  $('route').querySelector('[value="native"]').disabled = saved || !nativeReady;
  $('route-hint').textContent = deck.namespace === 'external'
    ? '外部模板只支持保持原版式：使用本机自备原件，原生填充只替换文字，不改版式。'
    : nativeReady
      ? '已锁定原生填充：只替换原模板的文字、表格与图表数据，不改任何版式。'
      : svgReady
        ? '此模板缺少完整的原生页库，只能选择 SVG 灵活排版（会重新设计布局）。'
        : '此模板既不能原生填充，也没有 SVG 版式，请改选其它模板。';
  if (!nativeReady && deck.routes.includes('svg')) {
    $('coverage-warning').textContent = '该模板没有 source.pptx 全页页库，无法保持原版式；选择 SVG 排版会重新设计布局，视觉风格仍沿用模板。';
    $('coverage-warning').hidden = false;
  } else if (!canChoose) {
    $('coverage-warning').textContent = '该模板不能用于制作：既缺少原生源 PPTX，也缺少 SVG 版式。请改选其它模板。';
    $('coverage-warning').hidden = false;
  }
  $('choose').disabled = saved || !canChoose;
  updatePrompt();
  $('detail').showModal();
}

$('choose').addEventListener('click', async () => {
  $('choose').disabled = true;
  try {
    if (published) {
      updatePrompt();
      try {
        await navigator.clipboard.writeText($('prompt').value);
        $('selection-status').textContent = '已复制，请粘贴到 AI 聊天中并填写汇报主题和页数。';
      } catch {
        $('prompt').focus();
        $('prompt').select();
        $('selection-status').textContent = '请手动复制上方指令，粘贴到 AI 聊天中。';
      }
    } else {
      const response = await fetch('/api/template-confirm', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({request_id: recommendation.request_id, template_id: current.id, route: $('route').value})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || '保存失败，请重试。');
      saved = true;
      $('selection-status').textContent = `已选定「${current.name}」，请回到聊天继续制作。`;
    }
  } catch (error) {
    $('selection-status').textContent = error.message;
  } finally {
    $('choose').disabled = saved || !canChoose;
  }
});
$('close').addEventListener('click', () => $('detail').close());
$('scene').addEventListener('change', render);
$('search').addEventListener('input', render);
$('route').addEventListener('change', updatePrompt);

async function start() {
  try {
    if (published) {
      templates = await readJSON('catalog.json');
      $('intro').textContent = `浏览 ${templates.length} 套模板，选定后复制指令发给 AI。`;
    } else {
      [templates, recommendation] = await Promise.all([readJSON('/api/templates'), readJSON('/api/recommendations')]);
      saved = recommendation._already_confirmed;
    }
    render();
    const requested = Number(new URLSearchParams(location.search).get('deck'));
    if (requested) {
      const deck = templates.find(item => Number(item.number) === requested);
      if (deck) showDetail(deck);
    }
  } catch (error) {
    $('status').textContent = error.message;
  }
}
start();
