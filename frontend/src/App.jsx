import { useEffect, useMemo, useRef, useState } from "react"
import Editor from "@monaco-editor/react"
import * as Babel from "@babel/standalone"
import JSZip from "jszip"
import "./App.css"

const THEMES = [
  ["light", "Light"], ["dark", "Dark"], ["blue", "Blue"],
  ["purple-gradient", "Purple Gradient"], ["ocean-gradient", "Ocean Gradient"],
  ["sunset-gradient", "Sunset Gradient"],
]
const THEME_ATTRIBUTE = /data-sketch-theme\s*=\s*(["'])(light|dark|blue|purple-gradient|ocean-gradient|sunset-gradient)\1/

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
const scriptLiteral = (value) => JSON.stringify(value).replace(/</g, "\\u003c")

function downloadFile(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const link = document.createElement("a")
  link.href = url
  link.download = name
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function projectFiles(editorCode) {
  if (!editorCode.trim()) throw new Error("Generate or enter React code before exporting.")
  // Validate the actual editor buffer. Never export the old backend response.
  const parsed = Babel.transform(editorCode, {
    presets: [["react", { runtime: "automatic" }]],
    sourceType: "module", ast: true, code: false,
  })
  const supportedImports = new Set(["react", "react-dom", "react-dom/client", "react/jsx-runtime", "react/jsx-dev-runtime"])
  let hasDefault = false
  const globalsNeeded = new Set()
  Babel.transform(editorCode, {
    presets: [["react", { runtime: "classic" }]], sourceType: "module",
    plugins: [() => ({ visitor: {
      ImportDeclaration(path) {
        if (!supportedImports.has(path.node.source.value)) {
          throw new Error(`Export cannot bundle ${path.node.source.value}. Keep the component self-contained or remove this import.`)
        }
      },
      ExportNamedDeclaration(path) {
        if (path.node.source) throw new Error("Export cannot bundle re-exported external files.")
        if (path.node.specifiers.some(item => item.exported?.name === "default")) hasDefault = true
      },
      ExportAllDeclaration() { throw new Error("Export cannot bundle external source files.") },
      ExportDefaultDeclaration() { hasDefault = true },
      ReferencedIdentifier(path) {
        const name = path.node.name
        if (["React", "useState", "useEffect", "useRef", "useMemo"].includes(name) && !path.scope.hasBinding(name)) globalsNeeded.add(name)
      },
      CallExpression(path) {
        if (path.node.callee.type === "Import" || path.node.callee.name === "require") {
          throw new Error("Dynamic imports and require() need additional project files and cannot be exported automatically.")
        }
      },
    } })],
  })
  let appCode = editorCode
  // The iframe supplies these React names globally. Supply equivalent imports
  // in the standalone project without changing the user's component body.
  if (globalsNeeded.size) {
    const names = [...globalsNeeded].map(name => name === "React" ? "default as React" : name)
    appCode = `import { ${names.join(", ")} } from "react"\n` + appCode
  }
  if (!hasDefault) {
    const declarations = parsed.ast.program.body
    const names = declarations.flatMap(node => node.type === "FunctionDeclaration" ? [node.id?.name]
      : node.type === "VariableDeclaration" ? node.declarations.map(item => item.id.name) : [])
    const entry = names.includes("GeneratedPage") ? "GeneratedPage" : names.includes("App") ? "App" : null
    if (!entry) throw new Error("The component needs a default export, or a GeneratedPage/App declaration.")
    appCode += `\nexport default ${entry};\n`
  }
  return {
    "package.json": JSON.stringify({
      name: "sketch2code-project", version: "1.0.0", private: true, type: "module",
      scripts: { dev: "vite", build: "vite build", preview: "vite preview" },
      dependencies: { react: "^19.2.8", "react-dom": "^19.2.8" },
      devDependencies: { vite: "^8.2.2", "@vitejs/plugin-react": "^6.1.0", tailwindcss: "3.4.17", postcss: "^8.5.6", autoprefixer: "^10.4.21" },
      engines: { node: "^20.19.0 || >=22.12.0" },
    }, null, 2) + "\n",
    "index.html": '<!doctype html>\n<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><title>Sketch2Code Project</title></head><body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body></html>\n',
    "src/main.jsx": 'import React from "react"\nimport { createRoot } from "react-dom/client"\nimport App from "./App.jsx"\nimport "./index.css"\n\ncreateRoot(document.getElementById("root")).render(<App />)\n',
    "src/App.jsx": appCode,
    "src/index.css": '@tailwind base;\n@tailwind components;\n@tailwind utilities;\n\nbody { margin: 0; }\n',
    "vite.config.js": 'import { defineConfig } from "vite"\nimport react from "@vitejs/plugin-react"\n\nexport default defineConfig({ plugins: [react()] })\n',
    "tailwind.config.js": 'export default { content: ["./index.html", "./src/**/*.{js,jsx}"], theme: { extend: {} }, plugins: [] }\n',
    "postcss.config.js": 'export default { plugins: { tailwindcss: {}, autoprefixer: {} } }\n',
    "README.md": '# Generated Sketch2Code project\n\nUse Node.js 20.19+ or 22.12+. Run `npm install`, then `npm run dev`.\n\nThis project contains the editor code captured when Download ZIP was clicked, including its selected theme and embedded image crops. Tailwind is built locally; no Sketch2Code backend is required. External image URLs or APIs added manually still need their original services.\n',
  }
}

function buildPreviewDocument(preview) {
  return `
                    <!DOCTYPE html>
                    <html>
                      <head>
                        <meta charset="utf-8" />
                        <meta name="viewport" content="width=device-width, initial-scale=1" />
                        <script src="https://cdn.tailwindcss.com"></script>
                        <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
                        <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
                      </head>

                      <body style="margin:0;">
                        <div id="status"></div>
                        <div id="root"></div>

                        <script>
                          function showError(error) {
                            const status = document.getElementById("status");
                            status.style.cssText = "margin:16px;padding:12px;color:#b91c1c;background:#fee2e2;border-radius:8px;font-family:Arial;white-space:pre-wrap;";
                            status.textContent = "Preview error: " + (error.message || error);
                          }
                          window.addEventListener("error", event => showError(event.error || event.message));
                          window.addEventListener("unhandledrejection", event => showError(event.reason));
                          try {
                            const compileError = ${scriptLiteral(preview.error)};
                            if (compileError) throw new Error(compileError);
                            if (!window.tailwind) throw new Error("Tailwind CSS could not load. Check your connection and reload.");
                            if (!window.React || !window.ReactDOM) throw new Error("Preview libraries could not load. Check your internet connection and reload.");
                            const rawJs =
                              ${scriptLiteral(preview.code)};

                            if (!rawJs) {
                              document.getElementById("status").innerHTML =
                                "<div style='padding:20px;color:#64748b;font-family:Arial;'>Waiting for valid code...</div>";
                            } else {
                              const {
                                useState,
                                useEffect,
                                useRef,
                                useMemo
                              } = React;

                              const ComponentToRender = new Function("React", "useState", "useEffect", "useRef", "useMemo",
                                rawJs + "\\nreturn typeof GeneratedPage !== 'undefined' ? GeneratedPage : (typeof App !== 'undefined' ? App : null);"
                              )(React, useState, useEffect, useRef, useMemo);

                              if (!ComponentToRender) {
                                throw new Error(
                                  "GeneratedPage component not found."
                                );
                              }

                              const root =
                                ReactDOM.createRoot(
                                  document.getElementById("root")
                                );

                              root.render(
                                React.createElement(ComponentToRender)
                              );
                            }
                          } catch (error) {
                            showError(error);
                          }
                        </script>
                      </body>
                    </html>
                  `
}

function App() {
  const [appStage, setAppStage] = useState("landing")
  const [message, setMessage] = useState("")
  const [image, setImage] = useState(null)
  const [processedImage, setProcessedImage] = useState(null)
  const [detections, setDetections] = useState([])
  const [ocrTexts, setOcrTexts] = useState([])
  const [mappedComponents, setMappedComponents] = useState([])
  const [isProcessing, setIsProcessing] = useState(false)

  const [diagnostics, setDiagnostics] = useState(null)
  const [originalUrl, setOriginalUrl] = useState("")
  const [detectionView, setDetectionView] = useState("original_detections")
  useEffect(() => () => { if (originalUrl) URL.revokeObjectURL(originalUrl) }, [originalUrl])

  const [generatedCode, setGeneratedCode] = useState("")
  const [editableCode, setEditableCode] = useState("")
  const [isExporting, setIsExporting] = useState(false)
  const [exportMessage, setExportMessage] = useState("")

  const exportProject = async () => {
    const currentCode = editableCode
    setIsExporting(true)
    setExportMessage("")
    try {
      const files = projectFiles(currentCode)
      const zip = new JSZip()
      const folder = zip.folder("sketch2code-project")
      Object.entries(files).forEach(([name, contents]) => folder.file(name, contents))
      const blob = await zip.generateAsync({ type: "blob", compression: "DEFLATE" })
      downloadFile("sketch2code-project.zip", blob, "application/zip")
      setExportMessage("ZIP created from the editor code at the time you clicked Download ZIP.")
    } catch (error) {
      setExportMessage(`Export failed: ${error.message}`)
    } finally {
      setIsExporting(false)
    }
  }

  const preview = useMemo(() => {
    try {
      if (!editableCode) return { code: "", error: "" }

      let cleanedCode = editableCode.replace(
        /import\s+[\s\S]*?from\s+['"][^'"]+['"];?/g,
        ""
      )

      cleanedCode = cleanedCode.replace(
        /export\s+default\s+[A-Za-z0-9_]+\s*;?/g,
        ""
      )

      const transformedCode = Babel.transform(cleanedCode, {
        presets: [["react", { runtime: "classic" }]],
        sourceType: "script",
      }).code

      return { code: transformedCode, error: "" }
    } catch (error) {
      console.error("Babel error:", error)
      return { code: "", error: error.message }
    }
  }, [editableCode])

  const handleImageChange = (event) => {
    const file = event.target.files[0]

    if (file) {
      setImage(file)
      setOriginalUrl(URL.createObjectURL(file))
      setProcessedImage(null)
      setDetections([])
      setOcrTexts([])
      setMappedComponents([])
      setMessage("")
      setDiagnostics(null)
      setGeneratedCode("")
      setEditableCode("")
      setExportMessage("")
    }
  }

  const uploadImage = async () => {
    if (!image) {
      setMessage("Please select a wireframe first.")
      return
    }

    const formData = new FormData()
    formData.append("file", image)

    setIsProcessing(true)
    setMessage("Analyzing wireframe...")

    try {
      const response = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const problem = await response.json().catch(() => ({}))
        throw new Error(problem.detail || "Backend request failed")
      }

      const data = await response.json()
      const code = data.generated_code || ""
      if (!code.trim()) throw new Error("No React code was returned. Please retry or choose another image.")

      setProcessedImage(data.processed_filename)
      setDetections(data.detections || [])
      setOcrTexts(data.ocr_texts || [])
      setMappedComponents(data.mapped_components || [])
      setDiagnostics(data)

      setGeneratedCode(code)
      setEditableCode(code)

      setMessage("Conversion complete. Compare the preview with your wireframe.")
      setAppStage("workspace")
    } catch (error) {
      console.error(error)
      setMessage(`Upload failed: ${error.message}`)
    } finally {
      setIsProcessing(false)
    }
  }

  const previewDocument = useMemo(() => buildPreviewDocument(preview), [preview])
  const [previewWidth, setPreviewWidth] = useState("1280")
  const selectedTheme = editableCode.match(THEME_ATTRIBUTE)?.[2] || "light"
  const canChangeTheme = THEME_ATTRIBUTE.test(editableCode)
    && editableCode.includes("--s2c-page")
  const changeTheme = (theme) => {
    // Modify Monaco's current buffer, preserving user edits and layout.
    if (!THEMES.some(([value]) => value === theme)) return
    setEditableCode(code => code.replace(THEME_ATTRIBUTE, `data-sketch-theme="${theme}"`))
  }
  const hasResults = Boolean(generatedCode)

  const imageDialog = useRef(null)
  const mainRef = useRef(null)
  const [imageView, setImageView] = useState("original")
  const navigate = (stage) => {
    if (!isProcessing) setAppStage(stage)
  }
  const openImage = (view) => {
    setImageView(view)
    imageDialog.current?.showModal()
  }
  useEffect(() => {
    mainRef.current?.focus({ preventScroll: true })
    window.scrollTo({ top: 0, left: 0, behavior: "instant" })
  }, [appStage])

  return (
    <div className="sc-app" id="top">
      <a href="#main-content" className="sc-button sc-skip-link" onClick={event => { event.preventDefault(); mainRef.current?.focus() }}>Skip to main content</a>
      <header className="sc-header">
        <div className="sc-shell sc-header-inner">
          <a className="sc-brand" href="#top" aria-label="Sketch2Code home" aria-disabled={isProcessing} onClick={event => { event.preventDefault(); navigate("landing") }}>
            <span className="sc-brand-mark" aria-hidden="true">&lt;/&gt;</span>
            <span>Sketch<em>2</em>Code</span>
          </a>
          <span className="sc-header-note">From an idea on paper to an interface.</span>
          <div className="sc-toolbar">
            {appStage === "workspace" ? <button className="sc-button sc-button-small" onClick={() => navigate("upload")}>← New Wireframe</button> : <>
              {appStage === "upload" && <button className="sc-button sc-button-quiet sc-button-small" disabled={isProcessing} onClick={() => navigate("landing")}>← Back to Home</button>}
              {(appStage === "landing" || hasResults) && <button className="sc-button sc-button-small" disabled={isProcessing} onClick={() => navigate(hasResults ? "workspace" : "upload")}>Open Workspace <Icon name="arrow" /></button>}
            </>}
          </div>
        </div>
      </header>

      <main className="sc-shell sc-stage" id="main-content" ref={mainRef} tabIndex={-1} key={appStage}>
        {appStage === "landing" && <>
        <section className="sc-hero" aria-labelledby="hero-title">
          <div className="sc-hero-grid">
            <div className="sc-hero-copy">
              <p className="sc-eyebrow"><span className="sc-dot" />Sketch. Analyze. Create.</p>
              <h1 id="hero-title">Turn Wireframes Into <span>React Interfaces.</span></h1>
              <p className="sc-hero-description">Bring hand-drawn and digital wireframes into the browser. Computer vision and AI turn your sketch into editable React + Tailwind code, with a live preview.</p>
              <div className="sc-hero-actions">
                <button onClick={() => navigate("upload")} className="sc-button sc-button-primary">Get Started <Icon name="arrow" /></button>
                <span className="sc-muted">Your sketch. Your code.</span>
              </div>
              <p className="sc-hero-footnote">Built with YOLO, EasyOCR & spatial layout reconstruction.</p>
            </div>
            <HeroVisual />
          </div>
        </section>

        <div className="sc-steps" aria-label="How Sketch2Code works">
          {[
            ["Upload a wireframe", "Start with a hand-drawn or digital sketch."],
            ["Analyze with AI", "Detect components, text and spatial relationships."],
            ["Generate React UI", "Translate the structure into React + Tailwind."],
            ["Edit & export", "Refine the code, preview and download."],
          ].map(([title, description], index) => <div className="sc-step" key={title}>
            <span className="sc-step-number">0{index + 1}</span>
            <div><h3>{title}</h3><p>{description}</p></div>
          </div>)}
        </div>

        </>}

        {appStage === "upload" && <div className="sc-workspace sc-upload-screen" style={{ maxWidth: 900, marginInline: "auto" }}>
          <section className="sc-section" aria-labelledby="upload-title">
            <div className="sc-section-heading">
              <div><p className="sc-eyebrow">The workspace</p><h2 id="upload-title">Upload your wireframe</h2><p>Analyze the components, text and spatial structure of your hand-drawn or digital wireframe.</p></div>
            </div>
            <div className="sc-panel sc-upload" aria-busy={isProcessing}>
              <div className="sc-dropzone">
                <div className="sc-upload-copy">
                  <span className="sc-upload-symbol"><Icon name="upload" /></span>
                  <div><h3>Choose your wireframe</h3><p>PNG, JPG or JPEG · Keep lines and text clearly visible.</p></div>
                </div>
                <label className="sc-button" htmlFor="wireframe-upload">
                  <Icon name="image" />{image ? "Change Image" : "Browse Image"}
                  <input id="wireframe-upload" type="file" accept="image/png,image/jpeg" disabled={isProcessing} onChange={handleImageChange} className="sc-file-input" />
                </label>
              </div>
              <div className="sc-upload-actions">
                <p className="sc-file-name">{image ? <>Selected: <strong>{image.name}</strong></> : "No image selected yet."}</p>
                <button className="sc-button sc-button-primary" disabled={!image || isProcessing} onClick={uploadImage}>
                  {isProcessing ? <><span className="sc-spinner" aria-hidden="true" />Analyzing Wireframe…</> : <>Analyze Wireframe <Icon name="arrow" /></>}
                </button>
              </div>
              {message && <p role="status" className={`sc-status ${message.includes("failed") ? "sc-status-error" : ""}`}>{message}</p>}
              {isProcessing && <div className="sc-analysis-status">
                <p className="sc-muted">Detecting interface components, reading text and reconstructing the layout.</p>
                <div className="sc-pipeline" aria-label="Pipeline overview, not live stage progress">
                {["Preprocessing", "Detection", "OCR", "Mapping", "Layout", "React generation" ].map(stage => <span key={stage}>{stage}</span>)}
                </div>
                <p className="sc-muted">Pipeline overview — individual stage progress is not reported.</p>
              </div>}
            </div>
          </section>

          {image && <section className="sc-section sc-panel" aria-labelledby="original-title">
            <div className="sc-panel-header">
              <div><h3 id="original-title">Selected Wireframe</h3><p className="sc-file-name">{image.name}</p></div>

            </div>
            <div className="sc-original"><img src={originalUrl} alt="Selected wireframe to analyze" style={{ maxHeight: 320 }} /></div>
          </section>}

        </div>}

        {appStage === "workspace" && hasResults && <div className="sc-workspace sc-result-screen">
          <section className="sc-section sc-panel" aria-label="Input wireframe reference">
            <div className="sc-panel-header">
              <div><h3>Input Wireframe</h3><p className="sc-file-name">{image?.name}</p></div>
              <div className="sc-toolbar">
                <button className="sc-button sc-button-small" disabled={!originalUrl} onClick={() => openImage("original")}><Icon name="image" />View Original</button>
                <button className="sc-button sc-button-small" disabled={!processedImage} onClick={() => openImage("processed")}><Icon name="image" />View Processed Image</button>
              </div>
            </div>
          </section>
            <section className="sc-section" aria-labelledby="code-title">
              <div className="sc-section-heading">
                <div><p className="sc-eyebrow">Make it yours</p><h2 id="code-title">Generated React code</h2><p>Edit the JSX below. Your preview and downloads use this editor's current code.</p></div>
                <span className="sc-result-meta">React + Tailwind CSS</span>
              </div>
              <div className="sc-panel">
                <div className="sc-panel-header">
                  <div className="sc-editor-label"><Icon name="code" /><h3>React Code</h3><code>GeneratedPage.jsx</code></div>
                  <div className="sc-toolbar">
                    <button className="sc-button sc-button-small" onClick={() => downloadFile("GeneratedPage.jsx", editableCode, "text/javascript")}>Download JSX</button>
                    <button className="sc-button sc-button-small" disabled={isExporting || !editableCode.trim() || Boolean(preview.error)} onClick={exportProject}><Icon name="download" />{isExporting ? "Creating ZIP…" : "Download ZIP"}</button>
                  </div>
                </div>
                {exportMessage && <p role="status" className="sc-export-message">{exportMessage}</p>}
                <div className="sc-editor">
                  <Editor height="520px" defaultLanguage="javascript" value={editableCode} onChange={value => setEditableCode(value || "")} theme="vs-dark"
                    options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: "on", padding: { top: 16 }, automaticLayout: true }} />
                </div>
              </div>
            </section>

            <section className="sc-section" aria-labelledby="preview-title">
              <div className="sc-section-heading"><div><p className="sc-eyebrow">See it take shape</p><h2 id="preview-title">Live preview</h2><p>Explore themes, check responsive layouts and interact with the generated interface.</p></div></div>
              <div className="sc-panel">
                <div className="sc-panel-header">
                  <div><h3>Generated Interface</h3><p>Updates from Monaco as you edit.</p></div>
                  <div className="sc-toolbar">
                    <label className="sc-control-label">Theme
                      <select aria-label="Generated interface theme" className="sc-control" value={selectedTheme} disabled={!canChangeTheme} onChange={event => changeTheme(event.target.value)}>
                        {THEMES.map(([value, label]) => <option key={value} value={value} disabled={!editableCode.includes(value)}>{label}</option>)}
                      </select>
                    </label>
                    <label className="sc-control-label">Viewport
                      <select aria-label="Preview viewport" className="sc-control" value={previewWidth} onChange={event => setPreviewWidth(event.target.value)}>
                        <option value="1280">Desktop · 1280 px</option><option value="768">Tablet · 768 px</option><option value="390">Mobile · 390 px</option><option value="auto">Fit available width</option>
                      </select>
                    </label>
                    <button className="sc-button sc-button-small" disabled={Boolean(preview.error)} onClick={() => downloadFile("GeneratedPage.html", previewDocument, "text/html")}>Download HTML</button>
                  </div>
                </div>
                {preview.error && <p role="alert" className="sc-preview-error">Preview error: {preview.error}</p>}
                <p className="sc-preview-note">Scroll horizontally when the selected viewport exceeds the available space. Preview and HTML export require an internet connection.</p>
                {!canChangeTheme && <p className="sc-preview-note">Theme selection requires the generated theme attribute and tokens in the editor.</p>}
                <div className="sc-preview-scroll">
                  <iframe title="Live Preview" sandbox="allow-scripts" className="sc-preview-frame" srcDoc={previewDocument}
                    style={{ width: previewWidth === "auto" ? "100%" : Number(previewWidth), minWidth: previewWidth === "auto" ? undefined : Number(previewWidth) }} />
                </div>
              </div>
            </section>

            <details className="sc-panel sc-diagnostics">
              <summary>Processing Details<span>YOLO · OCR · Mapping · Layout Reconstruction</span></summary>
              <div className="sc-diagnostic-body">
                {diagnostics && <>
                  <div className="sc-toolbar">
                    <span className="sc-muted">Completed in {diagnostics.duration_seconds}s</span>
                    <button className="sc-button sc-button-small" onClick={() => downloadFile("pipeline-trace.json", JSON.stringify(diagnostics, null, 2), "application/json")}>Download pipeline trace</button>
                    <select aria-label="Detection view" className="sc-control" value={detectionView} onChange={event => setDetectionView(event.target.value)}>
                      <option value="original_detections">YOLO: original image</option><option value="processed_detections">YOLO: processed image</option><option value="mapped_components">After mapping and corrections</option>
                    </select>
                  </div>
                  {diagnostics.warnings?.map((warning, i) => <p key={i} className="sc-warning">{warning}</p>)}
                  <DetectionOverlay imageUrl={originalUrl} items={diagnostics[detectionView] || []} />
                </>}
                <div className="sc-diagnostic-grid">
                  <div><h4>Detected Components ({detections.length})</h4><div className="sc-diagnostic-scroll"><table><thead><tr><th>Component</th><th>Confidence</th></tr></thead><tbody>
                    {detections.map((item, i) => <tr key={i}><td>{item.class}</td><td>{item.confidence}</td></tr>)}
                  </tbody></table></div></div>
                  <div><h4>Extracted Text ({ocrTexts.length})</h4><div className="sc-diagnostic-scroll"><table><thead><tr><th>Text</th></tr></thead><tbody>
                    {ocrTexts.map((item, i) => <tr key={i}><td>{item.text}</td></tr>)}
                  </tbody></table></div></div>
                  <div><h4>Mapped Components ({mappedComponents.length})</h4><div className="sc-diagnostic-scroll"><table><thead><tr><th>Component / source</th><th>Matched text</th></tr></thead><tbody>
                    {mappedComponents.map((item, i) => <tr key={i}><td>{item.class}<p className="sc-muted">{item.source}{item.original_class ? ` · corrected from ${item.original_class}` : ""}</p></td><td>{item.texts?.length ? item.texts.join(", ") : "No text matched"}</td></tr>)}
                  </tbody></table></div></div>
                </div>
              </div>
            </details>
        </div>}
      </main>

      <footer className="sc-footer"><div className="sc-shell sc-footer-inner">
        <span className="sc-brand">Sketch<em>2</em>Code</span>
        <p>AI-Driven Wireframe-to-React Code Synthesizer · MCA Mini Project</p>
      </div></footer>

      <dialog ref={imageDialog} className="sc-modal" aria-labelledby="image-dialog-title" onClick={event => {
        if (event.target !== event.currentTarget) return
        const rect = event.currentTarget.getBoundingClientRect()
        if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) event.currentTarget.close()
      }}>
        <div className="sc-modal-header"><div><h2 id="image-dialog-title">{imageView === "original" ? "Original Wireframe" : "Preprocessed Wireframe"}</h2><p>{imageView === "original" ? "Your uploaded design reference." : "OpenCV output used by the existing analysis pipeline."}</p></div>
          <button autoFocus className="sc-button sc-button-small" onClick={() => imageDialog.current?.close()} aria-label="Close wireframe image"><Icon name="close" />Close</button>
        </div>
        <div className="sc-modal-body">{imageView === "original" ? (originalUrl && <img src={originalUrl} alt="Original uploaded wireframe" />) : (processedImage && <img src={`${API_BASE}/uploads/${processedImage}`} alt="OpenCV preprocessed wireframe" />)}</div>
      </dialog>
    </div>
  )
}

function Icon({ name }) {
  const paths = {
    arrow: "M4 12h16m-6-6 6 6-6 6",
    upload: "M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5",
    download: "M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4",
    code: "m8 6-6 6 6 6m8-12 6 6-6 6m-3-14-2 16",
    image: "M3 3h18v18H3zM3 17l5-5 4 4 3-3 6 6M15 7h.01",
    close: "m6 6 12 12M6 18 18 6",
  }
  return <svg className="sc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.code} /></svg>
}

function HeroVisual() {
  return <div className="sc-visual" role="img" aria-label="Illustration of a wireframe becoming React code and a generated interface">
    <div className="sc-scene" aria-hidden="true">
      <svg className="sc-connectors" viewBox="0 0 500 450"><path d="M130 140C230 120 230 300 310 320M240 340C400 390 450 240 400 190" /></svg>
      <div className="sc-window sc-window-wire">
        <div className="sc-window-bar"><i /><i /><i /><span>01 / wireframe</span></div>
        <div className="sc-window-body"><div className="sc-wire-nav"><b /><span /></div><div className="sc-wire-title" /><div className="sc-wire-line" /><div className="sc-wire-line" /><div className="sc-wire-box"><Icon name="image" /></div></div>
      </div>
      <div className="sc-analysis-chip"><Icon name="code" />Component analysis</div>
      <div className="sc-window sc-window-code">
        <div className="sc-window-bar"><i /><i /><i /><span>02 / GeneratedPage.jsx</span></div>
        <div className="sc-window-body">
          <span className="sc-code-line"><small>1</small><em>function</em>{" Interface() {"}</span>
          <span className="sc-code-line"><small>2</small>{"  "}<em>return</em>{" ("}</span>
          <span className="sc-code-line"><small>3</small>{"    <"}<b>main</b>{" className="}<em>"grid"</em>{">"}</span>
          <span className="sc-code-line"><small>4</small>{"      <"}<b>Header</b>{" />"}</span>
          <span className="sc-code-line"><small>5</small>{"      <"}<b>Content</b>{" />"}</span>
          <span className="sc-code-line"><small>6</small>{"    </"}<b>main</b>{">"}</span>
          <span className="sc-code-line"><small>7</small>{"  );"}</span>
          <span className="sc-code-line"><small>8</small>{"}"}</span>
        </div>
      </div>
      <div className="sc-window sc-window-result">
        <div className="sc-window-bar"><i /><i /><i /><span>03 / live interface</span></div>
        <div className="sc-window-body">
          <div className="sc-mini-nav"><span className="sc-mini-logo" /><span className="sc-mini-menu"><i /><i /><i /></span></div>
          <div className="sc-mini-heading">An idea.<br />An interface.</div><div className="sc-mini-copy" /><div className="sc-mini-copy" /><div className="sc-mini-cta" />
          <div className="sc-mini-cards">{[1, 2, 3].map(i => <div className="sc-mini-card" key={i}><i /><span /></div>)}</div>
        </div>
      </div>
      <span className="sc-visual-caption">wireframe → code → interface</span>
    </div>
  </div>
}

function DetectionOverlay({ imageUrl, items }) {
  const [size, setSize] = useState({ width: 1, height: 1 })
  return <div className="sc-overlay">
    <img src={imageUrl} alt="Wireframe with component bounds"  onLoad={event => setSize({ width: event.target.naturalWidth, height: event.target.naturalHeight })} />
    <svg aria-hidden="true" style={{ pointerEvents: "none" }} viewBox={`0 0 ${size.width} ${size.height}`}>
      {items.map((item, i) => <g key={i}>
        <rect x={item.x1} y={item.y1} width={item.x2-item.x1} height={item.y2-item.y1} fill="none" stroke={item.source === "ocr" ? "#047857" : "#dc2626"} strokeWidth="3" />
        <text x={item.x1} y={Math.max(18, item.y1-5)} fontSize="18" fill="#991b1b" stroke="white" strokeWidth="3" paintOrder="stroke">{item.class} {item.confidence}</text>
      </g>)}
    </svg>
  </div>
}

export default App
