from flask import Flask, render_template, request, redirect, make_response, session, jsonify, flash, url_for
from functools import wraps
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

@app.before_request
def limpar_sessao_invalida():
    """Se a sessão estiver corrompida (cookie antigo/inválido), limpa silenciosamente."""
    try:
        _ = session.get('user_id')
    except Exception:
        session.clear()
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave_padrao_desenvolvimento_1212')
app.config['SESSION_COOKIE_NAME'] = 'solicita_session'  # nome único evita conflito com cookies antigos
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS no Render
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ─── CONEXÃO ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    "postgresql://neondb_owner:npg_giweRPT6d7Gp@ep-autumn-fire-aiuuc96n-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')


# ─── DECORATORS ───────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('user_permissao') != 'Administrador':
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ─── FUNÇÕES AUXILIARES ───────────────────────────────────────────────────────

def gerar_pdf_bytes(servicos):
    pdf_buffer = BytesIO()
    custom_page_size = (1850, 600)
    p = canvas.Canvas(pdf_buffer, pagesize=custom_page_size)
    width, height = custom_page_size
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TitleStyle', parent=styles['Title'],
        fontName='Courier-Bold', fontSize=26,
        textColor=colors.HexColor('#000000'), underline=True
    )
    title = Paragraph("Relatório de Serviços", title_style)
    title.wrapOn(p, width - 100, -40)
    title.drawOn(p, 50, height - 100)
    cabecalho = ["N°chamado", "Assunto", "Nome Funcionário", "Prazo", "Setor",
                 "Nome Solicitante", "Telefone", "Unidade", "Informações Gerais"]
    tabela_dados = [cabecalho] + [list(servico) for servico in servicos]
    colWidths = [80, 290, 150, 100, 130, 150, 100, 300, 335]
    tabela = Table(tabela_dados, colWidths=colWidths)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#115696')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Courier-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F6BF84')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#115696')),
        ('FONTNAME', (0, 1), (-1, -1), 'Courier'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    tabela.rowHeights = [30] * len(tabela_dados)
    tabela.wrapOn(p, width - 100, 100)
    tabela.drawOn(p, 50, height - 150 - (len(tabela_dados) * 30))
    p.showPage()
    p.save()
    pdf_buffer.seek(0)
    return pdf_buffer


def buscar_solicitacoes_por_id(servicos_id_seq):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT servicos_id_seq, assunto, funcionario, prazo, setor, unidade,
                           nome_solicitante, email_solicitante, telefone, informacoes_adicionais, status, foto, local
                    FROM servicos WHERE servicos_id_seq = %s
                """, (servicos_id_seq,))
                solicitacoes = cursor.fetchall()
                return {"solicitacoes": solicitacoes}
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return {"solicitacoes": []}


# ─── AUTENTICAÇÃO ─────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        if not email or not senha:
            flash('Preencha e-mail e senha.', 'danger')
            return render_template('login1.html', email=email)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        'SELECT id, nome, senha, permissao FROM usuarios WHERE email = %s', (email,)
                    )
                    user = cursor.fetchone()
            if user and check_password_hash(user[2], senha):
                session['user_id'] = user[0]
                session['user_nome'] = user[1]
                session['user_permissao'] = user[3]
                flash(f'Bem-vindo, {user[1]}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('E-mail ou senha inválidos. Tente novamente.', 'danger')
                return render_template('login1.html', email=email)
        except Exception as e:
            flash(f'Erro ao tentar login: {str(e)}', 'danger')
            return render_template('login1.html', email=email)
    return render_template('login1.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('login'))


@app.route('/esqueceu_senha', methods=['GET', 'POST'])
def esqueceu_senha():
    if request.method == 'POST':
        flash('Se o e-mail estiver cadastrado, você receberá as instruções em breve.', 'info')
        return redirect(url_for('login'))
    return render_template('esqueceu_senha.html')


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html',
                           nome_usuario=session.get('user_nome', ''),
                           user_permissao=session.get('user_permissao', ''))


@app.route('/servicos')
@login_required
def servicos():
    return render_template('index1.html',
                           nome_usuario=session.get('user_nome', ''),
                           user_permissao=session.get('user_permissao', ''))


# ─── CADASTROS (apenas Administrador) ────────────────────────────────────────

@app.route('/cadastros')
@admin_required
def cadastros():
    setores = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT nome_setor FROM setor ORDER BY nome_setor")
                setores = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        flash(f'Erro ao carregar setores: {str(e)}', 'danger')
    return render_template('cadastros.html', setores=setores)


@app.route('/cadastre_usuarios', methods=['GET', 'POST'])
def cadastre_usuarios():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        matricula = request.form.get('matricula', '').strip()
        setor = request.form.get('setor', '').strip()
        unidade = request.form.get('unidade', '')
        permissao = request.form.get('permissao', '')
        if not all([nome, email, senha, matricula, setor, unidade, permissao]):
            flash('Todos os campos obrigatórios devem ser preenchidos.', 'warning')
            return render_template('cadastros_usuario.html', nome=nome, email=email,
                                   setor=setor, unidade=unidade)
        if not matricula.isdigit():
            flash('Matrícula inválida. Somente números são permitidos.', 'warning')
            return render_template('cadastros_usuario.html', nome=nome, email=email,
                                   setor=setor, unidade=unidade)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT id FROM usuarios WHERE email = %s', (email,))
                    if cursor.fetchone():
                        flash('E-mail já cadastrado. Tente outro e-mail.', 'warning')
                        return render_template('cadastros_usuario.html', nome=nome, email=email,
                                               setor=setor, unidade=unidade)
                    senha_hash = generate_password_hash(senha)
                    cursor.execute(
                        'INSERT INTO usuarios (matricula, nome, email, senha, setor, unidade, permissao) '
                        'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                        (matricula, nome, email, senha_hash, setor, unidade, permissao)
                    )
                    conn.commit()
            flash('Usuário cadastrado com sucesso! Faça login para continuar.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Erro ao cadastrar usuário: {str(e)}', 'danger')
            return render_template('cadastros_usuario.html', nome=nome, email=email,
                                   setor=setor, unidade=unidade)
    return render_template('cadastros_usuario.html')


@app.route('/cadastre_funcionarios', methods=['GET', 'POST'])
@admin_required
def cadastre_funcionarios():
    if request.method == 'POST':
        campos = ['matricula', 'nome', 'email', 'cpf', 'datanasc', 'regiao',
                  'unidade', 'telefone', 'setor', 'turno']
        dados = {c: request.form.get(c, '').strip() for c in campos}
        if not all(dados.values()):
            flash('Todos os campos são obrigatórios.', 'warning')
            return redirect(url_for('cadastros'))
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO funcionarios (matricula, nome, email, cpf, datanasc, regiao, "
                        "unidade, telefone, setor, turno) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        tuple(dados.values())
                    )
                    conn.commit()
            flash('Funcionário cadastrado com sucesso!', 'success')
            return redirect(url_for('cadastros'))
        except Exception as e:
            flash(f'Erro ao cadastrar funcionário: {str(e)}', 'danger')
    return redirect(url_for('cadastros'))


@app.route('/cadastre_categorias', methods=['GET', 'POST'])
@admin_required
def cadastre_categorias():
    if request.method == 'POST':
        nome_categoria = request.form.get('nome_categoria', '').strip()
        descricao_categoria = request.form.get('descricao_categoria', '').strip()
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO categoria_servicos (nome_categoria, descricao_categoria) VALUES (%s, %s)",
                        (nome_categoria, descricao_categoria)
                    )
                    conn.commit()
            flash('Categoria cadastrada com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao cadastrar categoria: {str(e)}', 'danger')
    return redirect(url_for('cadastros'))


@app.route('/cadastre_setores', methods=['GET', 'POST'])
@admin_required
def cadastre_setores():
    if request.method == 'POST':
        nome_setor = request.form.get('nome_setor', '').strip()
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("INSERT INTO setor (nome_setor) VALUES (%s)", (nome_setor,))
                    conn.commit()
            flash('Setor cadastrado com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao cadastrar setor: {str(e)}', 'danger')
    return redirect(url_for('cadastros'))


# ─── CHAMADOS ────────────────────────────────────────────────────────────────

@app.route('/abrir_chamado', methods=['GET', 'POST'])
@login_required
def abrir_chamado():
    # Buscar lista de funcionários para o select
    funcionarios = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT nome FROM funcionarios ORDER BY nome")
                funcionarios = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        flash(f'Erro ao carregar funcionários: {str(e)}', 'danger')

    if request.method == 'POST':
        assunto = request.form.get('assunto', '').strip()
        funcionario = request.form.get('funcionario', '').strip()
        prazo = request.form.get('prazo') or None
        setor = request.form.get('setor', '')
        local = request.form.get('local', '')
        nome_solicitante = request.form.get('nome_solicitante', '').strip()
        email_solicitante = request.form.get('email_solicitante', '').strip()
        telefone = request.form.get('telefone', '').strip()
        unidade = request.form.get('unidade', '')
        informacoes_adicionais = request.form.get('informacoes_adicionais', '').strip()
        foto = request.files.get('foto')

        filename = None
        if foto and foto.filename:
            filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filename = f"uploads/{filename}"

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        '''INSERT INTO servicos
                           (assunto, funcionario, prazo, setor, nome_solicitante, email_solicitante,
                            telefone, unidade, informacoes_adicionais, foto, local, status)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'aberto')''',
                        (assunto, funcionario, prazo, setor, nome_solicitante,
                         email_solicitante, telefone, unidade, informacoes_adicionais, filename, local)
                    )
                    conn.commit()
            flash('Chamado aberto com sucesso!', 'success')
            return redirect(url_for('abrir_chamado'))
        except Exception as e:
            flash(f'Erro ao abrir chamado: {str(e)}', 'danger')

    return render_template('service.html',
                           funcionarios=funcionarios,
                           nome_usuario=session.get('user_nome', ''))


@app.route('/cadastre_solicitacoes', methods=['GET', 'POST'])
def cadastre_solicitacoes():
    return abrir_chamado()


@app.route('/consultar_servicos', methods=['GET', 'POST'])
@login_required
def consultar_servicos():
    resultado = []
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT servicos_id_seq, nome_solicitante, unidade, assunto, local, status "
                    "FROM servicos ORDER BY servicos_id_seq DESC"
                )
                resultado = cursor.fetchall()
    except Exception as e:
        flash(f'Erro ao obter solicitações: {str(e)}', 'danger')
    return render_template('Consultas.html', resultado=resultado)


@app.route('/grid_solicitacoes', methods=['GET', 'POST'])
def grid_solicitacoes():
    return consultar_servicos()


# ─── CONFIRMAÇÃO DE SERVIÇOS (somente Administrador) ─────────────────────────

@app.route('/confirmar_servicos')
@admin_required
def confirmar_servicos():
    resultado = []
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT servicos_id_seq, nome_solicitante, unidade, assunto, local, status "
                    "FROM servicos WHERE status = 'aberto' ORDER BY servicos_id_seq DESC"
                )
                resultado = cursor.fetchall()
    except Exception as e:
        flash(f'Erro ao obter chamados: {str(e)}', 'danger')
    return render_template('confirmar_servicos.html', resultado=resultado)


@app.route('/decidir_servico', methods=['POST'])
@admin_required
def decidir_servico():
    servicos_id_seq = request.form.get('servicos_id_seq')
    decisao = request.form.get('decisao')  # 'confirmado' ou 'descartado'

    if decisao not in ('confirmado', 'descartado'):
        flash('Decisão inválida.', 'danger')
        return redirect(url_for('confirmar_servicos'))

    novo_status = 'confirmado' if decisao == 'confirmado' else 'cancelado'
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE servicos SET status = %s WHERE servicos_id_seq = %s",
                    (novo_status, servicos_id_seq)
                )
                conn.commit()
        msg = 'Chamado confirmado! Agora aparece em Executar Serviços.' if novo_status == 'confirmado' \
              else 'Chamado descartado.'
        flash(msg, 'success' if novo_status == 'confirmado' else 'warning')
    except Exception as e:
        flash(f'Erro ao atualizar chamado: {str(e)}', 'danger')

    return redirect(url_for('confirmar_servicos'))


# ─── DETALHE / EXECUTAR ───────────────────────────────────────────────────────

@app.route('/servico/<int:servicos_id_seq>', methods=['GET', 'POST'])
@login_required
def servico_detalhe(servicos_id_seq):
    if request.method == 'POST':
        novo_status = request.form.get('novo_status', 'confirmado')
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE servicos SET status = %s WHERE servicos_id_seq = %s",
                        (novo_status, servicos_id_seq)
                    )
                    conn.commit()
            flash(f'Chamado atualizado para "{novo_status}" com sucesso!', 'success')
            return redirect(url_for('consultar_servicos'))
        except Exception as e:
            flash(f'Erro ao atualizar chamado: {str(e)}', 'danger')

    dados = buscar_solicitacoes_por_id(servicos_id_seq)
    if dados['solicitacoes']:
        return render_template('servico_solicitacoes.html',
                               solicitacao=dados['solicitacoes'][0],
                               servicos_id_seq=servicos_id_seq)
    flash('Chamado não encontrado.', 'danger')
    return redirect(url_for('consultar_servicos'))


@app.route('/executar_servicos', methods=['GET', 'POST'])
@login_required
def executar_servicos():
    resultado = []
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT servicos_id_seq, assunto, funcionario, prazo, setor, nome_solicitante, "
                    "email_solicitante, telefone, unidade, informacoes_adicionais, foto, local, status "
                    "FROM servicos WHERE status = 'confirmado' ORDER BY servicos_id_seq DESC"
                )
                resultado = cursor.fetchall()
    except Exception as e:
        flash(f'Erro ao obter dados: {str(e)}', 'danger')
    return render_template('grid_visualizacao.html', resultado=resultado)


@app.route('/grid_visualizacao', methods=['GET', 'POST'])
def visualizacao():
    return executar_servicos()


@app.route('/executar/<int:servicos_id_seq>', methods=['GET', 'POST'])
@login_required
def executar_detalhe(servicos_id_seq):
    if request.method == 'POST':
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE servicos SET status = 'executado' WHERE servicos_id_seq = %s",
                        (servicos_id_seq,)
                    )
                    conn.commit()
            flash('Serviço marcado como executado!', 'success')
            return redirect(url_for('executar_servicos'))
        except Exception as e:
            flash(f'Erro ao atualizar: {str(e)}', 'danger')

    dados = buscar_solicitacoes_por_id(servicos_id_seq)
    if dados['solicitacoes']:
        return render_template('visualizacao.html',
                               solicitacao=dados['solicitacoes'][0],
                               servicos_id_seq=servicos_id_seq)
    return redirect(url_for('executar_servicos'))


# ─── RELATÓRIO ────────────────────────────────────────────────────────────────

@app.route('/relatorio')
@login_required
def relatorio():
    resultado = []
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "SELECT servicos_id_seq, assunto, funcionario, prazo, setor, nome_solicitante, "
                    "telefone, unidade, informacoes_adicionais, status "
                    "FROM servicos ORDER BY servicos_id_seq DESC"
                )
                resultado = cursor.fetchall()
    except Exception as e:
        flash(f'Erro ao carregar relatório: {str(e)}', 'danger')
    return render_template('relatorio.html', resultado=resultado)


@app.route('/gerar_servicos_pdf')
@login_required
def gerar_pdf():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    'SELECT servicos_id_seq, assunto, funcionario, prazo, setor, '
                    'nome_solicitante, telefone, unidade, informacoes_adicionais FROM servicos'
                )
                servicos = cursor.fetchall()
        pdf_buffer = gerar_pdf_bytes(servicos)
        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename="relatorio_servicos.pdf"'
        return response
    except Exception as e:
        flash(f'Erro ao gerar PDF: {str(e)}', 'danger')
        return redirect(url_for('relatorio'))


# ─── USUÁRIOS / API ───────────────────────────────────────────────────────────

@app.route('/usuarios')
@login_required
def usuarios():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT nome, email, setor, unidade, permissao FROM usuarios')
                all_usuarios = cursor.fetchall()
        return render_template('usuarios.html', clientes=all_usuarios)
    except Exception as e:
        flash(f'Erro ao obter usuários: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


@app.route('/ver-imagem/<int:servicos_id_seq>')
@login_required
def ver_imagem(servicos_id_seq):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('SELECT foto FROM servicos WHERE servicos_id_seq = %s', (servicos_id_seq,))
                servico = cursor.fetchone()
        if servico and servico[0]:
            imagem_url = url_for('static', filename=servico[0])
            return render_template('ver_imagem.html', imagem_url=imagem_url)
        flash('Imagem não encontrada.', 'warning')
        return redirect(url_for('consultar_servicos'))
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
        return redirect(url_for('consultar_servicos'))


@app.route('/get_service_details/<int:id>')
@login_required
def get_service_details(id):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM servicos WHERE servicos_id_seq = %s", (id,))
                servico = cursor.fetchone()
        if servico:
            # Converter prazo para string para serializar em JSON
            data = dict(servico)
            if data.get('prazo'):
                data['prazo'] = str(data['prazo'])
            return jsonify(data)
        return jsonify({'error': 'Serviço não encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/enviar_nome_usuario')
def enviar_nome_usuario():
    if 'user_id' in session:
        return jsonify({"nome_usuario": session.get('user_nome', 'Usuário')})
    return jsonify({"nome_usuario": "Visitante"})


# ─── AJUDA / ERRO ─────────────────────────────────────────────────────────────

@app.route('/ajuda')
@login_required
def ajuda():
    return render_template('pagina_ajuda.html')


@app.route('/erro')
def erro():
    return render_template('erro.html')


# ─── INICIALIZAÇÃO ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
