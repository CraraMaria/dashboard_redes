from scapy.all import sniff, IP, TCP, UDP, conf

# --- CONFIGURAÇÃO CRÍTICA ---
# 🚨 MUDE ISTO para o IP do seu servidor alvo 🚨
SERVER_IP = "192.168.1.50" 

# Configura o Scapy para usar a interface de rede correta (opcional, mas recomendado para evitar problemas)
# Em muitos casos, o Scapy escolhe a correta, mas você pode forçar aqui
# conf.iface = "Sua interface de rede, ex: Ethernet ou Wi-Fi" 
# Para listar interfaces, rode 'scapy.all.show_interfaces()' no terminal.

# Filtro BPF (Berkeley Packet Filter)
# Garante que apenas o tráfego de/para o SERVER_IP seja processado, economizando CPU.
filtro_bpf = f"host {SERVER_IP}"

# --- LÓGICA DE PROCESSAMENTO ---
def process_packet(packet):
    """
    Função chamada a cada pacote capturado.
    Extrai as informações de IP, direção e protocolo.
    """
    if IP in packet:
        ip_src = packet[IP].src
        ip_dst = packet[IP].dst
        tamanho = len(packet)
        
        # 1. Determina a Direção e o Cliente (o IP que NÃO é o servidor)
        if ip_dst == SERVER_IP:
            direcao = "IN"
            cliente_ip = ip_src
        elif ip_src == SERVER_IP:
            direcao = "OUT"
            cliente_ip = ip_dst
        else:
            return # Ignora o pacote se não for de ou para o servidor
            
        # 2. Determina o Protocolo de Camada 4
        if TCP in packet:
            protocolo = "TCP"
        elif UDP in packet:
            protocolo = "UDP"
        else:
            protocolo = "OUTROS" # ICMP (ping), ARP, etc.
        
        # 3. Exibe o resultado no console
        print(f"[{direcao}]: Cliente={cliente_ip} | Proto={protocolo} | Bytes={tamanho}")

# --- INÍCIO DA CAPTURA ---
print(f"--- INICIANDO CAPTURA DE TESTE ---")
print(f"Servidor Alvo: {SERVER_IP}")
print(f"Filtro BPF Ativo: {filtro_bpf}")
print("Pressione Ctrl+C para parar a captura.")

try:
    # A função sniff é bloqueante e chama process_packet para cada pacote.
    # count=100 é um limite para o teste. Na versão final, será contínuo.
    sniff(filter=filtro_bpf, prn=process_packet, count=100, store=0) 
    
except Exception as e:
    print(f"\nERRO CRÍTICO NA CAPTURA: {e}")
    print("Se for erro de permissão, garanta que o VS Code está como Administrador.")