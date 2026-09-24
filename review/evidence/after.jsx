function GeneratedPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900">
      <section className="wireframe mx-auto w-full bg-white border border-slate-400 rounded-2xl p-6 sm:p-8" style={{maxWidth: 657}}>
        <style>{`
          .wireframe .sketch-row { display:grid; grid-template-columns:repeat(24,minmax(0,1fr)); align-items:center; }
          .wireframe .sketch-cell { min-width:0; overflow-wrap:anywhere; grid-column:var(--start) / span var(--span); }
          @media(max-width:700px) { .wireframe .sketch-row { display:flex; flex-wrap:wrap; gap:12px; } .wireframe .sketch-cell { flex:1 1 max(120px,var(--mobile-width)); } }
        `}</style>
        <div className="sketch-row" style={{marginTop: 0}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <h1 className="text-3xl sm:text-4xl font-bold text-slate-900" style={{textAlign: "center"}}>{"Welcome Back"}</h1>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 15}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <h2 className="text-lg text-slate-600" style={{textAlign: "center"}}>{"Login to your account"}</h2>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 46}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 3, "--mobile-width": "12%"}}>
            <label htmlFor={"component-2"} className="block text-sm font-medium text-slate-800">{"Email"}</label>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 14}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <input id={"component-2"} type="email" placeholder={"Enter your email"} aria-label={"Email"} className="w-full min-w-0 border border-slate-400 rounded-lg px-4 py-3 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 50}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 5, "--mobile-width": "21%"}}>
            <label htmlFor={"component-3"} className="block text-sm font-medium text-slate-800">{"Password"}</label>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 11}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <input id={"component-3"} type="password" placeholder={"Enter your password"} aria-label={"Password"} className="w-full min-w-0 border border-slate-400 rounded-lg px-4 py-3 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 27}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 9, "--mobile-width": "38%"}}>
            <label className="inline-flex items-center gap-2 text-sm cursor-pointer"><input type="checkbox" name="choice" className="w-4 h-4 shrink-0" /><span>{"Remember me"}</span></label>
          </div>
          <div className="sketch-cell" style={{"--start": 18, "--span": 7, "--mobile-width": "29%"}}>
            <a href="#" className="text-sm text-blue-700 underline underline-offset-4">{"Forgot password?"}</a>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 47}}>
          <div className="sketch-cell" style={{"--start": 1, "--span": 24, "--mobile-width": "100%"}}>
            <button type="button" className="w-full border border-slate-500 bg-slate-100 hover:bg-slate-200 rounded-lg px-4 py-3 font-medium">{"Login"}</button>
          </div>
        </div>
        <div className="sketch-row" style={{marginTop: 46}}>
          <div className="sketch-cell" style={{"--start": 6, "--span": 10, "--mobile-width": "42%"}}>
            <p className="text-sm text-slate-600" style={{textAlign: "left"}}>{"Don't have an account?"}</p>
          </div>
          <div className="sketch-cell" style={{"--start": 16, "--span": 4, "--mobile-width": "17%"}}>
            <a href="#" className="text-sm text-blue-700 underline underline-offset-4">{"Sign UP"}</a>
          </div>
        </div>
      </section>
    </main>
  );
}

export default GeneratedPage;