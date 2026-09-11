import os, json
import numpy as np, cv2
from PIL import Image

PROJ = r"C:\dev\diffpair\kicad\board_trace"
IMGDIR = os.path.join(PROJ, "images")
for src, dst in [("board_top-gimp.jpg","board_top.png"), ("board_bottom-gimp.jpg","board_bottom.png")]:
    Image.open(os.path.join(r"C:\dev\diffpair\photos", src)).convert("RGB").save(
        os.path.join(IMGDIR,dst),"PNG",dpi=(300,300))

def detect(path, excl, tag, fillmin, need_elong=False):
    img = cv2.imread(path); H,W = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h,s,v = hsv[:,:,0].astype(int), hsv[:,:,1].astype(int), hsv[:,:,2].astype(int)
    exm = np.zeros((H,W),np.uint8)
    for (x0,y0,x1,y1) in excl: cv2.rectangle(exm,(x0,y0),(x1,y1),255,-1)
    bright = ((v>150)&(s<95)).astype(np.uint8)*255
    bright[exm>0]=0
    bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN, np.ones((4,4),np.uint8))
    n,lab,st,cent = cv2.connectedComponentsWithStats(bright,8)
    comps=[]
    for i in range(1,n):
        x,y,w,hh,area = st[i]
        if area<60 or area>700 or w<10 or hh<10 or w>48 or hh>48: continue
        ar = max(w,hh)/float(min(w,hh))
        if ar>3.4: continue
        fill=area/float(w*hh)
        if fill<fillmin: continue
        if need_elong and ar<1.3: continue
        comps.append([float(cent[i][0]),float(cent[i][1]),int(w),int(hh)])
    vis=img.copy()
    for (cx,cy,w,hh) in comps: cv2.rectangle(vis,(int(cx-w/2),int(cy-hh/2)),(int(cx+w/2),int(cy+hh/2)),(0,0,255),1)
    cv2.imwrite(os.path.join(r"C:\Users\user\AppData\Local\Temp\opencode\dp","det_%s.png"%tag),vis)
    print(tag,"detected",len(comps))
    return comps

top = detect(os.path.join(IMGDIR,"board_top.png"),
    [(0,0,1030,420),(530,420,1005,885),(250,540,450,710),(30,880,205,1030),
     (30,1160,200,1390),(110,1380,350,1601),(280,1040,515,1275),(320,1115,565,1325),
     (893,885,1030,1601)],
    "top", fillmin=0.6)
bot = detect(os.path.join(IMGDIR,"board_bottom.png"), [(60,560,470,1010)], "bottom", fillmin=0.62, need_elong=True)
json.dump({"top":top,"bottom":bot}, open(os.path.join(PROJ,"detect.json"),"w"))
