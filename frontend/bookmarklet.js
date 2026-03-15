/**
 * TubeScribe Sidebar — loaded dynamically by the bookmarklet loader
 * Served from /bookmarklet.js — update here, all users get it instantly
 */
(function () {
  const API = 'https://tube-scribe.up.railway.app';
  const SIDEBAR_ID = 'tubescribe-sidebar';

  // Remove if already open (toggle)
  if (document.getElementById(SIDEBAR_ID)) {
    document.getElementById(SIDEBAR_ID).remove();
    document.body.style.marginRight = '';
    return;
  }

  if (!location.href.includes('youtube.com/watch') && !location.href.includes('youtube.com/playlist')) {
    showToast('❌ Open a YouTube video or playlist first.');
    return;
  }

  // ── Build sidebar ─────────────────────────────────────────────────────────
  const sidebar = document.createElement('div');
  sidebar.id = SIDEBAR_ID;
  sidebar.style.cssText = [
    'position:fixed', 'top:0', 'right:0', 'width:420px', 'height:100vh',
    'background:#07090f', 'color:#e6edf5', 'z-index:9999999',
    'font-family:-apple-system,BlinkMacSystemFont,sans-serif', 'font-size:14px',
    'box-shadow:-4px 0 24px rgba(0,0,0,0.6)',
    'display:flex', 'flex-direction:column',
    'border-left:1px solid #1e2d45',
    'transition:transform 0.2s ease',
  ].join(';');

  sidebar.innerHTML = `
    <div style="padding:16px 20px;border-bottom:1px solid #1e2d45;display:flex;align-items:center;gap:12px;flex-shrink:0">
      <span style="font-weight:800;font-size:16px;background:linear-gradient(135deg,#6c63ff,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent">TubeScribe</span>
      <span id="ts-status" style="color:#7d8fa8;font-size:12px;flex:1">Fetching transcript…</span>
      <button id="ts-pdf-btn" style="display:none;background:#6c63ff;color:#fff;border:none;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">⬇ PDF</button>
      <button id="ts-close" style="background:none;border:none;color:#7d8fa8;font-size:18px;cursor:pointer;padding:0 4px;line-height:1">✕</button>
    </div>
    <div id="ts-log" style="padding:10px 16px;font-size:11px;color:#7d8fa8;border-bottom:1px solid #1e2d45;flex-shrink:0;min-height:32px"></div>
    <div id="ts-body" style="flex:1;overflow-y:auto;padding:20px;line-height:1.7"></div>
  `;

  document.body.appendChild(sidebar);
  document.body.style.marginRight = '420px';

  // Close button
  sidebar.querySelector('#ts-close').onclick = () => {
    sidebar.remove();
    document.body.style.marginRight = '';
  };

  const statusEl = sidebar.querySelector('#ts-status');
  const logEl    = sidebar.querySelector('#ts-log');
  const bodyEl   = sidebar.querySelector('#ts-body');
  const pdfBtn   = sidebar.querySelector('#ts-pdf-btn');

  function log(msg) {
    const line = document.createElement('div');
    line.textContent = msg;
    logEl.appendChild(line);
    logEl.scrollTop = 99999;
  }

  function setStatus(msg) { statusEl.textContent = msg; }

  // ── Inject marked.js for rendering ───────────────────────────────────────
  function loadMarked() {
    return new Promise((resolve) => {
      if (window.marked) { resolve(); return; }
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
      s.onload = resolve;
      document.head.appendChild(s);
    });
  }

  // ── Get transcript ────────────────────────────────────────────────────────
  async function getTranscript() {
    const tracks = window?.ytInitialPlayerResponse?.captions
      ?.playerCaptionsTracklistRenderer?.captionTracks;

    if (tracks?.length) {
      const track =
        tracks.find(t => t.languageCode === 'en' && !t.kind) ||
        tracks.find(t => t.languageCode === 'en') ||
        tracks.find(t => t.languageCode?.startsWith('en')) ||
        tracks[0];

      if (track?.baseUrl) {
        const url = track.baseUrl.includes('fmt=')
          ? track.baseUrl.replace(/fmt=[^&]+/, 'fmt=json3')
          : track.baseUrl + '&fmt=json3';
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          const seen = new Set(), segs = [];
          for (const ev of (data.events || [])) {
            if (!ev.segs) continue;
            const t = ev.segs.map(s => s.utf8 || '').join('').replace(/\n/g,' ').replace(/\s+/g,' ').trim();
            if (!t || t === '[Music]' || seen.has(t)) continue;
            seen.add(t); segs.push(t);
          }
          if (segs.length > 5) return segs.join(' ');
        }
      }
    }

    // Fallback: click Show transcript
    setStatus('Opening transcript panel…');
    const sleep = ms => new Promise(r => setTimeout(r, ms));

    const expandBtn = document.querySelector('tp-yt-paper-button#expand, #expand');
    if (expandBtn) { expandBtn.click(); await sleep(500); }

    let transcriptBtn =
      [...document.querySelectorAll('button, tp-yt-paper-button')]
        .find(el => el.textContent.trim().toLowerCase() === 'show transcript') ||
      [...document.querySelectorAll('ytd-text-inline-expander button, #description button')]
        .find(el => el.textContent.toLowerCase().includes('transcript'));

    if (!transcriptBtn) {
      const moreBtn = document.querySelector('button[aria-label="More actions"]');
      if (moreBtn) {
        moreBtn.click(); await sleep(600);
        const item = [...document.querySelectorAll('tp-yt-paper-item, ytd-menu-service-item-renderer')]
          .find(el => el.textContent.toLowerCase().includes('transcript'));
        if (item) { item.click(); await sleep(1800); transcriptBtn = null; }
        else document.body.click();
      }
    } else {
      transcriptBtn.click();
      await sleep(1800);
    }

    const selectors = [
      'ytd-transcript-segment-renderer .segment-text',
      'ytd-transcript-segment-view-model .segment-text',
    ];
    let segs = [];
    for (const sel of selectors) {
      const els = document.querySelectorAll(sel);
      if (els.length > 5) { segs = [...els].map(e => e.textContent.trim()).filter(Boolean); break; }
    }
    if (!segs.length) {
      const panel = document.querySelector('[target-id="engagement-panel-transcript"] ytd-transcript-renderer');
      if (panel) segs = panel.innerText.split('\n').filter(l => l.trim() && !/^\d+:\d+$/.test(l.trim()));
    }
    if (segs.length < 5) throw new Error('No transcript found. Try scrolling down to expand the description first.');
    return segs.join(' ');
  }

  // ── Stream notes from server ──────────────────────────────────────────────
  async function streamNotes(title, videoId, transcript) {
    await loadMarked();
    const wordCount = transcript.split(/\s+/).filter(Boolean).length;
    log(`📋 ${wordCount.toLocaleString()} words received`);
    setStatus('Generating notes…');

    const res = await fetch(`${API}/stream-notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        url: `https://www.youtube.com/watch?v=${videoId}`,
        video_id: videoId,
        prefetched_title: title,
        prefetched_transcript: transcript,
      }),
    });

    if (!res.ok) throw new Error(`Server ${res.status}`);

    let fullMd = '';
    const reader = res.body.getReader();
    const dec = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      for (const line of dec.decode(value).split('\n')) {
        if (!line.startsWith('data: ')) continue;
        let d; try { d = JSON.parse(line.slice(6)); } catch { continue; }

        if (d.total_chunks) log(`📝 ${d.total_chunks} chunk${d.total_chunks > 1 ? 's' : ''}`);
        if (d.chunk) {
          fullMd += d.chunk;
          bodyEl.innerHTML = window.marked.parse(fullMd);
          bodyEl.scrollTop = 99999;
          if (d.chunk_index && d.total_chunks) {
            setStatus(`Chunk ${d.chunk_index}/${d.total_chunks}…`);
          }
        }
        if (d.done) {
          setStatus('✅ Done');
          log(`⚡ Complete`);
          pdfBtn.style.display = 'block';
          pdfBtn.onclick = () => downloadPDF(title, fullMd);
        }
        if (d.error) throw new Error(d.error);
      }
    }
    return fullMd;
  }

  // ── PDF download ──────────────────────────────────────────────────────────
  async function downloadPDF(title, markdown) {
    pdfBtn.textContent = '⏳ Building…';
    pdfBtn.disabled = true;
    try {
      const res = await fetch(`${API}/markdown-to-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ title, markdown }),
      });
      if (!res.ok) throw new Error(`PDF failed: ${res.status}`);
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = title.replace(/[^a-z0-9]/gi, '_').slice(0, 60) + '.pdf';
      a.click();
      pdfBtn.textContent = '✅ Downloaded';
    } catch (e) {
      pdfBtn.textContent = '❌ Failed';
      log('PDF error: ' + e.message);
    } finally {
      pdfBtn.disabled = false;
    }
  }

  // ── Toast for errors ──────────────────────────────────────────────────────
  function showToast(msg) {
    const t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999999;background:#1a1a2e;color:#fff;padding:12px 18px;border-radius:10px;font-family:sans-serif;font-size:14px;border-left:4px solid #ff4444;box-shadow:0 4px 20px rgba(0,0,0,0.5)';
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 6000);
  }

  // ── Run ───────────────────────────────────────────────────────────────────
  (async () => {
    try {
      const videoId = new URLSearchParams(location.search).get('v') || '';
      const title = document.title.replace(' - YouTube', '').trim();

      const transcript = await getTranscript();
      await streamNotes(title, videoId, transcript);
    } catch (err) {
      setStatus('❌ ' + err.message);
      log('Error: ' + err.message);
    }
  })();
})();