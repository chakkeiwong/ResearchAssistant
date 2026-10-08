#!/usr/bin/env python3
"""Render every PDF page and create four-page contact sheets for inspection."""
from pathlib import Path
import subprocess
from PIL import Image,ImageOps,ImageDraw
DOC=Path(__file__).resolve().parents[1]
OUT=DOC/'build/rendered';OUT.mkdir(parents=True,exist_ok=True)
subprocess.run(['pdftoppm','-png','-scale-to','1250',str(DOC/'salespitch_cashflow_fx.pdf'),str(OUT/'page')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
pages=sorted(OUT.glob('page-*.png'))
for start in range(0,len(pages),4):
    selected=pages[start:start+4]
    canvas=Image.new('RGB',(1800,2600),'#c5c5c5')
    draw=ImageDraw.Draw(canvas)
    for k,p in enumerate(selected):
        img=Image.open(p).convert('RGB')
        img=ImageOps.contain(img,(880,1250))
        x=(k%2)*900+10;y=(k//2)*1300+25
        canvas.paste(img,(x,y));draw.text((x,y-18),f'PDF page {start+k+1}',fill='black')
    canvas.save(OUT/f'contact-{start//4+1:02d}.jpg',quality=90)
print(f'Rendered {len(pages)} pages; {(len(pages)+3)//4} contact sheets in {OUT}')
