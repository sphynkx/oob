from db import get_pool


def _row_to_product_dict(row):
    d = dict(row)
    price = d.get("price")
    try:
        if price is not None:
            d["price"] = float(price)
    except Exception:
        pass
    return d


async def create_product_db(seller_id, title, description, price, currency, image_url):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO products (seller_id, title, description, price, currency, image_url)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, seller_id, title, description, price, currency, image_url, created_at, updated_at
            """,
            seller_id,
            title,
            description,
            price,
            currency,
            image_url,
        )
        return _row_to_product_dict(row)


async def list_products_db(limit=50, offset=0):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, seller_id, title, description, price, currency, image_url, created_at, updated_at
            FROM products
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        return [_row_to_product_dict(r) for r in rows]


async def get_product_db(product_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, seller_id, title, description, price, currency, image_url, created_at, updated_at
            FROM products
            WHERE id=$1
            """,
            product_id,
        )
        return _row_to_product_dict(row) if row else None


async def update_product_db(product_id, title, description, price, currency, image_url):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE products
            SET title=$2,
                description=$3,
                price=$4,
                currency=$5,
                image_url=$6,
                updated_at=NOW()
            WHERE id=$1
            RETURNING id, seller_id, title, description, price, currency, image_url, created_at, updated_at
            """,
            product_id,
            title,
            description,
            price,
            currency,
            image_url,
        )
        return _row_to_product_dict(row) if row else None


async def delete_product_db(product_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM products WHERE id=$1", product_id)


async def count_products_total_db():
    pool = get_pool()
    async with pool.acquire() as conn:
        val = await conn.fetchval("SELECT COUNT(*) FROM products")
        return int(val or 0)


async def count_products_by_seller_db(seller_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        val = await conn.fetchval("SELECT COUNT(*) FROM products WHERE seller_id=$1", seller_id)
        return int(val or 0)

