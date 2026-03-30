 Estrategia:
    1. Acumula datos en bytes hasta encontrar \\r\\n\\r\\n (fin de headers)
    2. Parsea los headers para extraer Content-Length
    3. Lee exactamente Content-Length bytes del body
    
    ¿Cómo sé si llegó el mensaje completo?
    - Para HTTP: cuando recibo headers completos (\\r\\n\\r\\n) + exactamente Content-Length bytes del body
    
    ¿Qué pasa si los headers no caben en mi buffer?
    - El bucle sigue recibiendo chunks de buff_size hasta encontrar \\r\\n\\r\\n
    - Los bytes se acumulan, así que headers grandes se reciben en múltiples recv()
    
    ¿Cómo sé que el HEAD llegó completo?
    - Cuando encuentro la secuencia \\r\\n\\r\\n en los datos acumulados
    
    ¿Y el BODY?
    - Después de encontrar \\r\\n\\r\\n, extraigo Content-Length del header
    - Leo exactamente esa cantidad de bytes; ni más, ni menos