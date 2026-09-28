"""Animated virtual newsroom layout; composited by make_video.py.
The newsroom is AI-generated; the coast is a photograph, not filmed footage.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont, ImageOps
import math, functools


def install(ns):
    global textimg, txt, num, HEADS, CAPS, LABEL, DURS
    for key in ('textimg','txt','num','HEADS','CAPS','LABEL','DURS'):
        globals()[key]=ns[key]

W,H=720,1280
CYAN='#74f4ff'; GOLD='#ffe285'; WHITE='#f2f8ff'; RED='#ff334b'
studio=Image.open('assets/newsroom.jpg').convert('RGB').resize((W,H),Image.Resampling.LANCZOS)
SCENE_IMAGES=[Image.open(f'assets/realistic/scene{i}.jpg').convert('RGB') for i in range(1,7)]
PHOTO_BOX=(38,452,270,466)
PANEL_BOX=(324,452,683,918)
PANEL_CENTER=(PANEL_BOX[0]+PANEL_BOX[2])//2

@functools.lru_cache(maxsize=140)
def extrude(s,size,gold=False):
    mask=textimg(s,size,'white').getchannel('A')
    if mask.width>626:
        mask=mask.resize((626,round(mask.height*626/mask.width)),Image.Resampling.LANCZOS)
    w,h=mask.size; im=Image.new('RGBA',(w+32,h+34))
    shadow=Image.new('RGBA',im.size);shadow.paste((0,0,0,230),(22,25,w+22,h+25),mask)
    im=Image.alpha_composite(im,shadow.filter(ImageFilter.GaussianBlur(6)))
    for z in range(14,0,-1):
        c=(96+z*3,49+z,8,255) if gold else (10,49+z*3,82+z*4,255)
        im.paste(c,(z,z,w+z,h+z),mask)
    # Bevel rim and a vertically shaded metallic face.
    rim=mask.filter(ImageFilter.MaxFilter(3));im.paste((255,250,208,255) if gold else (167,246,255,255),(0,0,w,h),rim)
    face=Image.new('RGBA',(w,h));d=ImageDraw.Draw(face)
    for y in range(h):
        k=y/max(1,h-1)
        if gold:c=(255,int(247-79*k),int(190-130*k),255)
        else:c=(int(253-62*k),int(255-24*k),255,255)
        d.line((0,y,w,y),fill=c)
    face.putalpha(mask);im.alpha_composite(face,(1,1))
    return im

def title(im,s,y,t,delay=0,gold=False,size=54):
    p=max(0,min(1,(t-delay)/.65));ease=1-(1-p)**3
    layer=extrude(s,size,gold)
    scale=.77+.23*ease
    layer=layer.resize((int(layer.width*scale),int(layer.height*scale)),Image.Resampling.BICUBIC)
    if p<1:layer.putalpha(layer.getchannel('A').point(lambda a:int(a*p)))
    im.alpha_composite(layer,(int((W-layer.width)/2+(1-ease)*(-110 if gold else 110)),int(y+30*(1-ease))))

def glass(im,box):
    d=ImageDraw.Draw(im)
    x,y,r,b=box
    d.polygon([(x,y+10),(x+14,y),(r,y),(r,b-10),(r-14,b),(x,b)],fill=(4,17,34,230),outline='#365d74',width=2)
    d.line((x+14,y,r,y),fill=CYAN,width=3)
    d.line((x,b,x+85,b),fill=RED,width=4)

def orbit(im,y,t):
    d=ImageDraw.Draw(im)
    for k in range(3):
        box=(94-k*17,y-k*8,626+k*17,y+80+k*8)
        d.ellipse(box,outline=(36,105,135,210),width=1)
        a=(t*48+k*120)%360
        d.arc(box,a,a+102,fill=CYAN if k%2 else RED,width=3)
    for k in range(8):
        a=t*.6+k*math.pi/4
        x=360+268*math.cos(a);yy=y+40+45*math.sin(a)
        d.ellipse((x-3,yy-3,x+3,yy+3),fill=CYAN)

def slab(im,x,y,w,h,depth=15,color='#123e5c'):
    d=ImageDraw.Draw(im)
    d.polygon([(x+w,y),(x+w+depth,y-depth),(x+w+depth,y+h-depth),(x+w,y+h)],fill='#08253c',outline='#327991')
    d.polygon([(x,y),(x+depth,y-depth),(x+w+depth,y-depth),(x+w,y)],fill='#296580',outline=CYAN)
    d.rectangle((x,y,x+w,y+h),fill=color,outline='#599db4',width=2)

def center_text(im,s,y,size=24,color=WHITE,max_width=320):
    layer=textimg(s,size,color)
    if layer.width>max_width:
        layer=layer.resize((max_width,max(1,round(layer.height*max_width/layer.width))),Image.Resampling.LANCZOS)
    im.alpha_composite(layer,(PANEL_CENTER-layer.width//2,int(y)))

def local_title(im,s,y,t,delay=0,gold=False,size=50):
    p=max(0,min(1,(t-delay)/.55));ease=1-(1-p)**3
    layer=extrude(s,size,gold)
    max_width=PANEL_BOX[2]-PANEL_BOX[0]-38
    if layer.width>max_width:
        layer=layer.resize((max_width,max(1,round(layer.height*max_width/layer.width))),Image.Resampling.LANCZOS)
    scale=.78+.22*ease
    layer=layer.resize((max(1,int(layer.width*scale)),max(1,int(layer.height*scale))),Image.Resampling.BICUBIC)
    if p<1:layer.putalpha(layer.getchannel('A').point(lambda a:int(a*p)))
    im.alpha_composite(layer,(PANEL_CENTER-layer.width//2,int(y+17*(1-ease))))

def photo_window(im,idx,t):
    x,y,w,h=PHOTO_BOX
    progress=max(0,min(1,t/DURS[idx]))
    zoom=1.018+.042*progress
    fx=max(0,min(1,.5+.018*math.sin(t*.36+idx*.8)))
    fy=max(0,min(1,.5+.026*math.sin(t*.28+idx*.6)))
    ow,oh=round(w*zoom),round(h*zoom)
    still=ImageOps.fit(SCENE_IMAGES[idx],(ow,oh),method=Image.Resampling.LANCZOS,centering=(fx,fy))
    still=still.crop(((ow-w)//2,(oh-h)//2,(ow-w)//2+w,(oh-h)//2+h)).convert('RGBA')
    shade=Image.new('RGBA',(w,h));sd=ImageDraw.Draw(shade)
    for j in range(80):
        a=int(205*(j/79)**1.7)
        sd.line((0,h-80+j,w,h-80+j),fill=(1,10,22,a),width=1)
    still=Image.alpha_composite(still,shade)
    mask=Image.new('L',(w,h));ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=17,fill=255)
    still.putalpha(mask)
    glow=Image.new('RGBA',(W,H));gd=ImageDraw.Draw(glow)
    gd.rounded_rectangle((x-2,y-2,x+w+2,y+h+2),radius=20,fill=(65,220,255,100))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14)))
    im.alpha_composite(still,(x,y))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((x,y,x+w,y+h),radius=17,outline='#8af5ff',width=2)
    # Restrained broadcast focus brackets and a moving specular glint keep the still image lively.
    for sx,sy,dx,dy in ((x+9,y+9,1,1),(x+w-9,y+9,-1,1),(x+9,y+h-9,1,-1),(x+w-9,y+h-9,-1,-1)):
        d.line((sx,sy,sx+dx*22,sy),fill='#e6324a',width=3)
        d.line((sx,sy,sx,sy+dy*22),fill='#e6324a',width=3)
    sweep=(t*.24+idx*.19)%1.0
    gx=x+int(18+sweep*(w-36))
    d.line((gx,y+34,gx-34,y+91),fill=(191,255,255,80),width=2)
    label='ఏఐతో రూపొందించిన దృశ్యం'
    badge=textimg(label,16,WHITE)
    if badge.width>w-20:
        badge=badge.resize((w-20,max(1,round(badge.height*(w-20)/badge.width))),Image.Resampling.LANCZOS)
    bx=x+(w-badge.width)//2;by=y+h-31
    d.rounded_rectangle((bx-6,by-4,bx+badge.width+6,by+badge.height+4),radius=7,fill=(2,15,29,224))
    im.alpha_composite(badge,(bx,by))

def panel_base(im,heading):
    glass(im,PANEL_BOX)
    d=ImageDraw.Draw(im)
    txt(im,heading,476,22,CYAN,x=PANEL_BOX[0]+22)
    d.line((PANEL_BOX[0]+22,514,PANEL_BOX[2]-22,514),fill=(70,135,158,180),width=1)
    d.rectangle((PANEL_BOX[0]+22,513,PANEL_BOX[0]+82,516),fill=RED)

def draw_ward_tiles(im,t):
    d=ImageDraw.Draw(im)
    lit=min(120,int(120*max(0,min(1,t/1.65))))
    for k in range(120):
        row,col=divmod(k,10);x=349+col*29;y=700+row*10
        active=k<lit
        c=CYAN if active else '#244256'
        d.polygon([(x,y),(x+22,y),(x+26,y-4),(x+4,y-4)],fill=c)
        d.polygon([(x,y),(x+22,y),(x+22,y+6),(x,y+6)],fill='#267c99' if active else '#182c3c')

def scene(im,idx,t):
    # Every chapter has its own AI-generated, photo-real illustrative still.
    orbit(im,826,t)
    photo_window(im,idx,t)
    if idx==0:
        panel_base(im,'ప్రధాన అప్‌డేట్')
        local_title(im,'120',533,t,.12,True,118)
        center_text(im,'వార్డులు',670,27,GOLD)
        cx=PANEL_CENTER;cy=765
        d=ImageDraw.Draw(im)
        d.ellipse((cx-65,cy-65,cx+65,cy+65),outline='#264f68',width=2)
        p=min(1,t/1.45)
        d.arc((cx-65,cy-65,cx+65,cy+65),210,210+int(285*p),fill=CYAN,width=5)
        d.arc((cx-54,cy-54,cx+54,cy+54),28,28+int(180*p),fill=RED,width=3)
        for k in range(12):
            a=math.radians(k*30+t*22);x=cx+76*math.cos(a);y=cy+76*math.sin(a)
            d.ellipse((x-2,y-2,x+2,y+2),fill=CYAN if k%3 else GOLD)
        center_text(im,'స్థానిక ఎన్నికల సన్నాహాలు',864,21,WHITE)
    elif idx==1:
        panel_base(im,'పరిధి వివరాలు')
        n=min(120,int(120*max(0,min(1,t/1.65))))
        local_title(im,str(n),530,t,0,True,106)
        center_text(im,'మొత్తం వార్డులు',650,24,GOLD)
        draw_ward_tiles(im,t)
        center_text(im,'ఎన్నికల సన్నాహాలు',847,21,WHITE)
    elif idx==2:
        panel_base(im,'సిబ్బందికి శిక్షణ')
        labels=['ఓటర్ల జాబితాలు','పోలింగ్ కేంద్రాలు','సిబ్బంది శిక్షణ']
        d=ImageDraw.Draw(im)
        for j,label in enumerate(labels):
            y=544+j*103
            p=max(0,min(1,(t-.32-j*.45)/.75))
            d.rounded_rectangle((345,y,662,y+79),radius=10,fill=(8,29,48,222),outline='#315870',width=1)
            c=CYAN if p>=.55 else '#356176'
            d.rounded_rectangle((357,y+18,389,y+50),radius=7,fill=c)
            if p>=.55:d.line((363,y+34,371,y+42,383,y+26),fill='#f3ffff',width=3)
            txt(im,label,y+17,22,WHITE,x=400)
            d.rounded_rectangle((357,y+61,650,y+68),radius=3,fill='#1a3447')
            d.rounded_rectangle((357,y+61,357+int(293*p),y+68),radius=3,fill=CYAN if p>=.55 else RED)
        center_text(im,'అవగాహన కార్యక్రమాలు',868,20,GOLD)
    elif idx==3:
        panel_base(im,'రాజకీయ చర్చ')
        center_text(im,'సమావేశంలో ప్రస్తావించినది',552,21,CYAN)
        local_title(im,'ఆశయం మాత్రమే',602,t,.12,True,44)
        center_text(im,'ఎన్నికల ఫలితం కాదు',697,23,WHITE)
        d=ImageDraw.Draw(im)
        d.line((PANEL_BOX[0]+37,739,PANEL_BOX[2]-37,739),fill='#34566b',width=1)
        d.rounded_rectangle((345,769,662,818),radius=8,fill=(155,26,49,228),outline='#ff6578',width=1)
        center_text(im,'నాయకుల ప్రకటన మాత్రమే',781,20,WHITE,300)
        center_text(im,'తుది ఫలితాలు కావు',842,22,GOLD)
    elif idx==4:
        panel_base(im,'అధికారిక షెడ్యూల్')
        d=ImageDraw.Draw(im)
        bx,by,bw,bh=389,548,226,186
        d.rounded_rectangle((bx,by,bx+bw,by+bh),radius=12,fill=(14,46,65,240),outline='#70e7f5',width=2)
        d.rounded_rectangle((bx,by,bx+bw,by+45),radius=11,fill='#e6324a')
        d.rectangle((bx,by+26,bx+bw,by+45),fill='#e6324a')
        for x in (bx+41,bx+bw-52):
            d.rounded_rectangle((x,by-9,x+12,by+15),radius=5,fill='#eefbff')
        for row in range(3):
            for col in range(4):
                x=bx+20+col*49;y=by+65+row*34
                pulse=(t*1.5+row*4+col)%8
                c='#54cadf' if pulse<1.5 else '#34536a'
                d.rounded_rectangle((x,y,x+34,y+23),radius=4,fill=c)
        center_text(im,'నోటిఫికేషన్, తేదీలు',767,22,CYAN)
        center_text(im,'అధికారిక ప్రకటన తర్వాతే',817,20,GOLD)
        center_text(im,'పూర్తి వివరాలు తెలుస్తాయి',853,20,WHITE)
    elif idx==5:
        panel_base(im,'జనసేవతో కలిసుండండి')
        local_title(im,'మీ మాటే ముఖ్యం',548,t,.1,False,43)
        center_text(im,'మీ అభిప్రాయాన్ని పంచుకోండి',627,20,WHITE)
        d=ImageDraw.Draw(im)
        pulse=.5+.5*math.sin(t*3)
        d.rounded_rectangle((350,695,657,772),radius=15,fill='#e92d48',outline='#ff8b9b',width=2)
        # Animated broadcast play/ring mark, not an English-language control label.
        cx=383;cy=733;r=13+int(3*pulse)
        d.ellipse((cx-r,cy-r,cx+r,cy+r),outline='#fff2ee',width=2)
        d.polygon([(cx-3,cy-7),(cx+7,cy),(cx-3,cy+7)],fill='white')
        center_text(im,'సబ్‌స్క్రైబ్ చేయండి',716,23,WHITE,255)
        local_title(im,'జనసేవ న్యూస్',799,t,.45,True,34)
        center_text(im,'ప్రజల కోసం ప్రజల వార్తలు',865,20,CYAN)


def frame(idx,t,absolute):
    # Slow camera push through the 3D studio, with moving light and HUD layers.
    z=1.025+.035*t/DURS[idx];cw=int(W/z);ch=int(H/z)
    dx=int(5*math.sin(absolute*.17));left=(W-cw)//2+dx
    im=studio.crop((left,(H-ch)//2,left+cw,(H+ch)//2)).resize((W,H),Image.Resampling.BILINEAR).convert('RGBA')
    overlay=Image.new('RGBA',(W,H));d=ImageDraw.Draw(overlay)
    d.rectangle((0,125,720,438),fill=(0,8,22,110))
    # Animated perspective floor and moving holographic light sweeps.
    for k in range(11):
        x=-350+k*140;d.line((360+(x-360)*.12,896,x,1280),fill=(71,180,210,36),width=1)
    for k in range(6):
        y=940+((k*70+absolute*18)%350);d.line((0,y,720,y),fill=(76,200,240,24),width=1)
    for k in range(22):
        x=(k*137+absolute*(8+k%4))%720;y=430+(k*73-absolute*14)%490
        a=70+int(70*math.sin(k+absolute)**2);d.ellipse((x,y,x+2,y+2),fill=(100,225,255,a))
    im=Image.alpha_composite(im,overlay);d=ImageDraw.Draw(im)
    d.polygon([(31,49),(288,49),(302,109),(31,109)],fill='#e92643')
    txt(im,'జనసేవ న్యూస్',67,28,x=47)
    txt(im,'విశాఖపట్నం',72,25,x=470)
    d.line((32,128,688,128),fill='#43748a',width=1)
    d.ellipse((47,170,56,179),fill=RED)
    txt(im,LABEL[idx],159,26,CYAN,x=72)
    title(im,HEADS[idx][0],224,t,0,False)
    title(im,HEADS[idx][1],316,t,.18,True)
    # Red broadcast underline draws on after headline entrance.
    p=min(1,t/.8);d.polygon([(52,410),(52+int(598*p),410),(44+int(598*p),415),(52,415)],fill=RED)
    scene(im,idx,t)
    txt(im,'ఏఐతో రూపొందించిన దృశ్యాలు • సూచనాత్మక ప్రదర్శన',923,20,'#abccd9')
    # Segmented kinetic lower-third changes with narration.
    count=len(CAPS[idx]);part=min(count-1,int(t/DURS[idx]*count));local=t%(DURS[idx]/count)
    glass(im,(36,977,684,1099))
    d=ImageDraw.Draw(im);d.rectangle((36,977,43,1099),fill=RED)
    cap=CAPS[idx][part]
    line=textimg(cap,31,WHITE)
    if line.width>597:line=line.resize((597,int(line.height*597/line.width)),Image.Resampling.LANCZOS)
    progress=min(1,local/.24);xx=int((W-line.width)/2+30*(1-progress))
    line=line.copy();line.putalpha(line.getchannel('A').point(lambda a:int(a*progress)))
    im.alpha_composite(line,(xx,1025))
    txt(im,'ఎన్నికల తేదీలకు అధికారిక ప్రకటన చూడండి',1130,22,'#c0d7e2')
    txt(im,'ప్రజల కోసం ప్రజల వార్తలు',1177,22,CYAN)
    for j in range(6):
        x=44+j*106;d.rectangle((x,1230,x+93,1233),fill='#365569')
        if j<idx: d.rectangle((x,1230,x+93,1233),fill=CYAN)
        if j==idx:d.rectangle((x,1230,x+int(93*t/DURS[idx]),1233),fill=RED)
    # Fast diagonal light-wipe at each scene boundary.
    if idx>0 and t<.30:
        wipe=Image.new('RGBA',(W,H));wd=ImageDraw.Draw(wipe);x=int(-500+t/.30*1800)
        wd.polygon([(x-160,0),(x,0),(x-490,H),(x-650,H)],fill=(73,229,255,160))
        wd.polygon([(x,0),(x+30,0),(x-460,H),(x-490,H)],fill=(240,255,255,225))
        im=Image.alpha_composite(im,wipe)
    return im.convert('RGB')
