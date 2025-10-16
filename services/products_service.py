from db.products_db import (
    create_product_db,
    list_products_db,
    get_product_db,
    update_product_db,
    delete_product_db,
    count_products_total_db,
    count_products_by_seller_db,
)


def _ensure_seller_or_admin(user):
    role = (user.get("role") or "").lower()
    if role not in ("seller", "admin"):
        raise PermissionError("Forbidden")


def _ensure_owner_or_admin(user, seller_id):
    role = (user.get("role") or "").lower()
    if role == "admin":
        return
    if user["id"] != seller_id:
        raise PermissionError("Forbidden")


async def create_product_service(user, title, description, price, currency, image_url):
    _ensure_seller_or_admin(user)
    if not title or price is None:
        raise ValueError("Title and price are required")
    currency_val = currency or "USD"
    product = await create_product_db(
        user["id"],
        title,
        description,
        float(price),
        currency_val,
        image_url,
    )
    return product


async def list_products_service(limit=50, offset=0):
    limit = min(max(int(limit), 1), 100)
    offset = max(int(offset), 0)
    return await list_products_db(limit=limit, offset=offset)


async def get_product_service(product_id):
    product = await get_product_db(product_id)
    if not product:
        raise LookupError("Not found")
    return product


async def update_product_service(
    user,
    product_id,
    title=None,
    description=None,
    price=None,
    currency=None,
    image_url=None,
):
    existing = await get_product_db(product_id)
    if not existing:
        raise LookupError("Not found")
    _ensure_owner_or_admin(user, existing["seller_id"])
    new_title = title if title is not None else existing["title"]
    new_description = description if description is not None else existing["description"]
    new_price = float(price) if price is not None else float(existing["price"])
    new_currency = currency if currency is not None else existing["currency"]
    new_image_url = image_url if image_url is not None else existing["image_url"]
    updated = await update_product_db(
        product_id,
        new_title,
        new_description,
        new_price,
        new_currency,
        new_image_url,
    )
    return updated


async def delete_product_service(user, product_id):
    existing = await get_product_db(product_id)
    if not existing:
        return
    _ensure_owner_or_admin(user, existing["seller_id"])
    await delete_product_db(product_id)


async def get_products_stats_service(user_id):
    total = await count_products_total_db()
    mine = await count_products_by_seller_db(user_id)
    return {"total": total, "mine": mine}

