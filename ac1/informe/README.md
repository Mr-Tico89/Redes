Respuestas para tu informe

1. ¿Cómo sé que el HEAD (las cabeceras) llegó completo?

Sabes que las cabeceras han terminado de llegar exclusivamente cuando detectas la secuencia de bytes \r\n\r\n (Retorno de carro + Salto de línea, repetido dos veces).
El estándar HTTP define esta línea en blanco como el separador oficial y único entre el bloque de cabeceras y el inicio del cuerpo (body). Tu proxy debe inspeccionar el texto acumulado y, en el instante en que encuentre ese patrón, debe dar por terminada la fase de lectura de headers.
2. ¿Qué pasa si los headers no caben en mi buffer?

Si el buffer es más pequeño que el tamaño total de las cabeceras, el proxy no falla ni pierde datos, sino que debe realizar múltiples ciclos de lectura.
Lo que sucede internamente es lo siguiente:

    El proxy lee un bloque (chunk) del tamaño máximo del buffer y lo guarda en una variable acumuladora (como un string dinámico o un arreglo de bytes más grande).

    Al revisar el acumulador, nota que la secuencia \r\n\r\n aún no está presente.

    El proxy vuelve a llamar a la función de lectura (recv) para obtener el siguiente fragmento del socket, concatenándolo con lo que ya tenía.

    Este ciclo se repite hasta que el buffer finalmente trae los bytes que completan la secuencia \r\n\r\n dentro del acumulador.

3. ¿Y el BODY (el cuerpo)? ¿Cómo sé que llegó completo?

Para saber cómo y cuánto leer del body, dependes de la información que acabas de leer en las cabeceras. Hay dos mecanismos principales:

    Content-Length: Es el método más común. El proxy busca la cabecera Content-Length: X (donde X es un número). Ese número indica exactamente la cantidad de bytes que tiene el body. El proxy debe seguir leyendo del socket e ir contando los bytes que llegan (después del \r\n\r\n) hasta que sumen exactamente X bytes.

    Transfer-Encoding: chunked: Si el servidor no sabe el tamaño final de antemano (como en un streaming), usa esta cabecera. En este caso, el cuerpo llega en fragmentos (chunks), donde cada fragmento indica su propio tamaño antes de enviar los datos, y el mensaje termina cuando llega un fragmento de tamaño 0. (Nota: Para tu informe, si no han implementado chunking, basta con mencionar la lógica del Content-Length o indicar que para métodos como GET generalmente el body es de 0 bytes).

4. ¿Cómo sé si llegó el mensaje completo?

El mensaje se considera 100% completo cuando se cumplen de manera consecutiva las dos condiciones anteriores:

    Fase de Headers: Se encontró el delimitador \r\n\r\n.

    Fase de Body: Se leyó exactamente la cantidad de bytes indicada en el Content-Length (o se completó la lectura chunked). Si no hay Content-Length (como en un GET estándar), el mensaje se considera completo inmediatamente después de leer el \r\n\r\n.

Al tener estas dos fases validadas, tu proxy ya tiene el mensaje HTTP empaquetado y listo para ser reenviado al servidor destino.





Para saber qué información debería extraer, revise el material sobre mensajes HTTP, evalúe qué debería extraer su función parse y anótelo en su informe.

se decidio la estructura de json puesto que en los futuros pasos vamos a utilizar json, los headers por separado y el body todo junto en la siguiente estructura json:
{
    "headers":{
        "header1": ...
        "header2": ...
        "header3": ...
    },
    "body": ""
}



Caso 1: Buffer < Mensaje Total, pero Buffer > Headers

El objetivo: Probar que tu proxy puede leer las cabeceras de una sola vez, procesarlas, darse cuenta de que falta el cuerpo (body) y hacer lecturas adicionales para procesar el resto del mensaje sin perder datos.

Cómo configurarlo:

    Ajusta tu código: Cambia el tamaño de lectura de tu buffer a 512 bytes.

    Prepara la petición: Necesitas enviar una petición que tenga un cuerpo grande. Un POST es ideal para esto. El tamaño total del mensaje debe ser mayor a 512 bytes (por ejemplo, 2000 bytes).

    Ejecuta la prueba (usando cURL en tu terminal):
    Bash

    # Esto envía un POST a tu proxy (asumiendo que corre en localhost:8080)
    # con un string de 2000 caracteres como cuerpo.
    curl -x http://localhost:8080 -d "dato=$(printf 'A%.0s' {1..2000})" http://httpbin.org/post

Qué anotar en el informe:

    Configuración: "Se configuró el buffer de lectura (recv) a 512 bytes. Se envió una petición POST con un cuerpo de 2000 bytes."

    Comportamiento observado: "En la primera lectura, el proxy recibió la Start Line y todas las cabeceras (incluyendo \r\n\r\n). El proxy analizó correctamente las cabeceras, identificó el Content-Length, y procedió a realizar múltiples llamadas de lectura (recv) en un bucle para consumir los bytes restantes del body, reenviándolos correctamente al servidor destino."

    Resultado: Exitoso. El servidor destino recibió el cuerpo completo sin corrupción de datos.







Caso 2: Buffer < Headers, pero Buffer > Start Line

El objetivo: Esta es la prueba de fuego. Sirve para probar que tu proxy no se rompe si las cabeceras se cortan por la mitad. Demuestra que tu código guarda el estado (acumula lo leído) y sigue leyendo hasta encontrar el \r\n\r\n antes de intentar analizar los headers.

Cómo configurarlo:

    Ajusta tu código: Cambia el tamaño de lectura de tu buffer a 40 o 50 bytes. (Asegúrate de que sea lo suficientemente grande para capturar GET / HTTP/1.1\r\n pero no más que eso).

    Prepara la petición: Una petición GET normal de un navegador o de cURL es suficiente, ya que sus cabeceras suelen sumar unos 300 bytes.

    Ejecuta la prueba:
    Bash

    curl -v -x http://localhost:8080 http://example.com

Qué anotar en el informe:

    Configuración: "Se configuró el buffer de lectura a 50 bytes. Se envió una petición GET estándar que contenía aproximadamente 300 bytes de cabeceras."

    Comportamiento observado: "En la primera lectura, el proxy solo recibió la Start Line y el inicio de la primera cabecera. Como no detectó la secuencia \r\n\r\n, el proxy almacenó este fragmento en una estructura dinámica (o string) y volvió a llamar a recv. Este proceso se repitió (aproximadamente 6-7 lecturas) concatenando los datos, hasta que finalmente la secuencia \r\n\r\n ingresó al buffer. Solo entonces se procedió a analizar el mensaje completo."

    Resultado: Exitoso. El proxy no intentó parsear cabeceras incompletas, no falló por Index Out of Bounds y logró construir la petición original íntegramente.