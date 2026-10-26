"""Original SVG villains and trophy badges for the second Ninja Maths chapter."""
from pathlib import Path
from html import escape
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'app'))
from ninja_content import VILLAINS
PALETTES=['#6d9745','#72884f','#8a8947','#96734c','#698d80','#7d8e9c','#665082','#78bcca','#b56142','#5f79b4']
TOKENS=[
 '<path d="M70 95 35 55 48 115M130 95l35-40-13 60" fill="#99c05c"/>',
 '<path d="M48 110 62 55h76l14 55Z" fill="#9ba6af"/><path d="m75 55 25-27 25 27" fill="#d3ae55"/>',
 '<path d="m65 115 12-55 14 55m18 0 14-55 12 55" fill="#fff0c6"/>',
 '<path d="M65 58h70v62l-35 28-35-28Z" fill="#d2ad52"/><path d="m100 75 12 20-12 22-12-22Z" fill="#6f8991"/>',
 '<path d="m57 135 26-73 25 9-23 74Z" fill="#82553d"/><path d="m70 89 36 12" stroke="#d2aa6b" stroke-width="8"/>',
 '<path d="m100 40 34 43-10 52H76L66 83Z" fill="#98f2d6"/><path d="m100 40-9 95m9-95 14 95" fill="none" stroke="#e5fff3" stroke-width="4"/>',
 '<path d="m100 40 12 28 32-8-12 28 20 19-33 3-19 30-19-30-33-3 20-19-12-28 32 8Z" fill="#d1b85e"/>',
 '<path d="m50 120-5-60 35 27 20-47 20 47 35-27-5 60Z" fill="#b4eeff"/>',
 '<path d="M65 122V80q0-17 13-10V54q10-15 17 2V48q12-12 16 5v5q14-14 20 0v40l-9 28Z" fill="#c98843"/>',
 '<path d="M100 37q64 39 33 87l-33 25-33-25Q36 76 100 37Z" fill="#75b5dc"/><path d="m100 45-16 40 16-7-9 38 29-49-18 8Z" fill="#fff0a6"/>',
]
def svg(title,body):
 return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 240" role="img"><title>'+escape(title)+'</title>'+body+'</svg>'
def main():
 folder=HERE/'app/static/ninja/enemies';folder.mkdir(parents=True,exist_ok=True)
 for i,((name,trophy),color,token) in enumerate(zip(VILLAINS,PALETTES,TOKENS),11):
  dragon=i==20;giant=i in (15,16,18,19);horns=i>=13
  body='<ellipse cx="100" cy="225" rx="68" ry="10" fill="#273542" opacity=".15"/>'
  if dragon:body+='<path d="m65 165-60-86 56 15 13-43 25 99m36 15 60-86-56 15-13-43-25 99" fill="#648cbf" stroke="#354963" stroke-width="4"/>'
  body+=f'<path d="M60 140Q35 160 35 192l22 7 18-33m65-26q25 20 25 52l-22 7-18-33" fill="{color}" stroke="#354354" stroke-width="5"/>'
  body+=f'<path d="M65 135h70l17 76-30 10-22-31-22 31-30-10Z" fill="{color}" stroke="#354354" stroke-width="5"/>'
  body+='<path d="m61 190 78-30v24l-78 26Z" fill="#4c4d62"/><circle cx="100" cy="185" r="10" fill="#f0cc73"/>'
  body+=f'<path d="M57 73 17 50l20 57 27 7m79-41 40-23-20 57-27 7" fill="{color}" stroke="#354354" stroke-width="4"/>' if i<16 else ''
  if horns:body+='<path d="M60 73Q23 41 45 20q0 28 33 38m62 15q37-32 15-53 0 28-33 38" fill="#e2d0a3" stroke="#59616d" stroke-width="4"/>'
  body+=f'<rect x="{48 if giant else 57}" y="48" width="{104 if giant else 86}" height="103" rx="{24 if i==16 else 40}" fill="{color}" stroke="#354354" stroke-width="5"/>'
  body+='<path d="m66 84 23 8m45-8-23 8" stroke="#354354" stroke-width="8" stroke-linecap="round"/><ellipse cx="79" cy="103" rx="9" ry="12" fill="#fff2b6"/><ellipse cx="121" cy="103" rx="9" ry="12" fill="#fff2b6"/><circle cx="81" cy="104" r="4"/><circle cx="119" cy="104" r="4"/><path d="M77 128q23-12 46 0" fill="none" stroke="#354354" stroke-width="5"/>'
  if i in (13,14):body+='<path d="m72 128 7-21 8 20m26 0 8-20 7 21" fill="#fff2cf"/>'
  if i==12:body+='<path d="M52 79 68 35h64l16 44Z" fill="#abb6be" stroke="#354354" stroke-width="4"/>'
  if i==17:body+='<path d="m47 90 18-54h70l18 54-18 67-25-14V94H90v49l-25 14Z" fill="#514466" stroke="#d2b86a" stroke-width="4"/>'
  if i==18:body+='<path d="m48 58 5-35 28 21 19-37 19 37 28-21 5 35Z" fill="#c5f4ff"/>'
  if i==19:body+='<path d="M65 63q-20-30 1-53 0 27 18 24L105 5l6 31 28-20q-4 22-8 38Z" fill="#f4ad49"/>'
  (folder/f'{i}.svg').write_text(svg(name,body),'utf-8')
  badge=f'<circle cx="100" cy="100" r="81" fill="{color}" stroke="#d6b660" stroke-width="8"/><circle cx="100" cy="100" r="69" fill="#fff7df"/>'+token+'<path d="M52 187h96l14 24H38Z" fill="#6e5269"/><rect x="75" y="175" width="50" height="26" rx="7" fill="#dec47d"/>'
  (folder/f'{i}-trophy.svg').write_text(svg(trophy,badge),'utf-8')
if __name__=='__main__':main()
