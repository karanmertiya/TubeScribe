(function () {
  const API = 'https://tube-scribe.up.railway.app';
  const ID = 'tubescribe-root';

  // Toggle off if already open
  if (document.getElementById(ID)) {
    document.getElementById(ID).remove();
    document.body.style.marginRight = '';
    return;
  }

  if (!location.href.includes('youtube.com/watch')) {
    alert('TubeScribe: Open a YouTube video first.');
    return;
  }

  const videoId = new URLSearchParams(location.search).get('v') || '';
  const title   = document.title.replace(' - YouTube', '').trim();

  // ── DOM helpers (no innerHTML — blocked by YouTube Trusted Types CSP) ──────
  function el(tag, styles, attrs) {
    const e = document.createElement(tag);
    if (styles) e.style.cssText = styles;
    if (attrs) Object.entries(attrs).forEach(([k,v]) => { e[k] = v; });
    return e;
  }
  function txt(str) { return document.createTextNode(str); }

  // ── Sidebar shell ──────────────────────────────────────────────────────────
  const root = el('div',
    'position:fixed;top:0;right:0;width:400px;height:100vh;z-index:9999999;' +
    'background:#07090f;color:#e6edf5;font-family:-apple-system,sans-serif;font-size:14px;' +
    'box-shadow:-4px 0 32px rgba(0,0,0,0.7);border-left:1px solid #1e2d45;' +
    'display:flex;flex-direction:column;'
  );
  root.id = ID;

  // Header
  const header = el('div', 'padding:14px 16px;border-bottom:1px solid #1e2d45;display:flex;align-items:center;gap:10px;flex-shrink:0;background:#0d1117;');
  const logoSpan = el('span', 'font-weight:800;font-size:15px;');
  logoSpan.style.background = 'linear-gradient(135deg,#6c63ff,#a78bfa)';
  logoSpan.style.webkitBackgroundClip = 'text';
  logoSpan.style.webkitTextFillColor = 'transparent';
  logoSpan.appendChild(txt('TubeScribe'));

  const titleSpan = el('span', 'flex:1;font-size:11px;color:#7d8fa8;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;');
  titleSpan.appendChild(txt(title));

  const closeBtn = el('button', 'background:none;border:none;color:#7d8fa8;font-size:20px;cursor:pointer;padding:0 2px;line-height:1;flex-shrink:0;', {textContent:'✕'});
  closeBtn.onclick = () => { root.remove(); document.body.style.marginRight = ''; };

  header.append(logoSpan, titleSpan, closeBtn);

  // Phase bar
  const phaseBar = el('div', 'padding:10px 16px;background:#0a0e19;border-bottom:1px solid #1e2d45;flex-shrink:0;');
  const phaseLabel = el('div', 'font-size:12px;font-weight:600;color:#a78bfa;margin-bottom:6px;');
  phaseLabel.appendChild(txt('⏳ Starting…'));

  const phaseTrack = el('div', 'display:flex;gap:4px;');
  const phases = ['Transcript', 'Sending', 'Generating', 'Done'];
  const phaseDots = phases.map((name, i) => {
    const dot = el('div',
      'flex:1;height:3px;border-radius:2px;background:#1e2d45;transition:background 0.3s;',
      {title: name}
    );
    phaseTrack.appendChild(dot);
    return dot;
  });

  function setPhase(idx, msg) {
    phaseLabel.textContent = '';
    phaseLabel.appendChild(txt(msg));
    phaseDots.forEach((d, i) => {
      d.style.background = i < idx ? '#6c63ff' : i === idx ? '#a78bfa' : '#1e2d45';
    });
  }

  phaseBar.append(phaseLabel, phaseTrack);

  // Log area
  const logArea = el('div', 'padding:8px 16px;font-size:11px;color:#5a7090;max-height:80px;overflow-y:auto;border-bottom:1px solid #1e2d45;flex-shrink:0;');

  function log(msg, color) {
    const line = el('div', 'margin-bottom:2px;' + (color ? 'color:'+color+';' : ''));
    line.appendChild(txt(msg));
    logArea.appendChild(line);
    logArea.scrollTop = 99999;
  }

  // Content area
  const contentArea = el('div', 'flex:1;overflow-y:auto;padding:16px;line-height:1.7;font-size:13px;');

  // PDF button (hidden initially)
  const pdfBar = el('div', 'padding:12px 16px;border-top:1px solid #1e2d45;flex-shrink:0;display:none;background:#0d1117;');
  const pdfBtn = el('button',
    'width:100%;padding:10px;background:linear-gradient(135deg,#6c63ff,#a78bfa);color:#fff;' +
    'border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;font-family:-apple-system,sans-serif;',
    {textContent: '⬇ Download PDF'}
  );
  pdfBar.appendChild(pdfBtn);

  root.append(header, phaseBar, logArea, contentArea, pdfBar);
  document.body.appendChild(root);
  document.body.style.marginRight = '400px';

  // ── Simple markdown renderer (no external lib needed) ─────────────────────
  function renderMd(md) {
    // We can't use innerHTML directly. Build a text node and use a pre for now,
    // but wrap in a div with white-space:pre-wrap for basic readability
    contentArea.textContent = '';
    // Render line by line
    md.split('\n').forEach(line => {
      const p = el('div', 'margin-bottom:4px;');
      if (line.startsWith('## ')) {
        p.style.cssText = 'font-size:15px;font-weight:700;color:#a78bfa;margin:12px 0 6px;border-bottom:1px solid #1e2d45;padding-bottom:4px;';
        p.appendChild(txt(line.slice(3)));
      } else if (line.startsWith('### ')) {
        p.style.cssText = 'font-size:13px;font-weight:700;color:#e6edf5;margin:10px 0 4px;';
        p.appendChild(txt(line.slice(4)));
      } else if (line.startsWith('- ') || line.startsWith('* ')) {
        p.style.cssText = 'padding-left:14px;color:#c9d8eb;';
        p.appendChild(txt('• ' + line.slice(2)));
      } else if (line.startsWith('> ')) {
        p.style.cssText = 'border-left:3px solid #6c63ff;padding-left:10px;color:#7d8fa8;font-style:italic;';
        p.appendChild(txt(line.slice(2)));
      } else if (line.startsWith('**') && line.endsWith('**')) {
        p.style.cssText = 'font-weight:700;color:#e6edf5;';
        p.appendChild(txt(line.slice(2, -2)));
      } else if (line.trim() === '') {
        p.style.height = '6px';
      } else {
        p.style.color = '#c9d8eb';
        p.appendChild(txt(line));
      }
      contentArea.appendChild(p);
    });
    contentArea.scrollTop = 99999;
  }

  // ── Get transcript ────────────────────────────────────────────────────────
  async function getTranscript() {
    setPhase(0, '⏳ Phase 1/4 — Reading transcript…');
    log('Looking for captions in page…');

    const tracks = window?.ytInitialPlayerResponse?.captions
      ?.playerCaptionsTracklistRenderer?.captionTracks;

    if (tracks?.length) {
      log('Found ' + tracks.length + ' caption track(s)');
      const track =
        tracks.find(t => t.languageCode === 'en' && !t.kind) ||
        tracks.find(t => t.languageCode === 'en') ||
        tracks.find(t => t.languageCode?.startsWith('en')) ||
        tracks[0];

      log('Using: ' + (track.languageCode || '?') + (track.kind ? ' [auto]' : ' [manual]'));

      const url = track.baseUrl.includes('fmt=')
        ? track.baseUrl.replace(/fmt=[^&]+/, 'fmt=json3')
        : track.baseUrl + '&fmt=json3';

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        const seen = new Set(), segs = [];
        for (const ev of (data.events || [])) {
          if (!ev.segs) continue;
          const t = ev.segs.map(s => s.utf8||'').join('').replace(/\n/g,' ').replace(/\s+/g,' ').trim();
          if (!t || t === '[Music]' || seen.has(t)) continue;
          seen.add(t); segs.push(t);
        }
        if (segs.length > 5) {
          log('✓ ' + segs.length + ' segments, ~' + segs.join(' ').split(/\s+/).length + ' words');
          return segs.join(' ');
        }
      }
    }

    // Fallback: click Show transcript
    log('No inline captions — trying Show Transcript button…');
    setPhase(0, '⏳ Phase 1/4 — Opening transcript panel…');
    const sleep = ms => new Promise(r => setTimeout(r, ms));

    const expandBtn = document.querySelector('tp-yt-paper-button#expand, #expand');
    if (expandBtn) { expandBtn.click(); await sleep(500); }

    let transcriptBtn =
      [...document.querySelectorAll('button, tp-yt-paper-button')]
        .find(el => el.textContent.trim().toLowerCase() === 'show transcript') ||
      [...document.querySelectorAll('#description button, ytd-text-inline-expander button')]
        .find(el => el.textContent.toLowerCase().includes('transcript'));

    if (transcriptBtn) {
      log('Clicking Show Transcript…');
      transcriptBtn.click();
      await sleep(2000);
    } else {
      // Try ... menu
      const moreBtn = document.querySelector('button[aria-label="More actions"]');
      if (moreBtn) {
        moreBtn.click(); await sleep(600);
        const item = [...document.querySelectorAll('tp-yt-paper-item, ytd-menu-service-item-renderer')]
          .find(el => el.textContent.toLowerCase().includes('transcript'));
        if (item) { item.click(); await sleep(2000); }
        else { document.body.click(); throw new Error('No transcript button found. Scroll down to expand the description first, then try again.'); }
      }
    }

    const selectors = ['ytd-transcript-segment-renderer .segment-text', 'ytd-transcript-segment-view-model .segment-text'];
    let segs = [];
    for (const sel of selectors) {
      const els = document.querySelectorAll(sel);
      if (els.length > 5) { segs = [...els].map(e => e.textContent.trim()).filter(Boolean); break; }
    }
    if (!segs.length) {
      const panel = document.querySelector('[target-id="engagement-panel-transcript"] ytd-transcript-renderer');
      if (panel) segs = panel.innerText.split('\n').filter(l => l.trim() && !/^\d+:\d+$/.test(l.trim()));
    }
    if (segs.length < 5) throw new Error('Transcript panel empty. Make sure the video has captions.');
    log('✓ ' + segs.length + ' segments from panel');
    return segs.join(' ');
  }

  // ── Stream notes ──────────────────────────────────────────────────────────
  async function streamNotes(transcript) {
    setPhase(1, '⏳ Phase 2/4 — Sending to server…');
    log('Sending ' + transcript.split(/\s+/).length + ' words to Groq…');

    const res = await fetch(API + '/stream-notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        url: 'https://www.youtube.com/watch?v=' + videoId,
        video_id: videoId,
        prefetched_title: title,
        prefetched_transcript: transcript,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({error: res.status}));
      throw new Error(err.error || 'Server ' + res.status);
    }

    setPhase(2, '⏳ Phase 3/4 — Generating notes…');
    log('Connected — streaming…');

    let fullMd = '';
    const reader = res.body.getReader();
    const dec = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      for (const line of dec.decode(value).split('\n')) {
        if (!line.startsWith('data: ')) continue;
        let d; try { d = JSON.parse(line.slice(6)); } catch { continue; }

        if (d.total_chunks) log('Processing ' + d.total_chunks + ' chunk' + (d.total_chunks > 1 ? 's' : '') + '…');
        if (d.chunk) {
          fullMd += d.chunk;
          renderMd(fullMd);
          if (d.chunk_index && d.total_chunks) {
            setPhase(2, '⏳ Phase 3/4 — Chunk ' + d.chunk_index + '/' + d.total_chunks + '…');
          }
        }
        if (d.done) {
          setPhase(3, '✅ Phase 4/4 — Done!');
          log('✓ Complete — ' + fullMd.split(/\s+/).length + ' word notes', '#6c63ff');
          pdfBar.style.display = 'block';
          pdfBtn.onclick = () => downloadPDF(fullMd);
        }
        if (d.error) throw new Error(d.error);
      }
    }
  }

  // ── PDF download ──────────────────────────────────────────────────────────
  async function downloadPDF(markdown) {
    pdfBtn.textContent = '⏳ Building PDF…';
    pdfBtn.style.opacity = '0.7';
    pdfBtn.disabled = true;
    try {
      const res = await fetch(API + '/markdown-to-pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ title, markdown }),
      });
      if (!res.ok) throw new Error('PDF failed: ' + res.status);
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = title.replace(/[^a-z0-9]/gi, '_').slice(0, 60) + '.pdf';
      a.click();
      pdfBtn.textContent = '✅ PDF Downloaded';
      pdfBtn.style.opacity = '1';
    } catch(e) {
      pdfBtn.textContent = '❌ Failed — ' + e.message;
      pdfBtn.style.opacity = '1';
      pdfBtn.disabled = false;
    }
  }

  // ── Run ───────────────────────────────────────────────────────────────────
  (async () => {
    try {
      const transcript = await getTranscript();
      await streamNotes(transcript);
    } catch(err) {
      setPhase(-1, '❌ Error');
      log('❌ ' + err.message, '#ff6b6b');
      // Show error in content area too
      contentArea.textContent = '';
      const errDiv = el('div', 'color:#ff6b6b;padding:16px;background:#1a0a0a;border-radius:8px;border:1px solid #3a1010;line-height:1.6;');
      errDiv.appendChild(txt(err.message));
      contentArea.appendChild(errDiv);
    }
  })();
})();