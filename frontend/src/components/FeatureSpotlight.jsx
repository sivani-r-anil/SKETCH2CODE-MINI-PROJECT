import { useEffect, useId, useRef, useState } from "react";

const FEATURES = [
  { label: "Upload", title: "Every interface starts with an idea.", description: "Bring a hand-drawn sketch or digital wireframe. Keep the freedom of paper while preparing your design for the web.", detail: "Hand-drawn and digital wireframes", icon: "M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5" },
  { label: "Analyze", title: "Find the structure behind the sketch.", description: "YOLOv8 detects components, EasyOCR reads their text, and spatial reconstruction connects them into a meaningful layout.", detail: "Detection · Text extraction · Spatial relationships", icon: "M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M7 7h10v10H7z" },
  { label: "Generate", title: "Your structure. Editable React code.", description: "Turn reconstructed components into React and Tailwind CSS. Inspect the generated source and make it your own in Monaco Editor.", detail: "React JSX · Tailwind CSS · Monaco Editor", icon: "m8 6-6 6 6 6m8-12 6 6-6 6m-3-14-2 16" },
  { label: "Preview & Export", title: "See it live. Take it with you.", description: "Refine your interface in the live preview, try its themes, and export your current code for the next step of your project.", detail: "Live preview · Themes · Project export", icon: "M3 3h18v13H3zM8 21h8m-4-5v5m-4-10 3 3 5-6" },
];

const STYLES = `
.sc-fd { position:relative; isolation:isolate; padding:64px 0 42px; color:var(--sc-text,#fff7ed); }
.sc-fd * { box-sizing:border-box; }
.sc-fd::before { content:""; position:absolute; z-index:-1; inset:8% 4% 15%; pointer-events:none; background:radial-gradient(ellipse at 75% 40%,#ff8a7e0d,transparent 60%); }
.sc-fd-head { max-width:740px; margin:0 auto 42px; text-align:center; animation:sc-fd-enter .6s ease-out both; }
.sc-fd-kicker { color:var(--sc-coral,#ff8a7e); font:10px/1.6 ui-monospace,monospace; letter-spacing:.17em; text-transform:uppercase; }
.sc-fd-head h1 { margin:14px 0 18px; font-size:clamp(34px,5vw,60px); font-weight:600; line-height:1.07; letter-spacing:-.055em; }
.sc-fd-head p { max-width:580px; margin:auto; color:var(--sc-muted,#b9b1ad); font-size:15px; line-height:1.8; }
.sc-fd-stage { position:relative; display:grid; border:1px solid var(--sc-line,#38343e); border-radius:28px; background:linear-gradient(145deg,#25212788,#17161cee); box-shadow:0 28px 80px #0004,inset 0 1px #ffffff06; }
.sc-fd-panel { grid-area:1/1; display:grid; grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr); align-items:center; gap:36px; padding:48px 44px 62px; min-width:0; }
/* All panels contribute to sizing; only the selected panel is accessible. */
.sc-fd-panel[hidden] { display:grid; visibility:hidden; pointer-events:none; }
.sc-fd-copy h2 { margin:16px 0 18px; max-width:440px; font-size:clamp(28px,3.2vw,42px); line-height:1.15; font-weight:550; letter-spacing:-.04em; }
.sc-fd-copy p { margin:0; max-width:430px; color:var(--sc-muted,#b9b1ad); font-size:14px; line-height:1.9; }
.sc-fd-detail { display:block; margin-top:26px; max-width:430px; color:var(--sc-coral,#ff8a7e); font:11px/1.8 ui-monospace,monospace; }
.sc-fd-panel:not([hidden]) .sc-fd-copy { animation:sc-fd-enter .4s ease-out both; }
.sc-fd-art { position:relative; min-width:0; aspect-ratio:1.2; perspective:1100px; display:grid; place-items:center; }
.sc-fd-art::before { content:""; position:absolute; inset:12%; background:radial-gradient(ellipse,#ff9a811a,transparent 70%); filter:blur(16px); }
.sc-fd-window { width:92%; position:relative; border:1px solid #64535280; border-radius:15px; background:#18171e; box-shadow:16px 30px 45px #0005,inset 0 1px #ffffff0a; transform:rotateY(-9deg) rotateX(5deg) rotateZ(2deg); }
.sc-fd-panel:not([hidden]) .sc-fd-window { animation:sc-fd-float 9s ease-in-out infinite; }
.sc-fd-chrome { height:34px; display:flex; align-items:center; gap:5px; padding:0 14px; border-bottom:1px solid #ffffff0a; }
.sc-fd-chrome i { width:5px; height:5px; border-radius:50%; background:#77656b; }
.sc-fd-chrome small { margin-left:auto; color:#b9b1ad; font:9px ui-monospace,monospace; }
.sc-fd-canvas { margin:18px; padding:17px; border:1px solid #ffffff12; border-radius:8px; }
.sc-fd-mocknav { display:flex; gap:9px; align-items:center; margin-bottom:24px; }
.sc-fd-mocknav b { display:block; width:24px; height:9px; background:#ffaf99; border-radius:3px; margin-right:auto; }
.sc-fd-line { height:5px; border-radius:4px; background:#91878e50; width:100%; }
.sc-fd-mocknav .sc-fd-line { width:22px; height:3px; }
.sc-fd-titleline { width:65%; height:12px; border-radius:3px; background:#efe2d5; margin:0 0 10px; }
.sc-fd-short { width:42%; margin-top:7px; }
.sc-fd-mockgrid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-top:23px; }
.sc-fd-mockcard { height:72px; border:1px solid #ffffff1c; border-radius:6px; padding:10px; background:linear-gradient(145deg,#ffad9112,#ffffff02); }
.sc-fd-mockcard svg { width:23px; height:23px; color:#ffb49d; margin-bottom:9px; }
.sc-fd-wire .sc-fd-canvas { border-style:dashed; }
.sc-fd-wire .sc-fd-titleline { background:transparent; border:1px solid #cab9b4; }
.sc-fd-wire .sc-fd-mockcard { background:none; border-style:dashed; }
.sc-fd-badge { position:absolute; bottom:2%; right:0; display:flex; align-items:center; gap:9px; max-width:95%; padding:12px 16px; border:1px solid #75574d70; border-radius:12px; background:#292229f5; box-shadow:0 12px 24px #0004; color:#ffe8dc; font:11px/1.5 ui-monospace,monospace; }
.sc-fd-badge svg { width:17px; height:17px; color:#ffb49d; flex-shrink:0; }
.sc-fd-box { position:absolute; border:1px solid #ffad91; border-radius:5px; pointer-events:none; }
.sc-fd-box small { position:absolute; top:-14px; left:0; color:#ffc7ae; font:8px ui-monospace,monospace; white-space:nowrap; }
.sc-fd-box-a { left:8%; top:39%; width:60%; height:23%; }
.sc-fd-box-b { left:8%; top:69%; width:84%; height:26%; }
.sc-fd-scan { position:absolute; left:5%; right:5%; top:20%; height:1px; background:#ffae9190; box-shadow:0 0 16px #ff9a8140; }
.sc-fd-panel:not([hidden]) .sc-fd-scan { animation:sc-fd-scan 5s ease-in-out infinite; }
.sc-fd-code { margin:0; padding:24px 18px 30px; min-height:240px; font:clamp(9px,1.15vw,13px)/2 ui-monospace,monospace; color:#e7d4c9; overflow:hidden; white-space:pre; }
.sc-fd-code span { display:block; }
.sc-fd-code em { font-style:normal; color:#ffb49d; }
.sc-fd-code .sc-fd-dim { color:#a496a2; }
.sc-fd-dock-wrap { position:relative; z-index:1; margin:-25px auto 0; width:fit-content; max-width:100%; padding:0 12px; }
.sc-fd-dock { display:flex; align-items:stretch; gap:6px; padding:9px; border:1px solid #ffffff1c; border-radius:21px; background:#29252ee8; backdrop-filter:blur(20px); box-shadow:0 16px 42px #0006,inset 0 1px #ffffff0a; }
.sc-fd-tab { position:relative; border:0; border-radius:13px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; width:116px; min-height:78px; padding:11px 7px; background:transparent; color:var(--sc-muted,#b9b1ad); font:inherit; font-size:11px; cursor:pointer; transition:background .2s,color .2s,transform .2s; }
.sc-fd-tab svg { width:22px; height:22px; transition:transform .2s; }
.sc-fd-tab[aria-selected="true"] { background:linear-gradient(145deg,#ffb69b24,#ff8a7e0d); color:#ffcab3; box-shadow:inset 0 0 0 1px #ffb49d22; }
@media(hover:hover) { .sc-fd-tab:hover { background:#ffffff08; color:#fff7ed; transform:translateY(-3px); } .sc-fd-tab:hover svg { transform:rotate(-5deg); } }
.sc-fd-tab:focus-visible,.sc-fd-panel:focus-visible,.sc-fd-start:focus-visible { outline:2px solid var(--sc-amber,#ffbf75); outline-offset:4px; }
.sc-fd-bottom { margin:28px auto 0; text-align:center; }
.sc-fd-bottom p { margin:0 0 16px; color:var(--sc-muted,#b9b1ad); font-size:12px; }
.sc-fd-start { display:inline-flex; align-items:center; gap:12px; padding:13px 23px; border:1px solid #ffc2a566; border-radius:11px; color:#23191c; background:linear-gradient(115deg,#ff9b8c,#ffc096); font:inherit; font-size:13px; font-weight:600; cursor:pointer; transition:transform .2s,box-shadow .2s; }
.sc-fd-start:hover { transform:translateY(-2px); box-shadow:0 7px 24px #ff8a7e18; }
.sc-fd-start:disabled { opacity:.5; cursor:wait; transform:none; }
.sc-fd-scroll-in { animation:sc-fd-enter .55s ease-out both; }
@keyframes sc-fd-enter { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
@keyframes sc-fd-float { 0%,100% { transform:rotateY(-9deg) rotateX(5deg) rotateZ(2deg) translateY(0); } 50% { transform:rotateY(-6deg) rotateX(3deg) rotateZ(1deg) translateY(-6px); } }
@keyframes sc-fd-scan { 0%,100% { transform:translateY(0); opacity:.35; } 50% { transform:translateY(180px); opacity:.8; } }
@media(max-width:800px) { .sc-fd { padding-top:40px; } .sc-fd-panel { padding:30px 26px 52px; gap:20px; } .sc-fd-copy h2 { font-size:28px; } .sc-fd-art { aspect-ratio:.95; } .sc-fd-canvas { margin:12px; padding:12px; } .sc-fd-code { font-size:9px; } }
@media(max-width:600px) { .sc-fd-head { margin-bottom:28px; } .sc-fd-head p { font-size:13px; } .sc-fd-panel { grid-template-columns:minmax(0,1fr); gap:16px; padding:27px 22px 48px; } .sc-fd-copy h2 { font-size:29px; max-width:350px; } .sc-fd-copy p { font-size:13px; } .sc-fd-detail { margin-top:16px; font-size:10px; } .sc-fd-art { width:100%; max-width:380px; margin:auto; aspect-ratio:1.25; } .sc-fd-tab { width:auto; flex:1; min-width:0; font-size:9px; min-height:72px; gap:7px; padding:9px 4px; } .sc-fd-dock { gap:2px; padding:6px; } .sc-fd-dock-wrap { width:100%; padding:0 5px; } .sc-fd-code { min-height:200px; font-size:10px; padding:17px; } }
@media(prefers-reduced-motion:reduce) { .sc-fd *, .sc-fd *::before { animation:none !important; transition:none !important; } .sc-fd-tab:hover,.sc-fd-start:hover { transform:none; } .sc-fd-scan { display:none; } }
`;

function Symbol({ index, ...props }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d={FEATURES[index].icon} /></svg>;
}

function Illustration({ index }) {
  return <div className={`sc-fd-art ${index === 0 ? "sc-fd-wire" : ""}`} aria-hidden="true">
    <div className="sc-fd-window">
      <div className="sc-fd-chrome"><i /><i /><i /><small>{["wireframe.png", "Component analysis", "GeneratedPage.jsx", "Live preview"][index]}</small></div>
      {index === 2 ? <pre className="sc-fd-code"><code>
        <span className="sc-fd-dim">// From sketch to structure</span>
        <span><em>function</em> GeneratedPage() {"{"}</span>
        <span>  <em>return</em> (</span>
        <span>    {"<main className=\"grid gap-6\">"}</span>
        <span>      {"<Header />"}</span>
        <span>      {"<Content />"}</span>
        <span>    {"</main>"}</span>
        <span>  );</span><span>{"}"}</span>
      </code></pre> : <div className="sc-fd-canvas">
        <div className="sc-fd-mocknav"><b /><div className="sc-fd-line" /><div className="sc-fd-line" /><div className="sc-fd-line" /></div>
        <div className="sc-fd-titleline" /><div className="sc-fd-line" /><div className="sc-fd-line sc-fd-short" />
        <div className="sc-fd-mockgrid">{[0, 1, 2].map(item => <div className="sc-fd-mockcard" key={item}><Symbol index={item} /><div className="sc-fd-line" /></div>)}</div>
      </div>}
      {index === 1 && <><div className="sc-fd-box sc-fd-box-a"><small>Text region</small></div><div className="sc-fd-box sc-fd-box-b"><small>Component group</small></div><div className="sc-fd-scan" /></>}
    </div>
    <div className="sc-fd-badge"><Symbol index={index} />{["Your idea, ready to begin", "Find components and relationships", "Readable, editable source", "Preview. Refine. Export."][index]}</div>
  </div>;
}

export default function FeatureSpotlight({ onStart, isProcessing = false }) {
  const [active, setActive] = useState(0);
  const tabs = useRef([]);
  const bottom = useRef(null);
  const id = useId();

  // Content remains visible by default. Only an initially offscreen CTA gets
  // a one-time reveal, avoiding the hide-after-paint flicker of many observers.
  useEffect(() => {
    const node = bottom.current;
    if (!node || !window.IntersectionObserver || window.matchMedia("(prefers-reduced-motion: reduce)").matches || node.getBoundingClientRect().top < window.innerHeight) return;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        node.classList.add("sc-fd-scroll-in");
        observer.disconnect();
      }
    }, { threshold: 0.25 });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  function handleTabKey(event, index) {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % FEATURES.length;
    else if (event.key === "ArrowLeft") next = (index + FEATURES.length - 1) % FEATURES.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = FEATURES.length - 1;
    else return;
    event.preventDefault();
    setActive(next);
    tabs.current[next]?.focus();
  }

  return <section className="sc-fd" aria-labelledby={`${id}-heading`}>
    <style>{STYLES}</style>
    <header className="sc-fd-head">
      <span className="sc-fd-kicker">The Sketch2Code workflow</span>
      <h1 id={`${id}-heading`}>From a first sketch.<br />To your next interface.</h1>
      <p>Explore the four steps connecting your wireframe to an editable React interface. Select a step to take a closer look.</p>
    </header>
    <div className="sc-fd-stage">
      {FEATURES.map((feature, index) => <div key={feature.label} className="sc-fd-panel" role="tabpanel" id={`${id}-panel-${index}`} aria-labelledby={`${id}-tab-${index}`} hidden={active !== index} tabIndex={0}>
        <div className="sc-fd-copy">
          <span className="sc-fd-kicker">0{index + 1} / {feature.label}</span>
          <h2>{feature.title}</h2><p>{feature.description}</p>
          <span className="sc-fd-detail">{feature.detail}</span>
        </div>
        <Illustration index={index} />
      </div>)}
    </div>
    <div className="sc-fd-dock-wrap">
      <div className="sc-fd-dock" role="tablist" aria-label="Explore the Sketch2Code workflow">
        {FEATURES.map((feature, index) => <button type="button" key={feature.label} ref={node => { tabs.current[index] = node; }} className="sc-fd-tab" role="tab" id={`${id}-tab-${index}`} aria-selected={active === index} aria-controls={`${id}-panel-${index}`} tabIndex={active === index ? 0 : -1} onClick={() => setActive(index)} onKeyDown={event => handleTabKey(event, index)}><Symbol index={index} /><span>{feature.label}</span></button>)}
      </div>
    </div>
    <div className="sc-fd-bottom" ref={bottom}>
      <p>Illustrations show the workflow, not actual detection results.</p>
      {typeof onStart === "function" && <button type="button" className="sc-fd-start" onClick={onStart} disabled={isProcessing}>Get Started <span aria-hidden="true">↗</span></button>}
    </div>
  </section>;
}
