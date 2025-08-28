import sqlite3

# Conectando ao banco
conn = sqlite3.connect('brasileirao.db')
cursor = conn.cursor()

times_2025 = [
    {"nome": "Flamengo", "estado": "RJ", "pontos": 46, "vitorias": 14, "empates": 4, "derrotas": 2, "saldo_gols": 35},
    {"nome": "Palmeiras", "estado": "SP", "pontos": 42, "vitorias": 13, "empates": 3, "derrotas": 4, "saldo_gols": 15},
    {"nome": "Cruzeiro", "estado": "MG", "pontos": 41, "vitorias": 12, "empates": 5, "derrotas": 3, "saldo_gols": 19},
    {"nome": "Bahia", "estado": "BA", "pontos": 36, "vitorias": 10, "empates": 6, "derrotas": 4, "saldo_gols": 10},
    {"nome": "Botafogo", "estado": "RJ", "pontos": 32, "vitorias": 9, "empates": 5, "derrotas": 6, "saldo_gols": 14},
    {"nome": "Mirassol", "estado": "SP", "pontos": 32, "vitorias": 9, "empates": 5, "derrotas": 6, "saldo_gols": 9},
    {"nome": "São Paulo", "estado": "SP", "pontos": 32, "vitorias": 9, "empates": 5, "derrotas": 6, "saldo_gols": 10},
    {"nome": "Bragantino", "estado": "SP", "pontos": 30, "vitorias": 9, "empates": 3, "derrotas": 8, "saldo_gols": 2},
    {"nome": "Fluminense", "estado": "RJ", "pontos": 27, "vitorias": 7, "empates": 6, "derrotas": 7, "saldo_gols": -3},
    {"nome": "Ceará", "estado": "CE", "pontos": 26, "vitorias": 7, "empates": 5, "derrotas": 8, "saldo_gols": 0},
    {"nome": "Corinthians", "estado": "SP", "pontos": 25, "vitorias": 7, "empates": 4, "derrotas": 9, "saldo_gols": -5},
    {"nome": "Atlético-MG", "estado": "MG", "pontos": 24, "vitorias": 6, "empates": 6, "derrotas": 8, "saldo_gols": 0},
    {"nome": "Internacional", "estado": "RS", "pontos": 24, "vitorias": 6, "empates": 6, "derrotas": 8, "saldo_gols": -2},
    {"nome": "Grêmio", "estado": "RS", "pontos": 24, "vitorias": 6, "empates": 6, "derrotas": 8, "saldo_gols": -6},
    {"nome": "Santos", "estado": "SP", "pontos": 21, "vitorias": 6, "empates": 3, "derrotas": 11, "saldo_gols": -11},
    {"nome": "Vasco", "estado": "RJ", "pontos": 19, "vitorias": 5, "empates": 4, "derrotas": 11, "saldo_gols": -9},
    {"nome": "Vitória", "estado": "BA", "pontos": 19, "vitorias": 5, "empates": 4, "derrotas": 11, "saldo_gols": -14},
    {"nome": "Juventude", "estado": "RS", "pontos": 18, "vitorias": 5, "empates": 3, "derrotas": 12, "saldo_gols": -23},
    {"nome": "Fortaleza", "estado": "CE", "pontos": 15, "vitorias": 3, "empates": 6, "derrotas": 11, "saldo_gols": -13},
    {"nome": "Sport", "estado": "PE", "pontos": 10, "vitorias": 1, "empates": 7, "derrotas": 12, "saldo_gols": -18}
]

#Atualizado 28/08/2025

#SEGUE O LIDER

#VOCE PENSA QUE O FLAMENGO É TIME????



# Inserindo os times
for time in times_2025:
    cursor.execute('''
        INSERT INTO times (nome, estado, pontos, vitorias, empates, derrotas, saldo_gols)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (time["nome"], time["estado"], time["pontos"], time["vitorias"], 
          time["empates"], time["derrotas"], time["saldo_gols"]))

# Salvando e fechando a conexão
conn.commit()
conn.close()
