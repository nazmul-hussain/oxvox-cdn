"""Helpers to write Lab modules compactly. Each module script writes v1/data/labs/<id>.json."""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def C(q,s,o,a,x,adv=False): return _d({"t":"choose","q":q,"s":s,"o":o,"a":a,"x":x},adv)
def T(q,s,h,a,x,adv=False): return _d({"t":"type","q":q,"s":s,"hint":h,"a":a if isinstance(a,list) else [a],"x":x},adv)
def F(q,o,a,x,adv=False): return _d({"t":"fix","q":q,"o":o,"a":a,"x":x},adv)
def B(q,o,a,x,adv=False): return _d({"t":"bn","q":q,"o":o,"a":a,"x":x},adv)
def _d(d,adv):
    if adv: d["lv"]="adv"
    return d
def U(id,title,level,idea,ideaBn,pattern,uses,keys,traps,drills):
    return {"id":id,"title":title,"level":level,"idea":idea,"ideaBn":ideaBn,"timeline":[],
            "formula":[{"name":n,"pos":p,"neg":"","q":""} for n,p in pattern],
            "uses":[{"rule":r,"bn":b,"ex":e} for r,b,e in uses],"signals":keys,
            "traps":[{"wrong":w,"right":r,"why":y,"bn":b} for w,r,y,b in traps],"drills":drills}
def save(id,title,intro,introBn,units,mastery,decide=()):
    for u in units:
        for q in u["drills"]: _check(q)
    for q in mastery: _check(q)
    d={"title":title,"intro":intro,"introBn":introBn,"units":units,"mastery":mastery,
       "decide":[{"q":q,"yes":y,"no":n} for q,y,n in decide]}
    out=ROOT/"v1"/"data"/"labs"/f"{id}.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(d,ensure_ascii=False,indent=1)+"\n")
    print(id, sum(len(u["drills"]) for u in units), "+", len(mastery))
def _check(q):
    assert q.get("s","").count("___")<=1, q
    if q["t"]=="type": assert "___" in q["s"], q
    else: assert q["a"] in q["o"] and len(set(q["o"]))==len(q["o"]), q
