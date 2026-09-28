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
# Use the modern animated virtual-studio compositor.
import newsroom_layout
newsroom_layout.install(globals())
frame = newsroom_layout.frame

def render():
    os.makedirs('output',exist_ok=True)
    # Retiming each passage modestly preserves clarity and the 55-second total.
    for i,dur in enumerate(DURS):
        with wave.open(f'assets/scene{i+1}.wav') as w: sec=w.getnframes()/w.getframerate()
        ratio=sec/(dur-.15)
        subprocess.run([FF,'-y','-loglevel','error','-i',f'assets/scene{i+1}.wav','-af',f'atempo={ratio},apad,atrim=duration={dur},afade=t=in:d=0.025,afade=t=out:st={dur-.08}:d=0.08','-ar','48000','-ac','1',f'assets/retimed{i}.wav'],check=True)
    with open('assets/audio.txt','w') as f:
        for i in range(6):f.write(f"file 'retimed{i}.wav'\n")
    subprocess.run([FF,'-y','-loglevel','error','-f','concat','-safe','0','-i','assets/audio.txt','-af','loudnorm=I=-16:TP=-1.5:LRA=9','assets/narration.wav'],check=True)
    cmd=[FF,'-y','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i','assets/narration.wav','-vf','scale=1080:1920:flags=lanczos','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-metadata:s:a:0','language=tel','-b:a','192k','-movflags','+faststart','-t','55','output/vsp_gvmc_news_telugu_short.mp4']
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

if __name__ == '__main__':
    render()
