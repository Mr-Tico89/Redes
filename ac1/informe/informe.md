## 1. Decisiones de Diseño y Parseo de Mensajes

De acuerdo a lo solicitado, fue necesario evaluar qué información extraer del mensaje HTTP en la función `parse` y documentarlo. 

**Estructura de Datos (Parseo)**
Se decidió utilizar una estructura de diccionario/JSON para almacenar el mensaje HTTP parseado, debido a que en pasos posteriores de la actividad se requiere el uso de archivos JSON para configuraciones y reglas de filtrado. La estructura definida separa los headers del body de la siguiente manera:
```json
{
    "headers":{
        "startLine": "GET / HTTP/1.1",
        "Host": "example.com",
        "headerN": "..."
    },
    "body": "..."
}
```
**Funcionamiento del Código**
El servidor proxy funciona recibiendo conexiones de clientes, leyendo la *request* completa y parseándola a texto. El flujo principal de funcionamiento es el siguiente:

* El código incluye funciones para leer archivos JSON desde el disco y procesarlos para buscar palabras prohibidas o sitios bloqueados.

* Si la URL solicitada se encuentra en la lista de sitios bloqueados, el proxy responde con un código de error 403 y un archivo HTML local (`ban.html`) que puede contener una imagen de gatos.

* Si no está bloqueado, el proxy se conecta al servidor destino en el puerto 80, reenvía la request agregando el header `X-ElQuePregunta: Jujalag`, recibe la response completa, y ejecuta una función para reemplazar palabras prohibidas en el body antes de reenviarlo al cliente.

* Existe una limitación de diseño importante: el proxy asume el uso de la cabecera `Content-Length` y no soporta nativamente la lectura de mensajes bajo la cabecera `Transfer-Encoding: chunked`. Además, al trabajar las conversiones en texto plano (como `decode()`), los datos en formato binario podrían verse corrompidos al ser procesados.

## 2. Diagrama y Flujo del Proxy

> **Nota:** Recuerda dibujar e insertar tu diagrama aquí antes de entregar el informe. A continuación se presenta la explicación textual requerida para acompañarlo.

**Explicación del Flujo del Proxy:**
El proxy actúa como intermediario. Utiliza un socket TCP servidor asociado a la IP de la máquina virtual (IP_VM) en el puerto 8000 para escuchar peticiones de los clientes (como un navegador o `curl`). Cuando un cliente se conecta, el proxy acepta la conexión y lee el requerimiento. Para reenviar esa petición, el proxy crea un **segundo socket** (socket cliente) para conectarse al servidor web destino en el puerto 80. El proxy envía la request, recibe la respuesta de este servidor a través del segundo socket, cierra la conexión externa, y finalmente devuelve la respuesta procesada al cliente a través del primer socket.

## 3. Manejo de Buffers y Mensajes HTTP

Al momento de implementar la capacidad de recibir mensajes con buffers más pequeños que el tamaño del mensaje, surgieron interrogantes fundamentales sobre el ciclo de lectura.

**¿Cómo sé que el HEAD (las cabeceras) llegó completo?**
Se sabe que las cabeceras han terminado de llegar exclusivamente cuando se detecta la secuencia de bytes correspondiente a un doble salto de línea `\r\n\r\n`. El proxy inspecciona el texto acumulado y, en el instante en que encuentra ese patrón, da por terminada la fase de lectura de headers.

**¿Qué pasa si los headers no caben en mi buffer?**
Si el buffer es más pequeño que el tamaño total de las cabeceras, el proxy no falla ni pierde datos, sino que debe realizar múltiples ciclos de lectura. El sistema lee un fragmento, lo acumula y verifica si el delimitador `\r\n\r\n` está presente. Si no lo está, vuelve a invocar la función de lectura (`recv`) hasta completar la secuencia.

**¿Y el BODY (el cuerpo)? ¿Cómo sé que llegó completo?**
Para saber cómo y cuánto leer del body, se depende de la información de las cabeceras, principalmente de `Content-Length`. El proxy busca el número indicado en esta cabecera y sigue leyendo del socket (después del `\r\n\r\n`) hasta que los bytes acumulados coincidan exactamente con dicho número.

**¿Cómo sé si llegó el mensaje completo?**
El mensaje se considera 100% completo cuando se validan dos fases consecutivas:
1.  Fase de Headers: Se encuentra el delimitador de doble salto de línea `\r\n\r\n`.
2.  Fase de Body: Se lee exactamente la cantidad de bytes indicada en el `Content-Length` (o finaliza inmediatamente tras los headers si no existe esta cabecera).

## 4. Pruebas y Experimentos de Buffer

Se realizaron diversas pruebas modificando el tamaño del buffer de recepción (`recv_buffer`) para garantizar la robustez del código.

### Experimento A: Buffer menor al total, pero mayor a los headers
* **Configuración:** Se ajustó el buffer de lectura a 512 bytes y se envió una petición POST con un cuerpo de 2000 bytes. En otra prueba de tamaño intermedio (Buffer 600) se observó que la lectura consolidó 143 bytes inicialmente.
* **Comportamiento observado:** En la primera lectura, el proxy recibió la Start Line y todas las cabeceras (incluyendo `\r\n\r\n`). El proxy analizó correctamente las cabeceras, identificó el `Content-Length`, y procedió a realizar múltiples llamadas de lectura en un bucle para consumir los bytes restantes del body.
* **Resultado:** Exitoso. El servidor destino recibió el cuerpo completo sin corrupción de datos.

### Experimento B: Buffer menor a los headers, pero mayor a la Start Line
* **Configuración:** Se configuró el buffer de lectura a 50 bytes (y posteriormente a 30 bytes). Se envió una petición GET estándar que contenía aproximadamente 300 bytes de cabeceras.
* **Comportamiento observado:** En la primera lectura, el proxy solo recibió la Start Line y el inicio de la primera cabecera. Como no detectó la secuencia `\r\n\r\n`, el proxy almacenó este fragmento en un acumulador y volvió a llamar a `recv`. En las pruebas con buffer de 30, el proceso tomó 5 ciclos (4 lecturas de 30 bytes y una de 23 bytes) antes de consolidar la información y analizar el mensaje completo.
* **Resultado:** Exitoso. El proxy no intentó parsear cabeceras incompletas, acumulando correctamente el estado.

### Prueba de Estrés: Buffer Extremadamente Pequeño (Buffer = 6)
* **Comportamiento observado:** Se forzó un buffer de 6 bytes. El servidor requirió 24 lecturas consecutivas (23 lecturas de 6 bytes y 1 de 5 bytes) para terminar de extraer los datos.
* **Conclusión:** Aunque la lectura de múltiples fragmentos funciona teóricamente, usar buffers minúsculos demostró que se corre el riesgo de truncar datos temporalmente, lo que puede causar un parsing inválido si el proxy intenta interpretar la estructura antes de que llegue la secuencia de fin de cabeceras.

***

**Pruebas Adicionales de Integración (Navegador/cURL):**
* **Filtro 403:** Se verificó que al intentar acceder a los dominios bloqueados en el archivo `.json`, el servidor intercepta la comunicación exitosamente y retorna un código HTML de error en lugar de cargar el sitio destino.
* **Reemplazo de palabras:** Al entrar al sitio de pruebas HTTP permitido por medio del proxy, se confirmó que las palabras definidas como prohibidas en el archivo JSON son interceptadas e inmediatamente reemplazadas por censuras en el cuerpo de la respuesta antes de mostrarse en el navegador local.