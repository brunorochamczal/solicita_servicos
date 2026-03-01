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
    try:
        _ = session.get('user_id')
    except Exception:
        session.clear()

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave_padrao_desenvolvimento_1212')
app.config['SESSION_COOKIE_NAME'] = 'solicita_session'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    "postgresql://neondb_owner:npg_giweRPT6d7Gp@ep-autumn-fire-aiuuc96n-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ─── DECORATORS ───────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def permissao_required(*permissoes_permitidas):
    """Aceita lista de permissões. Administrador sempre passa."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            p = session.get('user_permissao', '')
            if p == 'Administrador' or p in permissoes_permitidas:
                return f(*args, **kwargs)
            flash('Você não tem permissão para acessar esta área.', 'danger')
            return redirect(url_for('servicos'))
        return decorated
    return decorator


# ─── PDF ──────────────────────────────────────────────────────────────────────
def gerar_pdf_bytes(servicos):
    from reportlab.platypus import SimpleDocTemplate, Spacer
    from reportlab.lib.units import cm

    pdf_buffer = BytesIO()

    # Página A4 paisagem — espaço generoso para todas as colunas
    PAGE_W = 29.7 * cm   # 841 pt
    PAGE_H = 21.0 * cm   # 595 pt
    MARGIN = 1.5 * cm

    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=(PAGE_W, PAGE_H),
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    styles = getSampleStyleSheet()

    # ── Estilos de parágrafo para dentro das células ──────────────────────────
    header_style = ParagraphStyle(
        'HeaderCell',
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=colors.white,
        leading=14,
        wordWrap='CJK',
    )
    cell_style = ParagraphStyle(
        'BodyCell',
        fontName='Helvetica',
        fontSize=11,
        textColor=colors.HexColor('#115696'),
        leading=15,
        wordWrap='CJK',
    )

    # ── Largura disponível e proporção das colunas ────────────────────────────
    usable_w = PAGE_W - 2 * MARGIN   # ~810 pt
    # N°  | Assunto | Funcionário | Prazo  | Setor  | Solicitante | Telefone | Unidade | Informações
    col_proportions = [0.06, 0.14, 0.11, 0.08, 0.09, 0.10, 0.10, 0.13, 0.19]
    col_widths = [usable_w * p for p in col_proportions]

    cabecalho = ["N°", "Assunto", "Funcionário", "Prazo", "Setor",
                 "Solicitante", "Telefone", "Unidade", "Informações"]

    # Linha de cabeçalho com Paragraphs para permitir wrap
    header_row = [Paragraph(h, header_style) for h in cabecalho]

    # Linhas de dados — cada célula é um Paragraph (garante quebra automática)
    data_rows = []
    for servico in servicos:
        row = [Paragraph(str(c) if c is not None else '', cell_style) for c in servico]
        data_rows.append(row)

    tabela_dados = [header_row] + data_rows

    tabela = Table(tabela_dados, colWidths=col_widths, repeatRows=1)
    tabela.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#115696')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('ALIGN',         (0, 0), (-1, 0), 'LEFT'),
        ('TOPPADDING',    (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        # Dados — linhas alternadas
        ('BACKGROUND',    (0, 1), (-1, -1), colors.HexColor('#F6BF84')),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1),
         [colors.HexColor('#FFF3E0'), colors.HexColor('#F6BF84')]),
        ('TEXTCOLOR',     (0, 1), (-1, -1), colors.HexColor('#115696')),
        ('TOPPADDING',    (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        # Grade
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#888888')),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))

    # ── Título ────────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        'ReportTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#115696'),
        alignment=1,      # centralizado
        spaceAfter=14,
    )
    title = Paragraph("Relatório de Serviços", title_style)

    story = [title, tabela]
    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer


# ─── LOGIN / LOGOUT ───────────────────────────────────────────────────────────
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
                flash('E-mail ou senha inválidos.', 'danger')
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


# ─── CADASTROS — somente Administrador ───────────────────────────────────────
@app.route('/cadastros')
@permissao_required()   # só Administrador (nenhuma outra permissão é listada)
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
        nome      = request.form.get('nome', '').strip()
        email     = request.form.get('email', '').strip()
        senha     = request.form.get('senha', '')
        matricula = request.form.get('matricula', '').strip()
        setor     = request.form.get('setor', '').strip()
        unidade   = request.form.get('unidade', '')
        permissao = request.form.get('permissao', '')
        if not all([nome, email, senha, matricula, setor, unidade, permissao]):
            flash('Todos os campos obrigatórios devem ser preenchidos.', 'warning')
            return render_template('cadastros_usuario.html')
        if not matricula.isdigit():
            flash('Matrícula inválida. Somente números são permitidos.', 'warning')
            return render_template('cadastros_usuario.html')
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT id FROM usuarios WHERE email = %s', (email,))
                    if cursor.fetchone():
                        flash('E-mail já cadastrado.', 'warning')
                        return render_template('cadastros_usuario.html')
                    senha_hash = generate_password_hash(senha)
                    cursor.execute(
                        'INSERT INTO usuarios (matricula, nome, email, senha, setor, unidade, permissao) '
                        'VALUES (%s,%s,%s,%s,%s,%s,%s)',
                        (matricula, nome, email, senha_hash, setor, unidade, permissao)
                    )
                    conn.commit()
            flash('Usuário cadastrado com sucesso!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Erro ao cadastrar usuário: {str(e)}', 'danger')
    return render_template('cadastros_usuario.html')


@app.route('/cadastre_funcionarios', methods=['GET', 'POST'])
@permissao_required()
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
        except Exception as e:
            flash(f'Erro ao cadastrar funcionário: {str(e)}', 'danger')
    return redirect(url_for('cadastros'))


@app.route('/cadastre_categorias', methods=['GET', 'POST'])
@permissao_required()
def cadastre_categorias():
    if request.method == 'POST':
        nome_cat = request.form.get('nome_categoria', '').strip()
        desc_cat = request.form.get('descricao_categoria', '').strip()
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO categoria_servicos (nome_categoria, descricao_categoria) VALUES (%s,%s)",
                        (nome_cat, desc_cat)
                    )
                    conn.commit()
            flash('Categoria cadastrada com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao cadastrar categoria: {str(e)}', 'danger')
    return redirect(url_for('cadastros'))


@app.route('/cadastre_setores', methods=['GET', 'POST'])
@permissao_required()
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


# ─── ABRIR CHAMADO — Solicitação + Administrador ──────────────────────────────
@app.route('/abrir_chamado', methods=['GET', 'POST'])
@permissao_required('Solicitação')
def abrir_chamado():
    """
    UPLOAD DE FOTO:
    - O arquivo é recebido via multipart/form-data
    - É salvo em static/uploads/<nome_arquivo>  (pasta no servidor)
    - O banco armazena apenas o caminho relativo: "uploads/<nome_arquivo>"
    - Para exibir: <img src="/static/uploads/<nome_arquivo>">
    """
    funcionarios = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT nome FROM funcionarios ORDER BY nome")
                funcionarios = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        flash(f'Erro ao carregar funcionários: {str(e)}', 'danger')

    if request.method == 'POST':
        assunto               = request.form.get('assunto', '').strip()
        funcionario           = request.form.get('funcionario', '').strip()
        prazo                 = request.form.get('prazo') or None
        setor                 = request.form.get('setor', '')
        local                 = request.form.get('local', '')
        nome_solicitante      = request.form.get('nome_solicitante', '').strip()
        email_solicitante     = request.form.get('email_solicitante', '').strip()
        telefone              = request.form.get('telefone', '').strip()
        unidade               = request.form.get('unidade', '')
        informacoes_adicionais = request.form.get('informacoes_adicionais', '').strip()
        foto = request.files.get('foto')

        filename = None
        if foto and foto.filename and allowed_file(foto.filename):
            filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            filename = f"uploads/{filename}"   # caminho relativo salvo no banco

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
    return redirect(url_for('abrir_chamado'))


# ─── CONSULTAR SERVIÇOS — todos os perfis ─────────────────────────────────────
@app.route('/consultar_servicos')
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
        flash(f'Erro ao obter serviços: {str(e)}', 'danger')
    return render_template('Consultas.html', resultado=resultado)


@app.route('/grid_solicitacoes')
def grid_solicitacoes():
    return redirect(url_for('consultar_servicos'))


# ─── CONFIRMAÇÃO — Confirmação + Administrador ────────────────────────────────
@app.route('/confirmar_servicos')
@permissao_required('Confirmação')
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
@permissao_required('Confirmação')
def decidir_servico():
    """Chefe decide se o chamado prossegue (confirmado) ou é rejeitado (cancelado)."""
    servico_id = request.form.get('servicos_id_seq')
    decisao    = request.form.get('decisao')   # 'confirmado' ou 'descartado'
    observacao = request.form.get('observacao_confirmacao', '').strip()

    if decisao not in ('confirmado', 'descartado'):
        flash('Decisão inválida.', 'danger')
        return redirect(url_for('confirmar_servicos'))

    novo_status = 'confirmado' if decisao == 'confirmado' else 'cancelado'
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE servicos SET status = %s, observacao_confirmacao = %s "
                    "WHERE servicos_id_seq = %s",
                    (novo_status, observacao, servico_id)
                )
                conn.commit()
        if novo_status == 'confirmado':
            flash('Chamado confirmado! Agora aparece em Executar Serviços.', 'success')
        else:
            flash('Chamado descartado com sucesso.', 'warning')
    except Exception as e:
        flash(f'Erro ao atualizar chamado: {str(e)}', 'danger')
    return redirect(url_for('confirmar_servicos'))


# ─── EXECUTAR SERVIÇOS — Executar + Administrador ────────────────────────────
@app.route('/executar_servicos')
@permissao_required('Executar')
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
    return render_template('executar_servicos.html', resultado=resultado)


@app.route('/concluir_servico', methods=['POST'])
@permissao_required('Executar')
def concluir_servico():
    """Trabalhador confirma que o serviço foi realizado, com observação opcional."""
    servico_id = request.form.get('servicos_id_seq')
    observacao = request.form.get('observacao_execucao', '').strip()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE servicos SET status = 'executado', observacao_execucao = %s "
                    "WHERE servicos_id_seq = %s",
                    (observacao, servico_id)
                )
                conn.commit()
        flash('Serviço marcado como executado com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao concluir serviço: {str(e)}', 'danger')
    return redirect(url_for('executar_servicos'))


@app.route('/grid_visualizacao')
def grid_visualizacao():
    return redirect(url_for('executar_servicos'))


# ─── RELATÓRIO — todos os perfis ──────────────────────────────────────────────
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


# ─── API JSON ─────────────────────────────────────────────────────────────────
@app.route('/get_service_details/<int:id>')
@login_required
def get_service_details(id):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM servicos WHERE servicos_id_seq = %s", (id,))
                servico = cursor.fetchone()
        if servico:
            data = dict(servico)
            if data.get('prazo'):
                data['prazo'] = str(data['prazo'])
            # Normaliza o caminho da foto para sempre ser "uploads/arquivo.ext"
            foto = data.get('foto') or ''
            if foto:
                # Remove prefixos duplicados caso existam
                foto = foto.replace('static/uploads/', '').replace('uploads/', '')
                data['foto'] = f"uploads/{foto}"
            return jsonify(data)
        return jsonify({'error': 'Serviço não encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/enviar_nome_usuario')
def enviar_nome_usuario():
    if 'user_id' in session:
        return jsonify({"nome_usuario": session.get('user_nome', 'Usuário')})
    return jsonify({"nome_usuario": "Visitante"})


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


# ─── AJUDA ────────────────────────────────────────────────────────────────────
@app.route('/ajuda')
@login_required
def ajuda():
    return render_template('pagina_ajuda.html')


@app.route('/ajuda/abrir_chamado')
@login_required
def ajuda_abrir_chamado():
    return render_template('ajuda_abrir_chamado.html')


@app.route('/ajuda/consultar_servico')
@login_required
def ajuda_consultar_servico():
    return render_template('ajuda_consultar_servico.html')


@app.route('/ajuda/confirmar_servico')
@login_required
def ajuda_confirmar_servico():
    return render_template('ajuda_confirmar_servico.html')


@app.route('/ajuda/executar_servico')
@login_required
def ajuda_executar_servico():
    return render_template('ajuda_executar_servico.html')


@app.route('/ajuda/relatorio')
@login_required
def ajuda_relatorio():
    return render_template('ajuda_relatorio.html')


@app.route('/ajuda/cadastro')
@login_required
def ajuda_cadastro():
    return render_template('ajuda_cadastro.html')


@app.route('/erro')
def erro():
    return render_template('erro.html')


# ─── INICIALIZAÇÃO ────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)False)
