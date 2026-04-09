import socket
import dnslib
from dnslib import DNSRecord
from dnslib.dns import RR, A, CLASS, QTYPE


IP_VM = '192.168.1.109'
IP_DNS = '192.33.4.12'


PORT = 8000
PORT_DNS = 53
DEBUG_MODE = 1 # 1 = True / 0 = False


class DNSCache:
    #Caché para respuestas DNS que almacena los 3 dominios más consultados de las últimas 20 consultas.
    def __init__(self, max_queries=20, max_cached_domains=3):
        self.max_queries = max_queries
        self.max_cached_domains = max_cached_domains
        self.query_history = []  # Lista de consultas
        self.cache = {}
    

    def add_query(self, domain: str, ip: str):
        # Agrega una consulta al historial y actualiza el caché
        self.query_history.append(domain)
        # Mantener solo las últimas 20 consultas
        if len(self.query_history) > self.max_queries:
            self.query_history.pop(0)
        
        self.cache[domain] = ip
        self.update_cache()
    

    def update_cache(self):
        # Actualiza el caché para mantener solo los 3 dominios más frecuentes.
        if not self.query_history:
            return
        
        # Contar frecuencias manualmente
        freq_count = {}
        for domain in self.query_history:
            freq_count[domain] = freq_count.get(domain, 0) + 1
        
        # Obtener los 3 más frecuentes
        sorted_domains = sorted(freq_count.items(), key=lambda x: x[1], reverse=True)
        most_common = sorted_domains[:self.max_cached_domains]
        
        # Crear nuevo caché solo con los dominios más frecuentes
        new_cache = {}
        for domain, _ in most_common:
            if domain in self.cache:
                new_cache[domain] = self.cache[domain]
        self.cache = new_cache
    

    def get(self, domain: str):
        # Obtiene la dirección IP de un dominio del caché.
        return self.cache.get(domain)
    
    
    def is_cached(self, domain: str) -> bool:
        # Verifica si un dominio está en caché
        return domain in self.cache


# Instancia global del caché
cache = DNSCache()


def send_dns_message(query_name, address, port):
    # Acá ya no tenemos que crear el encabezado porque dnslib lo hace por nosotros, 
    # por default pregunta por el tipo A
    qname = query_name
    q = DNSRecord.question(qname)
    server_address = (address, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # lo enviamos, hacemos cast a bytes de lo que resulte de la función pack() sobre el mensaje
        sock.sendto(bytes(q.pack()), server_address)
        # En data quedará la respuesta a nuestra consulta
        data, _ = sock.recvfrom(4096)
        # le pedimos a dnslib que haga el trabajo de parsing por nosotros
        d = DNSRecord.parse(data)
    finally:
        sock.close()
    # Ojo que los datos de la respuesta van en en una estructura de datos
    return d


def parse_DNS_msg(dns_msg: DNSRecord) -> dict:  
    # Convierte un objeto DNSRecord en un diccionario estructurado con sus secciones.
    qname = None
    if dns_msg.questions:
        first_question = dns_msg.get_q()
        qname = str(first_question.get_qname())

    return {
        "Qname": qname,
        "ANCOUNT": dns_msg.header.a,
        "NSCOUNT": dns_msg.header.auth,
        "ARCOUNT": dns_msg.header.ar,
        "Answer": [rr_to_dict(rr) for rr in dns_msg.rr],
        "Authority": [rr_to_dict(rr) for rr in dns_msg.auth],
        "Additional": [rr_to_dict(rr) for rr in dns_msg.ar],
    }


def rr_to_dict(rr: dnslib.dns.RR) -> dict:
    # Convierte un registro DNS (Resource Record) a un diccionario con sus campos.
    return {
        "rname": str(rr.rname),
        "rtype": QTYPE.get(rr.rtype),
        "rclass": CLASS.get(rr.rclass),
        "ttl": rr.ttl,
        "rdata": str(rr.rdata),
    }


def resolver(msg_query: bytes, server_name: str = ".", server_address=(IP_DNS, PORT_DNS), from_cache=False) -> bytes:
    #  Resuelve recursivamente una consulta DNS siguiendo el árbol de servidores DNS.
    dns_query = DNSRecord.parse(msg_query)
    qname = dns_query.get_q().get_qname()
    qname_str = str(qname)
    
    # a) Verificar si la consulta está en caché
    if not from_cache and cache.is_cached(qname_str):
        cached_ip = cache.get(qname_str)
        if DEBUG_MODE:
            print(f"(debug) Respondiendo desde caché para {qname_str} -> {cached_ip}")
        dns_response = dns_query.reply()
        dns_response.add_answer(RR(qname, QTYPE.A, rdata=A(cached_ip)))
        return dns_response.pack()
    
    # Si no está en caché, hacer la consulta normal
    response = send_dns_message(qname, server_address[0], server_address[1])
    response_json = parse_DNS_msg(response)
    if DEBUG_MODE:
        print(f"(debug) Consultando {qname} a {server_name} con dirección IP {server_address[0]}")    

    # b) Revisar si la respuesta contiene una respuesta (Answer)
    if response_json.get('Answer'):
        # Tomamos las respuestas que sean de tipo A
        dns_response = dns_query.reply()
        a_answers = [ans for ans in response_json['Answer'] if ans['rtype'] == 'A']
        
        if a_answers:
            # Agregar TODOS los registros A a la respuesta
            for ans in a_answers:
                ip_answer = ans['rdata']
                dns_response.add_answer(RR(qname, QTYPE.A, rdata=A(ip_answer)))
            
            # Actualizar caché con la primera IP encontrada
            first_ip = a_answers[0]['rdata']
            cache.add_query(qname_str, first_ip)
            
            # Retornamos los bytes del mensaje listo para ser enviado al cliente
            return dns_response.pack()
            
        return b""

    else:
        # c) Revisar si hay delegación (NS en Authority)
        authority = response_json.get('Authority', [])
        additional = response_json.get('Additional', [])
        
        ns_records = [rr for rr in authority if rr['rtype'] == 'NS']
        a_records = [rr for rr in additional if rr['rtype'] == 'A']

        if ns_records and a_records:
            # c.i) Encontró A: usar la primera IP disponible
            first_a_record = a_records[0]
            next_server_ip = first_a_record['rdata']
            return resolver(msg_query, first_a_record['rname'], (next_server_ip, PORT_DNS), from_cache=True)

        else:
            # c.ii) No hay A: resolver recursivamente el NS
            if ns_records:
                ns_name = ns_records[0]['rdata']
                    
                ns_query = DNSRecord.question(ns_name)
                ns_query_bytes = bytes(ns_query.pack())
                # Esto ahora retorna BYTES
                ns_response_bytes = resolver(ns_query_bytes, ns_records[0]['rname'], (IP_DNS, PORT_DNS), from_cache=True)
                    
                # Como ns_response_bytes es de tipo bytes, debemos parsearlo antes de iterar
                if ns_response_bytes:
                    ns_response_record = DNSRecord.parse(ns_response_bytes)
                    ns_response_json = parse_DNS_msg(ns_response_record)
                    
                    for rr in ns_response_json.get('Answer', []):
                        if rr['rtype'] == 'A':
                            ns_ip = rr['rdata']
                            return resolver(msg_query, ns_records[0]['rname'], (ns_ip, PORT_DNS), from_cache=True)
                    
            # Si no se puede resolver, retornamos bytes vacíos
            return b""


if __name__ == "__main__":
    # DNS usa un socket NOC.
    addr = (IP_VM, PORT)
    buff_size = 4096
    
    print('Creando socket NOC - resolver')
    dns_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dns_sock.bind(addr)
    print(f"escuchando NOC en {addr}")

    while True:
        data, client_addr  = dns_sock.recvfrom(buff_size)
        print(f"Mensaje recibido desde {client_addr}")
        print(f"Bytes crudos:\n{data}\n")

        response_resolver = resolver(data)
        dns_sock.sendto(response_resolver, client_addr)
        
        # Mostrar estado del caché
        if DEBUG_MODE:
            print(f"\n(debug) Dominios en caché: {list(cache.cache.keys())}")
            print(f"(debug) Historial de consultas (últimas 20): {list(cache.query_history)}\n")
        print(f"Respuesta enviada a {addr}\n")
