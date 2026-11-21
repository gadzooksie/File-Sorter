#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
s=512
im=Image.new('RGBA',(s,s),(0,0,0,0))
d=ImageDraw.Draw(im)
d.rounded_rectangle((12,12,500,500),radius=106,fill=(18,26,41,255))
d.rounded_rectangle((85,146,420,382),radius=32,fill=(55,134,151,255))
d.rounded_rectangle((81,122,275,180),radius=18,fill=(77,177,177,255))
d.rounded_rectangle((91,183,415,390),radius=25,fill=(73,161,180,255))
d.line([(160,267),(270,267),(270,245)],fill=(245,250,255,255),width=29,joint='curve')
d.polygon([(272,285),(234,238),(308,238)],fill=(245,250,255,255))
d.arc((178,209,347,375),50,260,fill=(255,255,255,240),width=16)
im.save(Path(__file__).parent/'file-sorter.png')
