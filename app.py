from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from datetime import datetime

app = Flask(__name__, static_folder='public')
stores = {}

PRICING = {
    "starter": {"name": "Starter", "price": 29, "products": 10, "stores": 1},
    "growth": {"name": "Growth", "price": 79, "products": 50, "stores": 3},
    "pro": {"name": "Pro", "price": 199, "products": 200, "stores": 10}
}

def generate_catalog(brand):
    name = brand.get('name', 'Aether Lifts')
    colors = brand.get('colors', ['Black', 'Navy'])
    style = brand.get('style', 'premium athletic')
    slug = name.lower().replace(' ', '-')

    products = [
        {"title": f"{name} Performance Tee", "type": "Performance Tee", "price": "48.00",
         "desc": f"<p>Premium moisture-wicking tee from {name}. Built for training.</p><ul><li>Moisture-wicking fabric</li><li>Athletic fit</li><li>Minimal branding</li></ul>",
         "tags": [slug, "performance", "tee", "apliiq"], "sizes": ["S","M","L","XL"]},
        {"title": f"{name} Training Shorts", "type": "Training Shorts", "price": "54.00",
         "desc": f"<p>Performance shorts from {name}. Stretch and move.</p><ul><li>Four-way stretch</li><li>Secure waistband</li></ul>",
         "tags": [slug, "shorts", "training", "apliiq"], "sizes": ["S","M","L","XL"]},
        {"title": f"{name} Rest Day Hoodie", "type": "Hoodie", "price": "88.00",
         "desc": f"<p>Heavyweight recovery hoodie from {name}.</p><ul><li>Premium fleece</li><li>Relaxed fit</li></ul>",
         "tags": [slug, "hoodie", "rest-day", "apliiq"], "sizes": ["S","M","L","XL"]},
        {"title": f"{name} Sports Bra", "type": "Sports Bra", "price": "42.00",
         "desc": f"<p>Supportive sports bra from {name}.</p><ul><li>Medium support</li><li>Clean design</li></ul>",
         "tags": [slug, "sports-bra", "apliiq"], "sizes": ["XS","S","M","L"]},
        {"title": f"{name} Lifting Straps", "type": "Accessory", "price": "28.00",
         "desc": f"<p>Premium lifting straps from {name}.</p>",
         "tags": [slug, "accessories", "apliiq"], "sizes": ["One Size"]}
    ]

    collections = [
        {"title": "Performance", "desc": "Training-ready pieces"},
        {"title": "Rest Day", "desc": "Recovery and everyday"},
        {"title": "Accessories", "desc": "Gym essentials"}
    ]

    return {
        "brand": brand,
        "products": products,
        "collections": collections,
        "apliiq": {
            "steps": [
                "Filter Apliiq catalog to Activewear / Sport-Tek",
                f"Design Performance Tee with {name} logo",
                "Design Training Shorts",
                "Design Rest Day Hoodie",
                "Design Sports Bra",
                "Push each via Dropship this product",
                "Link to shells or replace drafts"
            ]
        }
    }

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/pricing')
def pricing():
    return send_from_directory('public', 'pricing.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    brand = request.json or {}
    if not brand.get('name'):
        return jsonify({"error": "name required"}), 400
    catalog = generate_catalog(brand)
    cid = datetime.now().strftime("%Y%m%d%H%M%S")
    stores[cid] = catalog
    return jsonify({"id": cid, "catalog": catalog})

@app.route('/api/pricing')
def get_pricing():
    return jsonify(PRICING)

@app.route('/api/checkout', methods=['POST'])
def checkout():
    plan = request.json.get('plan', 'starter')
    if plan not in PRICING:
        return jsonify({"error": "invalid plan"}), 400
    return jsonify({
        "status": "ready",
        "plan": PRICING[plan],
        "message": "Connect Stripe to activate checkout",
        "stripe_price_id": f"price_{plan}_placeholder"
    })

@app.route('/api/push-shopify', methods=['POST'])
def push_shopify():
    data = request.json or {}
    catalog = stores.get(data.get('catalogId'))
    if not catalog:
        return jsonify({"error": "catalog not found"}), 404
    token = data.get('shopifyToken')
    domain = (data.get('shopDomain') or '').replace('https://','').replace('http://','').rstrip('/')
    if not token or not domain:
        return jsonify({"error": "token and domain required"}), 400

    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    base = f"https://{domain}/admin/api/2024-10"
    created = []
    for p in catalog['products']:
        variants = []
        for size in p['sizes']:
            for color in catalog['brand'].get('colors', ['Black']):
                variants.append({"price": p['price'], "option1": size, "option2": color})
        payload = {"product": {
            "title": p['title'], "body_html": p['desc'], "vendor": catalog['brand']['name'],
            "product_type": p['type'], "tags": ",".join(p['tags']), "status": "draft",
            "options": [{"name": "Size"}, {"name": "Color"}], "variants": variants
        }}
        r = requests.post(f"{base}/products.json", json=payload, headers=headers, timeout=30)
        created.append({"title": p['title'], "ok": r.ok, "id": r.json().get('product',{}).get('id') if r.ok else None})
    return jsonify({"status": "pushed", "created": created})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 7860))
    app.run(host='0.0.0.0', port=port)
