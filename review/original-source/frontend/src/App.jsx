import { useState } from "react"
import Editor from "@monaco-editor/react"
import * as Babel from "@babel/standalone"

function App() {
  const [message, setMessage] = useState("")
  const [image, setImage] = useState(null)
  const [processedImage, setProcessedImage] = useState(null)
  const [detections, setDetections] = useState([])
  const [ocrTexts, setOcrTexts] = useState([])
  const [mappedComponents, setMappedComponents] = useState([])
  const [isProcessing, setIsProcessing] = useState(false)

  const [layout, setLayout] = useState({
    left: [],
    right: [],
  })

  const [generatedCode, setGeneratedCode] = useState("")
  const [editableCode, setEditableCode] = useState("")

  const generatePreview = () => {
    try {
      if (!editableCode) return ""

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

      return transformedCode
    } catch (error) {
      console.error("Babel error:", error)
      return ""
    }
  }

  const handleImageChange = (event) => {
    const file = event.target.files[0]

    if (file) {
      setImage(file)
      setProcessedImage(null)
      setDetections([])
      setOcrTexts([])
      setMappedComponents([])
      setMessage("")
      setLayout({ left: [], right: [] })
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
      const response = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error("Backend request failed")
      }

      const data = await response.json()

      setProcessedImage(data.processed_filename)
      setDetections(data.detections || [])
      setOcrTexts(data.ocr_texts || [])
      setMappedComponents(data.mapped_components || [])
      setLayout(data.layout || { left: [], right: [] })

      const code = data.generated_code || ""
      setGeneratedCode(code)
      setEditableCode(code)

      setMessage("Wireframe converted successfully.")
    } catch (error) {
      console.error(error)
      setMessage("Upload failed. Please check the FastAPI server.")
    } finally {
      setIsProcessing(false)
    }
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
              accept="image/*"
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
                  src={URL.createObjectURL(image)}
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
                    src={`http://127.0.0.1:8000/uploads/${processedImage}`}
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

            <section className="grid lg:grid-cols-2 gap-6 mb-8">

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

                  <span className="text-xs bg-blue-50 text-blue-700 px-3 py-1 rounded-full">
                    JSX
                  </span>
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
                <div className="px-5 py-4 border-b border-slate-200 flex justify-between items-center">
                  <div>
                    <h3 className="font-semibold">
                      Live Preview
                    </h3>
                    <p className="text-xs text-slate-500">
                      Interactive generated interface
                    </p>
                  </div>

                  <div className="flex gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-red-400"></span>
                    <span className="w-2.5 h-2.5 rounded-full bg-yellow-400"></span>
                    <span className="w-2.5 h-2.5 rounded-full bg-green-400"></span>
                  </div>
                </div>

                <iframe
                  title="Live Preview"
                  className="w-full h-[520px] bg-white"
                  srcDoc={`
                    <!DOCTYPE html>
                    <html>
                      <head>
                        <meta charset="utf-8" />
                        <script src="https://cdn.tailwindcss.com"></script>
                        <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
                        <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
                      </head>

                      <body style="margin:0;">
                        <div id="status"></div>
                        <div id="root"></div>

                        <script>
                          try {
                            const rawJs =
                              ${JSON.stringify(generatePreview())};

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

                              eval(rawJs);

                              const ComponentToRender =
                                (typeof GeneratedPage !== "undefined"
                                  ? GeneratedPage
                                  : null) ||
                                (typeof App !== "undefined"
                                  ? App
                                  : null);

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
                            document.getElementById("status").innerHTML =
                              "<div style='margin:16px;padding:12px;color:#b91c1c;background:#fee2e2;border-radius:8px;font-family:Arial;'>" +
                              "<b>Preview Error:</b> " +
                              error.message +
                              "</div>";
                          }
                        </script>
                      </body>
                    </html>
                  `}
                />
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

export default App