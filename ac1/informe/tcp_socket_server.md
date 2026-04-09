# `tcp_socket_server.py` — Explicación de funciones

Este script implementa un **proxy HTTP (TCP)** muy simple:
- Acepta conexiones de un cliente (ej. navegador configurado con proxy).
- Lee una *request* HTTP completa.
- Bloquea hosts/URLs definidos en `./ban/ban.json` (responde 403 con HTML local).
- Si no está bloqueado, reenvía la request al servidor destino (puerto 80), recibe la response, y **reemplaza palabras prohibidas** en el body.
- Además, si el cliente pide `ban.jpg`, la sirve localmente desde `./ban/ban.jpg`.

## Constantes

- `IP_VM`: IP donde el proxy hace `bind()` (interfaz/host local donde escucha).
- `PORT`: puerto TCP de escucha (por defecto `8000`).

## Funciones

### `receive_full_msg(connection_socket, buff_size) -> bytes`
Lee desde un socket TCP hasta reconstruir un **mensaje HTTP completo**.

1. Acumula `recv(buff_size)` hasta encontrar el fin de headers: `\r\n\r\n`.
2. Separa `headers_data` y el inicio del body que pudo llegar “pegado”.
3. Busca `Content-Length` en los headers (si no está, queda en `0`).
4. Sigue leyendo hasta que `len(body_data_received) == content_length`.

Retorna el mensaje completo como bytes: `headers + \r\n\r\n + body`.

### `parse_HTTP_msg(http_message: str) -> dict`
Convierte un mensaje HTTP en texto a un diccionario:

- Divide por `\r\n\r\n` en `head` y `body`.
- Guarda la start-line (ej. `GET / HTTP/1.1` o `HTTP/1.1 200 OK`) como `headers['startLine']`.
- Parsea el resto de headers `Key: Value`.

Salida:
```py
{"headers": {...}, "body": "..."}
```

### `create_HTTP_msg(json_msg: dict) -> str`
Hace el proceso inverso: arma un HTTP en texto desde el diccionario.

- Lee `headers` y `body`.
- Fuerza/actualiza `Content-Length` a `len(body)`.
- Imprime primero `startLine` y luego el resto de headers.
- Agrega `\r\n\r\n` y concatena el body.

### `read_JSON(path: str) -> dict`
Lee un archivo JSON desde disco y retorna el diccionario Python correspondiente.

### `read_HTML(path: str) -> str`
Lee un archivo HTML desde disco y retorna el contenido como string.

### `read_image(path: str) -> bytes`
Lee un archivo binario (en el código se usa para `.jpg`) y retorna los bytes.

### `check(json_msg: dict) -> bool`
Valida si la URL solicitada está bloqueada según `./ban/ban.json`.

- Obtiene la `startLine` de la request y separa: `method, url, version`.
- Recorre `ban_data['blocked']`.
- Si `url` coincide con un elemento bloqueado:
  - Cambia la start-line a una respuesta de error: `"{version} 403 ERROR"`.
  - Retorna `False`.
- Si no coincide, retorna `True`.

### `forbidden_words(json_msg: dict) -> dict`
Reemplaza palabras prohibidas en el **body** del mensaje según `./ban/ban.json`.

- Lee `forbidden_words` (lista de diccionarios `{palabra: reemplazo}`).
- Hace `body.replace(forbidden_word, replacement)` para cada par.
- Devuelve el mismo `json_msg` con `json_msg['body']` modificado.

## Flujo del `__main__`

1. Crea un socket servidor (`AF_INET`, `SOCK_STREAM`), hace `bind((IP_VM, PORT))` y `listen(3)`.
2. Acepta un cliente con `accept()`.
3. Lee request completa con `receive_full_msg()` y la parsea con `parse_HTTP_msg()`.
4. Obtiene `method, url, version` desde `headers['startLine']`.

### Caso especial: `ban.jpg`
Si `url.endswith("ban.jpg")`:
- Lee `./ban/ban.jpg` con `read_image()`.
- Responde directo al cliente con headers:
  - `HTTP/1.1 200 OK`
  - `Content-Type: image/jpeg`
  - `Content-Length: ...`
- Envía `headers + imagen` (bytes) y cierra.

### Caso normal: filtrar/bloquear o reenviar
- Llama `check()`:
  - Si está bloqueada (`False`):
    - Carga `./ban/ban_response.json` (plantilla de headers/status).
    - Carga `./ban/ban.html` y lo pone en `proxy_response_json['body']`.
  - Si está permitida (`True`):
    - Conecta al host destino en puerto 80 usando el header `Host`:
      - `host = (client_request_json['headers']['Host'].strip(), 80)`
    - Reenvía la request original, agregando el header:
      - `X-ElQuePregunta: Jujalag`
    - Recibe la response completa con `receive_full_msg()` y la parsea.

5. Aplica `forbidden_words()` sobre la response.
6. Reconstruye el HTTP con `create_HTTP_msg()` y lo envía al cliente.
7. Cierra el socket del cliente.

## Archivos que usa

- `./ban/ban.json`: lista de URLs bloqueadas y palabras prohibidas.
- `./ban/ban_response.json`: base de headers para la respuesta 403.
- `./ban/ban.html`: HTML mostrado cuando se bloquea.
- `./ban/ban.jpg`: imagen servida cuando se solicita `ban.jpg`.

## Notas/limitaciones prácticas

- `receive_full_msg()` depende de `Content-Length`; **no** maneja `Transfer-Encoding: chunked`.
- `parse_HTTP_msg()` y `create_HTTP_msg()` trabajan en texto; si una response real trae body binario (no HTML), el `decode()` puede fallar o corromper datos.
- `Content-Length = len(body)` mide caracteres de Python; si el body tiene caracteres no-ASCII, el tamaño en bytes puede diferir al hacer `.encode()`.
- Las rutas `./ban/...` son relativas al directorio donde ejecutes el script (ideal: ejecutar desde `ac1/`).
