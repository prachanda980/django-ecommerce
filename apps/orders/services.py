import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Order, OrderItem
from apps.products.models import Product
from django.shortcuts import get_object_or_404


class OrderService:

    @transaction.atomic
    def create_order(
        user,
        items,
        shipping_address,
        billing_address,
        payment_method,
        customer_phone=None,
    ):
        try:
            from apps.products.models import Product

            # 1. Lock Products
            product_ids = sorted([item["product_id"] for item in items])
            products = Product.objects.select_for_update().filter(id__in=product_ids)
            product_dict = {p.id: p for p in products}

            # 2. Calculate Totals
            calculated_subtotal = Decimal("0.00")
            for item in items:
                product = product_dict.get(item["product_id"])
                if not product or product.stock < item["quantity"]:
                    return {
                        "status": "error",
                        "message": f"Stock error for {product.name if product else 'item'}",
                    }
                calculated_subtotal += product.price * item["quantity"]

            # 3. Create Order Object
            txn_id = (
                f"COD-{timezone.now().timestamp()}" if payment_method == "cod" else None
            )
            order = Order.objects.create(
                user=user,
                subtotal=calculated_subtotal,
                total=calculated_subtotal,
                shipping_address=shipping_address,
                billing_address=billing_address or shipping_address,
                customer_email=user.email,
                customer_phone=customer_phone,
                payment_method=payment_method,
                transaction_id=txn_id,
            )

            # 4. Create Items & Deduct Stock
            for item in items:
                product = product_dict[item["product_id"]]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item["quantity"],
                    unit_price=product.price,
                    product_name_at_purchase=product.name,
                )
                product.stock -= item["quantity"]
                product.save(update_fields=["stock"])

            return {"status": "success", "order_number": order.order_number}

        except Exception as e:
            logging.error(f"Order Failed: {e}")
            return {"status": "error", "message": str(e)}

    @classmethod  
    def cancel_order(cls, order_id, user, reason=None): 
        """
        Cancels an order if it's in a cancellable state.
        Restores product stock securely.
        """
        try:
            with transaction.atomic():
                # 1. Get the order
                order = get_object_or_404(Order, id=order_id, user=user)

                # 2. Check if order can be cancelled
                if not order.can_cancel():
                    return {
                        "status": "error",
                        "message": "Order cannot be cancelled in its current state."
                    }

                # 3. Restore Stock for each item
                for item in order.items.all():
                    # Lock product to prevent race conditions
                    product = Product.objects.select_for_update().get(id=item.product.id)
                    product.stock += item.quantity
                    product.save()

                # 4. Update Order Status
                order.status = Order.Status.CANCELLED
                # Save the cancellation reason if your model has a field for it
                # order.cancellation_reason = reason 
                order.save()

                return {
                    "status": "success",
                    "message": "Order cancelled successfully."
                }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
