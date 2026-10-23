"""Render the locally generated engineering SVG primitives with Pillow; no HTML or network execution."""
from pathlib import Path
import hashlib, json, xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
base=Path(__file__).resolve().parents[1] / 'review'
source=base/'requested-support.svg'
raw=source.read_bytes()
root=ET.fromstring(raw)
assert root.attrib['viewBox']=='0 0 1320 940'
image=Image.new('RGB',(1320,940),'white')
draw=ImageDraw.Draw(image)
classes={'title':(25,True),'sub':(16,False),'small':(13,False),'case':(18,True)}
for item in root:
    tag=item.tag.rsplit('}',1)[-1]; a=item.attrib
    if tag=='style': continue
    if tag=='rect':
        x,y,w,h=(float(a.get(k,0)) for k in ('x','y','width','height'))
        draw.rectangle((x,y,x+w,y+h),fill=None if a.get('fill')=='none' else a.get('fill'),outline=None if a.get('stroke') in (None,'none') else a['stroke'],width=max(1,round(float(a.get('stroke-width',1)))))
    elif tag=='line':
        draw.line(tuple(float(a[k]) for k in ('x1','y1','x2','y2')),fill=a['stroke'],width=max(1,round(float(a.get('stroke-width',1)))))
    elif tag=='circle':
        x,y,r=(float(a[k]) for k in ('cx','cy','r'))
        draw.ellipse((x-r,y-r,x+r,y+r),fill=a['fill'])
    elif tag=='text':
        size,bold=classes[a['class']]
        font=ImageFont.truetype('C:/Windows/Fonts/'+('arialbd.ttf' if bold else 'arial.ttf'),size)
        draw.text((float(a['x']),float(a['y'])),''.join(item.itertext()),fill='#17232d',font=font,anchor='ls')
    else: raise ValueError('Unsupported generated SVG primitive '+tag)
output=base/'requested-support.png'
image.save(output)
receipt={'source_svg_sha256':hashlib.sha256(raw).hexdigest(),'png_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'dimensions':[1320,940],'method':'Pillow rasterization of generated rect/line/circle/text engineering SVG; no browser or HTML execution','not_a_terminal_screenshot':True}
(base/'render-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt))
