#!/usr/bin/env python3
"""以同一几何布局导出可编辑 SVG 与印刷 PNG：python3 论文配图/render.py。

图号、图题由文稿排版；绘图层只包含解释图形所需的标注。依赖 Pillow。
"""
from functools import lru_cache
from math import hypot
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parent
W, SCALE, PRINT_CM = 720, 4, 14.5
PAPER, INK, GRAY = "#FFFFFF", "#1E2939", "#52606F"
BLUE, COPPER = "#344F98", "#925433"
PALE, SILVER, HAIR = "#E9EDF7", "#98A5BA", "#D1D8E3"
FAMILIES = {
    "sans": "'Hiragino Sans GB','Noto Sans CJK SC','Microsoft YaHei',sans-serif",
    "serif": "'Songti SC','Noto Serif CJK SC','SimSun',serif",
}


@lru_cache(maxsize=None)
def font(size, bold, kind):
    weight = "Bold" if bold else "Regular"
    faces = {
        "sans": [("/System/Library/Fonts/Hiragino Sans GB.ttc", 2 if bold else 0),
                 (f"/usr/share/fonts/opentype/noto/NotoSansCJK-{weight}.ttc", 2),
                 (f"C:/Windows/Fonts/{'msyhbd' if bold else 'msyh'}.ttc", 0)],
        "serif": [("/System/Library/Fonts/Supplemental/Songti.ttc", 1 if bold else 6),
                  (f"/usr/share/fonts/opentype/noto/NotoSerifCJK-{weight}.ttc", 2),
                  ("C:/Windows/Fonts/simsun.ttc", 0)],
    }
    for name, idx in faces[kind]:
        if Path(name).is_file():
            return ImageFont.truetype(name, size*SCALE, index=idx)
    if kind == "serif":
        return font(size, bold, "sans")
    raise RuntimeError("请安装冬青黑体、Noto Sans CJK SC 或微软雅黑。")


def px(point):
    return tuple(round(v*SCALE) for v in point)


def coords(points):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def bezier(start, c1, c2, end, steps=32):
    points = []
    for i in range(steps+1):
        t = i/steps
        u = 1-t
        points.append(tuple(u**3*a + 3*u*u*t*b + 3*u*t*t*c + t**3*d
                            for a, b, c, d in zip(start, c1, c2, end)))
    return points


class Figure:
    def __init__(self, stem, name, description, height):
        self.stem, self.h = stem, height
        self.im = Image.new("RGB", (W*SCALE, height*SCALE), PAPER)
        self.pen = ImageDraw.Draw(self.im)
        self.labels = []
        self.svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg", "width": str(W), "height": str(height),
            "viewBox": f"0 0 {W} {height}", "role": "img", "aria-labelledby": "name desc",
        })
        ET.SubElement(self.svg, "title", id="name").text = name
        ET.SubElement(self.svg, "desc", id="desc").text = description
        ET.SubElement(self.svg, "rect", width=str(W), height=str(height), fill=PAPER)

    def text(self, x, y, value, size=18, *, bold=False, color=INK, kind="sans", center=False, limit):
        face = font(size, bold, kind)
        anchor = "ms" if center else "ls"
        box = tuple(v/SCALE for v in self.pen.textbbox(px((x,y)), value, font=face, anchor=anchor))
        l, t, r, b = box
        if r-l > limit or l < 2 or t < 2 or r > W-2 or b > self.h-2:
            raise ValueError(f"{self.stem}: 标注超界 {value!r} {box} / 宽限 {limit}")
        for label, (ll, tt, rr, bb) in self.labels:
            if min(r,rr) > max(l,ll) and min(b,bb) > max(t,tt):
                raise ValueError(f"{self.stem}: 标注相交 {value!r} / {label!r}")
        self.labels.append((value, box))
        self.pen.text(px((x,y)), value, font=face, fill=color, anchor=anchor)
        ET.SubElement(self.svg, "text", {
            "x": str(x), "y": str(y), "font-family": FAMILIES[kind], "font-size": str(size),
            "font-weight": "700" if bold else "400", "text-anchor": "middle" if center else "start",
            "fill": color,
        }).text = value

    def path(self, d, points, color=None, width=1.5, fill=None, dash=None):
        attr = {"d": d, "fill": fill or "none", "stroke": color or "none", "stroke-width": str(width),
                "stroke-linejoin": "round", "stroke-linecap": "round" if not dash else "butt"}
        if dash:
            attr["stroke-dasharray"] = " ".join(map(str, dash))
        ET.SubElement(self.svg, "path", attr)
        if fill:
            self.pen.polygon([px(p) for p in points], fill=fill)
        if not color:
            return
        lw = max(1, round(width*SCALE))
        if not dash:
            self.pen.line([px(p) for p in points], fill=color, width=lw, joint="curve")
            return
        phase, left = 0, dash[0]
        for (x,y), (u,v) in zip(points, points[1:]):
            length = hypot(u-x, v-y)
            pos = 0
            while pos < length-1e-8:
                step = min(left, length-pos)
                if phase == 0:
                    self.pen.line([px((x+(u-x)*s/length, y+(v-y)*s/length)) for s in (pos,pos+step)],
                                  fill=color, width=lw)
                pos += step
                left -= step
                if left < 1e-8:
                    phase = 1-phase
                    left = dash[phase]

    def line(self, points, color=GRAY, width=1.5, dash=None):
        self.path("M "+coords(points), points, color, width, dash=dash)

    def curve(self, p, a, b, q, color=BLUE, width=2, dash=None, arrow=False):
        self.path("M "+coords([p])+" C "+coords([a,b,q]), bezier(p,a,b,q), color, width, dash=dash)
        if arrow:
            self.head(b,q,color)

    def head(self, p, q, color):
        dx, dy = q[0]-p[0], q[1]-p[1]
        span = hypot(dx, dy)
        dx, dy = dx/span, dy/span
        a = (q[0]-9*dx+3.7*dy, q[1]-9*dy-3.7*dx)
        b = (q[0]-9*dx-3.7*dy, q[1]-9*dy+3.7*dx)
        self.polygon([q,a,b], color)

    def arrow(self, p, q, color=BLUE, width=1.8):
        self.line([p,q],color,width)
        self.head(p,q,color)

    def polygon(self, points, fill, edge=None, width=1.5):
        self.path("M "+coords(points)+" Z", points+[points[0]], edge, width, fill)

    def dot(self, x, y, r, fill, edge=None, width=1.6):
        ET.SubElement(self.svg, "circle", {"cx":str(x),"cy":str(y),"r":str(r),"fill":fill or "none",
                                          "stroke":edge or "none","stroke-width":str(width)})
        self.pen.ellipse(px((x-r,y-r,x+r,y+r)),fill=fill,outline=edge,width=max(1,round(width*SCALE)))

    def field(self, cx, cy, rx, ry, *, miniature=False, recipient=False):
        # 以闭合曲线表示可导航的联结结构。等形缩放使两位主体的示意保持同一视觉语法。
        shape = [(-.97,-.05),(-.76,-.66),(-.24,-.88),(.31,-.93),(.81,-.62),(.97,-.07),
                 (.84,.43),(.44,.85),(-.09,.92),(-.62,.71),(-.9,.34)]
        for k, shade, edge in [(1,"#F4F6FB","#AEBBD7"),(.84,"#EBEFF8","#B5C2DE"),(.68,"#E4EAF6","#BAC7E2")]:
            pts = [(cx+x*rx*k,cy+y*ry*k) for x,y in shape]
            d, samples = "M "+coords(pts[:1]), [pts[0]]
            for i,p in enumerate(pts):
                prev, q, after = pts[i-1],pts[(i+1)%len(pts)],pts[(i+2)%len(pts)]
                a = tuple(x+(y-z)/6 for x,y,z in zip(p,q,prev))
                b = tuple(x-(y-z)/6 for x,y,z in zip(q,after,p))
                d += " C "+coords([a,b,q]); samples.extend(bezier(p,a,b,q,12)[1:])
            self.path(d+" Z",samples,edge,1,shade)
        if miniature:
            if recipient:
                a,b,c,d = (cx-.34*rx,cy-.13*ry),(cx,cy+.15*ry),(cx+.30*rx,cy-.26*ry),(cx+.39*rx,cy+.22*ry)
                self.line([a,b,d],GRAY,1.2)
                self.line([b,c],BLUE,2)
                for pos in (a,d):
                    self.dot(*pos,2.6,PAPER,GRAY,1.2)
                for pos in (b,c):
                    self.dot(*pos,2.8,BLUE)
            else:
                a,b,c = (cx-.36*rx,cy+.12*ry),(cx+.04*rx,cy-.25*ry),(cx+.39*rx,cy+.13*ry)
                self.line([a,b,c],BLUE,1.5)
                for pos in (a,b,c):
                    self.dot(*pos,2.8,BLUE)

    def save(self):
        ET.indent(self.svg)
        ET.ElementTree(self.svg).write(OUT/(self.stem+".svg"),encoding="utf-8",xml_declaration=True)
        dpi = W*SCALE*2.54/PRINT_CM
        self.im.save(OUT/(self.stem+".png"),dpi=(dpi,dpi),optimize=True)
        print(f"{self.stem}: {self.im.width} × {self.im.height}")


def mechanism():
    f = Figure("01_元空间机制", "元空间中的行动反馈与跨主体习得",
               "当前线索进入元空间；执行后果反馈到记忆。言传产物并非能力的复制，接收者凭自身经验重建联结。", 306)
    f.text(78,35,"当前线索",21,kind="serif",bold=True,center=True,limit=140)
    f.text(619,35,"行动选择",21,kind="serif",bold=True,center=True,limit=142)

    for y in (65,90,115):
        f.curve((48,y),(73,y),(86,90),(111,90),SILVER,1.5)
        f.dot(46,y,4.3,PAPER,BLUE)
    f.arrow((111,90),(220,90),BLUE,1.8)
    f.text(80,149,"观察与任务",16,color=GRAY,center=True,limit=138)

    f.field(339,89,113,65)
    f.text(339,83,"元空间",29,kind="serif",bold=True,center=True,limit=132)
    f.text(339,113,"M = (G, F)",18,color=BLUE,center=True,limit=124)
    f.text(323,172,"G：经验联结　 F：功能组织",16,color=GRAY,center=True,limit=285)

    f.line([(454,90),(529,90)],BLUE,1.9)
    f.curve((529,90),(561,90),(569,65),(620,65),SILVER,1.6,dash=(5,4))
    f.curve((529,90),(561,90),(573,113),(620,113),BLUE,2.5)
    f.dot(529,90,3.8,BLUE)
    f.dot(624,65,5,PAPER,SILVER)
    f.dot(624,113,5.7,BLUE)
    f.text(640,72,"备选",16,color=GRAY,limit=58)
    f.text(640,120,"执行",17,bold=True,limit=58)
    f.curve((624,124),(622,174),(489,195),(410,143),COPPER,1.75,arrow=True)
    f.text(533,160,"结果反馈",16,color=COPPER,center=True,limit=99)

    f.line([(24,192),(696,192)],HAIR,1)
    f.field(92,247,42,29,miniature=True)
    f.field(628,247,42,29,miniature=True,recipient=True)
    f.polygon([(345,225),(364,225),(376,237),(376,268),(345,268)],"#F4F6FB",BLUE,1.5)
    f.line([(364,225),(364,237),(376,237)],BLUE,1.3)
    for i,length in enumerate((17,20,13)):
        f.line([(351,245+6*i),(351+length,245+6*i)],BLUE,1.2)
    f.arrow((144,247),(332,247),GRAY,1.5)
    f.arrow((388,247),(576,247),GRAY,1.5)
    f.text(238,234,"按听者需要言传",17,color=GRAY,center=True,limit=178)
    f.text(482,234,"结合自身经历习得",17,color=GRAY,center=True,limit=178)
    for x,label in ((92,"主体记忆"),(360,"言传产物 K"),(628,"接收者记忆")):
        f.text(x,291,label,18,bold=True,center=True,limit=163)
    f.save()


def association():
    f = Figure("02_联想激活与组合敏感性", "联想模式的激活与信息组合的披露边界",
               "A 路在高峰时唤起较慢的预期；非高峰联结仍保留。组织政策可对原本公开的日期、地点组合另设边界。", 290)
    f.text(78,78,"A 路",25,kind="serif",bold=True,center=True,limit=100)
    f.text(78,141,"路线线索",16,color=GRAY,center=True,limit=132)
    active = ((85,103),(181,103),(179,61),(298,61))
    f.curve(*active,PALE,8)
    f.curve(*active,BLUE,2.5)
    f.curve((85,103),(181,103),(179,146),(298,146),SILVER,1.8,dash=(6,4))
    f.line([(298,61),(511,61)],BLUE,2.5)
    f.line([(298,146),(511,146)],SILVER,1.8,dash=(6,4))
    f.dot(79,103,8,BLUE); f.dot(298,61,6,BLUE); f.dot(298,146,6,PAPER,SILVER,1.8)
    f.dot(514,61,4.5,BLUE); f.dot(514,146,4.5,PAPER,SILVER)
    f.text(298,44,"高峰",20,bold=True,center=True,limit=94)
    f.text(298,129,"非高峰",19,color=GRAY,center=True,limit=98)
    f.text(416,47,"当前激活",16,color=BLUE,center=True,limit=109)
    f.text(416,132,"已存、未激活",16,color=GRAY,center=True,limit=133)
    for y,val,hue in ((61,"22",BLUE),(146,"10",GRAY)):
        f.text(540,y+5,"约",16,color=hue,limit=24)
        f.text(566,y+11,val,36,kind="serif",bold=True,color=hue,limit=58)
        f.text(620,y+6,"分钟",17,color=hue,limit=55)

    f.line([(24,179),(696,179)],HAIR,1)
    f.text(27,208,"组织特例",17,bold=True,color=COPPER,limit=110)
    for y,term in ((234,"日期"),(268,"地点")):
        f.dot(36,y-5,4,PAPER,COPPER,1.5)
        f.text(52,y,term,18,bold=True,limit=65)
        f.text(119,y,"可公开",16,color=GRAY,limit=75)
    f.curve((188,228),(224,228),(216,247),(248,247),COPPER,1.7)
    f.curve((188,262),(224,262),(216,247),(248,247),COPPER,1.7)
    f.arrow((248,247),(319,247),COPPER,1.7)
    f.text(345,241,"未发布活动的完整安排",21,kind="serif",bold=True,limit=338)
    f.text(345,269,"若适用的规则限制该组合，则仅限内部。",16,color=GRAY,limit=350)
    f.save()


def learning():
    f = Figure("03_建构动力学", "反馈驱动的三类记忆更新",
               "多次经历可以沉淀为稳定联结；校准改变既有估计，重塑改变情境划分。跨事件保持与迁移用于辨别持久变化。", 337)
    for x,title in ((116,"沉淀"),(360,"校准"),(605,"重塑")):
        f.text(x,40,title,25,kind="serif",bold=True,center=True,limit=140)
    for x in (236,482):
        f.line([(x,20),(x,172)],HAIR,1)

    for y in (72,98,125):
        f.curve((44,y),(78,y),(88,98),(128,98),SILVER if y != 98 else BLUE,1.6)
        f.dot(41,y,4.2,PAPER,BLUE)
    f.line([(126,98),(195,98)],PALE,9)
    f.line([(126,98),(195,98)],BLUE,3.1)
    f.dot(195,98,6,BLUE)
    f.text(116,161,"重复经历留下稳定联结",17,center=True,limit=211)

    f.line([(280,109),(440,109)],HAIR,1.6)
    for x in (285,309,333,357,381,405,429):
        f.line([(x,105),(x,113)],SILVER,1)
    f.curve((310,100),(325,64),(386,64),(405,99),COPPER,1.9,arrow=True)
    f.dot(309,109,5.5,PAPER,GRAY,1.7); f.dot(405,109,6,BLUE)
    f.text(360,161,"保留情境，修正原估计",17,center=True,limit=224)

    f.line([(512,98),(541,98)],BLUE,2)
    f.dot(510,98,5.5,BLUE)
    for y,text in ((74,"高峰"),(122,"非高峰")):
        f.curve((541,98),(570,98),(573,y),(609,y),BLUE,1.9)
        f.dot(610,y,4.8,PAPER,BLUE,1.8)
        f.text(625,y+6,text,16,color=GRAY,limit=70)
    f.text(602,161,"按线索重划情境边界",17,center=True,limit=214)

    f.line([(24,186),(696,186)],HAIR,1)
    f.text(27,220,"跨事件检验",19,bold=True,limit=174)
    f.text(252,219,"本次任务",16,color=GRAY,center=True,limit=115)
    f.text(393,219,"撤除提示",16,color=GRAY,center=True,limit=115)
    f.text(605,219,"新情境",16,color=GRAY,center=True,limit=115)
    f.line([(393,231),(393,307)],SILVER,1.2,dash=(4,4))
    f.text(28,258,"当次提示",17,color=GRAY,limit=154)
    f.dot(248,251,4.2,GRAY)
    f.line([(252,251),(384,251)],SILVER,1.8)
    f.line([(384,245),(384,257)],GRAY,1.5)
    f.text(605,258,"提示效应消失",17,color=GRAY,center=True,limit=158)
    f.text(28,299,"持久联结",18,bold=True,color=BLUE,limit=154)
    f.dot(248,292,5,BLUE)
    f.arrow((252,292),(510,292),BLUE,2.2)
    f.text(605,299,"仍能独立运用",18,bold=True,color=BLUE,center=True,limit=164)
    f.text(27,328,"授权或规范改变是另一种变化，需单独归因。",16,color=GRAY,limit=660)
    f.save()


def icon(f,kind,x,y):
    if kind == "route":
        f.polygon([(x-10,y+9),(x+13,y-11),(x+5,y+13),(x+1,y+1)],PAPER,BLUE,1.7)
        f.line([(x+1,y+1),(x+12,y-10)],BLUE,1.4)
    elif kind == "time":
        f.dot(x,y,12,PAPER,BLUE,1.7)
        f.line([(x,y-7),(x,y),(x+6,y+3)],BLUE,1.7)
    else:
        f.curve((x-10,y+4),(x-14,y-13),(x+11,y-16),(x+12,y),BLUE,1.6)
        f.curve((x+12,y),(x+12,y+11),(x-1,y+15),(x-8,y+8),BLUE,1.6)
        f.line([(x-11,y-3),(x-10,y+4),(x-3,y+2)],BLUE,1.6)
        f.dot(x,y,2.6,BLUE)


def articulation():
    f = Figure("04_情境化言传", "同一行程记忆在三种沟通任务中的表达",
               "路线 A 的非高峰与高峰用时分别约为 10 和 22 分钟，路线 B 均约为 14 分钟。表达依当前任务选取内容。", 273)
    f.text(25,31,"预计用时",18,bold=True,limit=100)
    f.text(118,31,"分钟",16,color=GRAY,limit=60)
    f.text(350,31,"听者与任务",18,bold=True,limit=166)
    f.line([(317,17),(317,253)],HAIR,1)
    x1,x2 = 78,220
    for x in (x1,x2):
        f.line([(x,59),(x,193)],HAIR,1)
    f.line([(x1,174),(x2,66)],BLUE,2.7)
    f.line([(x1,138),(x2,138)],GRAY,1.8,dash=(6,4))
    for x,y in ((x1,174),(x2,66)):
        f.dot(x,y,5.3,BLUE)
    for x in (x1,x2):
        f.polygon([(x,132),(x+6,138),(x,144),(x-6,138)],PAPER,GRAY,1.7)
    for x,y,num,hue in ((47,182,"10",BLUE),(250,74,"22",BLUE),(47,145,"14",GRAY),(250,145,"14",GRAY)):
        f.text(x,y,num,25,kind="serif",bold=True,color=hue,center=True,limit=47)
    f.text(x1,216,"非高峰",17,center=True,limit=100)
    f.text(x2,216,"高峰",17,center=True,limit=100)
    f.line([(38,247),(70,247)],BLUE,2.4); f.dot(54,247,4,BLUE)
    f.text(80,253,"A 路",16,color=GRAY,limit=60)
    f.line([(155,247),(187,247)],GRAY,1.6,dash=(4,3))
    f.polygon([(171,242),(176,247),(171,252),(166,247)],PAPER,GRAY,1.5)
    f.text(197,253,"B 路",16,color=GRAY,limit=60)
    for y,kind,who,message in [
        (74,"route","司机 · 出发前","高峰走 B，预计 14 分钟。"),
        (150,"time","接站人 · 同次出发","若走 B，发车后约 14 分钟到。"),
        (226,"review","同一司机 · 行程复盘","非高峰 A 更快，下次先看时段。"),
    ]:
        icon(f,kind,361,y+2)
        f.text(391,y-1,who,16,bold=True,color=GRAY,limit=303)
        f.text(391,y+25,message,19,limit=305)
    f.save()


def overview():
    files = sorted(OUT.glob("0[1-4]_*.png"))
    if len(files) != 4:
        raise ValueError("预览需要四张配图。")
    width,gap = 720,24
    tiles = []
    for file in files:
        with Image.open(file) as im:
            tiles.append(im.resize((width,round(im.height*width/im.width)),Image.Resampling.LANCZOS))
    h1,h2 = max(t.height for t in tiles[:2]),max(t.height for t in tiles[2:])
    sheet = Image.new("RGB",(2*width+3*gap,h1+h2+3*gap),PAPER)
    pen = ImageDraw.Draw(sheet)
    pen.line([(gap+width+gap//2,gap),(gap+width+gap//2,sheet.height-gap)],fill=HAIR)
    pen.line([(gap,h1+gap+gap//2),(sheet.width-gap,h1+gap+gap//2)],fill=HAIR)
    for i,tile in enumerate(tiles):
        rowh = h1 if i < 2 else h2
        sheet.paste(tile,(gap+i%2*(width+gap), (gap if i < 2 else 2*gap+h1)+(rowh-tile.height)//2))
    sheet.save(OUT/"四图总览.png",optimize=True)


if __name__ == "__main__":
    for draw in (mechanism,association,learning,articulation):
        draw()
    overview()
