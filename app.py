from flask import Flask, request, jsonify, send_from_directory
import os
import requests
from datetime import datetime

app = Flask(__name__, static_folder='public')

stores = {}

def generate_catalog(brand):
    name = brand.get('name', 'Aether Lifts')
    colors = brand.get('colors', ['Black', 'Navy'])
    style = brand.get('style', 'premium athletic')
    brand_slug = name.lower().replace(' ', '-')

    products = [
        {
            "title": f"{name} Performance Tee",
            "productType": "Performance Tee",
            "price": "48.00",
            "description": f"<p>Premium moisture-wicking training tee from {name}. Lightweight performance fabric built for movement.</p><ul><li>Moisture-wicking athletic fabric</li><li>Clean {style} fit</li><li>Minimal branding</li></ul>",
            "tags": [brand_slug, "performance", "tee", "apliiq"],
            "colors": colors,
            "sizes": ["S", "M", "L", "XL"]
        },
        {
            "title": f"{name} Training Shorts",
            "productType": "Training Shorts",
            "price": "54.00",
            "description": f"<p>Performance training shorts from {name}. Stretch fabric with athletic cut.</p><ul><li>Four-way stretch</li><li>Secure waistband</li><li>Quick-drying</li></ul>",
            "tags": [brand_slug, "shorts", "training", "apliiq"],
            "colors": colors,
            "sizes": ["S", "M", "L", "XL"]
        },
        {
            "title": f"{name} Rest Day Hoodie",
            "productType": "Hoodie",
            "price": "88.00",
            "description": f"<p>Heavyweight recovery hoodie from {name}. Soft, clean, built for off-days.</p><ul><li>Premium fleece</li><li>Relaxed athletic fit</li><li>Minimal branding</li></ul>",
            "tags": [brand_slug, "hoodie", "rest-day", "apliiq"],
            "colors": colors,
            "sizes": ["S", "M", "L", "XL"]
        },
        {
            "title": f"{name} Sports Bra",
            "productType": "Sports Bra",
            "price": "42.00",
            "description": f"<p>Supportive sports bra from {name}. Clean lines, medium support.</p><ul><li>Medium support</li><li>Stretch performance fabric</li><li>Minimal branding</li></ul>",
            "tags": [brand_slug, "sports-bra", "training", "apliiq"],
            "colors": colors,
            "sizes": ["XS", "S", "M", "L"]
        }
    ]

    apliig_guide = {
        "steps": [
            "Open Apliiq catalog and filter Activewear / Sport-Tek",
            f"Create Performance Tee with {name} logo",
            "Create Training Shorts on performance poly blank",
            "Create Rest Day Hoodie on performance fleece",
            "Create Sports Bra on ladies performance style",
            "Use 'Dropship this product' to push into Shopify",
            "Link to the product shells in your store",
            "Set products Active once confirmed"
        ],
        "recommendedBlanks": [
            "Sport-Tek PosiCharge Competitor Tee",
            "Performance athletic shorts",
            "Performance raglan or Sport-Tek hoodie",
            "Ladies PosiCharge tank or sports bra"
        ]
    }

    return {"brand": brand, "products": products, "apliigGuide": apliig_guide}

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    brand = request.json
    if not brand or not brand.get('name'):
        return jsonify({"error": "Brand name required"}), 400
    catalog = generate_catalog(brand)
    cid = datetime.now().strftime("%Y%m%d%H%M%S")
    stores[cid] = catalog
    return jsonify({"id": cid, "catalog": catalog})

@app.route('/api/catalog/<cid>')
def get_catalog(cid):
    catalog = stores.get(cid)
    if not catalog:
        return jsonify({"error": "Not found"}), 404
    return jsonify(catalog)

@app.route('/api/push-shopify', methods=['POST'])
def push_shopify():
    data = request.json
    cid = data.get('catalogId')
    catalog = stores.get(cid)
    if not catalog:
        return jsonify({"error": "Catalog not found"}), 404

    token = data.get('shopifyToken')
    domain = data.get('shopDomain', '').replace('https://', '').replace('http://', '').rstrip('/')
    if not token or not domain:
        return jsonify({"error": "shopifyToken and shopDomain required"}), 400

    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }
    base = f"https://{domain}/admin/api/2024-10"

    created = []
    for p in catalog['products']:
        variants = []
        for size in p['sizes']:
            for color in p['colors']:
                variants.append({
                    "price": p['price'],
                    "option1": size,
                    "option2": color,
                    "inventory_management": "shopify"
                })
        payload = {
            "product": {
                "title": p['title'],
                "body_html": p['description'],
                "vendor": catalog['brand']['name'],
                "product_type": p['productType'],
                "tags": ",".join(p['tags']),
                "status": "draft",
                "options": [{"name": "Size"}, {"name": "Color"}],
                "variants": variants
            }
        }
        r = requests.post(f"{base}/products.json", json=payload, headers=headers, timeout=30)
        if r.ok:
            created.append({"title": p['title'], "id": r.json()['product']['id']})
        else:
            created.append({"title": p['title'], "error": r.text[:200]})

    return jsonify({"status": "pushed", "created": created, "count": len(created)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
