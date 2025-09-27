// --- CONFIGURAÇÃO ---
const API_ENDPOINT = 'http://127.0.0.1:5000/api/trafego/ultimos';
const POLLING_INTERVAL_MS = 2000; // Chamar a API a cada 2 segundos

// Variáveis para os objetos Chart.js
let mainChart = null;
let protocolChart = null;

// Armazena o último conjunto de dados recebido para ser usado no drill-down
let latestData = null;

// --- FUNÇÃO PRINCIPAL DE POLLING ---
async function fetchData() {
    try {
        const response = await fetch(API_ENDPOINT);
        if (!response.ok) {
            throw new Error(`Erro de rede! Status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 🚨 Ponto Crítico: Salva os dados para o drill-down
        latestData = data;
        
        // Processa e renderiza o gráfico principal (por cliente)
        renderMainChart(data.clientes);

        // Se o painel de detalhes estiver visível, atualiza ele também
        const detailContainer = document.getElementById('detail-container');
        if (detailContainer.style.display !== 'none') {
            const currentIP = document.getElementById('client-ip-title').textContent;
            if (currentIP) {
                const clientData = data.clientes.find(c => c.ip_cliente === currentIP);
                if (clientData) {
                    renderProtocolChart(clientData);
                }
            }
        }
        
        console.log(`Dados recebidos em: ${data.timestamp}. Clientes: ${data.clientes.length}`);
        
    } catch (error) {
        console.error("Erro ao buscar dados da API:", error.message);
        // Exibe uma mensagem de erro na tela se a API cair
        const container = document.getElementById('main-chart');
        container.innerHTML = `<p style="color: red;">Não foi possível conectar à API do Backend.</p>`;
    }
}

// --- FUNÇÃO DE RENDERIZAÇÃO DO GRÁFICO PRINCIPAL ---
function renderMainChart(clientes) {
    const ctx = document.getElementById('main-chart').getContext('2d');
    
    // 1. Prepara os dados no formato Chart.js
    const labels = clientes.map(c => c.ip_cliente);
    const trafegoIn = clientes.map(c => c.trafego_in / 1024); // Convertendo para KB
    const trafegoOut = clientes.map(c => c.trafego_out / 1024); // Convertendo para KB

    // Destroi o gráfico anterior para evitar sobreposição (fundamental no Polling)
    if (mainChart) {
        mainChart.destroy();
    }

    mainChart = new Chart(ctx, {
        type: 'bar', // Tipo de gráfico de barras
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Tráfego IN (KB)',
                    data: trafegoIn,
                    backgroundColor: 'rgba(75, 192, 192, 0.6)',
                },
                {
                    label: 'Tráfego OUT (KB)',
                    data: trafegoOut,
                    backgroundColor: 'rgba(255, 99, 132, 0.6)',
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Tráfego (KB)' } }
            },
            // 2. Implementa o CLICK para o Drill-Down
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const clientIP = labels[index];
                    
                    // Encontra os dados brutos do cliente que foi clicado
                    const clientData = latestData.clientes.find(c => c.ip_cliente === clientIP);
                    
                    if (clientData) {
                        showDetails(clientData); // Chama a função Drill-Down
                    }
                }
            }
        }
    });
}

// --- FUNÇÕES DE DRILL-DOWN ---

function showDetails(clientData) {
    // 1. Esconde o gráfico principal e mostra o detalhe
    document.getElementById('chart-container').style.display = 'none';
    document.getElementById('detail-container').style.display = 'block';

    // 2. Atualiza o título
    document.getElementById('client-ip-title').textContent = clientData.ip_cliente;

    // 3. Renderiza o gráfico de protocolo
    renderProtocolChart(clientData);
}

function renderProtocolChart(clientData) {
    const ctx = document.getElementById('protocol-chart').getContext('2d');
    
    // Prepara os dados dos protocolos para o gráfico
    const labels = clientData.detalhe_protocolos.map(p => p.protocolo);
    const inData = clientData.detalhe_protocolos.map(p => p.in / 1024);
    const outData = clientData.detalhe_protocolos.map(p => p.out / 1024);

    // Destroi o gráfico anterior
    if (protocolChart) {
        protocolChart.destroy();
    }

    protocolChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                { label: 'IN (KB)', data: inData, backgroundColor: 'rgba(75, 192, 192, 0.6)' },
                { label: 'OUT (KB)', data: outData, backgroundColor: 'rgba(255, 99, 132, 0.6)' }
            ]
        },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: true, title: { display: true, text: 'Tráfego (KB)' } } }
        }
    });
}

function hideDetails() {
    // Esconde o detalhe e mostra o gráfico principal
    document.getElementById('chart-container').style.display = 'block';
    document.getElementById('detail-container').style.display = 'none';
}


// --- INICIALIZAÇÃO DO POLLING ---
document.addEventListener('DOMContentLoaded', () => {
    // Faz a primeira chamada imediatamente
    fetchData();
    // Inicia o loop de Polling a cada 2 segundos
    setInterval(fetchData, POLLING_INTERVAL_MS);
});