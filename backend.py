from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import time
import random
import re
import asyncio
from datetime import datetime, timezone
from typing import Dict, List

# --- FIREBASE ADMIN (Optional for Google Auth Verification) ---
try:
    import firebase_admin
    from firebase_admin import credentials, auth
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={'projectId': 'apperture-4889e'})
    FIREBASE_ADMIN_AVAILABLE = True
except ImportError:
    FIREBASE_ADMIN_AVAILABLE = False

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import httpx

app = FastAPI(title="Apperture Real-Time Multiplayer Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "database.json"

ADMIN_SECRET_KEY = "divyanshgupta.Apperture.Elderweb.com@passkey142682920252717"
CO_ADMIN_KEYS = [
    "C0=Admin.4regtz@apperture.Nexus", "C0-Adminzzzz@apperture.Nexus",
    "Sanyam.Gupta4regt@Apperture.Nexus", "Naman.Ahuja4tagei@Apperture.Nexus", "Madhav.bHAIChara4redis@Apperture.Nexus"
]

COUPONS = {
    "APERTURE-VISION-BONUS-Q4M81": {"s": 500, "g": 7, "t": 3},
    "APERTURE-ELITE-SAVINGS-Z9K27": {"s": 1000, "g": 20, "t": 10},
    "APERTURE-GOLD-PASS-R8T63": {"s": 1000, "g": 20, "t": 10},
    "APERTURE-MAX-DEAL-P5X91": {"s": 1000, "g": 20, "t": 10},
    "APERTURE-PRO-OFFER-L2V78": {"s": 750, "g": 12, "t": 6},
    "APERTURE-BOOST-REWARD-N6Q54": {"s": 750, "g": 12, "t": 6},
    "APERTURE-PREMIUM-GIFT-X1Z86": {"s": 1000, "g": 20, "t": 10},
    "APERTURE-ULTRA-SALE-M9K32": {"s": 1000, "g": 20, "t": 10},
    "APERTURE-FAST-CASHBACK-T7R18": {"s": 500, "g": 7, "t": 3},
    "APERTURE-MEGA-DROP-Q2L97": {"s": 1000, "g": 20, "t": 10},
    "APERTURE-PLUS-ADVANTAGE-V8X41": {"s": 750, "g": 12, "t": 6},
    "APERTURE-NOVA-DEAL-Z5T26": {"s": 1000, "g": 20, "t": 10},
    "APERTURE-POWER-SAVER-R3M84": {"s": 500, "g": 7, "t": 3},
    "APERTURE-PRIME-LISTING-K9Q71": {"s": 750, "g": 12, "t": 6},
    "APERTURE-FLASH-BONUS-X6L23": {"s": 500, "g": 7, "t": 3},
    "APERTURE-EDGE-OFFER-T1Z95": {"s": 750, "g": 12, "t": 6},
    "APERTURE-CORE-REWARD-M8V62": {"s": 500, "g": 7, "t": 3},
    "APERTURE-LITE-PASS-Q7R14": {"s": 300, "g": 5, "t": 2},
    "APERTURE-MARKET-BOOST-P9X53": {"s": 750, "g": 12, "t": 6},
    "APERTURE-SELLER-PRO-K2T87": {"s": 1000, "g": 20, "t": 10},
    "APERTURE-DAILY-PERK-L4Z19": {"s": 200, "g": 2, "t": 1},
    "APERTURE-TOP-CHOICE-X8M46": {"s": 750, "g": 12, "t": 6},
    "APERTURE-FREE-ADVANCE-R5Q92": {"s": 500, "g": 7, "t": 3},
    "APERTURE-SUPER-ACCESS-V1K73": {"s": 1000, "g": 20, "t": 10},
    "APERTURE-REWARD-PRIME-X7L92": {"s": 750, "g": 12, "t": 6}
}

# --- EXTERNAL WEBSOCKET NOTIFIER ---
# Replace this URL with your deployed WebSocket server URL in production
WS_SERVER_URL = os.getenv("WS_SERVER_URL", "http://localhost:8001")

async def notify_ws(payload: dict, user_id: str = None):
    """Sends a webhook to the external WebSocket server to broadcast or DM."""
    async with httpx.AsyncClient() as client:
        try:
            headers = {"Authorization": f"Bearer {ADMIN_SECRET_KEY}"}
            if user_id:
                await client.post(f"{WS_SERVER_URL}/internal/send/{user_id}", json=payload, headers=headers)
            else:
                await client.post(f"{WS_SERVER_URL}/internal/broadcast", json=payload, headers=headers)
        except Exception as e:
            print(f"WebSocket Notification Failed: {e}")

# --- DATABASE LOGIC ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {
            "users": {}, "listings": [], "cart": {}, "chats": [], 
            "messages": [], "notifications": [], "supremeAds": [], 
            "rewards": {}, "votes": {}
        }
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def now_ms(): return int(time.time() * 1000)
def get_utc_date(ts_ms): return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).date()

# --- REST ENDPOINTS ---

@app.post("/auth")
async def auth_route(request: Request):
    body = await request.json()
    db = load_db()
    is_google_auth = body.get("isGoogleAuth", False)
    
    if is_google_auth:
        email, username, profile_pic = body.get("email"), body.get("username"), body.get("profile_pic", "")
        existing_id = next((k for k, v in db["users"].items() if v.get("email") == email or v.get("name") == username), None)
        if existing_id:
            return {"status": "logged_in", "reward": "Google Sign-In Successful!", "user_id": existing_id}
        else:
            new_id = f"user_{now_ms()}"
            db["users"][new_id] = {
                "id": new_id, "name": username, "email": email, "password": "OAUTH_SECURE", 
                "address": "Verified via Google", "role": "both", "isAdmin": False, "isCoAdmin": False, 
                "stars": 10, "gems": 1, "tickets": 1, "profilePic": profile_pic, "usedCoupons": []
            }
            save_db(db)
            return {"status": "created", "reward": "Google Account Linked! Profile Created.", "user_id": new_id}

    username, password, referral = body.get("username"), body.get("password"), body.get("referral")
    is_login = body.get("isLogin", False)
    
    existing_id = next((k for k, v in db["users"].items() if v["name"] == username), None)

    if is_login:
        if not existing_id: raise HTTPException(status_code=404, detail="User not found.")
        if db["users"][existing_id]["password"] != password: raise HTTPException(status_code=401, detail="Incorrect Password.")
        return {"status": "logged_in", "reward": "Welcome Back!", "user_id": existing_id}
    else:
        if existing_id: raise HTTPException(status_code=400, detail="Username already taken.")
        
        is_admin, is_co_admin, start_stars, start_gems, start_tickets = False, False, 10, 1, 1
        reward_msg = "Profile Created! Free ticket awarded."
        
        if referral:
            if referral == ADMIN_SECRET_KEY: is_admin = True
            elif referral in CO_ADMIN_KEYS: is_co_admin = True
            else:
                referrer_id = next((k for k, v in db["users"].items() if v["name"] == referral), None)
                if referrer_id:
                    db["users"][referrer_id]["stars"] += 50
                    db["users"][referrer_id]["gems"] += 2
                    start_stars += 50; start_gems += 2
                    reward_msg = "Profile Created! Friend Referral applied: +50 Stars & +2 Gems bonus!"
                else:
                    raise HTTPException(status_code=400, detail="Invalid Referral Code.")

        new_id = f"user_{now_ms()}"
        db["users"][new_id] = {
            "id": new_id, "name": username, "password": password, "address": body.get("address"), 
            "role": body.get("role", "both"), "isAdmin": is_admin, "isCoAdmin": is_co_admin, 
            "stars": start_stars, "gems": start_gems, "tickets": start_tickets,
            "profilePic": body.get("profile_pic", ""), "usedCoupons": []
        }
        save_db(db)
        return {"status": "created", "reward": reward_msg, "user_id": new_id}

@app.put("/profile")
async def update_profile(request: Request):
    body = await request.json()
    user_id = request.headers.get("user-id")
    db = load_db()
    user = db["users"].get(user_id)
    if not user: raise HTTPException(status_code=401, detail="Unauthorized")

    reward_msg = None
    coupon = body.get("coupon", "").strip()
    if coupon and coupon in COUPONS:
        if coupon in user.get("usedCoupons", []): raise HTTPException(status_code=400, detail="Already redeemed.")
        reward = COUPONS[coupon]
        user["stars"] += reward["s"]; user["gems"] += reward["g"]; user["tickets"] += reward["t"]
        user.setdefault("usedCoupons", []).append(coupon)
        reward_msg = f"Coupon Redeemed! +{reward['s']} Stars, +{reward['g']} Gems, +{reward['t']} Tickets"
        
    new_name = body.get("name")
    if new_name == ADMIN_SECRET_KEY: new_name = "Divyansh Gupta"; user["isAdmin"] = True
    if new_name: user["name"] = new_name
    if body.get("address"): user["address"] = body.get("address")
    if body.get("profile_pic"): user["profilePic"] = body.get("profile_pic")
    
    save_db(db)
    await notify_ws({"type": "profile_update", "user_id": user_id, "name": user["name"]})
    return {"status": "updated", "reward": reward_msg}

@app.post("/sync")
async def sync_data(request: Request):
    user_id = request.headers.get("user-id", "Guest")
    db = load_db()
    now = now_ms()
    
    db["supremeAds"] = [a for a in db["supremeAds"] if a.get("endTime", 0) > now]
    db["notifications"] = [n for n in db["notifications"] if n.get("expiresAt", 0) > now]
    
    for uid, claim in db["rewards"].items():
        if claim.get("streak", 0) > 0:
            if (get_utc_date(now) - get_utc_date(claim["lastClaimed"])).days > 1:
                claim["streak"] = 0

    save_db(db)
    my_notifs = [n for n in db["notifications"] if n.get("recipient_id") == user_id or (not n.get("recipient_id") and n.get("type") in ['admin_alert', 'sys']) or (n.get("type") == 'user_ad' and not n.get("recipient_id") and n.get("scheduledFor", 0) <= now)]
    
    return {
        "listings": db["listings"],
        "notifications": my_notifs,
        "my_scheduled": [n for n in db["notifications"] if n.get("poster_id") == user_id and n.get("type") == "user_ad"],
        "my_supreme": [a for a in db["supremeAds"] if a.get("buyerId") == user_id],
        "chats": [c for c in db["chats"] if user_id in c.get("participants", [])],
        "supreme_ads": db["supremeAds"],
        "profile": db["users"].get(user_id, {"name": "Guest", "isAdmin": False, "stars": 0, "gems": 0, "tickets": 0}),
        "rewards": db["rewards"].get(user_id, {"streak": 0, "lastClaimed": 0})
    }

# --- LISTINGS / MULTIPLAYER HUB ---
@app.post("/listings")
async def create_listing(request: Request):
    body = await request.json()
    user_id = request.headers.get("user-id")
    db = load_db()
    user = db["users"].get(user_id)
    if not user: raise HTTPException(status_code=401, detail="Unauthorized")

    new_id = now_ms()
    listing = {
        "id": new_id, "sellerId": user_id, "sellerName": user["name"],
        "title": body.get("title"), "category": body.get("category"),
        "price": body.get("price"), "currency": body.get("currency"),
        "description": body.get("description"), "condition": body.get("condition"),
        "address": body.get("address"), "image_data": body.get("image_data"), 
        "images": body.get("images", []), "isMagnetic": body.get("isMagnetic", False), 
        "starsCount": 0, "timestamp": new_id
    }
    db["listings"].append(listing)
    save_db(db)
    await notify_ws({"type": "new_listing", "data": listing}) # 🔴 MULTIPLAYER BROADCAST
    return {"status": "created", "id": new_id}

@app.delete("/listings/{item_id}")
async def delete_listing(item_id: int, request: Request):
    user_id = request.headers.get("user-id")
    db = load_db()
    user = db["users"].get(user_id)
    item = next((l for l in db["listings"] if l["id"] == item_id), None)
    
    if item and (item["sellerId"] == user_id or user.get("isAdmin")):
        db["listings"] = [l for l in db["listings"] if l["id"] != item_id]
        save_db(db)
        await notify_ws({"type": "listing_deleted", "id": item_id}) # 🔴 MULTIPLAYER BROADCAST
        return {"status": "deleted"}
    raise HTTPException(status_code=403, detail="Unauthorized")

@app.post("/listings/{item_id}/star")
async def star_listing(item_id: int, request: Request):
    user_id = request.headers.get("user-id")
    db = load_db()
    if not user_id: raise HTTPException(status_code=401, detail="Unauthorized")
    
    item = next((l for l in db["listings"] if l["id"] == item_id), None)
    if not item: raise HTTPException(status_code=404, detail="Item not found")
    
    if user_id not in db.setdefault("votes", {}): db["votes"][user_id] = []
    if item_id in db["votes"][user_id]: raise HTTPException(status_code=400, detail="Already starred")
    if len(db["votes"][user_id]) >= 20: raise HTTPException(status_code=400, detail="Max 20 stars")
    
    db["votes"][user_id].append(item_id)
    item["starsCount"] = item.get("starsCount", 0) + 1
    save_db(db)
    
    await notify_ws({"type": "listing_update", "listing": item}) # 🔴 MULTIPLAYER BROADCAST
    return {"stars": item["starsCount"], "message": "Starred +1!"}

@app.post("/listings/{item_id}/boost")
async def boost_listing(item_id: int, request: Request):
    body = await request.json()
    user_id = request.headers.get("user-id")
    db = load_db()
    user = db["users"].get(user_id)
    item = next((l for l in db["listings"] if l["id"] == item_id), None)
    
    if item:
        if user["gems"] < 25 and not body.get("paid"): raise HTTPException(status_code=400, detail="Insufficient Gems")
        if not body.get("paid"): user["gems"] -= 25
        item["isMagnetic"] = True
        item["gemBoosted"] = not body.get("paid")
        item["timestamp"] = now_ms() # Bump to top
        save_db(db)
        await notify_ws({"type": "listing_update", "listing": item}) # 🔴 MULTIPLAYER BROADCAST
        return {"status": "boosted"}
    raise HTTPException(status_code=404, detail="Not Found")

# --- CHATS & COMMS ---
@app.post("/chats")
async def create_chat(request: Request):
    body = await request.json()
    user_id = request.headers.get("user-id")
    db = load_db()
    new_chat = {
        "id": now_ms(), "participants": body.get("participants", []),
        "names": body.get("names", []), "last_message": body.get("lastMessage", ""), "last_updated": now_ms()
    }
    db["chats"].append(new_chat)
    save_db(db)

    recipient = next((p for p in new_chat["participants"] if p != user_id), None)
    if recipient:
        await notify_ws({"type": "new_chat", "chat_data": new_chat}, user_id=recipient)
    return {"id": new_chat["id"]}

@app.get("/chats/{chat_id}/messages")
async def get_messages(chat_id: int):
    return [m for m in load_db()["messages"] if m["chatId"] == chat_id]

@app.post("/chats/{chat_id}/messages")
async def send_message(chat_id: int, request: Request):
    body = await request.json()
    user_id = request.headers.get("user-id")
    db = load_db()
    new_msg = {"chatId": chat_id, "text": body.get("text"), "sender_id": user_id, "timestamp": now_ms()}
    db["messages"].append(new_msg)
    
    chat = next((c for c in db["chats"] if c["id"] == chat_id), None)
    if chat:
        chat["last_message"] = body.get("text"); chat["last_updated"] = now_ms()
        recipient = next((p for p in chat["participants"] if p != user_id), None)
        if recipient: await notify_ws({"type": "chat_message", "chat_id": chat_id, "message_data": new_msg}, user_id=recipient)
    save_db(db)
    return {"status": "sent"}

@app.post("/notifications")
async def handle_notifications(request: Request):
    body = await request.json()
    db = load_db()
    now = now_ms()
    
    if body.get("type") == 'admin_alert':
        new_notif = {**body, "scheduledFor": now, "expiresAt": now + 86400000}
        db["notifications"].append(new_notif)
        save_db(db)
        await notify_ws({"type": "global_alert", "data": new_notif}) # 🔴 MULTIPLAYER ALERTS
        return {"status": "sent"}
    
    # Handle user_ad logic...
    return {"status": "processed"}

# --- GAMIFICATION & ECONOMY ---
@app.post("/daily-rewards")
async def claim_reward(request: Request):
    user_id = request.headers.get("user-id")
    db = load_db()
    user = db["users"].get(user_id)
    claim = db["rewards"].setdefault(user_id, {"streak": 0, "lastClaimed": 0})
    
    now = now_ms()
    days_diff = 1 if claim["lastClaimed"] == 0 else (get_utc_date(now) - get_utc_date(claim["lastClaimed"])).days
    if claim["lastClaimed"] > 0 and days_diff == 0: raise HTTPException(status_code=400, detail="Already claimed today.")
    if days_diff > 1 or claim["streak"] >= 7: claim["streak"] = 0
    
    claim["streak"] += 1; claim["lastClaimed"] = now
    
    reward_str = ""
    if claim["streak"] == 1: user["stars"] += 30; reward_str = "30 Stars"
    elif claim["streak"] == 2: user["stars"] += 80; reward_str = "80 Stars"
    elif claim["streak"] == 3: user["stars"] += 300; reward_str = "300 Stars"
    elif claim["streak"] == 4: user["tickets"] += 2; reward_str = "2 Tickets"
    elif claim["streak"] == 5: user["gems"] += 1; reward_str = "1 Gem"
    elif claim["streak"] == 6: user["stars"] += 500; user["gems"] += 1; reward_str = "500 Stars & 1 Gem"
    elif claim["streak"] == 7: user["gems"] += 1; reward_str = "1 Gem"
    
    save_db(db)
    return {"status": "claimed", "reward": reward_str}

@app.post("/wheel/spin")
async def spin_wheel(request: Request):
    user_id = request.headers.get("user-id")
    db = load_db()
    user = db["users"].get(user_id)
    
    if user["tickets"] < 1 and not user.get("isAdmin"): raise HTTPException(status_code=400, detail="Requires 1 Ticket")
    if not user.get("isAdmin"): user["tickets"] -= 1
    
    r = random.random()
    if r < 0.08: prize = "Legendary Jackpot"; user["stars"] += 300; user["gems"] += 3; user["tickets"] += 2
    elif r < 0.20: prize = "1 Ticket"; user["tickets"] += 1
    elif r < 0.40: prize = "1 Gem & 30 Stars"; user["gems"] += 1; user["stars"] += 30
    elif r < 0.60: prize = "1 Gem"; user["gems"] += 1
    elif r < 0.68: prize = "200 Stars"; user["stars"] += 200
    elif r < 0.88: prize = "40 Stars"; user["stars"] += 40
    else: prize = "10 Stars"; user["stars"] += 10
    
    save_db(db)
    return {"prize": prize}

@app.post("/ads/supreme")
async def book_supreme(request: Request):
    body = await request.json()
    user_id = request.headers.get("user-id")
    db = load_db()
    now = now_ms()
    target_slot = body.get("slot")
    
    active_ads = [a for a in db["supremeAds"] if a["slot"] == target_slot and a["endTime"] > now]
    if active_ads: raise HTTPException(status_code=400, detail="Space Occupied!")
    if random.random() > 0.98: raise HTTPException(status_code=409, detail="ERR_303_SLOT_COLLISION")
    
    db["supremeAds"].append({**body, "buyerId": user_id, "startTime": now, "endTime": now + 86400000})
    save_db(db)
    await notify_ws({"type": "ads_updated"}) # 🔴 MULTIPLAYER BROADCAST
    return {"status": "booked"}

# --- ADMIN ROUTES ---
@app.get("/admin/users")
async def get_users(request: Request):
    db = load_db()
    return [{"id": u["id"], "name": u["name"], "role": u["role"], "isAdmin": u["isAdmin"], "isBanned": u.get("isBanned", False)} for u in db["users"].values()]

@app.post("/admin/users/{target_id}/ban")
async def ban_user(target_id: str, request: Request):
    db = load_db()
    if target_id in db["users"]:
        db["users"][target_id]["isBanned"] = True
        save_db(db)
        return {"status": "banned"}
    raise HTTPException(status_code=404, detail="User not found")