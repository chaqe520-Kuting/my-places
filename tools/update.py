#!/usr/bin/env python3
"""用 Google Takeout 匯出檔更新 places.json。
用法：python3 tools/update.py <takeout.zip 或解壓後的 Takeout 資料夾> [來源說明]
- 已存在的地點：保留原本的分類、地區、名稱，只更新所屬清單、備註、網址
- 新地點：依關鍵字自動分類，標記 isNew
- Google 地圖已刪除的地點：從名單移除
"""
import csv,io,json,re,sys,zipfile,datetime,os,glob
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dec=lambda s:re.sub(r'#U([0-9a-f]{4})',lambda m:chr(int(m.group(1),16)),s)
SKIP_LISTS={'儲存的網頁'}

def read_takeout(src):
    files={}
    if os.path.isdir(src):
        for p in glob.glob(os.path.join(src,'**','*'),recursive=True):
            if os.path.isfile(p) and (p.endswith('.csv') or p.endswith('.json')):
                files[dec(os.path.relpath(p,src))]=open(p,'rb').read()
    else:
        z=zipfile.ZipFile(src)
        for n in z.namelist():
            if n.endswith('.csv') or n.endswith('.json'): files[dec(n)]=z.read(n)
    rows=[]
    for n,b in files.items():
        parts=n.replace('\\','/').split('/')
        if n.endswith('.csv') and len(parts)>=2 and parts[-2]=='已儲存':
            lst=parts[-1][:-4]
            if lst in SKIP_LISTS: continue
            t=b.decode('utf-8-sig'); i=t.find('標題,')
            if i<0: continue
            for r in csv.DictReader(io.StringIO(t[i:])):
                if not (r.get('標題') or r.get('網址')): continue
                if '/maps/' not in (r.get('網址') or ''): continue
                rows.append((lst,(r['標題'] or '').strip(),(r.get('筆記') or '').strip(),(r.get('標籤') or '').strip(),r['網址']))
        elif n.endswith('已儲存的地點.json'):
            for f in json.loads(b).get('features',[]):
                p=f.get('properties',{});loc=p.get('location',{})
                name=loc.get('name') or ''
                url=p.get('google_maps_url','')
                if not name:
                    m=re.search(r'q=(?:[^&]*?\s)?([^\s&]+)&ftid',url); name=m.group(1) if m else ''
                if name: rows.append(('已加星號',name,loc.get('address',''),'',url))
    return rows

def key(name,url):
    m=re.search(r'1s(0x[0-9a-f]+:0x[0-9a-f]+)',url) or re.search(r'ftid=(0x[0-9a-f]+:0x[0-9a-f]+)',url) or re.search(r'cid=(\d+)',url)
    if m: return m.group(1)
    m=re.search(r'search/([-\d.]+,[-\d.]+)',url)
    return m.group(1) if m else nk(name)
def nk(n): return re.sub(r'[\s()（）]','',n)

CITIES='嘉義|高雄|台南|臺南|台中|臺中|台北|臺北|新北|桃園|新竹|苗栗|彰化|南投|雲林|屏東|宜蘭|花蓮|台東|臺東|基隆|澎湖|金門'
def region(name,notes):
    for t in (notes,name):
        m=re.search(r'('+CITIES+')(?:市|縣)?([\u4e00-\u9fff]{2})?(?:區|鎮|鄉|市)',t) or re.search(r'('+CITIES+')',t)
        if m: return (m.group(1).replace('臺','台')+(m.group(2) or '') if m.lastindex and m.lastindex>=2 else m.group(1).replace('臺','台'))
    return ''

def guess(name,notes,lists):
    t=name+' '+notes
    if re.search(r'[\u3040-\u30ff]|〒|Japan|日本',t) or any('日本' in l for l in lists): return '🇯🇵 日本旅遊'
    if '朋友的家' in lists or re.search(r'的家|師姐家|師兄家',notes): return '🏠 親友住家'
    if re.search(r'國術|推拿|理筋|整復|診所|醫院|中醫|復健',t): return '💆 國術推拿・診所'
    if re.search(r'素|蔬|vegan|Vegan|VEGAN|Vegetarian|plant-based',t) or '素食餐廳' in lists: return '🥬 素食餐廳'
    if re.search(r'宮|廟|寺|壇|代天府|順天府|天府|殿|古亭院|禪院|精舍|佛堂|Temple|Shrine',t): return '🙏 宮廟寺院'
    if re.search(r'溫泉|Onsen|飯店|旅館|民宿|山莊|Hotel|露營',t) or '溫泉清單' in lists: return '♨️ 溫泉住宿'
    if re.search(r'咖啡|Coffee|COFFEE|冰|餅|麵包|烘焙|茶飲|手搖|伴手禮|食品|甜點',t): return '☕ 咖啡甜點・伴手禮'
    if re.search(r'全聯|家樂福|超市|好市多|園藝|電器|學校|國中|國小|高中|大學|工程處|公所|協會|銀行|郵局|加油|五金|量販',t): return '🛒 生活・公務'
    return '🍜 美食小吃'

def short(n):
    n=re.sub(r'\s+',' ',n).strip()
    for sep in ('|','｜',' - '):
        if sep in n and n.index(sep)>=2: n=n[:n.index(sep)].strip()
    return n if len(n)<=30 else n[:30]+'…'

def main():
    src=sys.argv[1]; srcnote=sys.argv[2] if len(sys.argv)>2 else os.path.basename(src)
    data=json.load(open(os.path.join(ROOT,'places.json'),encoding='utf-8'))
    old={key(p.get('origName',p['name']),p['url']):p for p in data['places']}
    oldname={}
    for k,p in old.items():
        for n in (p['name'],p.get('origName','')):
            if n: oldname.setdefault(nk(n),k)
    rows=read_takeout(src)
    if not rows: sys.exit('找不到「已儲存」的地點資料，未更新')
    merged={}
    byname={}
    for lst,name,note,tag,url in rows:
        k=key(name,url)
        if k not in merged and nk(name) in byname: k=byname[nk(name)]
        if k not in old and k not in merged and nk(name) in oldname: k=oldname[nk(name)]
        byname.setdefault(nk(name),k)
        e=merged.setdefault(k,{'origName':name,'notes':[],'lists':[],'url':url})
        if lst not in e['lists']: e['lists'].append(lst)
        for x in (note,tag):
            if x and lst!='已加星號' and x not in e['notes']: e['notes'].append(x)
    out=[];new=[]
    for k,e in merged.items():
        notes='、'.join(e['notes'])
        if k in old:
            p=dict(old[k]); p.pop('isNew',None)
            p.update(lists=e['lists'],notes=notes,url=e['url'],origName=e['origName'])
        else:
            c=guess(e['origName'],notes,e['lists'])
            r='日本' if c.startswith('🇯🇵') else region(e['origName'],notes)
            p={'name':short(e['origName']),'origName':e['origName'],'cat':c,'region':r,'notes':notes,'lists':e['lists'],'url':e['url'],'isNew':True}
            new.append(p)
        out.append(p)
    removed=[p['name'] for k,p in old.items() if k not in merged]
    order=['🙏 宮廟寺院','🥬 素食餐廳','🍜 美食小吃','☕ 咖啡甜點・伴手禮','♨️ 溫泉住宿','💆 國術推拿・診所','🏠 親友住家','🛒 生活・公務','🇯🇵 日本旅遊']
    out.sort(key=lambda x:(order.index(x['cat']) if x['cat'] in order else 99,not x.get('isNew'),x['region']==''))
    data.update(updated=datetime.date.today().isoformat(),source=srcnote,places=out)
    json.dump(data,open(os.path.join(ROOT,'places.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    print(json.dumps({'total':len(out),'new':[(p['name'],p['cat'],p['region']) for p in new],'removed':removed},ensure_ascii=False,indent=1))
if __name__=='__main__': main()
