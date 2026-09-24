function GeneratedPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900">
      <section className="wireframe mx-auto w-full bg-white border border-slate-400 rounded-2xl p-6 sm:p-8" style={{maxWidth: 485}}>
        <style>{`
          .wireframe .sketch-row { display:grid; grid-template-columns:repeat(24,minmax(0,1fr)); align-items:center; }
          .wireframe .sketch-cell { min-width:0; overflow-wrap:anywhere; grid-column:var(--start) / span var(--span); }
          @media(max-width:700px) { .wireframe .sketch-row { display:flex; flex-wrap:wrap; gap:12px; } .wireframe .sketch-cell { flex:1 1 max(120px,var(--mobile-width)); } }
        `}</style>
        <div className="sketch-row" style={{marginTop: 0}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <textarea id={"component-0"} aria-label={"Text area"} placeholder={""} rows={4} className="w-full border border-slate-400 rounded-lg p-3" />
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 0}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <h2 className="text-lg text-slate-600" style={{textAlign: "center"}}>{"HEADER"}</h2>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 0}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <h2 className="text-lg text-slate-600" style={{textAlign: "center"}}>{"(first thing YOu want users t0 see)"}</h2>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 64}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <p className="text-sm text-slate-600" style={{textAlign: "center"}}>{"BODY"}</p>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 1}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <p className="text-sm text-slate-600" style={{textAlign: "center"}}>{"(followed by the content}"}</p>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 64}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <textarea id={"component-6"} aria-label={"Text area"} placeholder={""} rows={4} className="w-full border border-slate-400 rounded-lg p-3" />
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 0}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <p className="text-sm text-slate-600" style={{textAlign: "center"}}>{"FOOTER"}</p>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 0}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <p className="text-sm text-slate-600" style={{textAlign: "center"}}>{"(typically the less important stutf)"}</p>
          </div>
        </div>
      </section>
    </main>
  );
}

export default GeneratedPage;