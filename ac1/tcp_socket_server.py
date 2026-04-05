import socket
import json

IP_VM = '192.168.144.71'
PORT = 8000

def receive_full_msg(connection_socket, buff_size): 
    # 1. Recibir hasta que los HEADERS estén completos
    full_data = b""
    
    numero_de_lecturas = 0
    while b"\r\n\r\n" not in full_data:
        chunk = connection_socket.recv(buff_size)
        #if not chunk:
        #    break  # La conexión se cerró inesperadamente
        numero_de_lecturas = numero_de_lecturas + 1
        #print(f"Lectura #" + str(numero_de_lecturas) + ": Se leyeron " + str(len(chunk)) + " bytes.")
        full_data += chunk

    # Si no se encontró el fin de headers, retornamos lo que llegó
    if b"\r\n\r\n" not in full_data:
        return full_data

    # Separamos el HEAD del posible inicio del BODY que haya colado en el último recv
    headers_data, body_data_received = full_data.split(b"\r\n\r\n", 1)

    # 2. Buscar el Content-Length en los headers
    # Decodificamos solo los headers (es seguro porque los headers son texto ASCII)
    headers_text = headers_data.decode('utf-8', errors='ignore')
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

    return {"headers": headers, "body": parsed_body}


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
    with open(path, 'rb') as file:
        image_data = file.read()
    return image_data


def check(json_msg: dict) -> bool:
    # chekea si la url a la que va a entrar esta baneada o no
    ban_data = read_JSON("./ban/ban.json")
    start_line = json_msg["headers"]["startLine"].strip() # quitamos /r/n
    # dividimos el starLine en 3 GET, cc4303.bachmann.cl/secret, HTTP/1.1
    method, url, version = start_line.split(" ", 2) 
    
    for blocked in ban_data['blocked']:
        if url == blocked:
            # Host bloqueado: devolvemos start line 403 error al cliente
            json_msg["headers"]["startLine"] = version + " 403 ERROR"
            return False
        
    return True


def forbidden_words(json_msg: dict) -> dict:
    # revisa el body del http para cambiar las palabras baneadas por otras
    ban_words = read_JSON("./ban/ban.json")
    body = json_msg.get("body", "")
    for word_dict in ban_words.get('forbidden_words', []):
        for forbidden_word, replacement in word_dict.items():
            body = body.replace(forbidden_word, replacement)
        
    json_msg["body"] = body
    return json_msg


if __name__ == "__main__":
    buff_size = 6
    end_sequence = "\n"
    addr = (IP_VM, PORT) 
    print('Creando socket - Proxy')

    proxy_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_server_sock.bind(addr)
    proxy_server_sock.listen(3)
    print(f"proxy escuchando en {addr}")

    while True:
        client_sock, client_addr = proxy_server_sock.accept()
        print(f"Cliente conectado desde {client_addr}")
        client_request = receive_full_msg(client_sock, buff_size)
        client_request_json = parse_HTTP_msg(client_request.decode())
        
        # Extraer la URL de la request
        start_line = client_request_json["headers"]["startLine"].strip()
        method, url, version = start_line.split(" ", 2)
        
        # Si se solicita ban.jpg, servirla localmente
        if url.endswith("ban.jpg"):
            image_data = read_image("./ban/ban.jpg")
            # Construir headers para la imagen
            headers = f"HTTP/1.1 200 OK\r\n"
            headers += f"Content-Type: image/jpeg\r\n"
            headers += f"Content-Length: {len(image_data)}\r\n"
            headers += f"\r\n"
            
            # Enviar headers + imagen (binarios)
            client_sock.send(headers.encode() + image_data)
            client_sock.close()
            print(f"Imagen enviada a {client_addr}\n")
            continue
        
        else:
            ban_page = check(client_request_json)
            if not ban_page:
                # Página bloqueada: enviar respuesta 403 personalizada
                proxy_response_json = read_JSON("./ban/ban_response.json")
                body = read_HTML("./ban/ban.html")
                proxy_response_json["body"] = body
                    
            else:
                # Página permitida: conectar al servidor origen
                host = (client_request_json["headers"]["Host"].strip(), 80)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as proxy_client_sock:
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

            # filtrar palabras baneadas y enviar al cliente
            proxy_response_json_ban = forbidden_words(proxy_response_json)
            proxy_response = create_HTTP_msg(proxy_response_json_ban)

            # Enviar respuesta al cliente
            client_sock.send(proxy_response.encode())
            client_sock.close()


        print(f"Conexión con {client_addr} ha sido cerrada\n")