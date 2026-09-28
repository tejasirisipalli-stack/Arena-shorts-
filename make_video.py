from PIL import Image, ImageDraw, ImageFont, ImageFilter
import uharfbuzz as hb, freetype, math, subprocess, wave, functools, os
import imageio_ffmpeg
W,H,FPS=720,1280,24
FF=imageio_ffmpeg.get_ffmpeg_exe()
FONT='assets/Merged.ttf'
fontdata=open(FONT,'rb').read(); face=hb.Face(fontdata)
YELLOW='#ffe15b'; WHITE='#f7f9fc'; MUTED='#b6c8d8'; RED='#e53245'
@functools.lru_cache(maxsize=400)
def textimg(text,size,color=WHITE):
    font=hb.Font(face);font.scale=(size*64,size*64);hb.ot_font_set_funcs(font)
    buf=hb.Buffer();buf.add_str(text);buf.guess_segment_properties();hb.shape(font,buf)
    ft=freetype.Face(FONT);ft.set_pixel_sizes(0,size)
    width=int(sum(p.x_advance for p in buf.glyph_positions)/64)+16
    im=Image.new('RGBA',(max(width,1),size*3)); x=5; baseline=size*1.6
    for info,p in zip(buf.glyph_infos,buf.glyph_positions):
        ft.load_glyph(info.codepoint,freetype.FT_LOAD_RENDER);g=ft.glyph;b=g.bitmap
        if b.width and b.rows:
            mask=Image.frombytes('L',(b.width,b.rows),bytes(b.buffer))
            tile=Image.new('RGBA',mask.size,color);tile.putalpha(mask)
            im.alpha_composite(tile,(int(x+p.x_offset/64+g.bitmap_left),int(baseline-p.y_offset/64-g.bitmap_top)))
        x+=p.x_advance/64
    box=im.getbbox();return im.crop(box) if box else im

def txt(im,s,y,size=42,color=WHITE,x=None):
    t=textimg(s,size,color)
    if t.width>636: t=t.resize((636,round(t.height*636/t.width)),Image.Resampling.LANCZOS)
    im.alpha_composite(t,(int((W-t.width)/2 if x is None else x),int(y)))

def num(im,s,xy,size=80,color=YELLOW):
    d=ImageDraw.Draw(im);f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',size)
    d.text(xy,s,font=f,fill=color,anchor='mm')

DURS=[9,8,7,11,8,12]
HEADS=[['జీవీఎంసీ ఎన్నికలకు','సన్నాహాలు!'],['మొత్తం 120','వార్డులతో ఏర్పాట్లు'],['ఎన్నికల ఏర్పాట్లు','కొనసాగుతున్నాయి'],['మేయర్ పదవి','120 స్థానాలే లక్ష్యం'],['అధికారిక ప్రకటన','వచ్చాకే స్పష్టత'],['మీ అభిప్రాయం','కామెంట్ చేయండి']]
CAPS=[
['విశాఖపట్నం ఎన్నికల అప్‌డేట్','120 వార్డులతో సన్నాహాలు','నివేదికలు చెబుతున్న సమాచారం'],
['గ్రేటర్ విశాఖ మున్సిపల్ కార్పొరేషన్','120 వార్డుల్లో ఎన్నికల ఏర్పాట్లు','తాజా నివేదికల ప్రకారం'],
['ఎన్నికల విధులపై అవగాహన','అధికారులు, సిబ్బందికి శిక్షణ','నివేదికల్లో వెల్లడైన వివరాలు'],
['ఎన్‌డీఏ సమన్వయ సమావేశం','జీవీఎంసీ ఎన్నికలపై చర్చ','మేయర్, కార్పొరేటర్ స్థానాల లక్ష్యం','ఇవి నాయకుల ప్రకటనలు మాత్రమే'],
['ఎన్నికల నోటిఫికేషన్, షెడ్యూల్','అధికారిక ప్రకటన కోసం వేచి చూడాలి','ఆ తర్వాతే పూర్తి వివరాలు'],
['మరిన్ని వివరాలకు డిస్క్రిప్షన్ చూడండి','మీ అభిప్రాయాన్ని పంచుకోండి','తాజా వార్తలకు సబ్‌స్క్రైబ్ చేయండి','ప్రజల కోసం ప్రజల వార్తలు']]
LABEL=['తాజా సమాచారం','నివేదికల ప్రకారం','సిబ్బందికి శిక్షణ','నాయకుల ప్రకటన','ముఖ్య గమనిక','జనసేవ న్యూస్']
photo=Image.open('image-search/visakhapatnam-beach-aerial-city-1.jpg').convert('RGB').resize((W,H))
# Real coastline photo with editorial dark overlay. All civic imagery below is illustrative.
bg=photo.convert('RGBA');shade=Image.new('RGBA',(W,H));sd=ImageDraw.Draw(shade)
for y in range(H):
    alpha=int(145+85*abs(y-H*.46)/(H*.55));sd.line((0,y,W,y),fill=(3,15,30,min(alpha,240)))
bg=Image.alpha_composite(bg,shade)

def graphic(idx,t):
    g=Image.new('RGBA',(W,470));d=ImageDraw.Draw(g)
    d.rounded_rectangle((44,5,676,451),radius=26,fill=(10,30,48,235),outline=(76,111,134,255),width=2)
    if idx in (0,1):
        if idx==0:
            # Civic building illustration, not a depiction of a particular office.
            d.polygon([(105,174),(360,64),(615,174)],fill='#254d63',outline='#7badbc')
            txt(g,'జీవీఎంసీ',117,38,YELLOW)
            d.rectangle((115,184,605,199),fill='#82aabd')
            for x in [145,250,355,460,555]: d.rounded_rectangle((x,214,x+29,344),radius=5,fill='#8aabbc')
            d.rectangle((101,354,620,370),fill='#d9e6e9');txt(g,'ఎన్నికల సన్నాహాలు',389,29)
        else:
            num(g,'120',(360,99),112)
            txt(g,'వార్డులు',162,34)
            n=min(120,int(t*85)+1)
            for k in range(120):
                x=111+(k%15)*34;y=231+(k//15)*21
                d.rounded_rectangle((x,y,x+24,y+12),radius=3,fill=YELLOW if k<n else '#274459')
            txt(g,'వార్డుల సూచనాత్మక గ్రాఫిక్',414,21,MUTED)
    elif idx==2:
        d.rounded_rectangle((220,47,507,329),radius=14,fill='#e6eef0')
        for j in range(3):
            y=107+j*74; d.rounded_rectangle((249,y,279,y+30),radius=5,fill='#18a48f')
            d.line((255,y+15,264,y+23,277,y+7),fill='white',width=4)
            d.line((303,y+10,465,y+10),fill='#71899a',width=8)
            d.line((303,y+28,428,y+28),fill='#a4bac5',width=5)
        txt(g,'ఓటర్ల జాబితాలు • పోలింగ్ కేంద్రాలు',359,27)
        txt(g,'సిబ్బంది బాధ్యతలపై అవగాహన',405,25,MUTED)
    elif idx==3:
        txt(g,'ఎన్‌డీఏ సమావేశం',51,36,YELLOW)
        for x in [196,360,524]:
            d.ellipse((x-27,141,x+27,195),fill='#7799ad')
            d.rounded_rectangle((x-44,207,x+44,292),radius=23,fill='#365e78')
        d.rounded_rectangle((127,270,594,302),radius=9,fill='#dde8ed')
        txt(g,'ప్రచార లక్ష్యాలు మాత్రమే',336,34,YELLOW)
        txt(g,'నిర్ధారిత ఫలితాలు కావు',393,28)
    elif idx==4:
        d.rounded_rectangle((202,47,519,298),radius=18,fill='#e7edf1')
        d.rounded_rectangle((202,47,519,103),radius=18,fill=RED)
        for x in [259,463]: d.line((x,32,x,70),fill='white',width=13)
        for j in range(3):
            for k in range(5):
                x=235+k*52;y=132+j*47;d.rounded_rectangle((x,y,x+25,y+24),radius=4,fill='#a2b5c3')
        txt(g,'ఎన్నికల షెడ్యూల్',331,34,YELLOW)
        txt(g,'అధికారిక ప్రకటన కోసం వేచి చూడాలి',393,25)
    else:
        d.ellipse((289,39,431,181),fill=RED)
        d.polygon([(346,78),(346,141),(392,110)],fill='white')
        txt(g,'జనసేవ న్యూస్',220,49)
        d.rounded_rectangle((145,301,575,374),radius=36,fill=RED)
        txt(g,'సబ్‌స్క్రైబ్ చేయండి',320,32)
        txt(g,'లైక్ • కామెంట్ • షేర్',408,25,YELLOW)
    return g

def frame(idx,t,absolute):
    z=1.015+.025*t/DURS[idx];cw=int(W/z);ch=int(H/z)
    im=bg.crop(((W-cw)//2,(H-ch)//2,(W+cw)//2,(H+ch)//2)).resize((W,H),Image.Resampling.BILINEAR)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,9),fill=RED)
    d.rounded_rectangle((40,46,284,103),radius=8,fill=RED);txt(im,'జనసేవ న్యూస్',62,27,x=56)
    txt(im,'విశాఖపట్నం',62,25,x=478)
    d.line((43,126,677,126),fill='#557080',width=1)
    txt(im,LABEL[idx],158,27,YELLOW)
    for j,line in enumerate(HEADS[idx]):
        p=max(0,min(1,(t-j*.17)/.48));off=int(65*(1-(1-(1-p)**3)))
        layer=Image.new('RGBA',(W,H));txt(layer,line,224+j*82+off,55,YELLOW if j else WHITE)
        layer.putalpha(layer.getchannel('A').point(lambda a:int(a*p)));im=Image.alpha_composite(im,layer)
    g=graphic(idx,t);p=min(1,t/.6); gy=450+int((1-p)*40);im.alpha_composite(g,(0,gy))
    d=ImageDraw.Draw(im)
    txt(im,'సూచనాత్మక దృశ్యాలు' if idx not in (1,5) else ('నివేదికల ఆధారంగా' if idx==1 else 'ప్రజల కోసం ప్రజల వార్తలు'),916,21,MUTED)
    d.rounded_rectangle((38,979,682,1116),radius=17,fill=(2,13,24,235))
    cap=CAPS[idx][min(len(CAPS[idx])-1,int(t/DURS[idx]*len(CAPS[idx])))]
    txt(im,cap,1023,32)
    txt(im,'ఎన్నికల తేదీలకు అధికారిక ప్రకటన చూడండి',1152,21,MUTED)
    # Discrete scene progress markers.
    for j in range(6):
        x=45+j*106;d.rounded_rectangle((x,1220,x+95,1225),radius=2,fill=YELLOW if j<=idx else '#365062')
    d.rectangle((0,H-7,int(W*absolute/55),H),fill=YELLOW)
    return im.convert('RGB')

os.makedirs('output',exist_ok=True)
# Retiming each passage modestly preserves clarity and the 55-second total.
for i,dur in enumerate(DURS):
    with wave.open(f'assets/scene{i+1}.wav') as w: sec=w.getnframes()/w.getframerate()
    ratio=sec/(dur-.15)
    subprocess.run([FF,'-y','-loglevel','error','-i',f'assets/scene{i+1}.wav','-af',f'atempo={ratio},apad,atrim=duration={dur},afade=t=in:d=0.025,afade=t=out:st={dur-.08}:d=0.08','-ar','48000','-ac','1',f'assets/retimed{i}.wav'],check=True)
with open('assets/audio.txt','w') as f:
    for i in range(6):f.write(f"file 'retimed{i}.wav'\n")
subprocess.run([FF,'-y','-loglevel','error','-f','concat','-safe','0','-i','assets/audio.txt','-af','loudnorm=I=-16:TP=-1.5:LRA=9','assets/narration.wav'],check=True)
cmd=[FF,'-y','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i','assets/narration.wav','-vf','scale=1080:1920:flags=lanczos','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-t','55','output/vsp_gvmc_news_telugu_short.mp4']
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
absolute=0
for idx,dur in enumerate(DURS):
    print('Rendering scene',idx+1,flush=True)
    for k in range(dur*FPS):
        im=frame(idx,k/FPS,absolute+k/FPS)
        if idx==0 and k==30: im.resize((1080,1920)).save('output/thumbnail.jpg',quality=95)
        p.stdin.write(im.tobytes())
    absolute+=dur
p.stdin.close()
if p.wait():raise RuntimeError('Encoding failed')
print('Finished: output/vsp_gvmc_news_telugu_short.mp4')
