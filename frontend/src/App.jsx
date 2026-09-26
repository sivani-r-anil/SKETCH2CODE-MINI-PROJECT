import { useEffect, useMemo, useState } from "react"
import Editor from "@monaco-editor/react"
import * as Babel from "@babel/standalone"

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
const scriptLiteral = (value) => JSON.stringify(value).replace(/</g, "\\u003c")

function downloadFile(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const link = document.createElement("a")
  link.href = url
  link.download = name
  link.click()
  URL.revokeObjectURL(url)
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

      setProcessedImage(data.processed_filename)
      setDetections(data.detections || [])
      setOcrTexts(data.ocr_texts || [])
      setMappedComponents(data.mapped_components || [])
      setDiagnostics(data)

      const code = data.generated_code || ""
      setGeneratedCode(code)
      setEditableCode(code)

      setMessage("Conversion complete. Compare the preview with your wireframe.")
    } catch (error) {
      console.error(error)
      setMessage(`Upload failed: ${error.message}`)
    } finally {
      setIsProcessing(false)
    }
  }

  const previewDocument = useMemo(() => buildPreviewDocument(preview), [preview])
  const [previewWidth, setPreviewWidth] = useState("1280")
  const selectedTheme = editableCode.match(/data-sketch-theme=["'](light|dark|blue)["']/)?.[1] || "light"
  const canChangeTheme = /data-sketch-theme=["'](light|dark|blue)["']/.test(editableCode)
    && editableCode.includes("--s2c-page")
  const changeTheme = (theme) => {
    // Modify Monaco's current buffer, preserving user edits and layout.
    setEditableCode(code => code.replace(/data-sketch-theme=["'](light|dark|blue)["']/, `data-sketch-theme="${theme}"`))
  }
  const hasResults = Boolean(generatedCode)

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">

      {/* NAVBAR */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Sketch<span className="text-blue-600">2Code</span>
            </h1>
            <p className="text-xs text-slate-500">
              AI-Driven Wireframe to React
            </p>
          </div>

          <div className="hidden sm:flex items-center gap-2 text-sm text-slate-500">
            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            React + Tailwind
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-10">

        {/* HERO */}
        <section className="text-center max-w-3xl mx-auto mb-10">
          <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-sm font-medium mb-4">
            AI-Powered UI Generation
          </div>

          <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            Turn your wireframe into
            <span className="text-blue-600"> React code</span>
          </h2>

          <p className="text-slate-600 text-lg">
            Upload a hand-drawn or digital wireframe and generate
            editable React components with an interactive live preview.
          </p>
        </section>

        {/* UPLOAD CARD */}
        <section className="max-w-3xl mx-auto bg-white border border-slate-200 rounded-2xl shadow-sm p-6 mb-10">

          <label
            htmlFor="wireframe-upload"
            className="block border-2 border-dashed border-slate-300 rounded-xl p-8 text-center cursor-pointer hover:border-blue-500 hover:bg-blue-50/40 transition"
          >
            <div className="text-4xl mb-3">⌁</div>

            <p className="font-semibold text-slate-800">
              {image ? image.name : "Choose your wireframe"}
            </p>

            <p className="text-sm text-slate-500 mt-1">
              PNG, JPG or JPEG
            </p>

            <span className="inline-block mt-4 bg-slate-100 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium">
              Browse Image
            </span>

            <input
              id="wireframe-upload"
              type="file"
              accept="image/png,image/jpeg"
              disabled={isProcessing}
              onChange={handleImageChange}
              className="hidden"
            />
          </label>

          {image && (
            <button
              onClick={uploadImage}
              disabled={isProcessing}
              className="mt-5 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white py-3 rounded-xl font-semibold transition"
            >
              {isProcessing
                ? "Analyzing Wireframe..."
                : "Generate React UI"}
            </button>
          )}

          {message && (
            <div
              className={`mt-4 text-sm text-center rounded-lg p-3 ${
                message.includes("failed")
                  ? "bg-red-50 text-red-700"
                  : "bg-slate-50 text-slate-600"
              }`}
            >
              {message}
            </div>
          )}
        </section>

        {/* IMAGE COMPARISON */}
        {image && (
          <section className="grid md:grid-cols-2 gap-6 mb-10">

            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200">
                <h3 className="font-semibold">Original Wireframe</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Uploaded design
                </p>
              </div>

              <div className="h-80 p-5 flex items-center justify-center bg-slate-50">
                <img
                  src={originalUrl}
                  alt="Original wireframe"
                  className="max-w-full max-h-full object-contain rounded-lg"
                />
              </div>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-200">
                <h3 className="font-semibold">Processed Wireframe</h3>
                <p className="text-xs text-slate-500 mt-1">
                  OpenCV preprocessing result
                </p>
              </div>

              <div className="h-80 p-5 flex items-center justify-center bg-slate-50">
                {processedImage ? (
                  <img
                    src={`${API_BASE}/uploads/${processedImage}`}
                    alt="Processed wireframe"
                    className="max-w-full max-h-full object-contain rounded-lg"
                  />
                ) : (
                  <p className="text-sm text-slate-400">
                    Processed image will appear here
                  </p>
                )}
              </div>
            </div>

          </section>
        )}

        {/* MAIN WORKSPACE */}
        {hasResults && (
          <>
            <section className="mb-4">
              <div>
                <h2 className="text-2xl font-bold">
                  Generated Workspace
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                  Edit the generated React code and see changes instantly.
                </p>
              </div>
            </section>

            <section className="grid gap-6 mb-8">

              {/* CODE */}
              <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-200 flex justify-between items-center">
                  <div>
                    <h3 className="font-semibold">
                      React Code
                    </h3>
                    <p className="text-xs text-slate-500">
                      Editable JSX
                    </p>
                  </div>

                  <button className="text-xs bg-blue-50 text-blue-700 px-3 py-2 rounded-full" onClick={() => downloadFile("GeneratedPage.jsx", editableCode, "text/javascript")}>Download JSX</button>
                </div>

                <Editor
                  height="520px"
                  defaultLanguage="javascript"
                  value={editableCode}
                  onChange={(value) =>
                    setEditableCode(value || "")
                  }
                  theme="vs-dark"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    wordWrap: "on",
                    padding: { top: 16 },
                  }}
                />
              </div>

              {/* PREVIEW */}
              <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-200 flex flex-wrap gap-3 justify-between items-center">
                  <div>
                    <h3 className="font-semibold">
                      Live Preview
                    </h3>
                    <p className="text-xs text-slate-500">
                      Interactive generated interface
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-sm">
                    <label>Theme <select aria-label="Generated interface theme" value={selectedTheme} disabled={!canChangeTheme} onChange={event => changeTheme(event.target.value)} className="border rounded-lg p-2 disabled:opacity-50">
                      <option value="light">Light</option><option value="dark">Dark</option><option value="blue">Blue</option>
                    </select></label>
                    <label>Viewport <select aria-label="Preview viewport" value={previewWidth} onChange={event => setPreviewWidth(event.target.value)} className="border rounded-lg p-2">
                      <option value="1280">Desktop · 1280 px</option><option value="768">Tablet · 768 px</option><option value="390">Mobile · 390 px</option><option value="auto">Fit available width</option>
                    </select></label>
                    <button disabled={Boolean(preview.error)} className="text-blue-700 disabled:opacity-50" onClick={() => downloadFile("GeneratedPage.html", previewDocument, "text/html")}>Download HTML</button>
                  </div>
                </div>

                {preview.error && <p role="alert" className="p-4 text-sm text-red-700 bg-red-50 whitespace-pre-wrap">Preview error: {preview.error}</p>}
                <p className="px-5 py-2 text-xs text-slate-500">Select a viewport to check responsive layouts. Scroll horizontally when the selected width exceeds the available space. Preview and HTML export require an internet connection.</p>
                {!canChangeTheme && <p className="px-5 py-2 text-xs text-amber-800">Theme selection requires the generated theme attribute and tokens in the editor.</p>}
                <div className="overflow-auto bg-slate-100">
                <iframe
                  title="Live Preview"
                  sandbox="allow-scripts"
                  className="block mx-auto h-[760px] bg-white border-0"
                  srcDoc={previewDocument}
                  style={{ width: previewWidth === "auto" ? "100%" : Number(previewWidth), minWidth: previewWidth === "auto" ? undefined : Number(previewWidth) }}
                />
                </div>
              </div>

            </section>

            {/* PROCESSING DETAILS */}
            <details className="bg-white border border-slate-200 rounded-2xl shadow-sm mb-10">
              <summary className="cursor-pointer px-6 py-5 font-semibold">
                Processing Details
                <span className="ml-2 text-sm font-normal text-slate-500">
                  YOLO · OCR · Layout Reconstruction
                </span>
              </summary>

              {diagnostics && <div className="border-t border-slate-200 p-6 space-y-4">
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <span>Completed in {diagnostics.duration_seconds}s</span>
                  <button className="text-blue-700 underline" onClick={() => downloadFile("pipeline-trace.json", JSON.stringify(diagnostics, null, 2), "application/json")}>Download pipeline trace</button>
                  <select aria-label="Detection view" className="border rounded-lg p-2" value={detectionView} onChange={event => setDetectionView(event.target.value)}>
                    <option value="original_detections">YOLO: original image</option>
                    <option value="processed_detections">YOLO: processed image</option>
                    <option value="mapped_components">After mapping and corrections</option>
                  </select>
                </div>
                {diagnostics.warnings?.map((warning, i) => <p key={i} className="text-sm text-amber-800 bg-amber-50 rounded-lg p-3">{warning}</p>)}
                <DetectionOverlay imageUrl={originalUrl} items={diagnostics[detectionView] || []} />
              </div>}

              <div className="border-t border-slate-200 p-6 grid md:grid-cols-3 gap-6">

                <div>
                  <h4 className="font-semibold mb-3">
                    Detected Components
                  </h4>

                  <div className="space-y-2">
                    {detections.map((item, index) => (
                      <div
                        key={index}
                        className="flex justify-between text-sm bg-slate-50 px-3 py-2 rounded-lg"
                      >
                        <span>{item.class}</span>
                        <span className="text-slate-500">
                          {item.confidence}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-3">
                    Extracted Text
                  </h4>

                  <div className="space-y-2">
                    {ocrTexts.map((item, index) => (
                      <div
                        key={index}
                        className="text-sm bg-slate-50 px-3 py-2 rounded-lg"
                      >
                        {item.text}
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-3">
                    Mapped Components
                  </h4>

                  <div className="space-y-2">
                    {mappedComponents.map((item, index) => (
                      <div
                        key={index}
                        className="text-sm bg-slate-50 px-3 py-2 rounded-lg"
                      >
                        <span className="font-medium">
                          {item.class}
                        </span>

                        <p className="text-xs text-slate-500 mt-1">{item.source} {item.original_class ? ` · corrected from ${item.original_class}` : ""}</p>
                        <p className="text-xs text-slate-500 mt-1">
                          {item.texts?.length
                            ? item.texts.join(", ")
                            : "No text matched"}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </details>
          </>
        )}

      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-6 py-5 text-center text-sm text-slate-500">
          Sketch2Code · AI-Driven Wireframe to React Code Synthesizer
        </div>
      </footer>

    </div>
  )
}

function DetectionOverlay({ imageUrl, items }) {
  const [size, setSize] = useState({ width: 1, height: 1 })
  return <div className="relative max-w-xl mx-auto">
    <img src={imageUrl} alt="Wireframe with component bounds" className="w-full" onLoad={event => setSize({ width: event.target.naturalWidth, height: event.target.naturalHeight })} />
    <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox={`0 0 ${size.width} ${size.height}`}>
      {items.map((item, i) => <g key={i}>
        <rect x={item.x1} y={item.y1} width={item.x2-item.x1} height={item.y2-item.y1} fill="none" stroke={item.source === "ocr" ? "#047857" : "#dc2626"} strokeWidth="3" />
        <text x={item.x1} y={Math.max(18, item.y1-5)} fontSize="18" fill="#991b1b" stroke="white" strokeWidth="3" paintOrder="stroke">{item.class} {item.confidence}</text>
      </g>)}
    </svg>
  </div>
}

export default App