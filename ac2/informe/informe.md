## 1. Configuración Inicial y Tipo de Socket
Para la realización de esta actividad, el resolver fue ejecutado en una máquina virtual asociando el servicio a la IP de la misma (`192.168.1.109`) y utilizando el puerto `8000` para evitar conflictos con los puertos reservados del sistema. 

Respecto a la pregunta: **¿Qué tipo de socket debe usar?** 
* Socket "NOC", para realizar consultas rápidas y sin conexión previa. Por lo tanto, el socket adecuado en Python es del tipo Datagrama (`socket.SOCK_DGRAM`)

---

## 2. Pruebas de Funcionalidad
Las pruebas de funcionalidad base demuestran que el resolver procesa correctamente las respuestas, logrando transformar los mensajes a las estructuras correspondientes y consultar iterativamente.


### Resolución de dominios
Se verificó la resolución del dominio `www.uchile.cl` y `cc4303.bachmann.cl`, logrando obtener la dirección IP de forma exitosa mediante los siguientes comandos:
* `dig -p8000 @192.168.1.109 www.uchile.cl` resolvió exitosamente la IP `200.89.76.36`.
* `dig -p8000 @192.168.1.109 cc4303.bachmann.cl` resolvió a `104.248.65.245`.


### Funcionamiento del Caché
Se implementó un sistema de caché para almacenar las últimas consultas. Esto se evidenció repitiendo la consulta al dominio `eol.uchile.cl`:
* **Primera consulta:** El resolver consultó la jerarquía completa (Raíz -> TLD `.ca` -> Autoritativo `.cl`), tardando **336 msec**.
* **Segunda consulta:** Al repetir el comando, la respuesta se entregó inmediatamente desde el almacenamiento local en **0 msec**, y el modo *debug* mostró el mensaje: `Respondiendo desde cache para eol.uchile.cl.` confirmando el uso del caché.

---

## 3. Experimentos y Observaciones

### Experimento 1: `www.webofscience.com`
Al intentar resolver el dominio `www.webofscience.com`, se observó lo siguiente:
* **¿Resuelve el programa este dominio?** No.

* **¿Qué sucede?** La terminal de `dig` reporta múltiples errores `communications error to 192.168.1.109#8000: timed out` y finalmente indica que no se pudo alcanzar ningún servidor.

* **¿Por qué sucede esto?** Dominios grandes y complejos como *Web of Science* rara vez apuntan directamente a un registro `A`. Usualmente, la respuesta en la sección *Answer* contiene un alias (registro `CNAME`). Dado que las reglas de nuestro resolver casero establecen explícitamente: *"Si recibe algún otro tipo de respuesta simplemente ignórela"*, al recibir un `CNAME` en lugar de un registro tipo `A` o una delegación `NS`, el programa desecha el paquete. El cliente `dig` se queda esperando una respuesta que nunca llega, causando el *timeout*.

* **¿Cómo se arreglaría este problema?** Se debería modificar el código del resolver para que no ignore los registros de otros tipos. Si detecta un registro tipo `CNAME` en la respuesta, el resolver debería tomar el nuevo nombre de dominio (el alias) y reiniciar recursivamente el proceso de consulta desde el paso inicial para encontrar la IP definitiva.


### Experimento 2: `www.cc4303.bachmann.cl`
Se ejecutó el comando para buscar el dominio `www.cc4303.bachmann.cl` y se contrastó con el comportamiento del resolver público de Google.
* **¿Qué ocurre?** Al igual que en el experimento anterior, nuestro resolver sufre un *timeout* y no logra devolver ninguna información al cliente.

* **¿Qué se habría esperado que ocurriera?** Se esperaba que el servidor respondiera rápidamente indicando que el dominio solicitado no existe, en lugar de quedarse atascado o en silencio.

* **Contraste con `8.8.8.8` y explicación DNS:** Al consultarle al servidor `8.8.8.8`, este responde de inmediato con un estado `NXDOMAIN` (Non-Existent Domain) y entrega un registro `SOA` en la sección *Authority*. Esto indica formalmente que el subdominio con "www" no está registrado en esa zona. Nuestro resolver experimenta un *timeout* porque no está programado para entender o procesar un error `NXDOMAIN` ni registros `SOA`; está construido estrictamente para buscar delegaciones (`NS`) en *Authority* y registros `A` en *Answer/Additional*. Al no encontrar ninguno, ignora la respuesta.

### Experimento 3: Consulta iterativa de Name Servers
A través del modo *debug*, se observaron las distintas delegaciones para llegar a un dominio específico mediante varias consultas repetidas.
* **¿Son siempre los mismos Name Servers?** Sí, en todas las iteraciones se siguió el mismo camino: Servidor raíz `.` -> `cl2-tld.d-zone.ca.` -> `bachmann.cl.` -> etc.

* **¿Por qué sucede esto?** Se debe a la naturaleza jerárquica y estricta del protocolo DNS. La resolución de un nombre siempre fluye de derecha a izquierda por el árbol DNS (desde el nivel raíz hacia abajo). La administración de quién tiene la autoridad para cada zona es fija. Por lo tanto, el TLD encargado de `.cl` y los *Nameservers* autoritativos configurados por el dueño del dominio `bachmann.cl` serán exactamente los mismos, siempre y cuando el administrador del dominio no cambie deliberadamente su proveedor de infraestructura DNS