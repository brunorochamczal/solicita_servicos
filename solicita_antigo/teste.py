import psycopg2

try:
    conexao = psycopg2.connect(
        host="localhost",
        database="testando",
        user="postgres",
        password="1234",
        port="5432"
    )
    print("✅ Conectado com sucesso!")
    conexao.close()
    
except Exception as e:
    print(f"❌ Falha na conexão: {e}")