import socket
import json


IP_VM = '192.168.1.109'
PORT = 8000


def receive_full_msg(connection_socket, buff_size): 
    # 1. Recibir hasta que los HEADERS estén completos
    full_data = b""
    
    while b"\r\n\r\n" not in full_data:
        chunk = connection_socket.recv(buff_size)
        full_data += chunk

    # Si no se encontró el fin de headers, retornamos lo que llegó
    if b"\r\n\r\n" not in full_data:
        return full_data

    # Separamos el HEAD del posible inicio del BODY que haya colado en el último recv
    headers_data, body_data_received = full_data.split(b"\r\n\r\n", 1)

    # 2. Buscar el Content-Length en los headers

    headers_text = headers_data.decode()
    content_length = 0
    
    for line in headers_text.split('\r\n'):
        if line.lower().startswith('content-length:'):
            # Extraemos el número de bytes
            content_length = int(line.split(':')[1].strip())
            break

    # 3. Recibir el resto del BODY si es que falta
    # Verificamos cuántos bytes del body ya recibimos en el primer bucle
    while len(body_data_received) < content_length:
        chunk = connection_socket.recv(buff_size)
        if not chunk:
            break
        body_data_received += chunk
 
    # Reensamblamos el mensaje completo en bytes y lo retornamos
    return headers_data + b"\r\n\r\n" + body_data_received


def parse_HTTP_msg(http_message: str) -> dict:
    # Toma un mensaje HTTP y lo transforma a 
    # JSON permitiendo acceder fácil a la info del mensaje.
    head, separator, body = http_message.partition("\r\n\r\n")
    lines = [line.strip() for line in head.split("\r\n") if line.strip()]

    if not lines:
        return {"headers": {}, "body": ""}

    headers = {}
    # La start line como 'startLine'
    headers['startLine'] = lines[0]
    for header_line in lines[1:]:
        if ":" not in header_line:
            continue
        key, value = header_line.split(":", 1)
        headers[key.strip()] = value.strip()

    parsed_body = body if separator else ""

    return {
        "headers": headers,
        "body": parsed_body
    }


def create_HTTP_msg(json_msg: dict) -> str:
    # Toma un diccionario JSON y lo convierte en un mensaje HTTP
    headers_dict = json_msg.get("headers", {}) # obtiene los headers del json
    body = json_msg.get("body", "") # obtiene el body del json
    headers_dict["Content-Length"] = len(body)

    # Construimos el mensaje HTTP
    http_message = ""
    for key, value in headers_dict.items():
        if key == "startLine":
            http_message += headers_dict["startLine"] + "\r\n"
        else:
            http_message += f"{key}: {value}\r\n"

    # Separador entre headers y body
    http_message += "\r\n"
    http_message += body
    return http_message


def read_JSON(path: str) -> dict:
    # sirve para poder leer los archivos json
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def read_HTML(path: str) -> str:
    # sirve para poder leer los archivos HTML
    with open(path, "r", encoding="utf-8") as file:
        body = file.read()
    return body


def read_image(path: str) -> bytes:
    # sirve para poder leer los archivos jpg
    with open(path, 'rb') as file:
        image_data = file.read()
    return image_data


def check(url: str) -> bool:
    # chekea si la url a la que va a entrar esta baneada o no
    ban_data = read_JSON("./ban/ban.json")
    for blocked in ban_data['blocked']:
        if url == blocked:
            return False

    return True


def forbidden_words(json_msg: dict) -> dict:
    # revisa el body del http para cambiar las palabras baneadas por otras
    ban_words = read_JSON("./ban/ban.json")
    body = json_msg.get("body", "")
    for word_dict in ban_words.get('forbidden_words', []):
        for forbidden_word, replace in word_dict.items():
            body = body.replace(forbidden_word, replace)

    json_msg["body"] = body
    return json_msg


if __name__ == "__main__":
    # definimos el tamaño del buffer de recepción y la secuencia de fin de mensaje
    buff_size = 4096
    end_sequence = "\n"
    addr = (IP_VM, PORT) 
    print('Creando socket - Proxy')

    # armamos el socket os parámetros que recibe el socket indican el tipo de conexión
    # socket.SOCK_STREAM = socket orientado a conexión
    proxy_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # le indicamos al server socket que debe atender peticiones en la dirección 
    # address para ello usamos bind
    proxy_server_sock.bind(addr)

    # luego con listen (función de sockets de python) le decimos que puede tener hasta 3 
    # peticiones de conexión encoladas si recibiera una 4ta petición de conexión la va a rechazar
    proxy_server_sock.listen(3)

    # nos quedamos esperando a que llegue una petición de conexión
    print(f"proxy escuchando en {addr}")

    while True:
        # cuando llega una petición de conexión la aceptamos y 
        # se crea un nuevo socket que se comunicará con el cliente
        client_sock, client_addr = proxy_server_sock.accept()
        print(f"Cliente conectado desde {client_addr}")

        # recibimos el mensaje y lo parseamos a json
        client_request = receive_full_msg(client_sock, buff_size)
        client_request_json = parse_HTTP_msg(client_request.decode())
        
        # Extraer la URL de la request
        start_line = client_request_json["headers"]["startLine"].strip()
        method, url, version = start_line.split(" ", 2)
        
        # Si se solicita ban.jpg, servirla localmente
        if url.endswith("ban.jpg"):
            image_data = read_image("./ban/ban.jpg")
            # Construir headers para la imagen
            headers = f"HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\nContent-Length: {len(image_data)}\r\n\r\n"
            
            # Enviar headers + imagen (binarios)
            client_sock.send(headers.encode() + image_data)
            client_sock.close()
            print(f"Imagen enviada a {client_addr}\n")
            continue

        # Si no se revisa si la URL esta baneada o no
        else:
            ban_page = check(url)
            if not ban_page:
                # Página bloqueada: enviar respuesta 403 ERROR personalizada
                proxy_response_json = read_JSON("./ban/ban_response.json")
                body = read_HTML("./ban/ban.html")
                proxy_response_json["body"] = body
                    
            else:
                # Página permitida: conectar al servidor origen
                host = (client_request_json["headers"]["Host"].strip(), 80)
                proxy_client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                try:
                    proxy_client_sock.connect(host)
                    print(f"Proxy conectado a {host}")
                    
                    # Enviar request original
                    client_request = client_request.decode().rstrip("\r\n")
                    client_request += "\r\nX-ElQuePregunta: Jujalag\r\n\r\n"
                    proxy_client_sock.send(client_request.encode())
                    print("Proxy envió la request")
                    
                    # Recibir response del servidor
                    server_response = receive_full_msg(proxy_client_sock, buff_size)
                    print("Proxy recibió la response")
                    
                    # Parsear
                    proxy_response_json = parse_HTTP_msg(server_response.decode())

                finally:
                    proxy_client_sock.close()

            # filtrar palabras baneadas y enviar al cliente
            proxy_response_json_ban = forbidden_words(proxy_response_json)
            proxy_response = create_HTTP_msg(proxy_response_json_ban)

            # Enviar respuesta al cliente
            client_sock.send(proxy_response.encode())
            client_sock.close()


        print(f"Conexión con {client_addr} ha sido cerrada\n")