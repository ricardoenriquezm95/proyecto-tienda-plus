
## Descripción del dominio
### Problema de negocio
Tienda+ es una pequeña tienda de productos locales, quiere vender por internet sin comprar ni mantener servidores propios. Sus ventas son muy irregulares: pocas ventas entre semanas y picos fuertes en épocas de campañas puntuales (Black Friday, navidad, rebajas). Con un servidor propio tendría que dimensionar para sus momentos pico y después pagar por los mismos servicios durante todo el año sin utilizar toda la capacidad comprada; con la nube paga solo por lo que usa y escala automáticamente en los picos.
El problema de negocio no es “gestionar productos de la tienda” sino más bien vender sin sobrevender: cuando hay muchos clientes y compran a la vez el mismo producto, el sistema debe garantizar que no se acepten pedidos sin stock real.
### Lógica de negocio
-	Reserva de stock: al crear un pedido el servicio de orden de productos pide al servicio de catálogo de productos reservar las unidades. Si algún producto no tiene stock suficiente, el pedido se rechaza completo y se liberan las reservas de producto ya hechas.
-	Cálculo de pedido: Subtotal por línea y IVA 
-	Estados del pedido: se considerarán estos estados:
    -	PENDIENTE – PAGADO – ENVIADO.
    -	PENDIENTE – CANCELADO.
-	Cancelación con devolución de stock: Cancelar un pedido pendiente libera las unidades reservadas.
-	Pago simulado: El pago será simulado y no se integrará una pasarela real.

