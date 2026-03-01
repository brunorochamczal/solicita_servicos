from flask import Flask, render_template, request, redirect, make_response, session, jsonify, flash, url_for
import psycopg2
from psycopg2.extras import RealDictCursor

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os

from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__)
# Configurações devem vir de variáveis de ambiente em produção
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave_padrao_desenvolvimento_1212')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # O tamanho da foto deve ser até 16 MB

# Certifique-se de que o diretório de uploads exista
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DATABASE_URL = os.environ.get('DATABASE_URL', "postgresql://postgres:1234@localhost:5432/testando")

# Função para conectar ao banco de dados
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# --- FUNÇÕES AUXILIARES ---

def gerar_pdf_bytes(servicos):
    """Gera o binário do PDF para o relatório de serviços."""
    pdf_buffer = BytesIO()
    custom_page_size = (1850, 600)
    p = canvas.Canvas(pdf_buffer, pagesize=custom_page_size)
    width, height = custom_page_size

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Title'], fontName='Courier-Bold', fontSize=26, textColor=colors.HexColor('#000000'), underline=True)

    title = Paragraph("Relatório de Serviços", title_style)
    title.wrapOn(p, width - 100, -40)
    title.drawOn(p, 50, height - 100)

    cabecalho = ["N°chamado", "Assunto", "Nome Funcionário", "Prazo", "Setor", "Nome Solicitante", "Telefone", "Unidade", "Informações Gerais"]
    tabela_dados = [cabecalho] + [list(servico) for servico in servicos]
    colWidths = [80, 290, 150, 100, 130, 150, 100, 300, 335]

    tabela = Table(tabela_dados, colWidths=colWidths)

    header_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#115696')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Courier-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ])

    cell_style = TableStyle([
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F6BF84')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#115696')),
        ('FONTNAME', (0, 1), (-1, -1), 'Courier'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ])

    tabela.setStyle(header_style)
    tabela.setStyle(cell_style)
    tabela.rowHeights = [30] * len(tabela_dados)

    # Lógica de paginação simplificada para o exemplo
    tabela.wrapOn(p, width - 100, 100)
    tabela.drawOn(p, 50, height - 150 - (len(tabela_dados) * 30)) # Ajuste simples de posição
    
    p.showPage()
    p.save()
    pdf_buffer.seek(0)
    return pdf_buffer


# Rota principal - REDIRECIONA PARA LOGIN SE NÃO ESTIVER LOGADO
@app.route('/')
def index():
    # Se o usuário NÃO estiver logado, redireciona para login
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Se estiver logado, mostra a página principal
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT nome FROM usuarios WHERE id = %s', (session['user_id'],))
                user = cursor.fetchone()

        if user:
            nome_usuario = user[0]
            return render_template('index.html', nome_usuario=nome_usuario) # Corrigido para index.html (dashboard)
        else:
            flash('Usuário não encontrado.', 'danger')
            return redirect(url_for('login'))
    except Exception as e:
        flash(f'Erro ao obter nome do usuário: {str(e)}', 'danger')
        return redirect(url_for('login'))

# Rota para a página de serviços (abrir chamado, consultar, confirmar, executar)
@app.route('/servicos')
def servicos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index1.html')

# Rota para cadastro de novos usuários (acesso público)
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
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Verifica se o e-mail já existe
                    cursor.execute('SELECT id FROM usuarios WHERE email = %s', (email,))
                    email_exists = cursor.fetchone()

                    if email_exists:
                        flash('E-mail já cadastrado. Tente outro e-mail.', 'warning')
                        return render_template('cadastros_usuario.html', nome=nome, email=email)
                    else:
                        # Hash da senha para segurança
                        senha_hash = generate_password_hash(senha)
                        cursor.execute(
                            'INSERT INTO usuarios (matricula, nome, email, senha, setor, unidade, permissao) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                            (matricula, nome, email, senha_hash, setor, unidade, permissao)
                        )
                        conn.commit()
                        flash('Usuário cadastrado com sucesso! Faça login para continuar.', 'success')
                        return redirect(url_for('login'))
            
        except Exception as e:
            flash(f'Erro ao cadastrar usuário: {str(e)}', 'danger')
            return render_template('cadastros_usuario.html', nome=nome, email=email, setor=setor, unidade=unidade, permissao=permissao)

    return render_template('cadastros_usuario.html')

# Rota para login de usuários
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Se já estiver logado, redireciona para a página principal
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT id, nome, senha FROM usuarios WHERE email = %s', (email,))
                    user = cursor.fetchone()

            # Verifica se o usuário existe e se a senha (hash) confere
            if user and check_password_hash(user[2], senha):
                session['user_id'] = user[0]
                session['user_nome'] = user[1]
                flash(f'Bem-vindo, {user[1]}!', 'success')
                return render_template('index.html')
            else:
                flash('E-mail ou senha inválidos. Tente novamente.', 'danger')
                return render_template('index.html', email=email)
        except Exception as e:
            flash(f'Erro ao tentar login: {str(e)}', 'danger')
            return render_template('login2.html', email=email)

    return render_template('login1.html')

# Rota para logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('login'))

# ROTA PARA GERAR UM RELATÓRIO EM PDF
@app.route('/gerar_servicos_pdf')
def gerar_pdf():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT servicos_id_seq, assunto, funcionario, prazo, setor, nome_solicitante, telefone, unidade, informacoes_adicionais FROM servicos')
            servicos = cursor.fetchall()

    # Usa a função auxiliar para gerar o PDF
    pdf_buffer = gerar_pdf_bytes(servicos)

    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename="relatorio_servicos.pdf"'
    return response

# GRID DE SOLICITACOES
@app.route("/grid_solicitacoes", methods=['GET', 'POST'])
def grid_solicitacoes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    resultado = []
    if request.method == 'POST':
        try:
            with get_db_connection() as conexao:
                with conexao.cursor() as cursor:
                    cursor.execute("SELECT * FROM servicos")
                    resultado = cursor.fetchall()
                    if not resultado:
                        flash('Nenhuma solicitação encontrada.', 'info')
        except Exception as e:
            flash(f'Erro ao obter solicitações: {str(e)}', 'danger')
    return render_template('consultas.html', resultado=resultado)

@app.route('/servico_solicitacoes/<int:servicos_id_seq>', methods=['GET', 'POST'])
def servico_solicitacoes(servicos_id_seq):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        solicitacao_ids = request.form.getlist('solicitacao_ids')
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    for id_servico in solicitacao_ids:
                        cursor.execute("""
                            UPDATE servicos
                            SET status = 'confirmado'
                            WHERE servicos_id_seq = %s AND status = 'aberto'
                        """, (id_servico,))
                    conn.commit()
            flash('Solicitação(s) confirmada(s) com sucesso!', 'success')
            return redirect(url_for('servico_solicitacoes', servicos_id_seq=servicos_id_seq))
        except Exception as e:
            flash(f'Erro ao atualizar solicitações: {e}', 'danger')
            return redirect(url_for('servico_solicitacoes', servicos_id_seq=servicos_id_seq))

    dados = buscar_solicitacoes_por_id(servicos_id_seq)
    if dados['solicitacoes']:
        return render_template('servico_solicitacoes.html', solicitacoes=dados['solicitacoes'], servicos_id_seq=servicos_id_seq)
    else:
        return "Solicitações não encontradas", 404

@app.route('/ver-imagem/<int:servicos_id_seq>')
def ver_imagem(servicos_id_seq):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
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
        return "Erro ao buscar imagem", 500

# Rota para exibir a lista de usuários
@app.route('/usuarios')
def usuarios():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT nome, email, setor, unidade, permissao FROM usuarios')
                all_clientes = cursor.fetchall()
        return render_template('usuarios.html', clientes=all_clientes)
    except Exception as e:
        flash(f'Erro ao obter usuários: {str(e)}', 'danger')
        return redirect(url_for('index'))

# Rota para exibir nome do usuário via JSON
@app.route('/enviar_nome_usuario')
def enviar_nome_usuario():
    if 'user_id' in session:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (session['user_id'],))
                    nome_usuario = cursor.fetchone()[0]
            return jsonify({"nome_usuario": nome_usuario})
        except Exception as e:
            return jsonify({"nome_usuario": "Erro ao buscar nome"}), 500
    return jsonify({"nome_usuario": "Visitante"})

# Rota para página de erro
@app.route('/erro')
def erro():
    return render_template('erro.html')

# ROTA PARA ABRIR CHAMADO DE SERVIÇOS
@app.route('/cadastre_solicitacoes', methods=['GET', 'POST'])
def cadastre_solicitacoes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
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

        filename = None
        if foto and foto.filename != '':
            filename = secure_filename(foto.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            foto.save(filepath)

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        '''
                        INSERT INTO servicos (assunto, funcionario, prazo, setor, nome_solicitante, email_solicitante, telefone, unidade, informacoes_adicionais, foto, local, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'aberto')
                        ''',
                        (assunto, funcionario, prazo, setor, nome_solicitante, email_solicitante, telefone, unidade, informacoes_adicionais, filename, local)
                    )
                    conn.commit()
            flash('Solicitação feita com sucesso!', 'success')
            return redirect(url_for('cadastre_solicitacoes'))
        except Exception as e:
            flash(f'Erro na solicitação: {str(e)}', 'danger')

    return render_template('abrir_chamado.html')

@app.route("/grid_funcionarios", methods=['GET', 'POST'])
def grid_funcionarios():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    resultado = []
    if request.method == 'POST':
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM funcionarios") # Corrigido: estava consultando servicos
                    resultado = cursor.fetchall()
        except Exception as e:
            flash(f'Erro ao acessar o banco de dados: {e}', 'danger')
    
    return render_template('consultas.html', resultado=resultado)

# ROTA DE CADASTRO DE FUNCIONARIO
@app.route('/cadastre_funcionarios', methods=['GET', 'POST'])
def cadastre_funcionarios():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
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
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO funcionarios (matricula, nome, email, cpf, datanasc, regiao, unidade, telefone, setor, turno) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (matricula, nome, email, cpf, datanasc, regiao, unidade, telefone, setor, turno)
                    )
                    conn.commit()

            flash('Funcionário cadastrado com sucesso!', 'success')
            return redirect(url_for('cadastre_funcionarios'))
        
        except Exception as e:
            flash(f'Erro ao cadastrar funcionário: {str(e)}', 'danger')
            return redirect(url_for('cadastre_funcionarios'))
    
    return render_template('cadastros.html')

# Rota para visualização dos serviços
@app.route("/grid_visualizacao", methods=['GET', 'POST'])
def visualizacao():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    resultado = []
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

    return render_template('grid_visualizacao.html', resultado=resultado)

# Função para buscar solicitações por ID
def buscar_solicitacoes_por_id(servicos_id_seq):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT servicos_id_seq, assunto, funcionario, prazo, setor, unidade, nome_solicitante, email_solicitante, telefone, informacoes_adicionais
                    FROM servicos
                    WHERE servicos_id_seq = %s
                """, (servicos_id_seq,))
                solicitacoes = cursor.fetchall()
                return {"solicitacoes": solicitacoes}
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return {"solicitacoes": []}

# Rota para visualização detalhada de um serviço
@app.route('/visualizacao/<int:servicos_id_seq>', methods=['GET', 'POST'])
def servico_detalhado(servicos_id_seq):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        servico_ids = request.form.getlist('servicos_ids')
        
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    for id_servico in servico_ids:
                        cursor.execute("""
                            UPDATE servicos
                            SET status = 'confirmado'
                            WHERE servicos_id_seq = %s
                        """, (id_servico,))
                    conn.commit()
            return redirect(url_for('visualizacao'))
        except Exception as e:
            flash(f"Erro ao atualizar solicitações: {e}", 'danger')
            return redirect(url_for('servico_detalhado', servicos_id_seq=servicos_id_seq))
    
    dados = buscar_solicitacoes_por_id(servicos_id_seq)
    if dados['solicitacoes']:
        return render_template('visualizacao.html', solicitacoes=dados['solicitacoes'], servicos_id_seq=servicos_id_seq)
    else:
        return "Solicitações não encontradas", 404

@app.route('/get_service_details/<int:id>')
def get_service_details(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM servicos WHERE servicos_id_seq = %s", (id,))
                servico = cursor.fetchone()
        
        if servico:
            return jsonify(servico)
        return jsonify({'error': 'Serviço não encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ROTA DE CADASTRO DE CATEGORIAS DE SERVIÇOS
@app.route('/cadastre_categorias', methods=['GET', 'POST'])
def cadastre_categorias():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome_categoria = request.form['nome_categoria']
        descricao_categoria = request.form['descricao_categoria']
    
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO categoria_servicos (nome_categoria, descricao_categoria) VALUES (%s, %s)",
                        (nome_categoria, descricao_categoria)
                    )
                    conn.commit()

            flash('Categoria Cadastrada com Sucesso!', 'success')
            return redirect(url_for('cadastre_categorias'))
        
        except Exception as e:
            flash(f'Erro ao cadastrar a Categoria: {str(e)}', 'danger')
            return redirect(url_for('cadastre_categorias'))
    
    return render_template('cadastros.html')

# ROTA PARA CADASTRO DE SETORES
@app.route('/cadastre_setores', methods=['GET', 'POST'])
def cadastre_setores():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome_setor = request.form['nome_setor']
    
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO setor (nome_setor) VALUES (%s)",
                        (nome_setor,)
                    )
                    conn.commit()

            flash('Setor Cadastrado com Sucesso!', 'success')
            return redirect(url_for('cadastre_setores'))
        
        except Exception as e:
            flash(f'Erro ao cadastrar o Setor: {str(e)}', 'danger')
            return redirect(url_for('cadastre_setores'))
    
    return render_template('cadastros.html')

if __name__ == '__main__':
    app.run(debug=True)