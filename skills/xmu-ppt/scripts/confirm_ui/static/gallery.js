'use strict';
const $ = id => document.getElementById(id);
let templates = [];
let recommendation = null;
let current = null;
let saved = false;
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
  const mode = $('route').value === 'native' ? '保持原版式，使用原生填充' : '沿用模板风格，使用 SVG 灵活排版';
  $('prompt').value = `使用 xmu-ppt 的「${current.name}」模板（ID ${current.id}），${mode}。制作关于【填写汇报主题】的 PPT，约【填写页数】页。模板已由我选定，请开始整理内容。`;
}

function showDetail(deck) {
  current = deck;
  $('detail-title').textContent = deck.name;
  $('description').textContent = deck.style;
  $('previews').replaceChildren();
  for (const [name, file] of [['封面', deck.preview], ['正文', `previews/${String(deck.number).padStart(2, '0')}-content.svg`], ['章节页', `previews/${String(deck.number).padStart(2, '0')}-chapter.svg`]]) {
    const figure = document.createElement('figure');
    const image = document.createElement('img');
    image.src = file;
    image.alt = `${deck.name}${name}预览`;
    const caption = document.createElement('figcaption');
    caption.textContent = name;
    figure.append(image, caption);
    $('previews').append(figure);
  }
  $('route').value = 'svg';
  $('route').querySelector('[value="native"]').disabled = !deck.routes.includes('native');
  $('route-hint').textContent = deck.routes.includes('native') ? '灵活排版会重新组织正文。原生填充受原模板文字槽位容量约束。' : '此模板缺少原生源 PPTX，目前仅支持灵活排版。';
  $('selection-status').textContent = saved ? '此项目已确认模板。更换模板请回到聊天中新建项目。' : '';
  $('choose').disabled = saved;
  $('choose').textContent = published ? '复制使用指令' : '确认使用此模板';
  $('prompt-label').hidden = !published;
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
    $('choose').disabled = saved;
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
  } catch (error) {
    $('status').textContent = error.message;
  }
}
start();
