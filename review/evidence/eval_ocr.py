
import json
import re
import collections
from pathlib import Path
from jiwer import cer, wer

# Manually prepared reference text for six wireframes.
# Verify these transcripts against the original images
# before reporting the metrics as final results.

GT = {
    14: """Sign Up Create your account Full Name Email Password Confirm Password Sign Up Already have an account? Login""",

    15: """Login Welcome back! Please login to your account. Email or Username Password Forgot password? Login Don't have an account? Sign up""",

    16: """Sketch2Code Home Features How It Works About Contact Login Turn Your Sketches into Real Code Sketch2Code is an AI-powered platform that converts your hand-drawn wireframes into clean, editable React code instantly. Get Started Our Features Everything you need in one place. Easy to Use Clean and simple interface for better experience. Accurate Component Detection Detects UI components from sketches using AI. Editable Code Output Generate clean React code with live preview. 2026 Sketch2Code. All rights reserved.""",

    17: """StudentPortal Home Students Departments Reports About Admin Student Details Search students... Add Student No. Name Roll No. Department Email Phone Action 1 Aarav Mehta S001 Computer Science aarav@example.com 9876543210 2 Diya Nair S002 Information Technology diya@example.com 9876543211 3 Rohan Kumar S003 Electronics rohan@example.com 9876543212 4 Sneha Thomas S004 Mechanical sneha@example.com 9876543213 5 Vikram Singh S005 Civil vikram@example.com 9876543214 1 2 3""",

    18: """StudentPortal Dashboard Students Projects Tasks Reports Admin Dashboard Welcome back, Admin! 120 Total Students 5 Departments 12 Ongoing Projects 30 Completed Projects 8 Reports Generated 4 Upcoming Deadlines""",

    19: """Sketch2Code Home Features About Contact Logout Sivani sivani@gmail.com Settings Profile Notifications Security Settings Update your preferences. Name Sivani R Email sivani@gmail.com Theme Light Enable email notifications Make my profile public Save Changes"""
}

NAMES = {
    14: "Signup",
    15: "Login",
    16: "Homepage",
    17: "Student Table",
    18: "Dashboard",
    19: "Settings"
}


def tok(text):
    text = text.lower().replace("_", " ").replace("’", "'")
    return re.findall(
        r"[a-z0-9]+(?:'[a-z0-9]+)?(?:@[a-z0-9.]+)?",
        text
    )


def score(pred, truth):
    predicted = collections.Counter(tok(pred))
    expected = collections.Counter(tok(truth))

    matched = sum((predicted & expected).values())

    total_expected = sum(expected.values())
    total_predicted = sum(predicted.values())

    recall = (
        matched / total_expected * 100
        if total_expected else 0
    )

    precision = (
        matched / total_predicted * 100
        if total_predicted else 0
    )

    return round(recall, 2), round(precision, 2)


def normalize(text):
    # Consistent normalization for both reference and OCR output.
    text = text.lower().replace("_", " ").replace("’", "'")
    return " ".join(text.split())


def evaluate_ocr():
    evidence_dir = Path(__file__).resolve().parent

    print("\nSKETCH2CODE - OCR EVALUATION")
    print("=" * 70)

    results = []

    for n, truth in GT.items():

        trace_path = evidence_dir / f"pipeline-trace ({n}).json"

        with open(trace_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw = " ".join(
            str(item["text"])
            for item in data["raw_ocr_texts"]
        )

        processed = " ".join(
            str(item["text"])
            for item in data["ocr_texts"]
        )

        raw_recall, raw_precision = score(raw, truth)
        proc_recall, proc_precision = score(processed, truth)

        reference = normalize(truth)
        raw_text = normalize(raw)
        processed_text = normalize(processed)

        raw_cer = cer(reference, raw_text) * 100
        raw_wer = wer(reference, raw_text) * 100

        proc_cer = cer(reference, processed_text) * 100
        proc_wer = wer(reference, processed_text) * 100

        print(f"\n{NAMES[n]} (Trace {n})")
        print("-" * 50)

        print(f"Raw word recall       : {raw_recall:.2f}%")
        print(f"Processed word recall : {proc_recall:.2f}%")

        print(f"Raw word precision    : {raw_precision:.2f}%")
        print(f"Processed precision   : {proc_precision:.2f}%")

        print(f"Raw CER               : {raw_cer:.2f}%")
        print(f"Processed CER         : {proc_cer:.2f}%")

        print(f"Raw WER               : {raw_wer:.2f}%")
        print(f"Processed WER         : {proc_wer:.2f}%")

        results.append({
            "wireframe": NAMES[n],
            "trace": n,
            "raw_word_recall": raw_recall,
            "processed_word_recall": proc_recall,
            "raw_word_precision": raw_precision,
            "processed_word_precision": proc_precision,
            "raw_cer": round(raw_cer, 2),
            "processed_cer": round(proc_cer, 2),
            "raw_wer": round(raw_wer, 2),
            "processed_wer": round(proc_wer, 2)
        })

    output_path = evidence_dir / "ocr_evaluation_results.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print("\n" + "=" * 70)
    print("Evaluation completed.")
    print(f"Results saved to: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    evaluate_ocr()
