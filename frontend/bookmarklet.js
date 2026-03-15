(function () {
  var API = 'https://tube-scribe.up.railway.app';
  var ID = 'tubescribe-root';

  if (document.getElementById(ID)) {
    document.getElementById(ID).remove();
    document.body.style.marginRight = '';
    return;
  }

  var isPlaylist = location.href.includes('youtube.com/playlist');
  var isWatch    = location.href.includes('youtube.com/watch');

  if (!isWatch && !isPlaylist) {
    alert('TubeScribe: Open a YouTube video or playlist first.');
    return;
  }

  // Playlist mode — separate flow
  if (isPlaylist) {
    runPlaylist();
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
        var text = await res.text();
        var data;
        try {
          data = JSON.parse(text);
        } catch(e) {
          // JSON3 truncated — fall back to XML format
          log('JSON3 truncated, trying XML\u2026');
          var xmlUrl = track.baseUrl.includes('fmt=')
            ? track.baseUrl.replace(/fmt=[^&]+/, '')
            : track.baseUrl;
          var xmlRes = await fetch(xmlUrl);
          if (!xmlRes.ok) throw new Error('Caption fetch failed: ' + xmlRes.status);
          var xml = await xmlRes.text();
          var segs = [];
          var seen = new Set();
          var matches = xml.match(/<text[^>]*>([^<]+)<\/text>/g) || [];
          matches.forEach(function(m) {
            var t = m.replace(/<[^>]+>/g,'').replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&#39;/g,"'").replace(/&quot;/g,'"').replace(/\n/g,' ').trim();
            if (t && !seen.has(t)) { seen.add(t); segs.push(t); }
          });
          if (segs.length > 5) {
            log('\u2713 ' + segs.length + ' segments from XML');
            return segs.join(' ');
          }
          throw new Error('Both JSON3 and XML caption formats failed');
        }
        var seen = new Set(), segs = [];
        if (data && data.events) {
        (data.events || []).forEach(function(ev) {
          if (!ev.segs) return;
          var t = ev.segs.map(function(s){return s.utf8||'';}).join('').replace(/\n/g,' ').replace(/\s+/g,' ').trim();
          if (!t || t === '[Music]' || seen.has(t)) return;
          seen.add(t); segs.push(t);
        });
        }
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
      var lines = dec.decode(chunk.value).split('\n');
      for (var li = 0; li < lines.length; li++) {
        var line = lines[li];
        if (!line.startsWith('data: ')) continue;
        var d; try { d = JSON.parse(line.slice(6)); } catch(e) { continue; }
        if (!d) continue;
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
      }
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

  // Run (single video)
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

  // ── Playlist mode ─────────────────────────────────────────────────────────
  async function runPlaylist() {
    // Extract video list from ytInitialData (already in memory on playlist page)
    var data = window.ytInitialData;
    if (!data) { alert('TubeScribe: Could not read playlist data. Try refreshing.'); return; }

    var videos = [];
    try {
      var tabs = data.contents.twoColumnBrowseResultsRenderer.tabs;
      var tab  = tabs.find(function(t) { return t.tabRenderer && t.tabRenderer.selected; }) || tabs[0];
      var items = tab.tabRenderer.content.sectionListRenderer.contents[0]
        .itemSectionRenderer.contents[0].playlistVideoListRenderer.contents;
      items.forEach(function(item) {
        var r = item.playlistVideoRenderer;
        if (!r || !r.videoId) return;
        var t = r.title && r.title.runs && r.title.runs[0] && r.title.runs[0].text || 'Untitled';
        videos.push({ id: r.videoId, title: t });
      });
    } catch(e) {
      alert('TubeScribe: Could not parse playlist (' + e.message + '). YouTube may have changed its layout.');
      return;
    }

    if (!videos.length) { alert('TubeScribe: No videos found in playlist.'); return; }

    var playlistTitle = document.title.replace(' - YouTube','').trim();
    var confirmed = confirm('TubeScribe found ' + videos.length + ' videos in "' + playlistTitle + '".\n\nGenerate notes for all? This will take ~' + Math.ceil(videos.length * 15 / 60) + ' minutes.');
    if (!confirmed) return;

    // Build sidebar for playlist
    var proot = mk('div',
      'position:fixed;top:0;right:0;width:420px;height:100vh;z-index:9999999;' +
      'background:#07090f;color:#e6edf5;font-family:-apple-system,sans-serif;font-size:14px;' +
      'box-shadow:-4px 0 32px rgba(0,0,0,0.7);border-left:1px solid #1e2d45;display:flex;flex-direction:column;');
    proot.id = ID;

    var phdr = mk('div','padding:14px 16px;border-bottom:1px solid #1e2d45;display:flex;align-items:center;gap:10px;flex-shrink:0;background:#0d1117;');
    var plogo = mk('span','font-weight:800;font-size:15px;');
    plogo.style.background = 'linear-gradient(135deg,#6c63ff,#a78bfa)';
    plogo.style.webkitBackgroundClip = 'text';
    plogo.style.webkitTextFillColor = 'transparent';
    plogo.textContent = 'TubeScribe Playlist';
    var pcloBtn = mk('button','background:none;border:none;color:#7d8fa8;font-size:20px;cursor:pointer;padding:0 2px;margin-left:auto;');
    pcloBtn.textContent = '\u2715';
    pcloBtn.onclick = function() { proot.remove(); document.body.style.marginRight = ''; };
    phdr.appendChild(plogo); phdr.appendChild(pcloBtn);

    var pstatus = mk('div','padding:10px 16px;font-size:12px;color:#a78bfa;font-weight:600;border-bottom:1px solid #1e2d45;flex-shrink:0;background:#0a0e19;');
    pstatus.textContent = '\u23f3 Starting playlist (' + videos.length + ' videos)\u2026';

    var ptrack = mk('div','padding:8px 16px;border-bottom:1px solid #1e2d45;flex-shrink:0;');
    var progressBar = mk('div','height:4px;background:#1e2d45;border-radius:2px;');
    var progressFill = mk('div','height:4px;background:linear-gradient(90deg,#6c63ff,#a78bfa);border-radius:2px;width:0%;transition:width 0.3s;');
    progressBar.appendChild(progressFill);
    ptrack.appendChild(progressBar);

    var plist = mk('div','flex:1;overflow-y:auto;padding:8px;');
    var pfoot = mk('div','padding:12px 16px;border-top:1px solid #1e2d45;flex-shrink:0;background:#0d1117;display:flex;gap:8px;');

    proot.append(phdr, pstatus, ptrack, plist, pfoot);
    document.body.appendChild(proot);
    document.body.style.marginRight = '420px';

    // Render video list items
    var itemEls = videos.map(function(v, i) {
      var row = mk('div','padding:8px 10px;border-radius:6px;margin-bottom:4px;display:flex;align-items:center;gap:8px;font-size:12px;');
      var num = mk('span','color:#7d8fa8;flex-shrink:0;width:24px;text-align:right;');
      num.textContent = (i+1) + '.';
      var vtitle = mk('span','flex:1;color:#c9d8eb;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;');
      vtitle.textContent = v.title;
      var vstatus = mk('span','flex-shrink:0;font-size:11px;color:#7d8fa8;');
      vstatus.textContent = 'Waiting';
      row.append(num, vtitle, vstatus);
      plist.appendChild(row);
      return { row, vstatus };
    });

    // Process each video
    var pdfs = []; // {title, bytes}
    var done = 0;

    for (var i = 0; i < videos.length; i++) {
      var v = videos[i];
      var ui = itemEls[i];
      ui.row.style.background = '#0d1a2e';
      ui.vstatus.textContent = '\u23f3 Fetching\u2026';
      ui.vstatus.style.color = '#a78bfa';
      pstatus.textContent = '\u23f3 Video ' + (i+1) + '/' + videos.length + ': ' + v.title.slice(0,40);

      try {
        // Fetch the watch page (same-origin — we're on youtube.com)
        var pageRes = await fetch('https://www.youtube.com/watch?v=' + v.id + '&hl=en');
        var pageHtml = await pageRes.text();

        // Extract transcript from page HTML
        var trackInfo = extractTranscriptFromHtml(pageHtml, v.id);
        if (!trackInfo) throw new Error('No captions found');

        // Fetch the actual transcript
        var capUrl = trackInfo.baseUrl.includes('fmt=')
          ? trackInfo.baseUrl.replace(/fmt=[^&]+/, 'fmt=json3')
          : trackInfo.baseUrl + '&fmt=json3';
        var capRes = await fetch(capUrl);
        if (!capRes.ok) throw new Error('Caption fetch failed');
        var capText = await capRes.text();
        var capData; try { capData = JSON.parse(capText); } catch(e) { capData = null; }

        var transcript = '';
        if (capData && capData.events) {
          var seen = new Set(), segs = [];
          capData.events.forEach(function(ev) {
            if (!ev.segs) return;
            var t = ev.segs.map(function(s){return s.utf8||'';}).join('').replace(/\n/g,' ').replace(/\s+/g,' ').trim();
            if (!t || t==='[Music]' || seen.has(t)) return;
            seen.add(t); segs.push(t);
          });
          transcript = segs.join(' ');
        }
        if (!transcript) throw new Error('Empty transcript');

        ui.vstatus.textContent = '\u23f3 Generating\u2026';

        // Generate notes
        var notesRes = await fetch(API + '/stream-notes', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          credentials: 'include',
          body: JSON.stringify({
            url: 'https://www.youtube.com/watch?v=' + v.id,
            video_id: v.id,
            prefetched_title: v.title,
            prefetched_transcript: transcript,
          }),
        });
        if (!notesRes.ok) throw new Error('Server ' + notesRes.status);

        var fullMd = '';
        var nreader = notesRes.body.getReader();
        var ndec = new TextDecoder();
        while (true) {
          var nc = await nreader.read();
          if (nc.done) break;
          ndec.decode(nc.value).split('\n').forEach(function(line) {
            if (!line.startsWith('data: ')) return;
            var d; try { d = JSON.parse(line.slice(6)); } catch(e) { return; }
            if (d && d.chunk) fullMd += d.chunk;
          });
        }

        if (!fullMd) throw new Error('Empty notes returned');

        pdfs.push({ title: v.title, markdown: fullMd });
        ui.vstatus.textContent = '\u2705 Done';
        ui.vstatus.style.color = '#6c63ff';
        ui.row.style.background = '#0a1a0d';
        done++;
      } catch(e) {
        ui.vstatus.textContent = '\u274c ' + e.message.slice(0,30);
        ui.vstatus.style.color = '#ff6b6b';
        ui.row.style.background = '#1a0a0a';
      }

      progressFill.style.width = Math.round((i+1) / videos.length * 100) + '%';
    }

    pstatus.textContent = '\u2705 Done! ' + done + '/' + videos.length + ' videos processed.';
    pstatus.style.color = '#6c63ff';

    if (!pdfs.length) { pstatus.textContent = '\u274c No notes generated.'; return; }

    // Footer buttons
    var dlAllBtn = mk('button',
      'flex:1;padding:9px;background:linear-gradient(135deg,#6c63ff,#a78bfa);color:#fff;' +
      'border:none;border-radius:7px;font-size:12px;font-weight:700;cursor:pointer;',
      {textContent: '\u2b07 Download All (' + pdfs.length + ')'}
    );
    var dlZipBtn = mk('button',
      'flex:1;padding:9px;background:#1a2332;color:#e6edf5;border:1px solid #1e2d45;' +
      'border-radius:7px;font-size:12px;font-weight:700;cursor:pointer;',
      {textContent: '\ud83d\udce6 Download ZIP'}
    );

    dlAllBtn.onclick = async function() {
      dlAllBtn.disabled = true;
      dlAllBtn.textContent = '\u23f3 Building PDFs\u2026';
      for (var j = 0; j < pdfs.length; j++) {
        var p = pdfs[j];
        try {
          var r = await fetch(API + '/markdown-to-pdf', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            credentials: 'include',
            body: JSON.stringify({title: p.title, markdown: p.markdown}),
          });
          if (!r.ok) throw new Error(r.status);
          var blob = await r.blob();
          var a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = p.title.replace(/[^a-z0-9]/gi,'_').slice(0,60) + '.pdf';
          a.click();
          await new Promise(function(res){setTimeout(res,600);});
        } catch(e) {
          console.error('PDF failed for', p.title, e);
        }
      }
      dlAllBtn.textContent = '\u2705 All Downloaded';
    };

    dlZipBtn.onclick = async function() {
      dlZipBtn.disabled = true;
      dlZipBtn.textContent = '\u23f3 Building ZIP\u2026';
      try {
        var r = await fetch(API + '/playlist-zip', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          credentials: 'include',
          body: JSON.stringify({
            playlist_title: playlistTitle,
            videos: pdfs,
          }),
        });
        if (!r.ok) throw new Error(r.status);
        var blob = await r.blob();
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = playlistTitle.replace(/[^a-z0-9]/gi,'_').slice(0,60) + '.zip';
        a.click();
        dlZipBtn.textContent = '\u2705 ZIP Downloaded';
      } catch(e) {
        dlZipBtn.textContent = '\u274c Failed: ' + e.message;
        dlZipBtn.disabled = false;
      }
    };

    pfoot.appendChild(dlAllBtn);
    pfoot.appendChild(dlZipBtn);
  }

  // Extract transcript from a fetched YouTube watch page HTML
  function extractTranscriptFromHtml(html, videoId) {
    // Find ytInitialPlayerResponse by brace-counting
    var key = 'ytInitialPlayerResponse=';
    var startIdx = html.indexOf(key);
    if (startIdx === -1) return null;

    var depth = 0, jsonStart = -1, inString = false, escape = false;
    for (var i = startIdx + key.length; i < html.length; i++) {
      var ch = html[i];
      if (escape) { escape = false; continue; }
      if (ch === '\\' && inString) { escape = true; continue; }
      if (ch === '"') { inString = !inString; continue; }
      if (inString) continue;
      if (ch === '{') { if (depth === 0) jsonStart = i; depth++; }
      else if (ch === '}') {
        depth--;
        if (depth === 0) {
          try {
            var playerData = JSON.parse(html.slice(jsonStart, i + 1));
            if (!playerData.videoDetails) continue; // wrong object
            var tracks = playerData.captions &&
              playerData.captions.playerCaptionsTracklistRenderer &&
              playerData.captions.playerCaptionsTracklistRenderer.captionTracks;
            if (!tracks || !tracks.length) return null;
            var track = tracks.find(function(t){return t.languageCode==='en'&&!t.kind;}) ||
                        tracks.find(function(t){return t.languageCode==='en';}) ||
                        tracks[0];
            if (!track || !track.baseUrl) return null;
            // Return the baseUrl — caller will fetch it
            return { baseUrl: track.baseUrl };
          } catch(e) { return null; }
        }
      }
    }
    return null;
  }

})();
