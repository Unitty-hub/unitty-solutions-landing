/* One-click, minimal YouTube player for Unitty pages.
 *
 * Markup:  <div class="yt-card" data-yt-id="VIDEO_ID" data-yt-fit="cover|contain"> ...poster... </div>
 *
 * How it works
 *  - Our own poster + green play button stay on top; YouTube's own UI is never clickable
 *    (controls=0 and a transparent shield sits over the iframe).
 *  - The YouTube player is pre-created quietly once the card is on screen, so the visitor's
 *    single click calls playVideo() straight away.
 *  - If the browser blocks sound-on autoplay (Safari / iOS), the video still starts on that
 *    same click, muted, with a small "tap for sound" chip.
 *  - Click while playing = pause (poster comes back). Video end = poster comes back.
 */
(function () {
  'use strict';

  var API_SRC = 'https://www.youtube.com/iframe_api';
  var apiPromise = null;

  function log(msg, extra) {
    try { console.info('[yt-player] ' + msg, extra === undefined ? '' : extra); } catch (e) {}
  }

  function loadApi() {
    if (apiPromise) return apiPromise;
    apiPromise = new Promise(function (resolve) {
      if (window.YT && window.YT.Player) { resolve(); return; }
      var prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = function () {
        if (typeof prev === 'function') { try { prev(); } catch (e) {} }
        resolve();
      };
      var s = document.createElement('script');
      s.src = API_SRC;
      s.async = true;
      document.head.appendChild(s);
    });
    return apiPromise;
  }

  function clarityTag(key, value) {
    if (typeof window.clarity === 'function') { try { window.clarity('set', key, value); } catch (e) {} }
  }

  function setup(card) {
    var id = card.getAttribute('data-yt-id');
    if (!id) return;
    var fit = card.getAttribute('data-yt-fit') || 'contain';

    var frameWrap = document.createElement('div');
    frameWrap.className = 'yt-frame yt-fit-' + fit;
    var mount = document.createElement('div');
    frameWrap.appendChild(mount);

    var shield = document.createElement('div');
    shield.className = 'yt-shield';

    var sound = document.createElement('button');
    sound.type = 'button';
    sound.className = 'yt-sound';
    sound.setAttribute('aria-label', 'Turn sound on');
    sound.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/></svg>';

    // our own minimal controls: elapsed / total time + a seek bar (YouTube's UI stays hidden)
    var controls = document.createElement('div');
    controls.className = 'yt-controls';
    controls.innerHTML = '<span class="yt-time">0:00 / 0:00</span><div class="yt-track" role="slider" aria-label="Seek" tabindex="0"><div class="yt-fill"></div></div>';
    var timeEl = controls.querySelector('.yt-time');
    var track = controls.querySelector('.yt-track');
    var fill = controls.querySelector('.yt-fill');

    // total length shown on the poster before the first click
    var durEl = card.querySelector('[data-yt-duration]');
    if (!durEl) {
      durEl = document.createElement('span');
      durEl.className = 'yt-dur-chip';
      durEl.setAttribute('data-yt-duration', '');
    }

    card.insertBefore(frameWrap, card.firstChild);
    card.appendChild(shield);
    card.appendChild(sound);
    card.appendChild(controls);
    if (!durEl.parentNode) card.appendChild(durEl);

    var player = null;
    var ready = false;
    var wantPlay = false;
    var watchdog = null;
    var userStarted = false; // YouTube can fire PLAYING/PAUSED on its own while cueing; ignore until the visitor clicks

    function state(s) { card.setAttribute('data-state', s); }
    state('idle');

    function fmt(sec) {
      sec = Math.max(0, Math.round(sec || 0));
      return Math.floor(sec / 60) + ':' + ('0' + (sec % 60)).slice(-2);
    }
    function duration() { try { return player.getDuration() || 0; } catch (e) { return 0; } }
    function refresh() {
      if (!ready) return;
      var d = duration(), t = 0;
      try { t = player.getCurrentTime() || 0; } catch (e) {}
      timeEl.textContent = fmt(t) + ' / ' + fmt(d);
      fill.style.width = d ? Math.min(100, (t / d) * 100) + '%' : '0%';
    }
    setInterval(function () {
      var st = card.getAttribute('data-state');
      if (st === 'playing' || st === 'paused') refresh();
    }, 250);

    function seekFromEvent(e) {
      var d = duration();
      if (!d) return;
      var r = track.getBoundingClientRect();
      var x = (e.touches ? e.touches[0].clientX : e.clientX) - r.left;
      var frac = Math.min(1, Math.max(0, x / r.width));
      try { player.seekTo(frac * d, true); } catch (err) {}
      refresh();
      log('--- seek', Math.round(frac * 100) + '%');
    }
    var dragging = false;
    track.addEventListener('pointerdown', function (e) {
      e.stopPropagation(); dragging = true; seekFromEvent(e);
      try { track.setPointerCapture(e.pointerId); } catch (err) {}
    });
    track.addEventListener('pointermove', function (e) { if (dragging) seekFromEvent(e); });
    track.addEventListener('pointerup', function () { dragging = false; });
    track.addEventListener('keydown', function (e) {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      e.preventDefault(); e.stopPropagation();
      try { player.seekTo(Math.max(0, player.getCurrentTime() + (e.key === 'ArrowRight' ? 5 : -5)), true); } catch (err) {}
      refresh();
    });
    controls.addEventListener('click', function (e) { e.stopPropagation(); });

    function build() {
      if (player) return;
      loadApi().then(function () {
        if (player) return;
        log('>>> creating player', id);
        player = new window.YT.Player(mount, {
          host: 'https://www.youtube-nocookie.com',
          videoId: id,
          playerVars: {
            autoplay: 0, controls: 0, disablekb: 1, fs: 0, rel: 0,
            playsinline: 1, modestbranding: 1, iv_load_policy: 3, cc_load_policy: 0
          },
          events: {
            onReady: function () {
              ready = true;
              log('+++ player ready', id);
              var d = duration();
              if (d) { durEl.textContent = fmt(d); timeEl.textContent = '0:00 / ' + fmt(d); }
              if (wantPlay) play();
            },
            onStateChange: function (e) {
              var YS = window.YT.PlayerState;
              if (!userStarted) {
                if (e.data === YS.PLAYING) { try { player.pauseVideo(); player.seekTo(0, true); } catch (err) {} }
                log('--- ignored state before first click', e.data);
                return;
              }
              if (e.data === YS.PLAYING) {
                clearTimeout(watchdog);
                state('playing');
              } else if (e.data === YS.PAUSED) {
                if (card.getAttribute('data-state') === 'playing') state('paused');
              } else if (e.data === YS.ENDED) {
                log('<<< ended', id);
                try { player.seekTo(0, true); player.pauseVideo(); } catch (err) {}
                card.removeAttribute('data-muted');
                userStarted = false;
                state('idle');
              }
            },
            onError: function (e) { log('*** player error', e && e.data); }
          }
        });
      });
    }

    function play() {
      userStarted = true;
      wantPlay = false;
      if (!ready) { wantPlay = true; state('loading'); build(); return; }
      log('--- play', id);
      state('loading');
      try { player.unMute(); player.playVideo(); } catch (err) {}
      clearTimeout(watchdog);
      // Sound-on start was blocked: start muted instead and offer the sound chip.
      watchdog = setTimeout(function () {
        var s = player.getPlayerState && player.getPlayerState();
        if (s !== 1 && s !== 3) {
          log('*** sound autoplay blocked, starting muted', id);
          try { player.mute(); player.playVideo(); } catch (err) {}
          card.setAttribute('data-muted', '1');
        }
      }, 1200);
      clarityTag('video_' + id, 'played');
    }

    card.addEventListener('click', function (e) {
      if (e.target.closest('.yt-sound') || e.target.closest('.yt-controls')) return;
      var s = card.getAttribute('data-state');
      if (s === 'playing') {
        try { player.pauseVideo(); } catch (err) {}
        state('paused');
      } else if (s !== 'loading') {
        play();
      }
    });
    card.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.click(); }
    });

    sound.addEventListener('click', function (e) {
      e.stopPropagation();
      try { player.unMute(); player.setVolume(100); } catch (err) {}
      card.removeAttribute('data-muted');
      log('+++ sound on', id);
    });

    // Pre-create the player once the card is (nearly) on screen and the page has loaded,
    // so the first click plays immediately.
    function warm() {
      if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
          if (entries.some(function (en) { return en.isIntersecting; })) { io.disconnect(); build(); }
        }, { rootMargin: '200px' });
        io.observe(card);
      } else {
        build();
      }
    }
    if (document.readyState === 'complete') setTimeout(warm, 600);
    else window.addEventListener('load', function () { setTimeout(warm, 600); });
  }

  function init() {
    var cards = document.querySelectorAll('.yt-card[data-yt-id]');
    for (var i = 0; i < cards.length; i++) setup(cards[i]);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
