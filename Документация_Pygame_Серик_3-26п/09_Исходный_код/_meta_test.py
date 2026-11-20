import os, json, tempfile
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import pygame, game, progression as P, prog_ui as UI

s = game.new_save()
P.ensure(s)
s.update(money=500000, earned=400000, kills=500, level=9, won=False)
print("bp reward", P.bp_reward(s))
print("income", P.income_mult(s), "dmg", P.click_damage(s), "lives", P.start_lives(s))
res = P.rebirth(s)
print("rebirth", res, "money", s["money"], "level", s["level"], "bp", s["meta"]["bp"])
assert s["level"] >= 0 and s["meta"]["reborn"] == 1
# buy first affordable node
for u in P.META_UPGRADES:
    if P.can_buy_meta(s, u["key"]):
        print("buy", u["key"], P.buy_meta(s, u["key"]))
        break
# contracts
c=P.ensure(s)["contracts"]
print("contracts", c)
for cc in c: P.track(s, cc["kind"], cc["target"])
print("done", [x["done"] for x in P.ensure(s)["contracts"]])
if P.ensure(s)["contracts"][0]["done"]:
    print(P.claim_contract(s,0))
# relic choice
ch=P.ensure(s)["relic_choices"]
print("relic choices", ch)
if ch: print(P.take_relic(s,ch[0]))
# achievements
for _ in range(120): P.on_push(s)
print("ach", len(P.ensure(s)["ach"]), "bp", P.ensure(s)["bp"])
# drawing
canvas=game.canvas_buf
g=dict(depot=True, depot_tab=0, depot_confirm=0, toast="", toast_t=0, rate_show=10, boss=None, lives=5, hard_t=0, composite=None)
UI.draw_hud(canvas, s, g, (500,50), "Тест", False)
for tab in range(4):
    g["depot_tab"]=tab
    UI.draw_depot(canvas,s,g,(500,300))
    print("draw tab", tab, "ok")
# click tree node
g["depot_tab"]=0
key,r=UI._tree_rects()[0]
print("click tree", UI.depot_click(s,g,r.centerx,r.centery))
# save/load roundtrip
txt=json.dumps(s)
d=json.loads(txt); s2=game.new_save(); game.new_save(); s2.clear(); s2.update(game.new_save()); P.load_meta(s2,d)
print("meta roundtrip", s2["meta"]["reborn"], len(s2["meta"]["tree"]))

# ---------- узлы 3.1: ветки выросли до 9 узлов и эффекты реально влияют ----------
assert [len(P.META_BY_BRANCH[b]) for b in range(3)] == [9, 9, 9]
m = P.ensure(s2)
m["reborn"] = 6
m["bp"] = 9999
coin0, crit0 = P.coin_mult(s2), P.crit_mult(s2)
for _ in range(3):
    P.buy_meta(s2, "tips")
for _ in range(2):
    P.buy_meta(s2, "sharp")
for _ in range(4):
    P.buy_meta(s2, "seat")
for _ in range(3):
    P.buy_meta(s2, "peak")
P.buy_meta(s2, "revive")
P.buy_meta(s2, "premia")
assert P.coin_mult(s2) > coin0, (coin0, P.coin_mult(s2))
assert P.crit_mult(s2) > crit0, (crit0, P.crit_mult(s2))
assert P.capacity_bonus(s2) == 4
assert abs(P.rush_scale(s2) - 1.24) < 1e-6
assert P.revive_charges(s2) == 1
print("new nodes ok", round(P.coin_mult(s2), 3), round(P.crit_mult(s2), 3),
      P.capacity_bonus(s2), P.rush_scale(s2), P.revive_charges(s2))

# премия за станции добавляет ЧТ за каждый пройденный участок из 5 станций
s3 = game.new_save()
P.ensure(s3)
s3.update(money=0, earned=0, level=19)
P.ensure(s3)["bp"] = 999
P.ensure(s3)["reborn"] = 6
before = P.bp_reward(s3)
for _ in range(3):
    P.buy_meta(s3, "premia")
assert P.bp_reward(s3) > before, (before, P.bp_reward(s3))
print("premia ok", before, P.bp_reward(s3))

# дерево рисуется внутри панели: 9 рядов по 50 px
rects = [r for _, r in UI._tree_rects()]
assert len(rects) == 27
assert max(r.bottom for r in rects) <= UI.CONTENT_RECT.bottom, max(r.bottom for r in rects)
assert min(r.x for r in rects) >= UI.CONTENT_RECT.x
assert max(r.right for r in rects) <= UI.CONTENT_RECT.right
print("tree layout ok", max(r.bottom for r in rects), UI.CONTENT_RECT.bottom)
g["depot_tab"] = 0
UI.draw_depot(canvas, s2, g, (500, 300))
print("OK")
