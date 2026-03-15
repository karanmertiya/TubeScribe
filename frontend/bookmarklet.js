(function () {
  var API = 'https://tube-scribe.up.railway.app';
  var ID = 'tubescribe-root';

  if (document.getElementById(ID)) {
    document.getElementById(ID).remove();
    document.body.style.marginRight = '';
    return;
  }

  if (!location.href.includes('youtube.com/watch')) {
    alert('TubeScribe: Open a YouTube video first.');
    return;
  }

  var videoId = new URLSearchParams(location.search).get('v') || '';
  var title = document.title.replace(' - YouTube', '').trim();

  // All DOM via createElement — no innerHTML (blocked by YouTube Trusted Types CSP)
  function mk(tag, css, props) {
    var e = document.createElement(tag);
    if (css) e.style.cssText = css;
    if (props) { for (var k in props) e[k] = props[k]; }
    return e;
  }

  // Sidebar
  var root = mk('div',
    'position:fixed;top:0;right:0;width:400px;height:100vh;z-index:9999999;' +
    'background:#07090f;color:#e6edf5;font-family:-apple-system,sans-serif;font-size:14px;' +
    'box-shadow:-4px 0 32px rgba(0,0,0,0.7);border-left:1px solid #1e2d45;' +
    'display:flex;flex-direction:column;');
  root.id = ID;

  // Header
  var hdr = mk('div','padding:14px 16px;border-bottom:1px solid #1e2d45;display:flex;align-items:center;gap:10px;flex-shrink:0;background:#0d1117;');
  var logo = mk('span','font-weight:800;font-size:15px;');
  logo.style.background = 'linear-gradient(135deg,#6c63ff,#a78bfa)';
  logo.style.webkitBackgroundClip = 'text';
  logo.style.webkitTextFillColor = 'transparent';
  logo.textContent = 'TubeScribe';
  var titleEl = mk('span','flex:1;font-size:11px;color:#7d8fa8;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;');
  titleEl.textContent = title;
  var closeBtn = mk('button','background:none;border:none;color:#7d8fa8;font-size:20px;cursor:pointer;padding:0 2px;line-height:1;flex-shrink:0;');
  closeBtn.textContent = '\u2715';
  closeBtn.onclick = function() { root.remove(); document.body.style.marginRight = ''; };
  hdr.appendChild(logo); hdr.appendChild(titleEl); hdr.appendChild(closeBtn);

  // Phase bar
  var phaseBar = mk('div','padding:10px 16px;background:#0a0e19;border-bottom:1px solid #1e2d45;flex-shrink:0;');
  var phaseLabel = mk('div','font-size:12px;font-weight:600;color:#a78bfa;margin-bottom:6px;');
  phaseLabel.textContent = '\u23f3 Starting\u2026';
  var phaseTrack = mk('div','display:flex;gap:4px;');
  var dots = ['Transcript','Sending','Generating','Done'].map(function(name) {
    var d = mk('div','flex:1;height:3px;border-radius:2px;background:#1e2d45;transition:background 0.3s;');
    phaseTrack.appendChild(d);
    return d;
  });
  function setPhase(idx, msg) {
    phaseLabel.textContent = msg;
    dots.forEach(function(d,i) {
      d.style.background = i < idx ? '#6c63ff' : i === idx ? '#a78bfa' : '#1e2d45';
    });
  }
  phaseBar.appendChild(phaseLabel); phaseBar.appendChild(phaseTrack);

  // Log
  var logEl = mk('div','padding:8px 16px;font-size:11px;color:#5a7090;max-height:80px;overflow-y:auto;border-bottom:1px solid #1e2d45;flex-shrink:0;');
  function log(msg, color) {
    var line = mk('div','margin-bottom:2px;' + (color ? 'color:'+color+';' : ''));
    line.textContent = msg;
    logEl.appendChild(line);
    logEl.scrollTop = 99999;
  }

  // Content
  var content = mk('div','flex:1;overflow-y:auto;padding:16px;line-height:1.7;font-size:13px;');

  // PDF bar
  var pdfBar = mk('div','padding:12px 16px;border-top:1px solid #1e2d45;flex-shrink:0;display:none;background:#0d1117;');
  var pdfBtn = mk('button',
    'width:100%;padding:10px;background:linear-gradient(135deg,#6c63ff,#a78bfa);color:#fff;' +
    'border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;');
  pdfBtn.textContent = '\u2b07 Download PDF';
  pdfBar.appendChild(pdfBtn);

  root.appendChild(hdr); root.appendChild(phaseBar); root.appendChild(logEl);
  root.appendChild(content); root.appendChild(pdfBar);
  document.body.appendChild(root);
  document.body.style.marginRight = '400px';

  // Markdown renderer
  function renderMd(md) {
    content.textContent = '';
    md.split('\n').forEach(function(line) {
      var p = mk('div','margin-bottom:4px;');
      if (line.startsWith('## ')) {
        p.style.cssText = 'font-size:15px;font-weight:700;color:#a78bfa;margin:12px 0 6px;border-bottom:1px solid #1e2d45;padding-bottom:4px;';
        p.textContent = line.slice(3);
      } else if (line.startsWith('### ')) {
        p.style.cssText = 'font-size:13px;font-weight:700;color:#e6edf5;margin:10px 0 4px;';
        p.textContent = line.slice(4);
      } else if (line.startsWith('- ') || line.startsWith('* ')) {
        p.style.cssText = 'padding-left:14px;color:#c9d8eb;';
        p.textContent = '\u2022 ' + line.slice(2);
      } else if (line.startsWith('> ')) {
        p.style.cssText = 'border-left:3px solid #6c63ff;padding-left:10px;color:#7d8fa8;font-style:italic;';
        p.textContent = line.slice(2);
      } else if (line.trim() === '') {
        p.style.height = '6px';
      } else {
        p.style.color = '#c9d8eb';
        p.textContent = line;
      }
      content.appendChild(p);
    });
    content.scrollTop = 99999;
  }

  // Get transcript
  async function getTranscript() {
    setPhase(0, '\u23f3 Phase 1/4 \u2014 Reading transcript\u2026');
    log('Looking for captions\u2026');

    var tracks = window && window.ytInitialPlayerResponse &&
      window.ytInitialPlayerResponse.captions &&
      window.ytInitialPlayerResponse.captions.playerCaptionsTracklistRenderer &&
      window.ytInitialPlayerResponse.captions.playerCaptionsTracklistRenderer.captionTracks;

    if (tracks && tracks.length) {
      log('Found ' + tracks.length + ' caption track(s)');
      var track = tracks.find(function(t) { return t.languageCode === 'en' && !t.kind; }) ||
                  tracks.find(function(t) { return t.languageCode === 'en'; }) ||
                  tracks.find(function(t) { return t.languageCode && t.languageCode.startsWith('en'); }) ||
                  tracks[0];
      log('Using: ' + (track.languageCode||'?') + (track.kind ? ' [auto]' : ' [manual]'));
      var url = track.baseUrl.includes('fmt=')
        ? track.baseUrl.replace(/fmt=[^&]+/, 'fmt=json3')
        : track.baseUrl + '&fmt=json3';
      var res = await fetch(url);
      if (res.ok) {
        var data = await res.json();
        var seen = new Set(), segs = [];
        (data.events || []).forEach(function(ev) {
          if (!ev.segs) return;
          var t = ev.segs.map(function(s){return s.utf8||'';}).join('').replace(/\n/g,' ').replace(/\s+/g,' ').trim();
          if (!t || t === '[Music]' || seen.has(t)) return;
          seen.add(t); segs.push(t);
        });
        if (segs.length > 5) {
          log('\u2713 ' + segs.length + ' segments, ~' + segs.join(' ').split(/\s+/).length + ' words');
          return segs.join(' ');
        }
      }
    }

    // Fallback: click Show transcript
    log('No inline captions \u2014 trying Show Transcript\u2026');
    setPhase(0, '\u23f3 Phase 1/4 \u2014 Opening transcript panel\u2026');
    var sleep = function(ms) { return new Promise(function(r){setTimeout(r,ms);}); };

    var expandBtn = document.querySelector('tp-yt-paper-button#expand') || document.querySelector('#expand');
    if (expandBtn) { expandBtn.click(); await sleep(500); }

    var allBtns = Array.from(document.querySelectorAll('button, tp-yt-paper-button'));
    var transcriptBtn = allBtns.find(function(b) { return b.textContent.trim().toLowerCase() === 'show transcript'; }) ||
      Array.from(document.querySelectorAll('#description button, ytd-text-inline-expander button'))
        .find(function(b) { return b.textContent.toLowerCase().includes('transcript'); });

    if (transcriptBtn) {
      log('Clicking Show Transcript\u2026');
      transcriptBtn.click();
      await sleep(2000);
    } else {
      var moreBtn = document.querySelector('button[aria-label="More actions"]');
      if (moreBtn) {
        moreBtn.click(); await sleep(600);
        var menuItem = Array.from(document.querySelectorAll('tp-yt-paper-item, ytd-menu-service-item-renderer'))
          .find(function(x) { return x.textContent.toLowerCase().includes('transcript'); });
        if (menuItem) { menuItem.click(); await sleep(2000); }
        else { document.body.click(); throw new Error('No transcript button found. Scroll down to expand description first.'); }
      }
    }

    var segSelectors = ['ytd-transcript-segment-renderer .segment-text', 'ytd-transcript-segment-view-model .segment-text'];
    var segs = [];
    for (var i = 0; i < segSelectors.length; i++) {
      var els = document.querySelectorAll(segSelectors[i]);
      if (els.length > 5) { segs = Array.from(els).map(function(e){return e.textContent.trim();}).filter(Boolean); break; }
    }
    if (!segs.length) {
      var panel = document.querySelector('[target-id="engagement-panel-transcript"] ytd-transcript-renderer');
      if (panel) segs = panel.innerText.split('\n').filter(function(l){return l.trim() && !/^\d+:\d+$/.test(l.trim());});
    }
    if (segs.length < 5) throw new Error('Transcript panel empty. Make sure video has captions.');
    log('\u2713 ' + segs.length + ' segments from panel');
    return segs.join(' ');
  }

  // Stream notes
  async function streamNotes(transcript) {
    setPhase(1, '\u23f3 Phase 2/4 \u2014 Sending to server\u2026');
    log('Sending ' + transcript.split(/\s+/).length + ' words to Groq\u2026');
    var res = await fetch(API + '/stream-notes', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      credentials: 'include',
      body: JSON.stringify({
        url: 'https://www.youtube.com/watch?v=' + videoId,
        video_id: videoId,
        prefetched_title: title,
        prefetched_transcript: transcript,
      }),
    });
    if (!res.ok) {
      var err = await res.json().catch(function(){return {error:'Server '+res.status};});
      throw new Error(err.error || 'Server ' + res.status);
    }
    setPhase(2, '\u23f3 Phase 3/4 \u2014 Generating notes\u2026');
    log('Connected \u2014 streaming\u2026');
    var fullMd = '';
    var reader = res.body.getReader();
    var dec = new TextDecoder();
    while (true) {
      var chunk = await reader.read();
      if (chunk.done) break;
      dec.decode(chunk.value).split('\n').forEach(function(line) {
        if (!line.startsWith('data: ')) return;
        var d; try { d = JSON.parse(line.slice(6)); } catch(e) { return; }
        if (d.total_chunks) log('Processing ' + d.total_chunks + ' chunk(s)\u2026');
        if (d.chunk) {
          fullMd += d.chunk;
          renderMd(fullMd);
          if (d.chunk_index && d.total_chunks) setPhase(2, '\u23f3 Phase 3/4 \u2014 Chunk ' + d.chunk_index + '/' + d.total_chunks);
        }
        if (d.done) {
          setPhase(3, '\u2705 Done!');
          log('\u2713 ' + fullMd.split(/\s+/).length + ' word notes ready', '#6c63ff');
          pdfBar.style.display = 'block';
          pdfBtn.onclick = function() { downloadPDF(fullMd); };
        }
        if (d.error) throw new Error(d.error);
      });
    }
  }

  // PDF
  async function downloadPDF(markdown) {
    pdfBtn.textContent = '\u23f3 Building PDF\u2026';
    pdfBtn.disabled = true;
    try {
      var res = await fetch(API + '/markdown-to-pdf', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify({title: title, markdown: markdown}),
      });
      if (!res.ok) throw new Error('PDF failed: ' + res.status);
      var blob = await res.blob();
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = title.replace(/[^a-z0-9]/gi,'_').slice(0,60) + '.pdf';
      a.click();
      pdfBtn.textContent = '\u2705 PDF Downloaded';
    } catch(e) {
      pdfBtn.textContent = '\u274c Failed: ' + e.message;
      pdfBtn.disabled = false;
    }
  }

  // Run
  getTranscript().then(function(transcript) {
    return streamNotes(transcript);
  }).catch(function(err) {
    setPhase(-1, '\u274c Error');
    log('\u274c ' + err.message, '#ff6b6b');
    content.textContent = '';
    var errDiv = mk('div','color:#ff6b6b;padding:16px;background:#1a0a0a;border-radius:8px;border:1px solid #3a1010;line-height:1.6;');
    errDiv.textContent = err.message;
    content.appendChild(errDiv);
  });

})();
