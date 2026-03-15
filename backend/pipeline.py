<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TubeScribe — YouTube to PDF Notes</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:       #07090f;
  --surface:  #0d1117;
  --surface2: #131a24;
  --border:   #1e2d45;
  --text:     #e6edf5;
  --dim:      #7d8fa8;
  --accent:   #6c63ff;
  --accent2:  #a78bfa;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Syne', -apple-system, sans-serif;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ── Nav ── */
nav {
  padding: 20px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
}
.logo {
  font-size: 1.3rem;
  font-weight: 800;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
nav a {
  color: var(--dim);
  text-decoration: none;
  font-size: 0.85rem;
  transition: color 0.2s;
}
nav a:hover { color: var(--text); }

/* ── Hero ── */
.hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 60px 24px 40px;
  gap: 16px;
}

.hero-badge {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 6px 16px;
  font-size: 0.78rem;
  color: var(--dim);
  letter-spacing: 0.05em;
}

.hero h1 {
  font-family: 'DM Serif Display', serif;
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  line-height: 1.1;
  max-width: 700px;
}

.hero h1 em {
  font-style: italic;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero p {
  color: var(--dim);
  font-size: 1.05rem;
  max-width: 480px;
  line-height: 1.6;
}

/* ── Install card ── */
.install-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 40px;
  max-width: 560px;
  width: 100%;
  margin: 8px 0;
}

.steps { display: flex; flex-direction: column; gap: 0; }

.step {
  display: flex;
  gap: 16px;
  padding: 20px 0;
  border-bottom: 1px solid var(--border);
  align-items: flex-start;
}
.step:last-child { border-bottom: none; padding-bottom: 0; }
.step:first-child { padding-top: 0; }

.step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 2px;
}

.step-content h3 {
  font-size: 0.95rem;
  font-weight: 700;
  margin-bottom: 6px;
}

.step-content p {
  color: var(--dim);
  font-size: 0.85rem;
  line-height: 1.55;
}

/* ── Bookmarklet button ── */
.bm-wrap {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.bm-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: #fff;
  padding: 12px 24px;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 700;
  text-decoration: none;
  cursor: grab;
  user-select: none;
  box-shadow: 0 4px 20px rgba(108,99,255,0.35);
  transition: transform 0.15s, box-shadow 0.15s;
  font-family: 'Syne', sans-serif;
}
.bm-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 28px rgba(108,99,255,0.5);
}
.bm-btn:active { cursor: grabbing; }

.drag-hint {
  font-size: 0.78rem;
  color: var(--accent);
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ── Features ── */
.features {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
  max-width: 700px;
  margin-top: 8px;
}

.feat {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 0.82rem;
  color: var(--dim);
}
.feat span { color: var(--text); font-weight: 600; }

/* ── Stats ── */
.stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 4px;
}
.stat {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 0.75rem;
  color: var(--dim);
}
.stat b { color: var(--accent2); }

/* ── Footer ── */
footer {
  text-align: center;
  padding: 24px;
  color: var(--dim);
  font-size: 0.78rem;
  border-top: 1px solid var(--border);
}
footer a { color: var(--accent); text-decoration: none; }
</style>
</head>
<body>

<nav>
  <span class="logo">TubeScribe</span>
  <a href="https://github.com/karanmertiya/TubeScribe" target="_blank">GitHub ↗</a>
</nav>

<main class="hero">
  <div class="hero-badge">📋 One click · Any YouTube video · Instant PDF</div>

  <h1>YouTube, turned into<br><em>perfect notes</em></h1>

  <p>A sidebar that slides in on any YouTube video. Click once, get structured Markdown notes and a beautifully typeset PDF — without leaving the video.</p>

  <div class="install-card">
    <div class="steps">

      <div class="step">
        <div class="step-num">1</div>
        <div class="step-content">
          <h3>Drag this to your bookmarks bar</h3>
          <p>One time only. Works in Chrome, Firefox, Safari, Edge.</p>
          <div class="bm-wrap">
            <a class="bm-btn" id="bm-link" href="#">📋 TubeScribe</a>
            <span class="drag-hint">↑ Drag me to your bookmarks bar</span>
          </div>
        </div>
      </div>

      <div class="step">
        <div class="step-num">2</div>
        <div class="step-content">
          <h3>Open any YouTube video</h3>
          <p>Lectures, tutorials, podcasts — any video with captions.</p>
        </div>
      </div>

      <div class="step">
        <div class="step-num">3</div>
        <div class="step-content">
          <h3>Click TubeScribe in your bookmarks</h3>
          <p>A sidebar slides in on the YouTube page. Notes generate live, PDF downloads in one click.</p>
        </div>
      </div>

    </div>
  </div>

  <div class="features">
    <div class="feat"><span>No server IP issues</span> — runs in your browser</div>
    <div class="feat"><span>Groq LLaMA 3.3</span> — notes in seconds</div>
    <div class="feat"><span>WeasyPrint PDF</span> — beautifully typeset</div>
    <div class="feat"><span>Works on restricted videos</span> — age-gated, members</div>
  </div>

  <div class="stats" id="stats">
    <div class="stat">Loading stats…</div>
  </div>
</main>

<footer>
  Built with ♥ · <a href="https://github.com/karanmertiya/TubeScribe" target="_blank">Open source on GitHub</a>
</footer>

<script>
// ── Load stats ────────────────────────────────────────────────────────────────
fetch('/stats').then(r => r.json()).then(d => {
  const s = document.getElementById('stats');
  s.innerHTML = [
    `<div class="stat"><b>${(d.pdfs_generated||0).toLocaleString()}</b> PDFs generated</div>`,
    `<div class="stat"><b>${(d.videos_processed||0).toLocaleString()}</b> videos processed</div>`,
    `<div class="stat"><b>${(d.distinct_users||0).toLocaleString()}</b> users</div>`,
  ].join('');
}).catch(() => {
  document.getElementById('stats').innerHTML = '';
});

// ── Set bookmarklet href ──────────────────────────────────────────────────────
// Loader pattern: tiny href that fetches the real script from the server
// Update bookmarklet.js anytime — all users get it instantly, no re-drag needed
document.getElementById('bm-link').href = "javascript:void(function(){(function%20()%20%7B%20const%20API%20%3D%20'https%3A%2F%2Ftube-scribe.up.railway.app'%3B%20const%20ID%20%3D%20'tubescribe-root'%3B%20if%20(document.getElementById(ID))%20%7B%20document.getElementById(ID).remove()%3B%20document.body.style.marginRight%20%3D%20''%3B%20return%3B%20%7D%20if%20(!location.href.includes('youtube.com%2Fwatch'))%20%7B%20alert('TubeScribe%3A%20Open%20a%20YouTube%20video%20first.')%3B%20return%3B%20%7D%20const%20videoId%20%3D%20new%20URLSearchParams(location.search).get('v')%20%7C%7C%20''%3B%20const%20title%20%3D%20document.title.replace('%20-%20YouTube'%2C%20'').trim()%3B%20function%20el(tag%2C%20styles%2C%20attrs)%20%7B%20const%20e%20%3D%20document.createElement(tag)%3B%20if%20(styles)%20e.style.cssText%20%3D%20styles%3B%20if%20(attrs)%20Object.entries(attrs).forEach((%5Bk%2Cv%5D)%20%3D%3E%20%7B%20e%5Bk%5D%20%3D%20v%3B%20%7D)%3B%20return%20e%3B%20%7D%20function%20txt(str)%20%7B%20return%20document.createTextNode(str)%3B%20%7D%20const%20root%20%3D%20el('div'%2C%20'position%3Afixed%3Btop%3A0%3Bright%3A0%3Bwidth%3A400px%3Bheight%3A100vh%3Bz-index%3A9999999%3B'%20%2B%20'background%3A%2307090f%3Bcolor%3A%23e6edf5%3Bfont-family%3A-apple-system%2Csans-serif%3Bfont-size%3A14px%3B'%20%2B%20'box-shadow%3A-4px%200%2032px%20rgba(0%2C0%2C0%2C0.7)%3Bborder-left%3A1px%20solid%20%231e2d45%3B'%20%2B%20'display%3Aflex%3Bflex-direction%3Acolumn%3B'%20)%3B%20root.id%20%3D%20ID%3B%20const%20header%20%3D%20el('div'%2C%20'padding%3A14px%2016px%3Bborder-bottom%3A1px%20solid%20%231e2d45%3Bdisplay%3Aflex%3Balign-items%3Acenter%3Bgap%3A10px%3Bflex-shrink%3A0%3Bbackground%3A%230d1117%3B')%3B%20const%20logoSpan%20%3D%20el('span'%2C%20'font-weight%3A800%3Bfont-size%3A15px%3B')%3B%20logoSpan.style.background%20%3D%20'linear-gradient(135deg%2C%236c63ff%2C%23a78bfa)'%3B%20logoSpan.style.webkitBackgroundClip%20%3D%20'text'%3B%20logoSpan.style.webkitTextFillColor%20%3D%20'transparent'%3B%20logoSpan.appendChild(txt('TubeScribe'))%3B%20const%20titleSpan%20%3D%20el('span'%2C%20'flex%3A1%3Bfont-size%3A11px%3Bcolor%3A%237d8fa8%3Boverflow%3Ahidden%3Bwhite-space%3Anowrap%3Btext-overflow%3Aellipsis%3B')%3B%20titleSpan.appendChild(txt(title))%3B%20const%20closeBtn%20%3D%20el('button'%2C%20'background%3Anone%3Bborder%3Anone%3Bcolor%3A%237d8fa8%3Bfont-size%3A20px%3Bcursor%3Apointer%3Bpadding%3A0%202px%3Bline-height%3A1%3Bflex-shrink%3A0%3B'%2C%20%7BtextContent%3A'%E2%9C%95'%7D)%3B%20closeBtn.onclick%20%3D%20()%20%3D%3E%20%7B%20root.remove()%3B%20document.body.style.marginRight%20%3D%20''%3B%20%7D%3B%20header.append(logoSpan%2C%20titleSpan%2C%20closeBtn)%3B%20const%20phaseBar%20%3D%20el('div'%2C%20'padding%3A10px%2016px%3Bbackground%3A%230a0e19%3Bborder-bottom%3A1px%20solid%20%231e2d45%3Bflex-shrink%3A0%3B')%3B%20const%20phaseLabel%20%3D%20el('div'%2C%20'font-size%3A12px%3Bfont-weight%3A600%3Bcolor%3A%23a78bfa%3Bmargin-bottom%3A6px%3B')%3B%20phaseLabel.appendChild(txt('%E2%8F%B3%20Starting%E2%80%A6'))%3B%20const%20phaseTrack%20%3D%20el('div'%2C%20'display%3Aflex%3Bgap%3A4px%3B')%3B%20const%20phases%20%3D%20%5B'Transcript'%2C%20'Sending'%2C%20'Generating'%2C%20'Done'%5D%3B%20const%20phaseDots%20%3D%20phases.map((name%2C%20i)%20%3D%3E%20%7B%20const%20dot%20%3D%20el('div'%2C%20'flex%3A1%3Bheight%3A3px%3Bborder-radius%3A2px%3Bbackground%3A%231e2d45%3Btransition%3Abackground%200.3s%3B'%2C%20%7Btitle%3A%20name%7D%20)%3B%20phaseTrack.appendChild(dot)%3B%20return%20dot%3B%20%7D)%3B%20function%20setPhase(idx%2C%20msg)%20%7B%20phaseLabel.textContent%20%3D%20''%3B%20phaseLabel.appendChild(txt(msg))%3B%20phaseDots.forEach((d%2C%20i)%20%3D%3E%20%7B%20d.style.background%20%3D%20i%20%3C%20idx%20%3F%20'%236c63ff'%20%3A%20i%20%3D%3D%3D%20idx%20%3F%20'%23a78bfa'%20%3A%20'%231e2d45'%3B%20%7D)%3B%20%7D%20phaseBar.append(phaseLabel%2C%20phaseTrack)%3B%20const%20logArea%20%3D%20el('div'%2C%20'padding%3A8px%2016px%3Bfont-size%3A11px%3Bcolor%3A%235a7090%3Bmax-height%3A80px%3Boverflow-y%3Aauto%3Bborder-bottom%3A1px%20solid%20%231e2d45%3Bflex-shrink%3A0%3B')%3B%20function%20log(msg%2C%20color)%20%7B%20const%20line%20%3D%20el('div'%2C%20'margin-bottom%3A2px%3B'%20%2B%20(color%20%3F%20'color%3A'%2Bcolor%2B'%3B'%20%3A%20''))%3B%20line.appendChild(txt(msg))%3B%20logArea.appendChild(line)%3B%20logArea.scrollTop%20%3D%2099999%3B%20%7D%20const%20contentArea%20%3D%20el('div'%2C%20'flex%3A1%3Boverflow-y%3Aauto%3Bpadding%3A16px%3Bline-height%3A1.7%3Bfont-size%3A13px%3B')%3B%20const%20pdfBar%20%3D%20el('div'%2C%20'padding%3A12px%2016px%3Bborder-top%3A1px%20solid%20%231e2d45%3Bflex-shrink%3A0%3Bdisplay%3Anone%3Bbackground%3A%230d1117%3B')%3B%20const%20pdfBtn%20%3D%20el('button'%2C%20'width%3A100%25%3Bpadding%3A10px%3Bbackground%3Alinear-gradient(135deg%2C%236c63ff%2C%23a78bfa)%3Bcolor%3A%23fff%3B'%20%2B%20'border%3Anone%3Bborder-radius%3A8px%3Bfont-size%3A14px%3Bfont-weight%3A700%3Bcursor%3Apointer%3Bfont-family%3A-apple-system%2Csans-serif%3B'%2C%20%7BtextContent%3A%20'%E2%AC%87%20Download%20PDF'%7D%20)%3B%20pdfBar.appendChild(pdfBtn)%3B%20root.append(header%2C%20phaseBar%2C%20logArea%2C%20contentArea%2C%20pdfBar)%3B%20document.body.appendChild(root)%3B%20document.body.style.marginRight%20%3D%20'400px'%3B%20function%20renderMd(md)%20%7B%20contentArea.textContent%20%3D%20''%3B%20md.split('%5Cn').forEach(line%20%3D%3E%20%7B%20const%20p%20%3D%20el('div'%2C%20'margin-bottom%3A4px%3B')%3B%20if%20(line.startsWith('%23%23%20'))%20%7B%20p.style.cssText%20%3D%20'font-size%3A15px%3Bfont-weight%3A700%3Bcolor%3A%23a78bfa%3Bmargin%3A12px%200%206px%3Bborder-bottom%3A1px%20solid%20%231e2d45%3Bpadding-bottom%3A4px%3B'%3B%20p.appendChild(txt(line.slice(3)))%3B%20%7D%20else%20if%20(line.startsWith('%23%23%23%20'))%20%7B%20p.style.cssText%20%3D%20'font-size%3A13px%3Bfont-weight%3A700%3Bcolor%3A%23e6edf5%3Bmargin%3A10px%200%204px%3B'%3B%20p.appendChild(txt(line.slice(4)))%3B%20%7D%20else%20if%20(line.startsWith('-%20')%20%7C%7C%20line.startsWith('*%20'))%20%7B%20p.style.cssText%20%3D%20'padding-left%3A14px%3Bcolor%3A%23c9d8eb%3B'%3B%20p.appendChild(txt('%E2%80%A2%20'%20%2B%20line.slice(2)))%3B%20%7D%20else%20if%20(line.startsWith('%3E%20'))%20%7B%20p.style.cssText%20%3D%20'border-left%3A3px%20solid%20%236c63ff%3Bpadding-left%3A10px%3Bcolor%3A%237d8fa8%3Bfont-style%3Aitalic%3B'%3B%20p.appendChild(txt(line.slice(2)))%3B%20%7D%20else%20if%20(line.startsWith('**')%20%26%26%20line.endsWith('**'))%20%7B%20p.style.cssText%20%3D%20'font-weight%3A700%3Bcolor%3A%23e6edf5%3B'%3B%20p.appendChild(txt(line.slice(2%2C%20-2)))%3B%20%7D%20else%20if%20(line.trim()%20%3D%3D%3D%20'')%20%7B%20p.style.height%20%3D%20'6px'%3B%20%7D%20else%20%7B%20p.style.color%20%3D%20'%23c9d8eb'%3B%20p.appendChild(txt(line))%3B%20%7D%20contentArea.appendChild(p)%3B%20%7D)%3B%20contentArea.scrollTop%20%3D%2099999%3B%20%7D%20async%20function%20getTranscript()%20%7B%20setPhase(0%2C%20'%E2%8F%B3%20Phase%201%2F4%20%E2%80%94%20Reading%20transcript%E2%80%A6')%3B%20log('Looking%20for%20captions%20in%20page%E2%80%A6')%3B%20const%20tracks%20%3D%20window%3F.ytInitialPlayerResponse%3F.captions%20%3F.playerCaptionsTracklistRenderer%3F.captionTracks%3B%20if%20(tracks%3F.length)%20%7B%20log('Found%20'%20%2B%20tracks.length%20%2B%20'%20caption%20track(s)')%3B%20const%20track%20%3D%20tracks.find(t%20%3D%3E%20t.languageCode%20%3D%3D%3D%20'en'%20%26%26%20!t.kind)%20%7C%7C%20tracks.find(t%20%3D%3E%20t.languageCode%20%3D%3D%3D%20'en')%20%7C%7C%20tracks.find(t%20%3D%3E%20t.languageCode%3F.startsWith('en'))%20%7C%7C%20tracks%5B0%5D%3B%20log('Using%3A%20'%20%2B%20(track.languageCode%20%7C%7C%20'%3F')%20%2B%20(track.kind%20%3F%20'%20%5Bauto%5D'%20%3A%20'%20%5Bmanual%5D'))%3B%20const%20url%20%3D%20track.baseUrl.includes('fmt%3D')%20%3F%20track.baseUrl.replace(%2Ffmt%3D%5B%5E%26%5D%2B%2F%2C%20'fmt%3Djson3')%20%3A%20track.baseUrl%20%2B%20'%26fmt%3Djson3'%3B%20const%20res%20%3D%20await%20fetch(url)%3B%20if%20(res.ok)%20%7B%20const%20data%20%3D%20await%20res.json()%3B%20const%20seen%20%3D%20new%20Set()%2C%20segs%20%3D%20%5B%5D%3B%20for%20(const%20ev%20of%20(data.events%20%7C%7C%20%5B%5D))%20%7B%20if%20(!ev.segs)%20continue%3B%20const%20t%20%3D%20ev.segs.map(s%20%3D%3E%20s.utf8%7C%7C'').join('').replace(%2F%5Cn%2Fg%2C'%20').replace(%2F%5Cs%2B%2Fg%2C'%20').trim()%3B%20if%20(!t%20%7C%7C%20t%20%3D%3D%3D%20'%5BMusic%5D'%20%7C%7C%20seen.has(t))%20continue%3B%20seen.add(t)%3B%20segs.push(t)%3B%20%7D%20if%20(segs.length%20%3E%205)%20%7B%20log('%E2%9C%93%20'%20%2B%20segs.length%20%2B%20'%20segments%2C%20~'%20%2B%20segs.join('%20').split(%2F%5Cs%2B%2F).length%20%2B%20'%20words')%3B%20return%20segs.join('%20')%3B%20%7D%20%7D%20%7D%20log('No%20inline%20captions%20%E2%80%94%20trying%20Show%20Transcript%20button%E2%80%A6')%3B%20setPhase(0%2C%20'%E2%8F%B3%20Phase%201%2F4%20%E2%80%94%20Opening%20transcript%20panel%E2%80%A6')%3B%20const%20sleep%20%3D%20ms%20%3D%3E%20new%20Promise(r%20%3D%3E%20setTimeout(r%2C%20ms))%3B%20const%20expandBtn%20%3D%20document.querySelector('tp-yt-paper-button%23expand%2C%20%23expand')%3B%20if%20(expandBtn)%20%7B%20expandBtn.click()%3B%20await%20sleep(500)%3B%20%7D%20let%20transcriptBtn%20%3D%20%5B...document.querySelectorAll('button%2C%20tp-yt-paper-button')%5D%20.find(el%20%3D%3E%20el.textContent.trim().toLowerCase()%20%3D%3D%3D%20'show%20transcript')%20%7C%7C%20%5B...document.querySelectorAll('%23description%20button%2C%20ytd-text-inline-expander%20button')%5D%20.find(el%20%3D%3E%20el.textContent.toLowerCase().includes('transcript'))%3B%20if%20(transcriptBtn)%20%7B%20log('Clicking%20Show%20Transcript%E2%80%A6')%3B%20transcriptBtn.click()%3B%20await%20sleep(2000)%3B%20%7D%20else%20%7B%20const%20moreBtn%20%3D%20document.querySelector('button%5Baria-label%3D%22More%20actions%22%5D')%3B%20if%20(moreBtn)%20%7B%20moreBtn.click()%3B%20await%20sleep(600)%3B%20const%20item%20%3D%20%5B...document.querySelectorAll('tp-yt-paper-item%2C%20ytd-menu-service-item-renderer')%5D%20.find(el%20%3D%3E%20el.textContent.toLowerCase().includes('transcript'))%3B%20if%20(item)%20%7B%20item.click()%3B%20await%20sleep(2000)%3B%20%7D%20else%20%7B%20document.body.click()%3B%20throw%20new%20Error('No%20transcript%20button%20found.%20Scroll%20down%20to%20expand%20the%20description%20first%2C%20then%20try%20again.')%3B%20%7D%20%7D%20%7D%20const%20selectors%20%3D%20%5B'ytd-transcript-segment-renderer%20.segment-text'%2C%20'ytd-transcript-segment-view-model%20.segment-text'%5D%3B%20let%20segs%20%3D%20%5B%5D%3B%20for%20(const%20sel%20of%20selectors)%20%7B%20const%20els%20%3D%20document.querySelectorAll(sel)%3B%20if%20(els.length%20%3E%205)%20%7B%20segs%20%3D%20%5B...els%5D.map(e%20%3D%3E%20e.textContent.trim()).filter(Boolean)%3B%20break%3B%20%7D%20%7D%20if%20(!segs.length)%20%7B%20const%20panel%20%3D%20document.querySelector('%5Btarget-id%3D%22engagement-panel-transcript%22%5D%20ytd-transcript-renderer')%3B%20if%20(panel)%20segs%20%3D%20panel.innerText.split('%5Cn').filter(l%20%3D%3E%20l.trim()%20%26%26%20!%2F%5E%5Cd%2B%3A%5Cd%2B%24%2F.test(l.trim()))%3B%20%7D%20if%20(segs.length%20%3C%205)%20throw%20new%20Error('Transcript%20panel%20empty.%20Make%20sure%20the%20video%20has%20captions.')%3B%20log('%E2%9C%93%20'%20%2B%20segs.length%20%2B%20'%20segments%20from%20panel')%3B%20return%20segs.join('%20')%3B%20%7D%20async%20function%20streamNotes(transcript)%20%7B%20setPhase(1%2C%20'%E2%8F%B3%20Phase%202%2F4%20%E2%80%94%20Sending%20to%20server%E2%80%A6')%3B%20log('Sending%20'%20%2B%20transcript.split(%2F%5Cs%2B%2F).length%20%2B%20'%20words%20to%20Groq%E2%80%A6')%3B%20const%20res%20%3D%20await%20fetch(API%20%2B%20'%2Fstream-notes'%2C%20%7B%20method%3A%20'POST'%2C%20headers%3A%20%7B%20'Content-Type'%3A%20'application%2Fjson'%20%7D%2C%20credentials%3A%20'include'%2C%20body%3A%20JSON.stringify(%7B%20url%3A%20'https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D'%20%2B%20videoId%2C%20video_id%3A%20videoId%2C%20prefetched_title%3A%20title%2C%20prefetched_transcript%3A%20transcript%2C%20%7D)%2C%20%7D)%3B%20if%20(!res.ok)%20%7B%20const%20err%20%3D%20await%20res.json().catch(()%20%3D%3E%20(%7Berror%3A%20res.status%7D))%3B%20throw%20new%20Error(err.error%20%7C%7C%20'Server%20'%20%2B%20res.status)%3B%20%7D%20setPhase(2%2C%20'%E2%8F%B3%20Phase%203%2F4%20%E2%80%94%20Generating%20notes%E2%80%A6')%3B%20log('Connected%20%E2%80%94%20streaming%E2%80%A6')%3B%20let%20fullMd%20%3D%20''%3B%20const%20reader%20%3D%20res.body.getReader()%3B%20const%20dec%20%3D%20new%20TextDecoder()%3B%20while%20(true)%20%7B%20const%20%7B%20value%2C%20done%20%7D%20%3D%20await%20reader.read()%3B%20if%20(done)%20break%3B%20for%20(const%20line%20of%20dec.decode(value).split('%5Cn'))%20%7B%20if%20(!line.startsWith('data%3A%20'))%20continue%3B%20let%20d%3B%20try%20%7B%20d%20%3D%20JSON.parse(line.slice(6))%3B%20%7D%20catch%20%7B%20continue%3B%20%7D%20if%20(d.total_chunks)%20log('Processing%20'%20%2B%20d.total_chunks%20%2B%20'%20chunk'%20%2B%20(d.total_chunks%20%3E%201%20%3F%20's'%20%3A%20'')%20%2B%20'%E2%80%A6')%3B%20if%20(d.chunk)%20%7B%20fullMd%20%2B%3D%20d.chunk%3B%20renderMd(fullMd)%3B%20if%20(d.chunk_index%20%26%26%20d.total_chunks)%20%7B%20setPhase(2%2C%20'%E2%8F%B3%20Phase%203%2F4%20%E2%80%94%20Chunk%20'%20%2B%20d.chunk_index%20%2B%20'%2F'%20%2B%20d.total_chunks%20%2B%20'%E2%80%A6')%3B%20%7D%20%7D%20if%20(d.done)%20%7B%20setPhase(3%2C%20'%E2%9C%85%20Phase%204%2F4%20%E2%80%94%20Done!')%3B%20log('%E2%9C%93%20Complete%20%E2%80%94%20'%20%2B%20fullMd.split(%2F%5Cs%2B%2F).length%20%2B%20'%20word%20notes'%2C%20'%236c63ff')%3B%20pdfBar.style.display%20%3D%20'block'%3B%20pdfBtn.onclick%20%3D%20()%20%3D%3E%20downloadPDF(fullMd)%3B%20%7D%20if%20(d.error)%20throw%20new%20Error(d.error)%3B%20%7D%20%7D%20%7D%20async%20function%20downloadPDF(markdown)%20%7B%20pdfBtn.textContent%20%3D%20'%E2%8F%B3%20Building%20PDF%E2%80%A6'%3B%20pdfBtn.style.opacity%20%3D%20'0.7'%3B%20pdfBtn.disabled%20%3D%20true%3B%20try%20%7B%20const%20res%20%3D%20await%20fetch(API%20%2B%20'%2Fmarkdown-to-pdf'%2C%20%7B%20method%3A%20'POST'%2C%20headers%3A%20%7B%20'Content-Type'%3A%20'application%2Fjson'%20%7D%2C%20credentials%3A%20'include'%2C%20body%3A%20JSON.stringify(%7B%20title%2C%20markdown%20%7D)%2C%20%7D)%3B%20if%20(!res.ok)%20throw%20new%20Error('PDF%20failed%3A%20'%20%2B%20res.status)%3B%20const%20blob%20%3D%20await%20res.blob()%3B%20const%20a%20%3D%20document.createElement('a')%3B%20a.href%20%3D%20URL.createObjectURL(blob)%3B%20a.download%20%3D%20title.replace(%2F%5B%5Ea-z0-9%5D%2Fgi%2C%20'_').slice(0%2C%2060)%20%2B%20'.pdf'%3B%20a.click()%3B%20pdfBtn.textContent%20%3D%20'%E2%9C%85%20PDF%20Downloaded'%3B%20pdfBtn.style.opacity%20%3D%20'1'%3B%20%7D%20catch(e)%20%7B%20pdfBtn.textContent%20%3D%20'%E2%9D%8C%20Failed%20%E2%80%94%20'%20%2B%20e.message%3B%20pdfBtn.style.opacity%20%3D%20'1'%3B%20pdfBtn.disabled%20%3D%20false%3B%20%7D%20%7D%20(async%20()%20%3D%3E%20%7B%20try%20%7B%20const%20transcript%20%3D%20await%20getTranscript()%3B%20await%20streamNotes(transcript)%3B%20%7D%20catch(err)%20%7B%20setPhase(-1%2C%20'%E2%9D%8C%20Error')%3B%20log('%E2%9D%8C%20'%20%2B%20err.message%2C%20'%23ff6b6b')%3B%20contentArea.textContent%20%3D%20''%3B%20const%20errDiv%20%3D%20el('div'%2C%20'color%3A%23ff6b6b%3Bpadding%3A16px%3Bbackground%3A%231a0a0a%3Bborder-radius%3A8px%3Bborder%3A1px%20solid%20%233a1010%3Bline-height%3A1.6%3B')%3B%20errDiv.appendChild(txt(err.message))%3B%20contentArea.appendChild(errDiv)%3B%20%7D%20%7D)()%3B%20%7D)()%3B}())";
</script>

</body>
</html>