'use strict';
const $ = id => document.getElementById(id);
let templates = [];
let recommendation = null;
let current = null;
let saved = false;
let nativeReady = false;
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
  matches.sort((a, b) => Number(recommended.includes(b.id)) - Number(recommended.includes(a.id)));
  $('cards').replaceChildren();
  for (const deck of matches) {
    const card = document.createElement('article');
    card.className = 'card';
    const image = document.createElement('img');
    image.src = deck.preview;
    image.alt = `${deck.name}封面预览`;
    image.loading = 'lazy';
    const body = document.createElement('div');
    body.className = 'card-body';
    const title = document.createElement('h2');
    title.textContent = `${String(deck.number).padStart(2, '0')} ${deck.name}`;
    const style = document.createElement('p');
    style.textContent = deck.style;
    const tags = document.createElement('p');
    tags.textContent = deck.tags.join(' · ');
    const badge = document.createElement('p');
    badge.className = 'badge';
    badge.textContent = (recommended.includes(deck.id) ? '场景推荐 · ' : '') +
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
  $('prompt').value = `使用 xmu-ppt 的「${current.name}」模板（ID ${current.id}），${mode}。制作关于【填写汇报主题】的 PPT，约【填写页数】页。模板已由我选定，请开始整理内容。`;
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
  grid.hidden = false;
  grid.replaceChildren();
  const number = String(deck.number).padStart(2, '0');
  for (const [name, file] of [
    ['封面', deck.preview],
    ['正文（SVG 原型）', `previews/${number}-content.svg`],
    ['章节页（SVG 原型）', `previews/${number}-chapter.svg`],
  ]) {
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
    status.textContent = '静态预览：此处仅显示 3 页原型；逐页预览请在本机模板选择页中查看。';
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
      for (const page of data.pages) {
        const figure = document.createElement('figure');
        const image = document.createElement('img');
        image.src = page.preview || deck.preview;
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
  $('detail-title').textContent = deck.name;
  $('description').textContent = deck.style;
  $('previews').replaceChildren();
  $('selection-status').textContent = saved ? '此项目已确认模板。更换模板请回到聊天中新建项目。' : '';
  $('choose').textContent = published ? '复制使用指令' : '确认使用此模板';
  $('prompt-label').hidden = !published;
  const pages = await loadFullPages(deck);
  nativeReady = published || (deck.routes?.includes('native') && pages.complete);
  $('route').value = nativeReady ? 'native' : 'svg';
  $('route').querySelector('[value="svg"]').disabled = nativeReady && !published;
  $('route').querySelector('[value="native"]').disabled = !nativeReady;
  $('route-hint').textContent = nativeReady
    ? '已锁定原生填充：只替换原模板的文字、表格与图表数据，不改任何版式。'
    : '此模板尚未完成全页入库，暂不能用于原生填充。';
  if (!nativeReady) {
    $('coverage-warning').textContent = '该模板不能用于原生制作：缺少完整的源 PPTX 页库或全页预览。请改选已完整入库的模板，或先完成入库。';
    $('coverage-warning').hidden = false;
  }
  $('choose').disabled = saved || !nativeReady;
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
    $('choose').disabled = saved || !nativeReady;
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
      $('intro').textContent = '浏览 15 套模板，选定后复制指令发给 AI。';
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
