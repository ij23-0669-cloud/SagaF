// AÑADIRJUEGOS.JS
        
        // Inicializa los iconos de Lucide
        lucide.createIcons();

        // Estado del catálogo: empezamos vacío — los productos se cargan desde la base de datos / servidor
        let products = [];

        // Elementos del DOM
        const form = document.getElementById('add-product-form');
        const productListBody = document.getElementById('product-list');
        const gameCodeInput = document.getElementById('game-code');
        const catalogTitle = document.getElementById('catalog-title');
        const feedbackEl = document.getElementById('feedback-message');

        // Función para generar un nuevo ID de producto (GAME00X)
        const generateNewId = () => {
            // Encuentra el ID numérico más alto y suma 1
            const highestIdNum = products.reduce((max, product) => {
                const num = parseInt(product.id.replace('GAME', ''), 10);
                return num > max ? num : max;
            }, 0);
            const nextIndex = highestIdNum + 1;
            return 'GAME' + nextIndex.toString().padStart(3, '0');
        };

        // Función para mostrar feedback temporal
        const showFeedback = (message, type = 'success') => {
            feedbackEl.textContent = message;
            feedbackEl.classList.remove('opacity-0', 'pointer-events-none', 'bg-green-100', 'text-green-800', 'bg-red-100', 'text-red-800');
            
            if (type === 'success') {
                feedbackEl.classList.add('bg-green-100', 'text-green-800');
            } else {
                feedbackEl.classList.add('bg-red-100', 'text-red-800');
            }

            feedbackEl.classList.add('opacity-100');

            setTimeout(() => {
                feedbackEl.classList.remove('opacity-100');
                feedbackEl.classList.add('opacity-0', 'pointer-events-none');
            }, 3000);
        };

        // Renderiza la tabla de productos
        const renderProducts = () => {
            productListBody.innerHTML = '';
            products.forEach(product => {
                const row = document.createElement('tr');
                row.className = 'hover:bg-gray-50 transition duration-100';
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-900">${product.id}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${product.name}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${product.platform}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">$ ${product.price.toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                        <button class="text-red-600 hover:text-red-900 flex items-center mx-auto" onclick="deleteProduct('${product.id}')">
                            <i data-lucide="trash-2" class="w-4 h-4 mr-1"></i>
                            Eliminar
                        </button>
                    </td>
                `;
                productListBody.appendChild(row);
            });
            
            // Actualizar el título y el código de nuevo producto
            catalogTitle.textContent = `Catálogo Actual (${products.length} productos)`;
            gameCodeInput.value = generateNewId();
            lucide.createIcons(); // Vuelve a inicializar iconos para los nuevos botones
        };

        // Función global para eliminar producto (llamada desde el HTML)
        window.deleteProduct = (id) => {
            // NOTA: En un entorno real, esto se reemplaza por una modal de confirmación
            if (confirm(`¿Estás seguro de que quieres eliminar el producto ${id}?`)) {
                const deletedName = products.find(p => p.id === id)?.name || id;
                products = products.filter(p => p.id !== id);
                renderProducts();
                showFeedback(`Producto "${deletedName}" eliminado.`, 'error');
            }
        };

        // Manejo del formulario de adición
        form.addEventListener('submit', (e) => {
            e.preventDefault();

            const newId = document.getElementById('game-code').value;
            const productName = document.getElementById('game-name').value;
            const platform = document.getElementById('game-platform').value;
            const price = parseFloat(document.getElementById('game-price').value);

            if (!productName || !platform || isNaN(price) || price <= 0) {
                showFeedback('Error: Todos los campos deben ser válidos.', 'error');
                return;
            }

            const newProduct = {
                id: newId,
                name: productName,
                platform: platform,
                price: price
            };

            // 1. Añadir el nuevo producto al estado
            products.push(newProduct);
            
            // 2. Renderizar la lista actualizada
            renderProducts();

            // 3. Limpiar el formulario y mostrar feedback
            document.getElementById('game-name').value = '';
            document.getElementById('game-price').value = '';
            document.getElementById('game-platform').value = ''; // Resetear select
            
            showFeedback(`¡Producto "${productName}" añadido con éxito!`);
        });

        // Inicializar la vista al cargar
        document.addEventListener('DOMContentLoaded', () => {
            renderProducts();
        });










//FACTURA.JS
        // Datos de ejemplo: mantén la estructura simple y fácil de sustituir por datos reales
        (function(){
            const invoice = {
                number: 'SAGA-999999',
                date: new Date().toLocaleDateString('es-ES'),
                client: { name: 'X--30--X', address: 'Calle Falsa 123' },
                method: 'Tarjeta',
                notes: 'Factura generada automáticamente.',
                items: [
                    { id: 1, name: 'Juego X-40-X', qty: 1, price: 4999.99 },
                    { id: 2, name: 'Juego Y-20-Y', qty: 1, price: 2499.50 }
                ],
                taxRate: 0.19 // ejemplo 19%
            };

            // Fallback si logo no existe (intentar detectar)
            const logoEl = document.getElementById('saga-logo');
            (new Image()).src = logoEl.src;
            logoEl.onerror = function() {
                // Si falla, mostrar texto simple como fallback
                const a = logoEl.parentElement;
                logoEl.remove();
                const fallback = document.createElement('div');
                fallback.textContent = 'SAGA';
                fallback.className = 'text-xl font-extrabold text-saga-red';
                a.appendChild(fallback);
            };

            // Poner metadatos
            document.getElementById('invoice-number').textContent = invoice.number;
            document.getElementById('issue-date').textContent = invoice.date;
            document.getElementById('client-name').textContent = invoice.client.name;
            document.getElementById('client-address').textContent = invoice.client.address;
            document.getElementById('payment-method').textContent = invoice.method;
            document.getElementById('invoice-notes').textContent = invoice.notes;

            // Render items y totales
            const itemsBody = document.getElementById('items-body');
            itemsBody.innerHTML = '';
            let subtotal = 0;
            invoice.items.forEach(it => {
                const lineTotal = it.qty * it.price;
                subtotal += lineTotal;
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${it.name}</td>
                    <td class="right">${it.qty}</td>
                    <td class="right">${formatCurrency(it.price)}</td>
                    <td class="right">${formatCurrency(lineTotal)}</td>
                `;
                itemsBody.appendChild(tr);
            });

            const tax = subtotal * invoice.taxRate;
            const total = subtotal + tax;

            document.getElementById('subtotal-amount').textContent = formatCurrency(subtotal);
            document.getElementById('tax-amount').textContent = formatCurrency(tax);
            document.getElementById('total-amount').textContent = formatCurrency(total);

            // Descargar (placeholder): puedes integrar html2pdf o backend real
            document.getElementById('download-btn').addEventListener('click', () => {
                alert('Funcionalidad de descarga no implementada en este mock. Integra html2pdf o backend para generar PDF.');
            });

            function formatCurrency(v){
                return new Intl.NumberFormat('es-ES', { style:'currency', currency:'EUR' }).format(v);
            }
        })();












