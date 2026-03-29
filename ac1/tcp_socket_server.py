import socket
import json

IP_VM = '192.168.1.109'
PORT = 8000

def receive_full_message(connection_socket, buff_size, end_sequence): 
    """
    Recibe un mensaje HTTP completo manejando buffers pequeños.
    
    Estrategia:
    1. Acumula datos en bytes hasta encontrar \r\n\r\n (fin de headers)
    2. Parsea los headers para extraer Content-Length
    3. Lee exactamente Content-Length bytes del body
    
    ¿Cómo sé si llegó el mensaje completo?
    - Para HTTP: cuando recibo headers completos (\r\n\r\n) + exactamente Content-Length bytes del body
    
    ¿Qué pasa si los headers no caben en mi buffer?
    - El bucle sigue recibiendo chunks de buff_size hasta encontrar \r\n\r\n
    - Los bytes se acumulan, así que headers grandes se reciben en múltiples recv()
    
    ¿Cómo sé que el HEAD llegó completo?
    - Cuando encuentro la secuencia \r\n\r\n en los datos acumulados
    
    ¿Y el BODY?
    - Después de encontrar \r\n\r\n, extraigo Content-Length del header
    - Leo exactamente esa cantidad de bytes; ni más, ni menos
    """
    full_message = b''
    headers_complete = False
    content_length = 0
    body_received = 0
    
    while True:
        recv_message = connection_socket.recv(buff_size)
        if not recv_message:  # conexión cerrada
            break
        
        full_message += recv_message
        
        # Aún no tenemos headers completos
        if not headers_complete:
            # Buscar el fin de headers: \r\n\r\n
            if b'\r\n\r\n' in full_message:
                headers_complete = True
                # Extraer headers para obtener Content-Length
                header_end = full_message.find(b'\r\n\r\n')
                headers_bytes = full_message[:header_end]
                headers_str = headers_bytes.decode('utf-8', errors='ignore')
                
                # Parsear Content-Length
                for line in headers_str.split('\r\n'):
                    if line.lower().startswith('content-length:'):
                        try:
                            content_length = int(line.split(':')[1].strip())
                        except (ValueError, IndexError):
                            content_length = 0
                        break
                
                # Calcular cuántos bytes del body ya tenemos
                body_start = header_end + 4  # +4 por \r\n\r\n
                body_received = len(full_message) - body_start
        
        # Si headers están completos, verificar si tenemos todo el body
        if headers_complete:
            body_start = full_message.find(b'\r\n\r\n') + 4
            body_received = len(full_message) - body_start
            
            # Si ya recibimos todo el body, terminamos
            if body_received >= content_length:
                break
    
    # Decodificar todo el mensaje
    try:
        message_str = full_message.decode('utf-8')
    except UnicodeDecodeError:
        message_str = full_message.decode('utf-8', errors='ignore')
    
    return message_str
 
 
def contains_end_of_message(message, end_sequence):
    return message.endswith(end_sequence)
 
 
def remove_end_of_message(full_message, end_sequence):
    index = full_message.rfind(end_sequence)
    return full_message[:index]


def parse_HTTP_message(http_message):
    # Toma un mensaje HTTP y lo transforma a JSON permitiendo acceder fácil a la info del mensaje.
    
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


def create_HTTP_message(json_msg):
    # Toma un diccionario JSON y lo convierte en un mensaje HTTP
    headers_dict = json_msg.get("headers", {})
    body = json_msg.get("body", "")
    headers_dict["Content-Length"] = str(len(body.encode("utf-8")))

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

    # Elegimos el cuerpo según el código HTTP de la start line
    return http_message


def read_JSON_file(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def read_HTML_file(path):
    with open(path, "r", encoding="utf-8") as file:
        body = file.read()
    return body


def check(json_msg):
    # docs
    ban_data = read_JSON_file("./ban/ban.json")
    start_line = json_msg["headers"]["startLine"].strip()
    method, url, version = start_line.split(" ", 2)

    for blocked in ban_data['blocked']:
        if url == blocked:
            # Host bloqueado: devolvemos start line 403 error al cliente
            json_msg["headers"]["startLine"] = version + " 403 ERROR"
            return False
    return True


def forbidden_words(json_msg):
    ban_words = read_JSON_file("./ban/ban.json")
    body = json_msg.get("body", "")
    for word_dict in ban_words.get('forbidden_words', []):
        for forbidden_word, replacement in word_dict.items():
            body = body.replace(forbidden_word, replacement)
    
    json_msg["body"] = body
    return json_msg


if __name__ == "__main__":
    # Buffer pequeño para demostrar que funciona incluso con buff_size << tamaño del mensaje
    buff_size = 50  # Mucho más pequeño que un mensaje HTTP típico
    addr = (IP_VM, PORT) 
    print('Creando socket - Proxy')

    proxy_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_server_sock.bind(addr)
    proxy_server_sock.listen(3)
    print(f"proxy escuchando en {addr}")

    while True:
        client_sock, client_addr = proxy_server_sock.accept()
        print(f"Cliente conectado desde {client_addr}")
        client_request = receive_full_message(client_sock, buff_size, None)
        client_request_json = parse_HTTP_message(client_request)
        ban_page = check(client_request_json)
        
        if not ban_page:
            # Página bloqueada: enviar respuesta 403 personalizada
            ban_response = read_JSON_file("./ban/ban_response.json")
            body = read_HTML_file("./ban/ban.html")
            ban_response["body"] = body
            proxy_response = create_HTTP_message(ban_response)
        
        else:
            # Página permitida: conectar al servidor origen
            host = (client_request_json["headers"]["Host"].strip(), 80)
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as proxy_client_sock:
                proxy_client_sock.connect(host)
                print(f"Proxy conectado a {host}")
                
                # Enviar request original
                client_request = client_request.rstrip("\r\n")
                client_request += "\r\nX-ElQuePregunta: Jujalag\r\n\r\n"
                proxy_client_sock.sendall(client_request.encode())
                print("Proxy envió la request")
                
                # Recibir response del servidor (también con buff_size pequeño)
                proxy_response = receive_full_message(proxy_client_sock, buff_size, None)
                print("Proxy recibió la response")
                
                # Parsear y filtrar palabras baneadas
                proxy_response_json = parse_HTTP_message(proxy_response)
                proxy_response_json = forbidden_words(proxy_response_json)
                proxy_response = create_HTTP_message(proxy_response_json)
        
        # Enviar respuesta al cliente
        client_sock.sendall(proxy_response.encode())
        client_sock.close()
        print(f"Conexión con {client_addr} ha sido cerrada\n")


