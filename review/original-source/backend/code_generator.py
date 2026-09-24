import html

def escape_attr(val):
    if not val:
        return ""
    return html.escape(val, quote=True).replace('"', '&quot;')


def generate_component(component):
    component_class = component.get("class", "")
    texts = component.get("texts", [])
    raw_text = " ".join(texts).strip() if texts else ""
    safe_text = escape_attr(raw_text)
    lower_text = raw_text.lower()

    # Only convert text to Button if it was NOT already detected as Heading, Subheading, or Label
    if component_class not in ["Heading", "Subheading", "Label"]:
        if lower_text in ["submit", "sign in", "sign up", "register"]:
            component_class = "Button"
        elif lower_text == "login" and component_class == "Textbox":
            # Only turn 'login' into a button if it was misdetected as a Textbox (like the hatched box)
            component_class = "Button"
        elif any(k in lower_text for k in ["enter", "email", "password", "username"]):
            if "password" in lower_text:
                component_class = "Password box"
            else:
                component_class = "Textbox"

    if component_class == "Heading":
        return f'<h1 className="text-3xl font-extrabold text-gray-900 tracking-tight text-center mb-6">{safe_text or "Heading"}</h1>'

    elif component_class == "Subheading":
        return f'<h2 className="text-base font-semibold text-gray-700 text-center mb-4">{safe_text or "Subheading"}</h2>'

    elif component_class == "Button":
        return f'<button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg shadow transition-colors text-center">{safe_text or "Button"}</button>'

    elif component_class == "Textbox":
        return f'<input type="text" placeholder="{safe_text or "Enter text..."}" className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-gray-800 focus:ring-2 focus:ring-blue-500 focus:outline-none shadow-sm" />'

    elif component_class == "Password box":
        return f'<input type="password" placeholder="{safe_text or "••••••••"}" className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-gray-800 focus:ring-2 focus:ring-blue-500 focus:outline-none shadow-sm" />'

    elif component_class == "Label":
        return f'<label className="text-sm font-semibold text-gray-700 block mb-1">{safe_text or "Label"}</label>'

    elif component_class == "Check Box":
        label_markup = f'<span className="text-sm text-gray-700 font-medium">{safe_text}</span>' if safe_text else ""
        return f'<label className="inline-flex items-center gap-2 cursor-pointer">{label_markup}<input type="checkbox" className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500" /></label>'

    elif component_class == "Link":
        return f'<a href="#" className="text-sm text-blue-600 hover:text-blue-800 hover:underline">{safe_text or "Link"}</a>'

    elif component_class == "Paragraph":
        return f'<p className="text-sm text-gray-600 text-center leading-relaxed mt-2">{safe_text or "Paragraph text"}</p>'

    else:
        return f'<div className="text-gray-700 text-center">{safe_text or component_class}</div>'


def _render_row_list(rows, code_lines):
    for row in rows:
        components = row.get("components", [])
        if not components:
            continue

        if len(components) == 1:
            code_lines.append('        <div className="w-full mb-4">')
            code_lines.append(f"          {generate_component(components[0])}")
            code_lines.append("        </div>")
        else:
            code_lines.append('        <div className="flex flex-wrap items-center justify-between gap-3 w-full mb-4">')
            for component in components:
                code_lines.append('          <div className="flex-1 min-w-[120px]">')
                code_lines.append(f"            {generate_component(component)}")
                code_lines.append("          </div>")
            code_lines.append("        </div>")


def generate_react_code(layout):
    code_lines = []

    code_lines.append("function GeneratedPage() {")
    code_lines.append("  return (")
    code_lines.append('    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 sm:p-6">')

    is_multi = layout.get("mode") == "multi" and bool(layout.get("right"))

    if is_multi:
        code_lines.append('      <div className="w-full max-w-5xl bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8 grid grid-cols-1 md:grid-cols-2 gap-8 items-start">')
        code_lines.append('        <div className="flex flex-col">')
        _render_row_list(layout.get("left", []), code_lines)
        code_lines.append("        </div>")
        code_lines.append('        <div className="flex flex-col">')
        _render_row_list(layout.get("right", []), code_lines)
        code_lines.append("        </div>")
    else:
        code_lines.append('      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8 flex flex-col">')
        single_rows = layout.get("rows") or layout.get("left", [])
        _render_row_list(single_rows, code_lines)

    code_lines.append("      </div>")
    code_lines.append("    </div>")
    code_lines.append("  );")
    code_lines.append("}")
    code_lines.append("")
    code_lines.append("export default GeneratedPage;")

    return "\n".join(code_lines)