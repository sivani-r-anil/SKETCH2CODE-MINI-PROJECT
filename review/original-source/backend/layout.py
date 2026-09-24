def reconstruct_layout(components):
    if not components:
        return {
            "mode": "single",
            "page": {"width": 0, "height": 0},
            "rows": [],
            "left": [],
            "right": []
        }

    # Work with copies so original detection data is not modified[cite: 3]
    components = [c.copy() for c in components]

    # --- 1. ADD PHANTOM BOX FILTER HERE ---
    filtered = []
    for c in components:
        has_text = bool(c.get("texts") and len(c["texts"]) > 0)
        # Drop low-confidence textless textboxes and labels[cite: 3]
        if not has_text and c.get("class") in ["Textbox", "Label"] and c.get("confidence", 1.0) < 0.25:
            continue
        filtered.append(c)

    components = filtered
    if not components:
        return {
            "mode": "single",
            "page": {"width": 0, "height": 0},
            "rows": [],
            "left": [],
            "right": []
        }
    # --------------------------------------

    # 1. Calculate overall page boundaries[cite: 3]
    min_x = min(c["x1"] for c in components)
    max_x = max(c["x2"] for c in components)
    min_y = min(c["y1"] for c in components)
    max_y = max(c["y2"] for c in components)

    page_width = max_x - min_x
    page_height = max_y - min_y

    if page_width == 0:
        page_width = 1
    if page_height == 0:
        page_height = 1

    page_center_x = min_x + (page_width / 2)

    # 2. Add geometry information to every component[cite: 3]
    for c in components:
        c["center_y"] = (c["y1"] + c["y2"]) / 2
        c["center_x"] = (c["x1"] + c["x2"]) / 2
        c["pixel_width"] = c["x2"] - c["x1"]
        c["pixel_height"] = c["y2"] - c["y1"]

    # --- 2. UPDATE SORTING HERE (Use y1 instead of center_y) ---[cite: 3]
    sorted_components = sorted(
        components,
        key=lambda c: (c["y1"], c["x1"])
    )
    # -----------------------------------------------------------

    # 4. Group components into visual rows FIRST[cite: 3]
    rows = []
    row_threshold = 24

    for comp in sorted_components:
        placed = False
        for row in rows:
            reference_cy = row["reference_cy"]
            if abs(comp["center_y"] - reference_cy) <= row_threshold:
                row["components"].append(comp)
                row["reference_cy"] = (
                    sum(c["center_y"] for c in row["components"])
                    / len(row["components"])
                )
                placed = True
                break

        if not placed:
            rows.append({
                "reference_cy": comp["center_y"],
                "components": [comp]
            })

    # Sort each row left-to-right[cite: 3]
    for row in rows:
        row["components"] = sorted(
            row["components"],
            key=lambda c: c["x1"]
        )

    # 5. Check if layout is truly multi-column[cite: 3]
    multi_element_rows = sum(1 for r in rows if len(r["components"]) > 1)
    is_multi_column = (
        len(rows) > 0 and (multi_element_rows / len(rows)) > 0.6
    )

    # 6. Single-column layout[cite: 3]
    if not is_multi_column:
        formatted_rows = [
            {
                "row": idx,
                "components": row["components"]
            }
            for idx, row in enumerate(rows, start=1)
        ]

        return {
            "mode": "single",
            "page": {
                "width": round(page_width, 2),
                "height": round(page_height, 2)
            },
            "rows": formatted_rows,
            "left": formatted_rows,
            "right": []
        }

    # 7. Multi-column layout[cite: 3]
    left_rows = []
    right_rows = []

    for row in rows:
        row_center = (
            sum(c["center_x"] for c in row["components"])
            / len(row["components"])
        )
        if row_center < page_center_x:
            left_rows.append(row)
        else:
            right_rows.append(row)

    return {
        "mode": "multi",
        "page": {
            "width": round(page_width, 2),
            "height": round(page_height, 2)
        },
        "rows": [],
        "left": [
            {
                "row": idx,
                "components": row["components"]
            }
            for idx, row in enumerate(left_rows, start=1)
        ],
        "right": [
            {
                "row": idx,
                "components": row["components"]
            }
            for idx, row in enumerate(right_rows, start=1)
        ]
    }