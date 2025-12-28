/**
 * WebSocket connection management for real-time product updates
 */

class ProductWebSocketManager {
    constructor() {
        this.connections = new Map();
        this.reconnectAttempts = new Map();
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 5000; // 5 seconds
    }
    
    /**
     * Connect to a product's WebSocket for real-time updates
     * @param {number} productId - The product ID to connect to
     * @param {Function} onMessage - Callback for incoming messages
     * @param {Function} onConnect - Callback for successful connection
     * @param {Function} onDisconnect - Callback for disconnection
     */
    connect(productId, onMessage = null, onConnect = null, onDisconnect = null) {
        if (this.connections.has(productId)) {
            console.warn(`Already connected to product ${productId}`);
            return;
        }
        
        const wsUrl = `ws://localhost:8000/ws/products/${productId}/`;
        const ws = new WebSocket(wsUrl);
        
        // Store connection metadata
        const connectionData = {
            ws: ws,
            productId: productId,
            onMessage: onMessage,
            onConnect: onConnect,
            onDisconnect: onDisconnect,
            isConnected: false,
            reconnectCount: 0
        };
        
        this.connections.set(productId, connectionData);
        this.setupEventHandlers(connectionData);
    }
    
    /**
     * Setup WebSocket event handlers
     * @param {Object} connectionData - Connection metadata
     */
    setupEventHandlers(connectionData) {
        const { ws, productId, onConnect, onMessage, onDisconnect } = connectionData;
        
        ws.onopen = (event) => {
            console.log(`Connected to product ${productId} WebSocket`);
            connectionData.isConnected = true;
            connectionData.reconnectCount = 0;
            this.reconnectAttempts.delete(productId);
            
            // Update UI connection status
            this.updateConnectionStatus(productId, 'connected');
            
            // Call custom connect handler
            if (onConnect) {
                onConnect(event, productId);
            }
        };
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log(`WebSocket message for product ${productId}:`, data);
                
                // Handle different message types
                this.handleMessage(productId, data);
                
                // Call custom message handler
                if (onMessage) {
                    onMessage(data, productId);
                }
            } catch (error) {
                console.error(`Error parsing WebSocket message for product ${productId}:`, error);
            }
        };
        
        ws.onclose = (event) => {
            console.log(`Disconnected from product ${productId} WebSocket`);
            connectionData.isConnected = false;
            this.updateConnectionStatus(productId, 'disconnected');
            
            // Attempt reconnection
            this.attemptReconnect(productId);
            
            // Call custom disconnect handler
            if (onDisconnect) {
                onDisconnect(event, productId);
            }
        };
        
        ws.onerror = (error) => {
            console.error(`WebSocket error for product ${productId}:`, error);
            this.updateConnectionStatus(productId, 'error');
        };
    }
    
    /**
     * Handle different types of WebSocket messages
     * @param {number} productId - The product ID
     * @param {Object} data - The message data
     */
    handleMessage(productId, data) {
        switch (data.type) {
            case 'stock_update':
                this.handleStockUpdate(productId, data);
                break;
            case 'initial_stock':
                this.handleInitialStock(productId, data);
                break;
            case 'product_update':
                this.handleProductUpdate(productId, data);
                break;
            default:
                console.warn(`Unknown message type: ${data.type}`);
        }
    }
    
    /**
     * Handle stock update messages
     * @param {number} productId - The product ID
     * @param {Object} data - Stock update data
     */
    handleStockUpdate(productId, data) {
        // Update stock display
        this.updateStockDisplay(productId, data);
        
        // Update buy button state
        this.updateBuyButtonState(productId, data.available_stock);
        
        // Trigger custom event for other components
        this.triggerCustomEvent('stockUpdate', {
            productId: productId,
            stock: data.stock,
            availableStock: data.available_stock,
            isInStock: data.is_in_stock
        });
    }
    
    /**
     * Handle initial stock messages
     * @param {number} productId - The product ID
     * @param {Object} data - Initial stock data
     */
    handleInitialStock(productId, data) {
        this.updateStockDisplay(productId, data);
        this.updateBuyButtonState(productId, data.available_stock);
    }
    
    /**
     * Handle product update messages
     * @param {number} productId - The product ID
     * @param {Object} data - Product update data
     */
    handleProductUpdate(productId, data) {
        console.log(`Product ${productId} updated:`, data);
        
        // Trigger custom event
        this.triggerCustomEvent('productUpdate', {
            productId: productId,
            updateType: data.update_type,
            data: data.data
        });
    }
    
    /**
     * Update stock display in the UI
     * @param {number} productId - The product ID
     * @param {Object} data - Stock data
     */
    updateStockDisplay(productId, data) {
        // Update stock badge
        const stockBadge = document.getElementById(`stock-badge-${productId}`);
        const availableStock = document.getElementById(`available-stock-${productId}`);
        
        if (stockBadge && availableStock) {
            // Update stock badge
            if (data.available_stock > 10) {
                stockBadge.className = 'px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800';
                stockBadge.textContent = 'In Stock';
            } else if (data.available_stock > 0) {
                stockBadge.className = 'px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800';
                stockBadge.textContent = `Low Stock (${data.available_stock})`;
            } else {
                stockBadge.className = 'px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800';
                stockBadge.textContent = 'Out of Stock';
            }
            
            // Update available stock number
            availableStock.textContent = data.available_stock;
            
            // Update color
            if (data.available_stock > 10) {
                availableStock.className = availableStock.className.replace(/text-\w+-600/, 'text-green-600');
            } else if (data.available_stock > 0) {
                availableStock.className = availableStock.className.replace(/text-\w+-600/, 'text-yellow-600');
            } else {
                availableStock.className = availableStock.className.replace(/text-\w+-600/, 'text-red-600');
            }
        }
        
        // Update detail page if we're on the product detail page
        const detailStockBadge = document.getElementById('stock-badge-detail');
        const detailAvailableStock = document.getElementById('available-stock-detail');
        
        if (detailStockBadge && detailAvailableStock) {
            detailAvailableStock.textContent = data.available_stock;
            
            if (data.available_stock > 10) {
                detailStockBadge.className = 'px-3 py-1 text-sm font-medium rounded-full bg-green-100 text-green-800';
                detailStockBadge.textContent = 'In Stock';
                detailAvailableStock.className = detailAvailableStock.className.replace(/text-\w+-600/, 'text-green-600');
            } else if (data.available_stock > 0) {
                detailStockBadge.className = 'px-3 py-1 text-sm font-medium rounded-full bg-yellow-100 text-yellow-800';
                detailStockBadge.textContent = `Low Stock (${data.available_stock} left)`;
                detailAvailableStock.className = detailAvailableStock.className.replace(/text-\w+-600/, 'text-yellow-600');
            } else {
                detailStockBadge.className = 'px-3 py-1 text-sm font-medium rounded-full bg-red-100 text-red-800';
                detailStockBadge.textContent = 'Out of Stock';
                detailAvailableStock.className = detailAvailableStock.className.replace(/text-\w+-600/, 'text-red-600');
            }
        }
    }
    
    /**
     * Update buy button state based on stock availability
     * @param {number} productId - The product ID
     * @param {number} availableStock - Available stock quantity
     */
    updateBuyButtonState(productId, availableStock) {
        const buyButton = document.getElementById(`buy-button-${productId}`);
        const addToCartBtn = document.getElementById(`add-to-cart-btn`);
        const quantityInput = document.getElementById('quantity');
        
        if (availableStock > 0) {
            // Enable buttons
            if (buyButton) {
                buyButton.disabled = false;
                buyButton.classList.remove('opacity-50', 'cursor-not-allowed');
                buyButton.innerHTML = '<i class="fas fa-shopping-cart mr-1"></i>Add to Cart';
            }
            
            if (addToCartBtn) {
                addToCartBtn.disabled = false;
                addToCartBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
            
            if (quantityInput) {
                quantityInput.max = availableStock;
            }
        } else {
            // Disable buttons
            if (buyButton) {
                buyButton.disabled = true;
                buyButton.classList.add('opacity-50', 'cursor-not-allowed');
                buyButton.innerHTML = '<i class="fas fa-times mr-1"></i>Out of Stock';
            }
            
            if (addToCartBtn) {
                addToCartBtn.disabled = true;
                addToCartBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }
        }
    }
    
    /**
     * Update connection status in the UI
     * @param {number} productId - The product ID
     * @param {string} status - Connection status
     */
    updateConnectionStatus(productId, status) {
        const statusElements = [
            document.getElementById(`connection-status-${productId}`),
            document.getElementById('connection-status-detail')
        ];
        
        statusElements.forEach(element => {
            if (element) {
                switch (status) {
                    case 'connected':
                        element.innerHTML = '<i class="fas fa-circle text-green-400"></i> Live';
                        break;
                    case 'disconnected':
                        element.innerHTML = '<i class="fas fa-circle text-red-400"></i> Disconnected';
                        break;
                    case 'connecting':
                        element.innerHTML = '<i class="fas fa-circle text-yellow-400"></i> Connecting...';
                        break;
                    case 'error':
                        element.innerHTML = '<i class="fas fa-circle text-yellow-400"></i> Connection Error';
                        break;
                }
            }
        });
    }
    
    /**
     * Attempt to reconnect to a product WebSocket
     * @param {number} productId - The product ID
     */
    attemptReconnect(productId) {
        const connectionData = this.connections.get(productId);
        if (!connectionData) return;
        
        connectionData.reconnectCount++;
        
        if (connectionData.reconnectCount > this.maxReconnectAttempts) {
            console.warn(`Max reconnection attempts reached for product ${productId}`);
            this.updateConnectionStatus(productId, 'error');
            return;
        }
        
        console.log(`Attempting to reconnect to product ${productId} (attempt ${connectionData.reconnectCount})`);
        this.updateConnectionStatus(productId, 'connecting');
        
        // Schedule reconnection
        setTimeout(() => {
            if (!connectionData.isConnected) {
                this.connect(
                    productId,
                    connectionData.onMessage,
                    connectionData.onConnect,
                    connectionData.onDisconnect
                );
            }
        }, this.reconnectDelay);
    }
    
    /**
     * Disconnect from a product WebSocket
     * @param {number} productId - The product ID
     */
    disconnect(productId) {
        const connectionData = this.connections.get(productId);
        if (connectionData) {
            connectionData.ws.close();
            this.connections.delete(productId);
            console.log(`Disconnected from product ${productId} WebSocket`);
        }
    }
    
    /**
     * Disconnect from all product WebSockets
     */
    disconnectAll() {
        for (const productId of this.connections.keys()) {
            this.disconnect(productId);
        }
    }
    
    /**
     * Trigger a custom event
     * @param {string} eventName - The event name
     * @param {Object} data - Event data
     */
    triggerCustomEvent(eventName, data) {
        const event = new CustomEvent(`websocket:${eventName}`, {
            detail: data
        });
        document.dispatchEvent(event);
    }
    
    /**
     * Get connection status for a product
     * @param {number} productId - The product ID
     * @returns {string} Connection status
     */
    getConnectionStatus(productId) {
        const connectionData = this.connections.get(productId);
        if (!connectionData) return 'disconnected';
        return connectionData.isConnected ? 'connected' : 'connecting';
    }
    
    /**
     * Get all active connections
     * @returns {Array} Array of connected product IDs
     */
    getActiveConnections() {
        const activeConnections = [];
        for (const [productId, connectionData] of this.connections) {
            if (connectionData.isConnected) {
                activeConnections.push(productId);
            }
        }
        return activeConnections;
    }
}

// Global WebSocket manager instance
const productWebSocketManager = new ProductWebSocketManager();

// Utility functions for common WebSocket operations
function initializeProductWebSocket(productId) {
    return productWebSocketManager.connect(productId);
}

function disconnectProductWebSocket(productId) {
    return productWebSocketManager.disconnect(productId);
}

function getProductConnectionStatus(productId) {
    return productWebSocketManager.getConnectionStatus(productId);
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    productWebSocketManager.disconnectAll();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ProductWebSocketManager, productWebSocketManager };
}