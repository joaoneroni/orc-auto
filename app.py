from flask import Flask, render_template, request, jsonify
import ezdxf
import os

app = Flask(__name__)

# Pasta para salvar os arquivos enviados
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Mapeamento de espessura de chapa para velocidade de corte (mm/s) e espessura (mm)
CHAPAS = {
    "CHAPA 20": {"velocidade_corte": 300, "espessura": 0.90},
    "CHAPA 18": {"velocidade_corte": 250, "espessura": 1.20},
    "CHAPA 16": {"velocidade_corte": 200, "espessura": 1.50},
    "CHAPA 14": {"velocidade_corte": 150, "espessura": 1.90},
    "CHAPA 1/8\"": {"velocidade_corte": 100, "espessura": 3.175},
    "CHAPA 3/16\"": {"velocidade_corte": 80, "espessura": 4.7625},
    "CHAPA 1/4\"": {"velocidade_corte": 60, "espessura": 6.35},
    "CHAPA 5/16\"": {"velocidade_corte": 40, "espessura": 7.9375},
    "CHAPA 3/8\"": {"velocidade_corte": 35, "espessura": 9.525},
    "CHAPA 1/2\"": {"velocidade_corte": 30, "espessura": 12.7},
    "CHAPA 5/8\"": {"velocidade_corte": 25, "espessura": 15.875},
}

# Mapeamento de materiais para suas constantes
MATERIAIS = {
    "AÇO 1020": {"constante": 0.00787, "chapas": ["CHAPA 20", "CHAPA 18", "CHAPA 16", "CHAPA 14", "CHAPA 1/8\"", "CHAPA 3/16\"", "CHAPA 1/4\"", "CHAPA 5/16\"", "CHAPA 3/8\"", "CHAPA 1/2\"", "CHAPA 5/8\""]},
    "AÇO 1045": {"constante": 0.00787, "chapas": ["CHAPA 1/8\"", "CHAPA 3/16\"", "CHAPA 1/4\"", "CHAPA 5/16\"", "CHAPA 3/8\"", "CHAPA 1/2\"", "CHAPA 5/8\""]},
    "ALUMINIO": {"constante": 0.00270, "chapas": ["CHAPA 20", "CHAPA 18", "CHAPA 16", "CHAPA 14", "CHAPA 1/8\"", "CHAPA 3/16\"", "CHAPA 1/4\""]},
    "INOX 304": {"constante": 0.00800, "chapas": ["CHAPA 20", "CHAPA 18", "CHAPA 16", "CHAPA 14", "CHAPA 1/8\"", "CHAPA 3/16\"", "CHAPA 1/4\""]},
    "INOX 430": {"constante": 0.00800, "chapas": ["CHAPA 20", "CHAPA 18", "CHAPA 16", "CHAPA 14"]},
}

# Mapeamento de preços para cada combinação de material e espessura de chapa
PRECOS = {
    "AÇO 1020": {
        "CHAPA 20": 13.50,
        "CHAPA 18": 11.00,
        "CHAPA 16": 12.00,
        "CHAPA 14": 13.00,
        "CHAPA 1/8\"": 14.00,
        "CHAPA 3/16\"": 15.00,
        "CHAPA 1/4\"": 16.00,
        "CHAPA 5/16\"": 17.00,
        "CHAPA 3/8\"": 18.00,
        "CHAPA 1/2\"": 19.00,
        "CHAPA 5/8\"": 20.00,
    },
    "AÇO 1045": {
        "CHAPA 1/8\"": 14.50,
        "CHAPA 3/16\"": 15.50,
        "CHAPA 1/4\"": 16.50,
        "CHAPA 5/16\"": 17.50,
        "CHAPA 3/8\"": 18.50,
        "CHAPA 1/2\"": 19.50,
        "CHAPA 5/8\"": 20.50,
    },
    "ALUMINIO": {
        "CHAPA 20": 20.50,
        "CHAPA 18": 21.50,
        "CHAPA 16": 22.50,
        "CHAPA 14": 23.50,
        "CHAPA 1/8\"": 24.50,
        "CHAPA 3/16\"": 25.50,
        "CHAPA 1/4\"": 26.50,
    },
    "INOX 304": {
        "CHAPA 20": 50.00,
        "CHAPA 18": 51.00,
        "CHAPA 16": 52.00,
        "CHAPA 14": 53.00,
        "CHAPA 1/8\"": 54.00,
        "CHAPA 3/16\"": 55.00,
        "CHAPA 1/4\"": 56.00,
    },
    "INOX 430": {
        "CHAPA 20": 30.00,
        "CHAPA 18": 31.00,
        "CHAPA 16": 32.00,
        "CHAPA 14": 33.00,
    },
}

def calcular_perimetro_e_area(dxf_path):
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        perimetro_total = 0.0

        # Inicializa as coordenadas mínimas e máximas para a bounding box
        x_coords = []
        y_coords = []

        for entity in msp:
            if entity.dxftype() in ['LINE', 'ARC', 'CIRCLE', 'SPLINE']:
                if entity.dxftype() == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    perimetro_total += ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
                    x_coords.extend([start[0], end[0]])
                    y_coords.extend([start[1], end[1]])
                elif entity.dxftype() == 'ARC':
                    raio = entity.dxf.radius
                    angulo_inicial = entity.dxf.start_angle
                    angulo_final = entity.dxf.end_angle
                    comprimento_arco = raio * abs(angulo_final - angulo_inicial) * (3.141592653589793 / 180)
                    perimetro_total += comprimento_arco
                    # Aproximação da bounding box para arcos
                    centro = entity.dxf.center
                    x_coords.extend([centro[0] - raio, centro[0] + raio])
                    y_coords.extend([centro[1] - raio, centro[1] + raio])
                elif entity.dxftype() == 'CIRCLE':
                    raio = entity.dxf.radius
                    perimetro_total += 2 * 3.141592653589793 * raio
                    centro = entity.dxf.center
                    x_coords.extend([centro[0] - raio, centro[0] + raio])
                    y_coords.extend([centro[1] - raio, centro[1] + raio])
                elif entity.dxftype() == 'SPLINE':
                    # Aproximação do comprimento da spline
                    pontos = entity.flattening(0.01)
                    for i in range(1, len(pontos)):
                        perimetro_total += ((pontos[i][0] - pontos[i-1][0])**2 + (pontos[i][1] - pontos[i-1][1])**2)**0.5
                    x_coords.extend([p[0] for p in pontos])
                    y_coords.extend([p[1] for p in pontos])

        # Calcula a bounding box
        if not x_coords or not y_coords:
            return None, None, None, None

        min_x = min(x_coords)
        max_x = max(x_coords)
        min_y = min(y_coords)
        max_y = max(y_coords)

        largura = max_x - min_x
        altura = max_y - min_y
        area_total = largura * altura

        return perimetro_total, largura, altura, area_total
    except Exception as e:
        print(f"Erro ao calcular perímetro e área: {e}")
        return None, None, None, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

    # Verifica se o arquivo tem uma extensão .dxf
    if not file.filename.lower().endswith('.dxf'):
        return jsonify({'error': 'Formato de arquivo inválido. Apenas arquivos DXF são permitidos.'}), 400

    # Obtém a espessura de chapa selecionada
    espessura_chapa = request.form.get('espessura_chapa')
    if espessura_chapa not in CHAPAS:
        return jsonify({'error': 'Espessura de chapa inválida.'}), 400

    # Obtém o material selecionado
    material = request.form.get('material')
    if material not in MATERIAIS:
        return jsonify({'error': 'Material inválido.'}), 400

    # Verifica se a espessura de chapa é válida para o material selecionado
    if espessura_chapa not in MATERIAIS[material]["chapas"]:
        return jsonify({'error': 'Espessura de chapa inválida para o material selecionado.'}), 400

    # Obtém a velocidade de corte e a espessura correspondente
    velocidade_corte = CHAPAS[espessura_chapa]["velocidade_corte"]
    espessura = CHAPAS[espessura_chapa]["espessura"]

    # Obtém a constante do material
    constante_material = MATERIAIS[material]["constante"]

    # Obtém o preço do material e espessura selecionados
    preco_material = PRECOS[material][espessura_chapa]

    try:
        # Salva o arquivo temporariamente
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Calcula o perímetro, largura, altura e área total
        perimetro, largura, altura, area_total = calcular_perimetro_e_area(file_path)
        if perimetro is None:
            return jsonify({'error': 'Erro ao processar o arquivo DXF. Verifique se o arquivo é válido.'}), 400

        # Calcula o tempo de corte
        tempo_corte = perimetro / velocidade_corte

        # Calcula o peso
        peso = area_total * espessura * constante_material  # Peso em gramas

        # Calcula o preço da peça
        preco = (((500 * tempo_corte) / 3600) + (peso * preco_material) / 1000)

        return jsonify({
            'perimetro': perimetro,
            'tempo_corte': tempo_corte,
            'largura': largura,
            'altura': altura,
            'area_total': area_total,
            'peso': peso,
            'preco': preco
        })
    except Exception as e:
        print(f"Erro ao processar arquivo: {e}")
        return jsonify({'error': 'Erro interno ao processar o arquivo.'}), 500
    finally:
        # Remove o arquivo após o processamento
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == '__main__':
    app.run(debug=True)