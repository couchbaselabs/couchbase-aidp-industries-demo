"""Retail & E-Commerce — Staples, Walmart, Tesco, Domino's."""
from app.industries.base import Agent, AgentDecision, CopilotAction, Industry, KPI
from app.industries.utils import avg, count_where, top_by

SEED_ORDERS = [
    {"id": "ORD-1001", "customer_name": "Maria Chen", "channel": "app", "items": "Wireless mouse, USB-C hub", "order_value": 84.50, "store_id": "STL-014", "loyalty_tier": "Gold", "ship_to_state": "TX", "stock_on_hand": 2, "reorder_point": 8, "past_categories": "electronics, office"},
    {"id": "ORD-1002", "customer_name": "Devon Wright", "channel": "web", "items": "Office chair", "order_value": 219.00, "store_id": "STL-014", "loyalty_tier": "Silver", "ship_to_state": "CA", "stock_on_hand": 0, "reorder_point": 5, "past_categories": "furniture, office"},
    {"id": "ORD-1003", "customer_name": "Priya Nair", "channel": "store", "items": "Notebook 5-pack, pens", "order_value": 18.75, "store_id": "STL-002", "loyalty_tier": "Gold", "ship_to_state": "NY", "stock_on_hand": 44, "reorder_point": 10, "past_categories": "school, office"},
    {"id": "ORD-1004", "customer_name": "James Okafor", "channel": "app", "items": "Laser printer", "order_value": 329.99, "store_id": "STL-031", "loyalty_tier": "Platinum", "ship_to_state": "IL", "stock_on_hand": 1, "reorder_point": 6, "past_categories": "electronics, printing"},
    {"id": "ORD-1005", "customer_name": "Sofia Ramirez", "channel": "web", "items": "Desk lamp, extension cord", "order_value": 41.20, "store_id": "STL-002", "loyalty_tier": "Bronze", "ship_to_state": "NY", "stock_on_hand": 15, "reorder_point": 10, "past_categories": "home office"},
    {"id": "ORD-1006", "customer_name": "Liam Patel", "channel": "store", "items": "Backpack, water bottle", "order_value": 62.00, "store_id": "STL-031", "loyalty_tier": "Silver", "ship_to_state": "IL", "stock_on_hand": 3, "reorder_point": 12, "past_categories": "outdoor, school"},
    {"id": "ORD-1007", "customer_name": "Grace Kim", "channel": "app", "items": "Monitor arm, cable ties", "order_value": 97.40, "store_id": "STL-014", "loyalty_tier": "Gold", "ship_to_state": "TX", "stock_on_hand": 0, "reorder_point": 4, "past_categories": "electronics, office"},
    {"id": "ORD-1008", "customer_name": "Noah Fischer", "channel": "web", "items": "Paper shredder", "order_value": 74.99, "store_id": "STL-002", "loyalty_tier": "Bronze", "ship_to_state": "NY", "stock_on_hand": 9, "reorder_point": 6, "past_categories": "office, security"},
]


def _inventory_agent(entity: dict, all_entities: list) -> AgentDecision:
    on_hand, reorder = entity["stock_on_hand"], entity["reorder_point"]
    if on_hand == 0:
        rec, sev, impact = "Fulfill from nearest DC and trigger emergency reorder", "critical", ("Stockout risk", entity["store_id"])
        fallback = f"{entity['store_id']} shows 0 units on hand against a reorder point of {reorder} — recommend DC fulfillment and an emergency reorder."
        confidence = 0.95
    elif on_hand < reorder:
        rec, sev, impact = "Transfer stock from a nearby store before reordering", "warning", ("Units below reorder point", str(reorder - on_hand))
        fallback = f"{entity['store_id']} has {on_hand} units against a reorder point of {reorder} — check nearby stores for a transfer before placing a new PO."
        confidence = 0.8
    else:
        rec, sev, impact = "No action needed — stock is healthy", "positive", ("Units on hand", str(on_hand))
        fallback = f"{entity['store_id']} has {on_hand} units on hand, comfortably above the {reorder}-unit reorder point."
        confidence = 0.9
    return AgentDecision(rec, fallback, confidence, impact[0], impact[1], {"stock_on_hand": on_hand, "reorder_point": reorder, "store_id": entity["store_id"]}, sev)


def _recommendation_agent(entity: dict, all_entities: list) -> AgentDecision:
    category = entity["past_categories"].split(",")[0].strip()
    same_category = [e for e in all_entities if e["id"] != entity["id"] and category in e["past_categories"]]
    cross_sell = same_category[0]["items"] if same_category else "a related accessory"
    fallback = f"Customers who bought into '{category}' recently also bought {cross_sell} — surface it as a cross-sell on the confirmation page."
    return AgentDecision(
        f"Recommend: {cross_sell}", fallback, 0.72, "Loyalty tier", entity["loyalty_tier"],
        {"category": category, "cross_sell": cross_sell, "loyalty_tier": entity["loyalty_tier"]}, "info",
    )


INDUSTRY = Industry(
    id="retail",
    name="Retail & E-Commerce",
    tagline="Omnichannel shopping, real-time inventory, and personalization on one AI data plane.",
    icon="🛒",
    examples=["Staples", "Walmart", "Tesco", "Domino's"],
    entity_label="Order",
    entity_label_plural="Orders",
    entity_title_field="id",
    entity_subtitle_field="customer_name",
    kpis=[
        KPI("open_orders", "Open Orders", lambda es: len(es)),
        KPI("stockout_risk", "Stockout-Risk Orders", lambda es: count_where(es, lambda e: e["stock_on_hand"] < e["reorder_point"])),
        KPI("avg_order_value", "Avg Order Value", lambda es: round(avg(es, lambda e: e["order_value"]), 2), "currency"),
        KPI("gold_plus", "Gold+ Loyalty Orders", lambda es: count_where(es, lambda e: e["loyalty_tier"] in ("Gold", "Platinum"))),
    ],
    agents=[
        Agent("inventory-rebalancing", "Inventory Rebalancing Agent", "Flags stockout/reorder risk and recommends store-transfer vs. DC fulfillment vs. reorder.", _inventory_agent, lambda e: f"check inventory on hand for store {e['store_id']}"),
        Agent("personalized-recommendation", "Personalized Recommendation Agent", "Recommends a cross-sell/upsell product from the customer's purchase-category history.", _recommendation_agent, lambda e: f"get customer 360 profile for {e['customer_name']}"),
    ],
    copilot_actions=[
        CopilotAction("priority", "My priority", lambda e, es: f"Highest stockout risk: {top_by(es, lambda x: x['reorder_point'] - x['stock_on_hand'])['id']} ({top_by(es, lambda x: x['reorder_point'] - x['stock_on_hand'])['store_id']})."),
        CopilotAction("check-inventory", "Check inventory", lambda e, es: f"Order {e['id']} ships from {e['store_id']} with {e['stock_on_hand']} units on hand." if e else "Select an order first.", lambda e: f"check inventory for store {e['store_id']}" if e else "check inventory"),
        CopilotAction("customer-360", "Customer 360 summary", lambda e, es: f"{e['customer_name']} is {e['loyalty_tier']} tier, channel {e['channel']}, past categories: {e['past_categories']}." if e else "Select an order first."),
    ],
    mcp_namespace="retail",
    seed_entities=SEED_ORDERS,
    roadmap=[
        "Omnichannel shopping experiences — unified cart/session state across web, app, and in-store.",
        "Full Customer 360 profiles — this demo only reads recent purchase categories, not a durable cross-channel profile.",
        "High-speed checkout caching — this demo caches order-level agent decisions, not the POS checkout path itself.",
    ],
    color="#ea580c",
)
