from flask import Flask, render_template, request, redirect, make_response, session, jsonify, flash, url_for
import psycopg2
import bcrypt
from psycopg2.extras import RealDictCursor

from werkzeug.utils import secure_filename
import os
import secrets

from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors



app = Flask(__name__)
app.config['SECRET_KEY'] = '1212'  # Troque por uma chave secreta forte
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # O tamanho da foto deve ser até 16 MB



# Certifique-se de que o diretório de uploads exista
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

DATABASE_URL = "postgresql://postgres:1234@localhost:5432/postgres"

# Função para conectar ao banco de dados
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


# Rota para a página principal
@app.route('/')
def index():
    if 'user_id' in session:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT nome FROM usuarios WHERE id = %s', (session['user_id'],))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                nome_usuario = user[0]
                return render_template('pagina_principal.html', nome_usuario=nome_usuario)
            else:
                flash('Usuário não encontrado.', 'danger')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'Erro ao obter nome do usuário: {str(e)}', 'danger')
            return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))
    

#ROTA PARA A PÁGINA DE OPÇÕES
@app.route('/pagina_opcoes')
def pagina_opcoes():
    if 'user_id' in session:
        return render_template('index.html')
    else:
        return redirect(url_for('login'))    
    


#ROTA PARA A PÁGINA DE AJUDA 
@app.route('/pagina_ajuda')
def pagina_ajuda():
    return render_template('pagina_ajuda.html')    

   



# Rota para cadastro de novos usuários
@app.route('/cadastre_usuarios', methods=['GET', 'POST'])
def cadastre_usuarios():
    if request.method == 'POST':
        matricula = request.form.get('matricula', '')
        nome = request.form.get('nome', '')
        email = request.form.get('email', '')
        senha = request.form.get('senha', '')
        setor = request.form.get('setor', '')
        unidade = request.form.get('unidade', '')
        permissao = request.form.get('permissao', '')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verifica se o e-mail já existe
            cursor.execute('SELECT * FROM usuarios WHERE email = %s', (email,))
            email_exists = cursor.fetchone()

            # Verifica se a senha já existe
            cursor.execute('SELECT * FROM usuarios WHERE senha = %s', (senha,))
            senha_exists = cursor.fetchone()

            if email_exists:
                flash('E-mail já cadastrado. Tente outro e-mail.', 'warning')
                return render_template('cadastros_usuario.html', nome=nome, email=email, senha=senha)
            elif senha_exists:
                flash('Senha já cadastrada. Tente outra senha.', 'warning')
                return render_template('cadastros_usuario.html', nome=nome, email=email, senha=senha)
            else:
                cursor.execute(
                    'INSERT INTO usuarios (matricula, nome, email, senha, setor, unidade, permissao) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                    (matricula, nome, email, senha, setor, unidade, permissao)
                )
                conn.commit()
                cursor.close()
                conn.close()
                flash('Usuário cadastrado com sucesso! Faça login para continuar.', 'success')
                return redirect(url_for('login'))
            
        except Exception as e:
            flash(f'Erro ao cadastrar usuário: {str(e)}', 'danger')
            return render_template('cadastros_usuario.html', nome=nome, email=email, senha=senha, setor=setor, unidade=unidade, permissao=permissao)

    return render_template('cadastros_usuario.html')



# Rota para login de usuários
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, nome FROM usuarios WHERE email = %s AND senha = %s', (email, senha))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                session['user_id'] = user[0]  # Supondo que o ID do usuário seja o primeiro campo
                return redirect(url_for('index'))
            else:
                flash('E-mail ou senha inválidos. Tente novamente.', 'danger')
                return render_template('login1.html', email=email)
        except Exception as e:
            flash(f'Erro ao tentar login: {str(e)}', 'danger')
            return render_template('login1.html', email=email)

    return render_template('login1.html')







#ROTA PARA GERAR UM RELATÓRIO EM PDF, ONDE IRÁ MOSTRAR AS SOLICITAÇÕES
@app.route('/gerar_servicos_pdf')
def gerar_pdf():
    # Conectar ao banco de dados e obter os dados
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT servicos_id_seq, assunto, funcionario, prazo, setor, nome_solicitante, telefone, unidade, informacoes_adicionais FROM servicos')
    servicos = cursor.fetchall()
    cursor.close()
    conn.close()

    # Pdf_buffer é uma variável que usa a função da classe BytesIO para armazenar o PDF em memória
    pdf_buffer = BytesIO()

    # Cria o canvas para o PDF com um tamanho de página personalizado
    custom_page_size = (1850, 600)  # Exemplo de tamanho personalizado
    p = canvas.Canvas(pdf_buffer, pagesize=custom_page_size)
    width, height = custom_page_size

    # Estilos do corpo da tabela
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Title'], fontName='Courier-Bold', fontSize=26, textColor=colors.HexColor('#000000'), underline=True)

    # Adiciona o título da página
    title = Paragraph("Relatório de Serviços", title_style)
    title.wrapOn(p, width - 100, -40)
    title.drawOn(p, 50, height - 100)

    # Define o cabeçalho e os dados da tabela
    cabecalho = ["N°chamado", "Assunto", "Nome Funcionário", "Prazo", "Setor", "Nome Solicitante", "Telefone", "Unidade", "Informações Gerais"]
    tabela_dados = [cabecalho] + [list(servico) for servico in servicos]
    colWidths = [80, 290, 150, 100, 130, 150, 100, 300, 335 ]  # Ajuste essas larguras conforme necessário

    # Cria uma tabela com estilo
    tabela = Table(tabela_dados, colWidths=colWidths)

    # Estilos do cabeçalho da tabela
    header_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#115696')),  # Cor azul no cabeçalho
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # Texto branco no cabeçalho
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Courier-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ])

    # Estilos das células da tabela
    cell_style = TableStyle([
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F6BF84')),  # Cor laranja claro no corpo da tabela
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#115696')),  # Texto azul no corpo da tabela
        ('FONTNAME', (0, 1), (-1, -1), 'Courier'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ])

    # Aplica o estilo do cabeçalho e das células
    tabela.setStyle(header_style)  # Aplica o estilo do cabeçalho
    tabela.setStyle(cell_style)    # Aplica o estilo das células

    # Define a altura das linhas da tabela
    tabela.rowHeights = [30] * len(tabela_dados)  # Define a altura das linhas

    # Número máximo de linhas por página
    max_rows_per_page = 20
    y = height - 150
    current_row = 0

    while current_row < len(tabela_dados):
        if y < 50:
            p.showPage()
            p.setFont("Courier-Bold", 26)
            title.drawOn(p, 50, height - 100)
            y = height - 150

        # Desenha o cabeçalho da tabela na nova página
        header_table = Table([cabecalho], colWidths=colWidths)
        header_table.setStyle(header_style)  # Aplica apenas o estilo do cabeçalho
        header_table.wrapOn(p, width - 100, 100)
        header_table.drawOn(p, 50, y)
        y -= 30  # Espaço para o cabeçalho

        # Adiciona as linhas da tabela
        rows_to_draw = tabela_dados[current_row + 1:current_row + max_rows_per_page + 1]  # +1 para pular o cabeçalho
        for row in rows_to_draw:
            row_table = Table([row], colWidths=colWidths)
            row_table.setStyle(cell_style)  # Aplica apenas o estilo das células
            row_table.wrapOn(p, width - 100, 100)
            row_table.drawOn(p, 50, y)
            y -= 20

        current_row += max_rows_per_page

    # Finaliza a página e salva o PDF
    p.save()

    # Define o cabeçalho do arquivo PDF
    pdf_buffer.seek(0)
    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename="relatorio_servicos.pdf"'
    return response
#ROTA PARA GERAR UM RELATÓRIO EM PDF, ONDE IRÁ MOSTRAR AS SOLICITAÇÕES



#GRID DE SOLICITACOES
@app.route("/grid_servicos", methods=['GET', 'POST'])
def grid_servicos():
    if request.method == 'POST':
        try:
            with get_db_connection() as conexao:
                with conexao.cursor() as cursor:
                    cursor.execute("SELECT * FROM servicos")
                    resultado = cursor.fetchall()
                    if resultado is None:
                        resultado = []  # Garante que resultado nunca seja None
                        flash('Nenhuma solicitação encontrada.', 'info')
        except Exception as e:
            flash(f'Erro ao obter solicitações: {str(e)}', 'danger')
            resultado = []  # Garante que resultado nunca seja None
        return render_template('consultas.html', resultado=resultado)
    return render_template('consultas.html', resultado=[])



def buscar_solicitacoes_por_id(servicos_id_seq):
    solicitacoes = []
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT servicos_id_seq, assunto, funcionario, prazo, setor, nome_solicitante, email_solicitante, telefone, unidade, informacoes_adicionais, foto, local, status, categoria, prioridade
                FROM servicos
                WHERE servicos_id_seq = %s
            """, (servicos_id_seq,))
            solicitacoes = cursor.fetchall()  # Obtém uma lista de dicionários
    return {'solicitacoes': solicitacoes}








#Grid de serviços
@app.route("/grid_solicitacoes", methods=['GET', 'POST'])
def grid_solicitacoes():
    if request.method == 'POST':
        try:
            with get_db_connection() as conexao:
                with conexao.cursor() as cursor:
                    # Ajusta a consulta para não incluir o campo 'funcionario'
                    cursor.execute("""
                        SELECT servicos_id_seq, assunto, prazo, setor, nome_solicitante, email_solicitante, telefone, unidade, informacoes_adicionais, foto, local, status
                        FROM servicos
                        WHERE status = 'aberto'
                    """)
                    resultado = cursor.fetchall()
                    if not resultado: 
                        resultado = [] 
                        flash('Nenhuma solicitação encontrada.', 'info')
        except Exception as e:
            flash(f'Erro ao obter solicitações: {str(e)}', 'danger')
            resultado = []  
        return render_template('grid_solicitacoes.html', resultado=resultado)
    return render_template('grid_solicitacoes.html', resultado=[])


def buscar_solicitacoes_por_id(servicos_id_seq):
    solicitacoes = []
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT servicos_id_seq, assunto, funcionario, prazo, setor, nome_solicitante, email_solicitante, telefone, unidade, informacoes_adicionais
                FROM servicos
                WHERE servicos_id_seq = %s
            """, (servicos_id_seq,))
            solicitacoes = cursor.fetchall()  
    return {'solicitacoes': solicitacoes}


@app.route('/servico_solicitacoes/<int:servicos_id_seq>', methods=['GET', 'POST'])
def servico_solicitacoes(servicos_id_seq):
    if request.method == 'POST':
        solicitacao_ids = request.form.getlist('solicitacao_ids')
        categoria = request.form.get('categoria')
        prioridade = request.form.get('prioridade')
        funcionario = request.form.get('funcionario')
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    for id_servico in solicitacao_ids: 
                        cursor.execute("""
                            UPDATE servicos
                            SET status = 'confirmado',
                                funcionario = %s, 
                                categoria = %s,
                                prioridade = %s
                            WHERE servicos_id_seq = %s AND status = 'aberto'
                        """, (funcionario, categoria, prioridade, id_servico))  # Define categoria, funcionario, prioridade
                    conn.commit()
            flash('Solicitação(s) confirmada(s) com sucesso!', 'success')
            return redirect(url_for('servico_solicitacoes', servicos_id_seq=servicos_id_seq))
        except Exception as e:
            print(f"Erro ao atualizar solicitações: {e}")
            flash(f'Erro ao atualizar solicitações: {e}', 'danger')
            return redirect(url_for('servico_solicitacoes', servicos_id_seq=servicos_id_seq))



 # Busca as solicitações associadas ao ID do serviço fornecido
    dados = buscar_solicitacoes_por_id(servicos_id_seq)
    if dados['solicitacoes']:
        return render_template('servico_solicitacoes.html', solicitacoes=dados['solicitacoes'], servicos_id_seq=servicos_id_seq)
    else:
        return "Solicitações não encontradas", 404



#LINK DA IMAGEM
@app.route('/ver-imagem/<int:servicos_id_seq>')
def ver_imagem(servicos_id_seq):
    try:
        # Conecta ao banco de dados e busca o nome da imagem para o serviço
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT foto FROM servicos WHERE servicos_id_seq = %s', (servicos_id_seq,))
                servico = cursor.fetchone()
                if not servico:
                    return "Serviço não encontrado", 404
                if servico[0]:
                    imagem_url = url_for('static', filename=servico[0])
                    return render_template('ver_imagem.html', imagem_url=imagem_url)
                else:
                    return "Imagem não encontrada", 404
    except psycopg2.Error as e:
        print(f"Erro ao buscar imagem: {e}")
        return "Erro ao buscar imagem", 500



# Rota para exibir a lista de clientes
@app.route('/usuarios')
def usuarios():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT nome, email, senha FROM usuarios')
        all_clientes = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('usuarios.html', clientes=all_clientes)
    except Exception as e:
        flash(f'Erro ao obter usuários: {str(e)}', 'danger')
        return redirect(url_for('index'))
    


    

    

# Rota para exibir nome do usuário via JSON
@app.route('/enviar_nome_usuario')
def enviar_nome_usuario():
    if 'user_id' in session:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (session['user_id'],))
            nome_usuario = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return jsonify({"nome_usuario": nome_usuario})
        except Exception as e:
            return jsonify({"nome_usuario": "Erro ao buscar nome"}), 500
    return jsonify({"nome_usuario": "Visitante"})

# Rota para página de erro
@app.route('/erro')
def erro():
    return render_template('erro.html')




#ROTA PARA ABRIR CHAMADO DE SERVIÇOS    
@app.route('/cadastre_solicitacoes', methods=['GET', 'POST'])
def cadastre_solicitacoes():
    if request.method == 'POST':
        assunto = request.form.get('assunto')
        funcionario = request.form.get('funcionario')
        prazo = request.form.get('prazo')
        setor = request.form.get('setor')
        nome_solicitante = request.form.get('nome_solicitante')
        email_solicitante = request.form.get('email_solicitante')
        telefone = request.form.get('telefone')
        unidade = request.form.get('unidade')
        informacoes_adicionais = request.form.get('informacoes_adicionais')
        local = request.form.get('local')
        foto = request.files.get('foto')

        if foto:
            filename = secure_filename(foto.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            foto.save(filepath)
        else:
            filename = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO servicos (assunto, funcionario, prazo, setor, nome_solicitante, email_solicitante, telefone, unidade, informacoes_adicionais, foto, local, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'aberto')
                ''',
                (assunto, funcionario, prazo, setor, nome_solicitante, email_solicitante, telefone, unidade, informacoes_adicionais, filename, local)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Solicitação feita com sucesso!', 'success')
            return redirect(url_for('cadastre_solicitacoes'))
        except Exception as e:
            if conn:
                conn.close()
            flash(f'Erro na solicitação: {str(e)}', 'danger')

    return render_template('abrir_chamado.html')
  # Certifique-se de que o template corresponda
#ROTA PARA ABRIR CHAMADO DE SERVIÇOS


#ROTA DE CADASTRO DE FUNCIONARIO
@app.route('/cadastre_funcionarios', methods=['GET', 'POST'])
def cadastre_funcionarios():
    if request.method == 'POST':
        matricula = request.form['matricula']
        nome = request.form['nome']
        email = request.form['email']
        cpf = request.form['cpf']
        datanasc = request.form['datanasc']
        regiao = request.form['regiao']
        unidade = request.form['unidade']
        telefone = request.form['telefone']
        setor = request.form['setor']
        turno = request.form['turno']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO funcionarios (matricula, nome, email, cpf, datanasc, regiao, unidade, telefone, setor, turno) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (matricula, nome, email, cpf, datanasc, regiao, unidade, telefone, setor, turno)
            )
            conn.commit()
            cursor.close()
            conn.close()

            # Mensagem de sucesso
            flash('Funcionário cadastrado com sucesso!', 'success')
            return redirect(url_for('cadastre_funcionarios'))
        
        except Exception as e:
            flash(f'Erro ao cadastrar funcionário: {str(e)}', 'danger')
            return redirect(url_for('cadastre_funcionarios'))
    
    return render_template('cadastros.html')


# Rota para visualização dos serviços
@app.route("/grid_visualizacao", methods=['GET', 'POST'])
def visualizacao():
    if request.method == 'POST':
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT servicos_id_seq, assunto, funcionario, prazo, setor, nome_solicitante, email_solicitante, telefone, unidade, informacoes_adicionais, foto, local, status
                        FROM public.servicos where status = 'confirmado'
                    """)
                    resultado = cursor.fetchall()
        except Exception as e:
            flash(f'Erro ao obter dados: {str(e)}', 'danger')
            resultado = []
    else:
        resultado = []

    # Renderizar a página de visualização com os dados
    return render_template('grid_visualizacao.html', resultado=resultado)



# Função para buscar solicitações por ID
def buscar_solicitacoes_por_status(id_servicos_seq):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id_servicos_seq, assunto, funcionario, prazo, setor, unidade, nome_solicitante, email_solicitante, telefone, informacoes_adicionais, categoria, prioridade
                    FROM servicos
                    WHERE id_servicos_seq = %s
                """, (id_servicos_seq,))
                servicos = cursor.fetchall()

                servicos_list = [{'id_servicos_seq': s[0], 'assunto': s[1], 'funcionario': s[2], 'prazo': s[3], 'setor': s[4], 'unidade': s[5], 'nome_solicitante': s[6], 'email_solicitante': s[7], 'telefone': s[8], 'informacoes_adicionais': s[9], 'categoria': s[10], 'prioridade': s[11]} for s in servicos]

                return {"solicitacoes": servicos_list}
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return {"solicitacoes": []}


# Rota para visualização detalhada de um serviço
@app.route('/visualizacao/<int:id_servicos_seq>', methods=['GET', 'POST'])
def servico_detalhado(id_servicos_seq):
    if request.method == 'POST':
        servico_ids = request.form.getlist('servicos_ids')
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    for id_servico in servico_ids:
                        cursor.execute("""
                            UPDATE servicos
                            SET status = 'confirmado'
                            WHERE id_servicos_seq = %s
                        """, (id_servico,))
                    conn.commit()
            # Redirecionar para a página de visualização principal após a atualização
            return redirect(url_for('visualizacao'))
        except Exception as e:
            print(f"Erro ao atualizar solicitações: {e}")
            flash(f"Erro ao atualizar solicitações: {e}", 'danger')
            return redirect(url_for('servico_detalhado', id_servicos_seq=id_servicos_seq))
    
    dados = buscar_solicitacoes_por_status(id_servicos_seq)
    if dados['solicitacoes']:
        return render_template('visualizacao.html', servicos=dados['servicos'])
    else:
        return "Solicitações não encontradas", 404
    

@app.route('/get_service_details/<int:id>')
def get_service_details(id):
    for servicos in servicos:
        if servicos['servicos_id_seq'] == id:
            return jsonify(servicos)
    return jsonify({'error': 'Serviço não encontrado'}), 404
    


#ROTA DE CADASTRO DE CATEGORIAS DE SERVIÇOS 
@app.route('/cadastre_categorias', methods=['GET', 'POST'])
def cadastre_categorias():
    if request.method == 'POST':
        nome_categoria = request.form['nome_categoria']
        descricao_categoria = request.form['descricao_categoria']
    
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO categoria_servicos (nome_categoria, descricao_categoria) VALUES (%s, %s)",
                (nome_categoria, descricao_categoria)
            )
            conn.commit()
            cursor.close()
            conn.close()

            # Mensagem de sucesso
            flash('Categoria Cadastrada com Sucesso!', 'success')
            return redirect(url_for('cadastre_categorias'))
        
        except Exception as e:
            flash(f'Erro ao cadastrar a Categoria: {str(e)}', 'danger')
            return redirect(url_for('cadastre_categorias'))
    
    return render_template('cadastros.html')


#ROTA PARA CADASTRO DE SETORES
@app.route('/cadastre_setores', methods=['GET', 'POST'])
def cadastre_setores():
    if request.method == 'POST':
        nome_setor = request.form['nome_setor']
    
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO setor (nome_setor) VALUES (%s)",
                (nome_setor,)  # Corrigido para passar como tupla
            )
            conn.commit()
            cursor.close()
            conn.close()

            # Mensagem de sucesso
            flash('Setor Cadastrado com Sucesso!', 'success')
            return redirect(url_for('cadastre_categorias'))
        
        except Exception as e:
            flash(f'Erro ao cadastrar o Setor: {str(e)}', 'danger')
            return redirect(url_for('cadastre_setores'))
    
    return render_template('cadastros.html')









if __name__ == '__main__':
    app.run(debug=True)