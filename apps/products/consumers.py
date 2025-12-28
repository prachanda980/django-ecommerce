import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from .models import Product

logger = logging.getLogger(__name__)

class ProductConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.product_id = self.scope['url_route']['kwargs']['product_id']
        self.group_name = f'product_{self.product_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        # Send immediate stock status on connect
        await self.send_initial_stock()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_initial_stock(self):
        stock_data = await self.get_stock_data()
        await self.send(text_data=json.dumps({
            'type': 'initial_stock',
            **stock_data
        }))

    async def stock_update(self, event):
        """Handler for broadcast messages."""
        await self.send(text_data=json.dumps({
            'type': 'stock_update',
            'product_id': event['product_id'],
            'new_stock': event['new_stock'],
            'timestamp': event.get('timestamp')
        }))

    @database_sync_to_async
    def get_stock_data(self):
        try:
            product = Product.objects.get(id=self.product_id)
            return {
                'product_id': product.id,
                'stock': product.stock,
                'available': product.available_stock
            }
        except Product.DoesNotExist:
            return {'stock': 0, 'available': 0}

# Utility function for external services (e.g. OrderService)
async def broadcast_stock_update(product_id, new_stock):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f'product_{product_id}',
        {
            'type': 'stock_update',
            'product_id': product_id,
            'new_stock': new_stock
        }
    )