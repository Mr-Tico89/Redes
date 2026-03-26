import socket
import json

IP_VM = '192.168.27.71'
PORT = 8000

def receive_full_message(connection_socket, buff_size, end_sequence): 
    # recibimos la primera parte del mensaje
    recv_message = connection_socket.recv(buff_size)
    full_message = recv_message

    # verificamos si llegó el mensaje completo o si aún faltan partes del mensaje
    is_end_of_message = contains_end_of_message(full_message.decode(), end_sequence)

    # entramos a un while para recibir el resto y seguimos esperando información mientras el buffer no contenga secuencia de fin de mensaje
    while not is_end_of_message:
        # recibimos un nuevo trozo del mensaje
        recv_message = connection_socket.recv(buff_size)

        # lo añadimos al mensaje "completo"
        full_message += recv_message
 
        # verificamos si es la última parte del mensaje
        is_end_of_message = contains_end_of_message(full_message.decode(), end_sequence)

    # removemos la secuencia de fin de mensaje, esto entrega un mensaje en string
    full_message = remove_end_of_message(full_message.decode(), end_sequence)
    
    json_message = parse_HTTP_message(full_message)

    # finalmente retornamos el mensaje JSON
    return json_message


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
    headers_dict["X-ElQuePregunta"] = "jujalag"
    
    # Construimos el mensaje HTTP
    http_message = ""
    for key, value in headers_dict.items():
        if key == "startLine":
            http_message += headers_dict["startLine"]
        else:
            http_message += f"{key}: {value}\r\n"


    # Separador entre headers y body
    http_message += "\r\n"

    # Elegimos el cuerpo según el código HTTP de la start line
    start_line = headers_dict.get("startLine", "")
    if " 200 " in start_line:
        with open("./response.html", "r", encoding="utf-8") as file:
            html_body = file.read()
        headers_dict["Content-Length"] = str(len(html_body.encode('utf-8')))
        http_message += html_body
    else:
        with open("./ban.html", "r", encoding="utf-8") as file:
            html_body = file.read()
        headers_dict["Content-Length"] = str(len(html_body.encode('utf-8')))
        http_message += html_body


    return http_message


def create_HTTP_body(code_HTTP):
    return True


def read_JSON_file(name, path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    return data


def check(json_msg):
    # docs
    ban_data = read_JSON_file("ban", "./ban.json")
    for host in ban_data["blocked"]:
        if host == json_msg["headers"]["Host"]:
            print(f"{json_msg}")
            # Host bloqueado: devolvemos start line 403
            json_msg["Headers"]["startLine"] = "HTTP/1.1 403 ERROR\r\n"
    
    return json_msg



if __name__ == "__main__":
    # definimos el tamaño del buffer de recepción y la secuencia de fin de mensaje
    buff_size = 4032
    end_of_message = "\r\n\r\n"
    addr = (IP_VM, PORT) 
    print('Creando socket - Proxy')

    proxy_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_server_socket.bind(addr)
    proxy_server_socket.listen(3)
    print(f"proxy escuchando en {addr}")

    while True:
        client_sock, client_addr = proxy_server_socket.accept()
        print(f"Cliente conectado desde {client_addr}")

        client_json = receive_full_message(client_sock, buff_size, end_of_message)
        code = check(client_json)
        client_json["headers"]["startLine"] = code
        
    
        client_request = create_HTTP_message(client_json)
        
        proxy_client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"{client_json}")
        proxy_client_sock.connect((client_json["headers"]["Host"], 80)) 
        proxy_client_sock.send(client_request.encode())

        server_json = receive_full_message(proxy_client_sock, buff_size, end_of_message)
        server_response = create_HTTP_message(server_json)

        client_sock.send(server_response.encode())
        
        proxy_client_sock.close()
        client_sock.close()
