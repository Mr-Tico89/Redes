# dig -p8000 @192.168.1.109 www.uchile.cl


; <<>> DiG 9.20.21-1~deb13u1-Debian <<>> -p8000 @192.168.1.109 www.uchile.cl
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 61054
;; flags: qr aa rd ra ad; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;www.uchile.cl.                 IN      A

;; ANSWER SECTION:
www.uchile.cl.          300     IN      A       200.89.76.36

;; Query time: 160 msec
;; SERVER: 192.168.1.109#8000(192.168.1.109) (UDP)
;; WHEN: Wed Apr 08 17:09:19 -04 2026
;; MSG SIZE  rcvd: 47


# dig @8.8.8.8 www.uchile.cl

; <<>> DiG 9.20.21-1~deb13u1-Debian <<>> @8.8.8.8 www.uchile.cl
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 40785
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 512
;; QUESTION SECTION:
;www.uchile.cl.                 IN      A

;; ANSWER SECTION:
www.uchile.cl.          300     IN      A       200.89.76.36

;; Query time: 32 msec
;; SERVER: 8.8.8.8#53(8.8.8.8) (UDP)
;; WHEN: Wed Apr 08 17:09:49 -04 2026
;; MSG SIZE  rcvd: 58





# test con cache vs sin cache
pss@debian13:~$ dig -p8000 @192.168.1.109 cc4303.bachmann.cl

; <<>> DiG 9.20.21-1~deb13u1-Debian <<>> -p8000 @192.168.1.109 cc4303.bachmann.cl
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 31524
;; flags: qr aa rd ra ad; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;cc4303.bachmann.cl.            IN      A

;; ANSWER SECTION:
cc4303.bachmann.cl.     0       IN      A       104.248.65.245

;; Query time: 635 msec
;; SERVER: 192.168.1.109#8000(192.168.1.109) (UDP)
;; WHEN: Thu Apr 09 16:52:14 -04 2026
;; MSG SIZE  rcvd: 52

pss@debian13:~$ dig -p8000 @192.168.1.109 cc4303.bachmann.cl

; <<>> DiG 9.20.21-1~deb13u1-Debian <<>> -p8000 @192.168.1.109 cc4303.bachmann.cl
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 27193
;; flags: qr aa rd ra ad; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;cc4303.bachmann.cl.            IN      A

;; ANSWER SECTION:
cc4303.bachmann.cl.     0       IN      A       104.248.65.245

;; Query time: 3 msec
;; SERVER: 192.168.1.109#8000(192.168.1.109) (UDP)
;; WHEN: Thu Apr 09 16:52:15 -04 2026
;; MSG SIZE  rcvd: 52




# resolver el siguiente dominio con su programa www.webofscience.com

dig -p8000 @192.168.1.109 www.webofscience.com
;; Warning: short (< header size) message received
;; communications error to 192.168.1.109#8000: timed out
;; Warning: short (< header size) message received
;; communications error to 192.168.1.109#8000: timed out
;; Warning: short (< header size) message received
;; communications error to 192.168.1.109#8000: timed out

; <<>> DiG 9.20.21-1~deb13u1-Debian <<>> -p8000 @192.168.1.109 www.webofscience.com
; (1 server found)
;; global options: +cmd
;; no servers could be reached


¿Resuelve su programa este dominio? no
¿Qué sucede?  se demora mucho
¿Por qué?  quizas no haya dns cercano que tenga info de esa pagina o q no tenga permisos
¿Cómo arreglaría usted este problema? nose :)

# bachmann vs www.bachmann

 dig -p8000 @192.168.1.109 www.cc4303.bachmann.cl
;; Warning: short (< header size) message received
;; communications error to 192.168.1.109#8000: timed out
;; Warning: short (< header size) message received
;; communications error to 192.168.1.109#8000: timed out
;; Warning: short (< header size) message received
;; communications error to 192.168.1.109#8000: timed out

; <<>> DiG 9.20.21-1~deb13u1-Debian <<>> -p8000 @192.168.1.109 www.cc4303.bachmann.cl
; (1 server found)
;; global options: +cmd
;; no servers could be reached


dig -p8000 @192.168.1.109 cc4303.bachmann.cl

; <<>> DiG 9.20.21-1~deb13u1-Debian <<>> -p8000 @192.168.1.109 cc4303.bachmann.cl
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 58174
;; flags: qr aa rd ra ad; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;cc4303.bachmann.cl.            IN      A

;; ANSWER SECTION:
cc4303.bachmann.cl.     0       IN      A       104.248.65.245

;; Query time: 3 msec
;; SERVER: 192.168.1.109#8000(192.168.1.109) (UDP)
;; WHEN: Thu Apr 09 16:56:52 -04 2026
;; MSG SIZE  rcvd: 52

¿Qué ocurre? si ponemos www antes no encuentra el domininio
¿Qué habría esperado que ocurriera? que encontrara el dominio




# lab
(debug) Consultando cc4303.bachmann.cl. a . con dirección IP 192.33.4.12
(debug) Consultando cc4303.bachmann.cl. a cl2-tld.d-zone.ca. con dirección IP 185.159.198.56
(debug) Consultando ns1.digitalocean.com. a bachmann.cl. con dirección IP 192.33.4.12
(debug) Consultando ns1.digitalocean.com. a m.gtld-servers.net. con dirección IP 192.55.83.30
(debug) Consultando ns1.digitalocean.com. a kim.ns.cloudflare.com. con dirección IP 108.162.192.126
(debug) Consultando cc4303.bachmann.cl. a bachmann.cl. con dirección IP 172.64.52.210


(debug) Consultando cc4303.bachmann.cl. a . con dirección IP 192.33.4.12
(debug) Consultando cc4303.bachmann.cl. a cl2-tld.d-zone.ca. con dirección IP 185.159.198.56
(debug) Consultando ns1.digitalocean.com. a bachmann.cl. con dirección IP 192.33.4.12
(debug) Consultando ns1.digitalocean.com. a m.gtld-servers.net. con dirección IP 192.55.83.30
(debug) Consultando ns1.digitalocean.com. a kim.ns.cloudflare.com. con dirección IP 108.162.192.126
(debug) Consultando cc4303.bachmann.cl. a bachmann.cl. con dirección IP 172.64.52.210

(debug) Consultando cc4303.bachmann.cl. a . con dirección IP 192.33.4.12
(debug) Consultando cc4303.bachmann.cl. a cl2-tld.d-zone.ca. con dirección IP 185.159.198.56
(debug) Consultando ns1.digitalocean.com. a bachmann.cl. con dirección IP 192.33.4.12
(debug) Consultando ns1.digitalocean.com. a m.gtld-servers.net. con dirección IP 192.55.83.30
(debug) Consultando ns1.digitalocean.com. a kim.ns.cloudflare.com. con dirección IP 108.162.192.126
(debug) Consultando cc4303.bachmann.cl. a bachmann.cl. con dirección IP 172.64.52.210


(debug) Consultando cc4303.bachmann.cl. a . con dirección IP 192.33.4.12
(debug) Consultando cc4303.bachmann.cl. a cl2-tld.d-zone.ca. con dirección IP 185.159.198.56
(debug) Consultando ns1.digitalocean.com. a bachmann.cl. con dirección IP 192.33.4.12
(debug) Consultando ns1.digitalocean.com. a m.gtld-servers.net. con dirección IP 192.55.83.30
(debug) Consultando ns1.digitalocean.com. a kim.ns.cloudflare.com. con dirección IP 108.162.192.126
(debug) Consultando cc4303.bachmann.cl. a bachmann.cl. con dirección IP 172.64.52.210

(debug) Consultando cc4303.bachmann.cl. a . con dirección IP 192.33.4.12
(debug) Consultando cc4303.bachmann.cl. a cl2-tld.d-zone.ca. con dirección IP 185.159.198.56
(debug) Consultando ns1.digitalocean.com. a bachmann.cl. con dirección IP 192.33.4.12
(debug) Consultando ns1.digitalocean.com. a m.gtld-servers.net. con dirección IP 192.55.83.30
(debug) Consultando ns1.digitalocean.com. a kim.ns.cloudflare.com. con dirección IP 108.162.192.126
(debug) Consultando cc4303.bachmann.cl. a bachmann.cl. con dirección IP 172.64.52.210


¿Son siempre los mismos Name Servers? si
¿Por qué cree usted que sucede esto? por que son los mas cercanos, a menos que cambie den de lugar o eliminen la info del dominio no deberia cambiar