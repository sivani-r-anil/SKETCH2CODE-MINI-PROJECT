function GeneratedPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900">
      <section className="wireframe mx-auto w-full bg-white border border-slate-400 rounded-2xl p-6 sm:p-8" style={{maxWidth: 400}}>
        <style>{`
          .wireframe .sketch-row { display:grid; grid-template-columns:repeat(24,minmax(0,1fr)); align-items:center; }
          .wireframe .sketch-cell { min-width:0; overflow-wrap:anywhere; grid-column:var(--start) / span var(--span); }
          @media(max-width:700px) { .wireframe .sketch-row { display:flex; flex-wrap:wrap; gap:12px; } .wireframe .sketch-cell { flex:1 1 max(120px,var(--mobile-width)); } }
        `}</style>
        <div className="sketch-row" style={{marginTop: 0}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <h1 className="text-3xl sm:text-4xl font-bold text-slate-900" style={{textAlign: "center"}}>{"LOGIN"}</h1>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 46}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 4, "--mobile-width": "17%"}}>
            <label htmlFor={"component-2"} className="block text-sm font-medium text-slate-800">{"Email"}</label>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 9}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <input id={"component-2"} type="text" placeholder={""} aria-label={"Email"} className="w-full min-w-0 border border-slate-400 rounded-lg px-4 py-3 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 20}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 8, "--mobile-width": "33%"}}>
            <label htmlFor={"component-3"} className="block text-sm font-medium text-slate-800">{"Password"}</label>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 10}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <input id={"component-3"} type="password" placeholder={""} aria-label={"Password"} className="w-full min-w-0 border border-slate-400 rounded-lg px-4 py-3 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 11}}>
          <div className="sketch-cell" style={{"--start": 2, "--span": 8, "--mobile-width": "33%"}}>
            <label className="inline-flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" name="choice" className="w-4 h-4 shrink-0" /><span>{"Remember"}</span></label>
          </div>
          <div className="sketch-cell" style={{"--start": 14, "--span": 11, "--mobile-width": "46%"}}>
            <p className="text-sm text-slate-600" style={{textAlign: "left"}}>{"Forgot password?"}</p>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 28}}>
          <div className="sketch-cell" style={{"--start": 6, "--span": 15, "--mobile-width": "100%"}}>
            <button type="button" className="w-full border border-slate-500 bg-slate-100 hover:bg-slate-200 rounded-lg px-4 py-3 font-medium">{"SUBMIT"}</button>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 36}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <p className="text-sm text-slate-600" style={{textAlign: "center"}}>{"Create account"}</p>
          </div>
        </div>
      </section>
    </main>
  );
}

export default GeneratedPage;