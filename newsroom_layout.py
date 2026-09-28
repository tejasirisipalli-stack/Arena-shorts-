"""Animated virtual newsroom layout; composited by make_video.py.
The newsroom is AI-generated; the coast is a photograph, not filmed footage.
"""
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont
import math, functools


def install(ns):
    global textimg, txt, num, HEADS, CAPS, LABEL, DURS
    for key in ('textimg','txt','num','HEADS','CAPS','LABEL','DURS'):
        globals()[key]=ns[key]

W,H=720,1280
CYAN='#74f4ff'; GOLD='#ffe285'; WHITE='#f2f8ff'; RED='#ff334b'
studio=Image.open('assets/newsroom.jpg').convert('RGB').resize((W,H),Image.Resampling.LANCZOS)
coast=Image.open('image-search/visakhapatnam-beach-aerial-city-1.jpg').convert('RGB')

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

def scene(im,idx,t):
    d=ImageDraw.Draw(im)
    bob=math.sin(t*1.3)*5
    orbit(im,826,t)
    if idx in (0,5):
        # Photo-based city motion insert, explicitly labelled, not stock video.
        y=483;w=568;h=292
        zoom=1.03+.07*t/DURS[idx];cw=int(coast.width/zoom);ch=int(cw*h/w)
        cx=coast.width/2+math.sin(t*.15)*8;cy=coast.height*.5
        pic=coast.crop((int(cx-cw/2),int(cy-ch/2),int(cx+cw/2),int(cy+ch/2))).resize((w,h),Image.Resampling.LANCZOS).convert('RGBA')
        shade=Image.new('RGBA',pic.size,(0,21,41,65));pic=Image.alpha_composite(pic,shade)
        im.alpha_composite(pic,(76,y));d.rectangle((74,y-2,646,y+h+2),outline=CYAN,width=2)
        d.polygon([(74,y+h+2),(646,y+h+2),(628,y+h+16),(89,y+h+16)],fill='#12344f')
        d.rectangle((76,y+240,644,y+292),fill=(3,16,30,215));txt(im,'విశాఖ నగర ఛాయాచిత్రం',y+254,24,x=94)
        if idx==0:
            title(im,'120 వార్డులు',794,t,.4,True,48)
        else:
            d.rounded_rectangle((152,790,568,862),radius=7,fill=RED)
            txt(im,'సబ్‌స్క్రైబ్ చేయండి',812,32)
    elif idx==1:
        n=min(120,int(120*min(1,t/1.5)))
        title(im,str(n),475,t,0,True,158)
        txt(im,'వార్డుల్లో ఎన్నికల సన్నాహాలు',656,30)
        for k in range(120):
            row,col=divmod(k,15);x=135+col*29+row*3;y=731+row*13
            c=CYAN if k<n else '#1c3548'
            d.polygon([(x,y),(x+20,y),(x+25,y-5),(x+5,y-5)],fill=c)
            d.polygon([(x,y),(x+20,y),(x+20,y+5),(x,y+5)],fill='#267c99')
    elif idx==2:
        slab(im,190,483+bob,332,324,18,'#e1edf3')
        d.rectangle((208,506+bob,503,556+bob),fill='#153d58')
        txt(im,'ఎన్నికల సన్నద్ధత',517+bob,28,x=231)
        lines=['ఓటర్ల జాబితాలు','పోలింగ్ కేంద్రాలు','సిబ్బందికి శిక్షణ']
        for j,s in enumerate(lines):
            y=590+j*68+bob;p=max(0,min(1,(t-.4-j*.3)*3))
            d.rounded_rectangle((213,y,245,y+32),radius=5,fill='#087d8d')
            if p>0:d.line((219,y+15,227,y+24,239,y+7),fill='white',width=4)
            txt(im,s,y+4,27,'#0c3550',x=261)
        txt(im,'అవగాహన కార్యక్రమాలు',844,27,CYAN)
    elif idx==3:
        glass(im,(80,482,640,799))
        txt(im,'ఎన్‌డీఏ సమన్వయ సమావేశం',512,31,CYAN)
        title(im,'మేయర్',575,t,.2,False,55)
        title(im,'120 స్థానాలు',658,t,.5,True,59)
        d.rectangle((111,812,609,864),fill=(122,24,41,240))
        txt(im,'లక్ష్యాలు మాత్రమే • ఫలితాలు కావు',831,25)
    elif idx==4:
        slab(im,213,478+bob,286,310,18,'#dfedf3')
        d.rectangle((214,479+bob,498,537+bob),fill=RED)
        for x in [260,450]:d.rounded_rectangle((x,461+bob,x+12,503+bob),radius=5,fill='white')
        for j in range(3):
            for k in range(4):
                x=239+k*62;y=564+j*62+bob
                d.rectangle((x,y,x+39,y+37),fill='#b4cdd9')
        txt(im,'షెడ్యూల్',750+bob,30,'#0c3550')
        txt(im,'అధికారిక ప్రకటన కోసం వేచి చూడాలి',835,27,GOLD)


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
    txt(im,'వర్చువల్ స్టూడియో • సూచనాత్మక దృశ్యాలు',923,21,'#abccd9')
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
