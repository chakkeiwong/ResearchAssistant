"""Local CPU OCR of lawfully accessible scanned source copies; no framework/GPU."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / '.localresources/bank-sales-v2-2026-10-08/papers'
os.environ['OMP_THREAD_LIMIT'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

def ocr_image(image):
    output = image.with_suffix('')
    subprocess.run(['tesseract', str(image), str(output), '--psm', '3'],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output.with_suffix('.txt')

for key in ['shumway', 'smith', 'mcfadden', 'froot']:
    folder = BASE / (key + '-ocr')
    folder.mkdir(exist_ok=True)
    subprocess.run(['pdftoppm', '-r', '160', '-png', str(BASE/(key+'.pdf')),
                    str(folder/'page')], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    images = sorted(folder.glob('page-*.png'), key=lambda p: int(p.stem.split('-')[-1]))
    with ThreadPoolExecutor(max_workers=6) as pool:
        texts = list(pool.map(ocr_image, images))
    (BASE/(key+'.txt')).write_text('\n\f\n'.join(p.read_text() for p in texts))
    print(key, len(texts), 'pages OCR complete', flush=True)
