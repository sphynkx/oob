from fastapi import APIRouter, Depends, HTTPException, Query, status
from utils.schemas_ut import ProductCreate, ProductUpdate, ProductOut
from utils.security_ut import get_current_user
from services.products_service import (
    create_product_service,
    list_products_service,
    get_product_service,
    update_product_service,
    delete_product_service,
)

router = APIRouter()


@router.get("/products", response_model=list[ProductOut])
async def list_products(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    items = await list_products_service(limit=limit, offset=offset)
    return items


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(product_id: int):
    try:
        item = await get_product_service(product_id)
        return item
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.post("/products", response_model=ProductOut, status_code=201)
async def create_product(payload: ProductCreate, user=Depends(get_current_user)):
    try:
        item = await create_product_service(
            user=user,
            title=payload.title,
            description=payload.description,
            price=payload.price,
            currency=payload.currency,
            image_url=payload.image_url,
        )
        return item
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/products/{product_id}", response_model=ProductOut)
async def update_product(product_id: int, payload: ProductUpdate, user=Depends(get_current_user)):
    try:
        item = await update_product_service(
            user=user,
            product_id=product_id,
            title=payload.title,
            description=payload.description,
            price=payload.price,
            currency=payload.currency,
            image_url=payload.image_url,
        )
        return item
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(product_id: int, user=Depends(get_current_user)):
    try:
        await delete_product_service(user=user, product_id=product_id)
        return
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
