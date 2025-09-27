from flask import Flask, jsonify
from flask_cors import CORS
from scapy.all import sniff, IP, TCP, UDP
import threading
import time
from datetime import datetime
import json

# --- CONFIGURAÇÃO DE REDE ---
# 🚨 MUDE ISTO para o IP do seu servidor alvo 🚨
SERVER_IP = "192.168.1.50"
FILTRO_BPF = f"host {SERVER_IP}"
JANELA_TEMPO_SEGUNDOS = 5

# --- ESTRUTURAS DE DADOS GLOBAIS ---
# Use um Lock para garantir que a escrita (pela captura) e a leitura (pela API/Timer)
# das estruturas de dados não ocorram simultaneamente, evitando corrupção.
data_lock = threading.Lock()

# Armazena os dados da janela de 5 segundos ATUAL.
# Exemplo: {'192.168.1.10': {'IN': 1000, 'OUT': 500, 'protocols': {'TCP': {'IN': 900, 'OUT': 400}, 'UDP': {'IN': 100, 'OUT': 100}}}}
current_window_data = {} 

# Armazena o HISTÓRICO de dados. A API lerá daqui.
# Armazenaremos apenas a última janela salva.
last_saved_data = {} 
last_saved_timestamp = None


# --- LÓGICA DE CAPTURA E AGREGAÇÃO (Executado em uma Thread) ---

def process_packet(packet):
    """Função chamada pelo Scapy. Agrega os dados na estrutura 'current_window_data'."""
    if IP in packet:
        ip_src = packet[IP].src
        ip_dst = packet[IP].dst
        tamanho = len(packet)
        
        # 1. Determina Direção (IN/OUT) e Cliente (o IP oposto ao servidor)
        if ip_dst == SERVER_IP:
            direcao = "IN"
            cliente_ip = ip_src
        elif ip_src == SERVER_IP:
            direcao = "OUT"
            cliente_ip = ip_dst
        else:
            return

        # 2. Determina o Protocolo
        if TCP in packet:
            protocolo = "TCP"
        elif UDP in packet:
            protocolo = "UDP"
        else:
            protocolo = "OUTROS"
            
        # 3. ATUALIZAÇÃO SEGURA da estrutura de dados global
        with data_lock:
            # Inicializa o cliente se for a primeira vez
            if cliente_ip not in current_window_data:
                current_window_data[cliente_ip] = {'IN': 0, 'OUT': 0, 'protocols': {}}
            
            # Adiciona o tamanho do pacote ao total IN/OUT
            current_window_data[cliente_ip][direcao] += tamanho
            
            # Adiciona o detalhe do protocolo (para drill-down)
            if protocolo not in current_window_data[cliente_ip]['protocols']:
                current_window_data[cliente_ip]['protocols'][protocolo] = {'IN': 0, 'OUT': 0}
            
            current_window_data[cliente_ip]['protocols'][protocolo][direcao] += tamanho

def start_packet_capture():
    """Função que inicia a captura de pacotes em loop infinito."""
    print("Captura de pacotes iniciada...")
    # store=0: Não armazena pacotes na memória (economiza RAM)
    # timeout=1: A captura reinicia a cada segundo. Necessário para poder parar a thread.
    sniff(filter=FILTRO_BPF, prn=process_packet, store=0) 


# --- LÓGICA DE JANELA DE TEMPO (Executado em uma Thread/Timer) ---

def aggregate_and_reset():
    """
    Função chamada a cada JANELA_TEMPO_SEGUNDOS (5s).
    Salva os dados coletados e reseta a contagem para a próxima janela.
    """
    global current_window_data, last_saved_data, last_saved_timestamp

    # Bloqueia o acesso enquanto copia e reseta
    with data_lock:
        # 1. Salva os dados ATUAIS como o último dado salvo
        last_saved_data = current_window_data
        last_saved_timestamp = datetime.now().isoformat()
        
        # 2. Reseta a contagem para a próxima janela de 5s
        current_window_data = {}
    
    # Imprime no console para debug
    if last_saved_data:
        print(f"[{last_saved_timestamp}] DADOS SALVOS. Clientes: {len(last_saved_data)}")
        
    # Reinicia o Timer para chamar a si mesmo em 5 segundos (loop do timer)
    threading.Timer(JANELA_TEMPO_SEGUNDOS, aggregate_and_reset).start()

# --- API RESTful (FLASK) ---

app = Flask(__name__)
# Permite que o frontend (em outra porta, ex: 5500) acesse esta API
CORS(app) 

def format_data_for_frontend(raw_data):
    """Converte a estrutura de dados interna para o formato JSON final para o frontend."""
    clientes_formatados = []
    
    for ip_cliente, dados in raw_data.items():
        detalhe_protocolos = []
        for proto, volumes in dados['protocols'].items():
            detalhe_protocolos.append({
                "protocolo": proto,
                "in": volumes['IN'],
                "out": volumes['OUT']
            })
            
        clientes_formatados.append({
            "ip_cliente": ip_cliente,
            "trafego_in": dados['IN'],
            "trafego_out": dados['OUT'],
            "detalhe_protocolos": detalhe_protocolos
        })
        
    return {
        "timestamp": last_saved_timestamp,
        "clientes": clientes_formatados
    }


@app.route('/api/trafego/ultimos', methods=['GET'])
def get_latest_traffic():
    """Endpoint da API que retorna o último conjunto de dados agregados (da última janela de 5s)."""
    with data_lock:
        data_to_serve = last_saved_data.copy()

    formatted_response = format_data_for_frontend(data_to_serve)
    return jsonify(formatted_response)


# --- INICIALIZAÇÃO ---

if __name__ == '__main__':
    # 1. Inicia o Timer de 5s em uma Thread separada
    print("Iniciando o Timer de Agregação de 5 segundos...")
    aggregate_and_reset() # A primeira chamada inicia o loop do timer
    
    # 2. Inicia a Captura de Pacotes em outra Thread separada
    # É fundamental que a captura seja separada para não bloquear o servidor Flask
    capture_thread = threading.Thread(target=start_packet_capture, daemon=True)
    capture_thread.start()
    
    # 3. Inicia o Servidor Flask (API)
    print("Iniciando o servidor Flask em http://127.0.0.1:5000")
    # debug=False é recomendado para ambientes com multithreading
    app.run(debug=False, port=5000)