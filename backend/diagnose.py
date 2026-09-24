"""Run the real pipeline on any PNG/JPEG and save inspectable intermediate data."""
import argparse
import json
from pathlib import Path
import cv2
from main import run_pipeline


def overlay(image_path, components, output):
    image = cv2.imread(str(image_path))
    for c in components:
        x1, y1, x2, y2 = [int(c[k]) for k in ('x1','y1','x2','y2')]
        color = (40,150,0) if c.get('source') == 'ocr' else (0,0,210)
        cv2.rectangle(image,(x1,y1),(x2,y2),color,2)
        cv2.putText(image,f"{c['class']} {c.get('confidence', '')}",
                    (x1,max(16,y1-4)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,1)
    cv2.imwrite(str(output), image)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=Path)
    parser.add_argument('--output',type=Path,default=Path('diagnostics'))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    result=run_pipeline(args.image,args.output/'processed.png')
    (args.output/'trace.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (args.output/'GeneratedPage.jsx').write_text(result['generated_code'],encoding='utf-8')
    for key in ['original_detections','processed_detections','mapped_components']:
        overlay(args.image,result[key],args.output/f'{key}.png')
    print(f"Raw original: {len(result['original_detections'])}; raw processed: {len(result['processed_detections'])}; mapped: {len(result['mapped_components'])}")
    print(f"Saved trace, JSX and overlays to {args.output.resolve()}")
    for warning in result['warnings']: print('Review:',warning)


if __name__=='__main__':
    main()
